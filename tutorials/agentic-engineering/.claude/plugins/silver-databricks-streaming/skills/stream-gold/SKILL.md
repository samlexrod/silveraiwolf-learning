---
description: "[Stage 8] Deploy ALL Gold — domain-specific tables + cross-domain analytics pipeline"
---

# Streaming Gold — Domain Metrics + Cross-Domain Analytics

Deploy the Gold layer across all 3 pipelines: **app_streams** gets domain-specific Gold tables, **data_fabric** gets domain-specific Gold tables, and the **analytics** pipeline joins Silver tables from both pipelines into cross-domain Gold tables. Three tiers of Gold, one unified data model.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 5 (stream-silver), the learner has:
- app_streams: 7 CDC Bronze + 8 Silver tables (including derived positions)
- data_fabric: 5 API Bronze + 5 Silver tables (empty until Stage 7)
- Both pipelines running continuously
- No Gold tables yet

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm Silver tables are populated and pipelines are running:

```bash
source .env

# Check pipeline states
for PIPELINE_ID in $APP_STREAMS_PIPELINE_ID $DATA_FABRIC_PIPELINE_ID; do
  databricks pipelines get $PIPELINE_ID --output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'{data[\"name\"]}: {data[\"state\"]}')
"
done
```

Query Silver row counts to confirm data is flowing.

---

### Step 2 — Explain the Three-Tier Gold Architecture

Gold tables are organized in three tiers across 3 pipelines:

```
  app_streams pipeline                 data_fabric pipeline              analytics pipeline
 ┌──────────────────────────┐         ┌──────────────────────────┐     ┌──────────────────────────┐
 │  DOMAIN GOLD (CDC)       │         │  DOMAIN GOLD (API)       │     │  CROSS-DOMAIN GOLD       │
 │                          │         │                          │     │                          │
 │  Financial:              │         │  Compliance:             │     │  risk_dashboard          │
 │   financial_ratios       │         │   compliance_status      │     │   ← silver_counterparties│
 │   portfolio_summary      │         │                          │     │   ← silver_positions     │
 │                          │         │  Market Reference:       │     │   ← silver_sanctions     │
 │  Counterparty:           │         │   reference_rates        │     │   ← silver_exchange_rates│
 │   counterparty_health    │         │                          │     │                          │
 │                          │         │  Regulatory:             │     │  regulatory_report       │
 │  Operations:             │         │   regulatory_metrics     │     │   ← silver_transactions  │
 │   desk_overview          │         │                          │     │   ← silver_reporting_reqs│
 │                          │         │                          │     │   ← silver_counterparties│
 │                          │         │                          │     │                          │
 │  (reads from Silver      │         │  (reads from Silver      │     │  desk_pnl_exposure       │
 │   within same pipeline)  │         │   within same pipeline)  │     │   ← silver_positions     │
 └──────────────────────────┘         └──────────────────────────┘     │   ← silver_trading_desks │
                                                                       │   ← silver_desk_assigns  │
                                                                       │                          │
                                                                       │  (reads across BOTH      │
                                                                       │   other pipelines)       │
                                                                       └──────────────────────────┘
```

**Why three tiers — and why not put everything in one pipeline?**

The cross-domain analytics tables (`risk_dashboard`, `regulatory_report`, `desk_pnl_exposure`) join Silver tables from **both** app_streams and data_fabric. If you put them inside either pipeline:

- **In app_streams:** The pipeline would need to read data_fabric Silver tables. Every CDC micro-batch (~10s) would trigger a cross-domain join — even when the API data hasn't changed. That's wasted compute. Exchange rates update hourly, sanctions update daily — but you'd be re-joining them every 10 seconds.
- **In data_fabric:** Same problem in reverse — every API file arrival triggers a join against all CDC Silver tables, even when counterparty data hasn't changed.
- **In a separate triggered pipeline:** You control exactly when cross-domain joins run. Trigger it on a schedule (e.g., every 15 minutes) or on demand. No wasted compute on redundant joins.

