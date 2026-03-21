---
description: "[Stage 5] Deploy the Gold pipeline, run it on Databricks, and verify business metrics"
---

# Gold — Business Metrics (Data Marts)

Deploy and run the final layer of the medallion architecture — purpose-built aggregations shaped for specific business consumers: risk analysts, compliance officers, and traders.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 4 (run-silver), the learner has:
- Bronze + Silver tables populated in `main.financial_risk`
- Silver expectations tested with dirty data, then cleaned up
- `databricks.yml` scoped to Bronze + Silver (Gold still commented out)
- A working dev loop: edit → test → deploy → verify

This stage adds the Gold layer to the pipeline, deploys it, and verifies that business metrics are correct.

---

## Instructions

---

### Step 1 — Verify Prerequisites

Confirm Silver tables exist and auth works:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
```

Verify Silver tables have data by querying row counts:

```bash
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"SELECT 'silver_counterparties' as tbl, COUNT(*) as cnt FROM main.financial_risk.silver_counterparties UNION ALL SELECT 'silver_transactions', COUNT(*) FROM main.financial_risk.silver_transactions UNION ALL SELECT 'silver_market_data', COUNT(*) FROM main.financial_risk.silver_market_data UNION ALL SELECT 'silver_positions', COUNT(*) FROM main.financial_risk.silver_positions\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

If Silver tables are empty or missing, tell the user to run `/silver-databricks:run-silver` first.

---

### Step 2 — Explain What Gold Does

Tell the user:

> **Gold = Business Metrics.** This is where clean data becomes actionable. Gold tables are purpose-built for specific consumers — they answer business questions directly, without requiring analysts to write complex joins or aggregations.
>
> ```
>  Silver (clean, enriched)                Gold (business metrics)
>  ────────────────────────                ──────────────────────────
>
>  silver_counterparties ─────────────>  gold_financial_ratios
>    total_assets, equity, debt...         current_ratio, debt_to_equity,
>                                          ROE, ROA, net_profit_margin
>
>  silver_positions ──────────────────>  gold_risk_exposure
>  silver_counterparties ─┘               gross_exposure, concentration_pct,
>                                          risk_tier (LOW/MEDIUM/HIGH/CRITICAL)
>
>  silver_positions ──────────────────>  gold_portfolio_summary
>  silver_counterparties ─┘               aggregations by sector, instrument
>                                          type, and currency
> ```
>
> Each Gold table serves a different audience:
>
> | Table | Consumer | Question It Answers |
> |---|---|---|
> | `gold_financial_ratios` | Risk analysts | "Is this counterparty financially healthy?" |
> | `gold_risk_exposure` | Compliance officers | "Where is our portfolio concentrated? Who is high risk?" |
> | `gold_portfolio_summary` | Traders / executives | "What's our exposure by sector and instrument type?" |
>
> Gold is your **semantic layer** — business concepts expressed as reusable, governed metrics with shared definitions. Instead of every analyst writing their own "net exposure" calculation, Gold tables encode it once.

---

### Step 3 — Walk Through the Source Files

Tell the user:

> Let's look at each Gold source file before deploying. These are simpler than Silver — no cleaning or deduplication needed. Silver already handled that. Gold is pure business logic.

**File 1: `src/financial_risk/gold/financial_ratios.py`**

Read the file and present with this structure:

> ### `gold_financial_ratios`
>
> | Property | Value |
> |---|---|
> | **Source** | `silver_counterparties` |
> | **Read mode** | Batch (`sp.read`) |
> | **Consumer** | Risk analysts |
>
> **Ratios computed:**
>
> | Category | Ratio | Formula |
> |---|---|---|
> | Liquidity | `current_ratio` | current_assets / current_liabilities |
> | Liquidity | `quick_ratio` | (current_assets × 0.7) / current_liabilities |
> | Leverage | `debt_to_equity` | total_debt / total_equity |
> | Leverage | `interest_coverage` | ebit / interest_expense (null if expense = 0) |
> | Profitability | `roe` | net_income / total_equity |
> | Profitability | `roa` | net_income / total_assets |
> | Profitability | `net_profit_margin` | net_income / revenue (null if revenue = 0) |
>
> **Expectations** (1 — warn):
>
> | Expectation | Condition |
> |---|---|
> | `valid_counterparty` | `counterparty_id IS NOT NULL` |
>
> This is the simplest Gold table — a pure `select` with computed columns. No joins, no aggregations.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to risk exposure" and "I have questions about this file".

**File 2: `src/financial_risk/gold/risk_exposure.py`**

Read the file and present with this structure:

> ### `gold_risk_exposure`
>
> | Property | Value |
> |---|---|
> | **Source** | `silver_positions` + `silver_counterparties` |
> | **Read mode** | Batch (`sp.read`) |
> | **Consumer** | Compliance officers |
>
> **Transformations:**
> 1. Calculates total portfolio value (sum of absolute market values)
> 2. Aggregates per counterparty: gross exposure, net exposure, unrealized P&L, instrument count
> 3. Cross-joins with total portfolio to compute `concentration_pct`
> 4. Joins counterparty details (name, sector, credit rating)
> 5. Assigns `risk_tier` based on concentration:
>
> | Concentration | Risk Tier |
> |---|---|
> | > 20% | CRITICAL |
> | > 10% | HIGH |
> | > 5% | MEDIUM |
> | ≤ 5% | LOW |
>
> **Expectations** (1 — warn):
>
> | Expectation | Condition |
> |---|---|
> | `valid_counterparty` | `counterparty_id IS NOT NULL` |
>
> The `crossJoin` with total portfolio value is safe here because `total_portfolio` is a single-row DataFrame (one aggregate). In production, you'd verify this assumption doesn't change.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to portfolio summary" and "I have questions about this file".

**File 3: `src/financial_risk/gold/portfolio_summary.py`**

Read the file and present with this structure:

> ### `gold_portfolio_summary`
>
> | Property | Value |
> |---|---|
> | **Source** | `silver_positions` + `silver_counterparties` |
> | **Read mode** | Batch (`sp.read`) |
> | **Consumer** | Traders / executives |
>
> **Transformations:**
> 1. Joins positions with counterparty details (sector, country)
> 2. Groups by `(sector, instrument_type, currency)`
> 3. Computes: total market value, gross market value, total unrealized P&L, net quantity, counterparty count, instrument count
> 4. Derives `avg_pnl_per_counterparty`
> 5. Orders by gross market value descending
>
> **Expectations:** None — this is a summary table. Data quality was enforced in Silver.
>
> This table answers questions like "What's our total equity exposure in the technology sector?" or "Which currency has the highest unrealized P&L?"

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue — deploy Gold" and "I have questions about this file".

---

### Step 4 — Scope the Pipeline to All Layers

Tell the user:

> Now I'll update `databricks.yml` to include all three layers — Bronze, Silver, and Gold. This is the full pipeline.

Edit `databricks.yml` — uncomment the Gold entries:

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
        # Gold — business metrics
        - file:
            path: src/financial_risk/gold/financial_ratios.py
        - file:
            path: src/financial_risk/gold/risk_exposure.py
        - file:
            path: src/financial_risk/gold/portfolio_summary.py
```

After editing, confirm:

> ✓ `databricks.yml` updated — all three layers active: Bronze + Silver + Gold.

---

### Step 5 — Run Local Tests

Tell the user:

> Before deploying, let's run the local tests. The unit tests in `tests/unit/test_ratios.py` validate the exact same financial ratio calculations Gold uses — current ratio, debt-to-equity, interest coverage, ROE, and net profit margin.

Run:

```bash
export JAVA_HOME=$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

If tests pass:

> ✓ All tests passing, lint clean. Safe to deploy.

---

### Step 6 — Deploy and Validate

Tell the user:

> Deploying the complete pipeline — Bronze + Silver + Gold.

Run:

```bash
mise run deploy:dev
```

Then validate:

```bash
databricks bundle validate --target dev
```

If both succeed:

> ✓ Bundle deployed and validated — full medallion pipeline ready to run.

---

### Step 7 — Run the Pipeline

Tell the user:

> Time to run the complete pipeline. Since Gold reads from Silver (which reads from Bronze), Databricks resolves the full dependency chain:
>
> ```
>  Bronze                Silver                  Gold
>  ──────                ──────                  ────
>  counterparties ────>  counterparties ──┬───>  financial_ratios
>  transactions   ────>  transactions  ──┤
>  market_data    ────>  market_data   ──┤───>  risk_exposure
>                        positions     ──┤
>                                        └───>  portfolio_summary
> ```
>
> We'll use `--full-refresh` so Gold tables are populated from scratch.

Extract the pipeline ID:

```bash
PIPELINE_ID=$(databricks pipelines list-pipelines -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['pipeline_id'])")
```

Start the pipeline:

```bash
databricks pipelines start-update $PIPELINE_ID --full-refresh
```

Tell the user:

> Pipeline is running. I'll check the status — this typically takes 1–3 minutes on serverless.

Also tell the user they can watch live:

> While the pipeline runs, you can watch it in the Databricks UI:
> 1. Open your workspace → **Workflows → Delta Live Tables**
> 2. Click on the pipeline — you'll see the full graph: Bronze → Silver → Gold
> 3. Gold tables appear at the rightmost end of the dependency chain

Poll for completion (same pattern as previous stages — check every 30 seconds, up to 5 minutes).

**If `COMPLETED`**:

> ✓ Pipeline run completed — full medallion pipeline!

**If `FAILED`**, extract the error and help troubleshoot:
- **Silver table not found**: Silver tables may have been dropped — re-run `/silver-databricks:run-silver`
- **Division by zero**: Check if any counterparty has zero equity or zero liabilities — the `F.when` guards should handle this, but verify
- **Import error**: Check Gold Python files for typos

---

### Step 8 — Verify Gold Tables

Tell the user:

> Let's verify the Gold tables. I'll check row counts and sample key metrics.

Query row counts for all tables:

```sql
SELECT 'gold_financial_ratios' as tbl, COUNT(*) as cnt FROM main.financial_risk.gold_financial_ratios
UNION ALL SELECT 'gold_risk_exposure', COUNT(*) FROM main.financial_risk.gold_risk_exposure
UNION ALL SELECT 'gold_portfolio_summary', COUNT(*) FROM main.financial_risk.gold_portfolio_summary
```

Display the results alongside Silver for context:

```
┌────────────────────────────┬───────┬───────────────────────────────────────┐
│  Table                     │ Rows  │  What it represents                   │
├────────────────────────────┼───────┼───────────────────────────────────────┤
│  gold_financial_ratios     │  ~20  │  1 row per counterparty               │
│  gold_risk_exposure        │  ~20  │  1 row per counterparty with exposure │
│  gold_portfolio_summary    │  var  │  1 row per (sector, type, currency)   │
└────────────────────────────┴───────┴───────────────────────────────────────┘
```

Adapt to actual counts.

---

### Step 9 — Explore the Business Metrics

Tell the user:

> Let's look at the actual business metrics Gold produced. These are the tables that risk analysts, compliance officers, and traders would query directly.

#### 9a — Financial Ratios

Query:

```sql
SELECT counterparty_id, name, credit_rating,
       current_ratio, debt_to_equity, interest_coverage, roe, net_profit_margin
FROM main.financial_risk.gold_financial_ratios
ORDER BY current_ratio ASC LIMIT 10
```

Display results in a formatted table. Then present the risk analyst's reading guide as a reference table:

> ### How a risk analyst reads these ratios
>
> | Red Flag | What It Means |
> |---|---|
> | `current_ratio` < 1.0 | Current liabilities exceed current assets — may struggle to pay short-term debts |
> | `debt_to_equity` > 2.0 | Heavy leverage — significant debt relative to equity |
> | `interest_coverage` < 1.5 | Barely covering interest payments — default risk |
> | `roe` < 0 | Losing money — net income is negative |
> | `net_profit_margin` < 0 | Revenue doesn't cover costs |

After showing the data, call out specific counterparties from the results that hit these thresholds. Present each callout as a labeled block:

> **Counterparties to watch:**
>
> Point out 2-3 counterparties from the actual results that trigger red flags, formatted as:
>
> `COUNTERPARTY_NAME` (rating: X) — current_ratio Y, debt_to_equity Z. Why this matters in one sentence.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to risk exposure" and "I have questions about the ratios".

#### 9b — Risk Exposure

Query:

```sql
SELECT counterparty_id, name, credit_rating, risk_tier,
       concentration_pct, gross_exposure, net_exposure, instrument_count
FROM main.financial_risk.gold_risk_exposure
ORDER BY concentration_pct DESC LIMIT 10
```

Display results in a formatted table. Then present the risk tier reference:

> ### Risk tier thresholds
>
> | Tier | Concentration | Action Required |
> |---|---|---|
> | CRITICAL | > 20% | Immediate attention — position limits may be breached |
> | HIGH | > 10% | Active monitoring — escalate to risk committee |
> | MEDIUM | > 5% | Standard review — within normal operating range |
> | LOW | <= 5% | Normal operations — no action needed |

After showing the data, present observations as labeled callout blocks — not a bullet list. For each observation, explain *what you see* and *what a compliance officer would do about it*:

> **Highest concentration:** `COUNTERPARTY_NAME` at X% — what this means for the portfolio.
>
> **Interesting hedge:** Point out any counterparty with large gross exposure but near-zero net exposure — this means they're hedged.
>
> **Credit + concentration risk:** Point out any counterparty with both low credit rating AND high concentration — this is the dangerous combination.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to portfolio summary" and "I have questions about risk exposure".

