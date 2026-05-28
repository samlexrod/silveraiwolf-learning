---
description: "[Stage 9] Deploy the single-pipeline alternative (production/continuous) + provision OpenSearch + PySpark JDBC sink on EC2"
---

# Unified Pipeline — Single-Pipeline Alternative + OpenSearch

Deploy the same medallion architecture from Stages 6–8, but in a **single pipeline** instead of three — and add **OpenSearch** as the serving layer. Cross-domain Gold tables compute inline in the same micro-batch. A **PySpark Docker container on EC2** reads Gold tables via JDBC and writes to OpenSearch via the `opensearch-hadoop` Spark connector.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 8 (stream-gold), the learner has:
- The multi-pipeline approach verified: app_streams + data_fabric + analytics (triggered)
- All 35+ tables populated across 3 pipelines
- An understanding of why cross-domain Gold was in a separate triggered pipeline

Now we show the alternative: **one pipeline does it all** — and we add OpenSearch so Gold data is searchable, dashboardable, and API-accessible.

---

## Instructions

---

### Step 1 — Why a Single Pipeline?

Present the comparison the learner already saw in Stage 8, but now from the perspective of "let's build it":

```
  MULTI-PIPELINE (Stages 6–8)                SINGLE-PIPELINE (this stage)
 ┌────────────────────┐                      ┌────────────────────────────────────┐
 │ app_streams        │                      │ unified_risk_pipeline              │
 │  CDC B → S → G     │                      │                                    │
 └────────────────────┘                      │  CDC Bronze (7 Kafka tables)       │
 ┌────────────────────┐                      │  API Bronze (5 Auto Loader tables) │
 │ data_fabric        │         ──────>      │  All Silver (13 tables)            │
 │  API B → S → G     │                      │  All Gold — including cross-domain │
 └────────────────────┘                      │                                    │
 ┌────────────────────┐                      │  One pipeline, one DAG, real-time  │
 │ analytics          │                      └────────────────────────────────────┘
 │  Cross-domain Gold │
 └────────────────────┘                      ┌────────────────────────────────────┐
                                             │  OpenSearch Sink (EC2 Docker)      │
                                             │  PySpark JDBC → opensearch-hadoop  │
                                             │  Reads Gold, indexes 10 indices    │
                                             └────────────────────────────────────┘
```

**What changes:**
- 3 pipelines → 1 pipeline
- The analytics Gold tables (`risk_dashboard`, `regulatory_report`, `desk_pnl_exposure`) move from a triggered pipeline into the main pipeline
- Cross-domain Gold becomes real-time — updated on every micro-batch
- No pipeline quota issues — only 1 pipeline to run
- **OpenSearch added** — Gold tables indexed via a PySpark Docker container on EC2

**What stays the same:**
- All the same Bronze, Silver, and Gold source files
- Same CDC + Auto Loader ingestion patterns
- Same APPLY CHANGES INTO for CDC Silver
- Same data quality expectations

**Trade-offs of the single-pipeline approach:**

| | Multi-Pipeline (Stages 6–8) | Single Pipeline (this stage) |
|-|---------------------------|------------------------------|
| **Cross-domain freshness** | Minutes (triggered schedule) | Real-time (every micro-batch) |
| **Fault isolation** | High — Kafka failure doesn't affect API pipeline | DAG-aware — unrelated tables still complete, but pipeline won't process new micro-batches until fixed |
| **Continuous mode recovery** | Only the failed pipeline stops accepting new data | Entire pipeline pauses new micro-batches (CDC events queue up) until failure is resolved |
| **Deployment independence** | Teams can deploy CDC and API pipelines separately | One deploy, one rollback — all or nothing |
| **Scaling** | Each pipeline scales independently based on its throughput | One pipeline must handle both CDC burst + API batch |
| **Pipeline quota** | 3 slots (ran sequentially on free tier) | 1 slot — no quota issue |
| **Compute cost** | Lower — cross-domain joins only when triggered | Higher — cross-domain joins on every micro-batch |
| **Operational complexity** | Higher — 3 pipelines to monitor, start/stop | Lower — 1 pipeline to manage |
| **Serving layer** | None (query Delta tables directly) | OpenSearch — search, dashboards, REST API |
| **Best for** | Multiple teams, different data cadences, production | Single team, real-time cross-domain, prototyping |