| Approach | Compute Cost | Freshness | When to Use |
|----------|-------------|-----------|-------------|
| Domain Gold (in-pipeline) | Low — recomputes only when its own Silver changes | Real-time | Single-domain aggregations |
| Cross-Domain Gold (triggered) | Controlled — runs on schedule | Minutes | Multi-pipeline joins |
| Cross-Domain Gold (continuous) | High — every micro-batch re-joins everything | Real-time | Only if you truly need sub-minute cross-domain freshness |

**"But aren't the domain Gold tables inside app_streams and data_fabric also wasteful?"**

No — and this is an important distinction. Domain Gold tables are a **marginal cost**, not a fixed cost:

```
  app_streams pipeline (already running for CDC)
  ┌──────────────────────────────────────────┐
  │ Bronze ──> Silver ──> Domain Gold        │  ← Gold is "free" here,
  │                       (same data path)   │     pipeline is already running
  └──────────────────────────────────────────┘

  analytics pipeline (separate trigger)
  ┌──────────────────────────────────────────┐
  │ Read app_streams Silver ─┐               │  ← This would be wasteful
  │ Read data_fabric Silver ─┼──> Cross Gold │     every 10 seconds
  └──────────────────────────────────────────┘
```

- When a CDC event arrives, app_streams is **already running** to update Bronze → Silver. Computing `gold_financial_ratios` from the freshly-updated `silver_counterparties` is one more step in the same compute session — no extra cluster spin-up, no cross-pipeline reads, nearly free.
- If no CDC events arrive, the pipeline sits idle — Gold doesn't recompute. No waste.
- Cross-domain Gold is different: it reads from **multiple pipelines**, so running it on every micro-batch means re-reading unchanged data from other sources. That's waste.

**The design question:** "Does the application need this Gold table updated within seconds of a change?"

| Gold Table | Real-time needed? | Placement | Why |
|------------|-------------------|-----------|-----|
| `gold_financial_ratios` | YES — trading app needs current ratios to approve/reject trades | app_streams (in-pipeline) | Sub-second freshness, marginal cost |
| `gold_counterparty_health` | YES — credit checks happen on every trade | app_streams (in-pipeline) | Must reflect latest rating change immediately |
| `gold_desk_overview` | YES — desk managers need live assignment counts | app_streams (in-pipeline) | Operational awareness |
| `gold_compliance_status` | YES — compliance gates block trades if KYC expired | data_fabric (in-pipeline) | Must reflect latest KYC/sanctions status |
| `gold_reference_rates` | YES — pricing engine needs current FX rates | data_fabric (in-pipeline) | Rate changes affect all open positions |
| `gold_regulatory_metrics` | YES — compliance dashboard shows live deadlines | data_fabric (in-pipeline) | Overdue requirements need immediate visibility |
| `gold_risk_dashboard` | NO — risk team reviews every 15 min | analytics (triggered) | Cross-domain join, controlled cost |
| `gold_regulatory_report` | NO — filed quarterly | analytics (triggered) | Cross-domain join, batch cadence |
| `gold_desk_pnl_exposure` | NO — reviewed at end of day | analytics (triggered) | Cross-domain join, daily cadence |

**Rule of thumb:** If the Gold table feeds back into the application (trade approval, pricing, compliance gates), put it in the same pipeline as its Silver source — it's practically free. If it's for human consumption (dashboards, reports, analytics), use a triggered pipeline on a sensible cadence.

**Real-time scenario:** A trader executes a $10M bond purchase -> Postgres INSERT -> CDC -> Bronze -> Silver -> Positions updated -> `financial_ratios` and `portfolio_summary` recalculate instantly (domain Gold, zero waste). The analytics pipeline's `risk_dashboard` recalculates on its next trigger (e.g., every 15 min), combining the new position with the latest compliance and exchange rate data — no wasted joins in between.

