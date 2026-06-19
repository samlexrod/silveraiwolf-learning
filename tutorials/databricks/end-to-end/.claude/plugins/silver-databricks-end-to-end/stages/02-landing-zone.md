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
> | Free Edition | ✅ default (no setup) | ⚠️ opt-in via the AWS quickstart (your cloud, $) |
>
> On **Free Edition** there's no *built-in* external storage, so the tutorial stays **managed** throughout
> (this volume + every medallion **table** later). But external **is** possible: register an **external
> location** (e.g. the **AWS quickstart** → your own S3 bucket) + a storage credential, and external
> **tables and volumes** both become available — billed to **your** cloud account (real $), so it's opt-in.
> The optional **CDF** step in `ingest` is just one example that uses such an external-storage catalog.

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

## Section 4 — (Opt-in, real $) External storage on your own cloud

Everything above is **managed** and free. This section is **optional** and **costs real money** — it provisions
an **S3 bucket + IAM role in YOUR own AWS account** (not Free Edition quota). Do it only if you want to *see*
external tables/volumes, or you plan to run the optional **CDF** step in `ingest` (which requires it).

> 💳 **Cost + ownership.** The **AWS quickstart** runs a **CloudFormation** stack in your AWS account → creates
> an S3 bucket + IAM role, billed by **AWS**. The tutorial's `cleanup` drops the Databricks objects but **not**
> your AWS resources — you delete that CloudFormation stack yourself.

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
> CREATE EXTERNAL LOCATION IF NOT EXISTS silverline_ext
>   URL 's3://<your-bucket>/silverline' WITH (STORAGE CREDENTIAL silverline_cred);
> ```

**2. An external volume** — files live in *your* bucket; drop → files **kept**:
```sql
CREATE EXTERNAL VOLUME IF NOT EXISTS silverline.bronze.ext_files
  LOCATION 's3://<your-bucket>/ext_files'
  COMMENT 'External volume on your own S3 — contrast with the managed silverline.bronze.files.';
```

**3. An external table** — vs the managed default:
```sql
CREATE TABLE IF NOT EXISTS silverline.bronze.ext_demo (id INT, note STRING)
  USING DELTA LOCATION 's3://<your-bucket>/ext_demo';
-- Managed equivalent (UC picks the location): CREATE TABLE silverline.bronze.demo (id INT, note STRING);
-- Drop the EXTERNAL table → s3://…/ext_demo files STAY in your bucket; drop a MANAGED table → files deleted.
```

**4. Reused by the CDF step.** This **same external location** is the prerequisite for the optional **Lakebase
CDF** path in `ingest` (`07.5`), which creates an external-storage *catalog* (`silverline_cdf`,
`MANAGED LOCATION 's3://<your-bucket>/lakebase_cdf'`) on it. Set it up once here and CDF just reuses it — the
external volume/table above and the CDF catalog all sit on the one external location. (CDF needs a *catalog*,
not a volume — same storage, different UC object.)

**Pause.** If you opted in: confirm `SHOW EXTERNAL LOCATIONS` lists your location and the external volume/table
resolve. If you skipped it: fine — the tutorial runs fully on managed storage (render as `AskUserQuestion`).

---

## Recap

- ✓ Catalog **`silverline`** — the shared home for all tracks (you own it)
- ✓ Schemas **`bronze` / `silver` / `gold`** (the medallion)
- ✓ Managed volume **`silverline.bronze.files`** (`/Volumes/silverline/bronze/files/`) — managed storage, no cloud setup
- ✓ Verified via `SHOW SCHEMAS` / `SHOW VOLUMES`
- ◻️ *(Optional)* External location + external table/volume on **your own cloud** — opt-in, real $, and reused by the `ingest` CDF step

**Cost now:** $0 — free UC objects + a few-second query (unless you opted into the external-storage section, which bills to your AWS).
