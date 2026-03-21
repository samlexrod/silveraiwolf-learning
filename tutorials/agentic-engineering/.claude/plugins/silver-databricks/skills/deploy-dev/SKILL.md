---
description: "[Stage 2] Create the Unity Catalog landing zone and upload seed data"
---

# Prepare the Landing Zone

Set up the Unity Catalog schema and volume, upload seed data, and explain what Bronze will do — so the next stage has everything it needs to run.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 1 (scaffold-setup), the learner has:
- A working local project with passing tests and clean lint
- OAuth authentication configured via `databricks auth login`
- Seed CSVs in `data/seed/`

This stage prepares the **landing zone** on Databricks — the place where raw files live before the pipeline picks them up. No pipeline is deployed yet; that happens in Stage 3 when we build Bronze.

---

## Instructions

---

### Step 1 — Verify Prerequisites

Before setting up the landing zone, confirm the project is in good shape:

```bash
cd <target-directory>
ls data/seed/counterparties.csv data/seed/transactions.csv data/seed/market_data.csv
```

If seed data hasn't been generated, tell the user to run `/silver-databricks:scaffold-setup` first.

Also verify the Databricks connection (OAuth):

```bash
databricks auth describe
databricks workspace list /
```

If auth fails, tell the user to re-authenticate:

```bash
databricks auth login --host <WORKSPACE_URL>
```

If the connection fails, troubleshoot before proceeding.

---

### Step 2 — Create Unity Catalog Schema & Volume

Tell the user what's happening:

> In a real data platform, raw files land in a **landing zone** before any pipeline touches them. On Databricks, that landing zone is a **Unity Catalog Volume** — a managed directory inside your catalog that can hold arbitrary files (CSVs, JSON, Parquet, etc.).
>
> I'll create two things:
> 1. **Schema** `main.financial_risk` — the namespace for all our tables and volumes
> 2. **Volume** `main.financial_risk.raw` — the raw file landing zone
>
> ```
> Unity Catalog
> └── main (catalog)
>     └── financial_risk (schema)        ← I'll create this
>         ├── raw (volume)               ← and this
>         │   ├── counterparties/
>         │   ├── transactions/
>         │   └── market_data/
>         ├── bronze_* (tables)          ← Stage 3 creates these
>         ├── silver_* (tables)          ← Stage 4
>         └── gold_* (tables)            ← Stage 5
> ```

Run:

```bash
databricks schemas create --json '{"catalog_name": "main", "name": "financial_risk", "comment": "Financial risk pipeline data"}' 2>/dev/null || echo "(schema may already exist)"
databricks volumes create --json '{"catalog_name": "main", "schema_name": "financial_risk", "name": "raw", "volume_type": "MANAGED", "comment": "Raw data landing zone for CSV uploads"}' 2>/dev/null || echo "(volume may already exist)"
```

If the commands fail with permission errors on Free Edition, try creating them via SQL instead:

```bash
databricks sql execute --statement "CREATE SCHEMA IF NOT EXISTS main.financial_risk COMMENT 'Financial risk pipeline data'"
databricks sql execute --statement "CREATE VOLUME IF NOT EXISTS main.financial_risk.raw COMMENT 'Raw data landing zone for CSV uploads'"
```

After success:

> ✓ Unity Catalog schema `main.financial_risk` and volume `raw` are ready.

---

### Step 3 — Upload Seed Data

Tell the user:

