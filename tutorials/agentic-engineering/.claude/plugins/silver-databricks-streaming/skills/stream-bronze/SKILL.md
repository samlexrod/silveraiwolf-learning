---
description: "[Stage 6] Deploy ALL Bronze tables — CDC (7 tables from Kafka) + API (5 tables from Auto Loader) across 2 pipelines"
---

# Streaming Bronze — CDC + Auto Loader Ingestion

Deploy the Bronze layer across two pipelines: the **app_streams** pipeline reads 7 CDC topics from Kafka, and the **data_fabric** pipeline reads 5 API landing zone directories via Auto Loader. Two ingestion patterns, one Bronze philosophy: store raw data, parse nothing.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 3 (verify-cdc), the learner has:
- CDC pipeline verified: Postgres -> Debezium -> Redpanda (7 topics)
- Initial snapshot data in all topics
- No Databricks pipelines yet

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm CDC infrastructure and Databricks auth:

```bash
source .env

# Verify Kafka is reachable
nc -zv $EC2_PUBLIC_IP 9092

# Verify Databricks auth
databricks auth env

# Verify topics have data
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "docker exec redpanda rpk topic list"
```

---

### Step 2 — Explain the Two-Pipeline Bronze Architecture

This is the **key learning moment** — two different ingestion patterns feeding into the same medallion architecture:

```
                              Pipeline 1: app_streams (continuous)
                             ┌──────────────────────────────────────────────────┐
                             │  CDC Bronze — readStream("kafka")               │
  Redpanda (7 topics)        │                                                  │
 ┌──────────────────┐        │  Financial domain:                               │
 │ .counterparties  │───────>│    bronze_cdc_transactions                       │
 │ .credit_ratings  │───────>│    bronze_cdc_market_prices                      │
 │ .transactions    │───────>│  Counterparty domain:                            │
 │ .market_prices   │───────>│    bronze_cdc_counterparties                     │
 │ .office_locations│───────>│    bronze_cdc_credit_ratings_history             │
 │ .trading_desks   │───────>│  Operations domain:                              │
 │ .desk_assignments│───────>│    bronze_cdc_office_locations                   │
 └──────────────────┘        │    bronze_cdc_trading_desks                      │
                             │    bronze_cdc_desk_assignments                   │
                             └──────────────────────────────────────────────────┘

                              Pipeline 2: data_fabric (continuous)
                             ┌──────────────────────────────────────────────────┐
                             │  API Bronze — readStream("cloudFiles")          │
  Landing Zone (Volumes)     │                                                  │
 ┌──────────────────┐        │  Compliance domain:                              │
 │ /landing/        │        │    bronze_api_sanctions_watchlist                │
 │  sanctions/      │───────>│    bronze_api_kyc_records                       │
 │  kyc/            │───────>│  Market Reference domain:                       │
 │  exchange_rates/ │───────>│    bronze_api_exchange_rates                    │
 │  benchmark_rates/│───────>│    bronze_api_benchmark_rates                   │
 │  regulatory/     │───────>│  Regulatory domain:                              │
 └──────────────────┘        │    bronze_api_reporting_requirements            │
                             └──────────────────────────────────────────────────┘
```

**Why two pipelines?**
- **Different source systems** — Kafka topics vs file-based landing zones require different read patterns
- **Independent lifecycle** — CDC runs continuously; data_fabric runs continuously but processes data only when new files arrive
- **Fault isolation** — if the Kafka connection drops, the API pipeline keeps processing
- **Independent scaling** — each pipeline scales serverless based on its own throughput

**Both share the same Bronze philosophy:**
- Store raw data — no parsing, no schema enforcement
- Track ingestion metadata (timestamps, offsets/file paths)
- One table per source

Use `AskUserQuestion` to confirm understanding.

---

### Step 3 — Part A: CDC Bronze (app_streams pipeline)

Walk through the CDC Bronze pattern. This is the same pattern for all 7 tables — one file per topic.

#### Step 3a — `src/pipelines/app_streams/financial/bronze/transactions.py`

