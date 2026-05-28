[Stage 0] Show all available silver-databricks-streaming commands and skills. Do NOT run any of them. Display ALL content below VERBATIM — do not summarize, condense, or reformat. Output every section exactly as written.

---

# SilverAIWolf's Databricks Streaming Tutorial (Advanced)

### Real-Time Multi-Pipeline Monorepo — CDC + API Ingestion → OpenSearch

> **The Scenario:** You've already built the batch medallion pipeline (silver-databricks-batch tutorial).
> Now the risk department wants **real-time** data AND enrichment from external APIs. When a trader
> executes a transaction, updates a counterparty record, or new market prices arrive — the CDC
> pipeline should reflect those changes within seconds. Meanwhile, compliance data, exchange rates,
> benchmark rates, and regulatory requirements arrive from external APIs via scheduled Python jobs
> that land files for Auto Loader to pick up.
>
> You'll build this pipeline **two ways**:
> 1. **Multi-pipeline monorepo** — 3 separate Databricks pipelines (`app_streams`, `data_fabric`, `analytics`), 5 Python batch jobs, and a cross-domain analytics layer, all deployed from a single `databricks.yml` Asset Bundle
> 2. **Unified single pipeline** — everything (Bronze + Silver + Gold across all domains) in one fully real-time pipeline, with a **PySpark Docker container on EC2** reading Gold tables via JDBC and writing to **AWS OpenSearch** via the `opensearch-hadoop` Spark connector for search, dashboards, and REST API access
>
> Both approaches use the same infrastructure, the same CDC + API sources, and the same medallion
> architecture — the difference is how you organize the pipelines. The unified pipeline adds OpenSearch
> as the serving layer, provisioned via Terraform and indexed by a PySpark sink on EC2.
> Switching between the two requires only configuration changes (`databricks.yml`), not code changes —
> the same pipeline definitions and transformations work in both setups. You'll compare the
> trade-offs firsthand.

---

### Architecture

```
  OLTP Source              CDC Layer               Streaming Broker         Databricks Pipelines
 ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────────────────────┐
 │  PostgreSQL  │────>│   Debezium   │────>│     Redpanda     │     │  app_streams (continuous)    │
 │  (EC2)       │     │   (CDC)      │     │  (Kafka-compat)  │     │   readStream("kafka")        │
 │              │     │              │     │                  │────>│   7 CDC topics ─> B ─> S ─> G │
 │  7 tables:   │     │  captures:   │     │  7 topics:       │     │   3 domains: financial,       │
 │  financial   │     │   INSERT     │     │   .transactions  │     │     counterparty, operations   │
 │  counterparty│     │   UPDATE     │     │   .market_prices │     └──────────────────────────────┘
 │  operations  │     │   DELETE     │     │   .counterparties│
 └──────────────┘     └──────────────┘     │   .credit_ratings│     ┌──────────────────────────────┐
                                           │   .office_locs   │     │  data_fabric (continuous)    │
  External APIs                            │   .trading_desks │     │   readStream("cloudFiles")   │
 ┌──────────────┐                          │   .desk_assigns  │     │   5 Auto Loader tables       │
 │ Compliance   │                          └──────────────────┘     │   3 domains: compliance,      │
 │ Market Ref   │     Python Jobs (scheduled)                       │     market_ref, regulatory     │
 │ Regulatory   │────>┌──────────────────┐  Landing Zone            └──────────────────────────────┘
 │              │     │ fetch_sanctions  │──> /Volumes/.../   │
 │  5 API       │     │ fetch_kyc        │     landing/       │────>┌──────────────────────────────┐
 │  endpoints   │     │ fetch_exchange   │     *.json         │     │  analytics (triggered)       │
 └──────────────┘     │ fetch_benchmark  │                    │     │   Cross-domain Gold           │
                      │ fetch_regulatory │                    │     │   Reads from app_streams +    │
                      └──────────────────┘                    │     │     data_fabric Silver tables  │
                                                                    └──────────────────────────────┘

                                                                    ┌──────────────────────────────┐
                                                                    │  OpenSearch (serving layer)   │
                                                                    │   EC2 PySpark sink reads       │
                                                                    │   Gold via JDBC, writes via    │
                                                                    │   opensearch-hadoop (Stage 9)  │
                                                                    │   Search, dashboards, REST API │
                                                                    └──────────────────────────────┘
       EC2 instance (Docker Compose + PySpark)    Databricks Cloud (3 pipelines + 3 jobs)
                                                  + AWS OpenSearch (search & dashboards)
```

---

### Redpanda vs Production Kafka

