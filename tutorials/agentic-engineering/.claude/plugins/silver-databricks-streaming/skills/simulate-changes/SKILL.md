---
description: "[Stage 10] INSERT/UPDATE/DELETE in Postgres + re-run batch jobs, watch live changes flow through the running unified pipeline"
---

# Simulate Changes — Multi-Pipeline End-to-End

> **Note:** If you already ran simulate-changes in Stage 9 (stream-unified), this stage repeats the same scenarios but through the **multi-pipeline** setup instead. This lets you compare the experience: sequential pipeline starts vs one unified start.
>
> If you want to skip this stage, proceed to `/silver-databricks-streaming:backfill-opensearch`.

Make real changes in BOTH source systems and watch them flow through the multi-pipeline monorepo: Postgres CDC changes flow through app_streams, job re-runs flow through data_fabric, and the analytics pipeline recalculates cross-domain Gold tables.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 9 (stream-unified), the learner has:
- Unified pipeline: demonstrated real-time cross-domain updates in one pipeline
- Multi-pipeline setup: still intact (app_streams, data_fabric, analytics)
- Now we see the same scenarios through the multi-pipeline lens — sequential starts, separate analytics trigger
- analytics pipeline: fully populated (cross-domain Gold tables complete)
- All 3 pipelines running, all tables populated

---

## Instructions

---

### Step 1 — Verify All Pipelines are Running

```bash
source .env

for PIPELINE_ID in $APP_STREAMS_PIPELINE_ID $DATA_FABRIC_PIPELINE_ID; do
  databricks pipelines get $PIPELINE_ID --output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'{data[\"name\"]}: {data[\"state\"]}')
"
done
```

Confirm both continuous pipelines show `RUNNING`.

---

### Step 2 — Baseline Snapshot

Before making changes, capture current state for comparison:

```sql
-- Gold risk dashboard — capture current state
SELECT counterparty_id, name, risk_tier, concentration_pct, gross_exposure, sanctions_match
FROM main.financial_risk_streaming.gold_risk_dashboard
ORDER BY concentration_pct DESC
LIMIT 10;

-- Count rows across key Silver tables
SELECT
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_counterparties) as counterparties,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_transactions) as transactions,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_exchange_rates) as fx_rates,
  (SELECT COUNT(*) FROM main.financial_risk_streaming.silver_sanctions_watchlist) as sanctions;
```

Present baseline as tables. Save for comparison after changes.

---

### Step 3 — Scenario 1: New Large Transaction (INSERT via CDC)

**Business scenario:** A trader at one of the smaller counterparties executes a massive $50M equity purchase — this could shift risk tiers.

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO transactions (transaction_id, counterparty_id, direction, instrument_id,
    instrument_type, amount, currency, transaction_date, quantity)
  VALUES ('TXN_LIVE_001', 'CP005', 'BUY', 'MSFT', 'EQUITY', 50000000.00, 'USD', CURRENT_DATE, 200000);
"
```

**What should happen (app_streams pipeline):**
1. Postgres WAL records the INSERT (~10ms)
2. Debezium publishes CDC event to `postgres.public.transactions` topic (~50ms)
3. Bronze table `bronze_cdc_transactions` receives the event
4. Silver staging table parses the CDC envelope
5. `APPLY CHANGES INTO` inserts into `silver_transactions`
6. `silver_positions` recomputes — CP005 now has a massive MSFT position
7. `gold_financial_ratios` and `gold_portfolio_summary` recalculate

Wait ~30 seconds for the pipeline to process, then verify:

```sql
-- Check Silver: new transaction should appear
SELECT transaction_id, counterparty_id, direction, amount, instrument_id
FROM main.financial_risk_streaming.silver_transactions
WHERE transaction_id = 'TXN_LIVE_001';

-- Check Gold: portfolio summary should reflect the new position
SELECT sector, instrument_type, total_market_value, counterparty_count
FROM main.financial_risk_streaming.gold_portfolio_summary
ORDER BY gross_market_value DESC;
```

Use `AskUserQuestion` to discuss the results.

---

### Step 4 — Scenario 2: Credit Downgrade (UPDATE via CDC)

**Business scenario:** A counterparty's credit rating is downgraded from AA to BBB.

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  UPDATE counterparties
  SET credit_rating = 'BBB',
      total_assets = total_assets * 0.85,
      equity = equity * 0.70,
      updated_at = NOW()
  WHERE counterparty_id = 'CP001';
"
```

