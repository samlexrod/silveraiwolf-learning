<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Mosaic AI Vector Search — the unstructured retriever

Every stage so far worked the **structured** world — the Lakebase OLTP, the medallion, gold, metrics, Genie.
But back in the `seed` stage you also landed a pile of **unstructured** docs in the volume — 85 contract
**PDFs** (`silverline.bronze.files/contracts/`) + credit-memo **markdown** (`.../memos/`) — and nothing has
touched them since. This stage activates them: **parse → chunk → embed → index**, so you can ask questions
like *"what happens if a customer stops paying?"* and get back the **exact contract clause** that answers it —
or *"which customers are near their concentration limits?"* and get the right **credit memo** — semantic
search, not keyword `LIKE`.

This is the **semantic half** of an agent's toolbelt. It pairs with the tool you already built:

| Slot | Tool | Modality | Source |
|---|---|---|---|
| structured NL Q&A | **Genie** ✅ (`ai-bi` stage) | tables / metrics | `silverline.gold.portfolio_metrics` |
| **semantic retrieval** | **Mosaic AI Vector Search** ← this stage | contract docs | `silverline.bronze.files` |

> 📛 **Naming — "Vector Search", not "AI Search".** On Databricks the product is **Mosaic AI Vector Search**
> (a delta-sync vector index). *Azure AI Search* is a **different**, Azure-native service — a graduation-path
> variant if you later run on an enterprise Azure workspace, but **not** what we use here. Everything in this
> stage is Databricks' own, at $0 on Free Edition.

**Cost:** Free — counts against your fair-use quota. The Vector Search endpoint + index are free objects;
building the index and each query use a sliver of serverless compute + the free embedding endpoint. Free
Edition allows **one** Vector Search endpoint, one unit — enough for the whole tutorial.

**Precondition:** `seed` done — `silverline.bronze.files/{contracts,memos}/` holds the docs; the Starter
Warehouse runs. (Claude can confirm live: `databricks -p free fs ls dbfs:/Volumes/silverline/bronze/files/contracts`.)

This is an **interactive walkthrough** — pause after each section.

> 🏗️ **Provisioned in code — not clicked.** The **endpoint**, the **parse → chunk → index** workload, and the
> retrieval patterns all run from the notebooks: `13-vector-search/13.1_build_index` creates the endpoint (via
> the **Python SDK**, with the **CLI equivalent shown beside it**) and builds the table + index; `13.2_retrieval`
> runs the four query patterns. Claude pushes both; the learner runs them on serverless.

---

## Section 1 — Create the Vector Search endpoint (in the notebook; CLI shown too) + the provisioning reality

The endpoint is created **inside `13.1_build_index` (Section 1)** — you run it, so the whole build lives in one
notebook. The cell uses the **Python SDK** (`w.vector_search_endpoints.create_endpoint(...)`, idempotent — it
reuses `silverline-vs` if it already exists). The **CLI does the identical thing** and is shown right beside the
code, so you learn both and can reach for the CLI in a script or CI:

```bash
databricks -p free vector-search-endpoints create-endpoint silverline-vs STANDARD --no-wait
databricks -p free vector-search-endpoints get-endpoint    silverline-vs   # state, num_indexes
```

> ⚠️ **`ONLINE` is misleading on Free Edition — verified live.** The endpoint flips to `state: ONLINE`
> *instantly*, but that does **not** mean it can serve yet. Free Edition provisions the real serving compute
> **lazily, when the first index attaches** — so the **first index sync takes ~10–20 minutes**, walking
> through `pending endpoint provisioning → pending pipeline resources → syncing initial data → ready`. Plan
> for the wait in Section 3; it's a one-time cost, not a hang. (A query fired the instant the index reports
> `ready=True` can still `400 … is not ready` during a brief re-sync window — retry with a short backoff.)

**Pause.** Confirm the `silverline-vs` endpoint exists and reads `ONLINE` / `num_indexes: 0` (render as `AskUserQuestion`).

---

## Section 2 — Parse the docs → a chunked Delta table (`13.1_build_index`)

A delta-sync index reads from a **Delta table**, so first we turn the raw files into rows. The notebook:

