# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 13 · 13.1 — Build the Vector Search index (endpoint → parse → embed)
# MAGIC
# MAGIC The `seed` stage landed 85 contract **PDFs** and credit-memo **markdown** in
# MAGIC `silverline.bronze.files/{contracts,memos}/` and nothing has used them since. Here we do the whole build
# MAGIC **in this notebook**: create the **Vector Search endpoint**, parse the files into a Delta table, then build a
# MAGIC **delta-sync Vector Search index** that auto-embeds every chunk. Run on **serverless**.
# MAGIC
# MAGIC > 🧰 **Two ways to create the endpoint — you run the SDK one here.** Section 1 creates the endpoint with the
# MAGIC > **Python SDK** so the entire build lives in one place. The **CLI does the exact same thing** and is handy
# MAGIC > for scripts/CI — it's shown right beside the code so you learn both:
# MAGIC > `databricks vector-search-endpoints create-endpoint silverline-vs STANDARD`.
# MAGIC >
# MAGIC > ⚠️ **First sync takes ~10–20 min on Free Edition.** The endpoint reports `ONLINE` *instantly*, but the real
# MAGIC > compute is provisioned **lazily when the first index attaches** (Section 3) — so the initial sync is slow.
# MAGIC > That's expected, not a hang.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.104.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Create the Vector Search endpoint
# MAGIC Free Edition allows **one** Vector Search endpoint — the serving unit your index attaches to. We create it
# MAGIC **idempotently**: if `silverline-vs` already exists we reuse it. This is the same object the CLI would make.
# MAGIC
# MAGIC **CLI equivalent** (same result — use it in a script/CI instead of the SDK if you prefer):
# MAGIC ```bash
# MAGIC databricks vector-search-endpoints create-endpoint silverline-vs STANDARD   # --no-wait returns immediately
# MAGIC databricks vector-search-endpoints get-endpoint    silverline-vs            # check state / num_indexes
# MAGIC ```

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import EndpointType

ENDPOINT = "silverline-vs"
w = WorkspaceClient()

try:
    w.vector_search_endpoints.get_endpoint(endpoint_name=ENDPOINT)
    print(f"endpoint '{ENDPOINT}' already exists — reusing it")
except Exception:
    w.vector_search_endpoints.create_endpoint(name=ENDPOINT, endpoint_type=EndpointType.STANDARD)
    print(f"created endpoint '{ENDPOINT}' (STANDARD)")

