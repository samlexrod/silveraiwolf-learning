# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 5 — Silverline Capital data model (+ live exploration)
# MAGIC
# MAGIC **Silverline Capital** is a fictional **equipment lease & loan finance company**: it underwrites
# MAGIC applications from business customers, books them into lease/loan **contracts** backed by financed
# MAGIC **equipment**, then bills and collects on a monthly schedule.
# MAGIC
# MAGIC This is your **data dictionary** for the 9-table OLTP that `05.1_seed_oltp` loaded into the Lakebase
# MAGIC Postgres instance `silverline-oltp` (deterministic — `MOCK_SEED=42`). The bottom cells **explore the
# MAGIC seeded data live** by connecting to Postgres with `psycopg`.
# MAGIC
# MAGIC > 🔁 **Run `05.1_seed_oltp` first.** This notebook reads the rows it created.
# MAGIC > 🔭 **Later (stage 07 `ingest`)** the same data becomes queryable as the Unity Catalog catalog
# MAGIC > `lakebase_silverline_oltp` — you'll explore it with plain SQL there. Here we use psycopg because a
# MAGIC > notebook can't reach Lakebase Postgres via SQL until that registration happens.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entity relationships
# MAGIC Read each row as a **foreign key**: the **child** (the *many* side) points to its **parent** (the *one* side).
# MAGIC
# MAGIC | Child (many) | FK column | Parent (one) | Read it as |
# MAGIC |---|---|---|---|
# MAGIC | `applications` | `customer_id` | `customers` | a customer submits **many** applications |
# MAGIC | `applications` | `vendor_id` | `vendors` | each application names the equipment vendor |
# MAGIC | `contracts` | `application_id` | `applications` | an approved application is booked into **one** contract |
# MAGIC | `contracts` | `customer_id` | `customers` | (denormalized — the contract's customer) |
# MAGIC | `equipment` | `vendor_id` | `vendors` | each asset is supplied by **one** vendor |
# MAGIC | `contract_assets` | `contract_id` | `contracts` | a contract is backed by **many** assets… |
# MAGIC | `contract_assets` | `equipment_id` | `equipment` | …each linking one equipment → `contract_assets` is the **M:N bridge** |
# MAGIC | `payment_schedule` | `contract_id` | `contracts` | a contract amortizes into **many** scheduled periods |
# MAGIC | `invoices` | `contract_id`, `schedule_id` | `contracts`, `payment_schedule` | each elapsed period is **billed** as an invoice |
# MAGIC | `payments` | `invoice_id` | `invoices` | cash received is applied against an invoice |
# MAGIC
# MAGIC The same relationships as an **entity-relationship diagram** — in crow's-foot notation, the forked
# MAGIC ("many") end touches the child table and the single bar ("one") end touches the parent:
# MAGIC
# MAGIC ![Silverline Capital — ER diagram](https://mermaid.ink/svg/ZXJEaWFncmFtCiAgY3VzdG9tZXJzIHx8LS1veyBhcHBsaWNhdGlvbnMgOiBzdWJtaXRzCiAgdmVuZG9ycyB8fC0tb3sgYXBwbGljYXRpb25zIDogIm5hbWVkIGluIgogIGFwcGxpY2F0aW9ucyB8fC0tb3wgY29udHJhY3RzIDogImJvb2tlZCBpbnRvIgogIGN1c3RvbWVycyB8fC0tb3sgY29udHJhY3RzIDogaG9sZHMKICB2ZW5kb3JzIHx8LS1veyBlcXVpcG1lbnQgOiBzdXBwbGllcwogIGNvbnRyYWN0cyB8fC0tb3sgY29udHJhY3RfYXNzZXRzIDogImJhY2tlZCBieSIKICBlcXVpcG1lbnQgfHwtLW97IGNvbnRyYWN0X2Fzc2V0cyA6ICJhbGxvY2F0ZWQgaW4iCiAgY29udHJhY3RzIHx8LS1veyBwYXltZW50X3NjaGVkdWxlIDogImFtb3J0aXplZCBhcyIKICBjb250cmFjdHMgfHwtLW97IGludm9pY2VzIDogImJpbGxlZCB2aWEiCiAgcGF5bWVudF9zY2hlZHVsZSB8fC0tb3wgaW52b2ljZXMgOiAiZm9yIHBlcmlvZCIKICBpbnZvaWNlcyB8fC0tb3sgcGF5bWVudHMgOiAic2V0dGxlZCBieSIK)
# MAGIC
# MAGIC **Lifecycle:** **origination** (`applications`) → **booking** (`contracts` + `contract_assets`) →
# MAGIC **billing** (`payment_schedule` → `invoices`) → **collections** (`payments`).

