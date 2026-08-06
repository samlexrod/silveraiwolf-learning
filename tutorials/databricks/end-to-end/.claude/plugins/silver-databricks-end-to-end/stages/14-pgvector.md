<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# pgvector in Lakebase — the retriever that lives *inside* your database

Stage 13 built a **managed, lakehouse-native** retriever (Mosaic AI Vector Search). This stage shows the
**lighter-weight alternative** — **pgvector** inside the `silverline-oltp` Lakebase Postgres you already run.
It's the **cheaper option for small-to-medium corpora**: when the document set doesn't justify a dedicated
vector-search service, keep the embeddings in the same Postgres as your transactional rows. Same contract
corpus, no separate store to operate.

| Retriever | Best for | Where it lives |
|---|---|---|
| **Mosaic AI Vector Search** ✅ (`vector-search` stage) | large corpora · governed lakehouse RAG · scale | the **lakehouse** (Unity Catalog) |
| **pgvector** ← this stage | **small-to-medium** data · cheaper · retrieval next to app data | inside the **operational Postgres** (Lakebase OLTP) |

Because the embeddings sit **right next to the transactional rows** (`contracts`, `customers`, …), one query
does what the managed service can't in a single shot: **semantic retrieval *and* a transactional filter**
(*"the **delinquent** contracts that are about earth-moving equipment"*) — vector search and structured filter
in **one engine, against live rows**. The win is at **query time**; the trade (Section 2) is that **you** own
the embed + keeping the vectors fresh (a Delta→Lakebase refresh). And know the ceiling: at **large scale or
governed lakehouse RAG, the managed Vector Search wins** — pgvector is for the small-to-medium case.

> 🧠 **pgvector** is a Postgres extension that adds a `vector` column type and nearest-neighbor operators
> (`<=>` cosine, `<->` L2). Verified live on Free Edition Lakebase: **pgvector 0.8.0**, `vector(1024)` columns,
> and **HNSW** approximate-nearest-neighbor indexes all work at $0.

**Cost:** Free — counts against your fair-use quota. pgvector runs inside the Lakebase you already provisioned;
embedding the docs uses the free `bge-large-en` endpoint. Nothing here spends money.

**Preconditions:**
- `provision` + `seed` done — `silverline-oltp` (PG17) with the seeded `contracts` table (85 rows, incl. a
  `status` column: active / paid_off / delinquent / charged_off).
