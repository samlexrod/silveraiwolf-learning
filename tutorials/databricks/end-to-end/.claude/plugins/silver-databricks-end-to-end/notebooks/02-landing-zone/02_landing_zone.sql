-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 2 — Landing zone
-- MAGIC
-- MAGIC Create the **one Unity Catalog home** every later stage uses:
-- MAGIC `silverline` with medallion schemas (`bronze` / `silver` / `gold`) and a **managed volume**.
-- MAGIC
-- MAGIC On Free Edition you own the metastore and catalog (no service principal), so this is just a few
-- MAGIC idempotent `CREATE` statements. Run each cell top to bottom and watch the **Catalog Explorer**
-- MAGIC (left sidebar → Catalog) populate as you go.
-- MAGIC
-- MAGIC 💚 **Cost:** Free — UC objects cost nothing; the only compute is a few-second warehouse query (auto-stops when idle).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — Catalog + medallion schemas
-- MAGIC One catalog, schemas as the medallion. Every stage reads/writes `silverline.{bronze,silver,gold}`.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS silverline
  COMMENT 'Shared landing zone for the Databricks end-to-end tutorial phases (lakebase/lakehouse/analytics/ml/agents).';

CREATE SCHEMA IF NOT EXISTS silverline.bronze COMMENT 'Raw / ingested';
CREATE SCHEMA IF NOT EXISTS silverline.silver COMMENT 'Cleaned / current-state';
CREATE SCHEMA IF NOT EXISTS silverline.gold   COMMENT 'Business / serving';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Managed volume (seed files + contract PDFs)
-- MAGIC Free Edition has **no external storage**, so use a **managed** volume (Databricks-managed storage).
-- MAGIC Files will land under `/Volumes/silverline/bronze/files/`.

-- COMMAND ----------

CREATE VOLUME IF NOT EXISTS silverline.bronze.files
  COMMENT 'Managed volume — seed files + contract PDFs for the RAG track.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 — Verify
-- MAGIC Expect `bronze` / `silver` / `gold` (plus `default` / `information_schema`) and the `files` volume.

-- COMMAND ----------

SHOW SCHEMAS IN silverline;

-- COMMAND ----------

SHOW VOLUMES IN silverline.bronze;

-- COMMAND ----------

DESCRIBE VOLUME silverline.bronze.files;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ **Done.** Catalog `silverline`, the medallion schemas, and the managed volume all exist.
-- MAGIC Open **Catalog Explorer** and confirm you can see them. Next stage: `provision` (Lakebase OLTP).
