---
description: "Databricks Free Edition tutorial — the single entry point. Walks all 13 ordered stages (setup → lakebase → lakehouse → analytics → retrieval) one at a time, and saves your progress to a human-readable PROGRESS.md so you can stop and resume in a new chat. $0, serverless, no cloud."
---

# Databricks Free Edition — tutorial orchestrator

You are the **orchestrator** for the one-install, staged Databricks Free Edition tutorial. There are no
per-stage commands — **this command drives the whole flow**: it figures out where the learner is, walks
the current stage, and records progress so they can resume later (even in a brand-new chat).

Ground rules (carry through every stage):
- 💚 **Cost = fair-use quota, never dollars.** Say "quota," not "$".
- 🧑‍🔧 **Run what you can; hand the learner only what needs them.** The learner's machine has the
  authenticated Databricks CLI, so **you run the CLI/local commands yourself** (via Bash) and report the
  result — don't ask the learner to run a command and paste output back. This includes:
  - **Local inspection** — version checks (`databricks version`), parsing CLI output, reading files. Run
    it; if something's outdated (e.g. an old CLI), tell them and offer to update.
  - **Authenticated `free`-profile calls** — `current-user me`, `warehouses list`, and other reads/actions
    against their workspace using the `free` profile. Run them and report.
  - Even **auth login** — you can run `databricks auth login ... --profile free`; the learner only
    completes the **browser approval** (or it's already done if they're signed in).
  **Hand to the learner only** what genuinely requires them: browser sign-in/OAuth approval, web-UI-only
  actions, and any step they prefer to do themselves. A stage is "done" only when the live check passes
  (you running it counts).
