# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 14 · 14.1 — pgvector retrieval in Lakebase
# MAGIC
# MAGIC Stage 13 built a **managed, lakehouse-native** retriever (Mosaic AI Vector Search). This stage shows the
# MAGIC **lighter-weight alternative** — **pgvector** inside the `silverline-oltp` Lakebase Postgres you already
# MAGIC run — same contract corpus, no separate vector-search service to stand up or pay for.
# MAGIC
# MAGIC **When is it the right call? Small-to-medium corpora.** When the document set doesn't justify a dedicated
# MAGIC vector service, just keep the embeddings **in the same Postgres as your transactional rows** (`contracts`,
# MAGIC `customers`, …) — cheaper and simpler to operate. And because they're co-located, one query does what the
# MAGIC managed service can't in a single shot: **semantic retrieval *and* a transactional filter** (Section 5) —
# MAGIC *"find the **delinquent** contracts that are about earth-moving equipment"* — vector search and structured
# MAGIC filter in **one engine, against live rows**, no fan-out to a separate store and back.
# MAGIC
# MAGIC **The ceiling (be honest):** at large scale, big document sets, or governed lakehouse RAG, the managed
# MAGIC Vector Search (Stage 13) is the better fit. pgvector shines when the data is **small-to-medium** and you'd
# MAGIC rather not run a second system — and you do own the embed + keeping the vectors fresh (a Delta→Lakebase
# MAGIC refresh), where Stage 13's delta-sync handled that for you.
# MAGIC
# MAGIC > 🧭 **Delta-sync (Stage 13) vs pgvector (here).** There the index embedded + synced *for* you off a Delta
# MAGIC > table. Here **you** embed the docs and `INSERT` the vectors yourself — the trade is more control and a
# MAGIC > join to live OLTP data, in exchange for owning the embed + refresh.
# MAGIC >
# MAGIC > 🗄️ **Precondition:** the `vector-search` stage's `silverline.silver.doc_chunks` table (the parsed contract
# MAGIC > text) — we read the documents from it. If it's missing, run `13-vector-search/13.1_build_index` Section 2
# MAGIC > first. (We only *read* the text here; embeddings + storage are all pgvector.)

# COMMAND ----------

# MAGIC # -U forces the newest databricks-sdk: the autoscaling-Postgres API (`w.postgres`) isn't in older
# MAGIC # pre-installed runtime versions, and a bare `>=` floor lets the run keep a stale one.
# MAGIC %pip install -U pg8000 "databricks-sdk>=0.104.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Connect to Lakebase and enable pgvector
# MAGIC We mint a short-lived credential via the SDK (no token to paste), connect over SSL to the OLTP Postgres,
# MAGIC and turn on the extension. `CREATE EXTENSION vector` is the gate — everything below rides on it.

# COMMAND ----------

import ssl
import pg8000.dbapi
from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()
HOST  = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER  = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token

# Connect with pg8000 — a **pure-Python** Postgres driver.
# Driver note: Databricks' docs recommend psycopg (`psycopg[binary]`). We tested it here and it **SIGABRTs
# (exit 134 → "the Python kernel is unresponsive") on this Free-Edition serverless runtime** — it survives a
# bare connect but crashes the *full* notebook, where its bundled libpq/OpenSSL aborts alongside the
# pandas/pyarrow/grpc native libs Spark loads. pg8000 has no native code, so it can't — it runs the whole
# workload green. Lakebase requires SSL; an encrypt-only context matches `sslmode=require`.
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
conn = pg8000.dbapi.connect(host=HOST, port=5432, database="databricks_postgres", user=USER,
                            password=TOKEN, ssl_context=ssl_ctx)
