-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 8 · Parity — the three builds are identical
-- MAGIC
-- MAGIC You built the same medallion three ways. This proves they produce the **same gold**:
-- MAGIC
-- MAGIC | Build | Notebook | Gold tables |
-- MAGIC |---|---|---|
-- MAGIC | **notebook** (Spark SQL) | `08.1_build_notebook` | `gold_segment_portfolio_nb`, `gold_contract_aging_nb` |
-- MAGIC | **dbt** (`dbtRunner`) | `08.3_build_dbt` | `gold_segment_portfolio`, `gold_contract_aging` |
-- MAGIC | **SDP** (Lakeflow) | `08.2_build_sdp` | `segment_portfolio_sdp`, `contract_aging_sdp` |
-- MAGIC
-- MAGIC **Run on the SQL warehouse.** Run `08.1`/`08.2`/`08.3` first so all three exist.

-- COMMAND ----------

-- MAGIC %md ## The three golds, side by side (financing portfolio by segment)

-- COMMAND ----------

SELECT 'notebook' AS build, * FROM silverline.gold.gold_segment_portfolio_nb
UNION ALL SELECT 'dbt', * FROM silverline.gold.gold_segment_portfolio
UNION ALL SELECT 'sdp', * FROM silverline.gold.segment_portfolio_sdp
ORDER BY build, total_principal DESC;

-- COMMAND ----------

-- MAGIC %md ## Parity — `segment_portfolio`: notebook == dbt == SDP (every diff should be 0)

-- COMMAND ----------

SELECT
 (SELECT count(*) FROM silverline.gold.gold_segment_portfolio_nb) AS nb_rows,
 (SELECT count(*) FROM silverline.gold.gold_segment_portfolio)    AS dbt_rows,
 (SELECT count(*) FROM silverline.gold.segment_portfolio_sdp)     AS sdp_rows,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_segment_portfolio_nb EXCEPT SELECT * FROM silverline.gold.gold_segment_portfolio)) AS nb_minus_dbt,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_segment_portfolio EXCEPT SELECT * FROM silverline.gold.gold_segment_portfolio_nb)) AS dbt_minus_nb,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_segment_portfolio_nb EXCEPT SELECT * FROM silverline.gold.segment_portfolio_sdp)) AS nb_minus_sdp,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.segment_portfolio_sdp EXCEPT SELECT * FROM silverline.gold.gold_segment_portfolio_nb)) AS sdp_minus_nb;

-- COMMAND ----------

-- MAGIC %md ## Parity — `contract_aging` (85 contracts)

-- COMMAND ----------

SELECT
 (SELECT count(*) FROM silverline.gold.gold_contract_aging_nb) AS nb_rows,
 (SELECT count(*) FROM silverline.gold.gold_contract_aging)    AS dbt_rows,
 (SELECT count(*) FROM silverline.gold.contract_aging_sdp)     AS sdp_rows,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_contract_aging_nb EXCEPT SELECT * FROM silverline.gold.gold_contract_aging)) AS nb_minus_dbt,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_contract_aging EXCEPT SELECT * FROM silverline.gold.gold_contract_aging_nb)) AS dbt_minus_nb,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.gold_contract_aging_nb EXCEPT SELECT * FROM silverline.gold.contract_aging_sdp)) AS nb_minus_sdp,
 (SELECT count(*) FROM (SELECT * FROM silverline.gold.contract_aging_sdp EXCEPT SELECT * FROM silverline.gold.gold_contract_aging_nb)) AS sdp_minus_nb;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Same result — different trade-off
-- MAGIC All three are **correctness-equal**; pick on operations:
-- MAGIC - **notebook (Spark SQL)** — most direct, full control, in-platform; pair with a **Job/Workflow** to schedule it.
-- MAGIC - **dbt** — SQL framework with refs/tests/docs/lineage; portable across engines (Snowflake/BigQuery), but scheduler/lineage live in paid **dbt Cloud**.
-- MAGIC - **SDP / Lakeflow** — *declarative*: tables + `@dlt.expect` quality, managed materialized views + incremental refresh; least code to operate.
-- MAGIC
-- MAGIC **Orchestration is a separate axis:** any of these can be run on a schedule by a **Databricks Job** (the
-- MAGIC notebook + dbt builds as Job tasks; the SDP build as a pipeline). Native covers dbt's ground without
-- MAGIC dbt Cloud cost (~$200–$400/dev/mo); dbt's edge is cross-engine portability.
-- MAGIC [LatentView](https://www.latentview.com/blog/dbt-vs-databricks/) ·
-- MAGIC [Materialized views](https://docs.databricks.com/aws/en/ldp/dbsql/materialized) ·
-- MAGIC [dbt Cloud pricing](https://b-eye.com/blog/dbt-cloud-pricing/) · ➡️ Next: stage 09 (`refresh`).
