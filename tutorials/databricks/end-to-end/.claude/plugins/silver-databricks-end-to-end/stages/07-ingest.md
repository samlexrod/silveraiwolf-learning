<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Ingest — query Lakebase natively, then land bronze (four materialization patterns)

Bring Silverline Capital's operational data into the lakehouse. Lakebase is **native to Databricks**, so the
**first move is zero-ETL**: register the Lakebase project as a **read-only UC catalog** and query the live
Postgres tables directly (`07.1` — Databricks' **LTAP**, no copy). Then, when you want a **governed Delta
copy** (history, decoupling, the medallion), land into `silverline.bronze` — and this stage shows **four ways
to do that landing**, from a simple full snapshot to delete-aware CDC straight off the Postgres WAL.

**Cost:** Quota only — one registration + native reads + CTAS / incremental reads on the serverless warehouse; idles to ~0.

**Precondition:** `provision` + `seed` done — the 9-table OLTP is seeded; `LAKEBASE_*` in `.env`.

---

## Section 1 — Register the Lakebase project as a native UC catalog (zero-ETL) — notebook `07.1`

Lakebase is a **first-class UC citizen** — register it once and you query the **live** Postgres tables in SQL,
side by side with your Delta tables, **no data copied** (queries push down to Postgres). This is **LTAP** —
**native, not federated** (Lakehouse Federation is for *external* engines; Lakebase is inside the platform).

**Claude registers it via the Lakebase Autoscaling project API** (PG17 — provisioning):
```bash
databricks --profile free api post "/api/2.0/postgres/catalogs?catalog_id=lakebase_silverline_oltp" \
  --json '{"spec":{"postgres_database":"databricks_postgres","branch":"projects/silverline-oltp/branches/production"}}'
echo 'LAKEBASE_UC_CATALOG=lakebase_silverline_oltp' >> tutorials/databricks/end-to-end/.env
mise run sql 'SELECT count(*) AS customers FROM lakebase_silverline_oltp.public.customers'   # expect 60
```

> ℹ️ Postgres tables surface under `lakebase_silverline_oltp.public.<table>` — **read-only**, governed by Unity
> Catalog, queryable only from a **serverless** SQL warehouse.
> ⚠️ The old `database create-database-catalog` is for legacy **PG16 instances** and fails on a PG17 project
> (*"Database instance is not found"*) — use the `postgres/catalogs` API above.

The learner then runs **`07.1_native_catalog`** to explore the live OLTP (counts + a segment join) with zero ETL.

**Pause.** Confirm the native UC catalog is queryable (`…public.customers` = 60) (render as `AskUserQuestion`).

---

## Section 2 — Read it natively, then land into bronze

Each is a notebook in `SilverAIWolf/07-ingest/`. **`07.1` reads in place (zero-ETL) — start there.** Then run
the materialization pattern(s) you want: `07.2` (CTAS) is the baseline the medallion builds on; `07.3`/`07.4`
add CDC; `07.5` is the managed option.

| # | Notebook | Pattern | Mechanism | Inserts | Updates | **Deletes** | Managed |
|---|----------|---------|-----------|:------:|:------:|:----------:|:-------:|
| **07.1** | `07.1_native_catalog` | **Native query — zero ETL** | registered Lakebase catalog; queries pushed down to Postgres | n/a | n/a | n/a | ✅ |
| 07.2 | `07.2_ctas_snapshot` | **Full snapshot** | `CREATE OR REPLACE … AS SELECT *` (all 9 tables) | ✅ | ✅ | ✅ (rewrite) | n/a |
| 07.3 | `07.3_watermark_cdc` | **Watermark CDC** (frugal, portable) | `updated_at` timestamp watermark → append; silver dedups | ✅ | ✅ | ❌ | ❌ |
| 07.4 | `07.4_wal_cdc` | **WAL logical-decoding CDC** (DIY, delete-aware) | `test_decoding` slot + batch `pg_logical_slot_get_changes` | ✅ | ✅ | **✅** | ❌ |
| 07.5 | `07.5_lakebase_cdf` | **Lakebase CDF** — *native managed* CDC | `wal2delta` → `lb_<table>_history` Delta (UC) | ✅ | ✅ | **✅** | ✅ |

Verified Free-Edition facts behind these (docs lag — confirmed live):
- **Native registration** of a PG17 project uses the **`postgres/catalogs` API** (`POST /api/2.0/postgres/catalogs`) — the old `database create-database-catalog` is PG16-instance-only and **fails on a project** (*"Database instance is not found"*). The catalog is read-only; query from a **serverless** warehouse. ✅ Verified live (counts 60/85/1452).
- **Synced tables** (SDK/API `w.postgres.create_synced_table`) are the *reverse* direction (Delta→Postgres serving) — not bronze ingest.
- **Lakebase CDF** is the *native managed* Postgres→Delta CDC (`wal2delta` → `lb_<table>_history`), `07.5`. It needs three things, all now satisfied: **(1) PG17** — provision via `postgres create-project … pg_version 17` (the `database` API only gives PG16); **(2) a non-default-storage destination catalog** — `silverline_cdf` on an external location; **(3) `REPLICA IDENTITY FULL`** on the source tables. Enabling is **UI-only** (no API). ✅ Verified streaming once all three are met.
  - 💳 **Opt-in cost:** the external location is created via Databricks **External Locations → AWS quickstart**, which provisions an **S3 bucket + IAM role in the learner's own personal AWS account** (CloudFormation) — **billed by AWS to the learner**, outside Free Edition's $0/quota model. This is the **same external location** the `landing-zone` stage sets up in its opt-in Section 4 — reuse it if created there. Optional; only for learners who want CDF. The no-cost path is `07.4_wal_cdc`.
- The `updated_at` watermark needs a **`BEFORE UPDATE` trigger** (added in provisioning on `customers`/`contracts`/`invoices`).
- WAL: `wal_level=logical` ✅, `rolreplication` ✅, **`CREATE PUBLICATION` blocked**, but a `test_decoding` slot consumed in batch captures **deletes**. ⚠️ A logical slot **pins WAL until consumed** — 07.4 consumes + monitors + has a teardown cell.

**Pause.** Confirm bronze landed — 9 CTAS tables, 3 `*_cdc` watermark logs, `cdc_changes` (WAL); and note whether CDF (07.5) streams on your PG17 project (render as `AskUserQuestion`).

---

## Recap

- ✓ **Lakebase queried natively (zero-ETL)** — registered as the read-only UC catalog `lakebase_silverline_oltp` (`07.1`, LTAP), no copy
- ✓ **bronze materialized multiple ways:** CTAS snapshot (9 tables, `07.2`) · watermark CDC (`*_cdc`) · WAL CDC (`cdc_changes`, delete-aware) · **Lakebase CDF** (`07.5` — native managed; PG17-gated on Free Edition)
- ✓ Verified the medallion's three sources (60 / 85 / 1452) and live **delete capture** off the WAL

**Cost now:** quota only.
