# CLAUDE.md — databricks/end-to-end

Shared guidance for the **Databricks end-to-end** tutorial — a single Databricks **Free Edition**
workload tutorial walked as ordered stages, grouped into phases (`setup` · `lakebase` · `lakehouse` ·
`analytics`, with `ml` · `agents` planned). This file is **inherited by everything** under
`tutorials/databricks/end-to-end/` (CLAUDE.md loads up the directory tree). It layers on top of the
repo-level `CLAUDE.md` and the shared `docs/AUTHORING.md` conventions (the explain-then-start gate,
AskUserQuestion/Task-tool usage, presentation rules). Where they conflict, **this file wins** inside
`tutorials/databricks/end-to-end/`.

## Purpose

Teach the data + AI **workloads** you can run on **Databricks Free Edition** — **$0, serverless-only, no
cloud account or infrastructure**. It's the no-cloud, Free Edition counterpart to a full cloud-infra
deployment (Azure/Terraform) — Free Edition has no infrastructure layer to provision. **One tutorial, installed once,
walked as 12 ordered stages** (setup → lakebase → lakehouse → analytics) — Free Edition is a
platform/sandbox and the stages build on each other, so it's a single continuous path, not separate
tracks.

**The full plan, the verified Free Edition capability facts, the phase catalog + status, the
RAG-consumption ladder, and the reuse map all live in the author roadmap**
(`tutorials/databricks/end-to-end/ROADMAP.md` — outside the plugin, not shipped to learners). Read it
first — it's the source of truth for authoring.

## Free Edition reality (the constraints that shape every stage)

- **Serverless only.** One SQL warehouse (2X-Small), one active SDP pipeline per type, ≤5 concurrent job
  tasks, one Vector Search endpoint, limited model serving. No clusters/GPUs.
- **No cloud infra.** No Terraform-against-account, no VNet/private endpoints, no external storage (managed
  UC volumes only), no NCC. Nothing to provision in a cloud subscription.
- **No account console / SCIM.** Auth is email-OTP / Google / Microsoft; **you own the metastore + catalog**.
  ~~No service principals~~ — **CORRECTION (verified live 2026-06-16): Free Edition DOES support service
  principals** (`databricks service-principals create` + `service-principal-secrets-proxy` for M2M OAuth).
  This matters for the `data-api` stage, where the SP is the required non-owner API identity. Don't repeat
  the old "no SP" claim.
- **Lakebase works** (serverless Postgres 17 + Data API) despite the docs listing it "unsupported" —
  verified live. It's the operational source for the lakebase/lakehouse phases.
- **Cost = fair-use quota, not dollars.** Exceeding quota pauses compute for the day (data persists). The
  "cost" framing is always **quota**, never $/DBU.
- **Agent Bricks (Knowledge Assistant / Supervisor) is NOT available** — build agents yourself with the SDK.

## Build/verify model (different from databricks-infra)

In `databricks-infra` Claude live-ran stages via az-cli + a service principal. **Here there's no SP**, but
the learner authenticates the **Databricks CLI on their own machine** (the `free` profile) — and Claude
runs in that same environment. So Claude **can and should run the CLI itself**:

- **Claude authors** skills, scripts, notebooks, dbt models, bundle resources.
- **Claude runs the CLI/local commands** (via Bash) using the learner's `free` profile — version checks,
  `current-user me`, `warehouses list`, dbt, bundle deploys, SQL via the warehouse — and reports results.
  Don't ask the learner to run a command and paste output back when you can run it.
- **The learner runs only the irreducibly-human bits:** Free Edition browser signup, OAuth approval,
  web-UI-only actions (e.g. AI/BI dashboard authoring, Genie), and anything they prefer to do themselves.
- A stage is "done" only after the live check passes (no-faith rule) — **Claude running it counts**;
  surface the actual output. **Verify the Free Edition mechanic in-workspace before committing an
  approach** — docs lag (Lakebase is the proof).

**Teach with workspace notebooks (the standard).** The learner learns Databricks *by doing in the UI*, so
each stage's real workload ships as a **notebook the learner runs in their workspace**, not as headless
commands. Claude **authors** the notebook under the plugin's `notebooks/NN-<stage>/` and **pushes** it via
`databricks workspace import … --format SOURCE --overwrite` into `/Workspace/Users/<user>/SilverAIWolf/NN-<stage>/`;
the **learner opens and runs it** (Starter Warehouse for SQL) and explores Catalog Explorer / lineage.
Notebooks must be **idempotent**. Pure-plumbing/local-tooling stages (`connect`, `project`/dbt) need no
notebook. Shared catalog name is **`silverline`** (`bronze`/`silver`/`gold` + volume `silverline.bronze.files`).