#### 9c — Portfolio Summary

Query:

```sql
SELECT sector, instrument_type, currency,
       total_market_value, gross_market_value, total_unrealized_pnl,
       counterparty_count, instrument_count
FROM main.financial_risk.gold_portfolio_summary
ORDER BY gross_market_value DESC LIMIT 10
```

Display results in a formatted table. Then present what each column answers:

> ### Reading the executive dashboard
>
> | Column | Business Question |
> |---|---|
> | `gross_market_value` | "What's our biggest exposure by sector?" |
> | `total_unrealized_pnl` | "Where are we making or losing money?" |
> | `instrument_count` | "How diversified are we?" |
> | `counterparty_count` | "How many counterparties are in this segment?" |
> | `avg_pnl_per_counterparty` | "What's the average P&L impact per counterparty?" |

After showing the data, present observations as labeled callout blocks:

> **Dominant sector:** Which sector appears most in the top rows? What does this mean for diversification?
>
> **P&L concentration:** Which segment has the largest unrealized loss? Is it spread across many counterparties or concentrated?
>
> **Diversification signal:** How many instruments and counterparties are in the top segments? More = better diversified.

**PAUSE** — use `AskUserQuestion` to ask if the user is ready to continue. Offer "Continue to summary" and "I have questions about the metrics".

---

### Step 10 — What Just Happened

Tell the user:

> Here's the full picture — the complete medallion pipeline:
>
> ```
>  Stage 2: Raw Volume     Stage 3: Bronze        Stage 4: Silver          Stage 5: Gold
>  ──────────────────      ─────────────────      ──────────────────       ──────────────────
>
>  counterparties.csv ──>  bronze_cp       ───>  silver_cp         ──┬─>  gold_financial_ratios
>                                                                    │      7 ratios per CP
>  transactions.csv   ──>  bronze_txn      ───>  silver_txn        ──┤
>                                                silver_positions   ──┼─>  gold_risk_exposure
>  market_data.csv    ──>  bronze_mkt      ───>  silver_mkt        ──┤      risk tiers per CP
>                                                                    │
>                                                                    └─>  gold_portfolio_summary
>                                                                           sector/type/currency
>
>     CSV files            raw Delta tables       clean, enriched          business metrics
> ```
>
> **What each layer does:**
>
> 1. **Bronze** — ingests raw data as-is. Append-only, no transformations. Your safety net.
> 2. **Silver** — cleans, validates, deduplicates, and enriches. Data quality expectations catch bad rows. Derived tables combine sources.
> 3. **Gold** — computes business metrics from Silver. Purpose-built for specific consumers. No cleaning needed — Silver handled that.
>
> **Why this layering matters:**
>
> - **Reprocessing** — if a Gold calculation changes (e.g., new risk tier thresholds), you only re-run Gold. Bronze and Silver stay untouched.
> - **Data quality** — expectations in Silver act as a firewall. Bad data doesn't leak into Gold metrics.
> - **Multiple consumers** — different Gold tables serve different teams from the same Silver foundation. No one duplicates cleaning logic.

---

### Step 10b — Who Consumes Gold? Business Scenarios

Tell the user:

> Gold tables are the **consumption layer** — the place where the rest of the organization connects. The pipeline you just built doesn't end at a table. It feeds business decisions, applications, and systems. Here's how:

Present the following as a structured visual:

> ### Business Stakeholders
>
> ```
>  gold_financial_ratios ──────┬──> Risk Analysts (Databricks SQL / Notebooks)
>                              ├──> BI Dashboards (Power BI, Tableau, Looker)
>                              └──> Credit Review Workflows
>
>  gold_risk_exposure ─────────┬──> Compliance Officers (SQL Alerts)
>                              ├──> Regulatory Reporting (scheduled exports)
>                              └──> Risk Committee Decks (BI tools)
>
>  gold_portfolio_summary ─────┬──> Traders (real-time dashboards)
>                              ├──> Executive Summaries (BI tools)
>                              └──> Portfolio Optimization Models (ML)
> ```
>
> ### Applications and API Wrappers
>
> Gold tables are also the foundation for applications that serve the business programmatically:
>
> | Layer | What It Does | Example |
> |---|---|---|
> | **BI Dashboards** | Visual analytics on Gold tables — no SQL needed for end users | Power BI connected to `gold_risk_exposure`, auto-refreshing on pipeline runs |
> | **SQL Alerts** | Trigger notifications when Gold data crosses thresholds | Databricks SQL alert: "Notify Slack when any counterparty reaches CRITICAL risk tier" |
> | **REST APIs** | Wrap Gold queries in API endpoints for internal apps | FastAPI service querying `gold_financial_ratios` — mobile app shows a counterparty's health score |
> | **ML Feature Stores** | Gold metrics become features for ML models | `current_ratio`, `debt_to_equity`, `concentration_pct` feed a credit default prediction model |
> | **Neurosymbolic Guardrails** | Combine Gold metrics with symbolic rules for deterministic AI decisions | An LLM agent checks `gold_risk_exposure` before approving a trade — if `risk_tier = CRITICAL`, the agent blocks the trade with a structured explanation, no hallucination possible |
> | **Agentic Workflows** | AI agents query Gold tables as tool calls for context-aware decisions | A Claude agent with MCP tool access queries `gold_portfolio_summary` to answer "What's our FX exposure in Asia?" — grounded in real pipeline data, not training data |
>
> ### The Key Insight
>
> Tell the user:
>
> > Gold tables are **governed, versioned, and pipeline-backed**. Every number has a lineage trace back to the raw CSV that produced it. When an executive asks "where did this risk number come from?", you can trace it:
> >
> > ```
> > gold_risk_exposure.concentration_pct = 6.22%
> >   ↑ computed from silver_positions.market_value (sum of abs values)
> >     ↑ derived from silver_transactions (signed quantities) + silver_market_data (latest prices)
> >       ↑ cleaned from bronze_transactions + bronze_market_data
> >         ↑ ingested from /Volumes/.../raw/transactions.csv + market_data.csv
> > ```
> >
> > This lineage is what separates a production data platform from a collection of ad-hoc queries. It's also what makes Gold safe to expose to AI systems — the data is deterministic, traceable, and governed by expectations at every layer.

---

### Step 11 — Summary

Display a summary:

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 5 — Gold (Data Marts) Complete!                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Bundle:     ✓ Deployed (Bronze + Silver + Gold, dev mode)    │
│  Validation: ✓ Dry run passed                                 │
│  Execution:  ✓ Full refresh completed                         │
│                                                               │
│  Tables created:                                              │
│    gold_financial_ratios    7 ratios per counterparty          │
│    gold_risk_exposure       risk tiers + concentration         │
│    gold_portfolio_summary   sector/type/currency aggregations  │
│                                                               │
│  Full pipeline:                                               │
│    Bronze:  3 tables (raw ingestion)                          │
│    Silver:  4 tables (clean + enriched + derived)             │
│    Gold:    3 tables (business metrics)                       │
│    Total:   10 tables, 13 Silver expectations                 │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  Dev loop                                                     │
├───────────────────────────────────────────────────────────────┤
│  mise run test         Run local tests                        │
│  mise run lint         Lint check                             │
│  mise run deploy:dev   Push changes to Databricks             │
│  mise run deploy:prod  Deploy to production                   │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  Medallion Architecture — Complete!                           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  You've built a production-ready data pipeline from scratch:  │
│  raw files → staging → cleaned → business metrics             │
│                                                               │
│  From here, you could:                                        │
│  - Connect BI tools (Power BI, Tableau) to Gold tables        │
│  - Set up SQL alerts on risk_tier changes                     │
│  - Build REST APIs wrapping Gold queries (FastAPI)            │
│  - Feed Gold metrics into ML feature stores                   │
│  - Add neurosymbolic guardrails for AI agent decisions        │
│  - Expose Gold via MCP tools for agentic workflows            │
│  - Schedule the pipeline for daily runs                       │
│  - Deploy to production with mise run deploy:prod             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Important

- **Pipeline now includes all three layers** — Bronze + Silver + Gold. This is the complete medallion architecture.
- **Gold tables are all batch** (`sp.read`) — they compute metrics from Silver tables that are already materialized. No streaming needed.
- **Gold has minimal expectations** — only `valid_counterparty` on two tables. Data quality enforcement happens in Silver; Gold trusts Silver's output.
- **`gold_portfolio_summary` has no expectations at all** — it's a summary aggregation. If the input data is valid (Silver guarantees this), the output is valid.
- **The `crossJoin` in `gold_risk_exposure`** is safe because `total_portfolio` is a single-row DataFrame. This is a common pattern for computing percentages against a total.
- **`--full-refresh`** is recommended for this stage because it's the first time Gold tables are created. On subsequent runs without schema changes, you can omit it — Gold tables are materialized views that recompute automatically.
- If the SQL Statements API doesn't work on Free Edition, always fall back to the UI — Catalog browser and pipeline graph are reliable alternatives.
