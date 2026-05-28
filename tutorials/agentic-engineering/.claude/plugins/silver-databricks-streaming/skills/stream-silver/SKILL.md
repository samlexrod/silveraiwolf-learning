---
description: "[Stage 7] Deploy ALL Silver tables — CDC (APPLY CHANGES INTO) + API (streaming transforms) across 2 pipelines"
---

# Streaming Silver — CDC Parsing + API Transforms + Data Quality

Deploy the Silver layer across two pipelines: the **app_streams** pipeline uses `APPLY CHANGES INTO` for CDC workloads (UPSERT/DELETE semantics), and the **data_fabric** pipeline uses standard streaming transforms for API data (append-only). Two Silver patterns, one goal: clean, validated, business-ready data.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 4 (stream-bronze), the learner has:
- app_streams pipeline: 7 CDC Bronze tables consuming from Kafka
- data_fabric pipeline: 5 API Bronze tables watching landing zone (empty until Stage 7)
- Both pipelines running continuously in serverless mode

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm Bronze tables are populated and both pipelines are running:

```bash
source .env

# Check both pipeline states
for PIPELINE_ID in $APP_STREAMS_PIPELINE_ID $DATA_FABRIC_PIPELINE_ID; do
  databricks pipelines get $PIPELINE_ID --output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'{data[\"name\"]}: {data[\"state\"]}')
"
done
```

Query CDC Bronze row counts to confirm data is flowing.

---

### Step 2 — Explain the Two Silver Patterns

The transition from Bronze to Silver uses fundamentally different patterns depending on the data source:

```
  Pattern A: CDC Silver (APPLY CHANGES)        Pattern B: API Silver (streaming transforms)
 ┌──────────────────────────────────────┐      ┌──────────────────────────────────────┐
 │ Bronze CDC envelope:                 │      │ Bronze API file:                     │
 │ {                                    │      │ {                                    │
 │   "op": "u",                         │      │   "entity_id": "OFAC-12345",         │
 │   "before": { old row },             │      │   "name": "Sanctioned Corp",         │
 │   "after": { new row },              │      │   "list_type": "SDN",                │
 │   "ts_ms": 1234567890                │      │   "effective_date": "2024-01-15"     │
 │ }                                    │      │ }                                    │
 │                                      │      │                                      │
 │ ───── parse CDC envelope ─────>      │      │ ───── clean + validate ─────>        │
 │ ───── extract before/after ───>      │      │ ───── cast types ──────────>         │
 │ ───── APPLY CHANGES INTO ────>       │      │ ───── add expectations ────>         │
 │                                      │      │                                      │
 │ Result: current-state table          │      │ Result: append-only table            │
 │ (UPSERTs + DELETEs applied)          │      │ (each job run adds new rows)         │
 └──────────────────────────────────────┘      └──────────────────────────────────────┘
```

