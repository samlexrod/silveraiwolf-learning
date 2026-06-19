# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 9 — Refresh: a source change propagates to gold
# MAGIC
# MAGIC Edit the **Lakebase** source, re-ingest the changed tables to bronze, re-run the medallion, and **prove
# MAGIC the change reached silver + gold** — bronze→silver→gold lineage on a real source edit. Run on **serverless**.
# MAGIC
# MAGIC > 🧠 **Batch re-read, not log-based CDC** — `CREATE OR REPLACE` the changed bronze tables, then rebuild.
# MAGIC > (Bonus: the same edits also surface in Stage 7's `*_cdc` / `cdc_changes` logs, and in Lakebase CDF
# MAGIC > `lb_*_history` if you enabled it.)

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Apply a deterministic change-set to Lakebase
# MAGIC UPDATE customer 1 / invoice 1 / contract 1 · INSERT customer 9001 + invoice 900001 · DELETE invoice 3.
# MAGIC Idempotent (re-running converges to the same state).

# COMMAND ----------

import psycopg
from databricks.sdk import WorkspaceClient

EP = "projects/silverline-oltp/branches/production/endpoints/primary"
w = WorkspaceClient()
HOST = w.postgres.get_endpoint(EP).status.hosts.host
USER = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(EP).token

DML = """
UPDATE customers SET annual_revenue = 123456789.00 WHERE customer_id = 1;
UPDATE invoices  SET amount = 987654.00, status = 'overdue' WHERE invoice_id = 1;
UPDATE contracts SET status = 'delinquent' WHERE contract_id = 1;
INSERT INTO customers (customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date)
  VALUES (9001, 'Simulated Logistics Co', 'Logistics', 'West', 'BBB', 4242.00, DATE '2026-06-01')
  ON CONFLICT (customer_id) DO NOTHING;
INSERT INTO invoices (invoice_id, contract_id, schedule_id, invoice_date, due_date, amount, status)
  VALUES (900001, 1, NULL, DATE '2026-06-01', DATE '2026-07-01', 4242.00, 'open')
  ON CONFLICT (invoice_id) DO NOTHING;
DELETE FROM payments WHERE invoice_id = 3;
DELETE FROM invoices WHERE invoice_id = 3;
"""
with psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER,
                     password=TOKEN, sslmode="require", autocommit=True) as conn, conn.cursor() as cur:
    cur.execute(DML)
print("✓ change-set applied to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Re-ingest the changed tables to bronze
# MAGIC Only `customers` / `contracts` / `invoices` changed — re-`CREATE OR REPLACE` just those from the
# MAGIC registered Lakebase catalog (the "refresh" is the re-read).

# COMMAND ----------

for t in ["customers", "contracts", "invoices"]:
    spark.sql(f"CREATE OR REPLACE TABLE silverline.bronze.{t} AS "
              f"SELECT * FROM lakebase_silverline_oltp.public.{t}")
print("✓ bronze re-ingested: customers, contracts, invoices")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Re-run the medallion (dbt Job)
# MAGIC Triggers `silverline-dbt-job` to rebuild canonical `silver_*` / `gold_*` from the new bronze.

# COMMAND ----------

jobs = list(w.jobs.list(name="silverline-dbt-job"))
assert jobs, "silverline-dbt-job not found — run 08.2_build_dbt's provisioning first."
run = w.jobs.run_now(job_id=jobs[0].job_id).result()
print("dbt job:", run.state.result_state)

# COMMAND ----------

# MAGIC %md ## 4 — Assert the change reached **silver** (7 checks)

# COMMAND ----------

display(spark.sql("""
SELECT
  (SELECT count(*) FROM silverline.silver.silver_invoices  WHERE invoice_id = 900001) AS insert_present,    -- 1
  (SELECT count(*) FROM silverline.silver.silver_invoices  WHERE invoice_id = 3)      AS delete_dropped,    -- 0
  (SELECT amount   FROM silverline.silver.silver_invoices  WHERE invoice_id = 1)      AS update_amount,     -- 987654.00
  (SELECT status   FROM silverline.silver.silver_invoices  WHERE invoice_id = 1)      AS update_status,     -- overdue
  (SELECT status   FROM silverline.silver.silver_contracts WHERE contract_id = 1)     AS contract1_status,  -- delinquent
  (SELECT annual_revenue FROM silverline.silver.silver_customers WHERE customer_id = 1) AS customer1_revenue, -- 123456789.00
  (SELECT count(*) FROM silverline.silver.silver_customers WHERE customer_id = 9001)  AS new_customer        -- 1
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — Assert it reached **gold** (lineage all the way through)
# MAGIC Invoice 1 → overdue + new open invoice 900001 both land on contract 1's `gold_contract_aging` row.

# COMMAND ----------

display(spark.sql("""
    SELECT contract_id, overdue_amount, open_amount, paid_amount, total_billed
    FROM silverline.gold.gold_contract_aging
    WHERE contract_id = 1
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bonus — the same edits in the change feeds (Stage 7)
# MAGIC If Lakebase CDF (`07.5`) is streaming, the UPDATE/INSERT/DELETE show up as change rows. (Skips cleanly
# MAGIC if CDF isn't enabled.)

# COMMAND ----------

try:
    display(spark.sql("""
        SELECT _pg_change_type, count(*) AS n
        FROM silverline_cdf.public.lb_invoices_history
        GROUP BY _pg_change_type ORDER BY 1
    """))
except Exception as e:
    print("CDF lb_invoices_history not available (CDF not enabled / still snapshotting):", str(e)[:140])

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ One source edit → re-ingest → rebuild → **visible in silver and gold**. That's batch-refresh +
# MAGIC lineage. **Phase C (Lakehouse) complete.** Next: Analytics (`10-business-layer`).
