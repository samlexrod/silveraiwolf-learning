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

Create a **managed** UC volume (Databricks-managed storage — the zero-setup default). You'll build its
**external** counterpart hands-on in Section 4:

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
> | Where the bytes live | Databricks default | your own cloud bucket |
>
> **The choice is yours at every level** — catalog, schema, table, and volume. This tutorial uses **managed**
> by default (zero setup, no cloud account) for this volume + every medallion **table** later. **Section 4**
> then builds the **external** side hands-on — a catalog whose storage is your own cloud, plus external
> tables/volumes — so you've created **both**, the way you'd choose in production. (External storage = your own
> S3 via an external location, billed by your cloud — opt-in.) The optional **CDF** step reuses that location.

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

## Section 4 — Managed vs external, hands-on (opt-in)

Sections 1–2 built the **managed** side (the default — no cloud account, nothing to provision). Now build the
**external** side so you've created **both**, the way you'd actually choose in production: a **catalog** whose
storage is your own cloud, an external **volume**, and an external **table**. It's **opt-in** because external
storage means **your own S3** (billed by your cloud, not Free Edition quota) — skip it and the tutorial still
runs fully on managed.

> 💳 **External = your cloud = your bill.** Registering the external location runs an **AWS quickstart**
> (CloudFormation) in your AWS account → an S3 bucket + IAM role, billed by **AWS**. The tutorial's `cleanup`
> drops the Databricks objects but **not** your AWS resources — delete that CloudFormation stack yourself.

**1. Create the external location** (UI — the quickstart auto-registers the location + storage credential):
- Databricks UI → **Catalog → External Data → External Locations → Create → AWS quickstart**.
- Approve the **CloudFormation** stack in your AWS console; it creates the bucket + IAM role and registers the
  external location in Unity Catalog. Note your **bucket name**, then confirm:
  ```sql
  SHOW EXTERNAL LOCATIONS;   -- find your location's name + url (s3://<your-bucket>/…)
  ```
> 🛠️ **Manual alternative** (you already have a bucket + IAM role) — register it with SQL instead of the quickstart:
> ```sql
> CREATE STORAGE CREDENTIAL IF NOT EXISTS silverline_cred
>   WITH (AWS_IAM_ROLE 'arn:aws:iam::<acct-id>:role/<role-name>');
> CREATE EXTERNAL LOCATION IF NOT EXISTS silverline_ext_loc
>   URL 's3://<your-bucket>/silverline' WITH (STORAGE CREDENTIAL silverline_cred);
> ```

**2. A managed catalog vs an external-storage-backed catalog.** You already have `silverline` — a **managed
catalog** (no location given, so its managed objects use the metastore's default storage). Now create one whose
**managed-storage root is your own cloud**:
```sql
CREATE CATALOG IF NOT EXISTS silverline_ext
  MANAGED LOCATION 's3://<your-bucket>/silverline_ext'
  COMMENT 'Managed objects, stored on your own S3 — vs silverline (metastore default storage).';
```
> 🧠 `MANAGED LOCATION` sets **where a catalog's managed objects store their data**. *Both* catalogs hold
> **managed** objects (drop → data deleted); they differ only in **where** the bytes live — `silverline` uses
> Databricks default storage, `silverline_ext` uses your S3.

**3. An external volume** — the *unmanaged-data* side: UC owns only the metadata, the files are yours
(drop → files **kept**):
```sql
CREATE EXTERNAL VOLUME IF NOT EXISTS silverline.bronze.ext_files
  LOCATION 's3://<your-bucket>/ext_files'
  COMMENT 'External volume — contrast with the managed silverline.bronze.files.';
```

**4. An external table** — same for tabular data (drop → files **kept**), vs a managed table (drop → deleted):
```sql
CREATE TABLE IF NOT EXISTS silverline.bronze.ext_demo (id INT, note STRING)
  USING DELTA LOCATION 's3://<your-bucket>/ext_demo';
-- Managed equivalent (UC picks the location): CREATE TABLE silverline.bronze.demo (id INT, note STRING);
```

> 🔗 **The `ingest` CDF step uses this exact pattern.** CDF writes its `lb_*_history` tables as **managed**
> objects, but **requires the destination catalog's managed storage to sit on an external location** (a CDF
> requirement, any edition) — so `07.5` creates `silverline_cdf` with
> `MANAGED LOCATION 's3://<your-bucket>/lakebase_cdf'`, the same shape as `silverline_ext` above. Register the
> external location once here and CDF reuses it.

**Pause.** If you opted in: confirm `SHOW EXTERNAL LOCATIONS`, the `silverline_ext` catalog, and the external
volume/table all resolve — you've now built managed **and** external. If you skipped it: fine, the tutorial
runs fully on managed (render as `AskUserQuestion`).

---

## Recap

- ✓ Catalog **`silverline`** — the shared home for all tracks (you own it)
- ✓ Schemas **`bronze` / `silver` / `gold`** (the medallion)
- ✓ Managed volume **`silverline.bronze.files`** (`/Volumes/silverline/bronze/files/`) — managed storage, no cloud setup
- ✓ Verified via `SHOW SCHEMAS` / `SHOW VOLUMES`
- ◻️ *(Optional, Section 4)* The **external** side — an external location + an external-storage-backed catalog (`silverline_ext`) + an external volume/table on **your own cloud**, so you've built **managed and external both** (opt-in; your cloud's $; reused by the `ingest` CDF step)

**Cost now:** $0 — free UC objects + a few-second query (unless you opted into the external-storage section, which bills to your AWS).