---

**Alternative Design: The Single-Pipeline Approach**

There's a valid alternative — put **everything** in one pipeline. This is the right choice when the application needs cross-domain Gold tables updated in real-time (e.g., the risk dashboard must block trades within seconds of a sanctions list update).

```
  MULTI-PIPELINE (this tutorial)              SINGLE-PIPELINE (alternative)
 ┌────────────────────┐                      ┌────────────────────────────────────┐
 │ app_streams        │                      │ unified_risk_pipeline              │
 │  CDC B → S → G     │                      │                                    │
 └────────────────────┘                      │  CDC Bronze (7 Kafka tables)       │
 ┌────────────────────┐                      │  API Bronze (5 Auto Loader tables) │
 │ data_fabric        │                      │  All Silver (13 tables)            │
 │  API B → S → G     │         ──────>      │  All Gold — including cross-domain │
 └────────────────────┘                      │    risk_dashboard                  │
 ┌────────────────────┐                      │    regulatory_report               │
 │ analytics          │                      │    desk_pnl_exposure               │
 │  Cross-domain Gold │                      │                                    │
 └────────────────────┘                      │  One pipeline, one DAG, real-time  │
                                             └────────────────────────────────────┘
```

**When to choose the single-pipeline approach:**
- The risk dashboard must update **within seconds** of a CDC event OR an API file landing
- You want a single DAG with clear lineage from source to Gold — easier to debug
- Your Databricks tier supports it (no pipeline quota limitations)
- You accept the trade-off: every micro-batch re-evaluates all Gold tables, even cross-domain joins

**When to choose the multi-pipeline approach (this tutorial):**
- CDC and API sources have very different cadences (seconds vs hours) — separate pipelines avoid unnecessary recomputation
- You want fault isolation — a Kafka connection failure shouldn't block API data processing
- You want independent scaling — CDC throughput doesn't affect API pipeline sizing
- Cross-domain freshness of minutes (not seconds) is acceptable

**The key insight:** In the single-pipeline approach, the `gold_risk_dashboard` becomes a domain Gold table — it recomputes on every micro-batch alongside everything else. This is only wasteful if the cross-domain data rarely changes relative to the micro-batch interval. If **both** CDC events and API files arrive frequently, the single pipeline is actually more efficient because there's only one compute session to manage.

| Design | Pipelines | Cross-Domain Freshness | Compute Efficiency | Fault Isolation |
|--------|-----------|----------------------|-------------------|----------------|
| Multi-pipeline (this tutorial) | 3 | Minutes (triggered) | High — no wasted joins | High — independent failures |
| Single-pipeline | 1 | Real-time (every micro-batch) | Lower — re-joins on every batch | Low — one failure stops everything |

Both are valid production architectures. This tutorial uses multi-pipeline to teach the concepts separately, but show the learner this is a spectrum — not a binary choice.

Use `AskUserQuestion` to confirm understanding.

---

### Step 3 — Part A: Domain Gold (app_streams pipeline)

#### Step 3a — `src/pipelines/app_streams/financial/gold/financial_ratios.py`

```python
import pyspark.sql.functions as F
import sparktool.pipeline as sp


@sp.table(
    name="gold_financial_ratios",
    comment="Financial health ratios per counterparty — updated in real time from CDC events",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_financial_ratios():
    return (
        sp.read("silver_counterparties")
        .select(
            "counterparty_id",
            "name",
            "sector",
            "credit_rating",
            F.round(F.col("current_assets") / F.col("current_liabilities"), 4).alias("current_ratio"),
            F.round((F.col("current_assets") - F.col("inventory")) / F.col("current_liabilities"), 4).alias("quick_ratio"),
            F.round(F.col("total_liabilities") / F.col("equity"), 4).alias("debt_to_equity"),
            F.when(F.col("interest_expense") > 0,
                F.round(F.col("net_income") / F.col("interest_expense"), 4)
            ).alias("interest_coverage"),
            F.round(F.col("net_income") / F.col("equity"), 4).alias("roe"),
            F.round(F.col("net_income") / F.col("total_assets"), 4).alias("roa"),
            F.when(F.col("revenue") > 0,
                F.round(F.col("net_income") / F.col("revenue"), 4)
            ).alias("net_profit_margin"),
        )
    )
```