**What should happen:**
1. `APPLY CHANGES INTO` updates `silver_counterparties` — CP001 now shows BBB
2. `gold_financial_ratios` recalculates — debt_to_equity changes
3. `gold_counterparty_health` updates with new rating

Wait ~30 seconds, then verify:

```sql
-- Silver: updated credit rating
SELECT counterparty_id, name, credit_rating, total_assets, equity
FROM main.financial_risk_streaming.silver_counterparties
WHERE counterparty_id = 'CP001';

-- Gold: recalculated ratios
SELECT counterparty_id, name, credit_rating, current_ratio, debt_to_equity, roe
FROM main.financial_risk_streaming.gold_financial_ratios
WHERE counterparty_id = 'CP001';
```

**Teaching moment:** In the batch tutorial, you'd need to full-refresh the pipeline to see this change. In the streaming tutorial, it flows through automatically.

Use `AskUserQuestion` to discuss.

---

### Step 5 — Scenario 3: Counterparty Offboarded (DELETE via CDC)

**Business scenario:** A counterparty is offboarded — removed from all Gold metrics.

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  DELETE FROM desk_assignments WHERE counterparty_id = 'CP020';
  DELETE FROM transactions WHERE counterparty_id = 'CP020';
  DELETE FROM credit_ratings_history WHERE counterparty_id = 'CP020';
  DELETE FROM counterparties WHERE counterparty_id = 'CP020';
"
```

**What should happen:**
1. Debezium captures DELETE events for all affected rows across multiple tables
2. `APPLY CHANGES INTO` removes CP020 from `silver_counterparties`, their transactions, assignments, and ratings
3. Gold tables recalculate — CP020 disappears from all metrics

Wait ~30 seconds, then verify:

```sql
-- Silver: CP020 should be gone from all tables
SELECT 'counterparties' as tbl, COUNT(*) FROM main.financial_risk_streaming.silver_counterparties WHERE counterparty_id = 'CP020'
UNION ALL SELECT 'transactions', COUNT(*) FROM main.financial_risk_streaming.silver_transactions WHERE counterparty_id = 'CP020'
UNION ALL SELECT 'desk_assignments', COUNT(*) FROM main.financial_risk_streaming.silver_desk_assignments WHERE counterparty_id = 'CP020';
```

Use `AskUserQuestion` to discuss.

---

### Step 6 — Scenario 4: New API Data (Job Re-Run)

**Business scenario:** Exchange rates update — re-run the market reference job.

```bash
# Re-run the market reference job
databricks bundle run market_reference_hourly --target dev
```

**What should happen (data_fabric pipeline):**
1. Job fetches new exchange rates and benchmark rates
2. New JSON files written to landing zone
3. Auto Loader detects files within seconds
4. Bronze API tables append new records
5. Silver transforms and validates
6. Gold reference rates update

Wait for the job to complete, then verify:

```sql
-- New rows should appear (count increases)
SELECT COUNT(*) as total_rows, COUNT(DISTINCT source_file) as file_count
FROM main.financial_risk_streaming.bronze_api_exchange_rates;

-- Gold: latest reference rates
SELECT currency_pair, exchange_rate, benchmark_name, benchmark_rate
FROM main.financial_risk_streaming.gold_reference_rates
ORDER BY ingested_at DESC
LIMIT 5;
```

---

### Step 7 — Scenario 5: Cross-Domain Impact

Now trigger the analytics pipeline to see how BOTH types of changes (CDC + API) affect the cross-domain Gold tables:

```bash
# Trigger analytics pipeline
databricks pipelines start-update $ANALYTICS_PIPELINE_ID
```

Wait for completion, then verify:

```sql
-- Risk dashboard should reflect:
-- 1. CP005's new large position (from CDC INSERT)
-- 2. CP001's downgraded credit (from CDC UPDATE)
-- 3. CP020 removed (from CDC DELETE)
-- 4. Updated exchange rates (from job re-run)
SELECT counterparty_id, gross_exposure, concentration_pct, risk_tier, fx_rate
FROM main.financial_risk_streaming.gold_risk_dashboard
ORDER BY concentration_pct DESC
LIMIT 10;
```

**Key insight:** The analytics pipeline joins data from BOTH other pipelines. A single trigger produces Gold tables that reflect changes from completely different source systems (PostgreSQL CDC + external APIs).

Use `AskUserQuestion` to discuss.

---

### Step 8 — Verify Changes in OpenSearch

The Gold Delta tables are updated. The EC2-based PySpark sink (`opensearch-sink` container) syncs Gold → OpenSearch every 15 minutes. To see changes immediately, trigger a one-shot sync:

```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && docker run --rm --env-file .env -e SINK_INTERVAL_SECONDS=0 opensearch-sink"
```

Verify the changes landed in OpenSearch via the REST API:

```bash
# Check risk-dashboard reflects the changes:
# - CP001 should show credit_rating=BBB (downgrade)
# - CP005 should appear with the new position
# - CP020 should be ABSENT (offboarded)
curl -s -u admin:$OPENSEARCH_PASSWORD "https://$OPENSEARCH_ENDPOINT/risk-dashboard/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"terms":{"counterparty_id":["CP001","CP005","CP020"]}},"size":10}' | python3 -m json.tool