> Now I'll upload the seed CSVs to the volume. In production, these files would arrive from upstream systems — an API, a database export, or a streaming feed. For this tutorial, we're simulating that with synthetic data.
>
> Each entity gets its own subdirectory — this is a common pattern because Auto Loader (which we'll use in Bronze) watches a directory for new files.

First create the subdirectories (volumes don't auto-create parent dirs):

```bash
databricks fs mkdir dbfs:/Volumes/main/financial_risk/raw/counterparties
databricks fs mkdir dbfs:/Volumes/main/financial_risk/raw/transactions
databricks fs mkdir dbfs:/Volumes/main/financial_risk/raw/market_data
```

Then upload the CSVs:

```bash
databricks fs cp data/seed/counterparties.csv dbfs:/Volumes/main/financial_risk/raw/counterparties/counterparties.csv --overwrite
databricks fs cp data/seed/transactions.csv dbfs:/Volumes/main/financial_risk/raw/transactions/transactions.csv --overwrite
databricks fs cp data/seed/market_data.csv dbfs:/Volumes/main/financial_risk/raw/market_data/market_data.csv --overwrite
```

Verify the upload:

```bash
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/counterparties/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/transactions/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/market_data/
```

Each directory should show one CSV file. After success:

> ✓ Seed data uploaded — 3 CSVs in the raw volume.

---

### Step 4 — Verify in Workspace

Run a quick validation:

```bash
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/
```

Tell the user:

> The landing zone is ready. Here's what's now on your Databricks workspace:
>
> - **Schema**: `main.financial_risk` — your pipeline namespace
> - **Volume**: `/Volumes/main/financial_risk/raw/` with 3 subdirectories of seed CSVs
> - **Pipeline**: Not deployed yet — that's Stage 3
>
> You can verify by opening your workspace in the browser:
>
> **→  https://accounts.cloud.databricks.com/login  ←**
>
> Navigate to **Catalog → main → financial_risk → raw** to see the uploaded files.

---

### Step 5 — What's Coming Next: The Bronze Layer

Tell the user:

> Before we move to Stage 3, let's understand what we're about to build.
>
> **Bronze = Staging Area.** The first layer of the medallion architecture ingests raw data exactly as it arrives — no transformations, no cleaning, no business logic. It's an append-only landing zone that preserves the original data for auditability and reprocessing.
>
> ```
>   What we just did (Stage 2)              What Stage 3 will do
>  ┌─────────────────────────┐            ┌─────────────────────────┐
>  │  Raw Volume (files)     │            │  Bronze Tables (Delta)  │
>  │                         │            │                         │
>  │  counterparties/        │  ────────> │  bronze_counterparties  │
>  │    └─ counterparties.csv│   ingest   │    └─ 20 rows           │
>  │  transactions/          │  ────────> │  bronze_transactions    │
>  │    └─ transactions.csv  │   ingest   │    └─ ~960 rows         │
>  │  market_data/           │  ────────> │  bronze_market_data     │
>  │    └─ market_data.csv   │   ingest   │    └─ ~3,200 rows       │
>  └─────────────────────────┘            └─────────────────────────┘
>        CSV files on disk                   Delta tables in catalog
> ```
>
> Stage 3 will teach you two ingestion patterns:
>
> | Table | Method | Why |
> |---|---|---|
> | `bronze_counterparties` | **Batch** (`spark.read`) | Small, rarely changing reference data — read all at once |
> | `bronze_transactions` | **Auto Loader** (`cloudFiles`) | High-volume feed — incrementally process new files only |
> | `bronze_market_data` | **Auto Loader** (`cloudFiles`) | Daily prices — new files arrive over time |
>
> **Auto Loader** tracks which files have been processed using a checkpoint. In production, when new CSVs land in the volume, only the new ones get ingested — it never re-reads old data. This is what makes it production-ready for continuous data feeds.

---

### Step 6 — Summary

Display a summary:

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 2 — Landing Zone Ready!                                │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Schema:     ✓ main.financial_risk                            │
│  Volume:     ✓ /Volumes/main/financial_risk/raw/              │
│  Seed data:  ✓ 3 CSVs uploaded                                │
│                                                               │
│  Landing zone layout:                                         │
│    raw/counterparties/counterparties.csv   20 rows            │
│    raw/transactions/transactions.csv       ~960 rows          │
│    raw/market_data/market_data.csv         ~3,200 rows        │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  Dev loop                                                     │
├───────────────────────────────────────────────────────────────┤
│  mise run test         Run local tests                        │
│  mise run lint         Lint check                             │
│  mise run deploy:dev   Push changes to Databricks             │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  What's next                                                  │
├───────────────────────────────────────────────────────────────┤
│  Stage 3 — Bronze (raw ingestion)                             │
│  Deploy and run the Bronze pipeline to ingest raw CSVs        │
│  into Delta tables                                            │
│  Run /silver-databricks:run-bronze                            │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Important

- **No pipeline was deployed in this stage** — Stage 3 handles the first deployment, scoped to Bronze only. This keeps each stage focused: Stage 2 = infrastructure, Stage 3 = first pipeline layer.
- **Authentication uses OAuth** — credentials are in `~/.databrickscfg`, managed by the CLI.
- **Volume paths need `dbfs:` prefix** — use `dbfs:/Volumes/...` for `databricks fs` commands.
- If the user is on Free Edition, some CLI commands may behave differently — help troubleshoot patiently.
- The `--overwrite` flag on `databricks fs cp` is safe for seed data — it's regenerable.
