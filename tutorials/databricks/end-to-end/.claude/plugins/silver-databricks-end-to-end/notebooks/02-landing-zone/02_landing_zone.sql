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
-- MAGIC Files will land under `/Volumes/silverline/bronze/files/`.
-- MAGIC
-- MAGIC 🧠 **Managed vs external — who owns the storage** (the same axis applies to **volumes and tables**):
-- MAGIC - **Managed** — Unity Catalog owns the metadata **and** the data files, in Databricks-managed storage;
-- MAGIC   UC picks the location and the lifecycle follows the object: **drop it → the files are deleted.** No cloud setup.
-- MAGIC - **External** — UC owns only the metadata; data lives at a `LOCATION` in **your own cloud bucket**
-- MAGIC   (S3/ADLS/GCS) via an external location + storage credential: **drop it → the files stay.**
-- MAGIC
-- MAGIC | | Managed | External |
-- MAGIC |---|---|---|
-- MAGIC | Data files | Databricks-managed | your cloud bucket (`LOCATION '…'`) |
-- MAGIC | Drop the object | files **deleted** | files **kept** |
-- MAGIC | Setup needed | none | external location + storage credential |
-- MAGIC | Free Edition | ✅ default (no setup) | ⚠️ opt-in via the AWS quickstart (your cloud, $) |
-- MAGIC
-- MAGIC On **Free Edition** there's no *built-in* external storage, so the tutorial stays **managed** throughout
-- MAGIC (this volume + every medallion **table** later). But external **is** possible: register an **external
-- MAGIC location** (e.g. the **AWS quickstart** → your own S3 bucket) + a storage credential, and external
-- MAGIC **tables and volumes** both become available — billed to **your** cloud account (real $), so it's opt-in.
-- MAGIC The optional **CDF** step in `ingest` is just one example that uses such an external-storage catalog.

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
-- MAGIC ## 4 — (Opt-in, real $) External storage on your own cloud
-- MAGIC Everything above is **managed** + free. This section is **optional** and **bills your own AWS account**
-- MAGIC (not Free Edition quota) — do it only to *see* external tables/volumes, or to enable the optional **CDF**
-- MAGIC step in `ingest`.
-- MAGIC
-- MAGIC 💳 The **AWS quickstart** runs a **CloudFormation** stack in your AWS → S3 bucket + IAM role, billed by AWS.
-- MAGIC `cleanup` drops the Databricks objects but **not** your AWS resources (delete that stack yourself).
-- MAGIC
-- MAGIC **Create the external location (UI):** Catalog → External Data → External Locations → **Create → AWS
-- MAGIC quickstart** → approve the CloudFormation stack; it registers the location + storage credential in UC.
-- MAGIC Then replace `<your-bucket>` below and run the cells. *(Manual SQL alt: `CREATE STORAGE CREDENTIAL …` +
-- MAGIC `CREATE EXTERNAL LOCATION … URL 's3://<your-bucket>/…' WITH (STORAGE CREDENTIAL …)`.)*

-- COMMAND ----------

-- Opt-in: list your registered external locations (find the url s3://<your-bucket>/…)
SHOW EXTERNAL LOCATIONS;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ⚠️ **Edit `<your-bucket>`** in the two statements below to YOUR external-location bucket, then run them.
-- MAGIC They error until the external location above exists — expected if you skipped the quickstart.

-- COMMAND ----------

-- External VOLUME — files live in YOUR S3 (drop → files kept), unlike the managed silverline.bronze.files
CREATE EXTERNAL VOLUME IF NOT EXISTS silverline.bronze.ext_files
  LOCATION 's3://<your-bucket>/ext_files'
  COMMENT 'External volume on your own S3 — contrast with the managed silverline.bronze.files.';

-- COMMAND ----------

-- External TABLE — vs the managed default (drop external → files stay; drop managed → files deleted)
CREATE TABLE IF NOT EXISTS silverline.bronze.ext_demo (id INT, note STRING)
  USING DELTA LOCATION 's3://<your-bucket>/ext_demo';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🔗 **This same external location backs the optional CDF step** (`07.5_lakebase_cdf`). CDF's `lb_*_history`
-- MAGIC tables are **managed**, but Free Edition won't let them use its *default* storage — so the catalog
-- MAGIC `silverline_cdf` is created with its **managed-storage root on this external location**:
-- MAGIC `CREATE CATALOG silverline_cdf MANAGED LOCATION 's3://<your-bucket>/lakebase_cdf'`. (`MANAGED LOCATION` =
-- MAGIC where a catalog's *managed* objects store data — here, your own S3: managed objects on external storage,
-- MAGIC **not** an external table.) Set the external location up once here → CDF reuses it.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ **Done.** Catalog `silverline`, the medallion schemas, and the managed volume all exist.
-- MAGIC Open **Catalog Explorer** and confirm you can see them. Next stage: `provision` (Lakebase OLTP).
