-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 7 — Ingest · materialize bronze (pattern 1 of 4): **CTAS snapshot**
-- MAGIC
-- MAGIC In **`07.1`** you queried Lakebase **in place** (zero-ETL, no copy). Now we **materialize** it: land all 9
-- MAGIC OLTP tables into `silverline.bronze` as **Delta**, via **CTAS (full snapshot)** — the simplest of the four
-- MAGIC materialization patterns and the baseline the CDC ones (`07.3`–`07.5`) refine. The source is the same
-- MAGIC native catalog `lakebase_silverline_oltp.public.<table>` (registered in `07.1`). Run on the **Starter
-- MAGIC Warehouse** (SQL).
-- MAGIC
-- MAGIC > 🧭 **Why copy at all, when `07.1` already queries it natively?** For a **governed Delta bronze** —
-- MAGIC > history + time-travel, decoupling analytics from the live OLTP, and a stable base the **medallion**
-- MAGIC > (stage 08) builds on. The four materialization patterns: **`07.2`** CTAS (this) · **`07.3`** watermark
-- MAGIC > CDC · **`07.4`** WAL CDC · **`07.5`** Lakebase CDF.
-- MAGIC >
-- MAGIC > 💚 **Cost:** quota only — a handful of `CREATE OR REPLACE TABLE AS SELECT` on serverless.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — Land all 9 tables into `silverline.bronze` (CTAS)
-- MAGIC
-- MAGIC **What is CTAS?** `CREATE TABLE AS SELECT` — one statement that **creates a new table _and_ fills it
-- MAGIC with a query's result**, inferring columns + types from the `SELECT`:
-- MAGIC ```sql
-- MAGIC CREATE OR REPLACE TABLE silverline.bronze.customers          -- new Delta table
-- MAGIC AS SELECT * FROM lakebase_silverline_oltp.public.customers;  -- its data + schema = this query
-- MAGIC ```
-- MAGIC - `CREATE TABLE …` → a new managed **Delta** table.
-- MAGIC - `AS SELECT * FROM …` → run that query against the live Lakebase catalog; its result becomes the
-- MAGIC   table's rows + schema (`SELECT *` = all columns/rows).
-- MAGIC - `OR REPLACE` → if it already exists, drop + rebuild — this is what makes re-running **idempotent**
-- MAGIC   (same result every time), which is exactly what the `refresh` stage re-runs after the source changes.
-- MAGIC
-- MAGIC It's a **one-time snapshot**, not a live link — bronze reflects the source *as of when you run it*
-- MAGIC (that's the point of a raw layer). Nine statements → nine bronze tables. bronze is the lakehouse's own
-- MAGIC governed Delta copy (history, time travel) and the stable base the medallion builds silver/gold from.

-- COMMAND ----------

CREATE OR REPLACE TABLE silverline.bronze.customers        AS SELECT * FROM lakebase_silverline_oltp.public.customers;
CREATE OR REPLACE TABLE silverline.bronze.vendors          AS SELECT * FROM lakebase_silverline_oltp.public.vendors;
CREATE OR REPLACE TABLE silverline.bronze.equipment        AS SELECT * FROM lakebase_silverline_oltp.public.equipment;
CREATE OR REPLACE TABLE silverline.bronze.applications     AS SELECT * FROM lakebase_silverline_oltp.public.applications;
CREATE OR REPLACE TABLE silverline.bronze.contracts        AS SELECT * FROM lakebase_silverline_oltp.public.contracts;
CREATE OR REPLACE TABLE silverline.bronze.contract_assets  AS SELECT * FROM lakebase_silverline_oltp.public.contract_assets;
CREATE OR REPLACE TABLE silverline.bronze.payment_schedule AS SELECT * FROM lakebase_silverline_oltp.public.payment_schedule;
CREATE OR REPLACE TABLE silverline.bronze.invoices         AS SELECT * FROM lakebase_silverline_oltp.public.invoices;
CREATE OR REPLACE TABLE silverline.bronze.payments         AS SELECT * FROM lakebase_silverline_oltp.public.payments;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Verify bronze
-- MAGIC Expect the medallion's three sources: customers 60 / contracts 85 / invoices 1452.

-- COMMAND ----------

SELECT 'customers' AS t, count(*) AS n FROM silverline.bronze.customers
UNION ALL SELECT 'contracts', count(*) FROM silverline.bronze.contracts
UNION ALL SELECT 'invoices',  count(*) FROM silverline.bronze.invoices
UNION ALL SELECT 'vendors',          count(*) FROM silverline.bronze.vendors
UNION ALL SELECT 'equipment',        count(*) FROM silverline.bronze.equipment
UNION ALL SELECT 'applications',     count(*) FROM silverline.bronze.applications
UNION ALL SELECT 'contract_assets',  count(*) FROM silverline.bronze.contract_assets
UNION ALL SELECT 'payment_schedule', count(*) FROM silverline.bronze.payment_schedule
UNION ALL SELECT 'payments',         count(*) FROM silverline.bronze.payments
ORDER BY t;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC # 📐 Design notes (with Databricks evidence)
-- MAGIC Three questions worth answering before you accept this stage. All grounded in Databricks docs, not opinion.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q1 — Why a bronze layer at all, when the OLTP is already clean?
-- MAGIC Bronze is **not** justified by "taming messy data" — it's the **ingestion boundary**, and its value holds
-- MAGIC even for a pristine source:
-- MAGIC - **Schema-change / corruption shock absorber.** Databricks: *"Azure Databricks does not recommend
-- MAGIC   writing to silver tables directly from ingestion. If you write directly from ingestion, you'll
-- MAGIC   introduce failures due to schema changes or corrupt records in data sources."* A clean OLTP still
-- MAGIC   evolves (columns added/renamed/retyped) — bronze absorbs that at the edge.
-- MAGIC - **Single source of truth + replay/audit.** Bronze *"serves as the single source of truth, preserving
-- MAGIC   the data's fidelity"* and *"enables reprocessing and auditing by retaining all historical data."*
-- MAGIC - **OLTP/OLAP separation** (our specific reason): analytics read this Delta copy, never the live Postgres.
-- MAGIC
-- MAGIC And the honest caveat — the layers are a guideline, not a law: *"Following the medallion architecture is a
-- MAGIC recommended best practice but not a requirement."* A single clean source *could* collapse bronze→silver;
-- MAGIC we keep bronze to teach the pattern and for the decoupling/replay benefits above.
-- MAGIC
-- MAGIC 📄 [Medallion architecture — Bronze](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
-- MAGIC · [Why data layers matter (Databricks Community)](https://community.databricks.com/t5/community-articles/the-medallion-architecture-why-data-layers-matter-for-modern/td-p/140825)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q2 — "Isn't bronze supposed to be append-only?" Why CTAS (overwrite)?
-- MAGIC Append-only is **one of two** valid bronze load patterns — the choice is dictated by the **source**, not a rule:
-- MAGIC
-- MAGIC | Pattern | When | Mechanism |
-- MAGIC |---|---|---|
-- MAGIC | **Snapshot / full-refresh (overwrite)** | source hands you the **complete current dataset** each load and can't say what changed (OLTP reads, Salesforce/Qualtrics exports) | `CREATE OR REPLACE … AS SELECT` (our CTAS) |
-- MAGIC | **CDC / append** | source emits **change events** and you want every change | append / `MERGE INTO` |
-- MAGIC
-- MAGIC We read the Lakebase OLTP as **current state** via the native catalog — no change feed — so a **full
-- MAGIC snapshot is the correct bronze pattern here**, not a violation. Row-level history across loads isn't kept
-- MAGIC by overwrite, but Delta **time travel** retains prior table *versions* (`VERSION AS OF`). True row-level
-- MAGIC change history needs CDC/append — that's the `refresh` stage (09) + the streaming/CDC sibling tutorial.
-- MAGIC
-- MAGIC The **managed production mechanism** for Postgres→Delta is **Lakebase CDF** (`07.5`): the `wal2delta`
-- MAGIC extension streams every insert/update/**delete** into `lb_<table>_history` Delta tables, no code. (Don't
-- MAGIC confuse it with a **synced table**, which goes the *other* way — Delta→Postgres, to serve apps; see `07.1`
-- MAGIC §3.) We use CTAS here so `refresh` can re-run an explicit, inspectable step.
-- MAGIC
-- MAGIC 📄 [Full / incremental / change-only loads](https://medium.com/@jithujosekokken/understanding-data-patterns-in-medallion-architecture-full-incremental-and-change-only-loads-e33db28e51f4)
-- MAGIC · [Lakebase OLTP → lakehouse](https://qubika.com/blog/oltp-lakehouse-databricks-lakebase/)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q3 — So what does **silver** look like for a pristine OLTP? (preview of stage 08)
-- MAGIC Databricks lists silver's operations as *"schema enforcement, handling of null and missing values, data
-- MAGIC deduplication, … type casting, joins"* and *"always include at least one validated, **non-aggregated**
-- MAGIC representation of each record"* (aggregation is gold). When bronze already mirrors a clean relational
-- MAGIC source, most of that is a **no-op** and silver collapses to a light subset:
-- MAGIC
-- MAGIC | Silver operation (per docs) | For a pristine OLTP | Example (this tutorial's `silver_customers`) |
-- MAGIC |---|---|---|
-- MAGIC | Type casting / schema enforcement | ✅ | `cast(annual_revenue as decimal(14,2))`, `cast(onboarded_date as date)` |
-- MAGIC | Deduplication → one validated current-state row per key | ✅ **the key move** | `qualify row_number() over (partition by customer_id order by updated_at desc) = 1` |
-- MAGIC | Joins / conform / enrich | ✅ light | `silver_invoices` joins `silver_contracts` to carry `customer_id` + `contract_type` |
-- MAGIC | Null / validity handling | ✅ light guard | `where invoice_id is not null and contract_id is not null` |
-- MAGIC | Non-aggregated, row-level | ✅ | one row per customer / contract / invoice |
-- MAGIC | Heavy cleansing, error correction, quarantine, flatten nested | ❌ not needed | source already clean + relational |
-- MAGIC
-- MAGIC So for a clean OLTP: **silver = cast types + dedup-to-current-state + light conforming joins + null
-- MAGIC guards.** The most valuable move is turning this raw bronze snapshot into exactly **one validated,
-- MAGIC current-state row per business key** (via `updated_at`) — which is also what makes the `refresh`
-- MAGIC stage's updates resolve correctly. You'll build these in **stage 08 (`medallion`)**.
-- MAGIC
-- MAGIC 📄 [Medallion architecture — Silver](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ bronze landed. ➡️ Next: **stage 08 (`medallion`)** — build the silver models above, then gold.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
