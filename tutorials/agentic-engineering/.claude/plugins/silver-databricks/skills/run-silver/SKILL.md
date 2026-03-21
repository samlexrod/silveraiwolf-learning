---
description: "[Stage 4] Deploy the Silver pipeline, run it on Databricks, and verify cleaned/enriched data"
---

# Silver — Cleaned & Conformed (ODS / DWH)

Deploy and run the second layer of the medallion architecture — cleaning, validating, deduplicating, and enriching Bronze data into analyst-ready tables.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 3 (run-bronze), the learner has:
- Bronze tables populated in `main.financial_risk` (counterparties, transactions, market_data)
- `databricks.yml` scoped to Bronze only (Silver and Gold commented out)
- A working dev loop: edit → test → deploy → verify

This stage adds the Silver layer to the pipeline, deploys it, and verifies that cleaned/enriched data is correct.

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm Bronze tables exist and auth works:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
```

Verify auth:

```bash
databricks auth describe
```

If auth fails, tell the user to re-authenticate:

```bash
databricks auth login --host <WORKSPACE_URL>
```

Verify Bronze tables have data by querying row counts:

```bash
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"SELECT 'bronze_counterparties' as tbl, COUNT(*) as cnt FROM main.financial_risk.bronze_counterparties UNION ALL SELECT 'bronze_transactions', COUNT(*) FROM main.financial_risk.bronze_transactions UNION ALL SELECT 'bronze_market_data', COUNT(*) FROM main.financial_risk.bronze_market_data\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

If Bronze tables are empty or missing, tell the user to run `/silver-databricks:run-bronze` first.

If the SQL warehouse query fails, try listing the pipeline instead:

```bash
databricks pipelines list-pipelines -o json
```

Confirm the pipeline exists and had a completed Bronze run.

---

### Step 2 — Explain What Silver Does

Tell the user:

> **Silver = Cleaned, Conformed, Enriched.** This is where raw data becomes reliable. Silver applies:
>
> - **Schema enforcement** — explicit types (`decimal(18,2)`, `date`, `bigint`) instead of inferred strings
> - **Standardization** — names trimmed and uppercased, codes normalized
> - **Deduplication** — duplicate records removed by primary key
> - **Validation** — data quality expectations that flag or drop bad rows
> - **Enrichment** — derived columns like net positions and market values
>
> ```
>  Bronze (raw, as-is)                    Silver (cleaned, enriched)
>  ─────────────────────                  ──────────────────────────────
>
>  bronze_counterparties  ──── clean ──>  silver_counterparties
>    " apex capital "                       "APEX CAPITAL"
>    total_assets: "1500000"                total_assets: 1500000.00
>
>  bronze_transactions    ──── clean ──>  silver_transactions
>    direction: "buy"                       direction: "BUY"
>    amount: "50000"                        amount: 50000.00
>    (invalid rows)                         (dropped by expect_or_drop)
>
>  bronze_market_data     ──── clean ──>  silver_market_data
>    close_price: null (gap)                close_price: 142.50 (forward-filled)
>    (duplicates)                           (deduplicated by instrument+date)
>
>                                         silver_positions  (NEW — derived)
>                                           net_quantity, market_value,
>                                           unrealized_pnl per counterparty
> ```
>
> Silver uses two types of **data quality expectations** (decorators on the table functions):
>
> | Decorator | Behavior | Use When |
> |---|---|---|
> | `@sp.expect("name", "condition")` | **Warn** — row is kept, violation is logged | Soft rules you want to monitor |
> | `@sp.expect_or_drop("name", "condition")` | **Drop** — row is silently removed | Hard rules where bad data must not pass |
>
> For example, `silver_transactions` uses `@sp.expect_or_drop` for `direction IN ('BUY', 'SELL')` — any row with an invalid direction is dropped because downstream calculations (signed quantities) would be wrong.

---

### Step 3 — Walk Through the Source Files

Tell the user:

> Let's look at each Silver source file before deploying. Understanding the transformations helps you debug when expectations fire. I'll walk through them one at a time.

**File 1: `src/financial_risk/silver/counterparties.py`**

Read the file and present with this structure:

> ### `silver_counterparties`
>
> | Property | Value |
> |---|---|
> | **Source** | `bronze_counterparties` |
> | **Read mode** | Batch (`sp.read`) |
> | **Dedup key** | `counterparty_id` |
>
> **Transformations:**
> - Trims and uppercases `name`, `sector`, `country`
> - Casts all 10 financial columns to `decimal(18,2)` for precision
>
> **Expectations** (5 — all warn, rows kept):
>
> | Expectation | Condition |
> |---|---|
> | `valid_counterparty_id` | `counterparty_id IS NOT NULL` |
> | `valid_name` | `name IS NOT NULL AND length(name) > 0` |
> | `valid_credit_rating` | Must be AAA through D |
> | `positive_assets` | `total_assets > 0` |
> | `positive_equity` | `total_equity > 0` |

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue to the next file. Offer "Continue to transactions" and "I have questions about this file".

**File 2: `src/financial_risk/silver/transactions.py`**

Read the file and present with this structure:

> ### `silver_transactions`
>
> | Property | Value |
> |---|---|
> | **Source** | `bronze_transactions` |
> | **Read mode** | Streaming (`sp.read_stream`) |
> | **Dedup key** | `transaction_id` |
>
> **Transformations:**
> - Uppercases and trims `direction`, `instrument_type`, `currency`
> - Casts `transaction_date` to `date`, financial columns to `decimal`
>
> **Expectations** (4 warn + 2 drop):
>
> | Expectation | Condition | Action |
> |---|---|---|
> | `valid_transaction_id` | `transaction_id IS NOT NULL` | WARN |
> | `valid_date` | `transaction_date IS NOT NULL` | WARN |
> | `valid_counterparty` | `counterparty_id IS NOT NULL` | WARN |
> | `positive_amount` | `amount > 0` | WARN |
> | `valid_direction` | `direction IN ('BUY', 'SELL')` | **DROP** |
> | `valid_instrument_type` | `instrument_type IN ('EQUITY', 'BOND', 'DERIVATIVE', 'FX')` | **DROP** |
>
> This is the first file with `@sp.expect_or_drop` — those rows are silently removed, not just flagged. This matters because downstream tables (`silver_positions`) compute signed quantities from `direction`. A row with `direction = "HOLD"` would produce a wrong calculation.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to market data" and "I have questions about this file".

**File 3: `src/financial_risk/silver/market_data.py`**

Read the file and present with this structure:

> ### `silver_market_data`
>
> | Property | Value |
> |---|---|
> | **Source** | `bronze_market_data` |
> | **Read mode** | Batch (`sp.read`) — see architecture note below |
> | **Dedup key** | `(instrument_id, trade_date)` |
>
> **Transformations:**
> - Casts dates, prices to `decimal(18,4)`, volume to `bigint`
> - **Forward-fills** missing close prices using a window function — if an instrument has a null price on a given day, it inherits the last known price
>
> **Expectations** (3 — all warn):
>
> | Expectation | Condition |
> |---|---|
> | `valid_instrument` | `instrument_id IS NOT NULL` |
> | `valid_date` | `trade_date IS NOT NULL` |
> | `positive_close` | `close_price > 0` |
>
> ---
>
> **Architecture decision — why batch, not streaming?**
>
> The forward-fill uses `F.last("close_price", ignorenulls=True).over(Window.partitionBy("instrument_id").orderBy("trade_date"))` — an **unbounded window function** that scans all historical rows for an instrument. Spark Structured Streaming cannot do this because it processes data in micro-batches and only sees the rows arriving *right now*, not historical rows.
>
> | Approach | Why it doesn't work here |
> |---|---|
> | **Streaming** (`read_stream`) | Window functions require the full dataset — streaming only sees the current micro-batch |
> | **Watermarks** | Provide bounded lookback (e.g., 7 days) — but forward-fill needs *unbounded* lookback; an instrument might not trade for 30 days |
>
> **Trade-off**: `silver_market_data` is a **materialized view** (full recompute on each run). At 3,200 rows this is trivial. At billions, you'd push gap-filling upstream or partition the recompute.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to positions" and "I have questions about this file".

**File 4: `src/financial_risk/silver/positions.py`**

Read the file and present with this structure:

> ### `silver_positions`
>
> | Property | Value |
> |---|---|
> | **Source** | `silver_transactions` + `silver_market_data` (derived — not from Bronze) |
> | **Read mode** | Batch (`sp.read`) |
> | **Dedup key** | None (aggregation produces unique rows) |
>
> **Transformations:**
> 1. Calculates `signed_quantity` — BUY = positive, SELL = negative
> 2. Groups by counterparty + instrument → `net_quantity`, `total_cost`
> 3. Joins with latest market price per instrument (via `max_by`)
> 4. Computes `market_value` (qty × price) and `unrealized_pnl` (market_value - cost)
>
> **Expectations** (2 — all warn):
>
> | Expectation | Condition |
> |---|---|
> | `valid_position` | `net_quantity IS NOT NULL` |
> | `valid_market_value` | `market_value IS NOT NULL` |
>
> This is the first table that combines data from multiple sources — a classic Silver enrichment pattern.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue — inject dirty data" and "I have questions about this file".

---

### Step 3b — Inject Dirty Data

Tell the user:

> Now that you've seen what each expectation checks, let's **prove they work**. Our seed data is perfectly clean — all 13 expectations would pass with zero violations. That's useless for learning.
>
> I'll create small CSV files with intentionally bad rows and upload them to the Volume alongside the clean data. Bronze will ingest everything raw. Silver is where the expectations will catch the problems.

Create 3 dirty CSV files locally:

**`data/seed/counterparties_dirty.csv`** (3 bad rows):
```csv
counterparty_id,name,sector,country,credit_rating,total_assets,current_assets,total_liabilities,current_liabilities,total_equity,total_debt,revenue,net_income,ebit,interest_expense
CP-021,,TECHNOLOGY,US,A,5000000.00,1000000.00,2000000.00,500000.00,3000000.00,1500000.00,800000.00,100000.00,150000.00,20000.00
CP-022,Ghost Trading,FINANCE,UK,ZZZ,3000000.00,800000.00,1500000.00,400000.00,1500000.00,900000.00,600000.00,50000.00,80000.00,15000.00
CP-023,Negative Corp,ENERGY,DE,BB,-500000.00,200000.00,800000.00,300000.00,-100000.00,600000.00,400000.00,-30000.00,10000.00,25000.00
```

**`data/seed/transactions_dirty.csv`** (4 bad rows):
```csv
transaction_id,transaction_date,counterparty_id,instrument_id,instrument_type,direction,quantity,price,amount,currency
TX-000961,2025-04-01,CP-001,EQ-0001,EQUITY,HOLD,100,150.00,15000.00,USD
TX-000962,2025-04-01,CP-002,BD-0010,OPTION,BUY,500,25.00,12500.00,USD
TX-000963,2025-04-01,,EQ-0005,EQUITY,BUY,200,300.00,-60000.00,EUR
TX-000964,2025-04-01,CP-003,FX-0002,FX,SWAP,75,1200.00,90000.00,GBP
```

**`data/seed/market_data_dirty.csv`** (3 bad rows):
```csv
instrument_id,instrument_type,trade_date,open_price,high_price,low_price,close_price,volume
EQ-0001,EQUITY,2025-04-01,145.00,146.50,144.00,,500000
,EQUITY,2025-04-01,100.00,101.00,99.00,100.50,200000
EQ-0001,EQUITY,2025-04-02,146.00,147.00,145.50,,600000
```

After creating the files, show the user a table of what each dirty row will trigger:

```
┌──────────┬──────────────────────────────┬───────────────────────────────┐
│  File    │  Bad Row                     │  Expected Expectation         │
├──────────┼──────────────────────────────┼───────────────────────────────┤
│  CP      │  CP-021: empty name          │  valid_name → WARN           │
│  CP      │  CP-022: rating "ZZZ"        │  valid_credit_rating → WARN  │
│  CP      │  CP-023: negative assets     │  positive_assets → WARN      │
│  CP      │  CP-023: negative equity     │  positive_equity → WARN      │
├──────────┼──────────────────────────────┼───────────────────────────────┤
│  TX      │  TX-961: direction "HOLD"    │  valid_direction → DROP       │
│  TX      │  TX-962: type "OPTION"       │  valid_instrument_type → DROP │
│  TX      │  TX-963: null counterparty   │  valid_counterparty → WARN   │
│  TX      │  TX-963: negative amount     │  positive_amount → WARN      │
│  TX      │  TX-964: direction "SWAP"    │  valid_direction → DROP       │
├──────────┼──────────────────────────────┼───────────────────────────────┤
│  MKT     │  2 rows: null close_price    │  forward-fill should fix     │
│  MKT     │  1 row: null instrument_id   │  valid_instrument → WARN     │
└──────────┴──────────────────────────────┴───────────────────────────────┘
```

