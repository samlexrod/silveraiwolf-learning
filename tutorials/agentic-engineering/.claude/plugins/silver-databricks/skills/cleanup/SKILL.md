---
description: "[Cleanup] Delete all Databricks pipelines, schemas, and workspace artifacts — reset to fresh state"
---

# Cleanup — Reset Tutorial Environment

Remove all Databricks resources created by the tutorial so you can start fresh from any stage.

This is a **destructive operation** — it deletes pipelines, schemas, tables, volumes, and workspace artifacts. Use `AskUserQuestion` to confirm before proceeding.

---

## Instructions

---

### Step 1 — Confirm Cleanup

Load the `.env` file and verify Databricks connectivity:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
databricks auth describe
```

If auth fails, tell the user to check their `.env` file and try `databricks auth login --host "$DATABRICKS_HOST"`.

Then use `AskUserQuestion` to confirm:

> This will delete **all** Databricks resources created by the tutorial:
> - All DLT pipelines (dev and prod)
> - All `financial_risk*` schemas and their tables (Bronze, Silver, Gold)
> - All volumes in those schemas (including uploaded seed data)
> - All bundle deployment artifacts in the workspace
>
> Your local project files will **not** be deleted.

Options:
- "Yes, clean everything" — proceed with full cleanup
- "Cancel" — abort

---

### Step 2 — Delete Pipelines

List and delete all pipelines:

```bash
export $(grep -v '^#' .env | xargs)
databricks pipelines list-pipelines -o json
```

For each pipeline found, delete it:

```bash
databricks pipelines delete <pipeline-id>
```

If no pipelines exist, report "No pipelines found — skipping."

Present what was deleted:

```
Pipelines:
  ✓ [dev samlexrod] Financial Risk Pipeline (abc123) — deleted
  ✓ Financial Risk Pipeline (def456) — deleted
```

Adapt to actual pipeline names and IDs.

---

### Step 3 — Drop Schemas

Find and drop all `financial_risk*` schemas (dev per-user schemas + prod schema):

```bash
export $(grep -v '^#' .env | xargs)
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
```

First, list matching schemas:

```bash
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"SHOW SCHEMAS IN main LIKE 'financial_risk%'\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

For each schema found, drop it with CASCADE (removes all tables, views, and volumes):

```bash
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"DROP SCHEMA IF EXISTS main.<schema_name> CASCADE\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

If no schemas match, report "No financial_risk* schemas found — skipping."

Present what was dropped:

```
Schemas:
  ✓ main.financial_risk — dropped (CASCADE)
  ✓ main.financial_risk_samlexrod — dropped (CASCADE)
```

Adapt to actual schema names found.

---

### Step 4 — Clean Workspace Artifacts

Delete bundle deployment artifacts from the workspace:

```bash
export $(grep -v '^#' .env | xargs)
```

Check both the user workspace (dev) and the shared pipelines path (prod):

```bash
# Dev artifacts (user workspace)
databricks workspace list /Workspace/Users/<user-email>/.bundle 2>/dev/null

# Prod artifacts (shared path)
databricks workspace list /Workspace/pipelines/financial-risk-pipeline 2>/dev/null
```

Extract the user email from the auth describe output or `.env`. Delete any found:

```bash
# Dev
databricks workspace delete /Workspace/Users/<user-email>/.bundle/financial-risk-pipeline --recursive 2>/dev/null

# Prod
databricks workspace delete /Workspace/pipelines/financial-risk-pipeline --recursive 2>/dev/null
```

Report what was cleaned:

```
Workspace:
  ✓ /Workspace/Users/samlexrod@gmail.com/.bundle/financial-risk-pipeline — deleted
  ✓ /Workspace/pipelines/financial-risk-pipeline — deleted
```

If nothing found, report "No workspace artifacts found — skipping."

---

### Step 5 — Verify & Report

Run a final verification:

```bash
export $(grep -v '^#' .env | xargs)
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Verify no pipelines
databricks pipelines list-pipelines -o json

# Verify no schemas
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"SHOW SCHEMAS IN main LIKE 'financial_risk%'\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

Present the final summary:

```
┌────────────────────────────────────────────────────┐
│  Cleanup Complete                                  │
├────────────────────────────────────────────────────┤
│  Pipelines           ✅  0 remaining               │
│  Schemas             ✅  No financial_risk* found   │
│  Workspace artifacts ✅  Removed                    │
├────────────────────────────────────────────────────┤
│  Local project files are untouched.                │
│                                                    │
│  To restart the tutorial:                          │
│    Stage 2: /silver-databricks:deploy-dev          │
│    Stage 1: /silver-databricks:scaffold-setup      │
│             (only if you want a fresh project)     │
└────────────────────────────────────────────────────┘
```

---

## Important

- **This does NOT delete local files** — only Databricks cloud resources. The scaffolded project, `.env`, seed data, and workflow files remain intact.
- **CASCADE drops everything** in a schema — tables, views, and volumes. There is no undo.
- **Volumes with seed data** (from Stage 2 deploy-dev) are inside the schema and will be dropped with CASCADE.
- If the SQL warehouse is stopped or unavailable, schema operations will fail. Tell the user to start the warehouse from the Databricks UI first.
