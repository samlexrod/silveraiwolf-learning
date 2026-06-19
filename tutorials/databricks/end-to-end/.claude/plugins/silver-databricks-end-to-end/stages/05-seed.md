<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Seed — load Silverline Capital's data (structured + unstructured)

**Silverline Capital** is our fictional **equipment lease & loan finance company**: it underwrites
applications from business customers, books them into lease/loan **contracts** backed by financed
**equipment**, then bills and collects on a monthly schedule. In this stage you seed **both** of its
operational sources:

- **Structured** — the **full 9-table OLTP** in **Lakebase** (Postgres 17), filled with **deterministic**
  mock data, so every downstream phase (lakehouse, medallion, analytics) has a real source to pull from.
- **Unstructured** — Silverline's **documents**: a lease/loan **agreement PDF** per contract (plus a few
  **credit-memo** files), generated from the same seed data and landed in the Unity Catalog **volume**
  (`silverline.bronze.files`). These are what the later **`agents`** phase embeds for **Vector Search**.

**Cost:** Free — counts against your fair-use quota. A few thousand `INSERT`s on serverless Postgres + a
handful of small files uploaded to the volume.

**Precondition:** the `provision` stage done — Lakebase is reachable, `LAKEBASE_HOST` / `LAKEBASE_DB` /
`LAKEBASE_USER` are in `.env`, and you can mint a `PGPASSWORD` credential.

This is an **interactive walkthrough** — pause after each section. You run it; report counts.

---

## Section 1 — Meet the data model

Below is the conceptual overview of the model. The hands-on order in the workspace is **seed first, then
explore**: run **`05.1_seed_oltp`** (Section 3) to load the data, then **`05.2_data_model`** is your ERD +
data-dictionary reference whose bottom cells **explore the seeded data live via `psycopg`** (counts,
principal by segment, status mix). Both are Python notebooks Claude pushes to `SilverAIWolf/05-seed/`.
(Within a stage, notebooks are numbered `NN.1`, `NN.2` in run order.)

> 🔭 Querying the same data as **SQL** (`lakebase_silverline_oltp.public.<table>`) needs the `ingest` stage
> to register Lakebase in Unity Catalog — that SQL exploration lives in stage 07, not here. We use `psycopg`
> in this stage because a notebook can't reach Lakebase Postgres via SQL until that registration happens.

The seed script (`scripts/lakebase_seed.py`) stands up Silverline's whole **origination → booking →
billing → payments** lifecycle as 9 related tables. Here's the compact ERD:

```
customers ── applications ──> contracts ──< contract_assets >── equipment ──> vendors
                                  │                                             ▲
                                  ├──< payment_schedule                         │
                                  └──< invoices ──< payments      equipment.vendor_id ┘
```

| Table | Grain / role | Key columns |
|-------|--------------|-------------|
| `customers` | the businesses we finance | customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date |
| `vendors` | who supplies the equipment | vendor_id, name, vendor_type, region |
| `equipment` | assets we finance, per vendor | equipment_id, vendor_id, category, make, model, serial_number, cost, residual_value, in_service_date |
| `applications` | the credit pipeline | application_id, customer_id, vendor_id, amount_requested, status *(submitted / approved / declined / booked)*, submitted_date, decision_date |
| `contracts` | booked lease/loan deals | contract_id, application_id, customer_id, contract_type *(lease / loan)*, status *(active / paid_off / delinquent / charged_off)*, principal, apr, term_months, start_date, end_date, residual_value |
| `contract_assets` | which equipment backs a contract | contract_id, equipment_id, allocated_cost *(M:N bridge)* |
| `payment_schedule` | the amortization plan | schedule_id, contract_id, period_no, due_date, principal_due, interest_due, total_due |
| `invoices` | bills issued for elapsed periods | invoice_id, contract_id, schedule_id, invoice_date, due_date, amount, status *(open / paid / overdue)* |
| `payments` | cash received against invoices | payment_id, invoice_id, paid_date, amount, method |