# The endpoint flips to ONLINE almost immediately, but real compute is provisioned lazily on first index
# attach (Section 3) — so we don't block here; the one-time wait happens during the first index sync.
ep = w.vector_search_endpoints.get_endpoint(endpoint_name=ENDPOINT)
print("state:", ep.endpoint_status.state, "| num_indexes:", ep.num_indexes)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Parse the docs into `silverline.silver.doc_chunks`
# MAGIC **Let's use the docs we already created.** Back in the `seed` stage you generated these files from the
# MAGIC *same deterministic mock data* as the structured tables (`scripts/generate_contract_docs.py`: one
# MAGIC `reportlab` PDF per contract + a credit memo per customer) and uploaded them to
# MAGIC `bronze/files/{contracts,memos}/` — nothing external to fetch here, we just point at the volume.
# MAGIC
# MAGIC Two things follow from how they were built, and both matter downstream:
# MAGIC - **Parity** — `contract_36.pdf` is the *same entity* as contract row 36 in gold. That's what lets you join
# MAGIC   "row 36 is charged_off" (Genie) with "here's its default clause" (this retriever).
# MAGIC - **Fictional + boilerplate** — each PDF footers *"not a real contract,"* and every contract carries the
# MAGIC   *same five boilerplate clauses*. So a "what happens if they stop paying?" query matches nearly all of
# MAGIC   them, while make/model details (wheel loader, forklift) vary and separate cleanly.
# MAGIC
# MAGIC Now parse them: PDFs are read **natively** with `ai_parse_document()` (no `pypdf`); memos are read as whole
# MAGIC text. We concatenate each PDF's extracted elements into one document, one chunk per file (the seeded docs
# MAGIC are one page each). **Change Data Feed is on** — the delta-sync index requires it to track new/changed docs.
# MAGIC
# MAGIC > ℹ️ The `CREATE OR REPLACE TABLE … AS` cell **builds the table — it doesn't return data**, so its grid
# MAGIC > shows *"No rows returned"* (just `num_inserted_rows`). That's expected — the **two cells below** confirm
# MAGIC > the load: `85 contract + 10 memo = 95` rows, then a preview of the parsed text.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Setup: make sure the silver schema exists (idempotent, no-op if it already does).
# MAGIC CREATE SCHEMA IF NOT EXISTS silverline.silver;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Parse both sources into one chunked table. Change Data Feed is on so the delta-sync index can
# MAGIC -- incrementally pick up new/changed docs.
# MAGIC CREATE OR REPLACE TABLE silverline.silver.doc_chunks
# MAGIC   TBLPROPERTIES (delta.enableChangeDataFeed = true) AS
# MAGIC WITH contracts AS (
# MAGIC   -- Each PDF → one document. ai_parse_document() pulls structured elements out of the binary;
# MAGIC   -- we stitch their text back into a single string with newlines.
# MAGIC   SELECT
# MAGIC     path AS source_path,
# MAGIC     'contract' AS doc_type,
# MAGIC     concat_ws(
# MAGIC       '\n',
# MAGIC       transform(
# MAGIC         ai_parse_document(content):document:elements::ARRAY<VARIANT>,
# MAGIC         e -> e:content::STRING
# MAGIC       )
# MAGIC     ) AS content
# MAGIC   FROM
# MAGIC     READ_FILES('/Volumes/silverline/bronze/files/contracts/*.pdf', format => 'binaryFile')
# MAGIC ),
# MAGIC memos AS (
# MAGIC   -- Each memo is small markdown — read the whole file as one document.
# MAGIC   SELECT
# MAGIC     _metadata.file_path AS source_path,
# MAGIC     'memo' AS doc_type,
# MAGIC     value AS content
# MAGIC   FROM
# MAGIC     READ_FILES('/Volumes/silverline/bronze/files/memos/*.md', format => 'text', wholetext => true)
# MAGIC )
# MAGIC SELECT
# MAGIC   md5(source_path) AS chunk_id, -- stable primary key
# MAGIC   regexp_extract(source_path, '([^/]+)$', 1) AS doc_id, -- e.g. contract_1.pdf
# MAGIC   doc_type,
# MAGIC   source_path,
# MAGIC   content
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT
# MAGIC       *
# MAGIC     FROM
# MAGIC       contracts
# MAGIC     UNION ALL
# MAGIC     SELECT
# MAGIC       *
# MAGIC     FROM
# MAGIC       memos
# MAGIC   )
# MAGIC WHERE
# MAGIC   content IS NOT NULL
# MAGIC   AND length(content) > 0;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Sanity-check the load: expect 85 contract + 10 memo = 95 rows.
# MAGIC SELECT doc_type, count(*) AS n FROM silverline.silver.doc_chunks GROUP BY doc_type;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Spot-check the parsed text — the "garbage in, garbage out" gate
# MAGIC The **`content` column is the whole point of this table** — in Section 3 the delta-sync index feeds it
# MAGIC straight to the `databricks-bge-large-en` **embedding model**, so every vector (and therefore every search
# MAGIC result later) is computed from *exactly this text*. That's why we parse the PDFs into `content`:
# MAGIC you can't embed a binary PDF, but you can embed the words we extracted from it.
# MAGIC
# MAGIC So before spending ~15 minutes indexing, eyeball that the parse produced **clean, readable** text. The next
# MAGIC cell previews the first 200 chars of one contract and one memo. What to look for:
# MAGIC
# MAGIC - **`contract_1.pdf`** → the preview should read like the agreement itself
# MAGIC   (*"SILVERLINE CAPITAL — EQUIPMENT FINANCE AGREEMENT · Agreement No. …"*). That's proof `ai_parse_document()`
# MAGIC   extracted real text from the **binary PDF** — not empty, not garbled bytes.
# MAGIC - **`credit_memo_3.md`** → clean markdown (*"# Credit Memo — …"*), confirming the non-PDF path landed too.
# MAGIC - **`doc_type`** is tagged correctly (`contract` vs `memo`) — that's the exact column Way 2 filters on in `13.2`.
# MAGIC
# MAGIC If a preview comes back empty or **garbled** — encoding junk (the technical term is *mojibake*) like
# MAGIC `SILVERLINE CAPITAL â€" EQUIPMENT…` instead of clean text, the symptom of a wrong character encoding — fix
# MAGIC the parse **now**. An index built over blank or garbled content retrieves nothing, and you won't discover
# MAGIC it until after the long sync.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   doc_id,
# MAGIC   doc_type,
# MAGIC   substr(content, 1, 200) AS content_preview
# MAGIC FROM
# MAGIC   silverline.silver.doc_chunks
# MAGIC WHERE
# MAGIC   doc_id IN ('contract_1.pdf', 'credit_memo_3.md');

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Create the delta-sync index (auto-embed via `databricks-bge-large-en`)
# MAGIC
# MAGIC The index we build here is **bound to the `doc_chunks` Delta table** as its source of truth — that's the
# MAGIC "delta-sync" part. It reads the table's **Change Data Feed** (why we enabled it in Section 2) and keeps
# MAGIC itself in step: add or change rows and it re-embeds **only those**, no full rebuild — the low-maintenance
# MAGIC path, since the table is the source and syncing is automatic. (There's a second index type, **Direct Vector
# MAGIC Access**, where you manage the vectors yourself — the aside below shows exactly how it differs.)
# MAGIC
# MAGIC It also **embeds for you**: we point it at a Free-Edition embedding endpoint and name the text column
# MAGIC (`content`), and the index runs each chunk through `databricks-bge-large-en` (1024-dim, verified on Free
# MAGIC Edition) and stores the vector — no precomputing.
# MAGIC
# MAGIC `pipeline_type=TRIGGERED` syncs once, on demand — the cheapest mode (vs `CONTINUOUS`, which streams updates
# MAGIC and holds compute). The cell is idempotent: it deletes any existing index of the same name, then attaches a
# MAGIC fresh one to the `silverline-vs` endpoint from Section 1.
# MAGIC
# MAGIC How it all wires together — the **Change Data Feed** is the link that lets the index stay current without a
# MAGIC full rebuild:
# MAGIC
# MAGIC ```text
# MAGIC  BUILD & KEEP-CURRENT
# MAGIC  ────────────────────
# MAGIC    Contract PDFs + memos  (UC volume)
# MAGIC         │  ai_parse_document() / READ_FILES()
# MAGIC         ▼
# MAGIC    doc_chunks — Delta table  (CDF = on)
# MAGIC         │  Change Data Feed  →  only new / changed / deleted rows
# MAGIC         ▼
# MAGIC    delta-sync index (doc_chunks_idx) ───── content ─────►  databricks-bge-large-en
# MAGIC                                       ◄─── 1024-dim vec ───  (embedding model)
# MAGIC
# MAGIC  QUERY
# MAGIC  ─────
# MAGIC    query_text ──── vector_search() ────►  doc_chunks_idx  ────►  ranked nearest-neighbor chunks
# MAGIC ```
# MAGIC
# MAGIC The point: when `doc_chunks` changes, CDF hands the index **only the changed rows**, it re-embeds **just
# MAGIC those** through `bge-large-en`, and queries see the update — no full re-index.