Use `AskUserQuestion` to confirm understanding.

---

### Step 2 — Upgrade EC2 to t3.medium + Provision OpenSearch

The unified stage adds a **PySpark Docker container** (opensearch-sink) alongside the existing CDC stack. PySpark + JVM needs ~1-1.5GB RAM. On a `t3.small` (2GB), the combined memory of Postgres + Redpanda + Debezium + PySpark exceeds the limit and causes OOM-kills (SSH becomes unreachable, containers crash).

#### 2a — Upgrade EC2 Instance

Update `infra/terraform/terraform.tfvars`:

```hcl
instance_type = "t3.medium"   # 4GB RAM — was t3.small (2GB)
enable_opensearch = true
opensearch_master_password = "Admin1234!"
```

**Cost impact:**

| Component | Before (Stages 3-8) | After (Stage 9+) |
|-----------|---------------------|-------------------|
| EC2 | t3.small ~$0.02/hr | t3.medium ~$0.04/hr |
| OpenSearch | — | t3.small.search ~$0.036/hr |
| **Total** | **~$0.02/hr** | **~$0.076/hr** |

**Why t3.medium?** Memory breakdown on the EC2 instance:

| Container | RAM |
|-----------|-----|
| Redpanda | 512MB (explicit) |
| Debezium (JVM) | ~300-500MB |
| Postgres | ~100-200MB |
| Redpanda Console | ~50-100MB |
| **opensearch-sink (PySpark + JVM)** | **~1-1.5GB** |
| **Total** | **~2-2.8GB** |

On `t3.small` (2GB) this OOM-kills. On `t3.medium` (4GB) it runs comfortably.

Plan and apply — this replaces the EC2 instance (**new public IP**):

```bash
mise run plan    # Should show: 1 to add, 0 to change, 1 to destroy (EC2 replaced) + OpenSearch added
```

Use `AskUserQuestion` to confirm before applying — the EC2 instance will be replaced (new IP). All Docker state is lost — Postgres data, Debezium connectors, and Redpanda topics will need to be re-seeded (Stage 4-5 steps).

```bash
mise run apply    # Replaces EC2 + adds OpenSearch (~10-15 min for OpenSearch)
```

After applying:
1. Capture new outputs: `mise run outputs`
2. Update `.env` with the new `EC2_PUBLIC_IP`, `KAFKA_BOOTSTRAP_SERVERS`, `POSTGRES_HOST`
3. Wait ~2 min for cloud-init (Docker containers start automatically)
4. Re-seed Postgres: `PGPASSWORD=postgres psql -h $POSTGRES_HOST -U postgres -d financial_risk -f data/seed.sql`
5. Re-register Debezium: `curl -X POST http://$EC2_PUBLIC_IP:8083/connectors -H "Content-Type: application/json" -d @infra/debezium-connector.json`
6. Update `databricks.yml` unified target with the new Kafka IP

#### Why OpenSearch is Public-Access

OpenSearch is provisioned **without a VPC attachment** (public endpoint). This is required because:
- Databricks serverless pipelines run in Databricks-managed VPCs — they can't reach VPC-internal AWS resources
- The EC2-based PySpark sink also needs to reach OpenSearch over HTTPS
- In production with VPC-based OpenSearch, use a managed cluster with VPC peering/PrivateLink instead of serverless

#### 2a — Enable OpenSearch in Terraform

```bash
cd infra
```

Update `terraform.tfvars` to enable OpenSearch:

```hcl
enable_opensearch = true
opensearch_master_password = "Admin1234!"  # Or ask the user for a custom password
```

Plan and apply:

```bash
mise run plan    # Should show new resources: OpenSearch domain (no VPC security group)
```

Present the plan summary and use `AskUserQuestion` to confirm before applying:

> **Warning:** OpenSearch domains take **10–15 minutes** to provision. Combined with the EC2 upgrade, AWS billing increases to ~$0.076/hr. Proceed?