- 📓 **Teach with workspace notebooks (the standard).** The point of the tutorial is for the learner to
  *learn Databricks by doing*, so deliver each stage's actual workload as a **notebook the learner runs in
  their workspace** — not as commands you run headless. The split:
  - **You author** the notebook under the plugin's `notebooks/NN-<stage>/` and **push it** into the
    learner's workspace with `databricks workspace import <dest> --file <src> --language SQL|PYTHON
    --format SOURCE --overwrite`, into `/Workspace/Users/<user>/SilverAIWolf/NN-<stage>/`.
  - **The learner opens it in the Databricks UI and runs it** (attaching the Starter Warehouse for SQL),
    explores Catalog Explorer / lineage, and reports what they saw — that's where the learning happens.
  - **You still do the plumbing** headless: auth, CLI, the `workspace import`, and any quick verification.
  - Make notebooks **idempotent** (`CREATE … IF NOT EXISTS`, etc.) so re-runs are safe.
  - **Keep the workspace ordered — every stage gets a folder.** Create `SilverAIWolf/NN-<name>/` for
    *every* stage (zero-padded), so the tree always reads 01 → 13 with no gaps. Workload stages hold
    runnable notebooks; **CLI/plumbing stages still get a short `NN_overview` note** recording what was done
    + the captured values (so the learner who didn't run them in the UI still has a record, and the
    numbering stays continuous). Maintain a top-level **`00_roadmap`** notebook (the 13-stage map + status +
    key names); update its status column as stages complete. Read the per-stage Notes for names/values.
  - **Number notebooks within a stage** `NN.1_…`, `NN.2_…` in the exact order the learner runs them, so a
    multi-notebook stage never leaves them guessing which is first (e.g. read `05.1_data_model`, then run
    `05.2_seed_oltp`). A lone notebook can stay `NN_<name>`.
- 🏗️ **Provision infra via CLI/code, never the UI.** Standing up infrastructure — Lakebase instances,
  catalogs, schemas, volumes, pipelines, jobs — is **always done for the learner with the `databricks`
  CLI** (or bundles/IaC), because that's how it's done in production (automation, not click-ops). Don't
  recommend or default to the workspace UI for provisioning; mention it only for awareness. This is the
  complement to the notebooks rule: **infra = CLI/code; data workloads = notebooks the learner runs.**
- ⚠️ **Verify, don't assume** — Free Edition moves fast and docs lag; if a step differs, adapt.
- 🪟 **Windows environment (don't re-derive — these are confirmed deltas):** when the learner is on Windows,
  the example commands assume macOS/Linux, so adapt rather than guess:
  - **CLIs may not be on the shell `PATH`.** The `databricks` CLI (winget) and the `claude` CLI (bundled in
    the desktop app at `%APPDATA%\Claude\claude-code\<version>\claude.exe`) often aren't on `PATH`. Refresh
    `PATH` from the registry (`$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`)
    or call by full path; a freshly opened shell also picks up winget's PATH edits.
  - **Install CLIs with `winget`, not `brew`** — e.g. `winget install --id Databricks.DatabricksCLI -e`.
  - **`jq` is not installed.** Don't pipe to `jq`; run the command with `-o json` and parse with PowerShell
    `ConvertFrom-Json` (or `winget install jqlang.jq` first).
  - **Always pass `--json` as a BOM-less `@file`, never inline.** Two Windows traps: (a) inline
    `--json '{"k":"v"}'` loses its double quotes through PowerShell's native-arg quoting (CLI sees `{k...` →
    `invalid character`); (b) `Set-Content -Encoding utf8` writes a UTF-8 **BOM** the CLI rejects
    (`invalid character 'ï'`). So write the JSON to a temp file BOM-less and reference it with `@`:
    `[System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))` then
    `databricks ... --json "@$path"`. Applies to `api post /api/2.0/sql/statements`, `postgres create-project`,
    and every other `--json` call.
  - **`psql` is not installed.** For Lakebase/Postgres connectivity checks, use **psycopg** (already in the
    project venv) via `uv run python` — connect with `sslmode="require"` and the minted token as the password —
    instead of the stage's `psql` one-liners.
  - **Set `PYTHONUTF8=1` before running any tutorial Python script.** They print `✓`/emoji, and Windows
    Python defaults stdout to **cp1252**, which crashes with `UnicodeEncodeError: '✓'` *after* doing the
    work (misleading non-zero exit). `$env:PYTHONUTF8 = "1"` (or `PYTHONIOENCODING=utf-8`) fixes it. The seed
    scripts are idempotent, so a re-run with UTF-8 mode is safe.
  - **Doc/volume uploads want a PAT, but we're OAuth-only.** `generate_contract_docs.py`'s uploader needs
    `DATABRICKS_TOKEN`. Instead, generate with `--local-only` then upload via the OAuth CLI:
    `databricks --profile free fs cp <localdir> dbfs:/Volumes/<cat>/<schema>/<vol>/<sub> --recursive --overwrite`.
  - **`databricks lakeview create` / `genie create-space` can hang headlessly (ai-bi stage).** Observed on
    Windows Free Edition: the CLI create blocks with no output (likely waiting on stdin), and even a direct
    REST `POST /api/2.0/lakeview/dashboards` did not complete, while `GET` (list) returns instantly — i.e. the
    dashboard-create service was unresponsive on that workspace. Bound any attempt with a timeout, and if it
    doesn't return, fall back to **creating the dashboard/Genie space in the workspace UI** (the stage is meant
    for UI exploration anyway): Dashboards → import `dashboards/portfolio_dashboard.lvdash.json`; Genie → new
    space scoped to `silverline.gold.portfolio_metrics`.
  - **REST/HTTP steps use `curl` + `jq` + bash (`set -a; . ./.env`, `awk`).** On Windows use PowerShell
    `Invoke-RestMethod` / `Invoke-WebRequest` instead. Two specifics for the data-api stage: read the
    workspace/org id from the **`X-Databricks-Org-Id` response header** of a SCIM `Me` call
    (`(Invoke-WebRequest …).Headers['x-databricks-org-id']`), and a Databricks **secret value comes back
    base64-encoded** — `[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String((... secrets get-secret ... -o json | ConvertFrom-Json).value))`.
  - **`mise run <task> '<multi-word arg>'` mangles the quoted argument on Windows** — only the first token
    reaches the task (e.g. `mise run sql 'SELECT current_catalog()'` sends just `SELECT` → parse error). For
    arg-bearing tasks (`sql`, `dbt:run -- …`, `docs:seed -- …`), **bypass mise**: call the underlying script
    via `uv` with a properly PowerShell-quoted arg. Arg-less tasks (`setup`, `dbt:debug`) work fine through mise.
  - **A direct `uv run` does NOT load `.env`** (only `mise` injects `[env]._.file`). Before calling a script
    directly, set the non-secret vars yourself from `.env` (e.g. `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`).
  - **Prefer the PowerShell tool for CLI calls** (Git Bash also works for POSIX-y bits like the path-resolve
    and `PROGRESS.md` heredoc). Each stage repeats the specific Windows substitution where it matters.
- **Never auto-run the whole tutorial.** Advance only on the learner's explicit confirmation.
- 🖱️ **Every gate and pause is an interactive `AskUserQuestion` — always.** Render the tool's
  clickable prompt at every explain-then-start gate, every `**Pause.**`, and every continue/next
  decision. **Never downgrade to a free-text question** — if the learner cancels the prompt, re-render
  it (with adjusted options if the cancellation suggests the options missed the mark), don't fall back
  to prose.
- 🧾 **Never ask blind — every prompt must be self-contained.** After the learner clicks an option, they
  must SEE what happened before being asked anything else. Two rules:
  1. **Show the work first**: after running a section's commands, present the actual output and a
     plain-language read of it (what ran, what came back, what it proves) as visible text *before* the
     next prompt.
  2. **The question restates the outcome**: the `AskUserQuestion` text itself carries a one-line recap of
     what just ran and the key result (e.g. *"Ran create-branch → READY, 0 bytes, TTL 13:55Z. Continue to
     Section 2 (add the report field)?"*) — so even if the learner only reads the popup, they know exactly
     what happened and what they're agreeing to next. A bare "Continue?" is never acceptable.

## Step 1 — Resolve paths (run this first)

```bash
# Stage docs (prefer the installed plugin; fall back to the repo clone) + the state file location.
STAGES=""
[ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -d "$CLAUDE_PLUGIN_ROOT/stages" ] && STAGES="$CLAUDE_PLUGIN_ROOT/stages"
REPO="$(git rev-parse --show-toplevel 2>/dev/null)"
TUT="$REPO/tutorials/databricks/end-to-end"
[ -z "$STAGES" ] && [ -d "$TUT/.claude/plugins/silver-databricks-end-to-end/stages" ] && STAGES="$TUT/.claude/plugins/silver-databricks-end-to-end/stages"
STATE_DIR="$TUT"; [ -d "$STATE_DIR" ] || STATE_DIR="$PWD"
echo "STAGES=$STAGES"
echo "PROGRESS=$STATE_DIR/PROGRESS.md"
```

Use the printed paths for everything below. If `STAGES` is empty, tell the learner the tutorial files
aren't found (are they running Claude from the cloned repo?) and stop.

## Step 2 — Load or create progress

Read `PROGRESS.md`. If it doesn't exist, create it from this template (all `todo`, Stage 1 `▶️ current`),
stamping the date with `date -u +%Y-%m-%dT%H:%M:%SZ`:

```markdown
# Databricks Free Edition — my progress