**Why different patterns?**
- **CDC data** represents **changes** to existing rows — you need UPSERT/DELETE semantics to maintain the current state of each entity
- **API data** represents **point-in-time snapshots** — each job run produces a new set of records (today's exchange rates, current sanctions list). Append-only is correct because each snapshot is a valid historical record

Use `AskUserQuestion` to confirm understanding.

---

### Step 3 — Part A: CDC Silver (app_streams pipeline)

#### Step 3a — Introduce `APPLY CHANGES INTO`

Spark Declarative Pipelines provides `APPLY CHANGES INTO` (via `sp.apply_changes`) for CDC workloads:

```
  Batch tutorial:                    Streaming CDC tutorial:
 ┌────────────────────┐             ┌────────────────────────────────┐
 │ @sp.table           │             │ @sp.table (staging)            │
 │   read -> transform  │             │   readStream -> parse CDC JSON  │
 │   -> write           │             │                                │
 │                     │             │ sp.apply_changes(              │
 │ (append-only or     │             │   target = "silver_table",     │
 │  full recompute)    │             │   source = "staging_table",    │
 │                     │             │   keys = ["id"],               │
 │                     │             │   sequence_by = "ts_ms",       │
 │                     │             │   apply_as_deletes = "op='d'", │
 │                     │             │ )                              │
 │                     │             │                                │
 │ Result: append log  │             │ Result: current-state table    │
 │ or snapshot         │             │ (UPSERTs + DELETEs applied)    │
 └────────────────────┘             └────────────────────────────────┘
```

**`APPLY CHANGES INTO` handles:**
- Deduplication by primary key
- Ordering by sequence number (Debezium `ts_ms`)
- UPSERT semantics (INSERT or UPDATE based on key existence)
- DELETE propagation (when `op = 'd'`)
- Out-of-order event handling (late-arriving events resolved by sequence)

Use `AskUserQuestion` to confirm understanding.

#### Step 3b — `src/pipelines/app_streams/counterparty/silver/counterparties.py`

```python
import pyspark.sql.functions as F
import pyspark.sql.types as T
import sparktool.pipeline as sp


# Schema for the Debezium CDC "after" payload
counterparty_schema = T.StructType([
    T.StructField("counterparty_id", T.StringType()),
    T.StructField("name", T.StringType()),
    T.StructField("sector", T.StringType()),
    T.StructField("country", T.StringType()),
    T.StructField("credit_rating", T.StringType()),
    T.StructField("total_assets", T.DecimalType(18, 2)),
    T.StructField("total_liabilities", T.DecimalType(18, 2)),
    T.StructField("equity", T.DecimalType(18, 2)),
    T.StructField("revenue", T.DecimalType(18, 2)),
    T.StructField("net_income", T.DecimalType(18, 2)),
    T.StructField("interest_expense", T.DecimalType(18, 2)),
    T.StructField("current_assets", T.DecimalType(18, 2)),
    T.StructField("current_liabilities", T.DecimalType(18, 2)),
    T.StructField("inventory", T.DecimalType(18, 2)),
    T.StructField("updated_at", T.TimestampType()),
])

cdc_envelope_schema = T.StructType([
    T.StructField("before", counterparty_schema),
    T.StructField("after", counterparty_schema),
    T.StructField("op", T.StringType()),
    T.StructField("ts_ms", T.LongType()),
    T.StructField("source", T.StructType([
        T.StructField("lsn", T.LongType()),
        T.StructField("txId", T.LongType()),
    ])),
])


@sp.table(
    name="bronze_cdc_counterparties_parsed",
    comment="Parsed CDC events — staging table for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_counterparties_parsed():
    return (
        sp.readStream("bronze_cdc_counterparties")
        .select(
            F.from_json(F.col("kafka_value"), cdc_envelope_schema).alias("cdc")
        )
        .select(
            "cdc.op",
            "cdc.ts_ms",
            "cdc.source.lsn",
            F.coalesce("cdc.after", "cdc.before").alias("data"),
        )
        .select(
            "op",
            "ts_ms",
            "lsn",
            "data.*",
        )
    )


sp.apply_changes(
    target="silver_counterparties",
    source="bronze_cdc_counterparties_parsed",
    keys=["counterparty_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
```

**Key design decisions:**
- **Temporary staging table:** `bronze_cdc_counterparties_parsed` is `temporary=True` — exists only during pipeline execution
- **`F.coalesce("cdc.after", "cdc.before")`:** For INSERTs and UPDATEs, use `after`. For DELETEs, `after` is null so fall back to `before`
- **`apply_as_deletes`:** When `op = 'd'`, the row is deleted from the Silver table
- **`except_column_list`:** CDC metadata (`op`, `ts_ms`, `lsn`) not persisted in Silver

Use `AskUserQuestion` to confirm before moving to the next pattern.

#### Step 3c — All 7 CDC Silver Tables

The same CDC pattern applies to all 7 tables. Key differences per table:

| File Path | Target Table | Keys | Notes |
|-----------|-------------|------|-------|
| `src/pipelines/app_streams/counterparty/silver/counterparties.py` | `silver_counterparties` | `counterparty_id` | Core entity |
| `src/pipelines/app_streams/counterparty/silver/credit_ratings_history.py` | `silver_credit_ratings_history` | `rating_id` | Historical ratings |
| `src/pipelines/app_streams/financial/silver/transactions.py` | `silver_transactions` | `transaction_id` | Uppercase direction, cast amount |
| `src/pipelines/app_streams/financial/silver/market_prices.py` | `silver_market_prices` | `instrument_id, trade_date` | Composite key |
| `src/pipelines/app_streams/financial/silver/positions.py` | `silver_positions` | (derived) | Joins transactions + market_prices |
| `src/pipelines/app_streams/operations/silver/office_locations.py` | `silver_office_locations` | `office_id` | Reference data |
| `src/pipelines/app_streams/operations/silver/trading_desks.py` | `silver_trading_desks` | `desk_id` | Desk metadata |
| `src/pipelines/app_streams/operations/silver/desk_assignments.py` | `silver_desk_assignments` | `assignment_id` | Desk-counterparty mapping |

**Note:** `silver_positions` is a **derived Silver table** — it reads from `silver_transactions` and `silver_market_prices` (not from Bronze). When a new transaction CDC event arrives, the Silver transaction table is updated via `APPLY CHANGES INTO`, which triggers positions to recompute.

---

### Step 4 — Part B: API Silver (data_fabric pipeline)

The API Silver pattern is simpler — no CDC envelope parsing, no `APPLY CHANGES INTO`. Standard streaming transforms with expectations.

#### Step 4a — `src/pipelines/data_fabric/compliance/silver/sanctions_watchlist.py`

```python
import pyspark.sql.functions as F
import sparktool.pipeline as sp


@sp.table(
    name="silver_sanctions_watchlist",
    comment="Cleaned sanctions watchlist — validated and typed from API Bronze",
)
@sp.expect("valid_entity_id", "entity_id IS NOT NULL")
@sp.expect("valid_list_type", "list_type IN ('SDN', 'CONSOLIDATED', 'SECTORAL')")
def silver_sanctions_watchlist():
    return (
        sp.readStream("bronze_api_sanctions_watchlist")
        .select(
            F.col("entity_id").cast("string"),
            F.col("name").cast("string"),
            F.col("list_type").cast("string"),
            F.col("country").cast("string"),
            F.to_date("effective_date").alias("effective_date"),
            F.col("source_file"),
            F.col("ingested_at"),
        )
    )
```

**Key differences from CDC Silver:**
- **No staging table / `apply_changes`** — API data is append-only. Each job run adds new records
- **Direct `readStream`** — reads from Bronze and applies transforms in one step
- **`@sp.expect` decorators** — data quality expectations applied directly on the table
- **`source_file` preserved** — traces each row back to the specific file (and therefore the specific job run)

Use `AskUserQuestion` to confirm understanding.

#### Step 4b — All 5 API Silver Tables

| File Path | Table Name | Key Transforms |
|-----------|------------|----------------|
| `src/pipelines/data_fabric/compliance/silver/sanctions_watchlist.py` | `silver_sanctions_watchlist` | Validate entity_id, list_type |
| `src/pipelines/data_fabric/compliance/silver/kyc_records.py` | `silver_kyc_records` | Validate status, risk_level |
| `src/pipelines/data_fabric/market_reference/silver/exchange_rates.py` | `silver_exchange_rates` | Cast rates to decimal, validate currency pairs |
| `src/pipelines/data_fabric/market_reference/silver/benchmark_rates.py` | `silver_benchmark_rates` | Cast rates to decimal, validate benchmark names |
| `src/pipelines/data_fabric/regulatory/silver/reporting_requirements.py` | `silver_reporting_requirements` | Validate requirement types, deadlines |

**Important:** Like the Bronze API tables, these Silver API tables will remain empty until the Python batch jobs run in Stage 7.

---

### Step 5 — Scope Both Pipelines to Bronze + Silver

Uncomment Silver libraries in `databricks.yml`:

```yaml
resources:
  pipelines:
    app_streams:
      libraries:
        # Financial domain
        - file: { path: src/pipelines/app_streams/financial/bronze/transactions.py }
        - file: { path: src/pipelines/app_streams/financial/bronze/market_prices.py }
        - file: { path: src/pipelines/app_streams/financial/silver/transactions.py }
        - file: { path: src/pipelines/app_streams/financial/silver/market_prices.py }
        - file: { path: src/pipelines/app_streams/financial/silver/positions.py }
        # Counterparty domain
        - file: { path: src/pipelines/app_streams/counterparty/bronze/counterparties.py }
        - file: { path: src/pipelines/app_streams/counterparty/bronze/credit_ratings_history.py }
        - file: { path: src/pipelines/app_streams/counterparty/silver/counterparties.py }
        - file: { path: src/pipelines/app_streams/counterparty/silver/credit_ratings_history.py }
        # Operations domain
        - file: { path: src/pipelines/app_streams/operations/bronze/office_locations.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/trading_desks.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/desk_assignments.py }
        - file: { path: src/pipelines/app_streams/operations/silver/office_locations.py }
        - file: { path: src/pipelines/app_streams/operations/silver/trading_desks.py }
        - file: { path: src/pipelines/app_streams/operations/silver/desk_assignments.py }
        # Gold still commented out

    data_fabric:
      libraries:
        # Compliance domain
        - file: { path: src/pipelines/data_fabric/compliance/bronze/sanctions_watchlist.py }
        - file: { path: src/pipelines/data_fabric/compliance/bronze/kyc_records.py }
        - file: { path: src/pipelines/data_fabric/compliance/silver/sanctions_watchlist.py }
        - file: { path: src/pipelines/data_fabric/compliance/silver/kyc_records.py }
        # Market Reference domain
        - file: { path: src/pipelines/data_fabric/market_reference/bronze/exchange_rates.py }
        - file: { path: src/pipelines/data_fabric/market_reference/bronze/benchmark_rates.py }
        - file: { path: src/pipelines/data_fabric/market_reference/silver/exchange_rates.py }
        - file: { path: src/pipelines/data_fabric/market_reference/silver/benchmark_rates.py }
        # Regulatory domain
        - file: { path: src/pipelines/data_fabric/regulatory/bronze/reporting_requirements.py }
        - file: { path: src/pipelines/data_fabric/regulatory/silver/reporting_requirements.py }
        # Gold still commented out

    # analytics pipeline not deployed yet
```

---

### Step 6 — Run Local Tests

```bash
mise run test
mise run lint
```

---

### Step 7 — Deploy and Run

```bash
mise run deploy:dev
databricks bundle validate --target dev
```

Both pipelines update in place — Bronze streams continue running, Silver streams start consuming from Bronze tables.

---

### Step 8 — Verify CDC Silver Tables (app_streams)

Query Silver tables to confirm CDC events have been parsed and applied:

```sql
-- Should show current-state rows (not CDC envelopes)
SELECT counterparty_id, name, credit_rating, total_assets
FROM main.financial_risk_streaming.silver_counterparties
LIMIT 5;

-- Row counts should match seed data
SELECT
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_counterparties) as counterparties,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_transactions) as transactions,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_market_prices) as market_prices,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_credit_ratings_history) as credit_ratings,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_office_locations) as offices,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_trading_desks) as desks,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_desk_assignments) as assignments;
```

Present results as a table. Row counts should match the PostgreSQL seed data.

---

### Step 9 — Verify API Silver Tables (data_fabric)

API Silver tables should still be empty — waiting for jobs:

| Silver Table | Row Count | Status |
|-------------|-----------|--------|
| silver_sanctions_watchlist | 0 | Waiting for job (Stage 7) |
| silver_kyc_records | 0 | Waiting for job (Stage 7) |
| silver_exchange_rates | 0 | Waiting for job (Stage 7) |
| silver_benchmark_rates | 0 | Waiting for job (Stage 7) |
| silver_reporting_requirements | 0 | Waiting for job (Stage 7) |

---

### Step 10 — Compare the Two Silver Patterns

| Aspect | CDC Silver (app_streams) | API Silver (data_fabric) |
|--------|--------------------------|--------------------------|
| Source | Bronze CDC events (Kafka) | Bronze API files (Auto Loader) |
| Read pattern | `sp.readStream("bronze_cdc_*")` | `sp.readStream("bronze_api_*")` |
| Write pattern | `sp.apply_changes()` (UPSERT/DELETE) | `@sp.table` (append-only) |
| Schema handling | Explicit Debezium schema | Inferred from JSON files |
| Change handling | Real-time INSERT/UPDATE/DELETE | Append new snapshots |
| Deduplication | `keys=["id"]` in `apply_changes` | Not needed (each file is unique) |
| Delete support | `apply_as_deletes=expr("op='d'")` | Not applicable |
| Staging table | Temporary `_parsed` table | Not needed |

Use `AskUserQuestion` to confirm understanding.

---

### Step 11 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| CDC staging tables | Streaming | 7 temporary tables parsing CDC envelopes |
| silver_counterparties | APPLY CHANGES | UPSERT by `counterparty_id` |
| silver_credit_ratings_history | APPLY CHANGES | UPSERT by `rating_id` |
| silver_transactions | APPLY CHANGES | UPSERT by `transaction_id` |
| silver_market_prices | APPLY CHANGES | UPSERT by `(instrument_id, trade_date)` |
| silver_positions | Derived | Recomputed from streaming Silver tables |
| silver_office_locations | APPLY CHANGES | UPSERT by `office_id` |
| silver_trading_desks | APPLY CHANGES | UPSERT by `desk_id` |
| silver_desk_assignments | APPLY CHANGES | UPSERT by `assignment_id` |
| API Silver tables (5) | Empty | Waiting for Python jobs (Stage 7) |

**Next:** Run `/silver-databricks-streaming:stream-gold` to add domain-specific Gold tables and the cross-domain analytics pipeline.