**Streaming behavior:** When a counterparty's `total_assets` is updated via CDC, `silver_counterparties` is updated via `APPLY CHANGES INTO`, which triggers `gold_financial_ratios` to recompute.

Use `AskUserQuestion` to confirm before moving to next table.

#### Step 3b — All app_streams Domain Gold Tables

| File Path | Table Name | Reads From | Purpose |
|-----------|------------|-----------|---------|
| `src/pipelines/app_streams/financial/gold/financial_ratios.py` | `gold_financial_ratios` | `silver_counterparties` | 7 financial ratios per counterparty |
| `src/pipelines/app_streams/financial/gold/portfolio_summary.py` | `gold_portfolio_summary` | `silver_positions` + `silver_counterparties` | Sector x instrument x currency aggregates |
| `src/pipelines/app_streams/counterparty/gold/counterparty_health.py` | `gold_counterparty_health` | `silver_counterparties` + `silver_credit_ratings_history` | Credit health with rating history |
| `src/pipelines/app_streams/operations/gold/desk_overview.py` | `gold_desk_overview` | `silver_trading_desks` + `silver_office_locations` + `silver_desk_assignments` | Desk capacity and assignment summary |

---

### Step 4 — Part B: Domain Gold (data_fabric pipeline)

#### Step 4a — data_fabric Domain Gold Tables

| File Path | Table Name | Reads From | Purpose |
|-----------|------------|-----------|---------|
| `src/pipelines/data_fabric/compliance/gold/compliance_status.py` | `gold_compliance_status` | `silver_sanctions_watchlist` + `silver_kyc_records` | Compliance risk per entity |
| `src/pipelines/data_fabric/market_reference/gold/reference_rates.py` | `gold_reference_rates` | `silver_exchange_rates` + `silver_benchmark_rates` | Unified rate lookup |
| `src/pipelines/data_fabric/regulatory/gold/regulatory_metrics.py` | `gold_regulatory_metrics` | `silver_reporting_requirements` | Requirement tracking and deadlines |

**Note:** These Gold tables will remain empty until the Python batch jobs run in Stage 7, since their Silver inputs are still empty.

---

### Step 5 — Part C: Cross-Domain Analytics Gold

This is the third pipeline — **analytics** — and the unique part of this tutorial. It reads Silver tables from BOTH other pipelines:

#### Step 5a — `src/pipelines/analytics/gold/risk_dashboard.py`

```python
import pyspark.sql.functions as F
import sparktool.pipeline as sp


@sp.table(
    name="gold_risk_dashboard",
    comment="Cross-domain risk dashboard — combines CDC positions with API compliance and market data",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_risk_dashboard():
    counterparties = sp.read("silver_counterparties")
    positions = sp.read("silver_positions")
    sanctions = sp.read("silver_sanctions_watchlist")
    exchange_rates = sp.read("silver_exchange_rates")

    # Combine position exposure with compliance status and FX rates
    ...
```

**Key architecture point:** The analytics pipeline references Silver tables that live in the app_streams and data_fabric pipelines. This works because all three pipelines write to the **same Unity Catalog schema** (`main.financial_risk_streaming`). The analytics pipeline reads these tables as regular Delta tables — no streaming dependency, just table reads.

#### Step 5b — All Analytics Gold Tables

