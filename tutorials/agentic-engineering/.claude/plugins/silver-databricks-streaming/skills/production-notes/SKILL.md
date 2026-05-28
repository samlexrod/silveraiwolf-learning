---
description: "[Stage 12] What changes for production: managed Kafka, job scheduling, API auth, OpenSearch, multi-pipeline monitoring"
---

# Production Notes — From Tutorial to Production

What changes when moving from Redpanda on EC2 to a production-grade multi-pipeline architecture. The key insight: **your pipeline code doesn't change — only infrastructure, scheduling, and auth config**.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

The learner has completed the full streaming tutorial:
- EC2 running Postgres + Debezium + Redpanda (Docker Compose)
- 3 Databricks pipelines with 35+ streaming tables
- 5 Python batch jobs feeding the data_fabric pipeline
- Verified INSERT/UPDATE/DELETE + job re-runs end-to-end

Now: what does production look like?

---

## Instructions

---

### Step 1 — The Production Architecture

```
  OLTP Source              CDC Layer                Managed Streaming         Databricks
 ┌──────────────┐     ┌──────────────┐     ┌────────────────────┐     ┌──────────────────────┐
 │ Amazon RDS   │────>│ Debezium on  │────>│ Confluent Cloud    │     │ app_streams pipeline │
 │ (PostgreSQL) │     │ ECS/Fargate  │     │  or AWS MSK        │────>│ (continuous)          │
 │ Multi-AZ     │     │ Auto-scaling │     │  or Azure Event    │     │                      │
 │ Encrypted    │     │ Health checks│     │    Hubs             │     │ Same code as         │
 └──────────────┘     └──────────────┘     └────────────────────┘     │ tutorial!            │
                                                                       ├──────────────────────┤
  External APIs                                                        │ data_fabric pipeline │
 ┌──────────────┐     Databricks Workflows                             │ (continuous)          │
 │ Compliance   │────>┌──────────────────┐   Landing Zone              │                      │
 │ Market Ref   │     │ Scheduled jobs   │──>/Volumes/.../──────────>│ Same code as         │
 │ Regulatory   │     │ OAuth/API keys   │   landing/                │ tutorial!            │
 │              │     │ via Secret Scopes│                            ├──────────────────────┤
 │ mTLS / OAuth │     └──────────────────┘                            │ analytics pipeline   │
 └──────────────┘                                                      │ (triggered/scheduled)│
                                                                       └──────────────────────┘
```

Use `AskUserQuestion` to confirm understanding.

---

### Step 2 — What Changes: The Kafka Diff

The entire change from tutorial to production for Kafka is **connection config**:

#### Tutorial (Redpanda on EC2)

```python
kafka_options.bootstrap_servers: "44.201.xxx.xxx:9092"
kafka_options.security_protocol: "PLAINTEXT"
```

#### Production — Confluent Cloud

```python
kafka_options.bootstrap_servers: "pkc-xxxxx.us-east-1.aws.confluent.cloud:9092"
kafka_options.security_protocol: "SASL_SSL"
kafka_options.sasl_mechanism: "PLAIN"
kafka_options.sasl_username: "{{secrets/streaming/confluent-api-key}}"
kafka_options.sasl_password: "{{secrets/streaming/confluent-api-secret}}"
```

#### Production — AWS MSK (IAM Auth)

```python
kafka_options.bootstrap_servers: "b-1.financial-risk.xxxxx.c2.kafka.us-east-1.amazonaws.com:9098"
kafka_options.security_protocol: "SASL_SSL"
kafka_options.sasl_mechanism: "AWS_MSK_IAM"
kafka_options.sasl_jaas_config: "software.amazon.msk.auth.iam.IAMLoginModule required;"
```

Present this as a comparison table:

| Config | Tutorial | Confluent Cloud | AWS MSK |
|--------|----------|----------------|---------|
| Bootstrap servers | EC2 IP:9092 | Confluent URL:9092 | MSK URL:9098 |
| Security protocol | PLAINTEXT | SASL_SSL | SASL_SSL |
| Auth mechanism | None | API key/secret | IAM |
| Pipeline code | Same | Same | Same |
| Encryption in transit | No | Yes (TLS) | Yes (TLS) |

Use `AskUserQuestion` to confirm understanding.

---

### Step 3 — Job Scheduling in Production

#### Tutorial
- Manual `databricks bundle run` triggers
- No authentication to external APIs (mock/sample data)

#### Production — Databricks Workflows

The job definitions in `databricks.yml` are already production-ready — they define cron schedules:

| Job | Cron Expression | Schedule |
|-----|----------------|----------|
| compliance_daily | `0 0 6 * * ?` | Daily at 6:00 AM UTC |
| market_reference_hourly | `0 0 * * * ?` | Every hour on the hour |
| regulatory_hourly | `0 30 * * * ?` | Every hour at :30 |