```python
import pyspark.sql.functions as F
import sparktool.pipeline as sp


@sp.table(
    name="bronze_cdc_transactions",
    comment="Raw CDC events from PostgreSQL transactions table via Kafka",
)
def bronze_cdc_transactions():
    kafka_options = sp.get_pipeline_config("kafka_options")

    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_options["bootstrap_servers"])
        .option("subscribe", "postgres.public.transactions")
        .option("startingOffsets", "earliest")
        .option("kafka.security.protocol", "PLAINTEXT")
        .load()
        .select(
            F.col("key").cast("string").alias("kafka_key"),
            F.col("value").cast("string").alias("kafka_value"),
            F.col("topic"),
            F.col("partition"),
            F.col("offset"),
            F.col("timestamp").alias("kafka_timestamp"),
            F.current_timestamp().alias("ingested_at"),
        )
    )
```

**Key design decisions:**
- **Raw storage:** We store the entire Kafka envelope (key, value, topic, partition, offset, timestamp) — no parsing in Bronze
- **`kafka_value` is a JSON string:** The Debezium CDC event with `before`, `after`, `op`, `source`. Parsing happens in Silver
- **`ingested_at`:** When Databricks received the event (not when it happened in Postgres)
- **`startingOffsets: earliest`:** On first run, consume from the beginning of each topic (includes snapshot data)

Use `AskUserQuestion` to confirm before moving to the next pattern.

#### Step 3b — All 7 CDC Bronze Tables

The same pattern repeats for all 7 tables. The only difference is the topic name:

| File Path | Table Name | Topic |
|-----------|------------|-------|
| `src/pipelines/app_streams/financial/bronze/transactions.py` | `bronze_cdc_transactions` | `postgres.public.transactions` |
| `src/pipelines/app_streams/financial/bronze/market_prices.py` | `bronze_cdc_market_prices` | `postgres.public.market_prices` |
| `src/pipelines/app_streams/counterparty/bronze/counterparties.py` | `bronze_cdc_counterparties` | `postgres.public.counterparties` |
| `src/pipelines/app_streams/counterparty/bronze/credit_ratings_history.py` | `bronze_cdc_credit_ratings_history` | `postgres.public.credit_ratings_history` |
| `src/pipelines/app_streams/operations/bronze/office_locations.py` | `bronze_cdc_office_locations` | `postgres.public.office_locations` |
| `src/pipelines/app_streams/operations/bronze/trading_desks.py` | `bronze_cdc_trading_desks` | `postgres.public.trading_desks` |
| `src/pipelines/app_streams/operations/bronze/desk_assignments.py` | `bronze_cdc_desk_assignments` | `postgres.public.desk_assignments` |

**Observation:** The Bronze pattern is intentionally repetitive — every topic gets the same raw treatment. The differentiation happens in Silver.

---

### Step 4 — Part B: API Bronze (data_fabric pipeline)

Now the second ingestion pattern — Auto Loader for API data.

#### Step 4a — `src/pipelines/data_fabric/compliance/bronze/sanctions_watchlist.py`

```python
import pyspark.sql.functions as F
import sparktool.pipeline as sp


@sp.table(
    name="bronze_api_sanctions_watchlist",
    comment="Raw sanctions watchlist data from compliance API via Auto Loader",
)
def bronze_api_sanctions_watchlist():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/Volumes/.../schema/sanctions_watchlist")
        .option("cloudFiles.inferColumnTypes", "true")
        .load("/Volumes/.../landing/sanctions/")
        .select(
            "*",
            F.col("_metadata.file_path").alias("source_file"),
            F.col("_metadata.file_modification_time").alias("file_modified_at"),
            F.current_timestamp().alias("ingested_at"),
        )
    )
```

**Key differences from CDC Bronze:**
- **`readStream("cloudFiles")`** instead of `readStream("kafka")` — Auto Loader watches a directory for new files
- **`_metadata` columns:** Auto Loader provides file path and modification time — useful for auditing which job run produced which data
- **Schema inference:** `cloudFiles.inferColumnTypes` lets Auto Loader detect the JSON schema on first load and evolve it as new fields appear
- **No parsing needed:** JSON files from the Python jobs already have structured fields — unlike CDC envelopes which wrap business data in `before`/`after`