1. **Parses the PDFs natively** with `ai_parse_document()` — a Databricks SQL function that extracts a
   document's structure (titles, paragraphs) from the binary. **Verified live on Free Edition** over a real
   `contract_*.pdf`: it returns `document.elements[]` with `content` / `type` (title|text) / `confidence`.
   No `pypdf`, no external library.
   ```sql
   SELECT path, ai_parse_document(content) AS parsed
   FROM READ_FILES('/Volumes/silverline/bronze/files/contracts/*.pdf', format => 'binaryFile')
   ```
2. **Reads the memos** (`.md`) directly with `READ_FILES(..., format => 'text', wholetext => true)`.
3. **Writes** `silverline.silver.doc_chunks` (`chunk_id`, `doc_id`, `doc_type`, `source_path`, `content`)
   with **Change Data Feed on** (`delta.enableChangeDataFeed = true`) — the delta-sync index requires CDF so
   it can incrementally pick up new/changed docs.

> 🧠 **Chunking here is one-chunk-per-doc** — the seeded contracts/memos are one page each, so a whole doc is
> a sensible unit. For long documents you'd split into overlapping passages; the table shape (`chunk_id` PK +
> `content`) stays identical, so the index step below doesn't change.

**Pause.** Confirm `silverline.silver.doc_chunks` has ~95 rows (85 contracts + 10 memos) with CDF enabled (render as `AskUserQuestion`).

---

## Section 3 — Build the delta-sync index (auto-embed via `bge-large-en`) (`13.1` cont.)

