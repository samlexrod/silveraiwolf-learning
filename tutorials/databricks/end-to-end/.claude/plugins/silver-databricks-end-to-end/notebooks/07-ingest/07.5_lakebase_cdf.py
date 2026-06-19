# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 7 · Pattern 5 — **Lakebase CDF** (native managed Postgres → Delta CDC)
# MAGIC
# MAGIC The native, **no-code** way to land Lakebase changes into Unity Catalog: the `wal2delta` extension
# MAGIC reads the WAL and writes an **`lb_<table>_history`** Delta table per source table (every
# MAGIC insert/update/**delete** — `_pg_change_type` + `_pg_lsn` + `_pg_xid` + `_timestamp`), flushed ~15s.
# MAGIC
# MAGIC **All it needs is a destination catalog + schema** — but that catalog must be backed by **external
# MAGIC storage** (CDF rejects Databricks-managed *default storage*). Run on **serverless**.
# MAGIC
# MAGIC > 💳 **Opt-in — costs real money (not just quota).** The external location comes from Databricks
# MAGIC > **Catalog → External Data → External Locations → Create → AWS quickstart**, which runs a
# MAGIC > **CloudFormation template in YOUR personal AWS account** to create an **S3 bucket + IAM role**,
# MAGIC > **billed by AWS to you** — outside Free Edition's $0/quota model. It's the **same external location**
# MAGIC > the `landing-zone` stage sets up in its opt-in Section 4 — reuse that if you already created it. Only do
# MAGIC > this if you want CDF and accept the AWS cost. The no-cost delete-aware alternative is `07.4_wal_cdc`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Find YOUR external location
# MAGIC The AWS quickstart created an external location on your workspace — **the same one you (optionally) set up
# MAGIC in the `landing-zone` stage (Section 4)**. If you did it there, reuse it; if not, create it now via Catalog →
# MAGIC External Data → External Locations → Create → AWS quickstart. List them and copy the `url` base — you'll set
# MAGIC it as a variable below. Your bucket is **not** `silveraiwolf` (that's the tutorial author's).

# COMMAND ----------

display(spark.sql("SHOW EXTERNAL LOCATIONS"))

# COMMAND ----------

# MAGIC %md ## 2 — Create the destination catalog (managed storage on your external location)
# MAGIC CDF's `lb_*_history` tables are **managed**, but can't use Free Edition's *default* storage — so this
# MAGIC catalog's **managed-storage root** is set to a path on your external location via `MANAGED LOCATION`
# MAGIC (managed objects, stored on your own S3 — not external tables). Set `CDF_LOCATION` to YOUR path, then run.

# COMMAND ----------

CDF_LOCATION = "s3://<your-external-location-bucket>/lakebase_cdf"   # ← EDIT to your external location

assert not CDF_LOCATION.startswith("s3://<"), "Set CDF_LOCATION to YOUR external-location path first."
spark.sql(f"""
    CREATE CATALOG IF NOT EXISTS silverline_cdf
    MANAGED LOCATION '{CDF_LOCATION}'
    COMMENT 'External-storage catalog for Lakebase CDF — lb_<table>_history tables'
""")
spark.sql("CREATE SCHEMA IF NOT EXISTS silverline_cdf.public")
print("destination ready:", CDF_LOCATION, "→ silverline_cdf.public")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Start CDF (UI — no public API)
# MAGIC Lakebase Postgres → project `silverline-oltp` → **Branch overview → Change Data Feed → Start**:
# MAGIC - **Database** `databricks_postgres` · **Schema** `public`
# MAGIC - **To catalog** `silverline_cdf` · **Schema** `public`
# MAGIC
# MAGIC Click **Start** (briefly restarts the compute). Each `public` table appears as
# MAGIC `silverline_cdf.public.lb_<table>_history` (snapshotting → streaming over a few minutes).
# MAGIC
# MAGIC > **UI-only — no API/CLI:** the Beta Lakebase Postgres API has projects/branches/endpoints/roles/
# MAGIC > catalogs/synced-tables/credentials but **no CDF endpoint** (verified). Only the prereq + output are programmatic.
# MAGIC > **Prereqs (done):** `REPLICA IDENTITY FULL` on the source tables; instance is **PG17**; destination is external-storage.
# MAGIC >
# MAGIC > 🧪 **Public Preview — can be flaky.** The `wal2delta` worker may **stall mid-snapshot** (the slot goes
# MAGIC > `active=f`, only some `lb_*_history` tables appear, no `committed_lsn`). It's not your config (verified:
# MAGIC > external storage writable, replica identity full, PG17). Fix = **Disable then Start** CDF again. The
# MAGIC > stalled slot also **retains WAL** — Disable to drop it if you stop. For reliable delete-aware CDC, use
# MAGIC > `07.4_wal_cdc`.

# COMMAND ----------

# MAGIC %md ## 4 — After Start: the change-feed tables in UC

# COMMAND ----------

display(spark.sql("SHOW TABLES IN silverline_cdf.public"))

# COMMAND ----------

# Change types once a table has snapshotted (insert / update_preimage / update_postimage / delete).
try:
    display(spark.sql("""
        SELECT _pg_change_type, count(*) AS n
        FROM silverline_cdf.public.lb_customers_history
        GROUP BY _pg_change_type ORDER BY 1
    """))
except Exception as e:
    print("lb_customers_history not ready yet (still snapshotting) —", str(e)[:160])

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚠️ Observed on Free Edition — CDF (Public Preview) stalls
# MAGIC We ran this end to end and CDF **did not complete** on Free Edition, despite every documented
# MAGIC requirement being satisfied. Verified live:
# MAGIC - **PG17** ✅ (instance recreated via `postgres create-project … pg_version 17`)
# MAGIC - **External-storage destination** ✅ (`silverline_cdf`; we wrote + read a Delta table there fine)
# MAGIC - **`REPLICA IDENTITY FULL`** on all 9 tables ✅ · no partitioned/empty tables ✅ · compute **ACTIVE** ✅
# MAGIC
# MAGIC Yet the `wal2delta` worker **stuck mid-snapshot**: only `lb_vendors_history` registered (no committed
# MAGIC Delta data), the other 8 tables never started, the CDF replication slot stayed **`active=f`**, and its
# MAGIC **retained WAL kept growing** (~0.4 MB → ~1 MB). `wal2delta.info()` is permission-denied, so the
# MAGIC internal error isn't readable from SQL.
# MAGIC
# MAGIC **Conclusion:** this is the **Public Preview** status of Lakebase CDF, not a misconfiguration. Treat CDF
# MAGIC as *demonstrated* here (correct setup shown), and use **`07.4_wal_cdc`** for reliable, delete-aware CDC
# MAGIC on Free Edition. ⚠️ If you started CDF, **Disable** it (CDF tab) so the stuck slot stops retaining WAL.