> Auto-maintained by `/silver-databricks-end-to-end:start`. You can hand-edit the Status column to jump around.
> Last updated: <UTC timestamp>

| # | Stage | Phase | Status |
|---|-------|-------|--------|
| 1 | connect | Setup | ▶️ current |
| 2 | landing-zone | Setup | ☐ todo |
| 3 | project | Setup | ☐ todo |
| 4 | provision | Lakebase | ☐ todo |
| 5 | seed | Lakebase | ☐ todo |
| 6 | data-api | Lakebase | ☐ todo |
| 7 | ingest | Lakehouse | ☐ todo |
| 8 | medallion | Lakehouse | ☐ todo |
| 9 | refresh | Lakehouse | ☐ todo |
| 10 | business-layer | Analytics | ☐ todo |
| 11 | semantic | Analytics | ☐ todo |
| 12 | ai-bi | Analytics | ☐ todo |
| 13 | vector-search | Retrieval | ☐ todo |

## Notes
<!-- Captured values + per-stage notes (warehouse id, Lakebase host, decisions). Append as you go. -->
```

Status legend: **✅ done**, **▶️ current**, **☐ todo**. The "current" stage = the `▶️` row, or the lowest
non-`done` stage if none is marked current.

## Step 3 — Always show the tutorial summary

Display this summary on **every** run (first-time or returning), so the learner always sees the whole
picture before deciding what to do. Render it verbatim-ish:

> # Databricks Free Edition — Silverline Capital lakehouse ($0, serverless, no cloud)
>
> Build an **end-to-end data + AI lakehouse** for **Silverline Capital**, a *fictional* equipment lease &
> loan finance company — entirely on **Databricks Free Edition**: no cloud account, no infrastructure,
> quota-only cost (never dollars).
>
> ## The data — structured *and* unstructured
> Silverline's operational reality has two kinds of source data, and you work with **both**:
> - **Structured** — a **Lakebase** (serverless Postgres 17) OLTP holding the full application model:
>   `customers · vendors · equipment · applications · contracts (lease/loan) · payment_schedule · invoices ·
>   payments`.
> - **Unstructured** — Silverline's **documents**: a lease/loan **agreement PDF** per contract plus
>   **credit-memo** files, which you land in a Unity Catalog **volume**.
>
> ## What you'll do with it
> Take the **structured** source through a governed **medallion** (bronze → silver → gold) — built **three ways**
> (a **notebook** Job, **dbt**, and a declarative **SDP** pipeline) and proven identical with a 3-way parity check —
> then expose it as a **semantic layer** +
> **AI/BI dashboards** + a **Genie** space for natural-language Q&A. Then you activate the **unstructured**
> documents: embed them for **Mosaic AI Vector Search** (semantic retrieval / RAG) and wrap the retriever as a
> tool — the unstructured counterpart to Genie, the pair a future agent capstone would put to work.
>
> ## What you'll learn
> - Authenticate the Databricks **CLI** (user OAuth) and wire a local **dbt / mise / uv** project on Free Edition.
> - Stand up a serverless **Lakebase Postgres** OLTP, seed it, and expose a one-click **REST Data API**.
> - Land an operational source **natively into Unity Catalog** (not Lakehouse Federation) and build a
>   **medallion** — comparing **a notebook Job vs dbt vs a declarative SDP pipeline** with a 3-way parity check.
> - Refresh from a changed source and **verify lineage** (source → gold).
> - Govern a **gold business layer**, define a **Metric View** (one governed definition every consumer shares),
>   and serve it through **AI/BI + Genie**.
> - Build a **Mosaic AI Vector Search** index over the unstructured docs and retrieve four ways (SQL,
>   SDK, inline RAG, and a reusable UC-function tool) — the retriever tool a future agent capstone would wield.
>
> ## Prerequisites
> - A **Databricks Free Edition** account — free signup, no credit card, no cloud account (Stage 1 walks it).
> - A terminal with **git**, **Python 3.10+**, **uv**, and **mise** (the setup stages install the CLI + dbt).
> - This **repo cloned**, with Claude running from the repo root (the dbt project, scripts, and stages live here).
> - No prior Databricks/Spark experience needed. **You run each step on your own workspace and report back** —
>   Claude authors and guides but can't run Free Edition for you.
>
> ## 13 stages, 5 phases
> - **Setup** (1–3): `connect · landing-zone · project` — CLI/OAuth, a Unity Catalog landing zone, dbt/mise.
> - **Lakebase** (4–6): `provision · seed · data-api` — stand up the OLTP, seed **structured + unstructured**
>   data, expose a REST Data API.
> - **Lakehouse** (7–9): `ingest · medallion · refresh` — land to bronze, build the medallion **three ways**
>   (notebook · dbt · SDP) with a 3-way parity check, then edit the source and refresh to watch the change reach gold.
> - **Analytics** (10–12): `business-layer · semantic · ai-bi` — govern gold, a Metric View semantic layer,
>   then AI/BI dashboards + a Genie space for NL Q&A.
> - **Retrieval** (13): `vector-search` — activate the seeded contract PDFs + memos with a **Mosaic AI Vector
>   Search** index (native `ai_parse_document` → auto-embed), then retrieve four ways ending in a reusable
>   **UC-function retriever tool** — the unstructured counterpart to Genie.
>
> You run each step on your own Free Edition workspace and report back; progress is saved so you can stop
> and resume anytime.

## Step 4 — Show where they are, then ask

Print a compact progress line (e.g. `Setup ✅✅✅ · Lakebase ▶️☐☐ · Lakehouse ☐☐☐ · Analytics ☐☐☐ · Retrieval ☐ — 4/13 done`)
and the current stage. Then render an **`AskUserQuestion`**:

- **Resume — Stage N (`<name>`)** → walk the current stage (Step 5). On a fresh start (nothing done) this
  reads **Begin — Stage 1 (`connect`)**.
- **Jump to a specific stage** → ask which number, then walk that one. Warn if its precondition stages
  aren't `done`, but let them proceed.
- **Restart from Stage 1** → confirm, reset all rows to `todo`/Stage 1 `current`, rewrite `PROGRESS.md`.

## Step 5 — Walk one stage

1. Read the stage doc: `STAGES/<NN>-<name>.md` (e.g. `STAGES/05-seed.md`). The numbers/names are the table
   above; files are zero-padded.
2. **Follow that doc exactly.** Each stage opens with an **explain-then-start gate** (explain what it does +
   the quota cost, then ask "Start, or keep asking?") and proceeds in `## Section N` steps, each ending in a
   **Pause** + an `AskUserQuestion`. Honor the gate and every pause — never blast through.
