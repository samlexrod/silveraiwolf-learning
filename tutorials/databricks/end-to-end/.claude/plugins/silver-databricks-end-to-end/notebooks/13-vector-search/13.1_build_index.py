# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 13 · 13.1 — Build the Vector Search index (parse → chunk → embed)
# MAGIC
# MAGIC The `seed` stage landed 85 contract **PDFs** and credit-memo **markdown** in
# MAGIC `silverline.bronze.files/{contracts,memos}/` and nothing has used them since. Here we turn them into a
# MAGIC **searchable index**: parse the files into a Delta table, then build a **delta-sync Vector Search index**
# MAGIC that auto-embeds every chunk. Run on **serverless**.
# MAGIC
# MAGIC > ⚠️ **The endpoint is created via CLI, not here** (`databricks vector-search-endpoints create-endpoint
# MAGIC > silverline-vs STANDARD`). This notebook builds the **table + index** on that endpoint. The first sync
# MAGIC > takes **~10–20 min** on Free Edition (lazy compute provisioning) — that's expected, not a hang.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Parse the docs into `silverline.silver.doc_chunks`
# MAGIC PDFs are parsed **natively** with `ai_parse_document()` (no `pypdf`); memos are read as whole text. We
# MAGIC concatenate each PDF's extracted elements into one document, one chunk per file (the seeded docs are one
# MAGIC page each). **Change Data Feed is on** — the delta-sync index requires it to track new/changed docs.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS silverline.silver;
# MAGIC
# MAGIC CREATE OR REPLACE TABLE silverline.silver.doc_chunks
# MAGIC   TBLPROPERTIES (delta.enableChangeDataFeed = true) AS
# MAGIC WITH contracts AS (
# MAGIC   SELECT
# MAGIC     path AS source_path,
# MAGIC     'contract' AS doc_type,
# MAGIC     concat_ws('\n',
# MAGIC       transform(ai_parse_document(content):document:elements::ARRAY<VARIANT>,
# MAGIC                 e -> e:content::STRING)) AS content
# MAGIC   FROM READ_FILES('/Volumes/silverline/bronze/files/contracts/*.pdf', format => 'binaryFile')
# MAGIC ),
# MAGIC memos AS (
# MAGIC   SELECT _metadata.file_path AS source_path, 'memo' AS doc_type, value AS content
# MAGIC   FROM READ_FILES('/Volumes/silverline/bronze/files/memos/*.md', format => 'text', wholetext => true)
# MAGIC )
# MAGIC SELECT
# MAGIC   md5(source_path)                          AS chunk_id,     -- stable primary key
# MAGIC   regexp_extract(source_path, '([^/]+)$', 1) AS doc_id,      -- e.g. contract_1.pdf
# MAGIC   doc_type, source_path, content
# MAGIC FROM (SELECT * FROM contracts UNION ALL SELECT * FROM memos)
# MAGIC WHERE content IS NOT NULL AND length(content) > 0;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Expect ~95 rows (85 contracts + 10 memos). Peek at one contract + one memo.
# MAGIC SELECT doc_type, count(*) AS n FROM silverline.silver.doc_chunks GROUP BY doc_type;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT doc_id, doc_type, substr(content, 1, 200) AS preview
# MAGIC FROM silverline.silver.doc_chunks
# MAGIC WHERE doc_id IN ('contract_1.pdf', 'credit_memo_3.md');

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Create the delta-sync index (auto-embed via `databricks-bge-large-en`)
# MAGIC A **delta-sync** index stays current from the source table and **computes the embeddings for you** — we
# MAGIC only point it at a Free-Edition embedding endpoint. `databricks-bge-large-en` (1024-dim) is verified
# MAGIC invokable on Free Edition. Idempotent: it deletes any existing index of the same name first.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.104.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn, VectorIndexType, PipelineType)

ENDPOINT = "silverline-vs"                          # created via CLI (see the stage doc, Section 1)
INDEX    = "silverline.silver.doc_chunks_idx"
SOURCE   = "silverline.silver.doc_chunks"
EMB      = "databricks-bge-large-en"
w = WorkspaceClient()

try:
    w.vector_search_indexes.delete_index(index_name=INDEX)
    print("deleted existing index (rebuild)")
except Exception:
    pass

w.vector_search_indexes.create_index(
    name=INDEX,
    endpoint_name=ENDPOINT,
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
# MAGIC ## 3 — Wait for the first sync (~10–20 min on Free Edition)
# MAGIC The endpoint shows `ONLINE` immediately, but the real compute provisions **lazily when the first index
# MAGIC attaches**. Poll until `ready=True` and the rows are indexed. This is a one-time cost; later syncs are fast.

# COMMAND ----------

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
