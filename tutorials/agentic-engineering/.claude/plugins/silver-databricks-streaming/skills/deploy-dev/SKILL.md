---
description: "[Stage 2] Create Unity Catalog schema, landing zone volumes, and verify Databricks connectivity"
---

# Deploy Dev — Unity Catalog Landing Zone

Create the Unity Catalog schema and landing zone volumes on Databricks. This is zero-cost setup (Databricks free tier) — no AWS infrastructure is provisioned yet.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 1 (infra-setup), the learner has:
- Project scaffolded with all source code and config
- Tools installed (Terraform, AWS CLI, uv, etc.)
- Databricks CLI authenticated
- No AWS resources provisioned yet (that's Stage 3)

---

## Instructions

---

### Step 1 — Verify Databricks Auth

**Important:** Run Databricks CLI commands from `/tmp` or outside the project directory to avoid `databricks.yml` bundle config interference. Always `source .env && export DATABRICKS_HOST DATABRICKS_TOKEN` before running commands.

```bash
cd /tmp
source <project-dir>/.env
export DATABRICKS_HOST DATABRICKS_TOKEN
databricks workspace list /
```

Do NOT use `databricks auth env` — it fails when there's no DEFAULT profile in `.databrickscfg`. The `workspace list /` command is the reliable auth check.

---

### Step 2 — Discover SQL Warehouse + Dev Schema Name

First, find the warehouse ID:

```bash
databricks warehouses list
# Pick the warehouse ID from the output (it will auto-start if stopped)
```

Next, determine the **dev schema name**. The `databricks.yml` dev target appends a username suffix:

```yaml
# From databricks.yml
targets:
  dev:
    variables:
      schema: financial_risk_streaming_${workspace.current_user.short_name}
```

Get the current user's short name and construct the schema:

```bash
# Get the username from Databricks
databricks current-user me --output json | python3 -c "import sys,json; print(json.load(sys.stdin)['userName'].split('@')[0])"
```

The dev schema will be `financial_risk_streaming_<username>` (e.g., `financial_risk_streaming_samlexrod`). Use this for all subsequent commands.

Then create the schema. Use `wait_timeout: "50s"` (maximum allowed is 50 seconds):

```bash
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "CREATE SCHEMA IF NOT EXISTS main.<DEV_SCHEMA>", "wait_timeout": "50s"}'
```

**Note:** Do NOT use the `-n` flag — it does not exist in the Databricks CLI.

---

### Step 3 — Create Landing Zone Volume

The landing zone is where Python batch jobs write API data. Auto Loader watches these directories.

```bash
# Create the landing zone volume
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "CREATE VOLUME IF NOT EXISTS main.<DEV_SCHEMA>.landing", "wait_timeout": "50s"}'
```

Create subdirectories using the **Files API** (NOT `databricks fs mkdirs` — that doesn't work on Volumes):

```bash
for dir in compliance/sanctions_watchlist compliance/kyc_records market_reference/exchange_rates market_reference/benchmark_rates regulatory/reporting_requirements; do
  databricks api put "/api/2.0/fs/directories/Volumes/main/<DEV_SCHEMA>/landing/$dir"
done
```

Verify using the Files API (NOT `databricks fs ls`):

```bash
databricks api get "/api/2.0/fs/directories/Volumes/main/<DEV_SCHEMA>/landing/"
```

Present the landing zone structure:

```
/Volumes/main/<DEV_SCHEMA>/landing/
├── compliance/
│   ├── sanctions_watchlist/ ← fetch_sanctions.py writes here (daily)
│   └── kyc_records/         ← fetch_kyc.py writes here (daily)
├── market_reference/
│   ├── exchange_rates/     ← fetch_exchange_rates.py writes here (hourly)
│   └── benchmark_rates/    ← fetch_benchmark_rates.py writes here (hourly)
└── regulatory/
    └── reporting_requirements/  ← fetch_reporting_requirements.py writes here (hourly)
```

---

### Step 4 — Create Checkpoints Volume

Auto Loader needs a schema location for checkpoint data:

```bash
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "CREATE VOLUME IF NOT EXISTS main.<DEV_SCHEMA>.checkpoints", "wait_timeout": "50s"}'
```

---

### Step 5 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| Unity Catalog schema | ✓ Created | `main.<DEV_SCHEMA>` |
| Landing zone volume | ✓ Created | 5 subdirectories for API data |
| Checkpoints volume | ✓ Created | For Auto Loader schema tracking |
| AWS cost so far | **$0** | No infrastructure provisioned yet |

**Next:** Run `/silver-databricks-streaming:infra-cdc` to provision the EC2 instance with Postgres, Debezium, and Redpanda. **This is where AWS billing starts (~$0.02/hr).**
