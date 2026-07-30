# Databricks Free Edition — roadmap, catalog & build tracker

> 🛠️ **Author/build doc — NOT part of the shipped tutorial.** This lives at the tutorial root (outside the
> `silver-databricks-end-to-end` plugin), so it is **not installed** and the learner never sees it. It's the plan
> *you* (the author) use to build and track the tutorial. The learner-facing flow is only
> `/silver-databricks-end-to-end:start` → the stage docs.

The **source-of-truth plan** for the Free Edition tutorial. `databricks/end-to-end` is **one tutorial**,
installed once and walked as **ordered stages grouped into phases** (setup → lakebase → lakehouse →
analytics → retrieval, with `agentic-reporting` and `ml` planned; more of the RAG `agents` ladder to follow). This file is the catalog (what phases/stages exist, what they
teach, build status), the **shared Free Edition facts**, and the **reuse map**. Read it before authoring any
stage; update it when a stage lands.

> 🟢 **Zero cost, provisions nothing.** Reads/plans only.
> 📍 **Location:** `tutorials/databricks/end-to-end/ROADMAP.md` (author doc, not shipped).

---

## Why this exists (and why one staged tutorial)

A full Databricks-on-Azure **infrastructure** deployment (Terraform, VNet, private endpoints, ADLS, SQL
Server VMs, NCC, Key Vault, SP-driven UC) is an entire layer that **Free Edition removes** — serverless-only,
Databricks-hosted, no cloud subscription. So this tutorial teaches the **workloads** Free Edition *can* run —
data engineering, analytics, ML, and agents — at **$0**, no cloud setup.