> **Redpanda** is used in this tutorial as a lightweight, Kafka-compatible broker.
> It requires no JVM, no ZooKeeper, runs on a `t3.small` EC2, and starts in seconds.
> Your Databricks pipeline code (`readStream.format("kafka")`) is **identical** whether
> the broker is Redpanda, Apache Kafka, Confluent Cloud, or AWS MSK.
>
> **For production**, use a managed service — Confluent Cloud, AWS MSK, or Azure Event Hubs.
> The only change is connection config + auth. See Stage 13 (Production Notes) for the exact diff.

---

### Prerequisites

Before running any stage, make sure you have:

1. **Databricks account** — With Unity Catalog enabled
2. **AWS account** — For provisioning EC2 (free tier eligible: `t3.small`)
3. **AWS CLI configured** — SSO profile recommended; Stage 1 will refresh your token and verify with `aws sts get-caller-identity`
4. **Terraform** — Managed via `mise install` (no manual install needed)
5. **SSH key pair** — For EC2 access; the setup skill can generate one
6. **Python 3.10+** and **uv** — For dependency management and batch jobs

---

### Cost Awareness

Infrastructure is provisioned **just-in-time** — you only pay for what you're using. The tutorial is designed so you can pause between sessions and tear down infra to stop charges.

| Stage | AWS Cost | What's Running |
|-------|----------|---------------|
| 1–2 | **$0** | Local only + Databricks (free tier) |
| 3 | **~$0.02/hr starts** | EC2 t3.small provisioned (Postgres + Debezium + Redpanda) |
| 4–8 | **~$0.02/hr** | EC2 still running |
| 9 | **~$0.076/hr starts** | EC2 upgraded to t3.medium (PySpark sink needs 4GB) + OpenSearch provisioned (~10-15 min) |
| 10 | **~$0.076/hr** | Simulate changes — infra still running |
| 11 | **~$0.076/hr** | Backfill OpenSearch — infra still running |
| 12 | **~$0.076/hr** | Reading — but infra still running |
| 14 (cleanup) | **$0** | Everything destroyed |

> **Total if done in one sitting (8 hours):** ~$0.50
> **Total if spread over a week:** ~$12
> **If you forget to cleanup for a month:** ~$55 (EC2 t3.medium $28 + OpenSearch $27)
>
> **Tip:** Run `/silver-databricks-streaming:cleanup` when you're done for the day. Everything is idempotent — you can re-provision and resume.
>
> **Important:** Even after running cleanup, it's good practice to verify in the AWS Console and Databricks workspace that all resources have been fully removed. Automated teardown can occasionally leave orphaned resources (e.g., a security group with a dependency, an OpenSearch domain still deleting). A quick manual check ensures you're not accumulating surprise charges.

---

### Stages

| Stage | Skill | What It Does |
|-------|-------|-------------|
| 1 | `/silver-databricks-streaming:infra-setup` | Scaffold project, install tools, configure Databricks auth |
| 2 | `/silver-databricks-streaming:deploy-dev` | Create Unity Catalog schema + landing zone volumes |
| 3 | `/silver-databricks-streaming:infra-cdc` | Provision EC2 (Postgres + Debezium + Redpanda) via Terraform |
| 4 | `/silver-databricks-streaming:seed-postgres` | Create ALL Postgres tables (7 tables), insert seed data, register Debezium |
| 5 | `/silver-databricks-streaming:verify-cdc` | Verify CDC events for all 7 topics |
| 6 | `/silver-databricks-streaming:stream-bronze` | Deploy ALL Bronze — CDC (Kafka) + API (Auto Loader) across 2 pipelines |
| 7 | `/silver-databricks-streaming:stream-silver` | Deploy ALL Silver — CDC (APPLY CHANGES) + API (streaming transforms) |
| 8 | `/silver-databricks-streaming:stream-gold` | Deploy ALL Gold — domain-specific + cross-domain analytics pipeline |
| 9 | `/silver-databricks-streaming:stream-unified` | Deploy unified pipeline (production/continuous) + provision OpenSearch + PySpark JDBC sink on EC2 |
| 10 | `/silver-databricks-streaming:simulate-changes` | INSERT/UPDATE/DELETE in Postgres + re-run batch jobs, watch live changes flow through unified pipeline to OpenSearch |
| 11 | `/silver-databricks-streaming:backfill-opensearch` | Run standalone backfill job to repopulate OpenSearch from existing Gold tables — no pipeline recomputation |
| 12 | `/silver-databricks-streaming:production-notes` | Redpanda → managed Kafka, EC2 → RDS, job scheduling, OpenSearch scaling |
| 13 | `/silver-databricks-streaming:cleanup` | Tear down EC2 + OpenSearch + all Databricks pipelines |

