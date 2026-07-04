# 🐺 Silverline Lakehouse Explorer

A visual companion to the **Databricks end-to-end** tutorial. Instead of *reading* what each phase does,
you **see** it: query the Silverline OLTP data and watch live changes stream in. Built on
**React + Vite + Apollo GraphQL**, with **Lakebase (Postgres 17)** as the data source.

> **Iteration 1 (skeleton):** two views — *Get data* (GraphQL queries) and *Streaming* (GraphQL
> subscriptions over Postgres `LISTEN/NOTIFY`). Later iterations add the medallion flow, the
> refresh→lineage animation, and the gold metric charts.

```
client/  React + Vite + TS + Apollo Client (split HTTP/WS link)
server/  Apollo Server 4 + Express + ws + pg → Lakebase
```

## How it works

- **Get data** → GraphQL **queries** → `pg` SELECTs over `customers` / `contracts` / `invoices`.
- **Streaming** → a DB **trigger** `pg_notify()`s every change onto `silverline_changes`; the server
  `LISTEN`s and pushes each event to a GraphQL **subscription**; the client renders a live feed.
- **Auth** → the Lakebase password is a short-lived (~1h) OAuth token the server **mints on demand** via
  the Databricks CLI (`free` profile) — no secret in `.env`. (Prod: swap for the service-principal M2M flow.)

## Prerequisites

- Node 18+ and the **`silver-databricks-end-to-end`** tutorial run through at least the **seed** stage
  (so the 9 Silverline tables exist in Lakebase) with the Databricks CLI authenticated as the `free` profile.

## Run it

```bash
# 1) server
cd server
cp .env.example .env          # fill LAKEBASE_HOST / USER from the tutorial's .env
npm install
npm run setup:notify          # one-time: install the LISTEN/NOTIFY triggers
npm run dev                   # http://localhost:4000/graphql

# 2) client (new terminal)
cd client
npm install
npm run dev                   # http://localhost:5173
```

Then open the client, switch to **Streaming**, and from the tutorial dir run
`mise run lakebase:simulate` — the INSERT/UPDATE/DELETE rows appear in the live feed instantly.

## Run with Docker (any machine)

The container can't use your local Databricks CLI, so it authenticates **headlessly** with the
**service principal** from the tutorial's `data-api` stage (`client_credentials` → token used as the
Postgres password; the SP connects directly to Lakebase — verified). No user login, no CLI in the image.

```bash
# 1) one-time on a machine WITH the Databricks CLI: install the LISTEN/NOTIFY triggers
cd server && cp .env.example .env   # fill LAKEBASE_HOST / USER / DATABRICKS_HOST / SP_CLIENT_ID
npm install && npm run setup:notify

# 2) add the SP secret to server/.env (enables headless/SP mode)
SP_SECRET=$(databricks --profile free secrets get-secret silverline data_api_sp_secret -o json \
  | python -c "import sys,json,base64;print(base64.b64decode(json.load(sys.stdin)['value']).decode())")
echo "SP_SECRET=$SP_SECRET" >> server/.env

# 3) build + run both containers
docker compose up --build        # server :4000, client :8080
```

Open **http://localhost:8080**. The server auto-detects SP mode when `SP_CLIENT_ID` + `SP_SECRET` are set
(falls back to CLI minting otherwise). Requires **Docker Desktop**.

