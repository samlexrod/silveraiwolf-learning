---
description: "[Stage 3] Deploy the Bronze pipeline, run it on Databricks, and verify raw data landed"
---

# Bronze — Raw Ingestion (Staging)

Deploy and run the first layer of the medallion architecture — landing raw data as-is into Delta tables, with no transformations.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 2 (deploy-dev), the learner has:
- Unity Catalog schema `main.financial_risk` created
- Seed CSVs uploaded to `/Volumes/main/financial_risk/raw/`
- An understanding of what Bronze will do (batch vs Auto Loader)

This stage deploys the pipeline (scoped to Bronze only), runs it, and verifies that raw data landed in Unity Catalog tables.

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm seed data is uploaded and auth works:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
```

Verify seed data is present:

```bash
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/counterparties/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/transactions/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/market_data/
```

If any directory is empty or missing, tell the user to run `/silver-databricks:deploy-dev` first.

Verify auth:

```bash
databricks auth describe
```

If auth fails, tell the user to re-authenticate:

```bash
databricks auth login --host <WORKSPACE_URL>
```

---

### Step 2 — Scope the Pipeline to Bronze Only

Tell the user:

> The project template includes source files for all three layers — Bronze, Silver, and Gold. But we want to **build layer by layer**, so I'll scope `databricks.yml` to include only the Bronze libraries. Silver and Gold will be added back in later stages.
>
> This is how you'd do it on a real team too — deploy incrementally, verify each layer works, then expand.

Edit `databricks.yml` in the project directory. Comment out the Silver and Gold library entries so only Bronze remains:

```yaml
      libraries:
        # Bronze — raw ingestion
        - file:
            path: src/financial_risk/bronze/counterparties.py
        - file:
            path: src/financial_risk/bronze/transactions.py
        - file:
            path: src/financial_risk/bronze/market_data.py
        # Silver — cleaned and conformed (Stage 4)
        # - file:
        #     path: src/financial_risk/silver/counterparties.py
        # - file:
        #     path: src/financial_risk/silver/transactions.py
        # - file:
        #     path: src/financial_risk/silver/market_data.py
        # - file:
        #     path: src/financial_risk/silver/positions.py
        # Gold — business metrics (Stage 5)
        # - file:
        #     path: src/financial_risk/gold/financial_ratios.py
        # - file:
        #     path: src/financial_risk/gold/risk_exposure.py
        # - file:
        #     path: src/financial_risk/gold/portfolio_summary.py