Now the index. A **delta-sync** index keeps itself current from the source table and **computes the
embeddings for you** — you point it at a Free-Edition embedding endpoint and it embeds every chunk:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn, VectorIndexType, PipelineType)
w = WorkspaceClient()
w.vector_search_indexes.create_index(
    name="silverline.silver.doc_chunks_idx",
    endpoint_name="silverline-vs",
    primary_key="chunk_id",
    index_type=VectorIndexType.DELTA_SYNC,
    delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
        source_table="silverline.silver.doc_chunks",
        pipeline_type=PipelineType.TRIGGERED,
        embedding_source_columns=[EmbeddingSourceColumn(
            name="content", embedding_model_endpoint_name="databricks-bge-large-en")],
    ),
)
```

> ✅ **Verified live on Free Edition:** endpoint create → CDF source → delta-sync index auto-embedding with
> `databricks-bge-large-en` → query returned sensible, score-ranked hits. `databricks-bge-large-en` (1024-dim)
> is one of the open-weight embedding endpoints Free Edition actually serves.

The notebook then **waits for the first sync** (the ~10–20 min from Section 1's warning), polling
`get_index(...).status.ready` until the chunks are indexed.

> 🔀 **Optional — the other index type, live.** `13.3_direct_access_demo` builds a **Direct Vector Access**
> index (no source table — you compute the embeddings and upsert the raw vectors yourself), queries it by
> vector, then tears down. Run it for a hands-on contrast to the delta-sync index above.

**Pause.** Confirm the index reached `ready=True` with `indexed_row_count` ≈ the chunk count (render as `AskUserQuestion`).

---

## Section 4 — Retrieve four ways (`13.2_retrieval`)

The same index, consumed four ways — the "RAG-consumption ladder" from SQL up to a reusable tool. This is
exactly the kind of tool a future agent capstone would wield.

> 🧭 **Match the query to the intent.** Vector search does two jobs, and the *shape* of the answer differs:
> - **FIND / retrieve** — you want a **list of documents** to open (*"the agreements financing wheel loaders"*).
>   The ranked list **is** the result. → patterns 1, 2, 4.
> - **ANSWER (RAG)** — you're asking *what to do / what does it say* and want a **synthesized answer**, with the
>   docs as hidden context (*"what happens if a customer stops paying?"*). → pattern 3.
>
> Same `vector_search()` underneath — the difference is whether you *read the list* or *feed it to a model*.
> Asking a "what to do" question in a raw-list cell just returns a pile of contracts (the wrong shape), so the
> patterns below use find-queries for 1/2/4 and an answer-query for 3.

1. **SQL `vector_search()`** *(find)* — retrieval right inside a `SELECT`, joinable back to the structured tables:
   ```sql
   SELECT doc_id, doc_type, content, search_score FROM vector_search(
     index => 'silverline.silver.doc_chunks_idx',
     query_text => 'financing agreements for heavy earth-moving machinery', num_results => 4);
   ```
   (The query never says "loader", yet it surfaces the wheel-loader agreements — semantic matching a keyword
   `LIKE` can't do.)
2. **Python SDK `query_index(...)`** *(find, scoped)* — programmatic retrieval with a server-side pre-filter
   (e.g. `filters_json = '{"doc_type": "memo"}'` for *"customers near their concentration limits"*), for use in a data workflow or an app.
3. **Inline RAG loop** *(answer)* — for a "what to do" question, retrieve then **ground + cite** with
   `ai_query()`: feed the top chunks to a Free-Edition chat model as hidden context and ask it to answer *only*
   from them, citing the `doc_id`. The user sees the **answer**, not the raw hits. Retrieval + generation in one SQL cell.
4. **Retriever as a UC function** *(find, reusable)* — wrap the retrieval as `silverline.gold.search_docs(query STRING)`
   so any analyst (or agent, or Genie space) can call it from plain SQL. This is the **tool** a future agentic
   capstone would hand to an Omnigent agent — the unstructured counterpart to the structured Genie tool.

> 🧠 **Genie + retriever = the full toolbelt.** Genie answers *structured* questions ("total billed by
> segment") over the metric view; the retriever answers *unstructured* ones ("which memos flag a customer near
> its concentration limit") over the docs. An agent holding **both** can field a cross-modal request like
> *"which delinquent contracts belong to lower-credit-rated customers?"* — join Genie's who's-delinquent
> (structured) with the retriever's credit-rating language from the memos (unstructured). That combo is where an
> agentic capstone goes next.

> ✅ **All four verified live on Free Edition** (95 real chunks): the **find** query *"heavy earth-moving
> machinery"* surfaced Wheel-Loader agreements (score ~0.64, cleanly above the ~0.55 boilerplate-clause
> near-ties); the SDK filter narrowed to memos only; the **answer** query grounded a cited reply
> (*"…constitutes an event of default; Silverline Capital may declare the balance due and repossess…"* [contract_36]);
> and `silverline.gold.search_docs('agreements financing wheel loaders')` returned 5 ranked wheel-loader
> contracts. Gotcha the notebook handles: `vector_search`'s `num_results` must be a **constant**, so the UC
> function hardcodes it (a `k` parameter fails with `NON_FOLDABLE_ARGUMENT`).

**Pause.** Confirm at least the SQL `vector_search()` query returns relevant chunks (render as `AskUserQuestion`).

---

## Section 5 — Why semantic retrieval, and where it goes next

| Keyword search (`LIKE '%litigation%'`) | Vector Search (this stage) |
|---|---|
| matches the exact word, misses paraphrase | matches **meaning** — "legal dispute", "pending suit" all hit |
| no ranking by relevance | **score-ranked** nearest neighbors |
| nothing to hand an agent | a **governed retriever tool** (UC function) an agent calls |

You've now given the platform its **unstructured retriever**. Structured (Genie) + unstructured (Vector
Search) is the pair an agent needs to reason across *all* of Silverline's data. A **planned agentic-reporting
capstone** — a future direction, not part of this release — would put an Omnigent agent in the driver's seat
with both tools in hand.

**Pause.** Confirm you can explain when semantic retrieval beats keyword search, and how the retriever becomes an agent tool (render as `AskUserQuestion`).

---

## Recap

- ✓ A **Mosaic AI Vector Search endpoint** on Free Edition (one, $0) — with the honest `ONLINE`-is-lazy
  provisioning reality
- ✓ **Parsed** the seeded contract PDFs (native `ai_parse_document`) + memos into `silverline.silver.doc_chunks` (CDF on)
- ✓ A **delta-sync index** auto-embedding via `databricks-bge-large-en`, kept current from the source table
- ✓ Retrieval **four ways** — SQL `vector_search()`, SDK, inline RAG (`ai_query` ground+cite), and a
  reusable **UC-function retriever tool**
- ✓ The unstructured retriever that pairs with Genie to complete the agent's toolbelt

**Cost now:** quota only. Where this goes next: a planned agentic capstone that wields Genie + this retriever
in an agent's hands (future work, not part of this release).
