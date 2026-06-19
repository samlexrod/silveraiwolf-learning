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
-- MAGIC ## 4 — Managed vs external, hands-on (opt-in)
-- MAGIC Sections 1–2 built the **managed** side (the default). Now build the **external** side so you've created
-- MAGIC **both** — a catalog whose storage is your own cloud, an external volume, and an external table. **Opt-in**
-- MAGIC because external = **your own S3** (billed by your cloud, not Free Edition quota); skip it and the tutorial
-- MAGIC still runs fully on managed.
-- MAGIC
-- MAGIC 💳 The **AWS quickstart** runs a **CloudFormation** stack in your AWS → S3 bucket + IAM role, billed by AWS.
-- MAGIC `cleanup` drops the Databricks objects but **not** your AWS resources (delete that stack yourself).
-- MAGIC
-- MAGIC **Register the external location (UI):** Catalog → External Data → External Locations → **Create → AWS
-- MAGIC quickstart** → approve the CloudFormation stack; it registers the location + storage credential in UC.
-- MAGIC Then replace `<your-bucket>` below and run the cells. *(Manual SQL alt: `CREATE STORAGE CREDENTIAL …` +
-- MAGIC `CREATE EXTERNAL LOCATION … URL 's3://<your-bucket>/…' WITH (STORAGE CREDENTIAL …)`.)*

-- COMMAND ----------

-- Opt-in: list your registered external locations (find the url s3://<your-bucket>/…)
SHOW EXTERNAL LOCATIONS;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ⚠️ **Edit `<your-bucket>`** in the statements below to YOUR external-location bucket, then run them.
-- MAGIC They error until the external location above exists — expected if you skipped the quickstart.

-- COMMAND ----------

-- A managed catalog vs an external-storage-backed catalog: silverline (above) is managed (metastore default
-- storage); this catalog's MANAGED objects store data on YOUR S3. Both are managed (drop → data deleted) —
-- they differ only in WHERE the bytes live.
CREATE CATALOG IF NOT EXISTS silverline_ext
  MANAGED LOCATION 's3://<your-bucket>/silverline_ext'
  COMMENT 'Managed objects, stored on your own S3 — vs silverline (metastore default storage).';

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
-- MAGIC 🔗 **The `ingest` CDF step uses this exact pattern.** CDF writes its `lb_*_history` tables as **managed**
-- MAGIC objects, but **requires the destination catalog's managed storage on an external location** (a CDF
-- MAGIC requirement, any edition) — so `07.5` creates `silverline_cdf` with
-- MAGIC `MANAGED LOCATION 's3://<your-bucket>/lakebase_cdf'`, the same shape as `silverline_ext` above. Register
-- MAGIC the external location once here → CDF reuses it.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ **Done.** Catalog `silverline`, the medallion schemas, and the managed volume all exist.
-- MAGIC Open **Catalog Explorer** and confirm you can see them. Next stage: `provision` (Lakebase OLTP).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