# COMMAND ----------

# MAGIC %md
# MAGIC > 🔀 **There's a second index type — Direct Vector Access**, where there's *no* source table and **you**
# MAGIC > compute the embeddings and upsert the raw vectors yourself. Rather than hand-wave it, the optional notebook
# MAGIC > **`13.3_direct_access_demo`** builds one *live* — embed → create a `DIRECT_ACCESS` index → upsert your
# MAGIC > vectors → query by vector → tear down (verified on Free Edition: an "earth-moving machinery" query ranked
# MAGIC > the wheel-loader doc top). Delta-sync (below) is the default for a table-backed corpus like ours; direct
# MAGIC > access is the tool when the vectors are yours to manage.

# COMMAND ----------

from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn, VectorIndexType, PipelineType)

INDEX  = "silverline.silver.doc_chunks_idx"
SOURCE = "silverline.silver.doc_chunks"
EMB    = "databricks-bge-large-en"

try:
    w.vector_search_indexes.delete_index(index_name=INDEX)
    print("deleted existing index (rebuild)")
except Exception:
    pass

w.vector_search_indexes.create_index(
    name=INDEX,
    endpoint_name=ENDPOINT,                         # the endpoint created in Section 1
    primary_key="chunk_id",
    index_type=VectorIndexType.DELTA_SYNC,
    delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
        source_table=SOURCE,
        pipeline_type=PipelineType.TRIGGERED,
        embedding_source_columns=[EmbeddingSourceColumn(
            name="content", embedding_model_endpoint_name=EMB)],
    ),
)
print("index create submitted")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Wait for the first sync (~10–20 min on Free Edition)
# MAGIC The endpoint showed `ONLINE` in Section 1, but the real compute provisions **lazily now that the first index
# MAGIC attaches**. Poll until `ready=True` and the rows are indexed. This is a one-time cost; later syncs are fast.

# COMMAND ----------

import time

last = None
for _ in range(120):                                # up to ~30 min
    s = w.vector_search_indexes.get_index(index_name=INDEX).status
    line = f"ready={s.ready} rows={s.indexed_row_count} — {s.message}"
    if line != last:
        print(line); last = line
    if s.ready and (s.indexed_row_count or 0) > 0:
        break
    time.sleep(15)
print("✅ index is ready" if s.ready else "⏳ still provisioning — re-run this cell")

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Index built.** `silverline.silver.doc_chunks_idx` is live on `silverline-vs`, auto-embedded and
# MAGIC synced from `doc_chunks`. Continue to **`13.2_retrieval`** to query it four ways.