# Check financial-ratios reflects CP001's new debt-to-equity after downgrade
curl -s -u admin:$OPENSEARCH_PASSWORD "https://$OPENSEARCH_ENDPOINT/financial-ratios/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"term":{"counterparty_id":"CP001"}}}' | python3 -m json.tool

# Verify document counts match Gold table counts
curl -s -u admin:$OPENSEARCH_PASSWORD "https://$OPENSEARCH_ENDPOINT/_cat/count/risk-dashboard?v"
curl -s -u admin:$OPENSEARCH_PASSWORD "https://$OPENSEARCH_ENDPOINT/_cat/count/financial-ratios?v"
```

**This closes the loop:** Postgres → CDC → Bronze → Silver → Gold → **OpenSearch** — the full end-to-end pipeline from source-of-truth to search layer.

Use `AskUserQuestion` to confirm OpenSearch reflects the changes.

---

### Step 9 — Revert Test Data

Clean up the test changes:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  -- Remove the large test transaction
  DELETE FROM transactions WHERE transaction_id = 'TXN_LIVE_001';

  -- Restore CP001's credit rating
  UPDATE counterparties
  SET credit_rating = 'AA',
      total_assets = total_assets / 0.85,
      equity = equity / 0.70,
      updated_at = NOW()
  WHERE counterparty_id = 'CP001';
"
```

Note: CP020 and the API data cannot be reverted. For a tutorial, this is acceptable — the point was to demonstrate the multi-pipeline CDC + API flow.

---

### Step 10 — What Just Happened

```
  PostgreSQL (CDC)                  External APIs (Jobs)
 ┌──────────────┐                  ┌──────────────┐
 │ INSERT txn   │─── op:"c" ──┐   │ Re-run job   │──┐
 │ UPDATE cp    │─── op:"u" ──┤   │ New JSON     │  │
 │ DELETE cp    │─── op:"d" ──┤   └──────────────┘  │
 └──────────────┘             │                      │
                              ▼                      ▼
                   ┌──────────────────────────────────────────────┐
                   │      Unified Pipeline (continuous)           │
                   │  CDC Bronze → Silver (APPLY CHANGES) ──┐     │
                   │  API Bronze → Silver (transforms)  ────┼──> Gold
                   │  Cross-domain Gold (inline)        ────┘     │
                   └──────────────────────────────────────────────┘
                              │
                              ▼  (re-index job)
                   ┌──────────────────────────────────────────────┐
                   │      OpenSearch (serving layer)              │
                   │  risk-dashboard    ← gold_risk_dashboard     │
                   │  financial-ratios  ← gold_financial_ratios   │
                   │  regulatory-report ← gold_regulatory_report  │
                   │  desk-pnl-exposure ← gold_desk_pnl_exposure  │
                   │  compliance-status ← gold_compliance_status  │
                   │                                              │
                   │  Search, dashboards, REST API, alerting      │
                   └──────────────────────────────────────────────┘
```

The full end-to-end flow:
- **Postgres COMMIT** → Debezium WAL read (~10ms) → Redpanda topic (~50ms) → **Bronze** → **Silver** (APPLY CHANGES) → **Gold** → **OpenSearch** (re-index)
- **API job** → JSON file in landing zone → Auto Loader → **Bronze** → **Silver** → **Gold** → **OpenSearch**

---

### Step 10b — Explore in OpenSearch Dashboards

Tell the user to open the **OpenSearch Dashboards** URL from Terraform outputs (or `.env`):