```

After editing, confirm the change:

> ✓ `databricks.yml` scoped to Bronze only — Silver and Gold commented out.

---

### Step 3 — Deploy the Bronze Bundle

Tell the user:

> Now I'll deploy the project to Databricks using **Asset Bundles**. This is the first deploy — it pushes the pipeline definition and Bronze source files to your workspace.
>
> In dev mode, everything gets prefixed with your username (e.g., `[dev samlexrod] Financial Risk Pipeline`) so it doesn't collide with other developers.

Run the deployment:

```bash
mise run deploy:dev
```

This runs `databricks bundle deploy --target dev` which:
- Creates a development pipeline named `[dev <username>] Financial Risk Pipeline`
- Uploads the 3 Bronze source files under `src/financial_risk/bronze/`
- Uploads exploration notebooks

If the deploy fails:
- **Authentication error**: Re-run `databricks auth login --host <WORKSPACE_URL>`
- **Permission error**: The Free Edition workspace may need specific settings — help troubleshoot
- **Bundle validation error**: Check `databricks.yml` for syntax issues

After a successful deploy:

> ✓ Bronze bundle deployed to Databricks!

Extract the pipeline ID — you'll need it for later steps:

```bash
PIPELINE_ID=$(databricks pipelines list-pipelines | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['pipeline_id'])")
```

If no pipeline is found, something went wrong with the deploy — investigate the error.

---

### Step 4 — Validate (Dry Run)

Tell the user:

> Before running the pipeline for real, let's do a **dry run**. This validates the bundle configuration — checking that table definitions, file paths, and YAML structure are correct without provisioning compute or processing data.
>
> Think of it as a compilation check: fast feedback before committing to a full run.

Run the validation:

```bash
databricks bundle validate --target dev
```

This validates the bundle configuration locally (YAML syntax, resource references).

**If validation succeeds**, tell the user:

> ✓ Validation passed — Bronze pipeline is ready to run.

**If validation fails**, read the error carefully:
- **Import error in source file**: Check the Bronze Python files for typos
- **Path not found**: Verify the volume paths match what's in the Bronze code
- **Schema error in `databricks.yml`**: Check YAML indentation and structure

Help the user fix the issue and re-validate before proceeding.

---

### Step 5 — Run the Pipeline

Tell the user:

> Time to run the pipeline! This will:
>
> 1. **Provision serverless compute** (~30–60 seconds on Free Edition)
> 2. **Execute the 3 Bronze table definitions**
> 3. **Read CSVs** from the raw volume and **write them** to Unity Catalog Delta tables
>
> Since this is the first run, we'll use `--full-refresh` to populate the tables from scratch.
>
> ```
>   /Volumes/.../raw/                    main.financial_risk
>   ├── counterparties/*.csv  ────────>  bronze_counterparties  (batch)
>   ├── transactions/*.csv    ────────>  bronze_transactions    (Auto Loader)
>   └── market_data/*.csv     ────────>  bronze_market_data     (Auto Loader)
> ```

Start the pipeline update:

```bash
databricks pipelines start-update $PIPELINE_ID --full-refresh
```

This returns an update ID. Extract it:

```bash
UPDATE_ID=$(databricks pipelines list-updates $PIPELINE_ID | python3 -c "import sys,json; updates=json.load(sys.stdin); print(updates['updates'][0]['update_id'])")
```

Tell the user:

> Pipeline is running. I'll check the status — this typically takes 1–3 minutes on serverless.

Also tell the user they can watch the run live:

> While the pipeline runs, you can watch it live in the Databricks UI:
> 1. Open your workspace
> 2. Go to **Workflows → Delta Live Tables** (or search for the pipeline name)
> 3. Click on `[dev <username>] Financial Risk Pipeline`
> 4. You'll see the pipeline graph with Bronze tables and their status

Poll for completion (check every 20–30 seconds, up to 5 minutes):

```bash
databricks pipelines get-update $PIPELINE_ID $UPDATE_ID
```

Look at the `state` field:
- `QUEUED` or `CREATED` — waiting for compute
- `WAITING_FOR_RESOURCES` — provisioning cluster
- `SETTING_UP_TABLES` — initializing table definitions
- `RUNNING` — executing table definitions
- `COMPLETED` — success
- `FAILED` — check error details

**If `COMPLETED`**:

> ✓ Pipeline run completed successfully!

**If `FAILED`**, extract the error from the update details and help troubleshoot:
- **Volume path not found**: Check that seed data was uploaded in Stage 2
- **Schema mismatch**: The CSV may have unexpected columns — check with `databricks fs cp` to download and inspect locally
- **Permission error**: On Free Edition, verify the pipeline has access to the `main` catalog

---

### Step 6 — Verify Bronze Tables

Tell the user:

> Let's verify the Bronze tables were created with the expected data. I'll query each table to check row counts and sample a few rows.

First, find the SQL warehouse ID:

```bash
databricks warehouses list
```

Use the warehouse ID to query via the Statements API:

```bash
WAREHOUSE_ID=<from the list above>
databricks api post /api/2.0/sql/statements --json '{"statement": "SELECT ...", "warehouse_id": "'$WAREHOUSE_ID'", "wait_timeout": "50s"}'
```

Query each Bronze table for row counts:

```sql
SELECT 'counterparties' as tbl, COUNT(*) as row_count FROM main.financial_risk.bronze_counterparties
UNION ALL SELECT 'transactions', COUNT(*) FROM main.financial_risk.bronze_transactions
UNION ALL SELECT 'market_data', COUNT(*) FROM main.financial_risk.bronze_market_data
```

If the SQL warehouse or Statements API is not available, tell the user:

> The CLI SQL command requires a SQL warehouse. On Free Edition, you can verify via the UI instead:
> 1. Go to **Catalog → main → financial_risk**
> 2. Click on each `bronze_*` table
> 3. Click the **Sample Data** tab to see rows

Expected row counts (from seed data):

| Table | Expected Rows |
|---|---|
| `bronze_counterparties` | 20 |
| `bronze_transactions` | ~960 |
| `bronze_market_data` | ~3,200 |

If SQL works, also show a sample of the counterparties table:

```sql
SELECT counterparty_id, name, sector, credit_rating
FROM main.financial_risk.bronze_counterparties LIMIT 5
```

Tell the user:

> Notice that Bronze preserves the data exactly as it arrived:
> - Column names come from the CSV headers
> - Types were inferred by Spark (strings, integers, doubles) — not explicitly defined
> - No cleaning, no renaming, no validation
>
> This is intentional. Bronze is your raw safety net — if something goes wrong downstream, you can always reprocess from Bronze. The Silver layer (Stage 4) is where we'll apply schema enforcement, type casting, deduplication, and validation.

---

### Step 7 — What Just Happened

Tell the user:

> Here's what happened end to end across Stages 2 and 3:
>
> ```
>  Stage 2: Landing Zone                 Stage 3: Bronze Pipeline
>  ───────────────────────               ──────────────────────────
>
>  /Volumes/main/financial_risk/raw/     main.financial_risk
>  ├── counterparties/                   ├── bronze_counterparties  (batch)
>  │   └── counterparties.csv  ───────>  │   └── 20 rows
>  ├── transactions/                     ├── bronze_transactions    (Auto Loader)
>  │   └── transactions.csv    ───────>  │   └── ~960 rows
>  └── market_data/                      └── bronze_market_data     (Auto Loader)
>      └── market_data.csv     ───────>      └── ~3,200 rows
>
>     CSV files on disk                     Delta tables in catalog
> ```
>
> **Key concepts:**
>
> 1. **Spark Declarative Pipelines** (`@sp.table`) — you declared *what* each table should contain, not *how* to orchestrate it. The framework handles execution order, retries, and checkpointing.
>
> 2. **Auto Loader checkpointing** — for `bronze_transactions` and `bronze_market_data`, Databricks tracks which files have been processed. If you add new CSVs to the volume and re-run the pipeline, only the new files get ingested — the old ones are skipped. This is what makes it production-ready for continuous data feeds.
>
> 3. **Batch vs streaming** — `bronze_counterparties` uses `spark.read` (batch) because counterparty master data is small and gets full-refreshed. The other two use `cloudFiles` (streaming) because in production, new transaction and market data files would arrive continuously.
>
> 4. **Dev loop established** — from now on, every stage follows the same rhythm:
>    ```
>    edit code → mise run test → mise run deploy:dev → verify on Databricks
>    ```

---

### Step 8 — Summary

Display a summary:

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 3 — Bronze (Staging) Complete!                         │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Bundle:     ✓ Deployed (Bronze only, dev mode)               │
│  Validation: ✓ Dry run passed                                 │
│  Execution:  ✓ Full refresh completed                         │
│                                                               │
│  Tables created:                                              │
│    bronze_counterparties   20 rows      (batch)               │
│    bronze_transactions     ~960 rows    (Auto Loader)         │
│    bronze_market_data      ~3,200 rows  (Auto Loader)         │
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
│  Stage 4 — Silver (ODS / DWH)                                 │
│  Add Silver tables: clean, validate, deduplicate, and enrich  │
│  Run /silver-databricks:run-silver                            │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Important

- **Pipeline is scoped to Bronze only** — Silver and Gold are commented out in `databricks.yml`. Stage 4 will uncomment Silver and redeploy.
- **`--full-refresh`** forces all tables to recompute from scratch. Without it, Auto Loader tables would only process new files (there are none, so they'd be no-ops on re-run).
- **Auto Loader checkpoints** are stored by Databricks automatically in dev mode. If you re-run without `--full-refresh`, the streaming tables won't reprocess the same CSVs — this is correct behavior, not a bug.
- If the SQL Statements API doesn't work on Free Edition, always fall back to the UI — Catalog browser and pipeline graph are reliable alternatives.
- If the pipeline run takes longer than 5 minutes, suggest the user check the Databricks UI for detailed logs.