**One install, ordered stages:** the phases build on each other (setup is the shared prereq; lakehouse needs
lakebase's source; analytics/ml/agents need the medallion). So it's a single plugin you install once and
walk top-to-bottom, not separate per-workload installs. New work (`ml`, `agents`, later `jobs`/`streaming`)
is added as more stages in the same plugin.

---

## Why the medallion is built three ways (notebook · dbt · SDP)

The `medallion` stage builds the same gold **three ways** — a **notebook** Job (`08.4`), **dbt** (`08.2`), and a
declarative **SDP** pipeline (`08.3`) — and proves **3-way parity** (`08.5`). The notebook + SDP are the two
**native Databricks** paths; comparing them against dbt teaches an **honest trade-off**, not "dbt is bad":

- **Not capability.** Both do SQL *and* PySpark (dbt via Python models). Don't claim dbt "can't" do the
  imperative RAG work — it can; the difference is below.
- **Abstraction vs transparency.** dbt compiles/abstracts the transform; the compiled code, lineage, and
  docs are surfaced through **dbt Cloud**. Native **Jobs running notebooks** keep the **notebook as the
  code** — jump from a job run straight into it. dbt-core has **no scheduler**; Workflows are built in.
- **Cost.** dbt Cloud (the org tier) is **paid** (~$200–$400/dev/mo); Databricks Workflows are included (quota).
- **Already native.** Materialized views (incremental + CRON), data-quality **expectations** (`@dlt.expect`),
  and **Unity Catalog** auto-lineage/docs cover what dbt layers on.
- **dbt's real edge = portability** (Snowflake/BigQuery/…), which a Databricks-committed learner doesn't need.
- **Imperative work leans native:** the `refresh` stage and the future `agents` RAG (parse → embed → create/
  sync the Vector Search index) run as **Jobs+notebooks** — natural fit for imperative API orchestration + direct code.

> 📎 **Evidence** (for the stage's box): redundancy-for-simple-cases —
> https://www.latentview.com/blog/dbt-vs-databricks/ · native materialized views (incremental + CRON) —
> https://docs.databricks.com/aws/en/ldp/dbsql/materialized · UC auto column-level lineage —
> https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage · dbt Cloud pricing —
> https://b-eye.com/blog/dbt-cloud-pricing/ · "hybrid by design" counterpoint —
> https://www.dsstream.com/post/delta-live-tables-dlt-vs-dbt-where-transformation-ends-and-platform-engineering-begins

---

## Free Edition reality (shared across all stages — keep honest)

| Capability | Status | Notes |
| --- | --- | --- |
| Serverless notebooks/jobs | ✅ | limited size; **≤5 concurrent job tasks** |
| SQL warehouse | ✅ | **one, 2X-Small** |
| Lakeflow Declarative Pipelines (SDP) | ✅ | **one active pipeline per type** |
| Vector Search / AI Search | ✅ | **one endpoint, one unit**; no Direct Vector Access; delta-sync OK |
| Foundation Model APIs / model serving | ✅ | no provisioned-throughput/GPU; some models gated; limited endpoint count |
| Unity Catalog (1 metastore), Genie, AI/BI, Apps (≤3) | ✅ | single-user owns the metastore/catalog |
| dbt (on serverless SQL) | ✅ | — |
| **Lakebase (serverless Postgres 17) + Data API** | ✅ | **docs are STALE — it WORKS** (verified live 2026-06-14) |
| Service principals / account console / account APIs | ❌ | single-user; auth = email-OTP / Google / Microsoft (no SP, no SCIM) |
| Custom/external storage locations | ❌ | managed UC volumes only |
| Private networking / clusters / GPUs / online tables / Lakebase-claimed-unsupported | ❌/✅ | no networking/clusters/GPU/online-tables; Lakebase docs wrong (see above) |
| **Agent Bricks: Knowledge Assistant / Supervisor Agent** | ❌ | not on Free Edition — build agents yourself (SDK) |
| Cost model | 💚 | **free + fair-use quota** (exceed → compute paused for the day), NOT $/DBU |

> ⚠️ **Verify in-workspace as you build** — Free Edition + Lakebase move fast, docs lag. Confirm each
> mechanic before committing. **Lakebase↔UC is native** (Lakebase is Databricks' own Postgres — it
> registers in Unity Catalog directly; do NOT use Lakehouse Federation, which is for *external* engines).
> Confirm the exact native-registration path in your workspace.

> 🧑‍🔧 **Build/verify model:** Claude **authors**; the **learner runs + verifies** on their Free Edition
> workspace (no SP creds Claude can use). A stage is "done" only after the learner's live check passes.

---

## Phase + stage catalog (one plugin, 13 stages built across 5 phases; agentic-reporting + ml planned)

The plugin exposes **one command** — `/silver-databricks-end-to-end:start` (`commands/start.md`), the
orchestrator. It walks the stages in order, reading each stage's content from `stages/NN-<name>.md`
(plain docs, not invokable skills) and persisting progress to a human-readable `PROGRESS.md` in the
learner's tutorial dir so they can resume in a new chat. This file (`roadmap.md`) is the
author/reference catalog. Legend: ☐ to build · ◐ in progress · ✅ built.

| Phase | Stages (`stages/NN-<name>.md`) | Teaches | Reuses from `databricks-infra` | Status |
| ----- | ------------------------------------------ | ------- | ------------------------------ | ------ |
| **Setup** (1–3) | `connect` · `landing-zone` · `project` | signup, CLI/OAuth, UC catalog, mise/dbt — the shared prereq every later stage assumes | environment-setup (trimmed) | ◐ authored — awaiting live verify (+ the mise/uv/dbt scaffold) |
| **Lakebase** (4–6) | `provision` · `seed` · `data-api` | serverless **Postgres 17** OLTP source + structured seed **+ unstructured docs** (contract PDFs / credit memos → the UC volume, for the agents phase's Vector Search) + **Data API (REST)** | `generate_mock_data` | ◐ authored — awaiting live verify (lakebase_seed.py + generate_contract_docs.py); verify credential-mint, volume upload, Data-API URL/auth in-workspace |
| **Lakehouse** (7–9) | `ingest` · `medallion` · `refresh` | register Lakebase in UC (native) → **bronze**, **medallion 3 ways (notebook/dbt/SDP) + parity**, then edit-source→re-run→verify (honest batch refresh, NOT CDC — real CDC is the streaming tutorial) | dbt models + SDP/notebook extraction + parity | ◐ authored — awaiting live verify (+ dbt silver/gold + medallion.py SDP + lakebase_simulate.py); verify native Lakebase UC-registration + SDP pipeline create |
| **Analytics** (10–12) | `business-layer` · `semantic` · `ai-bi` | govern gold, **Metric Views** (semantic), **AI/BI + Genie** | expose_business_layer, invoice_metrics, genie_ask | ◐ authored — awaiting live verify (+ sql/invoice_metrics.sql); verify Metric View DDL + Genie create on FE |
| **Retrieval** (13) | `vector-search` | **Mosaic AI Vector Search** over the seeded contract PDFs + credit memos: native `ai_parse_document` parse → chunked CDF Delta table → **delta-sync index auto-embedding via `databricks-bge-large-en`** → retrieve **four ways** (SQL `vector_search()` · SDK+filter · inline RAG `ai_query` · **UC-function retriever tool** `search_docs`) — the unstructured counterpart to Genie | `rag_retrieval.py` (ladder #1–#4) | ✅ built — **verified live end-to-end 2026-07-10** (95 real chunks; see [[fe-vector-search-verified]]). Gotchas baked in: endpoint `ONLINE` is lazy (first sync ~10–20 min); `num_results` must be constant (UC fn hardcodes it); TVF cols `chunk_id·doc_id·doc_type·source_path·content·search_score`. |
| **Agentic reporting** (14, capstone) | `agentic-reporting` | **Lakebase copy-on-write branching** (0-byte, TTL'd), then an **Omnigent** agent that spins an ephemeral branch to prototype a new **gold report field** on prod-like data + tears it down — reasoning on **FE Foundation Model APIs**, governed by policy (cost budget + blast-radius) | new (Omnigent + Lakebase branching) | ◐ **PLANNED / deferred** — **deferred to a future PR; not in the 13-stage shipped release.** Verified in spike (**Gate A+B verified live**, 2026-07-01) — facts retained below to inform the future stage. Manual loop verified verbatim (incl. UI-visibility pause); agent loop proven end-to-end (claude-native, full PASS). **FE model finding:** ALL proprietary models (claude/gemini) disabled on FE (403 rate-limit-0 / 404) despite catalog listing → default = open-weight `databricks-gpt-oss-120b` (selectable). **Blocker:** Omnigent 0.3.0.dev0 GPT-harnesses ignore configured model (default to nonexistent gpt-5-5) + override crashes → FE-model path pending upstream fix; ship with claude-native fallback documented. |
| **ML** (planned) | — | **MLflow** tracking, feature engineering, train → register (UC) → **serve** a model | — (new) | ☐ |
| **Agents** (partly built) | `vector-search` (13) done | Ladder **#1–#4 now built as Stage 13** (index + SQL/SDK/inline-RAG/UC-tool). Still planned: **#5–#8** — Mosaic-AI `ResponsesAgent` → MLflow → UC → serving, agent+Genie multi-tool, `mlflow.evaluate`, review app → handoff to `silver-databricks-agents`. (Lakebase **pgvector** dual-backend + a Databricks **App** are candidate stages to insert into the Retrieval phase before the capstone — pgvector needs an FE `CREATE EXTENSION vector` spike first.) | `rag_retrieval.py` + genie tool | ◐ |

**Dependency:** Setup → Lakebase → Lakehouse → Analytics → **Retrieval** ( → **Agentic reporting** planned |
ML planned). Lakehouse assumes Lakebase (the source); Analytics/ML assume the Lakehouse gold/silver exists.
**Retrieval** (13) only needs the `seed`-stage docs in the volume (`silverline.bronze.files`) + the warehouse.
**Agentic reporting** (planned/deferred, not in the shipped release) branches the Lakebase OLTP, so it needs
`provision`/`seed`; it's slated as the capstone — the agent can wield the Stage-13 retriever (`search_docs`)
alongside Genie.

---

## RAG-consumption ladder ("show every way to use it") — **#1–#4 built in Stage 13 (`vector-search`)**; #5–#10 still planned

| # | Pattern | What | FE? |
| - | ------- | ---- | --- |
| 1 | SQL `vector_search()` | retrieval in a `SELECT` | ✅ |
| 2 | Python SDK `similarity_search(filters=…)` | programmatic + server-side pre-filter | ✅ |
| 3 | Inline RAG loop | retrieve → `ai_query` ground+cite | ✅ |
| 4 | **Retriever as a UC function** | reusable **tool** callable from SQL/agents/Genie | ✅ |
| 5 | **Mosaic AI Agent** | `ResponsesAgent` + retriever tool → MLflow → UC → **serving endpoint** | ✅ |
| 6 | **Agent + Genie (multi-tool)** | one agent: Genie/SQL tool (structured) **+** retriever tool (unstructured) | ✅ (build it) |
| 7 | **Agent Evaluation** | `mlflow.evaluate` + judges (groundedness/relevance/correctness) | ✅ |
| 8 | **Review App** | experts chat + feedback | ✅ |
| 9 | **Databricks App (chat UI)** | hosted front-end calling the retriever/endpoint | ✅ (≤3) |
| 10 | Agent Bricks — Knowledge Assistant | no-code managed RAG agent | ❌ FE (build #5; mention as paid path) |

> 🧠 **"Genie using the RAG":** Genie is text-to-SQL over structured data; combine via the retriever as a
> **UC-function tool in the Genie space**, or the **agent (#6)** holding both a Genie tool + the retriever
> tool. 🤝 #5–#8 are the **`silver-databricks-agents`** plugin's lifecycle — the `agents` phase wires the
> retriever as a UC tool, then hands off to that plugin.

---

## Reuse map (assets adapted from prior SilverAIWolf Databricks infra work)

| Asset | Source | Free Edition adaptation |
| ----- | ------ | ----------------------- |
| dbt medallion/rag models | `dbt/models/**` | drop SP run-as; one serverless SQL warehouse |
| notebook extraction | `dbx/pipelines/rag_extract/contract_rag_notebook.py` | unchanged (serverless notebook job) |
| metric view | `dbx/metric_views/invoice_metrics.sql` | point at FE silver |
| RAG lesson notebook | `dbx/explorations/rag_retrieval.py` | drop SP-grant note (single-user owns it) |
| genie / semantic / business scripts | `scripts/{genie_ask,semantic_check,expose_business_layer}.py` | user-auth, single catalog |
| mock data | `scripts/generate_mock_data.py` | seed into **Lakebase** instead of SQL Server |

---

## Build order + how to use this
1. **Setup** (stages 1–3) first — the shared prereq.
2. Then **Lakebase** (4–6) (you already have a live Lakebase instance to build on), then **Lakehouse**
   (7–9), then **Analytics** (10–12). **ML**/**Agents** come after Lakehouse when built.
3. Per stage: verify the FE mechanic in-workspace → author the `skills/<stage>/SKILL.md` (reuse the map) →
   add it to `commands/start.md` + this catalog → learner live-runs → flip status to ✅ here.

## Recap
- ✓ One staged tutorial (one plugin): 13 stages shipped across 5 phases (Setup · Lakebase · Lakehouse · Analytics · Retrieval); Agentic reporting + ML planned (deferred to a future PR); more of the RAG-agents ladder to follow
- ✓ Captured the shared Free Edition facts (incl. the Lakebase-docs-are-stale finding) + the build/verify model
- ✓ Kept the RAG-consumption ladder for the planned `agents` phase + the agents-plugin handoff
- ✓ Touched no cloud resources

Live-verified so far: **Retrieval** (13, `vector-search`, end-to-end 2026-07-10) — shipped. **Agentic reporting**
(14, Gate A+B) was verified live in a spike but is **NOT shipped in this release — deferred to a future PR**.
Next candidates: promote the deferred **Agentic reporting** capstone, the **pgvector-on-FE** spike (gates a
dual-backend retrieval stage), and the **Omnigent→MLflow** trace bridge (agent observability).

> **Offer to continue (interactive).** Render an `AskUserQuestion` — **"Begin Stage 1 now, or keep exploring the roadmap?"** — choosing **Begin Stage 1** invokes `connect`; **Keep exploring** stays here and runs nothing. Only chain forward on **Begin Stage 1**.