conn.autocommit = True
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
print(f"connected to {HOST} as {USER}  ·  pgvector {cur.fetchone()[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Embed the contract docs yourself, store them next to the OLTP data
# MAGIC No managed embedding here — **you** call the model. We read the parsed contract text from `doc_chunks`,
# MAGIC embed each doc with `databricks-bge-large-en` (1024-dim), and `INSERT` the vectors into a `vector(1024)`
# MAGIC column **keyed by `contract_id`** — so every embedding lines up with a real row in the `contracts` table.
# MAGIC That key is what makes Section 5's join possible.

# COMMAND ----------

import re

# Read the parsed contract documents from the Stage-13 table (Spark), derive the numeric contract_id.
rows = (spark.table("silverline.silver.doc_chunks")
        .filter("doc_type = 'contract'")
        .select("doc_id", "content").collect())
docs = [(int(re.search(r"contract_(\d+)", r["doc_id"]).group(1)), r["doc_id"], r["content"]) for r in rows]
print(f"{len(docs)} contract docs to embed")

def embed(texts):
    """Embed a list of texts with the Free-Edition bge-large-en endpoint (batched)."""
    out = []
    for i in range(0, len(texts), 20):
        out += [d.embedding for d in w.serving_endpoints.query(name="databricks-bge-large-en",
                                                               input=texts[i:i+20]).data]
    return out

vectors = embed([content for _, _, content in docs])
print(f"embedded {len(vectors)} docs · dim {len(vectors[0])}")

# COMMAND ----------

# Store them in pgvector. The embedding is passed as a '[f1,f2,…]' string literal cast to ::vector
# (no extra adapter needed). Idempotent: rebuild the table each run.
cur.execute("DROP TABLE IF EXISTS doc_embeddings")
cur.execute("""
    CREATE TABLE doc_embeddings (
        contract_id int  PRIMARY KEY,
        doc_id      text,
        content     text,
        embedding   vector(1024)
    )
""")
for (cid, did, content), vec in zip(docs, vectors):
    cur.execute(
        "INSERT INTO doc_embeddings (contract_id, doc_id, content, embedding) VALUES (%s, %s, %s, %s::vector)",
        (cid, did, content, "[" + ",".join(map(str, vec)) + "]"))
cur.execute("SELECT count(*) FROM doc_embeddings")
print(f"stored {cur.fetchone()[0]} rows in doc_embeddings")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Index for fast nearest-neighbor search (HNSW)
# MAGIC Without an index, a query scans every row (fine for 85 docs; not for millions). **HNSW** is pgvector's
# MAGIC approximate-nearest-neighbor index — `vector_cosine_ops` matches the `<=>` (cosine distance) operator we
# MAGIC query with.

# COMMAND ----------

cur.execute("CREATE INDEX IF NOT EXISTS doc_embeddings_hnsw ON doc_embeddings "
            "USING hnsw (embedding vector_cosine_ops)")
print("HNSW cosine index ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Retrieve by meaning (cosine `<=>`)
# MAGIC Embed the question the same way, then order by cosine distance. `1 - (embedding <=> q)` is the cosine
# MAGIC **similarity** (higher = closer). This is the pgvector equivalent of Stage 13's `vector_search()`.

# COMMAND ----------

import pandas as pd

def search(query_text, extra_sql="", params=()):
    qv = "[" + ",".join(map(str, embed([query_text])[0])) + "]"
    cur.execute(f"""
        SELECT c.contract_id, c.status,
               round((1 - (e.embedding <=> %s::vector))::numeric, 4) AS cosine_sim,
               left(e.content, 60) AS preview
        FROM doc_embeddings e
        JOIN contracts c USING (contract_id)
        {extra_sql}
        ORDER BY e.embedding <=> %s::vector
        LIMIT 5
    """, (qv, *params, qv))
    return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])

display(search("financing for heavy earth-moving machinery"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — The payoff: semantic retrieval **+ a transactional filter**, in one SQL
# MAGIC The embeddings live *inside* the OLTP database, so a single query can do **both** jobs at once: rank by
# MAGIC meaning **and** filter on live transactional columns. Ask *"which of our **delinquent / charged-off**
# MAGIC contracts are about earth-moving equipment?"* — the `JOIN contracts … WHERE status IN (…)` runs right
# MAGIC beside the `<=>` similarity. Mosaic AI Vector Search can't do this in one query — the structured filter
# MAGIC lives in a different system.

# COMMAND ----------

# Scoped: only genuinely troubled contracts, ranked by semantic relevance.
display(search("financing for heavy earth-moving machinery",
               extra_sql="WHERE c.status IN (%s, %s)", params=("delinquent", "charged_off")))

# COMMAND ----------

# Contrast — the same semantic query with NO status filter returns a mix of active/paid_off/delinquent.
display(search("financing for heavy earth-moving machinery"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 — Which retriever, when?
# MAGIC | | **Mosaic AI Vector Search** (Stage 13) | **pgvector in Lakebase** (this stage) |
# MAGIC |---|---|---|
# MAGIC | Where it lives | the lakehouse (Unity Catalog) | inside the **operational Postgres** |
# MAGIC | Embeddings | **managed** — the index embeds for you | **you** embed + `INSERT` the vectors |
# MAGIC | Staying current | auto (delta-sync + CDF) | you re-embed / upsert on change |
# MAGIC | Killer move | governed, joins to **gold**/Genie; scales to huge corpora | **retrieval + live OLTP filter in one SQL** (query-time, one engine) |
# MAGIC | You own | little — managed embed + sync | getting embeddings *in* + keeping them fresh (Delta→Lakebase refresh) |
# MAGIC | Reach for it when | **large** corpora · governed lakehouse RAG · scale | **small-to-medium** data · no separate service (cheaper) · retrieval next to app data |
# MAGIC
# MAGIC Same embedding model, same corpus — **two options for two scales**: the managed service when you need
# MAGIC governance + scale, pgvector when the data is small-to-medium and you'd rather not run a second system.
# MAGIC
# MAGIC > 🧹 The `doc_embeddings` table lives on the Lakebase `production` branch; the tutorial's `cleanup` drops it
# MAGIC > with the Lakebase project. Nothing here costs money — quota only.

# COMMAND ----------

conn.close()
print("done — connection closed")
