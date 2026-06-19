<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Refresh — change in Lakebase → propagates to gold

An honest **batch-refresh + lineage** demo: edit Silverline Capital's operational source (Lakebase),
re-ingest the changed tables to bronze, re-run the medallion, and **prove the change reached silver/gold**
end to end — no infra to stand up.

> 🧠 **This is NOT log-based CDC.** It's a full batch re-read of the source (`CREATE OR REPLACE` the bronze
> tables, then rebuild). It teaches *change propagation through the medallion + lineage*, not streaming
> change capture. Real CDC — append-only change feeds, Auto Loader, Debezium-style log capture — is the
> separate **`silver-databricks-streaming`** tutorial. Here, the OLTP source is right next door in the same
> platform, so a re-CTAS is the simplest correct way to refresh.

**Cost:** Quota only — a few Postgres writes + a re-ingest + a dbt re-run; all serverless.

**Precondition:** the `ingest` and `medallion` stages done; Lakebase reachable (`PGPASSWORD` mintable).

This is an **interactive walkthrough** — pause after each section.

---

> ▶️ **Delivered as a notebook:** `SilverAIWolf/09-refresh/09.1_refresh` (serverless) does all of the below —
> applies the change-set (psycopg), re-ingests bronze, triggers the dbt Job, and runs the assertions. The
> CLI/`mise` commands below are the equivalent if you prefer the terminal.

## Section 1 — Apply a change-set to the Lakebase source

```bash
cd tutorials/databricks/end-to-end
# PG17 Autoscaling project → mint via the postgres API (the old database-API command no longer applies):
EP=projects/silverline-oltp/branches/production/endpoints/primary
export PGPASSWORD="$(databricks --profile free postgres generate-database-credential "$EP" -o json | jq -r '.token')"
mise run lakebase:simulate
```
The script (`scripts/lakebase_simulate.py`) applies a **deterministic, idempotent** change-set — re-running
converges to the same state:

| Op | Table | Change |
|----|-------|--------|
| UPDATE | `customers` | customer 1 → `annual_revenue = 123456789.00` |
| UPDATE | `invoices` | invoice 1 → `amount = 987654.00`, `status = 'overdue'` |
| UPDATE | `contracts` | contract 1 → `status = 'delinquent'` |
| INSERT | `customers` | customer 9001 (`Simulated Logistics Co`) |
| INSERT | `invoices` | invoice 900001 (contract 1, `amount = 4242.00`, `status = 'open'`) |
| DELETE | `payments` then `invoices` | invoice 3 — its dependent **payment is deleted first** (FK `payments.invoice_id`) |

**Pause.** Confirm the simulate reported the change-set applied (render as `AskUserQuestion`).

---

## Section 2 — Re-ingest the changed tables to bronze

Only three tables changed — re-`CREATE OR REPLACE` just those (idempotent CTAS, same as `ingest`):

```bash
CAT=lakebase_silverline_oltp
for t in customers contracts invoices; do
  mise run sql "CREATE OR REPLACE TABLE silverline.bronze.$t AS SELECT * FROM $CAT.public.$t"
done
```

> 🧱 **The "refresh" is the re-read.** Re-querying the native Lakebase UC catalog picks up the current
> Postgres state and overwrites the bronze Delta copy. In production you'd schedule this (a job/trigger);
> here you run it on demand. It is a batch snapshot, not a change stream.

**Pause.** Confirm the three bronze tables re-ingested (render as `AskUserQuestion`).

---

## Section 3 — Re-run the medallion

```bash
mise run medallion:dbt        # rebuild silver + gold from the new bronze
# (optional) re-run the SDP pipeline too, to keep the *_sdp tables in sync
```

**Pause.** Confirm the medallion re-ran green (render as `AskUserQuestion`).

---

## Section 4 — Assert the change propagated (silver)

```bash
mise run sql "
SELECT
  (SELECT count(*) FROM silverline.silver.silver_invoices  WHERE invoice_id = 900001) AS insert_present,    -- 1
  (SELECT count(*) FROM silverline.silver.silver_invoices  WHERE invoice_id = 3)      AS delete_dropped,    -- 0
  (SELECT amount   FROM silverline.silver.silver_invoices  WHERE invoice_id = 1)      AS update_amount,     -- 987654.00
  (SELECT status   FROM silverline.silver.silver_invoices  WHERE invoice_id = 1)      AS update_status,     -- overdue
  (SELECT status   FROM silverline.silver.silver_contracts WHERE contract_id = 1)     AS contract1_status,  -- delinquent
  (SELECT annual_revenue FROM silverline.silver.silver_customers WHERE customer_id = 1)  AS customer1_revenue, -- 123456789.00
  (SELECT count(*) FROM silverline.silver.silver_customers WHERE customer_id = 9001)  AS new_customer"      -- 1
```
Expect: `insert_present=1`, `delete_dropped=0`, `update_amount=987654.00`, `update_status=overdue`,
`contract1_status=delinquent`, `customer1_revenue=123456789.00`, `new_customer=1` — the source change is
now in silver, end to end.

> ℹ️ The new invoice 900001 has `schedule_id = NULL` but a valid `contract_id = 1`, so it passes
> `silver_invoices`' not-null guard and joins to contract 1 (carrying its `customer_id` + `contract_type`).

**Pause.** Confirm all seven silver assertions hold (render as `AskUserQuestion`).

---

## Section 5 — Assert it reached gold (lineage all the way through)

The same change rolls up into the business layer. Invoice 1 flipping to `overdue` plus the new `open`
invoice 900001 both land on contract 1's row in `gold_contract_aging`:

```bash
mise run sql "SELECT contract_id, overdue_amount, open_amount, paid_amount, total_billed
              FROM silverline.gold.gold_contract_aging
              WHERE contract_id = 1"
# overdue_amount now includes invoice 1's 987654.00; open_amount includes invoice 900001's 4242.00
```

That's bronze → silver → gold lineage on a real source edit: one `UPDATE`/`INSERT`/`DELETE` in Lakebase,
re-ingested and rebuilt, visibly reshaping the gold collections view.

**Pause.** Confirm contract 1's aging row reflects the new overdue + open amounts (render as `AskUserQuestion`).

---

## Recap

- ✓ Edited the **Lakebase** source (deterministic, idempotent insert/update/delete)
- ✓ Re-ingested the changed tables → re-ran the medallion → **change reached silver and gold** (verified per-row)
- ✓ A clear **batch-refresh + lineage** demo — explicitly **not** log-based CDC (that's the `silver-databricks-streaming` tutorial)
- ✓ Re-runnable + idempotent, all serverless

**Cost now:** quota only. **Phase C (Lakehouse) complete** — stages 7–9 of 12 done.
