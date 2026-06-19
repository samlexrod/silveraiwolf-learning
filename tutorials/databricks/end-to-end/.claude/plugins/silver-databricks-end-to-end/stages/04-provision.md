<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Provision — a Lakebase Postgres **Autoscaling project (PG17)**

Create a Lakebase **Autoscaling project** running **PostgreSQL 17** and capture how to connect. Provisioning
is **always done via the `databricks` CLI** (production = automation, not click-ops); Claude runs it.

> 🔢 **Use the Autoscaling project API to get PG17 (verified).** There are two Lakebase APIs:
> - **`databricks postgres create-project`** → the **Autoscaling** model; takes `spec.pg_version` → **PG17**. ✅ use this.
> - ~~`databricks database create-database-instance`~~ → the older **Provisioned** model; **only gives PG16**
>   (no version flag; even an explicit `pg_version` in its JSON is ignored). ❌ avoid.
>
> PG17 matters: **Lakebase CDF** (the native managed CDC in `ingest`) requires it.

**Cost:** Quota only — serverless Postgres, autoscales/idles to ~0. No money.

**Precondition:** `setup/` done (CLI `free` profile + the local project).

---

## Section 1 — Create the PG17 Autoscaling project

```bash
databricks --profile free postgres create-project silverline-oltp \
  --json '{"spec":{"pg_version":17}}' --timeout 15m -o json | jq '{name, pg: .status.pg_version}'
# reuse later:
databricks --profile free postgres list-projects -o json | jq -r '.[].name'
```

> ⚠️ **Re-provisioning after a `cleanup`?** Lakebase **reserves a deleted project's slug** for a retention
> window, so `create-project silverline-oltp` may fail with **`slug already exists`** even though the project
> is gone. If so, provision under a fresh name (e.g. `silverline-oltp-2`) and use that name for the rest of the
> run — the later stages read the project name + host from `.env`, so update those accordingly.

You get a project with a **`production` branch** + a **primary** read-write endpoint and the default
database `databricks_postgres`.

> 🧠 **Project / branch / endpoint:** an Autoscaling project holds branches (git-like); the `production`
> branch has a **primary endpoint** (compute) that autoscales and idles to ~0 when unused.
> ⚠️ A project is **not** a "database instance" — manage it with the **`postgres`** CLI/API, not `database`.

**Pause.** Confirm `pg = 17` and the project is created (render as `AskUserQuestion`).

---

## Section 2 — Capture connection details (the `postgres` API)

The endpoint resource path is `projects/silverline-oltp/branches/production/endpoints/primary`. Claude reads
the host and writes the non-secret bits to `.env`:

```bash
EP=projects/silverline-oltp/branches/production/endpoints/primary
HOST=$(databricks --profile free postgres get-endpoint "$EP" -o json | jq -r '.status.hosts.host')
cd tutorials/databricks/end-to-end
cat >> .env <<EOF
LAKEBASE_HOST=$HOST
LAKEBASE_DB=databricks_postgres
LAKEBASE_USER=<your-databricks-email>
EOF
```

**Pause.** Confirm host / database / user are in `.env` (render as `AskUserQuestion`).

---

## Section 3 — Mint a credential + verify connectivity

Lakebase auth = a **short-lived OAuth token used as the Postgres password** (≈1h), minted via the
**`postgres`** API for the endpoint:

```bash
EP=projects/silverline-oltp/branches/production/endpoints/primary
TOKEN=$(databricks --profile free postgres generate-database-credential "$EP" -o json | jq -r '.token')
export PGPASSWORD="$TOKEN"
psql "host=$LAKEBASE_HOST port=5432 dbname=$LAKEBASE_DB user=$LAKEBASE_USER sslmode=require" \
  -tAc "SELECT version();"     # expect PostgreSQL 17.x over SSL
```

> In notebooks, the SDK equivalent is `w.postgres.get_endpoint(EP).status.hosts.host` +
> `w.postgres.generate_database_credential(EP).token` (the seed notebooks use this).

**Pause.** Confirm `SELECT version()` returns **PostgreSQL 17** over SSL (render as `AskUserQuestion`).

---

## Recap

- ✓ A serverless **Lakebase Autoscaling project** `silverline-oltp` on **PostgreSQL 17** (autoscaling, quota-cheap)
- ✓ Created with `postgres create-project … pg_version 17` (the `database` API only gives PG16)
- ✓ Connection details in `.env`; password = short-lived OAuth token via `postgres generate-database-credential`
- ✓ Verified `SELECT version()` → PostgreSQL 17 over SSL

**Cost now:** quota only (idles to ~0).
