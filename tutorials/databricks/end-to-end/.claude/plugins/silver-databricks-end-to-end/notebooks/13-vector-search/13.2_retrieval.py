# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 13 · 13.2 — Retrieve four ways (the RAG-consumption ladder)
# MAGIC
# MAGIC `13.1` built `silverline.silver.doc_chunks_idx`. Here we **consume** it four ways — from a one-line SQL
# MAGIC query up to a reusable **tool** an agent can call. Same index throughout. Run on **serverless**.
# MAGIC
# MAGIC > 🧭 **Two intents — pick the query to match.** Vector search serves *two* jobs, and the query you ask
# MAGIC > should fit the job:
# MAGIC > - **FIND / retrieve** — you want a **list of documents** to open (*"show me the agreements that finance
# MAGIC >   wheel loaders"*). The raw ranked list **is** the answer. → Ways 1, 2, 4.
# MAGIC > - **ANSWER (RAG)** — you're asking *what to do / what does it say*, and you want a **synthesized answer**,
# MAGIC >   not a document list (*"what happens if a customer stops paying?"*). The docs are hidden **context**
# MAGIC >   the model reads. → Way 3.
# MAGIC >
# MAGIC > Same index, same `vector_search()` under the hood — the difference is whether you *read the list* or
# MAGIC > *feed it to a model*. Asking a "what to do" question in a raw-list cell returns a pile of contracts, which
# MAGIC > is the wrong shape for that question — so the cells below use FIND queries for 1/2/4 and an ANSWER query for 3.
# MAGIC
# MAGIC | # | Pattern | Intent | Surface |
# MAGIC |---|---|---|---|
# MAGIC | 1 | `vector_search()` in SQL | **find** | retrieval inside a `SELECT`, joinable to gold |
# MAGIC | 2 | SDK `query_index(filters=…)` | **find** (scoped) | programmatic + server-side pre-filter |
# MAGIC | 3 | inline RAG (`ai_query` ground+cite) | **answer** | retrieve → answer from context |
# MAGIC | 4 | retriever as a **UC function** | **find** (reusable) | a tool for analysts / Genie / **the agent** |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Way 1 — `vector_search()` in SQL  (intent: **find**)
# MAGIC Semantic retrieval right inside a `SELECT`. `query_text` is embedded with the same model the index uses,
# MAGIC then matched by nearest-neighbor. This is a **find** query — you want the *documents*, and the ranked list
# MAGIC is the result. Note the query never says "loader", yet it surfaces wheel-loader agreements — semantic
# MAGIC matching a keyword `LIKE` couldn't do.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT doc_id, doc_type, substr(content, 1, 160) AS preview, search_score
# MAGIC FROM vector_search(
# MAGIC   index      => 'silverline.silver.doc_chunks_idx',
# MAGIC   query_text => 'financing agreements for heavy earth-moving machinery',
# MAGIC   num_results => 4);
# MAGIC -- returns: chunk_id · doc_id · doc_type · source_path · content · search_score (nearest-neighbor, ranked)
# MAGIC -- verified live → top hits are Wheel Loader agreements (Doosan/John Deere), scores ~0.64 (vs ~0.55 for
# MAGIC -- boilerplate-clause queries, which near-tie because every contract shares the same clause text).

# COMMAND ----------