Then upload the dirty files to the Volume as **new files** (Auto Loader picks up new files automatically):

```bash
databricks fs cp data/seed/counterparties_dirty.csv dbfs:/Volumes/main/financial_risk/raw/counterparties/counterparties_dirty.csv --overwrite
databricks fs cp data/seed/transactions_dirty.csv dbfs:/Volumes/main/financial_risk/raw/transactions/transactions_dirty.csv --overwrite
databricks fs cp data/seed/market_data_dirty.csv dbfs:/Volumes/main/financial_risk/raw/market_data/market_data_dirty.csv --overwrite
```

Verify each directory now has 2 files (clean + dirty):

```bash
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/counterparties/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/transactions/
databricks fs ls dbfs:/Volumes/main/financial_risk/raw/market_data/
```

Tell the user:

> Each directory now has 2 files — the clean original and the dirty additions. When the pipeline runs with `--full-refresh`, Bronze will ingest all files raw, and Silver will catch the bad data.

---

### Step 4 — Scope the Pipeline to Bronze + Silver

Tell the user:

> Now I'll update `databricks.yml` to include the Silver libraries alongside Bronze. Gold stays commented out for Stage 5.

Edit `databricks.yml` — uncomment the Silver entries, keep Gold commented:

```yaml
      libraries:
        # Bronze — raw ingestion
        - file:
            path: src/financial_risk/bronze/counterparties.py
        - file:
            path: src/financial_risk/bronze/transactions.py
        - file:
            path: src/financial_risk/bronze/market_data.py
        # Silver — cleaned and conformed
        - file:
            path: src/financial_risk/silver/counterparties.py
        - file:
            path: src/financial_risk/silver/transactions.py
        - file:
            path: src/financial_risk/silver/market_data.py
        - file:
            path: src/financial_risk/silver/positions.py
        # Gold — business metrics (Stage 5)
        # - file:
        #     path: src/financial_risk/gold/financial_ratios.py
        # - file:
        #     path: src/financial_risk/gold/risk_exposure.py
        # - file:
        #     path: src/financial_risk/gold/portfolio_summary.py
```

After editing, confirm:

> ✓ `databricks.yml` updated — Bronze + Silver active, Gold still commented out.

---

### Step 5 — Run Local Tests

Tell the user:

> Before deploying, let's run the local tests to make sure the transformation logic is sound. The unit tests in `tests/unit/test_transformations.py` validate the exact same operations the Silver tables perform — name standardization, deduplication, signed quantities, and market value calculations.

Run:

```bash
export JAVA_HOME=$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

If tests pass:

> ✓ All tests passing, lint clean. Safe to deploy.

If tests fail, investigate and help the user fix before proceeding.

---

### Step 6 — Deploy and Validate

Tell the user:

> Deploying the updated bundle with Silver tables included.

Run:

```bash
mise run deploy:dev
```

Then validate:

```bash
databricks bundle validate --target dev
```

If both succeed:

> ✓ Bundle deployed and validated — Bronze + Silver ready to run.

If deploy fails, troubleshoot:
- **Authentication error**: Re-run `databricks auth login`
- **File not found**: Verify Silver source files exist in `src/financial_risk/silver/`
- **YAML syntax**: Check indentation in `databricks.yml`

---

### Step 7 — Run the Pipeline

Tell the user:

> Time to run the pipeline with Silver included. Since Silver reads from Bronze, Databricks will:
>
> 1. Check that Bronze tables are up to date (they are — no new files since Stage 3)
> 2. Execute all 4 Silver table definitions
> 3. Apply expectations and log any violations
>
> We'll use `--full-refresh` so Silver tables are populated from scratch.
>
> ```
>  Bronze (existing)              Silver (new)
>  ─────────────────              ─────────────────────
>  bronze_counterparties ──────>  silver_counterparties
>  bronze_transactions   ──────>  silver_transactions
>  bronze_market_data    ──────>  silver_market_data
>  silver_transactions + ──────>  silver_positions
>  silver_market_data
> ```

Extract the pipeline ID:

```bash
PIPELINE_ID=$(databricks pipelines list-pipelines -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['pipeline_id'])")
```

Start the pipeline:

```bash
databricks pipelines start-update $PIPELINE_ID --full-refresh
```

Extract the update ID:

```bash
UPDATE_ID=$(databricks pipelines list-updates $PIPELINE_ID -o json | python3 -c "import sys,json; updates=json.load(sys.stdin); print(updates['updates'][0]['update_id'])")
```

Tell the user:

> Pipeline is running. I'll check the status — this typically takes 1–3 minutes on serverless.

Also tell the user they can watch live:

> While the pipeline runs, you can watch it in the Databricks UI:
> 1. Open your workspace
> 2. Go to **Workflows → Delta Live Tables**
> 3. Click on the pipeline — you'll see both Bronze and Silver tables in the graph
> 4. Silver tables will show expectation results (pass/fail counts)

Poll for completion (check every 20–30 seconds, up to 5 minutes):

```bash
databricks pipelines get-update $PIPELINE_ID $UPDATE_ID -o json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"State: {d['update']['state']}\")"
```

Look at the `state` field:
- `QUEUED` or `CREATED` — waiting for compute
- `WAITING_FOR_RESOURCES` — provisioning cluster
- `SETTING_UP_TABLES` — initializing table definitions
- `RUNNING` — executing table definitions
- `COMPLETED` — success
- `FAILED` — check error details

**If `COMPLETED`**:

> ✓ Pipeline run completed — Bronze + Silver!

**If `FAILED`**, extract the error and help troubleshoot:
- **Table not found (bronze_*)**: Bronze tables may have been dropped — re-run Stage 3
- **Expectation violation causing failure**: Check if `@sp.expect_or_fail` was used (it shouldn't be in these files — only `expect` and `expect_or_drop`)
- **Import error**: Check Silver Python files for typos
- **Timeout**: Serverless provisioning can be slow on Free Edition — retry

---

### Step 8 — Verify Silver Tables

Tell the user:

> Let's verify the Silver tables. I'll check row counts, compare with Bronze to confirm deduplication, and inspect expectations.

Query row counts for all tables:

```bash
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
```

```sql
SELECT 'bronze_counterparties' as tbl, COUNT(*) as cnt FROM main.financial_risk.bronze_counterparties
UNION ALL SELECT 'silver_counterparties', COUNT(*) FROM main.financial_risk.silver_counterparties
UNION ALL SELECT 'bronze_transactions', COUNT(*) FROM main.financial_risk.bronze_transactions
UNION ALL SELECT 'silver_transactions', COUNT(*) FROM main.financial_risk.silver_transactions
UNION ALL SELECT 'bronze_market_data', COUNT(*) FROM main.financial_risk.bronze_market_data
UNION ALL SELECT 'silver_market_data', COUNT(*) FROM main.financial_risk.silver_market_data
UNION ALL SELECT 'silver_positions', COUNT(*) FROM main.financial_risk.silver_positions
```

Display as a comparison table:

```
┌────────────────────────────┬───────────┬───────────┐
│  Table                     │  Bronze   │  Silver   │
├────────────────────────────┼───────────┼───────────┤
│  counterparties            │  20       │  20       │
│  transactions              │  ~960     │  ≤960     │
│  market_data               │  ~3,200   │  ≤3,200   │
│  positions (derived)       │  —        │  varies   │
├────────────────────────────┴───────────┴───────────┤
│  Silver ≤ Bronze is expected (dedup + drop rules)  │
└────────────────────────────────────────────────────┘
```

Adapt the table to actual counts. Silver counts should be equal to or less than Bronze counts (due to deduplication and `expect_or_drop`).

If the SQL warehouse is not available, tell the user to verify via the Databricks UI:

> Go to **Catalog → main → financial_risk** and click on each `silver_*` table. Use the **Sample Data** tab to inspect rows.

---

### Step 9 — Inspect Data Quality

Tell the user:

> One of the most powerful features of Silver is built-in data quality monitoring. Let's see what the expectations caught from our dirty data.

#### 9a — Query Expectation Results from the Event Log

DLT stores expectation pass/fail counts in the pipeline's event log. Query the **latest** expectation results per table using the `event_log()` table function:

```sql
WITH latest AS (
  SELECT
    row_expectations.name as expectation,
    row_expectations.dataset as table_name,
    row_expectations.passed_records as passed,
    row_expectations.failed_records as failed,
    row_number() OVER (
      PARTITION BY row_expectations.name, row_expectations.dataset
      ORDER BY timestamp DESC
    ) as rn
  FROM (
    SELECT timestamp,
      explode(from_json(
        details:flow_progress:data_quality:expectations,
        'array<struct<name:string,dataset:string,passed_records:int,failed_records:int>>'
      )) as row_expectations
    FROM event_log(TABLE(main.financial_risk.silver_counterparties))
    WHERE event_type = 'flow_progress'
      AND details:flow_progress:data_quality IS NOT NULL
  )
)
SELECT expectation,
  replace(table_name, 'main.financial_risk.', '') as tbl,
  passed, failed
