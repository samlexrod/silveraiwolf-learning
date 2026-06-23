-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 10 — Business layer: document gold + a curated view
-- MAGIC
-- MAGIC Make the gold tables a proper **business layer**: add table + column **COMMENTs** (the lakehouse
-- MAGIC equivalent of dbt `persist_docs`) so **Genie / AI assistants understand the schema**, plus a curated
-- MAGIC **`customer_360`** view. Comments seed the **semantic layer** + **Genie** stages next. Run on the **SQL warehouse**.
-- MAGIC
-- MAGIC > 🧠 Genie generates SQL from natural language by reading column COMMENTs — undocumented gold = worse answers.

-- COMMAND ----------

-- MAGIC %md ## 1 — Document `gold_segment_portfolio`

-- COMMAND ----------

COMMENT ON TABLE silverline.gold.gold_segment_portfolio IS 'Financing portfolio rolled up per customer segment — contract counts, principal, APR, residual.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN segment          COMMENT 'Customer business segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN contract_count   COMMENT 'Total lease/loan contracts in the segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN active_contracts COMMENT 'Contracts currently in active status.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN total_principal  COMMENT 'Sum of contract principal financed for the segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN avg_apr          COMMENT 'Average annual percentage rate across the segment''s contracts.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN total_residual   COMMENT 'Sum of residual (end-of-term) value across the segment''s contracts.';

-- COMMAND ----------

-- MAGIC %md ## 2 — Document `gold_contract_aging`

-- COMMAND ----------

COMMENT ON TABLE silverline.gold.gold_contract_aging IS 'Billing/collections aging per contract — overdue / open / paid / total billed.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN contract_id    COMMENT 'Lease/loan contract identifier.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN overdue_amount COMMENT 'Sum of overdue invoice amounts for the contract.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN open_amount    COMMENT 'Sum of open (billed, not yet paid or overdue) invoice amounts.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN paid_amount    COMMENT 'Sum of paid invoice amounts.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN total_billed   COMMENT 'Sum of all invoice amounts billed against the contract.';

-- COMMAND ----------

-- MAGIC %md ## 3 — Curated `customer_360` view
-- MAGIC `gold_contract_aging` is keyed by contract; roll it up to the customer (via `silver_contracts`) for a
-- MAGIC one-row-per-customer collections surface — the grain Genie + dashboards want.

-- COMMAND ----------

CREATE OR REPLACE VIEW silverline.gold.customer_360 (
  customer_id    COMMENT 'Customer id',
  legal_name     COMMENT 'Customer legal name',
  segment        COMMENT 'Business segment',
  region         COMMENT 'Region',
  credit_rating  COMMENT 'Credit rating',
  overdue_amount COMMENT 'Overdue billed amount across the customer''s contracts',
  total_billed   COMMENT 'Total billed amount across the customer''s contracts'
) COMMENT 'Per-customer collections view: profile + contract aging — the curated business surface.'
AS
SELECT c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating,
       sum(a.overdue_amount) AS overdue_amount,
       sum(a.total_billed)   AS total_billed
FROM silverline.gold.gold_contract_aging a
JOIN silverline.silver.silver_contracts ct ON ct.contract_id = a.contract_id
JOIN silverline.silver.silver_customers c  ON c.customer_id  = ct.customer_id
GROUP BY c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating;

-- COMMAND ----------

-- MAGIC %md ## 4 — Verify

-- COMMAND ----------

-- comments landed?
DESCRIBE TABLE EXTENDED silverline.gold.gold_segment_portfolio;

-- COMMAND ----------

-- the curated view returns rows (top overdue customers)
SELECT customer_id, legal_name, segment, overdue_amount, total_billed
FROM silverline.gold.customer_360
ORDER BY overdue_amount DESC
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ Gold documented (table + column COMMENTs) + `customer_360` curated view. These comments power
-- MAGIC **Genie** + the **Metric View** semantic layer. ➡️ Next: `11-semantic`.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