---

### Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Infrastructure | **Terraform** (via mise) | Provision EC2, security groups, IAM |
| OLTP Database | **PostgreSQL 16** | Source of truth — WAL-based CDC (7 tables) |
| Change Data Capture | **Debezium 2.x** | Captures INSERT/UPDATE/DELETE from Postgres WAL |
| Streaming Broker | **Redpanda** (Kafka-compatible) | Lightweight topic-based message broker |
| Container Runtime | **Docker Compose** | Runs Postgres + Debezium + Redpanda on EC2 |
| Pipeline Framework | **Spark Declarative Pipelines** | Serverless streaming transformations (3 pipelines) |
| Auto Loader | **cloudFiles** format | Incremental file ingestion for API data |
| Batch Jobs | **Python + Databricks SDK** | 5 scheduled jobs fetching from external APIs |
| Deployment | **Databricks Asset Bundles** | Declarative pipeline + job deployment (monorepo) |
| Data Quality | **`@sp.expect` / `@sp.expect_or_drop`** | Runtime expectations on streaming data |
| Search & Dashboards | **AWS OpenSearch** (`t3.small.search`) | Full-text search, dashboards, alerting on Gold data |
| OpenSearch Connector | **opensearch-hadoop** (`opensearch-spark-40_2.13:2.0.0`) | Spark-native connector — PySpark on EC2 reads Gold via JDBC, writes to OpenSearch via `df.write.format("opensearch")` |
| Task Runner | **mise** | Tool management + task runner |
| Package Manager | **uv** | Python dependency management |

---

### What You'll Build

| Aspect | Details |
|--------|---------|
| Data sources | PostgreSQL CDC (7 tables) + External APIs (5 endpoints) |
| Ingestion | `readStream("kafka")` for CDC + `readStream("cloudFiles")` for API data |
| Latency | Seconds (CDC), minutes (API jobs) |
| Infrastructure | EC2 (Postgres + Debezium + Redpanda) + Databricks + OpenSearch |
| Domains | 6: financial, counterparty, operations, compliance, market_ref, regulatory |
| Change handling | INSERT + UPDATE + DELETE (CDC) + append (API) |
| Serving layer | OpenSearch for search, dashboards, and REST API |

**Two deployment approaches — same data, same medallion layers:**

| | Multi-Pipeline (Stages 6–8) | Unified Pipeline (Stage 10) |
|---|---|---|
| Pipelines | 3: `app_streams`, `data_fabric`, `analytics` | 1: single pipeline with all layers |
| Jobs | 5 Python batch jobs across 3 job definitions | Same jobs, single pipeline consumer |
| Triggers | Continuous (CDC + API) + triggered (analytics) | Fully real-time, single continuous pipeline |
| Cross-domain | Separate analytics pipeline joins across domains | Cross-domain Gold tables in the same pipeline |
| OpenSearch | Not included | EC2 PySpark sink reads Gold via JDBC, writes via `opensearch-hadoop` (every 15 min) |
| Trade-off | Isolation, independent scaling, team ownership | Simplicity, end-to-end real-time pipeline + search serving layer |
| Key learning | Multi-pipeline monorepo patterns | Unified pipeline + serverless limitations + EC2-based OpenSearch sink |

---

### Tutorial Progress

| Stage | Skill | Status |
|-------|-------|--------|
| 0 | start | ✓ |
| 1 | infra-setup | ← next |
| 2 | deploy-dev | |
| 3 | infra-cdc | |
| 4 | seed-postgres | |
| 5 | verify-cdc | |
| 6 | stream-bronze | |
| 7 | stream-silver | |
| 8 | stream-gold | |
| 9 | stream-unified | |
| 10 | simulate-changes | |
| 11 | backfill-opensearch | |
| 12 | production-notes | |
| 13 | cleanup | |

---

After displaying all content above, ask the user if they'd like to proceed to **Stage 1 — infra-setup**. Use `AskUserQuestion` with these options:

1. **"Yes, run Stage 1 now (Recommended)"** — description: "Runs `/silver-databricks-streaming:infra-setup` to scaffold the project, install tools, and configure Databricks auth"
2. **"No, I'll run it manually"** — description: "You can run `/silver-databricks-streaming:infra-setup` whenever you're ready"

If the user selects option 1, invoke the `silver-databricks-streaming:infra-setup` skill automatically using the Skill tool.
