# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 7 — Ingest · Pattern 4: **WAL logical-decoding CDC** (delete-aware)
# MAGIC
# MAGIC The `updated_at` watermark in `07.3` can't see **deletes** (a vanished row has no timestamp). This
# MAGIC notebook closes that gap using Postgres's **Write-Ahead Log** via **logical decoding** — the same
# MAGIC source real CDC tools use — and it captures **inserts, updates, AND deletes**, fully on Free Edition.
# MAGIC
# MAGIC **What we verified on this instance:** `wal_level=logical` ✅, replication slots available ✅, our role
# MAGIC has `rolreplication` ✅. `CREATE PUBLICATION` is **blocked** by Databricks (so the standard
# MAGIC `pgoutput`/Debezium path is out — that's reserved for managed *Lakehouse Sync*), **but** a
# MAGIC `test_decoding` slot consumed in **batch** via `pg_logical_slot_get_changes(...)` works.
# MAGIC
# MAGIC > ⚠️ **SLOT RETENTION RISK.** A logical slot pins WAL until consumed. If you create it and walk away,
# MAGIC > WAL grows unbounded → storage/quota pressure. This notebook **consumes** (advances) every run and has
# MAGIC > a **monitor** cell + a **teardown** cell. **Drop the slot if you pause the tutorial.**
# MAGIC >
# MAGIC > ℹ️ `test_decoding` emits **plain text** (not JSON). Parsing is intentionally light — we store the
# MAGIC > decoded change + its operation/table. `wal2json`/`pgoutput` would be cleaner but aren't available here.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Connect + ensure the slot exists (idempotent)

# COMMAND ----------

import uuid, psycopg
from databricks.sdk import WorkspaceClient

INSTANCE, SLOT = "silverline-oltp", "silverline_cdc"
ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()
# Lakebase Autoscaling project (PG17) → use the `w.postgres` API (not `w.database`).
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token


def pg():
    return psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres",
                           user=USER, password=TOKEN, sslmode="require", autocommit=True)


with pg() as c, c.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_replication_slots WHERE slot_name=%s", (SLOT,))
    if not cur.fetchone():
        cur.execute("SELECT pg_create_logical_replication_slot(%s, 'test_decoding')", (SLOT,))
        print(f"created slot {SLOT}")
    else:
        print(f"slot {SLOT} already exists")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Monitor: how much WAL is this slot retaining?
# MAGIC Watch this go **up** as changes accumulate and **down** after you consume (cell 4).

# COMMAND ----------

with pg() as c, c.cursor() as cur:
    cur.execute("""
        SELECT slot_name, active,
               pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS retained_wal
        FROM pg_replication_slots WHERE slot_name=%s""", (SLOT,))
    print(cur.fetchone())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — (Demo) make an INSERT + UPDATE + DELETE the slot will capture
# MAGIC Uses a throwaway customer id `99999` so it doesn't touch seeded business rows. In real life these
# MAGIC changes come from the app / the `refresh` stage — they flow through identically.

# COMMAND ----------

with pg() as c, c.cursor() as cur:
    cur.execute("""
        INSERT INTO customers (customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date)
        VALUES (99999, 'WAL Demo Co', 'Retail', 'West', 'BBB', 1000000, DATE '2026-06-01')
        ON CONFLICT (customer_id) DO UPDATE SET legal_name = EXCLUDED.legal_name;""")
    cur.execute("UPDATE customers SET annual_revenue = 2000000 WHERE customer_id = 99999;")
    cur.execute("DELETE FROM customers WHERE customer_id = 99999;")
print("applied insert + update + delete on customer 99999")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Consume the changes (advances the slot → releases WAL)
# MAGIC `get_changes` is destructive (it advances `confirmed_flush_lsn`). We parse the `test_decoding` text
# MAGIC into (table, operation, change) and **append to `silverline.bronze.cdc_changes`** — deletes included.

# COMMAND ----------

import re
from datetime import datetime, timezone
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

rows = []
with pg() as c, c.cursor() as cur:
    # NOTE: Postgres `xid` can't cast to bigint — cast to text.
    cur.execute("SELECT lsn::text, xid::text, data FROM pg_logical_slot_get_changes(%s, NULL, NULL)", (SLOT,))
    fetched = cur.fetchall()

now = datetime.now(timezone.utc)
for lsn, xid, data in fetched:
    m = re.match(r"^table ([^:]+): (INSERT|UPDATE|DELETE): (.*)$", data)
    if not m:
        continue  # skip BEGIN/COMMIT
    rows.append((lsn, xid, m.group(1).strip(), m.group(2), m.group(3), now))

schema = StructType([
    StructField("lsn", StringType()), StructField("xid", StringType()),
    StructField("table_name", StringType()), StructField("operation", StringType()),
    StructField("change_data", StringType()), StructField("_ingested_at", TimestampType()),
])
if rows:
    (spark.createDataFrame(rows, schema)
        .write.mode("append").saveAsTable("silverline.bronze.cdc_changes"))
print(f"captured {len(rows)} change rows (incl. deletes):")
for r in rows:
    print(f"  {r[3]:6} {r[2]}: {r[4][:80]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — The change log (note the DELETE row) + WAL released
# MAGIC `operation='DELETE'` is exactly what the watermark pattern could never capture.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT operation, table_name, change_data, _ingested_at
# MAGIC FROM silverline.bronze.cdc_changes
# MAGIC ORDER BY _ingested_at DESC, lsn DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# re-check retained WAL — should have dropped after the get_changes consume
with pg() as c, c.cursor() as cur:
    cur.execute("""
        SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS retained_wal
        FROM pg_replication_slots WHERE slot_name=%s""", (SLOT,))
    print("retained WAL after consume:", cur.fetchone()[0])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 — ⚠️ Teardown — run this when you pause/finish (drops the slot, frees WAL)
# MAGIC Leaving the slot is the only real risk. Uncomment + run to drop it; recreate anytime via cell 1.

# COMMAND ----------

# with pg() as c, c.cursor() as cur:
#     cur.execute("SELECT pg_drop_replication_slot(%s)", (SLOT,))
#     print(f"dropped slot {SLOT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## The four ingest patterns, complete
# MAGIC | Pattern | Notebook | Inserts | Updates | **Deletes** | Managed | Notes |
# MAGIC |---|---|---|---|---|---|---|
# MAGIC | Full snapshot (CTAS) | `07.1` | ✅ | ✅ | ✅ (full rewrite) | n/a | simplest baseline |
# MAGIC | Lakehouse Sync | `07.2` | ✅ | ✅ | ✅ | ✅ | managed; **preview**, no CLI |
# MAGIC | Watermark CDC | `07.3` | ✅ | ✅ | ❌ | ❌ | portable; needs `updated_at` |
# MAGIC | **WAL logical-decoding CDC** | `07.4` (this) | ✅ | ✅ | **✅** | ❌ | needs slot mgmt; delete-aware |
# MAGIC
# MAGIC **Takeaway:** to capture deletes without the managed feature, go to the **WAL** — Postgres's source of
# MAGIC truth for every change. `silver` applies these (a `DELETE` row tombstones the key). ➡️ Next: stage 08.