**In production, enable the schedules:**

```yaml
targets:
  prod:
    resources:
      jobs:
        compliance_daily:
          schedule:
            pause_status: UNPAUSED    # Enable the schedule
        market_reference_hourly:
          schedule:
            pause_status: UNPAUSED
        regulatory_hourly:
          schedule:
            pause_status: UNPAUSED
```

**Job alerting:**

```yaml
resources:
  jobs:
    compliance_daily:
      email_notifications:
        on_failure:
          - ops-team@company.com
        on_duration_warning_threshold_exceeded:
          - ops-team@company.com
      health:
        rules:
          - metric: RUN_DURATION_SECONDS
            op: GREATER_THAN
            value: 600    # Alert if job takes > 10 minutes
```

---

### Step 4 — API Authentication Patterns

#### Tutorial
- No auth (mock APIs or public endpoints)

#### Production — Databricks Secret Scopes

Store API credentials in Databricks Secret Scopes, referenced in job code:

```python
# In src/jobs/compliance/fetch_sanctions.py (production)
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
api_key = w.dbutils.secrets.get(scope="api-credentials", key="compliance-api-key")

response = requests.get(
    "https://api.compliance-provider.com/v2/sanctions",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=30,
)
```

**Set up secret scopes:**

```bash
# Create scope
databricks secrets create-scope api-credentials

# Store API keys
databricks secrets put-secret api-credentials compliance-api-key
databricks secrets put-secret api-credentials market-data-api-key
databricks secrets put-secret api-credentials regulatory-api-key
```

| API | Auth Method | Secret Scope Key |
|-----|------------|-----------------|
| Compliance (sanctions) | OAuth2 client credentials | `compliance-api-key` |
| Compliance (KYC) | API key header | `compliance-api-key` |
| Market reference (FX rates) | API key query param | `market-data-api-key` |
| Market reference (benchmarks) | API key header | `market-data-api-key` |
| Regulatory | mTLS + API key | `regulatory-api-key` + cert in scope |

---

### Step 5 — Networking

#### Tutorial
- EC2 security group allows Databricks NAT IPs on port 9092
- Public internet traffic

#### Production
- **VPC Peering** or **AWS PrivateLink** between Databricks VPC and MSK/Confluent VPC
- No public internet exposure
- Private DNS resolution

```
  Databricks VPC                     MSK VPC
 ┌──────────────────┐              ┌──────────────────┐
 │ Pipeline compute │              │ MSK brokers      │
 │                  │── Peering ──>│                  │
 │ NAT gateway      │  or          │ Private subnet   │
 │                  │  PrivateLink │                  │
 └──────────────────┘              └──────────────────┘
       No public internet
```

---

### Step 6 — Multi-Pipeline Monitoring

#### Tutorial
- Manual verification (SQL queries, `rpk topic consume`)
- No alerts

#### Production — 3 Pipelines + 3 Jobs to Monitor

| What to Monitor | Where | Alert Threshold |
|----------------|-------|-----------------|
| Kafka consumer lag | Confluent / MSK CloudWatch | > 10,000 messages |
| Debezium connector status | Connect REST / CloudWatch | State != RUNNING |
| app_streams pipeline state | Databricks API | State != RUNNING |
| app_streams streaming lag | DLT event log | > 5 minutes behind |
| data_fabric pipeline state | Databricks API | State != RUNNING |
| data_fabric streaming lag | DLT event log | > 5 minutes behind |
| analytics pipeline state | Databricks API | Last run > 1 hour ago |
| Job run failures | Databricks Workflows | Any FAILURE state |
| Job duration | Databricks Workflows | > 2x average duration |
| Replication slot WAL size | RDS CloudWatch | > 1GB |
| Data quality expectations | DLT event log | Any FAIL count > 0 |
| Landing zone file count | Volume monitoring | No new files in 2x schedule |

```sql
-- Example: SQL alert for expectation failures across all 3 pipelines
SELECT
  details:expectation_name AS expectation,
  details:dataset AS table_name,
  details:num_failing_records AS failures
FROM event_log(TABLE(main.financial_risk_streaming))
WHERE event_type = 'flow_progress'
  AND details:num_failing_records > 0
  AND timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR;
```

---

### Step 7 — Landing Zone Management

#### Tutorial
- Files accumulate indefinitely
- No archiving or cleanup

#### Production

| Concern | Solution |
|---------|----------|
| File retention | Auto-archive to S3 Glacier after 30 days |
| File cleanup | Delete processed files after 90 days |
| File naming | Timestamp-based: `{source}_{YYYY-MM-DD_HHmmss}.json` |
| Duplicate detection | Auto Loader tracks processed files — no duplicates |
| Failed files | Move to `/landing/dead_letter/` for manual review |
| File size | Target 10-100MB per file for optimal Auto Loader performance |