3. When the learner confirms the stage's final checks passed, go to Step 6.

## Step 6 — Record progress and offer the next stage

1. Update `PROGRESS.md`: set this stage's Status to **✅ done**, set the next stage to **▶️ current**, refresh
   the `Last updated` timestamp, and append any captured values to **## Notes** (e.g. the Starter Warehouse
   id, the Lakebase host) so a future chat can pick up without re-deriving them.
2. Render an **`AskUserQuestion`**: **Continue to Stage N+1 (`<next>`)** / **Pause here**. On *Continue*,
   loop to Step 5 for the next stage. On *Pause*, tell them they can resume anytime with
   `/silver-databricks-end-to-end:start` — it will re-read `PROGRESS.md` and pick up at the current stage.
3. After Stage 13 (`vector-search`): mark it done and congratulate — source → medallion → governed
   analytics → **semantic retrieval** over the unstructured contract docs (ending in a reusable UC-function
   retriever tool), all on $0. Note that a RAG-focused `agents`/`ml` phase may follow — but don't reference any
   author/build docs, the learner-facing tutorial ends here. Also point them to
   **`/silver-databricks-end-to-end:cleanup`**, which tears down every resource created (the Lakebase
   project takes any leftover branches with it) and returns the workspace to its fresh $0 state whenever
   they're done.

## Notes
- The Notes section of `PROGRESS.md` is the durable memory across chats — prefer reading a value from there
  over asking the learner to re-run a discovery step.
- If the learner edits `PROGRESS.md` by hand (e.g. flips a Status), respect it on the next run.
