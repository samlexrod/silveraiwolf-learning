---
description: "[Stage 11] Run the standalone backfill job to repopulate OpenSearch from existing Gold tables — no pipeline recomputation"
---

# Backfill OpenSearch — Emergency Repopulation

Run the standalone `backfill_opensearch.py` Spark job to push all Gold tables to OpenSearch without triggering a full pipeline refresh. Use this when OpenSearch needs repopulating but the Gold data in Delta is already correct.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 10 (simulate-changes), the learner has:
- Unified pipeline running with all 10 Gold tables populated in Delta
- EC2-based PySpark sink (`infra/opensearch-sink/`) indexing Gold → OpenSearch every 15 min via JDBC + opensearch-hadoop
- OpenSearch indices populated and queryable

Now: what happens when OpenSearch needs a full reindex — but your Gold data hasn't changed?

---

## When to Use This

| Scenario | Use Pipeline Refresh? | Use Backfill Job? |
|----------|----------------------|-------------------|
| Gold data changed (upstream update) | Yes — pipeline handles it | No need |
| OpenSearch index mapping changed | No — wasteful recompute | **Yes** |
| OpenSearch cluster rebuilt/replaced | No — wasteful recompute | **Yes** |
| OpenSearch corrupted or out of sync | No — wasteful recompute | **Yes** |
| Initial population of new OpenSearch cluster | No — data already in Delta | **Yes** |

**Key insight:** The EC2 PySpark sink polls every 15 min. The backfill job is imperative — you run it on demand when OpenSearch needs immediate repopulating from existing data (don't wait for the next 15-min cycle).

---

## Instructions

---

### Step 1 — Simulate an OpenSearch Problem

To demonstrate the backfill use case, delete one of the OpenSearch indices:

```bash
source .env

# Delete the risk-dashboard index
curl -s -k -u "admin:${OPENSEARCH_PASSWORD}" \
  -X DELETE "${OPENSEARCH_ENDPOINT}/risk-dashboard" | python3 -m json.tool
```

Confirm the index is gone:

```bash
curl -s -k -u "admin:${OPENSEARCH_PASSWORD}" \
  "${OPENSEARCH_ENDPOINT}/_cat/indices?v"
```

The `risk-dashboard` index should no longer appear. The Gold table in Delta is unaffected — only the OpenSearch copy is gone.

Present the before/after as a table showing which indices exist.

Use `AskUserQuestion` to confirm the user sees the index is deleted before proceeding.

---

### Step 2 — Review the Backfill Job

Show the user the backfill job code:

```bash
cat src/jobs/opensearch/backfill_opensearch.py
```

Walk through the key points:
- Reads Gold tables directly from Delta (`spark.sql("SELECT * FROM catalog.schema.table")`)
- Writes to OpenSearch via `df.write.format("opensearch")` — same opensearch-hadoop connector as the EC2 sink
- Casts `DecimalType` → `double` (opensearch-hadoop workaround)
- Handles ARRAY columns via SQL pushdown (`CAST(col AS STRING)`) — JDBC can't read Databricks ARRAY types
- Maps 10 Gold tables to 10 OpenSearch indices with upsert semantics
- **No pipeline involved** — this is a standalone Spark job

Use `AskUserQuestion` to confirm before running the job.

---

### Step 3 — Run the Backfill Job

Run the backfill job on Databricks:

```bash
source .env

databricks jobs run-now $BACKFILL_OPENSEARCH_JOB_ID --output json
```

If the job ID isn't set in `.env`, look it up:

```bash
databricks jobs list --output json | python3 -c "
import sys, json
jobs = json.load(sys.stdin).get('jobs', [])
for j in jobs:
    if 'backfill' in j['settings']['name'].lower():
        print(f\"Job: {j['settings']['name']}, ID: {j['job_id']}\")
"
```

Monitor the run:

```bash
# Get the run ID from the run-now output, then:
databricks runs get <RUN_ID> --output json | python3 -c "
import sys, json
run = json.load(sys.stdin)
print(f\"State: {run['state']['life_cycle_state']}\")
if 'result_state' in run['state']:
    print(f\"Result: {run['state']['result_state']}\")
"
```

Wait for the job to complete (typically 1-2 minutes).

Use `AskUserQuestion` to confirm the job completed successfully.

---

### Step 4 — Verify the Backfill

Check that all 5 indices are back:

```bash
curl -s -k -u "admin:${OPENSEARCH_PASSWORD}" \
  "${OPENSEARCH_ENDPOINT}/_cat/indices?v"
```

Present results as a table:

| Index | Docs | Status |
|-------|------|--------|
| risk-dashboard | (count) | Restored |
| financial-ratios | (count) | Unchanged |
| regulatory-report | (count) | Unchanged |
| desk-pnl-exposure | (count) | Unchanged |
| compliance-status | (count) | Unchanged |

Verify the restored index has data:

```bash
curl -s -k -u "admin:${OPENSEARCH_PASSWORD}" \
  "${OPENSEARCH_ENDPOINT}/risk-dashboard/_search?size=2&pretty"
```

---

### Step 5 — Summary

Present a comparison:

| Approach | What Runs | Cost | When to Use |
|----------|-----------|------|-------------|
| Pipeline full refresh | Bronze + Silver + Gold recompute | High (recomputes everything) | Gold data needs updating |
| Backfill job (one-shot) | Read Delta via JDBC → Write OpenSearch | Low (read-only on Delta) | OpenSearch needs immediate repopulating |
| EC2 PySpark sink (scheduled) | Read Delta via JDBC → Write OpenSearch (every 15 min) | Low | Normal operation |

**Key takeaway:** The backfill job exists for the gap between "my pipeline data is correct" and "my search layer is wrong." It bridges that gap without burning compute on unnecessary recomputation.

---

**Next:** Run `/silver-databricks-streaming:production-notes` for production deployment guidance, or `/silver-databricks-streaming:cleanup` to tear down all infrastructure.
