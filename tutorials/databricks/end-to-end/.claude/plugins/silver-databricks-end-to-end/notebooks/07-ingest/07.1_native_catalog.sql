-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 7 — Ingest · the native default: **query Lakebase in place (zero-ETL)**
-- MAGIC
-- MAGIC Lakebase is **native to Databricks**, so Silverline's operational Postgres is reachable from Unity
-- MAGIC Catalog **without moving a single row**. Register the Lakebase project once as a **read-only UC catalog**
-- MAGIC and query the live tables with ordinary SQL — no pipeline, no copy, no connector. Queries are **pushed
-- MAGIC down** to Postgres and the results come back through your warehouse.
-- MAGIC
-- MAGIC This is Databricks' **LTAP** (Lake Transactional/Analytical Processing): **one** copy of the data, served
-- MAGIC both *transactionally* (Postgres / the `data-api` stage) and *analytically* (Unity Catalog), governed in
-- MAGIC one place.
-- MAGIC
-- MAGIC > 🧭 **Start here — this is the default way to read Lakebase.** There's nothing to ingest: the data is
-- MAGIC > already queryable. The **other 07.x notebooks** show when and why you'd instead **materialize a governed
-- MAGIC > Delta copy** (`07.2` CTAS · `07.3` watermark CDC · `07.4` WAL CDC · `07.5` Lakebase CDF) — which the
-- MAGIC > medallion (stage 08) builds on. See **§4** below for when each is worth it.
-- MAGIC >
-- MAGIC > 💚 **Cost:** quota only — a few reads on the serverless warehouse. **Serverless SQL warehouse required**
-- MAGIC > (a registered Lakebase catalog can't be queried from classic compute).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — How the catalog gets registered (done for you — infra is automation, not click-ops)
-- MAGIC Provisioning happens **via the CLI/API**, not the UI — so it's reproducible. Claude registers the Lakebase
-- MAGIC **Autoscaling project** (PG17) as a UC catalog with the `postgres/catalogs` API:
-- MAGIC
-- MAGIC ```bash
-- MAGIC databricks api post "/api/2.0/postgres/catalogs?catalog_id=lakebase_silverline_oltp" --profile free \
-- MAGIC   --json '{"spec":{"postgres_database":"databricks_postgres","branch":"projects/silverline-oltp/branches/production"}}'
-- MAGIC ```
-- MAGIC
-- MAGIC The equivalent **UI** path (awareness only): **Catalog Explorer → ➕ → Create a catalog → type _Lakebase
-- MAGIC Postgres_ → _Autoscaling_ →** pick project `silverline-oltp`, branch `production`, database
-- MAGIC `databricks_postgres` **→ Create**.
-- MAGIC
-- MAGIC > 🔒 The result is **read-only** — you still manage the data through Lakebase; Unity Catalog just governs
-- MAGIC > and queries it (permissions, lineage, audit).
-- MAGIC >
-- MAGIC > ⚠️ **Not the old command.** `databricks database create-database-catalog` is for legacy **PG16
-- MAGIC > instances** and fails on a PG17 **project** with *"Database instance is not found"*. Autoscaling
-- MAGIC > projects use the `postgres/catalogs` API above (verified live on Free Edition).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Query the live OLTP directly (zero copy)
-- MAGIC `lakebase_silverline_oltp.public.<table>` reads Postgres **in real time** — no Delta, no staleness. These
-- MAGIC are the same explorations `05.2_data_model` ran over psycopg, now as plain warehouse SQL.

-- COMMAND ----------

SELECT 'customers' AS table_name, count(*) AS rows FROM lakebase_silverline_oltp.public.customers
UNION ALL SELECT 'contracts', count(*) FROM lakebase_silverline_oltp.public.contracts
UNION ALL SELECT 'invoices',  count(*) FROM lakebase_silverline_oltp.public.invoices
ORDER BY table_name;   -- expect customers 60 · contracts 85 · invoices 1452

-- COMMAND ----------

-- Principal financed by segment — a customer⋈contract join, straight off the live OLTP (pushed down to Postgres)
SELECT c.segment, count(*) AS contracts, round(sum(co.principal)) AS principal_financed
FROM lakebase_silverline_oltp.public.customers c
JOIN lakebase_silverline_oltp.public.contracts co USING (customer_id)
GROUP BY c.segment
ORDER BY principal_financed DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 — The three ways data crosses the OLTP ⇄ lakehouse line
-- MAGIC "Native" can mean three different things — don't confuse them. This notebook is the **first row**:
-- MAGIC
-- MAGIC | Direction | Feature | What it does | In this tutorial |
-- MAGIC |---|---|---|---|
-- MAGIC | **Postgres → query in UC** *(no copy)* | **Registered Lakebase catalog** (this notebook) | read live OLTP through UC; queries pushed down to Postgres | ✅ the zero-ETL **default** |
-- MAGIC | **Postgres → Delta** *(copy / CDC)* | CTAS · watermark · WAL · **Lakebase CDF** | materialize a **governed Delta copy** (history, time-travel) | ✅ `07.2`–`07.5` |
-- MAGIC | **Delta → Postgres** *(serving)* | **Synced tables** (SDK/API: `w.postgres.create_synced_table`) | publish lakehouse results back to Postgres so apps can read them | ↗ *serving* direction — not ingest |
-- MAGIC
-- MAGIC The **synced-table** row is the *reverse* of ingest (Delta→Postgres, GA) — it's how you'd serve a gold
-- MAGIC table back to an app, not how you bring OLTP into bronze. Mentioned so you don't reach for it here.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4 — If it's native, why do `07.2`–`07.5` copy into Delta at all?
-- MAGIC Because the read-only catalog gives you the live **current state** — perfect for exploring and joining,
-- MAGIC but not everything analytics needs. You **materialize a Delta copy** when you want:
-- MAGIC
-- MAGIC - **History + time-travel** — the catalog shows Postgres *as it is now*; Delta retains versions (`VERSION AS OF`).
-- MAGIC - **Decoupling** — heavy analytical scans shouldn't load the operational database; **bronze** isolates them.
-- MAGIC - **The medallion** — stage 08 builds `silver`/`gold` from a **stable, governed bronze** Delta layer, not a live link.
-- MAGIC - **Change capture** — deletes/updates *over time* (`07.3` watermark, `07.4` WAL, `07.5` CDF) — a point-in-time read can't see them.
-- MAGIC
-- MAGIC **Rule of thumb: native to _query_ now; Delta to _govern history_ and power the medallion.** With clean,
-- MAGIC modest OLTP like Silverline's, you could even analyze straight off this catalog — we still land bronze to
-- MAGIC teach the pattern and get the decoupling/replay benefits.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ✅ You queried Silverline's live operational data through Unity Catalog with **zero ETL** — the LTAP
-- MAGIC native path, the default way to read Lakebase.
-- MAGIC
-- MAGIC ➡️ Next: **`07.2_ctas_snapshot`** — materialize this same data into a governed Delta **bronze** that the
-- MAGIC medallion builds on (and the baseline the CDC patterns refine).

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