```bash
mise run apply:opensearch   # ~10-15 minutes
```

After provisioning, capture the outputs:

```bash
cd infra && mise run outputs
```

Present the outputs:

| Output | Value |
|--------|-------|
| opensearch_endpoint | `https://search-silveraiwolf-streaming-gold-xxxx.us-east-1.es.amazonaws.com` |
| opensearch_dashboard | `https://search-silveraiwolf-streaming-gold-xxxx.us-east-1.es.amazonaws.com/_dashboards` |

#### 2b — Update .env with OpenSearch Config

Update `.env` with the OpenSearch endpoint and credentials:

```bash
OPENSEARCH_ENDPOINT=<endpoint from terraform output — without https://>
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Admin1234!
```

#### 2c — Why NOT an In-Pipeline OpenSearch Sink

Explain to the user: we investigated running the OpenSearch sink **inside** the Databricks serverless pipeline and hit several hard limitations:

| Approach Tried | Result | Why |
|---------------|--------|-----|
| Maven JAR (`opensearch-hadoop`) | **Blocked** | JVM libraries not allowed on serverless SDP |
| `foreachPartition` + `opensearch-py` | **Blocked** | `PY4J_BLOCKED_API` — RDD access denied on serverless |
| `toPandas()` + `opensearch-py` | **Blocked** | Uses `.rdd` internally — same PY4J error |
| `collect()` + `opensearch-py` | Works but impractical | Materialized view caching prevents re-execution |
| `environment.dependencies` (PyPI) | **Works** | Set via pipeline REST API, not `databricks.yml` |

**The production-ready pattern:** Serverless SDP handles **pure transforms** (Bronze → Silver → Gold). OpenSearch indexing runs as a **separate PySpark process on EC2** that reads Gold tables via JDBC and writes via `opensearch-hadoop`.

#### 2d — The EC2-Based PySpark Sink Architecture

```
  Databricks (serverless SDP)              EC2 Docker Compose
 ┌────────────────────────────┐          ┌──────────────────────────────────┐
 │ unified_risk pipeline      │          │ opensearch-sink (PySpark)        │
 │  Bronze → Silver → Gold    │   JDBC   │  spark.read.format("jdbc")      │
 │  (pure transforms)         │────────→│  df.write.format("opensearch")  │
 │  No side-effects           │          │  via opensearch-hadoop JAR       │
 └────────────────────────────┘          │                                  │
                                         │  Also writes sync stats back:    │
                                         │  gold_opensearch_sync via JDBC   │
                                         └──────────────┬─────────────────┘
                                                        │ opensearch-hadoop
                                                        ▼
                                                   OpenSearch (10 indices)
```

**How it works:**
- PySpark runs locally on EC2 (`local[*]` mode) with two JARs: Databricks JDBC driver + opensearch-hadoop
- `spark.read.format("jdbc")` reads each Gold table from the Databricks SQL warehouse
- `df.write.format("opensearch")` writes to OpenSearch — JVM-to-JVM, no Python serialization
- After syncing all 10 Gold tables, writes stats back to `gold_opensearch_sync` via JDBC
- Runs on a configurable interval (default: 15 min) or one-shot for backfill

**Why PySpark on EC2 instead of a Python REST client?**
- `df.write.format("opensearch")` is distributed — Spark partitions push data in parallel
- No manual serialization — Spark handles type conversion natively
- Production-scalable — works for hundreds to millions of rows
- Same `opensearch-hadoop` connector used in Databricks classic compute pipelines