- `vector-search` done — we **read the parsed contract text** from `silverline.silver.doc_chunks`. (Only read;
  the embeddings + storage are all pgvector. If it's missing, run `13.1_build_index` Section 2 first.)

This is an **interactive walkthrough** — pause after each section.

> 🏗️ **All in one notebook.** The whole workload — connect → enable pgvector → embed → store → index → query —
> runs as `14-pgvector/14.1_pgvector`, which connects to Lakebase with `psycopg` (SDK-minted credential, no
> token to paste). Claude pushes it; the learner runs it on serverless.

---

## Section 1 — Connect to Lakebase and enable pgvector

The notebook mints a short-lived credential via the SDK, connects over SSL to the OLTP Postgres, and turns on
the extension — the make-or-break step:

```python
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

> ✅ **Verified live on Free Edition:** `CREATE EXTENSION vector` succeeds → **pgvector 0.8.0**. This was the
> open question the roadmap flagged; it works.
>
> 🕒 **Idle branch may read `ARCHIVED`.** Lakebase auto-archives an idle branch to save quota and **transparently
> resumes it on connect** — a returning learner may see `ARCHIVED` in `list-branches` yet still connect fine.

**Pause.** Confirm the notebook printed `connected … · pgvector 0.8.0` (render as `AskUserQuestion`).

---

## Section 2 — Embed the docs yourself, store them next to the OLTP data

Unlike delta-sync, **you** call the embedding model. The notebook reads the parsed contract text from
`doc_chunks`, embeds each doc with `databricks-bge-large-en` (1024-dim), and `INSERT`s the vectors into a
`vector(1024)` column **keyed by `contract_id`**:

```sql
CREATE TABLE doc_embeddings (
  contract_id int PRIMARY KEY, doc_id text, content text, embedding vector(1024));
```

The vector is passed as a `'[f1,f2,…]'` string literal cast `::vector` (no extra adapter needed). Keying on
`contract_id` is deliberate — it lines every embedding up with a real `contracts` row, which is what makes
Section 5's join possible.

> 🧠 **This is the trade vs Stage 13.** Delta-sync embedded + kept the index current *for* you; here you own the
> embed and the refresh. In exchange you get a vector store that joins to live transactional data.

**Pause.** Confirm `doc_embeddings` holds ~85 rows (render as `AskUserQuestion`).

---

## Section 3 — Index for fast nearest-neighbor search (HNSW)

A vector query without an index scans every row (fine for 85 docs, not for millions). **HNSW** is pgvector's
approximate-nearest-neighbor index; `vector_cosine_ops` matches the `<=>` cosine operator we query with:

```sql
CREATE INDEX ON doc_embeddings USING hnsw (embedding vector_cosine_ops);
```

> ✅ **Verified live on Free Edition:** the HNSW index builds successfully.

**Pause.** Confirm the HNSW index was created (render as `AskUserQuestion`).

---

## Section 4 — Retrieve by meaning (cosine `<=>`)

Embed the question the same way, then order by cosine distance — `1 - (embedding <=> q)` is the cosine
**similarity** (higher = closer). This is the pgvector equivalent of Stage 13's `vector_search()`:

```sql
SELECT contract_id, 1 - (embedding <=> :q) AS cosine_sim
FROM doc_embeddings ORDER BY embedding <=> :q LIMIT 5;
```

> ✅ **Verified live:** *"financing for heavy earth-moving machinery"* → wheel-loader / excavator contracts top
> (~0.70), forklifts lower — semantic match, no keyword overlap.

**Pause.** Confirm the query returns relevant contracts ranked by `cosine_sim` (render as `AskUserQuestion`).

---

## Section 5 — The payoff: semantic retrieval **+ a transactional filter**, in one SQL

Because the embeddings live *inside* the OLTP database, a single query can rank by **meaning** and filter on
**live transactional columns** at the same time:

```sql
SELECT c.contract_id, c.status, 1 - (e.embedding <=> :q) AS cosine_sim
FROM doc_embeddings e JOIN contracts c USING (contract_id)
WHERE c.status IN ('delinquent', 'charged_off')      -- transactional filter
ORDER BY e.embedding <=> :q                           -- semantic rank
LIMIT 5;
```

> ✅ **Verified live** — *"earth-moving machinery"* scoped to troubled contracts returned **only** delinquent /
> charged-off ones (`54·49·36·42·80`), where the unfiltered query returned a mix of statuses (`48 active · 54
> delinquent · 35 active · …`). Same semantic rank; the join narrows it to the contracts that actually matter.

**This is what a co-located vector store buys you.** Mosaic AI Vector Search can't do this in one query — the
structured `status` lives in a different system, so you'd retrieve, then filter in a second step. Here it's one
`SELECT`, right beside the data.

**Pause.** Confirm the scoped query returns only `delinquent`/`charged_off` contracts, and contrast it with the
unfiltered result (render as `AskUserQuestion`).

---

## Section 6 — Which retriever, when?

| | Keyword `LIKE` | Mosaic AI VS (Stage 13) | **pgvector** (this stage) |
|---|---|---|---|
| Matches | exact words | **meaning**, lakehouse-governed | **meaning**, in Postgres |
| Embeddings | — | managed (delta-sync) | **you** embed + upsert |
| Killer move | — | joins to gold/Genie; huge corpora | **retrieval + live OLTP filter in one SQL** |
| Reach for it when | — | **large** corpora · governed RAG · scale | **small-to-medium** · cheaper (no separate service) · next to app data |

pgvector isn't a bigger hammer — it's the **lighter, cheaper one** for the small-to-medium case, where standing
up a managed vector service is overkill and you'd rather keep vectors in the Postgres you already run. Pick by
scale: managed Vector Search when you need governance + scale, pgvector when the corpus is modest and
co-location with the OLTP data pays off. (An agent could hold either as its retriever tool.)

**Pause.** Confirm you can explain when pgvector-in-Lakebase beats a managed lakehouse index (the co-located
OLTP join), and vice-versa (render as `AskUserQuestion`).

---

## Recap

- ✓ Enabled **pgvector 0.8.0** in the `silverline-oltp` Lakebase (`CREATE EXTENSION vector`)
- ✓ **Embedded the contract docs yourself** (`bge-large-en`) into a `vector(1024)` column keyed by `contract_id`
- ✓ Built an **HNSW** cosine index for approximate nearest-neighbor search
- ✓ Retrieved by meaning with `<=>`, then — the payoff — **semantic retrieval + a transactional filter in one
  SQL** by joining to the live `contracts` table
- ✓ A **cheaper, small-to-medium** retriever that lives *inside* the operational database — the co-located
  alternative to Stage 13's managed lakehouse Vector Search (pick by scale)

**Cost now:** quota only — the `doc_embeddings` table is dropped with the Lakebase project at cleanup.