**Why it matters:** this is a realistic normalized OLTP — many-to-many (`contract_assets`), a status
pipeline (`applications`), and derived facts (`payment_schedule` / `invoices` / `payments` are computed
from each contract's amortization). That richness is what makes the later medallion + analytics work
meaningful instead of toy joins.

**Pause.** Confirm the model makes sense before you load it (render as `AskUserQuestion`).

---

## Section 2 — Seed the OLTP from the notebook (`05.1_seed_oltp`)

Run **`SilverAIWolf/05-seed/05.1_seed_oltp`** in the workspace (serverless, **Run All**). It does everything
in-workspace — no shell, no token to paste:

1. `%pip install "psycopg[binary]" "databricks-sdk>=0.61.0"` + `restartPython()`.
2. **Mints a credential via the SDK** using the notebook's own identity — the *documented Lakebase pattern*
   for an Autoscaling project: `w.postgres.get_endpoint(...)` for the host +
   `w.postgres.generate_database_credential(...)` for the short-lived OAuth token (the Postgres password).
3. Builds the **deterministic** dataset (`MOCK_SEED=42` → identical rows) and seeds via `psycopg` over SSL.

> ⚠️ **SDK version matters.** The `w.postgres` service (Autoscaling projects) needs a **current
> `databricks-sdk`**; serverless ships an older one, so the notebook upgrades it in cell 1. Without that
> you'd hit `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'`.

Expected final output:

```
✓ seeded Lakebase (Silverline Capital): customers=60 vendors=15 equipment=220 applications=140 contracts=85 contract_assets=180 payment_schedule=2904 invoices=1452 payments=1291
```

The fixed dimensions (customers, vendors, equipment, applications) are sized directly; the rest are
**derived** — ~60% of applications get `booked` into contracts, each gets an amortization `payment_schedule`,
and only periods elapsed as of the `2026-06-01` snapshot produce `invoices` (and a `payment` when paid).

> 🔁 **Idempotent:** re-running `TRUNCATE`s + reloads the same rows. (Later, the `refresh` stage mutates
> these to demonstrate change propagation.)
>
> 🛠️ **Local fallback** (if you'd rather not use the notebook): `export PGPASSWORD="$(databricks --profile
> free postgres generate-database-credential projects/silverline-oltp/branches/production/endpoints/primary \
> | jq -r '.token')"` then `mise run lakebase:seed` (`scripts/lakebase_seed.py`, same logic).

**Pause.** Confirm the seed reported the 9 counts above — especially `customers=60` and `contracts=85`
(render as `AskUserQuestion`).

---

## Section 3 — Explore the seeded data (`05.2_data_model`)

Run **`SilverAIWolf/05-seed/05.2_data_model`** (serverless, Run All) — the ERD + data dictionary, plus a
**live exploration** that connects to Postgres with `psycopg` (same documented pattern) and shows:
- **row counts** per table (matching the seed),
- **principal financed by customer segment** (a `customers → contracts` join),
- the **contract status mix** (active / delinquent / charged_off / paid_off).

> 🔭 Querying this same data as **SQL** (`lakebase_silverline_oltp.public.<table>`) needs the `ingest` stage
> to register Lakebase in Unity Catalog — that SQL exploration lives in stage 07. Here we use `psycopg`
> because a notebook can't reach Lakebase Postgres via SQL until that registration happens.

**Pause.** Confirm the exploration returns sensible rows (render as `AskUserQuestion`).

---

## Section 4 — Land Silverline's unstructured documents (`05.3_documents`)

Silverline's reality isn't only rows: every contract has a **signed agreement PDF**, and underwriters keep
**credit memos** — the *unstructured* source the later **`agents`** phase embeds for Vector Search. Run
**`SilverAIWolf/05-seed/05.3_documents`** (serverless, Run All). It:

1. installs `psycopg` + `databricks-sdk>=0.61.0` + `reportlab`,
2. pulls the contracts/customers/equipment **from the already-seeded Postgres** (single source of truth),
3. renders one **`contract_<id>.pdf`** per booked contract + a few **`credit_memo_<customer_id>.md`**, and
4. writes them straight to the UC volume via its `/Volumes/...` path:

```
/Volumes/silverline/bronze/files/contracts/contract_<id>.pdf
/Volumes/silverline/bronze/files/memos/credit_memo_<customer_id>.md
```

> 🔗 **Why the filename carries the id:** `contract_<id>` / `credit_memo_<customer_id>` lets the future
> `agents` phase join an unstructured RAG hit back to the structured `contracts` / `customers` rows.

> 💡 The volume is **format-agnostic** (PDF, Markdown, text, images, Office docs); parsing → embedding →
> indexing happens later in the `agents` phase, not here.
>
> 🛠️ **Local fallback:** `mise run docs:seed` (`scripts/generate_contract_docs.py`) generates + uploads the
> same files (uses a PAT; `-- --local-only` to generate without uploading).

Verify by browsing **Catalog → silverline → bronze → files**, or the notebook's final `dbutils.fs.ls` cell.

**Pause.** Confirm the contract PDFs + memos are in the volume (render as `AskUserQuestion`).

---

## Recap

- ✓ Silverline Capital's **9-table OLTP** created in **Lakebase Postgres 17** and seeded (customers 60 · vendors 15 · equipment 220 · applications 140 · contracts 85 · contract_assets 180 · payment_schedule 2904 · invoices 1452 · payments 1291)
- ✓ **Deterministic + idempotent** — same `MOCK_SEED` → identical rows
- ✓ Seeded + explored from **notebooks** (`05.1_seed_oltp` → `05.2_data_model`) via the documented Lakebase psycopg pattern
- ✓ **Unstructured docs landed** — contract PDFs + credit memos in the volume `silverline.bronze.files` (the source for the later `agents` phase's Vector Search), written by `05.3_documents`

**Cost now:** quota only. (`data-api` is the last Lakebase stage.)