```python
# In production job code — structured file naming
import datetime

timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
output_path = f"/Volumes/.../landing/exchange_rates/{timestamp}_fetch.json"
```

---

### Step 8 — Debezium and PostgreSQL in Production

#### Debezium

| Option | Pros | Cons |
|--------|------|------|
| **Confluent managed connector** | Fully managed, monitoring | Confluent-only |
| **Debezium on ECS/Fargate** | Auto-restart, CloudWatch | AWS ops overhead |
| **MSK Connect** | Managed Kafka Connect on MSK | MSK-only |

#### PostgreSQL

- **Amazon RDS PostgreSQL** or **Aurora PostgreSQL**
- Multi-AZ, automated backups, encryption
- **Critical setting:** `rds.logical_replication = 1`

---

### Step 9 — Secrets Management

#### Tutorial
- `.env` file with plaintext credentials

#### Production
- **Databricks Secret Scopes** for pipeline and job credentials:
  ```bash
  databricks secrets create-scope streaming
  databricks secrets put-secret streaming confluent-api-key
  databricks secrets put-secret streaming confluent-api-secret
  ```
- **AWS Secrets Manager** for Debezium connector credentials
- **No plaintext credentials anywhere**

---

### Step 10 — Cost Considerations

| Component | Tutorial Cost | Production Cost (Estimate) |
|-----------|-------------|--------------------------|
| EC2 (`t3.small`) | ~$0.02/hr ($15/mo) | N/A (replaced by managed services) |
| OpenSearch (`t3.small.search`) | ~$0.036/hr ($27/mo) | ~$200-500/mo (multi-AZ, larger instances) |
| Databricks serverless (3 pipelines) | Pay per DBU | Same (scales with throughput) |
| Confluent Cloud / MSK | N/A | ~$200-800/mo |
| RDS PostgreSQL | N/A | ~$50-200/mo |
| Debezium (ECS) | N/A | ~$20-50/mo |
| Job compute (4 jobs) | Pay per DBU | ~$10-50/mo (short-lived tasks) |
| Landing zone storage | Negligible | ~$5-10/mo (JSON files, archived) |

---

### Step 11 — OpenSearch in Production

#### Tutorial
- `t3.small.search`, single node, no replicas, public access
- Full reindex via job (delete + recreate index)

#### Production

| Aspect | Tutorial | Production |
|--------|----------|-----------|
| Instance | `t3.small.search` × 1 | `r6g.large.search` × 3 (multi-AZ) |
| Replicas | 0 | 1 (one replica per shard) |
| Access | Public endpoint + basic auth | VPC endpoint + IAM/SAML |
| Indexing | Full reindex (delete + create) | Upsert by `_id` (incremental) |
| Index lifecycle | No management | ISM policies (hot → warm → delete) |
| Dashboards | Manual setup | Saved objects exported as JSON, deployed via API |

**For high-frequency updates** (risk dashboard refreshing every minute), consider:
- **OpenSearch Ingestion Pipeline** — managed pipeline that reads from Kafka topics directly (skip the Databricks job)
- **Delta CDF streaming** — read change data feed from Gold tables and incrementally upsert into OpenSearch

---

### Step 12 — Summary: Tutorial -> Production Checklist

| Area | Tutorial | Production | Change Required |
|------|----------|-----------|----------------|
| Kafka broker | Redpanda on EC2 | Confluent / MSK | Config only |
| Pipeline code | `readStream("kafka")` | `readStream("kafka")` | **None** |
| Auto Loader code | `readStream("cloudFiles")` | `readStream("cloudFiles")` | **None** |
| Job code | Manual trigger | Scheduled via Workflows | Enable schedules |
| API auth | None (mock data) | OAuth / API keys via Secret Scopes | Job code + secrets |
| Networking | Public IP | VPC peering / PrivateLink | Infrastructure |
| Kafka auth | PLAINTEXT | SASL_SSL + IAM/API keys | Config + secrets |
| PostgreSQL | Docker on EC2 | RDS / Aurora | Infrastructure |
| Debezium | Docker Compose | Managed connector / ECS | Infrastructure |
| OpenSearch | `t3.small.search` × 1 | `r6g.large.search` × 3 multi-AZ | Infrastructure |
| Monitoring | Manual queries | CloudWatch + SQL alerts | New setup |
| Secrets | `.env` plaintext | Secret Scopes | Migration |
| Landing zone | No management | Archiving + cleanup | New setup |
| Job alerting | None | Email + PagerDuty | New setup |

**Bottom line:** Your pipeline code, job definitions, and indexer are production-ready today. The gap is infrastructure (swap Redpanda for MSK, EC2 for RDS, scale OpenSearch), auth (add secret scopes), and monitoring (add alerts for 3 pipelines + 4 jobs).

**Next:** Run `/silver-databricks-streaming:cleanup` to tear down the tutorial infrastructure and all Databricks resources.
