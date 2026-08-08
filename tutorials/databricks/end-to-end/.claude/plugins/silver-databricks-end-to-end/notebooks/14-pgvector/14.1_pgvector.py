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
# MAGIC **The ceiling:** at large scale, big document sets, or governed lakehouse RAG, the managed
# MAGIC Vector Search (Stage 13) is the better fit. pgvector shines when the data is **small-to-medium** and you'd
# MAGIC rather not stand up — and **pay for** — a separate, dedicated vector-search service just to add search to a
# MAGIC database you already run. (You do own the embed + keeping the vectors fresh — a Delta→Lakebase refresh —
# MAGIC where Stage 13's delta-sync handled that for you.)
# MAGIC
# MAGIC > 🧭 **Delta-sync (Stage 13) vs pgvector (here).** There the index embedded + synced *for* you off a Delta
# MAGIC > table. Here **you** embed the docs and `INSERT` the vectors yourself — the trade is more control and a
# MAGIC > join to live OLTP data, in exchange for owning the embed + refresh.
# MAGIC >
# MAGIC > 🗄️ **Precondition:** the `vector-search` stage's `silverline.silver.doc_chunks` table (the parsed contract
# MAGIC > text) — we read the documents from it. If it's missing, run `13-vector-search/13.1_build_index` Section 2
# MAGIC > first. (We only *read* the text here; embeddings + storage are all pgvector.)

# COMMAND ----------

# MAGIC # Install **pure** psycopg — NOT `psycopg[binary]`. The binary wheel bundles its own libpq, which
# MAGIC # SIGABRTs ("the Python kernel is unresponsive") on this serverless runtime once Spark's native libs
# MAGIC # (pyarrow/grpc) are loaded. Pure psycopg links the runtime's **system** libpq — same OpenSSL as those
# MAGIC # libs, so no conflict. `-U` also pulls a databricks-sdk new enough for the autoscaling API (`w.postgres`).
# MAGIC %pip install -U psycopg "databricks-sdk>=0.104.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Connect to Lakebase and enable pgvector
# MAGIC We mint a short-lived credential via the SDK (no token to paste), connect over SSL to the OLTP Postgres,
# MAGIC and turn on the extension. `CREATE EXTENSION vector` is the gate — everything below rides on it.

# COMMAND ----------

import psycopg
from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()
HOST  = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER  = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token

# One autocommit connection reused across the cells below. psycopg (psycopg3) is Databricks' documented
# Lakebase driver; the SDK mints a short-lived OAuth token used as the Postgres password.
conn = psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER,
                       password=TOKEN, sslmode="require", autocommit=True)
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
# MAGIC ### Peek at what you stored
# MAGIC The next cell previews five rows of `doc_embeddings` so the store isn't abstract. You'll see:
# MAGIC - **`contract_id`** — the join key into the live `contracts` table (what makes Section 5's filter possible)
# MAGIC - **`content_preview`** — the document text that got embedded
# MAGIC - **`dims`** — `1024`, the width of a `databricks-bge-large-en` vector
# MAGIC - **`embedding_head`** — the first few of those 1024 floats, so you can actually *see* the vector
# MAGIC
# MAGIC Each row is one document's *meaning* stored as numbers, sitting right beside your transactional rows.

# COMMAND ----------

import pandas as pd

preview = cur.execute("""
    SELECT contract_id,
           doc_id,
           left(content, 40)                AS content_preview,
           vector_dims(embedding)           AS dims,
           left(embedding::text, 40) || '…' AS embedding_head
    FROM doc_embeddings
    ORDER BY contract_id
    LIMIT 5
""").fetchall()
display(pd.DataFrame(preview, columns=["contract_id", "doc_id", "content_preview", "dims", "embedding_head"]))

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
# MAGIC ### See *why* the index matters — benchmark it yourself
# MAGIC Our 85 docs are too few to feel the difference, so the next cells time a nearest-neighbor query on a
# MAGIC **scratch table of 5,000 random vectors** — first with **no index**, then with **HNSW**. Watch two things
# MAGIC in the output: the query **plan** (`Seq Scan` → `Index Scan`) and the **milliseconds**. The scratch table
# MAGIC is dropped at the end; your real `doc_embeddings` keeps the index built above.

# COMMAND ----------

import numpy as np
import time

N = 5000
cur.execute("DROP TABLE IF EXISTS bench_index_demo")
cur.execute("CREATE TABLE bench_index_demo (id int, embedding vector(1024))")
V = np.random.default_rng(0).random((N, 1024), dtype="float32")
with cur.copy("COPY bench_index_demo (id, embedding) FROM STDIN") as cp:      # fast bulk load
    for i in range(N):
        cp.write_row([i, "[" + ",".join(map(str, V[i].tolist())) + "]"])