FROM latest
WHERE rn = 1
ORDER BY tbl, expectation
```

Display the results as a formatted table showing which expectations fired:

```
┌──────────────────────────┬──────────────────────────┬────────┬────────┬──────────┐
│ Expectation              │ Table                    │ Passed │ Failed │ Action   │
├──────────────────────────┼──────────────────────────┼────────┼────────┼──────────┤
│ valid_name               │ silver_counterparties    │     22 │      1 │ WARN ⚠   │
│ valid_credit_rating      │ silver_counterparties    │     22 │      1 │ WARN ⚠   │
│ positive_assets          │ silver_counterparties    │     22 │      1 │ WARN ⚠   │
│ positive_equity          │ silver_counterparties    │     22 │      1 │ WARN ⚠   │
│ ...                      │ ...                      │        │        │          │
│ valid_direction          │ silver_transactions      │    962 │      2 │ DROP ✗   │
│ valid_instrument_type    │ silver_transactions      │    963 │      1 │ DROP ✗   │
│ ...                      │ ...                      │        │        │          │
└──────────────────────────┴──────────────────────────┴────────┴────────┴──────────┘
```

Adapt the table to actual results. Then walk through each observation — don't just list them, explain what it means:

**WARN expectations** (counterparties): CP-021 (empty name), CP-022 (rating ZZZ), CP-023 (negative assets/equity) were all **kept in the table** but flagged as violations. Tell the user:

> These rows are still in `silver_counterparties`. That's intentional — `@sp.expect` is a monitoring tool, not a filter. The data flows through, but the violation count is permanently recorded in the pipeline's event log. If you set up alerting on this (e.g., via Databricks SQL alerts or a webhook), your team gets notified when bad data appears — without blocking the pipeline.
>
> This is something unit tests can't do. Your unit tests validate that the *transformation logic* is correct — "does `F.upper(F.trim(...))` produce the right output?" But they can't tell you that *today's data* has a counterparty with a blank name. Unit tests run against synthetic fixtures at build time. Expectations run against real data at pipeline time. They answer different questions:
>
> | | Unit Tests | Expectations |
> |---|---|---|
> | **When** | Build time (CI) | Pipeline runtime |
> | **What** | Logic correctness | Data correctness |
> | **Input** | Synthetic fixtures | Real production data |
> | **Catches** | Code bugs | Upstream data issues |
> | **Example** | "Does uppercase work?" | "Did a vendor send a blank name today?" |

**DROP expectations** (transactions): TX-961 (direction HOLD), TX-964 (direction SWAP) were dropped by `valid_direction`. TX-962 (instrument type OPTION) was dropped by `valid_instrument_type`. TX-963 (null counterparty, negative amount) was **kept** with two warnings. Tell the user:

> Notice that TX-963 survived even though it has two violations — null counterparty and negative amount. That's because both `valid_counterparty` and `positive_amount` are `@sp.expect` (warn), not `@sp.expect_or_drop`. The row stays in the table. Whether that's the right behavior depends on your business rules. If null counterparties should be blocked, change the decorator to `@sp.expect_or_drop`.
>
> The 3 dropped rows (HOLD, SWAP, OPTION) are gone permanently from Silver. They still exist in Bronze — that's your raw safety net. If you later decide to support a new direction like "HOLD", you'd update the expectation condition and full-refresh to reprocess from Bronze.

**Forward-fill worked** (market data): The 2 rows with null `close_price` for EQ-0001 were filled from the last known price. Tell the user:

> `positive_close` shows 0 failures even though we injected nulls — the forward-fill logic on line 28 ran *before* the expectation evaluated. This is important: transformations happen first, then expectations check the result. The expectation validates the *output*, not the *input*.
>
> The 1 row with null `instrument_id` triggered `valid_instrument` — and because that row has no instrument to join on, it also caused 1 `valid_market_value` failure downstream in `silver_positions`. This is a cascade effect: one bad row in market data ripples into derived tables. Expectations make this visible — without them, you'd see a null market value in Gold and have no idea where it came from.

Tell the user they can also see these in the UI:

> To see these results visually:
> 1. Open the pipeline in **Workflows → Delta Live Tables**
> 2. Click on any Silver table node in the graph
> 3. Look at the **Data Quality** tab — it shows the same pass/fail counts
>
> In production, you'd set up alerts on these counts. A sudden spike in `valid_name` failures means something changed upstream — maybe a vendor changed their API format, or a migration broke a field. Expectations give you observability into data quality the same way application metrics give you observability into service health.

#### 9b — Sample Cleaned Data

Sample the Silver counterparties to show cleaning worked:

```sql
SELECT counterparty_id, name, sector, credit_rating, total_assets
FROM main.financial_risk.silver_counterparties LIMIT 5
```

Point out:
- Names are now uppercased and trimmed (e.g., `APEX CAPITAL` not `apex capital`)
- Financial columns are proper decimals (e.g., `1500000.00` not `"1500000"`)

Sample the Silver positions to show enrichment:

```sql
SELECT counterparty_id, instrument_id, net_quantity, latest_price, market_value, unrealized_pnl
FROM main.financial_risk.silver_positions
ORDER BY ABS(market_value) DESC LIMIT 10
```

Tell the user:

> These positions were **derived** by Silver — they don't exist in any source CSV. The pipeline:
> 1. Read cleaned transactions and computed signed quantities (BUY = +, SELL = -)
> 2. Aggregated net position per counterparty + instrument
> 3. Joined with the latest market price from `silver_market_data`
> 4. Calculated market value and unrealized P&L
>
> This is the kind of enrichment that makes Silver valuable — it turns raw transactional data into a queryable positions table that analysts and risk systems can use directly.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue — clean up dirty data" and "I have questions about the expectations".

---

### Step 9c — Clean Up Dirty Data (Production Pattern)

Tell the user:

> In production, you'll eventually discover bad data upstream — a vendor sends malformed files, a schema changes, or someone uploads a test file to the wrong path. Here's how you handle it in the medallion architecture.
>
> **The problem:** Our Volume now has dirty files alongside clean ones. Bronze ingested everything (it's designed to — raw, as-is). Silver caught the issues via expectations, but the bad data is still sitting in Bronze and flowing through.
>
> **The fix has three steps:**

**1. Remove the bad files from the Volume**

```bash
databricks fs rm dbfs:/Volumes/main/financial_risk/raw/counterparties/counterparties_dirty.csv
databricks fs rm dbfs:/Volumes/main/financial_risk/raw/transactions/transactions_dirty.csv
databricks fs rm dbfs:/Volumes/main/financial_risk/raw/market_data/market_data_dirty.csv
```

Tell the user:

> Removing the files alone isn't enough. Bronze already ingested them — the bad rows are in Delta tables. Deleting upstream files doesn't delete downstream rows.

**2. Full-refresh the pipeline**

```bash
databricks pipelines start-update $PIPELINE_ID --full-refresh
```

Tell the user:

> `--full-refresh` resets all streaming checkpoints and recomputes all tables from scratch. Since the dirty files are gone from the Volume, Auto Loader will only see the clean files.
>
> **Trade-off in production:** At scale, full-refresh is expensive. The alternatives:
> - **DELETE + VACUUM** — surgically remove bad rows from Bronze via SQL, then incrementally refresh Silver
> - **Quarantine pattern** — expectations route bad rows to a `_quarantine` table instead of dropping; an operator reviews and fixes upstream
> - **Reprocessing window** — only full-refresh the affected date partition, not the entire table

Poll for pipeline completion (same pattern as Step 7).

**3. Verify the cleanup**

Query row counts again — they should be back to the original clean counts (20 / 960 / 3200).

Also clean up the local dirty CSV files:

```bash
rm -f data/seed/counterparties_dirty.csv data/seed/transactions_dirty.csv data/seed/market_data_dirty.csv
```

---

### Step 10 — What Just Happened

Tell the user:

> Here's the full picture across Stages 2–4:
>
> ```
>  Stage 2: Raw Volume          Stage 3: Bronze            Stage 4: Silver
>  ──────────────────           ─────────────────          ──────────────────────
>
>  counterparties.csv  ──────>  bronze_counterparties ──>  silver_counterparties
>                                 20 rows                    20 rows (cleaned)
>
>  transactions.csv    ──────>  bronze_transactions  ──>  silver_transactions
>                                 ~960 rows                  ≤960 rows (deduped)
>                                                                    │
>  market_data.csv     ──────>  bronze_market_data   ──>  silver_market_data
>                                 ~3,200 rows                ≤3,200 rows (gap-filled)
>                                                                    │
>                                                          silver_positions (derived)
>                                                            net qty + market value
>
>     CSV files               raw Delta tables           clean, enriched, validated
> ```
>
> **Key concepts from this stage:**
>
> 1. **Data Quality Expectations** — `@sp.expect` warns on violations (rows kept), `@sp.expect_or_drop` removes bad rows. These are declarative quality gates — no custom error handling code needed. You saw this in action: our dirty data triggered 4 warn expectations and 3 row drops.
>
> 2. **Type enforcement** — Bronze stores everything as inferred types (often strings). Silver casts to explicit types (`decimal(18,2)`, `date`, `bigint`). This catches schema drift early.
>
> 3. **Forward-fill and the batch trade-off** — `silver_market_data` uses an unbounded window function to fill price gaps. Streaming can't do this (it only sees the current micro-batch), and watermarks only provide bounded lookback. So this table uses `sp.read` (batch) and recomputes fully on each run. At 3,200 rows the cost is trivial; at scale, you'd push gap-filling upstream or partition the recompute.
>
> 4. **Derived tables** — `silver_positions` reads from other Silver tables, not from Bronze. This is valid — Silver can have internal dependencies. The framework resolves the execution order automatically.
>
> 5. **Incremental by default (with exceptions)** — streaming tables (`read_stream`) like `silver_transactions` only process new data. On re-run without `--full-refresh`, they're no-ops if no new files arrived. However, batch tables (`sp.read`) like `silver_market_data` and `silver_positions` are materialized views — they recompute fully every run. This is a deliberate trade-off: streaming for simple transformations, batch for operations that need full dataset access.

---

### Step 11 — Summary

Display a summary:

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 4 — Silver (ODS / DWH) Complete!                       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Bundle:     ✓ Deployed (Bronze + Silver, dev mode)           │
│  Validation: ✓ Dry run passed                                 │
│  Execution:  ✓ Full refresh completed                         │
│                                                               │
│  Tables created:                                              │
│    silver_counterparties   cleaned + typed        (batch)     │
│    silver_transactions     deduped + validated    (streaming) │
│    silver_market_data      gap-filled + deduped   (batch*)    │
│    silver_positions        derived: qty * price   (batch)     │
│                                                               │
│  * batch because forward-fill window function needs           │
│    unbounded lookback — incompatible with streaming            │
│                                                               │
│  Data quality:                                                │
│    Expectations:  warn (11) + drop (2) = 13 rules active      │
│    Dirty data test: warnings fired, rows dropped              │
│    Cleanup: full-refresh after removing bad source files       │
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
│  Stage 5 — Gold (Business Metrics)                            │
│  Add Gold tables: financial ratios, risk exposure,            │
│  and portfolio summary for executive dashboards               │
│  Run /silver-databricks:run-gold                              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Important

- **Pipeline now includes Bronze + Silver** — Gold is still commented out in `databricks.yml`. Stage 5 will uncomment Gold and redeploy.
- **`--full-refresh`** is needed because Silver streaming tables need to reprocess all Bronze data on first run. Without it, they'd see no new data (Bronze hasn't changed since Stage 3).
- **Expectation results are visible in the pipeline UI** — the Data Quality tab shows pass/fail counts per expectation per table. This is the primary monitoring interface for production pipelines.
- **`silver_positions` depends on `silver_transactions` and `silver_market_data`** — the framework handles execution order automatically. If a dependency fails, dependent tables are skipped.
- If the SQL Statements API doesn't work on Free Edition, always fall back to the UI — Catalog browser and pipeline graph are reliable alternatives.
- If the pipeline run takes longer than 5 minutes, suggest the user check the Databricks UI for detailed logs.