| File Path | Table Name | Reads From (cross-pipeline) | Purpose |
|-----------|------------|---------------------------|---------|
| `src/pipelines/analytics/gold/risk_dashboard.py` | `gold_risk_dashboard` | `silver_counterparties`, `silver_positions`, `silver_sanctions_watchlist`, `silver_exchange_rates` | Unified risk view |
| `src/pipelines/analytics/gold/regulatory_report.py` | `gold_regulatory_report` | `silver_transactions`, `silver_reporting_requirements`, `silver_counterparties` | Regulatory filing data |
| `src/pipelines/analytics/gold/desk_pnl_exposure.py` | `gold_desk_pnl_exposure` | `silver_positions`, `silver_trading_desks`, `silver_desk_assignments` | P&L by desk with exposure |

**Important:** The analytics pipeline is configured as `continuous: false` in `databricks.yml`. It runs on demand (or on a trigger) rather than continuously, because cross-domain joins should happen on a cadence — not on every micro-batch.

Use `AskUserQuestion` to confirm understanding.

---

### Step 6 — Deploy All 3 Pipelines with Full Bronze + Silver + Gold

Uncomment all libraries in `databricks.yml` for all 3 pipelines:

```yaml
resources:
  pipelines:
    app_streams:
      libraries:
        # Full library list from databricks.yml — all Bronze + Silver + Gold
        # Financial domain (Bronze + Silver + Gold)
        - file: { path: src/pipelines/app_streams/financial/bronze/transactions.py }
        - file: { path: src/pipelines/app_streams/financial/bronze/market_prices.py }
        - file: { path: src/pipelines/app_streams/financial/silver/transactions.py }
        - file: { path: src/pipelines/app_streams/financial/silver/market_prices.py }
        - file: { path: src/pipelines/app_streams/financial/silver/positions.py }
        - file: { path: src/pipelines/app_streams/financial/gold/financial_ratios.py }
        - file: { path: src/pipelines/app_streams/financial/gold/portfolio_summary.py }
        # Counterparty domain (Bronze + Silver + Gold)
        - file: { path: src/pipelines/app_streams/counterparty/bronze/counterparties.py }
        - file: { path: src/pipelines/app_streams/counterparty/bronze/credit_ratings_history.py }
        - file: { path: src/pipelines/app_streams/counterparty/silver/counterparties.py }
        - file: { path: src/pipelines/app_streams/counterparty/silver/credit_ratings_history.py }
        - file: { path: src/pipelines/app_streams/counterparty/gold/counterparty_health.py }
        # Operations domain (Bronze + Silver + Gold)
        - file: { path: src/pipelines/app_streams/operations/bronze/office_locations.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/trading_desks.py }
        - file: { path: src/pipelines/app_streams/operations/bronze/desk_assignments.py }
        - file: { path: src/pipelines/app_streams/operations/silver/office_locations.py }
        - file: { path: src/pipelines/app_streams/operations/silver/trading_desks.py }
        - file: { path: src/pipelines/app_streams/operations/silver/desk_assignments.py }
        - file: { path: src/pipelines/app_streams/operations/gold/desk_overview.py }

    data_fabric:
      libraries:
        # Full library list — all Bronze + Silver + Gold
        # (all entries from databricks.yml)

    analytics:
      libraries:
        - file: { path: src/pipelines/analytics/gold/risk_dashboard.py }
        - file: { path: src/pipelines/analytics/gold/regulatory_report.py }
        - file: { path: src/pipelines/analytics/gold/desk_pnl_exposure.py }
```

---

### Step 7 — Deploy and Run

```bash
mise run deploy:dev
databricks bundle validate --target dev

# Start/update app_streams and data_fabric (continuous)
databricks pipelines start-update $APP_STREAMS_PIPELINE_ID
databricks pipelines start-update $DATA_FABRIC_PIPELINE_ID

# Run analytics pipeline (triggered — one-time execution)
databricks pipelines start-update $ANALYTICS_PIPELINE_ID
```

The app_streams and data_fabric pipelines update in place. The analytics pipeline runs once to compute its Gold tables.

---

### Step 8 — Verify Domain Gold Tables (app_streams)

