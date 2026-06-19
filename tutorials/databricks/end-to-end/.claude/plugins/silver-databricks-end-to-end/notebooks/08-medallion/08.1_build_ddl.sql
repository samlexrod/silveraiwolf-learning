-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 8 · 08.1 — **DDL**: define the `_nb` medallion tables (empty)
-- MAGIC Pure **DDL** — just `CREATE TABLE IF NOT EXISTS` for the silver + gold `_nb` tables (structure only,
-- MAGIC no data). The **ELT** that loads them lives in `notebook_project/` and is run by `silverline-notebook-job`
-- MAGIC (built by `08.4_build_notebook`). Separating DDL (structure) from ELT (load) is the point. Run on the
-- MAGIC **SQL warehouse**. Idempotent.

-- COMMAND ----------
-- MAGIC %md ## silver table definitions
-- COMMAND ----------
CREATE TABLE IF NOT EXISTS silverline.silver.silver_customers_nb (
  customer_id    INT,
  legal_name     STRING,
  segment        STRING,
  region         STRING,
  credit_rating  STRING,
  annual_revenue DECIMAL(14,2),
  onboarded_date DATE
);
-- COMMAND ----------
CREATE TABLE IF NOT EXISTS silverline.silver.silver_contracts_nb (
  contract_id    INT,
  customer_id    INT,
  contract_type  STRING,
  status         STRING,
  principal      DECIMAL(14,2),
  apr            DECIMAL(6,4),
  term_months    INT,
  start_date     DATE,
  end_date       DATE,
  residual_value DECIMAL(14,2)
);
-- COMMAND ----------
CREATE TABLE IF NOT EXISTS silverline.silver.silver_invoices_nb (
  invoice_id    INT,
  contract_id   INT,
  customer_id   INT,
  contract_type STRING,
  invoice_date  DATE,
  due_date      DATE,
  amount        DECIMAL(12,2),
  status        STRING
);
-- COMMAND ----------
-- MAGIC %md ## gold table definitions
-- COMMAND ----------
CREATE TABLE IF NOT EXISTS silverline.gold.gold_segment_portfolio_nb (
  segment          STRING,
  contract_count   BIGINT,
  active_contracts BIGINT,
  total_principal  DECIMAL(38,2),
  avg_apr          DECIMAL(6,4),
  total_residual   DECIMAL(38,2)
);
-- COMMAND ----------
CREATE TABLE IF NOT EXISTS silverline.gold.gold_contract_aging_nb (
  contract_id    INT,
  overdue_amount DECIMAL(38,2),
  open_amount    DECIMAL(38,2),
  paid_amount    DECIMAL(38,2),
  total_billed   DECIMAL(38,2)
);
-- COMMAND ----------
-- MAGIC %md
-- MAGIC ✅ DDL done — empty `_nb` tables defined. Now `08.4_build_notebook` runs the **ELT** Job
-- MAGIC (`notebook_project/` → `INSERT OVERWRITE`) to load them.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
