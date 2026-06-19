<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Ingest — Lakebase → Unity Catalog → bronze (four patterns)

Bring Silverline Capital's operational tables into the lakehouse. Lakebase is **native to Unity Catalog** —
**register the Lakebase database in UC** (a real UC catalog you query *directly*, no federation), then land
into `silverline.bronze` — and this stage shows **four ways to do that landing**, from a simple full
snapshot to delete-aware CDC straight off the Postgres WAL.

**Cost:** Quota only — one registration + CTAS / incremental reads on the serverless warehouse; idles to ~0.

**Precondition:** `provision` + `seed` done — the 9-table OLTP is seeded; `LAKEBASE_*` in `.env`.

---

## Section 1 — Register the Lakebase database in Unity Catalog (CLI)

Lakebase is a **first-class UC citizen** — it registers as an ordinary **UC catalog** queried natively in
SQL, side by side with your Delta tables. **Native, not federated** (Lakehouse Federation is for *external*
engines; Lakebase is inside the platform).

**Claude registers it via CLI** (provisioning):
```bash
databricks --profile free database create-database-catalog \
  lakebase_silverline_oltp silverline-oltp databricks_postgres
echo 'LAKEBASE_UC_CATALOG=lakebase_silverline_oltp' >> tutorials/databricks/end-to-end/.env
mise run sql 'SELECT count(*) AS customers FROM lakebase_silverline_oltp.public.customers'   # expect 60
```

> ℹ️ Postgres tables surface under `lakebase_silverline_oltp.public.<table>`, governed by Unity Catalog.

**Pause.** Confirm the native UC catalog is queryable (`…public.customers` = 60) (render as `AskUserQuestion`).

---

## Section 2 — Land into bronze: the four patterns

Each is a notebook in `SilverAIWolf/07-ingest/`. Run 07.1 + 07.3 + 07.4 (07.2 is read-only).

| # | Notebook | Pattern | Mechanism | Inserts | Updates | **Deletes** | Managed |
|---|----------|---------|-----------|:------:|:------:|:----------:|:-------:|
| 07.1 | `07.1_ctas_snapshot` | **Full snapshot** | `CREATE OR REPLACE … AS SELECT *` (all 9 tables) | ✅ | ✅ | ✅ (rewrite) | n/a |
| 07.2 | `07.2_lakehouse_sync` | **Managed CDC overview** → points to 07.5 | (concepts: Lakebase CDF vs synced tables) | — | — | — | — |
| 07.3 | `07.3_watermark_cdc` | **Watermark CDC** (frugal, portable) | `updated_at` timestamp watermark → append; silver dedups | ✅ | ✅ | ❌ | ❌ |
| 07.4 | `07.4_wal_cdc` | **WAL logical-decoding CDC** (DIY, delete-aware) | `test_decoding` slot + batch `pg_logical_slot_get_changes` | ✅ | ✅ | **✅** | ❌ |
| 07.5 | `07.5_lakebase_cdf` | **Lakebase CDF** — *native managed* CDC | `wal2delta` → `lb_<table>_history` Delta (UC) | ✅ | ✅ | **✅** | ✅ |

Verified Free-Edition facts behind these (docs lag — confirmed live):
- **Native registration** works via `database create-database-catalog` (CLI).
- **Synced tables** (`create-synced-database-table`) are the *reverse* direction (Delta→Postgres serving) — not bronze ingest.
- **Lakebase CDF** is the *native managed* Postgres→Delta CDC (`wal2delta` → `lb_<table>_history`), `07.5`. It needs three things, all now satisfied: **(1) PG17** — provision via `postgres create-project … pg_version 17` (the `database` API only gives PG16); **(2) a non-default-storage destination catalog** — `silverline_cdf` on an external location; **(3) `REPLICA IDENTITY FULL`** on the source tables. Enabling is **UI-only** (no API). ✅ Verified streaming once all three are met.
  - 💳 **Opt-in cost:** the external location is created via Databricks **External Locations → AWS quickstart**, which provisions an **S3 bucket + IAM role in the learner's own personal AWS account** (CloudFormation) — **billed by AWS to the learner**, outside Free Edition's $0/quota model. This is the **same external location** the `landing-zone` stage sets up in its opt-in Section 4 — reuse it if created there. Optional; only for learners who want CDF. The no-cost path is `07.4_wal_cdc`.
- The `updated_at` watermark needs a **`BEFORE UPDATE` trigger** (added in provisioning on `customers`/`contracts`/`invoices`).
- WAL: `wal_level=logical` ✅, `rolreplication` ✅, **`CREATE PUBLICATION` blocked**, but a `test_decoding` slot consumed in batch captures **deletes**. ⚠️ A logical slot **pins WAL until consumed** — 07.4 consumes + monitors + has a teardown cell.

**Pause.** Confirm bronze landed — 9 CTAS tables, 3 `*_cdc` watermark logs, `cdc_changes` (WAL); and note whether CDF (07.5) streams on your PG17 project (render as `AskUserQuestion`).

---

## Recap

- ✓ **Lakebase registered in UC natively** via CLI (`lakebase_silverline_oltp`) — queried directly, no federation
- ✓ **bronze landed multiple ways:** CTAS snapshot (9 tables) · watermark CDC (`*_cdc`) · WAL CDC (`cdc_changes`, delete-aware) · **Lakebase CDF** (07.5 — native managed; PG17-gated on Free Edition)
- ✓ Verified the medallion's three sources (60 / 85 / 1452) and live **delete capture** off the WAL

**Cost now:** quota only.
