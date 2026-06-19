<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Data API — REST over Lakebase (the data-services layer)

Turn on the **Data API** to expose Silverline Capital's Lakebase tables over **REST** (PostgREST-compatible),
with zero backend code — the piece a cloud tutorial would stand up a FastAPI service for. An app, dashboard,
or agent can then read the operational data (customers, contracts, the overdue-invoice queue) over plain
HTTPS.

**Cost:** Quota only — the API rides the same serverless Postgres compute.

**Precondition:** `seed` done — the 9 Silverline tables exist in `silverline-oltp`.

> 🔑 **Key Free-Edition facts (verified live, docs lag):**
> - The Data API **is supported** on Free Edition's autoscaling Lakebase.
> - **Enabling it is UI-only** — there's no documented CLI/REST toggle. This is a deliberate exception to
>   "provision via CLI": a feature with no API yet.
> - **The database owner (you) can't be the API identity** — the `authenticator` role can't assume an
>   elevated role. The fix is a **service principal**, which **Free Edition *does* support** (despite older
>   notes saying otherwise) — and an SP is the production-recommended identity anyway.

---

## Section 1 — Enable the Data API (UI)

In the workspace: **Database** (Lakebase) → open the **`silverline-oltp`** project → **Data API** page (under
*App Backend*) → **Enable Data API**. This auto-creates the `authenticator` Postgres role and exposes the
`public` schema. On the **API** tab, copy the **API URL** — it looks like:

```
https://<endpoint-host>/api/2.0/workspace/<workspace-id>/rest/databricks_postgres
```

> You append the schema (`/public`) + table when querying (Section 4).

**Pause.** Confirm the Data API is enabled and you've copied the API URL (render as `AskUserQuestion`).

---

## Section 2 — Create the API identity: a service principal (CLI)

The Data API call must come from a **non-owner** identity. Claude creates a service principal + an OAuth
secret (M2M):

```bash
# create the SP
databricks --profile free service-principals create --display-name "silverline-data-api" -o json \
  | jq '{id, applicationId, displayName}'
# mint a workspace-level OAuth secret for it (capture .secret — shown once)
databricks --profile free service-principal-secrets-proxy create <sp-id> -o json | jq '{id, status}'
```

Store the SP's **client id** (`applicationId`) + **secret** in a **Databricks secret scope** (the
production home, and what the demo notebook reads) — and also in the gitignored `.env` for CLI use:

```bash
databricks --profile free secrets create-scope silverline
databricks --profile free secrets put-secret silverline data_api_sp_client_id --string-value "<APP_ID>"
databricks --profile free secrets put-secret silverline data_api_sp_secret    --string-value "<SECRET>"
```

**Pause.** Confirm the SP exists, an OAuth secret was minted, and both are in the `silverline` secret scope
(render as `AskUserQuestion`).

---

## Section 3 — Give the SP a Postgres role + grants (SQL, run as owner)

Run as the database **owner** (the owner mints its own token; the SP can't grant itself). `<APP_ID>` is the
SP's `applicationId`:

```sql
CREATE EXTENSION IF NOT EXISTS databricks_auth;                       -- once per database
SELECT databricks_create_role('<APP_ID>', 'SERVICE_PRINCIPAL');       -- Postgres role for the SP
GRANT "<APP_ID>" TO authenticator;                                    -- lets the API assume the SP (works: SP isn't elevated)
GRANT USAGE ON SCHEMA public TO "<APP_ID>";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "<APP_ID>";            -- add INSERT/UPDATE/DELETE for writes
```

> ⚠️ `GRANT "<owner-email>" TO authenticator` would fail (`permission denied to grant role`) — that's the
> elevated-owner restriction, and exactly why we use the SP.

**Pause.** Confirm the SP role exists and is granted to `authenticator` (render as `AskUserQuestion`).

---

## Section 4 — Query the Data API over HTTPS

**Notebook (primary):** run **`SilverAIWolf/06-data-api/06.1_data_api_demo`** — it reads the SP creds from
the `silverline` secret scope (`dbutils.secrets.get`), mints the M2M token, and queries the API with
`requests` (customers, overdue invoices, active loans > $250k, and a contracts↔customers embedded join),
displaying each as a table. That's how an app/agent would consume it.

**CLI equivalent:** mint a short-lived **M2M OAuth token** for the SP, then `curl` the endpoint. Append
`/public/<table>` to the API URL; filtering/sorting/pagination follow PostgREST conventions.

```bash
cd tutorials/databricks/end-to-end && set -a && . ./.env && set +a
HOST=https://<your-workspace>.cloud.databricks.com
API="<API-URL-from-Section-1>"

TOKEN=$(curl -s -X POST "$HOST/oidc/v1/token" \
  --user "$LAKEBASE_SP_CLIENT_ID:$LAKEBASE_SP_SECRET" \
  --data 'grant_type=client_credentials&scope=all-apis' | jq -r '.access_token')

# top 3 customers (select specific columns):
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/public/customers?limit=3&select=customer_id,legal_name,segment" | jq .

# overdue invoices (server-side filter):
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/public/invoices?status=eq.overdue&limit=5" | jq .

# active loan contracts over $250k (combined filters):
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/public/contracts?status=eq.active&contract_type=eq.loan&principal=gt.250000&limit=5" | jq .
```

Common operators: `eq` `neq` `gt` `gte` `lt` `lte` `like` `in`; also `select=`, `order=`, `limit/offset`.

> 🔒 **Production note:** the grants above are table-level. For real multi-user APIs, add **row-level
> security** (RLS) policies so each identity sees only its rows. See the Lakebase Data API RLS docs.

**Pause.** Confirm a REST `GET` returns JSON rows from a seeded table (render as `AskUserQuestion`).

---

## Section 5 — Why this matters

| Build it yourself | With the Lakebase Data API (here) |
|---|---|
| expose data via a **FastAPI** service you build + host | **enable once** → governed REST over your operational tables |
| manage compute, auth, pagination, filtering | rides serverless Postgres; OAuth + PostgREST filtering built-in |

An app, dashboard, or agent reads Silverline's operational data over plain HTTPS — no backend to write or
deploy. (The lakehouse phase next lands this same data into the lakehouse for analytics/AI; the Data API is
the *operational* read/write path.)

**Pause.** Confirm you can explain the Data API vs hand-building one (render as `AskUserQuestion`).

---

## Recap

- ✓ **Data API enabled** (UI) — REST over your Lakebase `public` schema, zero backend code
- ✓ **Service principal** created as the API identity (Free Edition supports SPs; the owner can't be the identity)
- ✓ SP **Postgres role + grants** (`databricks_create_role` → `GRANT … TO authenticator` → table grants)
- ✓ Live **M2M-OAuth REST queries** with PostgREST filters (customers, overdue invoices, active loans > $250k)

**Cost now:** quota only. **Phase B (Lakebase) complete** — stages 4–6 of 12 done.