# MAGIC %md
# MAGIC Because it's just SQL, you can **join retrieval back to the structured tables** — e.g. pull the customer
# MAGIC row for each retrieved memo (the `doc_id` encodes the id), fusing unstructured hits with gold.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Way 2 — Python SDK with a server-side pre-filter  (intent: **find**, scoped)
# MAGIC For app/agent code: `query_index(...)` with `filters_json` narrows the search space *before* the
# MAGIC nearest-neighbor step — here, only memos. Still a **find** (you want the matching memos), just scoped to
# MAGIC one doc_type so contracts can't crowd the results.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.104.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
res = w.vector_search_indexes.query_index(
    index_name="silverline.silver.doc_chunks_idx",
    columns=["doc_id", "doc_type", "content"],
    filters_json='{"doc_type": "memo"}',            # server-side pre-filter
    query_text="customers near their concentration limits",
    num_results=3,
)
for row in (res.result.data_array or []):
    print(f"{row[-1]:.4f}  {row[0]}  {row[2][:120]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Way 3 — Inline RAG: retrieve, then ground + cite with `ai_query()`  (intent: **answer**)
# MAGIC This is the **answer** intent — a "what happens if…" question where you want a *synthesized answer*, not a
# MAGIC list of contracts. Retrieval **and** generation in one cell: feed the top chunks to a Free-Edition chat
# MAGIC model as hidden **context** and require it to answer *only* from them, citing the `doc_id`. The learner
# MAGIC never sees the raw hits — they see the grounded answer. (Uses `databricks-gpt-oss-120b` — Free Edition
# MAGIC disables the proprietary models; open-weight endpoints work.)

# COMMAND ----------

# MAGIC %sql
# MAGIC WITH hits AS (
# MAGIC   SELECT doc_id, content
# MAGIC   FROM vector_search(
# MAGIC     index => 'silverline.silver.doc_chunks_idx',
# MAGIC     query_text => 'what happens if the obligor fails to make a payment?', num_results => 3)
# MAGIC ),
# MAGIC ctx AS (
# MAGIC   SELECT array_join(collect_list('[' || doc_id || '] ' || content), '\n---\n') AS context FROM hits
# MAGIC )
# MAGIC SELECT ai_query(
# MAGIC   'databricks-gpt-oss-120b',
# MAGIC   'Answer ONLY from the context. Cite the [doc_id] you used. If the context does not say, reply "not found".\n\n'
# MAGIC   || 'Context:\n' || context
# MAGIC   || '\n\nQuestion: what happens if the obligor fails to make a payment?'
# MAGIC ) AS grounded_answer
# MAGIC FROM ctx;
# MAGIC -- verified live → "…triggers an event of default; Silverline Capital may declare the balance due and repossess…" [contract_36.pdf]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Way 4 — The retriever as a Unity Catalog function (a reusable tool)  (intent: **find**)
# MAGIC Wrap retrieval as `silverline.gold.search_docs(query)` so **any** analyst, Genie space, or agent can call
# MAGIC it from plain SQL. This is the **tool a future agentic capstone would hand to an Omnigent agent** — the
# MAGIC unstructured counterpart to the structured Genie tool.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- NOTE: vector_search's num_results must be a CONSTANT (foldable) — a `k` parameter fails with
# MAGIC -- NON_FOLDABLE_ARGUMENT, so we hardcode it. query_text can be a parameter.
# MAGIC CREATE OR REPLACE FUNCTION silverline.gold.search_docs(query STRING)
# MAGIC RETURNS TABLE (doc_id STRING, doc_type STRING, content STRING, search_score DOUBLE)
# MAGIC COMMENT 'Semantic retriever over Silverline contract PDFs + credit memos (Vector Search).'
# MAGIC RETURN
# MAGIC   SELECT doc_id, doc_type, content, search_score
# MAGIC   FROM vector_search(
# MAGIC     index => 'silverline.silver.doc_chunks_idx',
# MAGIC     query_text => query, num_results => 5);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Call the tool like any table function (one arg — num_results is fixed inside the function):
# MAGIC SELECT doc_id, doc_type, content, search_score
# MAGIC FROM silverline.gold.search_docs('agreements financing wheel loaders');
# MAGIC -- verified live → top hits are Wheel Loader agreements (Doosan/Volvo), scores ~0.66–0.67.

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Four ways, one index.** SQL for analysts, SDK for apps, inline RAG for grounded answers, and a **UC
# MAGIC function tool** for agents. Paired with the **Genie** tool from the `ai-bi` stage, an agent would have both
# MAGIC a **structured** and an **unstructured** retriever — the toolbelt a planned agentic capstone would put to work.
