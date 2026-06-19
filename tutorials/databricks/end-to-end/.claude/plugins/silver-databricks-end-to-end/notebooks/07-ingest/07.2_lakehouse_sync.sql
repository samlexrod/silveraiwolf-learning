-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 7 — Ingest · the **managed** Postgres → Delta CDC: **Lakebase CDF**
-- MAGIC
-- MAGIC The **managed, production-grade** way to land Lakebase changes into Unity Catalog is **Lakebase Change
-- MAGIC Data Feed (CDF)** — the `wal2delta` extension reads the WAL and writes `lb_<table>_history` Delta tables
-- MAGIC (every insert/update/**delete**, `_pg_change_type` + LSN + xid + timestamp), flushed ~15s.
-- MAGIC
-- MAGIC > ✅ **It's a real feature, surfaced in your Lakebase project (Change Data Feed tab → Start).** The
-- MAGIC > hands-on walkthrough is **`07.5_lakebase_cdf`**. ⚠️ On **Free Edition** it needs **PG17** + a
-- MAGIC > **non-default-storage** destination catalog — Free Edition gives PG16 + default-storage, so it may not
-- MAGIC > stream; `07.4_wal_cdc` is the runnable Free-Edition equivalent (same WAL decoding, by hand).
-- MAGIC >
-- MAGIC > *(Earlier this notebook called it "Lakehouse Sync / private preview, no CLI" — that was imprecise;
-- MAGIC > the actual feature is Lakebase CDF. See `07.5`.)*

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Don't confuse the two "sync" features (opposite directions)
-- MAGIC
-- MAGIC | Feature | Direction | Purpose | On Free Edition |
-- MAGIC |---|---|---|---|
-- MAGIC | **Lakehouse Sync** | **Lakebase Postgres → Delta/UC** (CDC) | bring operational data *into* the lakehouse (our bronze need) | ⚠️ Private Preview, no CLI |
-- MAGIC | **Synced tables** (`create-synced-database-table`) | **Delta/UC → Lakebase Postgres** | *serve* lakehouse data back to apps as read-only Postgres relations | ✅ GA, but **wrong direction** for ingest |
-- MAGIC
-- MAGIC The CLI command we *do* have (`databricks database create-synced-database-table`) is for the **serving**
-- MAGIC direction (Delta→Postgres) — not bronze ingestion. Lakehouse Sync is the ingest direction.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## What Lakehouse Sync gives you over the other two patterns
-- MAGIC - **Delete-aware CDC** — captures inserts **and updates and deletes** (the watermark pattern in `07.3`
-- MAGIC   can't see deletes; CTAS in `07.1` only sees current state).
-- MAGIC - **Full change history** — each change appended as a row, governed in Unity Catalog.
-- MAGIC - **Fully managed** — serverless sync compute decoupled from your query warehouse; monitoring + retries.
-- MAGIC - **No watermark bookkeeping** — no `updated_at` column or trigger needed; it reads the Postgres WAL/CDC.
-- MAGIC
-- MAGIC **How you'd enable it (when available):** in the Lakebase project UI, configure **Lakehouse Sync** for the
-- MAGIC database/tables → pick a target UC schema (e.g. `silverline.bronze`) → it provisions a managed CDC
-- MAGIC pipeline Postgres → Delta. (Check your project's UI for a *Lakehouse Sync* / *Sync to Unity Catalog*
-- MAGIC option; if it's absent, the preview isn't enabled for your workspace yet.)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Why we still teach `07.1` (CTAS) and `07.3` (watermark CDC)
-- MAGIC Even once Lakehouse Sync is GA, the manual patterns are worth understanding: CTAS is the universal
-- MAGIC full-refresh baseline for *any* source, and the `updated_at` **watermark** pattern is the portable
-- MAGIC "frugal CDC" you reach for when a source has no managed CDC (it's the same shape we use for SQL Server
-- MAGIC via its change tables — only the watermark differs: LSN there, timestamp here).
-- MAGIC
-- MAGIC 📄 [Lakehouse Sync (Postgres→Delta CDC, preview)](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/lakehouse-sync)
-- MAGIC · [Synced tables (Delta→Postgres serving)](https://docs.databricks.com/aws/en/oltp/instances/sync-data/sync-table)
-- MAGIC
-- MAGIC ➡️ Next: **`07.3_watermark_cdc`** — the hands-on custom CDC.
