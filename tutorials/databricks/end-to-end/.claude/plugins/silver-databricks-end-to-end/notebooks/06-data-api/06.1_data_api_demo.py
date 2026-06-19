# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 6 — Query the Lakebase Data API
# MAGIC
# MAGIC The **Data API** is a PostgREST-compatible REST surface over Silverline's Lakebase `public` schema —
# MAGIC zero backend code. This notebook calls it from Python the way an **app or agent** would: read the
# MAGIC service-principal credentials from a **Databricks secret scope**, mint an **M2M OAuth token**, and
# MAGIC `GET` rows with PostgREST filters.
# MAGIC
# MAGIC > 🔑 **Why a service principal?** The Data API can't be called as the database *owner* (the
# MAGIC > `authenticator` role can't assume an elevated identity). The SP `silverline-data-api` is the
# MAGIC > non-owner identity; its OAuth secret lives in the secret scope `silverline` (set up via CLI in the
# MAGIC > provisioning step — never hard-coded here).
# MAGIC >
# MAGIC > **Prereqs (done for you):** Data API enabled (UI), SP created + granted a Postgres role on `public`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Config: **derive** the Data API URL + read the SP credentials
# MAGIC Nothing to paste. The Data API URL is just three pieces your workspace already knows —
# MAGIC **endpoint host · workspace id · database** — so we assemble it from the SDK:
# MAGIC
# MAGIC ```
# MAGIC https://{endpoint-host}/api/2.0/workspace/{workspace-id}/rest/databricks_postgres
# MAGIC         └ w.postgres.get_endpoint(...)   └ w.get_workspace_id()   └ the default Lakebase db
# MAGIC ```
# MAGIC
# MAGIC > 💡 **Why derive, not paste?** The endpoint host **changes every time you re-provision Lakebase**
# MAGIC > (e.g. `ep-round-violet…` → `ep-aged-rain…`). A hardcoded URL silently rots; a derived one is always
# MAGIC > current. It's the same URL shown on your project's **Data API** page — check there if you're curious.
# MAGIC >
# MAGIC > The SP **client id / secret** still come from the `silverline` secret scope — never shown in output.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()

# Assemble the Data API base URL — re-provision-proof, no paste. Append /public/<table> to query.
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host    # ← changes on re-provision; always current here
WORKSPACE_ID = w.get_workspace_id()
API_URL = f"https://{HOST}/api/2.0/workspace/{WORKSPACE_ID}/rest/databricks_postgres"

SCOPE = "silverline"
CLIENT_ID = dbutils.secrets.get(SCOPE, "data_api_sp_client_id")
CLIENT_SECRET = dbutils.secrets.get(SCOPE, "data_api_sp_secret")

# Workspace host (for the OAuth token endpoint) — derived from the notebook context.
WORKSPACE_HOST = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
print("API_URL:", API_URL)
print("workspace:", WORKSPACE_HOST)
print("client id loaded:", bool(CLIENT_ID), "· secret loaded:", bool(CLIENT_SECRET))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Mint an M2M OAuth token for the service principal
# MAGIC `client_credentials` grant against the workspace OIDC token endpoint.

# COMMAND ----------

import requests

resp = requests.post(
    f"{WORKSPACE_HOST}/oidc/v1/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    data={"grant_type": "client_credentials", "scope": "all-apis"},
    timeout=30,
)
resp.raise_for_status()
TOKEN = resp.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("token minted:", bool(TOKEN))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Query the Data API (PostgREST over HTTPS)
# MAGIC A small helper returns rows as a DataFrame. Note the `/public/<table>` path + PostgREST filters
# MAGIC (`eq`, `gt`, `select`, `order`, `limit`).

# COMMAND ----------

import pandas as pd


def api_get(path: str) -> pd.DataFrame:
    r = requests.get(f"{API_URL}/public/{path}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())


# Top customers
display(api_get("customers?select=customer_id,legal_name,segment,credit_rating&limit=10"))

# COMMAND ----------

# Overdue invoices — server-side filter
display(api_get("invoices?status=eq.overdue&select=invoice_id,contract_id,amount,due_date&order=amount.desc&limit=10"))

# COMMAND ----------

# Active loan contracts over $250k — combined filters
display(api_get("contracts?status=eq.active&contract_type=eq.loan&principal=gt.250000"
                "&select=contract_id,customer_id,principal,apr,term_months&order=principal.desc&limit=10"))

# COMMAND ----------

# Embedded relationship (PostgREST resource embedding): contracts with their customer
display(api_get("contracts?select=contract_id,principal,customers(legal_name,segment)&limit=10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ You've read Silverline's operational data over plain HTTPS — no backend to build or host, governed
# MAGIC by the SP's Postgres grants. This is the **operational read/write path**; the **Lakehouse** phase
# MAGIC (next) lands this same data into Unity Catalog for analytics + AI.
# MAGIC
# MAGIC > 🔒 Production: add **row-level security** policies so each identity sees only its rows, and scope the
# MAGIC > SP's grants to least privilege.

# COMMAND ----------

# MAGIC %md
# MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