# COMMAND ----------

# MAGIC %md
# MAGIC ## The 9 tables
# MAGIC | Table | Grain / role | Key columns |
# MAGIC |-------|--------------|-------------|
# MAGIC | `customers` | businesses we finance | customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date |
# MAGIC | `vendors` | equipment suppliers | vendor_id, name, vendor_type, region |
# MAGIC | `equipment` | financed assets, per vendor | equipment_id, vendor_id, category, make, model, serial_number, cost, residual_value, in_service_date |
# MAGIC | `applications` | the credit pipeline | application_id, customer_id, vendor_id, amount_requested, **status** (submitted/approved/declined/booked), submitted_date, decision_date |
# MAGIC | `contracts` | booked lease/loan deals | contract_id, application_id, customer_id, **contract_type** (lease/loan), **status** (active/paid_off/delinquent/charged_off), principal, apr, term_months, start_date, end_date, residual_value |
# MAGIC | `contract_assets` | equipment backing a contract (M:N) | contract_id, equipment_id, allocated_cost |
# MAGIC | `payment_schedule` | amortization plan | schedule_id, contract_id, period_no, due_date, principal_due, interest_due, total_due |
# MAGIC | `invoices` | bills for elapsed periods | invoice_id, contract_id, schedule_id, invoice_date, due_date, amount, **status** (open/paid/overdue) |
# MAGIC | `payments` | cash received vs invoices | payment_id, invoice_id, paid_date, amount, method |
# MAGIC
# MAGIC **Why it matters:** a realistic normalized OLTP — many-to-many (`contract_assets`), a status pipeline
# MAGIC (`applications`), and derived facts (`payment_schedule`/`invoices`/`payments` computed from each
# MAGIC contract's amortization). That richness makes the later medallion + analytics meaningful.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Live exploration — connect to the seeded Postgres
# MAGIC The official Lakebase-from-notebook pattern: upgrade the SDK (the `w.postgres` service for Autoscaling
# MAGIC projects needs a **current `databricks-sdk`**), install `psycopg`, mint a credential via the SDK (you,
# MAGIC no token to paste), connect over SSL.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import pandas as pd
import psycopg
from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token


def q(sql: str) -> pd.DataFrame:
    with psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER,
                         password=TOKEN, sslmode="require") as conn, conn.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])


print(f"connected to {HOST} as {USER}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Row counts per table
# MAGIC Expect customers=60, vendors=15, equipment=220, applications=140, contracts=85,
# MAGIC contract_assets=180, payment_schedule=2904, invoices=1452, payments=1291.

# COMMAND ----------

display(q("""
    SELECT 'customers' AS table_name, count(*) AS rows FROM customers
    UNION ALL SELECT 'vendors',          count(*) FROM vendors
    UNION ALL SELECT 'equipment',        count(*) FROM equipment
    UNION ALL SELECT 'applications',     count(*) FROM applications
    UNION ALL SELECT 'contracts',        count(*) FROM contracts
    UNION ALL SELECT 'contract_assets',  count(*) FROM contract_assets
    UNION ALL SELECT 'payment_schedule', count(*) FROM payment_schedule
    UNION ALL SELECT 'invoices',         count(*) FROM invoices
    UNION ALL SELECT 'payments',         count(*) FROM payments
    ORDER BY table_name
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Portfolio principal financed by customer segment
# MAGIC A customer → contract join — proves the relationships line up and the money makes sense.

# COMMAND ----------

display(q("""
    SELECT c.segment,
           count(*)                  AS contracts,
           round(sum(co.principal))  AS principal_financed
    FROM customers c
    JOIN contracts co USING (customer_id)
    GROUP BY c.segment
    ORDER BY principal_financed DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Contract status mix
# MAGIC active / delinquent / charged_off / paid_off across the booked portfolio.

# COMMAND ----------

display(q("""
    SELECT status, contract_type, count(*) AS contracts, round(sum(principal)) AS principal
    FROM contracts
    GROUP BY status, contract_type
    ORDER BY status, contract_type
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ You've seen the seeded OLTP live. Next stage `06-data-api`, then `07-ingest` brings this same data
# MAGIC into Unity Catalog as `lakebase_silverline_oltp` for SQL + the medallion build.

# COMMAND ----------

# MAGIC %md
# MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
