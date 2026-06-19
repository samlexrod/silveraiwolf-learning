# /silver-databricks-end-to-end:cleanup — tear down everything

Remove **all** resources this tutorial created and return the workspace to its fresh **$0** Free Edition
state. **Destructive + irreversible.** Keeps the shared Starter Warehouse (pre-existing). Does **not** touch
the learner's personal AWS account.

> The work is done by `scripts/cleanup.sh` (idempotent — safe to re-run). Claude runs it; the learner just
> confirms. Resource names default to the tutorial's conventions and can be overridden via env vars.

## What gets removed
- UC catalog `silverline` (CASCADE — bronze/silver/gold, all tables/views, the volume, `portfolio_metrics`, `customer_360`, `assess_credit_memo`)
- `silverline_cdf` (if the optional CDF step was run) + `lakebase_silverline_oltp` (the Lakebase UC catalog)
- Lakebase project `silverline-oltp` (the serverless Postgres — also drops the WAL slot + triggers)
- Service principal `silverline-data-api`, secret scope `silverline`
- SDP pipeline `silverline-medallion-sdp`, jobs `silverline-dbt-job` + `silverline-notebook-job`
- AI/BI dashboard + Genie space (matched by title)
- Workspace notebooks under `/Workspace/Users/<you>/SilverAIWolf/`
- **Kept:** the shared Starter Warehouse (never deleted)

## Run it (Claude performs this)
1. **Dry run first** — list what would be deleted, remove nothing:
   ```bash
   ./scripts/cleanup.sh --dry-run
   ```
2. Show the learner the list and **confirm via `AskUserQuestion`** — this is irreversible.
3. On confirm, run for real:
   ```bash
   ./scripts/cleanup.sh --yes
   ```
4. **Verify the $0 state** and surface the output:
   ```bash
   databricks --profile free catalogs list | grep -i silverline || echo "no silverline* catalogs ✓"
   databricks --profile free postgres list-projects -o json | grep -i silverline-oltp || echo "no lakebase project ✓"
   ```

## ⚠️ Re-provisioning gotcha — the Lakebase slug stays reserved
Deleting the Lakebase project **soft-deletes** it and **reserves its slug** (`silverline-oltp`) for a
retention window (observed several hours). So a `cleanup` → immediately re-run `provision` cycle **fails** at
provisioning with `slug already exists`, even though the project is gone. Two ways through it:
- **Wait** for the slug to free, or
- **Re-provision under a different name** — `databricks postgres create-project silverline-oltp-2 --json '{"spec":{"pg_version":17}}'` (set the matching name when you continue the tutorial; the seed/data-api/ingest stages read the project name + host from `.env`, so update those).

The cleanup script prints this reminder at the end too.

## ⚠️ Not removed — manual, and it costs real money
If the learner ran the **optional CDF / AWS-quickstart** step, the S3 bucket + IAM role live in **their own
AWS account** as a CloudFormation stack billed by AWS (not Databricks). The script can't touch AWS — tell the
learner to:
1. **Disable CDF** in the Lakebase UI (if still on), so the slot stops retaining WAL.
2. Delete the **CloudFormation stack** (+ S3 bucket) in their AWS console.

Local artifacts: `rm -rf .venv dbt/target dbt/logs` clears the Python venv + dbt build dirs.
