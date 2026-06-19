-- Databricks notebook source
-- MAGIC %md
-- MAGIC # notebook_project · load_silver  (ELT task of silverline-notebook-job)
-- MAGIC **ELT** — `INSERT OVERWRITE` the silver tables defined in `08.1_build_ddl` (load from bronze: typed,
-- MAGIC current-state, conformed). One table per cell. Idempotent; no schema changes.

-- COMMAND ----------
-- MAGIC %md ### silver_customers_nb — typed, latest row per customer
-- COMMAND ----------
INSERT OVERWRITE TABLE silverline.silver.silver_customers_nb
SELECT customer_id, legal_name, segment, region, credit_rating,
       cast(annual_revenue AS decimal(14,2)), cast(onboarded_date AS date)
FROM silverline.bronze.customers
QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;

-- COMMAND ----------
-- MAGIC %md ### silver_contracts_nb — typed, latest row per contract
-- COMMAND ----------
INSERT OVERWRITE TABLE silverline.silver.silver_contracts_nb
SELECT contract_id, customer_id, contract_type, status,
       cast(principal AS decimal(14,2)), cast(apr AS decimal(6,4)), term_months,
       cast(start_date AS date), cast(end_date AS date), cast(residual_value AS decimal(14,2))
FROM silverline.bronze.contracts
QUALIFY row_number() OVER (PARTITION BY contract_id ORDER BY updated_at DESC) = 1;

-- COMMAND ----------
-- MAGIC %md ### silver_invoices_nb — conformed with contract (carries customer_id + contract_type)
-- COMMAND ----------
INSERT OVERWRITE TABLE silverline.silver.silver_invoices_nb
SELECT i.invoice_id, i.contract_id, ct.customer_id, ct.contract_type,
       cast(i.invoice_date AS date), cast(i.due_date AS date), cast(i.amount AS decimal(12,2)), i.status
FROM silverline.bronze.invoices i
JOIN silverline.silver.silver_contracts_nb ct ON ct.contract_id = i.contract_id
WHERE i.invoice_id IS NOT NULL AND i.contract_id IS NOT NULL;
