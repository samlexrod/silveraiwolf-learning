-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 7 — Ingest · Pattern 3 of 3: **Custom watermark CDC** (frugal)
-- MAGIC
-- MAGIC The portable "frugal CDC" pattern: **snapshot-then-incremental**, driven by a **watermark**. It's the
-- MAGIC same shape we use for SQL Server (where the watermark is the CDC **LSN** over `cdc.*` change tables) —
-- MAGIC here, Postgres has no change tables, so the watermark is the **`updated_at` timestamp** over the base
-- MAGIC table. A `BEFORE UPDATE` trigger keeps `updated_at` moving on every update (added in the provisioning
-- MAGIC step on `customers` / `contracts` / `invoices`).
-- MAGIC
-- MAGIC **How one idempotent cell does both snapshot and incremental:** we append source rows where
-- MAGIC `updated_at > (max _source_updated_at already landed)`. On the **first** run the CDC table is empty →
-- MAGIC the watermark is epoch → it appends **all current rows (the snapshot)**. On **later** runs (after the
-- MAGIC `refresh` stage mutates the source) → only the **changed rows** land. Append-only = a change log with
-- MAGIC full history; `silver` dedups it to current state.
-- MAGIC
-- MAGIC > ⚠️ **Honest limit:** a timestamp watermark catches **inserts + updates, not deletes** (a vanished row
-- MAGIC > has no `updated_at` to exceed the watermark). Delete-aware CDC needs Lakehouse Sync (`07.2`), Postgres
-- MAGIC > logical replication, or a soft-delete flag. Run on the **Starter Warehouse** (SQL).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — Define the append-only CDC bronze tables (once, idempotent)
-- MAGIC `CREATE TABLE IF NOT EXISTS … WHERE 1=0` defines each table from the source schema + 3 metadata
-- MAGIC columns (`_source_updated_at`, `_operation`, `_ingested_at`), without loading any rows yet.

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS silverline.bronze.customers_cdc AS
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.customers WHERE 1=0;

CREATE TABLE IF NOT EXISTS silverline.bronze.contracts_cdc AS
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.contracts WHERE 1=0;

CREATE TABLE IF NOT EXISTS silverline.bronze.invoices_cdc AS
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.invoices WHERE 1=0;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Snapshot-then-incremental append (the watermark cell)
-- MAGIC Re-runnable: first run lands the full snapshot; later runs land only rows changed since the last
-- MAGIC watermark. (Run this same cell again after the `refresh` stage to see incremental rows appear.)

-- COMMAND ----------

INSERT INTO silverline.bronze.customers_cdc
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.customers
WHERE updated_at > (SELECT coalesce(max(_source_updated_at), TIMESTAMP '1970-01-01')
                    FROM silverline.bronze.customers_cdc);

-- COMMAND ----------

INSERT INTO silverline.bronze.contracts_cdc
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.contracts
WHERE updated_at > (SELECT coalesce(max(_source_updated_at), TIMESTAMP '1970-01-01')
                    FROM silverline.bronze.contracts_cdc);

-- COMMAND ----------

INSERT INTO silverline.bronze.invoices_cdc
SELECT *, updated_at AS _source_updated_at, 'upsert' AS _operation, current_timestamp() AS _ingested_at
FROM lakebase_silverline_oltp.public.invoices
WHERE updated_at > (SELECT coalesce(max(_source_updated_at), TIMESTAMP '1970-01-01')
                    FROM silverline.bronze.invoices_cdc);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 — Verify
-- MAGIC On the **first** run the CDC log holds one row per current record (the snapshot): customers 60,
-- MAGIC contracts 85, invoices 1452. After the `refresh` stage + re-running cell 2, you'll see **extra** rows
-- MAGIC for the changed records (history), and `_ingested_at` will differ.

-- COMMAND ----------

SELECT 'customers_cdc' AS cdc_table, count(*) AS rows, count(distinct customer_id) AS keys,
       max(_source_updated_at) AS watermark FROM silverline.bronze.customers_cdc
UNION ALL
SELECT 'invoices_cdc', count(*), count(distinct invoice_id), max(_source_updated_at) FROM silverline.bronze.invoices_cdc
UNION ALL
SELECT 'contracts_cdc', count(*), count(distinct contract_id), max(_source_updated_at) FROM silverline.bronze.contracts_cdc
ORDER BY cdc_table;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4 — From change log → current state (what `silver` does)
-- MAGIC The CDC bronze is **append-only** (a row may appear several times as it changes). Current state =
-- MAGIC the latest row per key — exactly the dedup the `silver` models do. Preview it here for customers:

-- COMMAND ----------

SELECT customer_id, legal_name, annual_revenue, _source_updated_at
FROM (
  SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY _source_updated_at DESC) AS rn
  FROM silverline.bronze.customers_cdc
)
WHERE rn = 1
ORDER BY customer_id
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## The three patterns, side by side
-- MAGIC | Pattern | Notebook | Captures | History | Managed? | Deletes |
-- MAGIC |---|---|---|---|---|---|
-- MAGIC | Full snapshot (CTAS) | `07.1` | current state | Delta time-travel only | n/a (you run it) | reflected (full rewrite) |
-- MAGIC | Lakehouse Sync | `07.2` | every change | full, as rows | ✅ fully managed | ✅ yes |
-- MAGIC | Watermark CDC | `07.3` (this) | inserts + updates | full, as appended rows | ❌ DIY | ❌ no |
-- MAGIC
-- MAGIC **When to use which:** CTAS for small/simple full refreshes; watermark CDC when the source has a
-- MAGIC reliable change marker (`updated_at`/LSN) but no managed CDC; Lakehouse Sync when you want hands-off,
-- MAGIC delete-aware CDC and it's available. ➡️ Next: **stage 08 (`medallion`)** builds silver/gold on bronze.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