Use `AskUserQuestion` to confirm understanding.

#### Step 4b — All 5 API Bronze Tables

| File Path | Table Name | Landing Zone Path |
|-----------|------------|------------------|
| `src/pipelines/data_fabric/compliance/bronze/sanctions_watchlist.py` | `bronze_api_sanctions_watchlist` | `/Volumes/.../landing/sanctions/` |
| `src/pipelines/data_fabric/compliance/bronze/kyc_records.py` | `bronze_api_kyc_records` | `/Volumes/.../landing/kyc/` |
| `src/pipelines/data_fabric/market_reference/bronze/exchange_rates.py` | `bronze_api_exchange_rates` | `/Volumes/.../landing/exchange_rates/` |
| `src/pipelines/data_fabric/market_reference/bronze/benchmark_rates.py` | `bronze_api_benchmark_rates` | `/Volumes/.../landing/benchmark_rates/` |
| `src/pipelines/data_fabric/regulatory/bronze/reporting_requirements.py` | `bronze_api_reporting_requirements` | `/Volumes/.../landing/regulatory/` |

**Important note:** These Bronze tables will be **empty** until the Python batch jobs run (Stage 7). The data_fabric pipeline is deployed and running, but Auto Loader will not process anything until files land in the landing zone directories.

Use `AskUserQuestion` to confirm understanding.

---

### Step 5 — Configure Kafka Connection in Pipeline

The `kafka_options` are passed via pipeline configuration in `databricks.yml`:

```yaml
resources:
  pipelines:
    app_streams:
      configuration:
        kafka_options.bootstrap_servers: "${var.kafka_bootstrap_servers}"
        kafka_options.security_protocol: "PLAINTEXT"
```

This keeps connection config out of source code — the same pipeline code works in dev and prod by changing the variable.

Show how the variable is set per target:

```yaml
targets:
  dev:
    variables:
      kafka_bootstrap_servers: "xx.xx.xx.xx:9092"  # EC2 Redpanda
  prod:
    variables:
      kafka_bootstrap_servers: "b-1.msk-cluster.xxx:9096"  # MSK (future)
```

---

### Step 6 — Scope Both Pipelines to Bronze Only

Deploy incrementally. Comment out Silver and Gold libraries in `databricks.yml`, keeping only Bronze for both pipelines:

```yaml
resources:
  pipelines:
    app_streams:
      libraries:
        # Financial domain — Bronze only
        - file: { path: src/pipelines/app_streams/financial/bronze/transactions.py }
        - file: { path: src/pipelines/app_streams/financial/bronze/market_prices.py }
        # Counterparty domain — Bronze only
        - file: { path: src/pipelines/app_streams/counterparty/bronze/counterparties.py }
        - file: { path: src/pipelines/app_streams/counterparty/bronze/credit_ratings_history.py }
        # Operations domain — Bronze only
        - file: { path: src/pipelines/app_streams/operations/bronze/office_locations.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/trading_desks.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/desk_assignments.py }
        # Silver and Gold commented out for now

    data_fabric:
      libraries:
        # Compliance domain — Bronze only
        - file: { path: src/pipelines/data_fabric/compliance/bronze/sanctions_watchlist.py }
        - file: { path: src/pipelines/data_fabric/compliance/bronze/kyc_records.py }
        # Market Reference domain — Bronze only
        - file: { path: src/pipelines/data_fabric/market_reference/bronze/exchange_rates.py }
        - file: { path: src/pipelines/data_fabric/market_reference/bronze/benchmark_rates.py }
        # Regulatory domain — Bronze only
        - file: { path: src/pipelines/data_fabric/regulatory/bronze/reporting_requirements.py }
        # Silver and Gold commented out for now

    # analytics pipeline not deployed yet — depends on Silver tables
```

---

### Step 7 — Deploy and Run

