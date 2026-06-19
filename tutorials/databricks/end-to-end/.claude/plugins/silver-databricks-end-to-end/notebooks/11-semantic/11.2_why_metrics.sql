-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 11 · 11.2 — **Why a Metric View instead of just gold?**
-- MAGIC
-- MAGIC You already have governed gold tables (`gold_segment_portfolio`, `gold_contract_aging`) — documented,
-- MAGIC fast, physical. So why add `portfolio_metrics`? This notebook **proves** the gap with three runnable
-- MAGIC demonstrations, not assertions. Run on the **SQL warehouse** (read-only — it creates nothing).
-- MAGIC
-- MAGIC | | Pre-aggregated **gold** table | Governed **Metric View** |
-- MAGIC |---|---|---|
-- MAGIC | Stores | **values** at one fixed grain | the **definition** (measure formula) |
-- MAGIC | New slice (by region, by month) | new table / rewrite vs silver | same `MEASURE()`, new `GROUP BY` |
-- MAGIC | Ratios / non-additive measures | break when rolled up | recomputed correctly at any grain |
-- MAGIC | Consumers | each re-derives → **drift** | one definition for Genie + dashboard + SQL |
-- MAGIC
-- MAGIC > 💡 This isn't gold *vs* metric view — it's **both**. Gold is a materialized slice (fast, physical);
-- MAGIC > the metric view is the governed definition. They agree (11.1 proved `MATCH`). This notebook shows the
-- MAGIC > jobs a fixed gold rollup **can't** do.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Demo 1 — The "average of averages" trap (non-additive measures)
-- MAGIC `overdue_ratio = SUM(overdue) / SUM(billed)` is a **ratio** — it is **not additive**. If gold *stored*
-- MAGIC the ratio per segment, any consumer who later rolls those rows up (a natural thing to do) averages the
-- MAGIC per-segment ratios — and gets the **wrong** company number, because each segment carries a different
-- MAGIC billing weight.
-- MAGIC
-- MAGIC The CTE below simulates exactly that mistake; the second query is what a Metric View gives you.

-- COMMAND ----------

-- ❌ WRONG: roll up pre-computed per-segment ratios (what a stored gold ratio forces on you)
WITH stored_gold_ratio_by_segment AS (
  SELECT segment, MEASURE(overdue_ratio) AS overdue_ratio   -- pretend this was a physical gold column
  FROM silverline.gold.portfolio_metrics
  GROUP BY segment
)
SELECT round(avg(overdue_ratio), 4) AS company_overdue_ratio_WRONG
FROM stored_gold_ratio_by_segment;   -- averaging ratios ignores each segment's billing weight

-- COMMAND ----------

-- ✅ RIGHT: the Metric View recomputes SUM(overdue)/SUM(billed) at the grain you ask for (here: all-up)
SELECT round(MEASURE(overdue_ratio), 4) AS company_overdue_ratio_RIGHT
FROM silverline.gold.portfolio_metrics;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC **Result:** ~**0.1357** (wrong) vs ~**0.1129** (right) — a **2.3-point**, ~20% relative overstatement,
-- MAGIC from doing something that *looks* perfectly reasonable. A Metric View can't be rolled up wrong: it never
-- MAGIC stores the ratio, only the formula, and re-evaluates the numerator and denominator at your query grain.
-- MAGIC This is the single biggest reason semantic layers exist.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Demo 2 — A fixed gold rollup answers ONE grain; the metric view answers any
-- MAGIC `gold_segment_portfolio` is keyed by **segment** — look at its columns: there is **no `region`**. So
-- MAGIC "billed by region", or "by region × contract type", simply **cannot** come from it; you'd write fresh
-- MAGIC SQL against silver (and re-implement the measure — the drift risk returns).

-- COMMAND ----------

DESCRIBE TABLE silverline.gold.gold_segment_portfolio;   -- segment-grain only — no region, no month

-- COMMAND ----------

-- The metric view answers a grain gold never pre-computed — one GROUP BY, same governed measure:
SELECT region, contract_type,
       MEASURE(total_billed)     AS total_billed,
       round(MEASURE(overdue_ratio), 4) AS overdue_ratio
FROM silverline.gold.portfolio_metrics
GROUP BY region, contract_type
ORDER BY total_billed DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC With **6 dimensions** you could be asked for any of dozens of slice combinations. Pre-aggregating each as
-- MAGIC its own gold table is a combinatorial explosion (and every copy re-implements the measures). **One**
-- MAGIC metric-view definition covers them all.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Demo 3 — One definition, identical everywhere (no drift across consumers)
-- MAGIC Hand-writing "overdue ratio" invites disagreement — different filters, denominators, NULL handling.
-- MAGIC Below, a plausible **hand-rolled** version divides only within `overdue + open`, **forgetting that 87%
-- MAGIC of billing is already `paid`** — so its denominator collapses and the KPI detonates:

-- COMMAND ----------

-- ❌ hand-rolled by analyst A — looks fine, wrong denominator (excludes paid invoices)
SELECT round(
         sum(CASE WHEN status = 'overdue' THEN amount END) /
         sum(CASE WHEN status IN ('overdue','open') THEN amount END), 4) AS overdue_ratio_handrolled
FROM silverline.silver.silver_invoices;

-- COMMAND ----------

-- ✅ the governed measure — every consumer (this query, Genie, the dashboard) gets the SAME number
SELECT round(MEASURE(overdue_ratio), 4) AS overdue_ratio_governed
FROM silverline.gold.portfolio_metrics;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC **Result:** ~**0.8494** (hand-rolled) vs ~**0.1129** (governed) — the same KPI off by **7.5×**, from one
-- MAGIC wrong denominator. That's the drift a dashboard and a Genie answer would show on the *same metric*. The
-- MAGIC Metric View removes the entire class of bug: define `overdue_ratio` **once**, and every consumer —
-- MAGIC this query, Genie, the AI/BI dashboard (Stage 12) — reads that one definition.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Takeaways
-- MAGIC - **Non-additive measures** (ratios, distinct counts) can't be rolled up from stored values — the metric
-- MAGIC   view recomputes them correctly at any grain. *(Demo 1: 13.57% wrong → 11.29% right.)*
-- MAGIC - **A fixed gold rollup serves one grain;** the metric view serves any slice from one definition, with no
-- MAGIC   combinatorial table sprawl. *(Demo 2: gold has no `region`; the view slices by it instantly.)*
-- MAGIC - **One governed definition** = no drift between SQL, Genie, and dashboards. *(Demo 3.)*
-- MAGIC - **Keep the gold too** — it's the fast materialized slice; the metric view is the source-of-truth
-- MAGIC   definition. They agree by construction (11.1 = `MATCH`). ➡️ Next: `12-ai-bi` consumes this view.
