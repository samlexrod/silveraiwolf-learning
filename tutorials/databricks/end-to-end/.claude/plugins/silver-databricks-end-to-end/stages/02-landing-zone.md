<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Landing zone — the shared Unity Catalog home

Create the **one catalog every track uses** — `silverline` — with medallion schemas and a managed
volume. On Free Edition you're the **owner** of the metastore and catalog (no service principal), so this
is just a few `CREATE` statements.

**Cost:** Free — Unity Catalog objects are free; the only compute is a few-second warehouse query (auto-stops). No quota concern.

**Precondition:** `connect` done — CLI authenticated (`free` profile) and the Starter Warehouse id captured.

This is an **interactive walkthrough** — pause after each section. You run the SQL; report results.

---

## Section 1 — Create the catalog + medallion schemas

Run this in the workspace **SQL editor** (paste all, Run) — or via the CLI (Section 3). It's idempotent:

```sql
CREATE CATALOG IF NOT EXISTS silverline
  COMMENT 'Shared landing zone for the Databricks end-to-end tutorial phases (lakebase/lakehouse/analytics/ml/agents).';

CREATE SCHEMA IF NOT EXISTS silverline.bronze COMMENT 'Raw / ingested';
CREATE SCHEMA IF NOT EXISTS silverline.silver COMMENT 'Cleaned / current-state';
CREATE SCHEMA IF NOT EXISTS silverline.gold   COMMENT 'Business / serving';
```

> 🧱 **One catalog, schemas as the medallion** — simpler than the sibling's multi-catalog, SP-owned model
> (which doesn't apply on Free Edition). Every track reads/writes `silverline.{bronze,silver,gold}`.

**Pause.** Confirm the catalog + three schemas exist (render as `AskUserQuestion`).

---

## Section 2 — Create the managed volume (for seed data + PDFs)

Free Edition has **no external storage** — use a **managed** UC volume (Databricks-managed storage):

```sql
CREATE VOLUME IF NOT EXISTS silverline.bronze.files
  COMMENT 'Managed volume — seed files + contract PDFs for the RAG track.';
-- files land under:  /Volumes/silverline/bronze/files/
```

> 🧠 **Managed vs external — who owns the storage** (the same axis applies to **volumes and tables**):
> - **Managed** — Unity Catalog owns the metadata **and** the data files, in Databricks-managed storage. UC
>   picks the location and the lifecycle follows the object: **drop it → the files are deleted.** No cloud setup.
> - **External** — UC owns only the metadata; the data lives at a `LOCATION` you give in **your own cloud
>   bucket** (S3/ADLS/GCS) via an *external location* + *storage credential*: **drop it → the files stay.**
>
> | | Managed | External |
> |---|---|---|
> | Data files | Databricks-managed | your cloud bucket (`LOCATION '…'`) |
> | Drop the object | files **deleted** | files **kept** |
> | Setup needed | none | external location + storage credential |
> | Free Edition | ✅ the only option | ❌ needs the AWS quickstart (real $) |
>
> On **Free Edition** there's no external storage, so this volume — and every medallion **table** you build
> later — is **managed**. The lone exception is the optional **CDF** step in `ingest`, which needs an
> external-storage catalog from the AWS quickstart (billed to *your* AWS — opt-in).

**Pause.** Confirm the volume exists (`DESCRIBE VOLUME silverline.bronze.files`) (render as `AskUserQuestion`).

---

## Section 3 — Verify (and the CLI alternative)

Verify in the SQL editor:
```sql
SHOW SCHEMAS IN silverline;          -- expect: bronze, silver, gold (+ default/information_schema)
SHOW VOLUMES IN silverline.bronze;   -- expect: files
```

Or run any statement headless via the CLI (using the Starter Warehouse id from `connect`):
```bash
WID=<starter-warehouse-id>
databricks --profile free api post /api/2.0/sql/statements \
  --json '{"warehouse_id":"'"$WID"'","wait_timeout":"30s","statement":"SHOW SCHEMAS IN silverline"}' \
  | jq -r '.result.data_array[]?[]'
```

**Pause.** Confirm `bronze`/`silver`/`gold` + the `files` volume are present (render as `AskUserQuestion`).

---

## Recap

- ✓ Catalog **`silverline`** — the shared home for all tracks (you own it)
- ✓ Schemas **`bronze` / `silver` / `gold`** (the medallion)
- ✓ Managed volume **`silverline.bronze.files`** (`/Volumes/silverline/bronze/files/`) — no external storage needed
- ✓ Verified via `SHOW SCHEMAS` / `SHOW VOLUMES`

**Cost now:** $0 — free UC objects + a few-second query.