```bash
# Deploy both pipelines
databricks bundle deploy --target dev

# Validate
databricks bundle validate --target dev

# Get pipeline IDs from bundle summary
databricks bundle summary --target dev --output json | python3 -c "
import sys, json
summary = json.load(sys.stdin)
for name, pipeline in summary.get('resources', {}).get('pipelines', {}).items():
    print(f'{name}: {pipeline[\"id\"]}')
"
```

**Important — Pipeline Quota:** Free and standard-tier Databricks workspaces can only run **1 active pipeline** at a time. We run each pipeline sequentially: start app_streams, verify it, stop it, then start data_fabric. In production (Enterprise tier), both would run concurrently.

**Important:** Unlike the batch tutorial where we used `--full-refresh`, streaming pipelines run **continuously**. The app_streams pipeline starts, consumes from `earliest`, processes all snapshot data, then waits for new events. The data_fabric pipeline starts and watches for new files — it will be idle until jobs run.

---

### Step 8 — Run and Verify CDC Bronze (app_streams)

Start the app_streams pipeline first — it has CDC data ready to consume:

```bash
databricks pipelines start-update $APP_STREAMS_PIPELINE_ID
```

Poll until the pipeline reaches `RUNNING` or completes its initial batch:

```bash
databricks pipelines get $APP_STREAMS_PIPELINE_ID --output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'{data[\"name\"]}: {data[\"state\"]}')
"
```

Expected states: `QUEUED -> STARTING -> RUNNING`

Once running, query the CDC Bronze tables to verify snapshot data landed:

```sql
SELECT COUNT(*) as cnt, MIN(kafka_timestamp) as earliest, MAX(kafka_timestamp) as latest
FROM main.financial_risk_streaming.bronze_cdc_counterparties
```

Present results as a table:

| Bronze Table | Row Count | Earliest Event | Latest Event |
|-------------|-----------|---------------|-------------|
| bronze_cdc_counterparties | ~20 | (snapshot time) | (snapshot time) |
| bronze_cdc_credit_ratings_history | ~60 | (snapshot time) | (snapshot time) |
| bronze_cdc_transactions | ~900 | (snapshot time) | (snapshot time) |
| bronze_cdc_market_prices | ~3,200 | (snapshot time) | (snapshot time) |
| bronze_cdc_office_locations | ~8 | (snapshot time) | (snapshot time) |
| bronze_cdc_trading_desks | ~12 | (snapshot time) | (snapshot time) |
| bronze_cdc_desk_assignments | ~30 | (snapshot time) | (snapshot time) |

After verification, **stop the app_streams pipeline** to free the quota slot:

```bash
databricks pipelines stop $APP_STREAMS_PIPELINE_ID
```

Wait for it to reach `IDLE` state before starting the next pipeline.

**What just happened:**
- The app_streams pipeline consumed all 7 Kafka topics from `earliest` offset
- Debezium's initial snapshot data (all existing rows as `op: r` events) was ingested into 7 Bronze tables
- Each table stored raw Kafka envelopes: key, value (JSON CDC event), topic, partition, offset, timestamp
- Checkpoints were saved — next time this pipeline starts, it resumes from where it left off (no re-processing)

---

### Step 9 — Seed the Landing Zone with Python Batch Jobs

Before starting the data_fabric pipeline, run the Python batch jobs to drop JSON files into the landing zone. This way Auto Loader has data to process immediately — you'll see data flow through Bronze in one pass.

The 5 jobs simulate external API calls and write JSON Lines files to the landing zone:

```bash
# Set the schema to the dev schema (with username suffix)
export CATALOG=main
export SCHEMA=financial_risk_streaming_<username>

# Run all 5 jobs
uv run python src/jobs/compliance/fetch_sanctions.py
uv run python src/jobs/compliance/fetch_kyc.py
uv run python src/jobs/market_reference/fetch_exchange_rates.py
uv run python src/jobs/market_reference/fetch_benchmark_rates.py
uv run python src/jobs/regulatory/fetch_reporting_requirements.py
```

