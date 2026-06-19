-- Databricks notebook source
-- MAGIC %md
-- MAGIC # notebook_project · load_gold  (ELT task, depends on load_silver)
-- MAGIC **ELT** — `INSERT OVERWRITE` the gold tables (defined in `08.1_build_ddl`) from `silver_*_nb`.
-- MAGIC One table per cell.

-- COMMAND ----------
-- MAGIC %md ### gold_segment_portfolio_nb — financing portfolio by segment
-- COMMAND ----------
INSERT OVERWRITE TABLE silverline.gold.gold_segment_portfolio_nb
SELECT c.segment, count(*),
       sum(CASE WHEN ct.status='active' THEN 1 ELSE 0 END),
       sum(ct.principal), round(avg(ct.apr),4), sum(ct.residual_value)
FROM silverline.silver.silver_contracts_nb ct
JOIN silverline.silver.silver_customers_nb c ON c.customer_id = ct.customer_id
GROUP BY c.segment;

-- COMMAND ----------
-- MAGIC %md ### gold_contract_aging_nb — AR aging per contract
-- COMMAND ----------
INSERT OVERWRITE TABLE silverline.gold.gold_contract_aging_nb
SELECT contract_id,
       sum(CASE WHEN status='overdue' THEN amount ELSE 0 END),
       sum(CASE WHEN status='open' THEN amount ELSE 0 END),
       sum(CASE WHEN status='paid' THEN amount ELSE 0 END),
       sum(amount)
FROM silverline.silver.silver_invoices_nb
GROUP BY contract_id;