```
https://<opensearch_endpoint>/_dashboards
```

Login with the `OPENSEARCH_USER` and `OPENSEARCH_PASSWORD` from `.env`.

**Quick tour for the learner:**

1. **Query Workbench (fastest way to explore)** — go to the hamburger menu (☰) → **OpenSearch Plugins** → **Query Workbench**. You can run SQL directly against OpenSearch indices — no index patterns needed:
   ```sql
   -- See all counterparties in the risk dashboard
   SELECT counterparty_id, name, risk_tier, gross_exposure
   FROM "risk-dashboard"
   ORDER BY gross_exposure DESC

   -- Check CP001's financial ratios after downgrade
   SELECT name, credit_rating, debt_to_equity, roe
   FROM "financial-ratios"
   WHERE counterparty_id = 'CP001'

   -- Verify CP020 is absent
   SELECT COUNT(*) FROM "risk-dashboard" WHERE counterparty_id = 'CP020'
   ```
   **Note:** Index names with hyphens must be quoted with double quotes in SQL.

2. **Create index patterns (needed for Discover + Visualize)** — go to the hamburger menu (☰) → **Dashboards Management** → **Index patterns** → **Create index pattern**.
   - Enter `risk-dashboard` as the index pattern name. If it shows a green checkmark and "Your index pattern matches 1 source", click **Next step** then **Create index pattern** (skip the time field).
   - Repeat for `financial-ratios`, `desk-pnl-exposure`, `regulatory-report`, and `compliance-status`.
   - **Important:** You must create at least one index pattern before Discover will show any data.

3. **Discover** — go to the hamburger menu (☰) → **Discover**. Select `risk-dashboard` from the index pattern dropdown (top left). You can now:
   - Type `CP001` in the search bar (uses full-text search across all fields)
   - Use the **Add filter** button → field: `risk_tier`, operator: `is`, value: `HIGH` to filter high-risk counterparties
   - Search for `CP020` to verify it's absent (0 hits — offboarded)
   - Click on any row to expand and see all fields

4. **Visualize** — go to the hamburger menu (☰) → **Visualize** → **Create visualization**:
   - **Pie chart**: Select `risk-dashboard` index → Buckets → Split slices → Aggregation: Terms → Field: `risk_tier.keyword` → shows distribution of CRITICAL/HIGH/MEDIUM/LOW
   - **Data table**: Select `financial-ratios` index → Metrics: select columns `name.keyword`, `credit_rating.keyword`, `debt_to_equity`, `roe`
   - **Vertical bar chart**: Select `desk-pnl-exposure` index → X-axis: Terms on `desk_name.keyword`, Y-axis: Average of `total_pnl`

5. **Dashboard** — go to the hamburger menu (☰) → **Dashboard** → **Create new dashboard** → **Add** existing visualizations. Combine the pie chart, data table, and bar chart into a single view. This is the "risk dashboard" that analysts and traders would see in production.

**Key insight:** OpenSearch Dashboards gives non-technical users (risk managers, compliance officers) a self-service way to explore Gold data — no SQL, no Databricks access needed. The data is the same Delta tables, just served through a search-optimized layer.

**Note on `.keyword` fields:** When filtering or creating visualizations on text fields (like `risk_tier`, `name`, `desk_name`), use the `.keyword` variant (e.g., `risk_tier.keyword`). The `.keyword` field is an exact-match version that works with aggregations and filters. The base field (without `.keyword`) is analyzed for full-text search.

Use `AskUserQuestion` to confirm the learner explored the dashboards.

---

### Step 11 — Summary

| Scenario | Source | Verified At |
|----------|--------|-------------|
| Large transaction | Postgres INSERT → CDC | Silver + Gold + OpenSearch |
| Credit downgrade | Postgres UPDATE → CDC | Silver + Gold ratios + OpenSearch |
| Offboarded counterparty | Postgres DELETE → CDC | Removed from Silver + Gold + OpenSearch |
| Exchange rate update | Job re-run → Auto Loader | Silver + Gold reference rates |
| Cross-domain impact | All of the above | Risk dashboard (Gold + OpenSearch) |
| **Full loop** | Postgres → CDC → Bronze → Silver → Gold → **OpenSearch** | End-to-end verified |

**Next:** Run `/silver-databricks-streaming:backfill-opensearch` to learn emergency OpenSearch repopulation, or skip to `/silver-databricks-streaming:production-notes` for production deployment guidance.