The sink code is at `infra/opensearch-sink/sink.py`. Walk through the key parts:
- `GOLD_TO_INDEX` — maps all 10 Gold tables to OpenSearch indices with ID fields
- `ARRAY_CAST_QUERIES` — handles tables with ARRAY columns (JDBC can't read Databricks ARRAY types, so we push down a CAST to STRING server-side)
- `write_sync_stats()` — writes sync results back to `gold_opensearch_sync` via JDBC for monitoring

Use `AskUserQuestion` to confirm understanding.

---

### Step 3 — Configure databricks.yml for Unified Pipeline

Comment out the 3 multi-pipeline definitions and enable the `unified_risk` pipeline. **No OpenSearch sink in the pipeline** — that runs on EC2.

```yaml
resources:
  pipelines:
    # --- Multi-pipeline (commented out for unified deployment) ---
    # app_streams: ...
    # data_fabric: ...
    # analytics: ...

    unified_risk:
      name: "Unified Risk Pipeline"
      catalog: ${var.catalog}
      target: ${var.unified_schema}
      serverless: true
      continuous: true
      configuration:
        pipeline.schema: ${var.unified_schema}
        pipeline.catalog: ${var.catalog}
        kafka_options.bootstrap_servers: ${var.kafka_bootstrap_servers}
        kafka_options.security_protocol: "PLAINTEXT"
      libraries:
        # === CDC Bronze (from Kafka) — 7 tables ===
        # === API Bronze (from Auto Loader) — 5 tables ===
        # === CDC Silver (APPLY CHANGES) — 8 tables ===
        # === API Silver (streaming transforms) — 5 tables ===
        # === Domain Gold (CDC + API) — 7 tables ===
        # === Cross-Domain Gold (inline) — 3 tables ===
        # (full library list from databricks.yml — all 35 files)
        # === NO OpenSearch sink — runs as Docker container on EC2 ===
```

**Notice:** The source files are **exactly the same** as the multi-pipeline approach — no code changes. The only difference is all libraries in one `libraries:` list.

Set the variables in the `unified` target:

```yaml
targets:
  unified:
    variables:
      kafka_bootstrap_servers: "<EC2_PUBLIC_IP>:19092"
      opensearch_endpoint: "<from terraform output>"
      opensearch_user: "admin"
      opensearch_password: "<from terraform.tfvars>"
```

---

### Step 4 — Create Landing Zone for Unified Schema + Seed Data

The unified pipeline writes to a separate schema (`financial_risk_unified_<username>`). Create its landing zone and seed it with the same Python batch jobs:

```bash
# Create schema + volumes for the unified pipeline
export UNIFIED_SCHEMA=financial_risk_unified_<username>

# Create schema
databricks api post /api/2.0/sql/statements --json '{"warehouse_id": "<WH>", "statement": "CREATE SCHEMA IF NOT EXISTS main.<UNIFIED_SCHEMA>", "wait_timeout": "50s"}'

# Create landing + checkpoints volumes
databricks api post /api/2.0/sql/statements --json '{"warehouse_id": "<WH>", "statement": "CREATE VOLUME IF NOT EXISTS main.<UNIFIED_SCHEMA>.landing", "wait_timeout": "50s"}'
databricks api post /api/2.0/sql/statements --json '{"warehouse_id": "<WH>", "statement": "CREATE VOLUME IF NOT EXISTS main.<UNIFIED_SCHEMA>.checkpoints", "wait_timeout": "50s"}'

# Create subdirectories
for dir in compliance/sanctions_watchlist compliance/kyc_records market_reference/exchange_rates market_reference/benchmark_rates regulatory/reporting_requirements; do
  databricks api put "/api/2.0/fs/directories/Volumes/main/<UNIFIED_SCHEMA>/landing/$dir"
done

# Run the 5 Python batch jobs with SCHEMA=$UNIFIED_SCHEMA
export CATALOG=main SCHEMA=$UNIFIED_SCHEMA
uv run python src/jobs/compliance/fetch_sanctions.py
uv run python src/jobs/compliance/fetch_kyc.py
uv run python src/jobs/market_reference/fetch_exchange_rates.py
uv run python src/jobs/market_reference/fetch_benchmark_rates.py
uv run python src/jobs/regulatory/fetch_reporting_requirements.py
```

---

### Step 5 — Deploy, Patch root_path, and Run

#### 5a — Stop ALL dev-target pipelines first

**Critical — Pipeline Quota:** The `unified` target deploys **all 4 pipeline definitions** (app_streams, data_fabric, analytics, unified_risk) as production-mode pipelines. Production pipelines auto-start, so they will all compete for the 1-pipeline quota on free/standard tiers. Stop **every** pipeline from the dev target before deploying:

```bash
# Stop all dev-target pipelines
for PID in $(databricks bundle summary --target dev --output json | python3 -c "
import sys, json
s = json.load(sys.stdin)
for p in s.get('resources',{}).get('pipelines',{}).values():
    print(p['id'])
"); do
  databricks pipelines stop $PID
done

# Also stop any unified-target pipelines from previous runs
for PID in $(databricks bundle summary --target unified --output json 2>/dev/null | python3 -c "
import sys, json
s = json.load(sys.stdin)
for p in s.get('resources',{}).get('pipelines',{}).values():
    print(p['id'])
" 2>/dev/null); do
  databricks pipelines stop $PID 2>/dev/null
done
```

#### 5b — Deploy the pipeline

```bash
databricks bundle deploy --target unified
```

After deploying, **immediately stop** the 3 non-unified pipelines that were created under the unified target (they auto-start in production mode):

```bash
# Get all unified-target pipeline IDs
databricks bundle summary --target unified --output json | python3 -c "
import sys, json
s = json.load(sys.stdin)
for name, p in s.get('resources',{}).get('pipelines',{}).items():
    print(f'{name}: {p[\"id\"]}')
"

# Stop app_streams, data_fabric, and analytics — keep only unified_risk
for PID in $APP_STREAMS_PID $DATA_FABRIC_PID $ANALYTICS_PID; do
  databricks pipelines stop $PID
done
```

#### 5c — Patch root_path (required after every deploy)

The Databricks bundle schema doesn't support `root_path` for pipelines, but the pipeline API does. Without it, the pipeline UI shows "No root folder defined". Patch it after every deploy:

```bash
PIPELINE_ID=$(databricks bundle summary --target unified --output json | python3 -c "import sys,json; s=json.load(sys.stdin); print(list(s['resources']['pipelines'].values())[0]['id'])")

# Read current spec, add root_path, PUT back
databricks api get "/api/2.0/pipelines/$PIPELINE_ID" | python3 -c "
import sys,json
d = json.load(sys.stdin)
spec = d['spec']
spec['root_path'] = spec['deployment']['metadata_file_path'].replace('/state/metadata.json', '/files')
with open('/tmp/ps.json','w') as f: json.dump(spec, f)
" && databricks api put "/api/2.0/pipelines/$PIPELINE_ID" --json @/tmp/ps.json
```

#### 5d — Wait for pipeline to process

The pipeline auto-starts in production mode. A continuous pipeline stays in `RUNNING` state forever — don't poll for `COMPLETED`.

```bash
# Poll until RUNNING
for i in $(seq 1 30); do
  state=$(databricks pipelines get $PIPELINE_ID --output json | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','UNKNOWN'))")
  echo "$(date +%H:%M:%S) — $state"
  if [ "$state" = "RUNNING" ]; then break; fi
  sleep 15
done

# Wait for Gold tables to materialize (~3-5 min after RUNNING)
sleep 180
```

#### 5e — Verify Gold tables

Query all 10 Gold tables from the unified schema:

```sql
SELECT 'gold_risk_dashboard' AS t, COUNT(*) FROM main.<unified_schema>.gold_risk_dashboard
UNION ALL SELECT 'gold_financial_ratios', COUNT(*) FROM main.<unified_schema>.gold_financial_ratios
UNION ALL SELECT 'gold_counterparty_health', COUNT(*) FROM main.<unified_schema>.gold_counterparty_health
UNION ALL SELECT 'gold_desk_overview', COUNT(*) FROM main.<unified_schema>.gold_desk_overview
UNION ALL SELECT 'gold_portfolio_summary', COUNT(*) FROM main.<unified_schema>.gold_portfolio_summary
UNION ALL SELECT 'gold_compliance_status', COUNT(*) FROM main.<unified_schema>.gold_compliance_status
UNION ALL SELECT 'gold_reference_rates', COUNT(*) FROM main.<unified_schema>.gold_reference_rates
UNION ALL SELECT 'gold_regulatory_metrics', COUNT(*) FROM main.<unified_schema>.gold_regulatory_metrics
UNION ALL SELECT 'gold_regulatory_report', COUNT(*) FROM main.<unified_schema>.gold_regulatory_report
UNION ALL SELECT 'gold_desk_pnl_exposure', COUNT(*) FROM main.<unified_schema>.gold_desk_pnl_exposure
```

All 10 Gold tables should be populated.

---

### Step 6 — Deploy and Verify OpenSearch Sink

#### 6a — Upload sink files to EC2

```bash
scp -i <key_path> -r infra/opensearch-sink ec2-user@$EC2_PUBLIC_IP:~/cdc-stack/opensearch-sink
scp -i <key_path> infra/docker-compose.yml ec2-user@$EC2_PUBLIC_IP:~/cdc-stack/docker-compose.yml
```

#### 6b — Create .env on EC2

```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cat > ~/cdc-stack/.env << 'EOF'
DATABRICKS_HOST=<workspace_url>
DATABRICKS_TOKEN=<token>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse_id>
CATALOG=main
SCHEMA=financial_risk_unified_<username>
OPENSEARCH_ENDPOINT=<endpoint without https://>
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=<password>
SINK_INTERVAL_SECONDS=0
EC2_PUBLIC_IP=<ec2_ip>
EOF"
```

#### 6c — Build and test (one-shot)

```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && docker build -t opensearch-sink ./opensearch-sink"
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && docker run --rm --env-file .env opensearch-sink"
```

Expected output — all 10 Gold tables indexed:

```
[2026-03-27 16:58:37 UTC] Syncing Gold → OpenSearch
  gold_risk_dashboard              → risk-dashboard              20 docs
  gold_regulatory_report           → regulatory-report           20 docs
  gold_desk_pnl_exposure           → desk-pnl-exposure           12 docs
  gold_financial_ratios            → financial-ratios            20 docs
  gold_portfolio_summary           → portfolio-summary           45 docs
  gold_counterparty_health         → counterparty-health         20 docs
  gold_desk_overview               → desk-overview               12 docs
  gold_compliance_status           → compliance-status           20 docs
  gold_reference_rates             → reference-rates             14 docs
  gold_regulatory_metrics          → regulatory-metrics          11 docs
  Stats written to main.<schema>.gold_opensearch_sync
  Total: 194 docs indexed
```

#### 6d — Verify OpenSearch indices

```bash
curl -s -u $OPENSEARCH_USER:$OPENSEARCH_PASSWORD "https://$OPENSEARCH_ENDPOINT/_cat/indices?v" | grep -v "^\."
```

| OpenSearch Index | Document Count | Source Gold Table |
|-----------------|---------------|-------------------|
| risk-dashboard | ~20 | gold_risk_dashboard |
| financial-ratios | ~20 | gold_financial_ratios |
| regulatory-report | ~20 | gold_regulatory_report |
| desk-pnl-exposure | ~12 | gold_desk_pnl_exposure |
| portfolio-summary | ~45 | gold_portfolio_summary |
| counterparty-health | ~20 | gold_counterparty_health |
| desk-overview | ~12 | gold_desk_overview |
| compliance-status | ~20 | gold_compliance_status |
| reference-rates | ~14 | gold_reference_rates |
| regulatory-metrics | ~11 | gold_regulatory_metrics |

#### 6e — Verify sync stats in Databricks

```sql
SELECT * FROM main.<unified_schema>.gold_opensearch_sync ORDER BY gold_table
```

This table is written by the EC2 sink (not the pipeline). It tracks doc counts, status, and timestamps for each sync run.

#### 6f — Start continuous mode

```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && sed -i 's/SINK_INTERVAL_SECONDS=0/SINK_INTERVAL_SECONDS=900/' .env && docker compose up -d opensearch-sink"
```

Tell the user they can open **OpenSearch Dashboards** at the dashboard URL from Terraform outputs to create visualizations, saved searches, and alerts.

Use `AskUserQuestion` to confirm all tables and OpenSearch indices are populated.

---

### Step 7 — Compare: What's Different?

Present the comparison:

| Aspect | Multi-Pipeline (Stages 6–8) | Single Pipeline (this stage) |
|--------|---------------------------|------------------------------|
| Pipelines | 3 (app_streams, data_fabric, analytics) | 1 (unified_risk) |
| Pipeline quota usage | 3 slots (ran sequentially in free tier) | 1 slot |
| Cross-domain Gold freshness | Minutes (triggered on schedule) | Real-time (every micro-batch) |
| Serving layer | None (query Delta directly) | OpenSearch (search, dashboards, REST API) |
| OpenSearch sink | N/A | PySpark on EC2 via JDBC + opensearch-hadoop (every 15 min) |
| Fault isolation | High — Kafka failure doesn't affect API pipeline | DAG-aware — unrelated tables complete, pipeline pauses new micro-batches |
| Compute efficiency | Higher — no wasted cross-domain joins | Lower — re-joins on every batch |
| DAG visibility | Split across 3 pipeline UIs | One unified DAG in one UI |
| Code changes needed | None | None — same source files, different `databricks.yml` |
| Best for | Independent teams, different data cadences | Single team, real-time cross-domain analytics |

**The takeaway:** The architecture choice is in the **deployment config**, not the code. The same `@sp.table` definitions work in both designs. You choose based on your freshness requirements, team structure, and cost tolerance.

**Key insight — serverless SDP limitations for external sinks:**
Serverless SDP is designed for pure transforms. External writes (OpenSearch, Elasticsearch, Redis) require a separate process because:
1. Maven JARs are blocked (no JVM connectors)
2. RDD-level APIs are blocked (`foreachPartition`, `toPandas`)
3. The production pattern is: pipeline writes to Delta, separate process reads Delta and sinks externally

In production with a Databricks Enterprise tier, you could use a classic-compute pipeline or Databricks Connect with a managed cluster — both support Maven JARs and RDD APIs. The EC2 Docker approach in this tutorial is the free-tier equivalent.

---

### Step 8 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| Unified pipeline | Running (continuous) | 35 tables: 12 Bronze + 13 Silver + 10 Gold |
| OpenSearch domain | Provisioned | `t3.small.search`, HTTPS, public-access |
| OpenSearch sink | Running (EC2 Docker, every 15 min) | PySpark JDBC + opensearch-hadoop, 10 Gold tables |
| Gold → OpenSearch | 10 indices, ~194 docs | All Gold tables indexed |
| `gold_opensearch_sync` | Updated | Sync stats + timestamps written back via JDBC |
| Cross-domain Gold | Real-time | risk_dashboard updated in same micro-batch as CDC changes |
| Code changes | None | Same source files, different databricks.yml |
| Multi-pipeline | Destroyed (clean slate) | Can be redeployed with `--target dev` |
| **Total AWS cost** | | **~$0.076/hr** (EC2 t3.medium $0.04 + OpenSearch $0.036) |

**Key learnings:**

1. **Multi-pipeline vs single-pipeline is a deployment decision, not a code decision** — same `@sp.table` definitions work in both
2. **Serverless SDP = pure transforms only** — no Maven JARs, no RDD APIs, no external writes
3. **OpenSearch sink runs on EC2** — PySpark with JDBC (read) + opensearch-hadoop (write), JVM-to-JVM, production-scalable
4. **`gold_opensearch_sync` for monitoring** — the EC2 sink writes stats back to Databricks via JDBC after each sync
5. **`root_path` must be patched via API** — bundle schema doesn't support it, but the pipeline API accepts it
6. **ARRAY columns need special handling** — JDBC can't read Databricks ARRAY types; push down `CAST(col AS STRING)` server-side
7. **Choose based on your needs:**
   - **Single pipeline** — single team, real-time cross-domain, prototyping
   - **Multi-pipeline** — independent teams, operational clarity, production
   - **Enterprise tier** — classic compute pipelines can use Maven JARs for in-pipeline OpenSearch sinking

**Next:** Run `/silver-databricks-streaming:simulate-changes` to INSERT/UPDATE/DELETE in Postgres, re-run batch jobs, and watch live changes flow through the running unified pipeline all the way to OpenSearch.
