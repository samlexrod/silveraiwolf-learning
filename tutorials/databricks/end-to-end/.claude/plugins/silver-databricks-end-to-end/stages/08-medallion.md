<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Medallion — build it three ways, prove they're identical

Build `silver` + `gold` from `bronze`, then see the **same transform** three ways — and proven to produce
**identical gold**. The lesson: the *transform* is the data engineering; the *tool/orchestration* is an
operational choice (cost / portability / control), not correctness.

The Silverline medallion:
- **silver** (current-state, typed, conformed): `silver_customers`, `silver_contracts`, `silver_invoices`.
- **gold**: `gold_segment_portfolio` (financing by segment) + `gold_contract_aging` (AR aging).

Pattern: each orchestrated build is a `build_*` notebook that **builds + runs its orchestrator pointing at a
`*_project/` source folder**.

The **notebook build is split DDL → ELT** (08.1 defines the tables, 08.4's Job loads them); dbt and SDP
each manage their own tables.

| # | Notebook | What it is | Source | Tables |
|---|----------|-----------|--------|--------|
| 1 | `08.1_build_ddl` | **DDL** — `CREATE TABLE IF NOT EXISTS` the empty `_nb` tables (structure only) | (inline SQL) | `*_nb` (empty) |
| 2 | `08.2_build_dbt` | builds + runs **dbt Job** (`silverline-dbt-job`, dbt task) | `dbt_project/` | canonical `gold_*` |
| 3 | `08.3_build_sdp` | creates + runs **SDP pipeline** (`silverline-medallion-sdp`) | `sdp_project/` | `*_sdp` |
| 4 | `08.4_build_notebook` | builds + runs **notebook Job** (`silverline-notebook-job`, silver→gold DAG) — **ELT** `INSERT OVERWRITE` into 08.1's tables | `notebook_project/` | `*_nb` (loaded) |
| 5 | `08.5_parity` | proves notebook == dbt == SDP | — | — |

**Cost:** Quota only — warehouse queries + two serverless Jobs + the one serverless pipeline; all idle to ~0.

**Precondition:** `ingest` done — `silverline.bronze.{customers,contracts,invoices}` exist.

---

## Section 1 — DDL: define the `_nb` tables (empty)

Run **`08.1_build_ddl`** (SQL warehouse). Pure **DDL** — `CREATE TABLE IF NOT EXISTS` for the silver + gold
`_nb` tables (column definitions only, **no data**). This separates *structure* (DDL, here) from *load*
(ELT, Section 4) — the load `INSERT OVERWRITE`s these tables without touching their schema.

**Pause.** Confirm the empty `_nb` tables exist (0 rows) (render as `AskUserQuestion`).

---

## Section 2 — Build 2: dbt, run as a Databricks Job (dbt task)

The production way to run dbt on Databricks. The dbt project is staged as **workspace files**
(`dbt_project/`); a Job with a native **`dbt task`** runs `dbt build` on serverless against the Starter
Warehouse (Databricks auto-generates the profile from `warehouse_id`/`catalog`/`schema` — no token in the
project). Run **`08.2_build_dbt`** (serverless) — it triggers `silverline-dbt-job` and waits → canonical `gold_*`.

**Pause.** Confirm the dbt Job ran SUCCESS and `gold_segment_portfolio` is populated (render as `AskUserQuestion`).

---

## Section 3 — Build 3: SDP / Lakeflow (create + run the pipeline)

Run **`08.3_build_sdp`** (serverless). It **creates** the declarative pipeline `silverline-medallion-sdp`
if absent (source = `sdp_project/medallion_sdp`: `@dlt.table` + `@dlt.expect_or_drop`), then **runs** it →
`*_sdp`. (Free Edition allows one active pipeline.)

**Pause.** Confirm the pipeline created/ran and `segment_portfolio_sdp` is populated (render as `AskUserQuestion`).

---

## Section 4 — ELT: load the tables via a notebook Job (Workflows)

The **ELT** that loads the tables `08.1` defined — and the notebook/**Workflows** orchestration. The load
notebooks live in **`notebook_project/`** (`load_silver` → `load_gold`, doing `INSERT OVERWRITE … SELECT`)
and a **Job runs them as a 2-task DAG** (gold depends on silver). Run **`08.4_build_notebook`** (serverless) —
it **builds the Job pointing at `notebook_project/` and runs it** → loads `*_nb`. (Load notebooks have no
trigger inside → no recursion.) Run `08.1` (DDL) first.

**Pause.** Confirm the Job ran (silver→gold SUCCESS) and `*_nb` is now populated (render as `AskUserQuestion`).

---

## Section 5 — Parity + the trade-off

Run **`08.5_parity`** (SQL warehouse): the three golds side by side, then symmetric `EXCEPT` diffs across
**DDL / dbt / SDP** for `segment_portfolio` (6 rows) and `contract_aging` (85). All diffs **0** → identical.

**Same result, different trade-off:**
- **DDL (CTAS)** — most direct, full control; schedule it with a Job (Section 4).
- **dbt (Job/dbt task)** — refs/tests/docs/lineage + cross-engine **portability**; scheduler/lineage otherwise in paid dbt Cloud.
- **SDP / Lakeflow** — *declarative*, managed materialized views + `@dlt.expect` quality; least code to operate.

Native (Jobs + SDP) covers dbt's ground without dbt Cloud cost (~$200–$400/dev/mo); dbt's edge is
portability. Evidence: [LatentView](https://www.latentview.com/blog/dbt-vs-databricks/) ·
[Materialized views](https://docs.databricks.com/aws/en/ldp/dbsql/materialized) ·
[dbt Cloud pricing](https://b-eye.com/blog/dbt-cloud-pricing/)

**Pause.** Confirm all pairwise diffs = 0 and you can name the trade-off (render as `AskUserQuestion`).

---

## Recap

- ✓ Medallion built **three ways** — notebook (`_nb`, **DDL** `08.1` + **ELT** Job `08.4`) · dbt **Job** (canonical) · SDP **pipeline** (`_sdp`)
- ✓ **DDL/ELT split**: `08.1` defines empty `_nb` tables; `notebook_project/` Job `INSERT OVERWRITE`s them
- ✓ **Parity** proven: notebook == dbt == SDP (0-row symmetric diffs)
- ✓ Source folders: `notebook_project/` · `dbt_project/` · `sdp_project/` ; all serverless/warehouse, idle to $0

**Cost now:** quota only.