Query Gold tables from the app_streams pipeline:

```sql
-- Financial ratios
SELECT counterparty_id, name, current_ratio, debt_to_equity, roe
FROM main.financial_risk_streaming.gold_financial_ratios
ORDER BY debt_to_equity DESC
LIMIT 5;

-- Counterparty health
SELECT counterparty_id, name, credit_rating, latest_agency, latest_outlook
FROM main.financial_risk_streaming.gold_counterparty_health
ORDER BY credit_rating;

-- Desk overview
SELECT desk_name, office_city, asset_class, assignment_count
FROM main.financial_risk_streaming.gold_desk_overview
ORDER BY assignment_count DESC;

-- Portfolio summary
SELECT sector, instrument_type, total_market_value, counterparty_count
FROM main.financial_risk_streaming.gold_portfolio_summary
ORDER BY gross_market_value DESC;
```

Present results as tables with business-context callouts.

---

### Step 9 — Verify Cross-Domain Analytics Gold

The analytics Gold tables join data from both pipelines. Since API data is not yet available (Stage 7), the cross-domain tables will have partial data:

```sql
-- Risk dashboard — positions populated, compliance columns null
SELECT counterparty_id, gross_exposure, concentration_pct, sanctions_match, fx_rate
FROM main.financial_risk_streaming.gold_risk_dashboard
ORDER BY concentration_pct DESC
LIMIT 5;

-- Desk P&L exposure — populated from app_streams Silver
SELECT desk_name, total_pnl, instrument_count, head_trader
FROM main.financial_risk_streaming.gold_desk_pnl_exposure
ORDER BY ABS(total_pnl) DESC;
```

**Expected:** Cross-domain Gold tables show CDC-derived columns populated but API-derived columns as NULL. After Stage 7 (run-jobs), all columns will be populated.

---

### Step 10 — Full Pipeline Lineage

```
  PostgreSQL (EC2)                      External APIs
       │                                      │
       ├── INSERT/UPDATE/DELETE                ├── Python batch jobs
       ▼                                      ▼
  Debezium (WAL reader)               Landing Zone (Volumes)
       │                                      │
       ├── CDC JSON events                    ├── JSON files
       ▼                                      ▼
  Redpanda (7 topics)                  Auto Loader (5 dirs)
       │                                      │
       ▼                                      ▼
  ═══════════════════════════        ═══════════════════════════
  app_streams pipeline               data_fabric pipeline
  (continuous)                       (continuous)
  ═══════════════════════════        ═══════════════════════════
       │                                      │
       ├── BRONZE (7 CDC tables)              ├── BRONZE (5 API tables)
       ├── SILVER (8 tables)                  ├── SILVER (5 tables)
       └── GOLD (4 domain tables)             └── GOLD (3 domain tables)
              │                                      │
              └──────────────┬───────────────────────┘
                             │
                             ▼
                    ═══════════════════════════
                    analytics pipeline
                    (triggered)
                    ═══════════════════════════
                             │
                             └── GOLD (3 cross-domain tables)

  3 pipelines, 35+ tables, 6 domains
  ═══════════════════════════════════════════════════
```

---

### Step 11 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| app_streams pipeline | Running | 19 tables: 7 Bronze + 8 Silver + 4 Gold |
| data_fabric pipeline | Running | 13 tables: 5 Bronze + 5 Silver + 3 Gold (empty) |
| analytics pipeline | Completed | 3 cross-domain Gold tables (partial data) |
| CDC domain Gold | Computing | financial_ratios, portfolio_summary, counterparty_health, desk_overview |
| API domain Gold | Empty | compliance_status, reference_rates, regulatory_metrics |
| Cross-domain Gold | Partial | risk_dashboard, regulatory_report, desk_pnl_exposure |

**Next:** Run `/silver-databricks-streaming:run-jobs` to execute the Python batch jobs, populate the API tables, and watch the data_fabric pipeline pick up new data.