**Provision infra via CLI/code, never the UI.** Lakebase instances, catalogs, schemas, volumes, pipelines,
jobs — always created **for the learner** via the `databricks` CLI (or bundles/IaC), because production is
automation, not click-ops. The UI is for awareness only; don't default to it for provisioning. Complement
to the notebooks rule: **infra = CLI/code; data workloads = notebooks the learner runs.** (Verified: the
`databricks database …` subcommands create/inspect Lakebase and mint credentials — Postgres **16** by CLI
default, no version flag.)

## Plugin structure (single-entry orchestrator)

The tutorial is **one Claude Code plugin**, `silver-databricks-end-to-end`, under
`tutorials/databricks/end-to-end/.claude/plugins/silver-databricks-end-to-end/` (in the tutorial's
`.claude/.claude-plugin/marketplace.json`). It exposes **exactly one command** — no
per-stage skills (they cluttered the menu):

- `.claude-plugin/plugin.json` — the manifest.
- `commands/start.md` — the **only** command, `/silver-databricks-end-to-end:start`. It's the **orchestrator**:
  resolves paths, loads/creates `PROGRESS.md`, shows where the learner is, and walks one stage at a time,
  advancing only on confirmation.
- `stages/NN-<name>.md` — the 12 stage docs (plain markdown, **not** invokable skills), read on demand by
  the orchestrator. Setup `01-connect · 02-landing-zone · 03-project`; Lakebase `04-provision · 05-seed ·
  06-data-api`; Lakehouse `07-ingest · 08-medallion · 09-refresh`; Analytics `10-business-layer ·
  11-semantic · 12-ai-bi`.

That's the **entire shipped tutorial** — `plugin.json` + `commands/start.md` + `stages/`. Nothing else in
the plugin dir.

> 🛠️ **`ROADMAP.md` is an author/build doc, NOT shipped.** It lives at the **tutorial root**
> (`tutorials/databricks/end-to-end/ROADMAP.md`), **outside** the plugin, so it is never installed and the
> learner never sees it. It's the catalog/build-tracker *you* use to author the tutorial (Free Edition
> facts, build status, reuse map, RAG ladder). The orchestrator does **not** reference it.

**State / resume:** the orchestrator persists progress to a human-readable `PROGRESS.md` in the learner's
tutorial dir (`tutorials/databricks/end-to-end/PROGRESS.md`, gitignored) — a stage table (✅/▶️/☐) plus a
Notes section for captured values. A fresh chat re-reads it and picks up at the current stage. Dependency:
Setup → Lakebase → Lakehouse → Analytics (→ `ml` | `agents` when built).

> Adding a stage = new `stages/NN-<name>.md` + a row in the `PROGRESS.md` template inside
> `commands/start.md` + a row in `ROADMAP.md` (the author doc). Adding a future phase (`ml`, `agents`) =
> more stage docs in the same plugin — still no new skills/commands.

## Stage-doc authoring conventions

Follow the repo-level `docs/AUTHORING.md` conventions, with these deltas
(stage docs are plain markdown under `stages/`, **not** SKILL.md files — no YAML frontmatter needed):

1. Start each stage doc with the **explain-then-start gate** (`<!-- gate:explain-then-start -->` block —
   copy it verbatim from another stage), then `# <Stage title>`.
2. **Open with cost as a quota statement** — "Free — counts against your fair-use quota," never a $/hr burn.
3. `## Section N — <title>` interactive steps; end each with `**Pause.**` + an `AskUserQuestion`.
4. End with a `## Recap`. **Do not** add per-stage Next/Progress chaining — the orchestrator
   (`commands/start.md`) owns progression, the `Next:`/continue prompts, and the persistent `PROGRESS.md`.
5. Reference sibling stages by bare name (e.g. "the `seed` stage"), not as `/`-commands (they aren't
   invokable).
6. **No SP / Terraform / Key-Vault** flows — Databricks CLI + bundles with **user OAuth**, `mise` for tasks.
   Secrets (if any) via Databricks secret scopes, never a committed `.env`.
7. **Reuse, don't reinvent** — copy/adapt the portable assets noted in `ROADMAP.md`'s reuse map; keep
   names aligned so lessons transfer.

## When in doubt
- Read `ROADMAP.md` (tutorial root, author doc) — the plan + verified Free Edition facts + build ledger.
- Don't assume a feature exists on Free Edition; have the learner confirm in-workspace.
- Don't introduce cloud-infra / Terraform / SP patterns — they don't apply here.
- Keep cost framing as **quota**, never dollars.
