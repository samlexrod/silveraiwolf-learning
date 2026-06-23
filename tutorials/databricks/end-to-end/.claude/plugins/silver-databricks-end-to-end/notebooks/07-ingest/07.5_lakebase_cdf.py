# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 7 · Pattern 5 — **Lakebase CDF** (native managed Postgres → Delta CDC)
# MAGIC
# MAGIC > ⛔ **Capability demo only — Free Edition can't actually stream CDC.** Lakebase CDF is **Public Preview**,
# MAGIC > and on **Free Edition the `wal2delta` worker stalls** mid-snapshot: tables show **Error**, the slot goes
# MAGIC > inactive, and it keeps **retaining WAL**. We verified this end-to-end with **every** prerequisite correct
# MAGIC > (PG17 · external-storage destination · `REPLICA IDENTITY FULL` on all 9 · clean slate). So this notebook
# MAGIC > exists to **show how CDF is set up and what it would produce** — not to run it for real here. **For working,
# MAGIC > delete-aware CDC on Free Edition, use `07.4_wal_cdc`.** See the "Observed on Free Edition" section at the end.
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
# MAGIC CDF's `lb_*_history` tables are **managed**, but CDF **requires the destination catalog's managed storage
# MAGIC on an external location** (a CDF requirement, any edition) — so this catalog's **managed-storage root** is
# MAGIC set to a path on your external location via `MANAGED LOCATION` (managed objects on your own S3 — the same
# MAGIC `silverline_ext`-style pattern from `landing-zone` Section 4, not external tables). Set `CDF_LOCATION`, then run.

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
# MAGIC ## 2b — Prereq: `REPLICA IDENTITY FULL` on every source table (required)
# MAGIC CDF's `wal2delta` worker needs **full row images** to decode updates/deletes — without it, every table
# MAGIC shows **Error** on the CDF page. Postgres tables default to `REPLICA IDENTITY DEFAULT` (the PK only), and
# MAGIC re-creating/re-seeding (`05.1`) resets it — so set it **here**, idempotently, right before Start. We connect
# MAGIC to Postgres as the owner (same `w.postgres` credential pattern as `05.1`) and `ALTER` all 9 tables.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import psycopg
from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"
w = WorkspaceClient()
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token

TABLES = ["customers", "vendors", "equipment", "applications", "contracts",
          "contract_assets", "payment_schedule", "invoices", "payments"]

with psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER,
                     password=TOKEN, sslmode="require") as conn, conn.cursor() as cur:
    for t in TABLES:
        cur.execute(f"ALTER TABLE {t} REPLICA IDENTITY FULL")   # idempotent
    conn.commit()
    cur.execute("""
        SELECT relname, relreplident FROM pg_class
        WHERE relname = ANY(%s) ORDER BY relname""", (TABLES,))
    rows = cur.fetchall()

print("REPLICA IDENTITY (expect 'f' = FULL for all):")
for name, ident in rows:
    print(f"  {name:18} {ident}{'  ✅' if ident == 'f' else '  ❌ not FULL'}")
assert all(ident == "f" for _, ident in rows), "Some tables are not REPLICA IDENTITY FULL"

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
# MAGIC > **Prereqs:** `REPLICA IDENTITY FULL` on the source tables (**set in §2b above** — verify it printed `f`
# MAGIC > for all 9); instance is **PG17**; destination is external-storage. If CDF shows **Error** per table, the
# MAGIC > usual cause is replica identity not FULL — re-run §2b, then **Disable → Start** CDF.
# MAGIC >
# MAGIC > 🧪 **Public Preview — stalls on Free Edition.** The `wal2delta` worker **stalls mid-snapshot** (the slot
# MAGIC > goes `active=f`, tables show **Error**, no `committed_lsn`). It's not your config (verified: external
# MAGIC > storage writable, replica identity full, PG17, clean slate). Retrying **Disable → remove config → Start**
# MAGIC > does **not** fix it — it stalls again. For reliable delete-aware CDC on Free Edition, use `07.4_wal_cdc`.
# MAGIC >
# MAGIC > ⚠️ **Cleanup is manual (two gotchas, verified live):**
# MAGIC > 1. **Disable does NOT drop the replication slot** — the stalled `wal2delta_*` slot lingers `active=f` and
# MAGIC >    keeps **retaining/growing WAL**. Drop it yourself: `SELECT pg_drop_replication_slot('<slot>');` (find it
# MAGIC >    via `SELECT slot_name FROM pg_replication_slots WHERE slot_name LIKE 'wal2delta%'`).
# MAGIC > 2. **Disable does NOT remove the schema configuration** — to re-Start you must **remove the existing CDF
# MAGIC >    configuration** (CDF page → **Schemas** tab → remove), *not* drop the destination UC schema.

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
# MAGIC Yet the `wal2delta` worker **stuck mid-snapshot**: tables show **Error** (no committed Delta data), the CDF
# MAGIC replication slot stayed **`active=f`**, and its **retained WAL kept growing**. Reproduced more than once —
# MAGIC remove the config, drop the slot, re-Start with everything correct, and it **stalls again**.
# MAGIC `wal2delta.info()` is permission-denied, so the internal error isn't readable from SQL.
# MAGIC
# MAGIC **Conclusion:** this is the **Public Preview** status of Lakebase CDF on Free Edition, not a
# MAGIC misconfiguration — **Free Edition cannot actually stream CDC**. Treat this notebook as a **capability
# MAGIC demo** (correct setup + expected output shown) and use **`07.4_wal_cdc`** for reliable, delete-aware CDC.
# MAGIC
# MAGIC ⚠️ **To fully stop it** (two manual steps — Disable alone is not enough):
# MAGIC 1. **CDF page → Schemas tab → remove the configuration** (Disable only pauses; the config blocks re-Start).
# MAGIC 2. **Drop the lingering slot** in Postgres — Disable doesn't:
# MAGIC    `SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name LIKE 'wal2delta%';`

# COMMAND ----------

# MAGIC %md
# MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
