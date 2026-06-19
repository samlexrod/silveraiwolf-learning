-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 11 — Semantic layer: a governed **Metric View**
-- MAGIC
-- MAGIC `gold_segment_portfolio` answers **one** question (portfolio *by segment*). A **Metric View** answers
-- MAGIC *every* slice of the same governed billing measures — by region, credit rating, contract type, status,
-- MAGIC month — from **one definition**, so "billed" and "overdue ratio" can't drift between a dashboard, a
-- MAGIC notebook, and Genie. Run on the **SQL warehouse**.
-- MAGIC
-- MAGIC | One gold rollup per question | One Metric View, every question |
-- MAGIC |---|---|
-- MAGIC | `gold_segment_portfolio` = billed-by-segment only | `MEASURE(total_billed)` sliced by any dimension |
-- MAGIC | New slice (region, contract type) = new SQL/table | Same measure, new `GROUP BY` |
-- MAGIC | "Overdue ratio" reimplemented per query → drift | One `overdue_ratio` definition, reused everywhere |
-- MAGIC
-- MAGIC > 🧠 **Measures are definitions, not stored values** — resolved at whatever grain you query. Nothing is
-- MAGIC > copied; the view is a UC metadata object over the silver billing fact.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — Create the Metric View
-- MAGIC `WITH METRICS LANGUAGE YAML` over `silver_invoices` (the conformed billing fact — carries `customer_id`,
-- MAGIC `contract_type`, `status`, `invoice_date`, `amount`) joined to `silver_customers` for `segment` / `region` /
-- MAGIC `credit_rating`. **measures:** `total_billed`, `invoice_count`, `overdue_amount`, `overdue_ratio` ·
-- MAGIC **dimensions:** segment, region, credit_rating, contract_type, status, invoice_date.

-- COMMAND ----------

CREATE OR REPLACE VIEW silverline.gold.portfolio_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed Silverline Capital billing metrics — single source of truth for billed/overdue, sliceable by any dimension.'
AS $$
version: 0.1
source: silverline.silver.silver_invoices
joins:
  - name: customer
    source: silverline.silver.silver_customers
    'on': source.customer_id = customer.customer_id
dimensions:
  - name: segment
    expr: customer.segment
  - name: region
    expr: customer.region
  - name: credit_rating
    expr: customer.credit_rating
  - name: contract_type
    expr: source.contract_type
  - name: status
    expr: source.status
  - name: invoice_date
    expr: source.invoice_date
measures:
  - name: total_billed
    expr: SUM(amount)
  - name: invoice_count
    expr: COUNT(1)
  - name: overdue_amount
    expr: SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END)
  - name: overdue_ratio
    expr: SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END) / SUM(amount)
$$;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Query it: one definition, any slice
-- MAGIC You read measures with **`MEASURE(<name>)`** and slice with any `GROUP BY`. First, the governed
-- MAGIC equivalent of the segment rollup:

-- COMMAND ----------

SELECT segment,
       MEASURE(total_billed)  AS total_billed,
       MEASURE(invoice_count) AS invoice_count
FROM silverline.gold.portfolio_metrics
GROUP BY segment
ORDER BY total_billed DESC;

-- COMMAND ----------

-- MAGIC %md The **same** measures, re-sliced — no new table, no re-implemented logic. Loans run hotter on
-- MAGIC overdue than leases; the West region is the worst:

-- COMMAND ----------

SELECT region, contract_type,
       round(MEASURE(overdue_ratio), 4) AS overdue_ratio
FROM silverline.gold.portfolio_metrics
GROUP BY region, contract_type
ORDER BY overdue_ratio DESC;

-- COMMAND ----------

-- MAGIC %md And a time slice — billed by quarter — from the very same definition:

-- COMMAND ----------

SELECT date_trunc('quarter', invoice_date) AS qtr,
       MEASURE(total_billed) AS total_billed
FROM silverline.gold.portfolio_metrics
GROUP BY qtr
ORDER BY qtr;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 — Verify it matches gold
-- MAGIC `gold_contract_aging` rolls billing up per contract; the metric view rolls the **same** `silver_invoices`
-- MAGIC fact up by any dimension. Their grand total of billed amount must agree — same fact, same SUM, governed
-- MAGIC once. Expect **`MATCH`**.

-- COMMAND ----------

WITH m AS (SELECT MEASURE(total_billed) tb FROM silverline.gold.portfolio_metrics),
     g AS (SELECT sum(total_billed) tb FROM silverline.gold.gold_contract_aging)
SELECT (SELECT tb FROM m) AS metric_view_billed,
       (SELECT tb FROM g) AS gold_billed,
       CASE WHEN (SELECT tb FROM m) <=> (SELECT tb FROM g) THEN 'MATCH' ELSE 'DRIFT' END AS result;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ A governed **Metric View** `portfolio_metrics`: measures + dimensions defined **once**, sliceable any
-- MAGIC way via `MEASURE()`, and verified to **match** the physical gold (gold = a materialized slice; the metric
-- MAGIC view = the definition). This is the single source of truth **Genie** and the **AI/BI dashboard** consume next.
-- MAGIC ➡️ Next: `12-ai-bi`.