QUERY_VEC = "[" + ",".join(map(str, np.random.default_rng(1).random(1024, dtype="float32").tolist())) + "]"

KNN = "SELECT id FROM bench_index_demo ORDER BY embedding <=> %s::vector LIMIT 5"

def knn_ms(reps=5):
    best = 1e9
    for _ in range(reps):
        t0 = time.perf_counter()
        cur.execute(KNN, (QUERY_VEC,)).fetchall()
        best = min(best, time.perf_counter() - t0)
    return best * 1000

def plan_line():                                                             # the Seq/Index Scan node
    return next(r[0].strip() for r in cur.execute("EXPLAIN " + KNN, (QUERY_VEC,)).fetchall() if "Scan" in r[0])

print(f"loaded {N} random vectors into bench_index_demo")

# COMMAND ----------

# MAGIC %md
# MAGIC **Without an index** — Postgres compares your query to *every* row (a sequential scan):

# COMMAND ----------

print("plan:", plan_line())                       # -> Seq Scan on bench_index_demo
no_index_ms = knn_ms()
print(f"no index (sequential scan): {no_index_ms:6.1f} ms")

# COMMAND ----------

# MAGIC %md
# MAGIC **With HNSW** — the *identical* query, now navigating the index graph:

# COMMAND ----------

cur.execute("CREATE INDEX ON bench_index_demo USING hnsw (embedding vector_cosine_ops)")
print("plan:", plan_line())                       # -> Index Scan using ..._hnsw
with_index_ms = knn_ms()
print(f"with HNSW index:            {with_index_ms:6.1f} ms   →   ~{no_index_ms/with_index_ms:.0f}x faster")

cur.execute("DROP TABLE bench_index_demo")
print("scratch table dropped — your doc_embeddings index (above) stays")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Retrieve by meaning (cosine `<=>`)
# MAGIC Embed the question the same way, then order by **cosine distance** (`<=>`). `1 - (embedding <=> q)` is the
# MAGIC cosine **similarity** (higher = closer). This is the pgvector equivalent of Stage 13's `vector_search()`.
# MAGIC
# MAGIC > 📐 **"Distance" between two vectors — three common ones; pick by what you're comparing.** Picture each
# MAGIC > embedding as an arrow from the origin in 1024-D space, and take two of them, `a=[1,2,3]` and `b=[4,6,8]`:
# MAGIC >
# MAGIC > | Metric | pgvector | On `a,b` | Intuition |
# MAGIC > |---|---|---|---|
# MAGIC > | **Euclidean / L2** | `<->` (`vector_l2_ops`) | `7.07` | the **pigeon** — it flies straight over the Manhattan rooftops, corner to corner in one diagonal hop (`√(3²+4²+5²)`). |
# MAGIC > | **Manhattan / L1** | `<+>` (`vector_l1_ops`) | `12` | the **yellow cab** — it can't fly, so it drives the blocks one direction at a time and adds them up: 3 + 4 + 5 = 12, never diagonal (`\|3\|+\|4\|+\|5\|`). |
# MAGIC > | **Cosine** | `<=>` (`vector_cosine_ops`) | `0.007` | **the angle** between the arrows, **ignoring length** — do they *point the same way*? |
# MAGIC >
# MAGIC > *Same trip across Manhattan, two ways: the pigeon flies the straight line, the cab counts the blocks. Cosine is a different question again — it ignores distance entirely and asks only whether two vectors point the **same way**.*
# MAGIC >
# MAGIC > **Why cosine for text?** The model encodes *meaning as direction*; a vector's **length** tends to track
# MAGIC > doc length / word count — which we don't want deciding a "same topic?" match. Cosine throws length away
# MAGIC > and compares direction only, so a one-paragraph memo and a ten-page contract about the same thing still
# MAGIC > score close. That's why it's the default for semantic search — and why our HNSW index was built with
# MAGIC > `vector_cosine_ops`. (Reach for L2/L1 when magnitude *is* the signal — raw counts, coordinates, pixels.)

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
# MAGIC governance + scale, pgvector when the data is small-to-medium and you'd rather not run — and pay for — a
# MAGIC separate, dedicated vector-search service.
# MAGIC
# MAGIC > 🧹 The `doc_embeddings` table lives on the Lakebase `production` branch; the tutorial's `cleanup` drops it
# MAGIC > with the Lakebase project. Nothing here costs money — quota only.

# COMMAND ----------

conn.close()
print("done — connection closed")