Each job:
1. Generates realistic sample data (sanctions entries, KYC records, FX rates, benchmark rates, regulatory requirements)
2. Writes a timestamped JSON Lines file to the appropriate landing zone directory (e.g., `/Volumes/.../landing/compliance/sanctions_watchlist/20260321_143000.json`)

Verify files landed:

```bash
databricks api get "/api/2.0/fs/directories/Volumes/main/<schema>/landing/compliance/sanctions_watchlist/"
```

You should see at least one `.json` file per directory.

---

### Step 10 — Run and Verify API Bronze (data_fabric)

Now start the data_fabric pipeline — it has files to process:

```bash
databricks pipelines start-update $DATA_FABRIC_PIPELINE_ID
```

Poll until COMPLETED:

```bash
databricks pipelines get-update $DATA_FABRIC_PIPELINE_ID $UPDATE_ID --output json
```

Query the API Bronze tables — they should now have data:

| Bronze Table | Expected Rows | Source |
|-------------|--------------|--------|
| bronze_sanctions_watchlist | ~50 | sanctions_watchlist/*.json |
| bronze_kyc_records | ~20 | kyc_records/*.json |
| bronze_exchange_rates | ~10 | exchange_rates/*.json |
| bronze_benchmark_rates | ~4 | benchmark_rates/*.json |
| bronze_reporting_requirements | ~15 | reporting_requirements/*.json |

After verification, **stop the data_fabric pipeline** to free the quota slot:

```bash
databricks pipelines stop $DATA_FABRIC_PIPELINE_ID
```

**What just happened:**
- Python batch jobs wrote JSON files to 5 landing zone directories
- The data_fabric pipeline started and Auto Loader detected the new files
- Each Bronze table ingested the JSON data with explicit schemas
- Checkpoints saved — next run will only process new files (incremental)

---

### Step 11 — What Just Happened (Both Pipelines)

```
  EC2 Docker Compose                         Databricks Serverless
 ┌────────────────────┐                     ┌──────────────────────────────────────┐
 │ PostgreSQL         │                     │ app_streams pipeline (verified)     │
 │   ↓ WAL            │                     │                                      │
 │ Debezium           │                     │ 7 CDC Bronze tables ✓                │
 │   ↓ CDC events     │                     │   ← readStream("kafka")             │
 │ Redpanda           │── port 19092 ──────>│   Snapshot data consumed             │
 │   7 topics         │                     │   Checkpoints saved                  │
 └────────────────────┘                     └──────────────────────────────────────┘

  Python Batch Jobs                         ┌──────────────────────────────────────┐
 ┌────────────────────┐                     │ data_fabric pipeline (verified)     │
 │ fetch_sanctions    │                     │                                      │
 │ fetch_kyc          │──> Landing Zone ───>│ 5 API Bronze tables ✓ (populated)   │
 │ fetch_exchange     │    /Volumes/.../    │   ← readStream("cloudFiles")        │
 │ fetch_benchmark    │    landing/         │   JSON files ingested               │
 │ fetch_regulatory   │    *.json           │   Checkpoints saved                  │
 └────────────────────┘                     └──────────────────────────────────────┘
```

**12 Bronze tables verified across 2 pipelines — all populated.** Each table independently:
- Tracks its own checkpoint (Kafka offset or file position)
- Handles backpressure independently
- Can be restarted without affecting others
- Resumes from checkpoint — no re-processing on restart

**Note on pipeline quota:** In production (Enterprise tier), both pipelines run concurrently. In this tutorial, we run them sequentially. Checkpoints ensure exactly-once processing regardless of start/stop cycles.

---

### Step 12 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| app_streams pipeline | Verified + stopped | 7 CDC Bronze tables consumed snapshot data |
| data_fabric pipeline | Verified + stopped | 5 API Bronze tables ingested JSON files |
| CDC Bronze tables | Populated | Snapshot data from all 7 Postgres tables |
| API Bronze tables | Populated | Data from 5 Python batch jobs |
| Checkpointing | Saved | Both pipelines track offsets/file positions |

**Next:** Run `/silver-databricks-streaming:stream-silver` to parse CDC events, apply transformations, and handle INSERT/UPDATE/DELETE operations across all tables.
