---
description: "[Stage 4] Create ALL 7 tables, insert seed data into PostgreSQL, and register Debezium connectors"
---

# Seed PostgreSQL — Tables, Data, and CDC Connectors

Create the source tables in PostgreSQL, insert seed data, and register Debezium connectors to start capturing changes. This stage now covers all 7 tables across 3 domains (financial, counterparty, operations).

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 3 (infra-cdc), the learner has:
- EC2 running with Postgres, Debezium, and Redpanda
- Unity Catalog schema and landing zone created (Stage 2)
- Connection config in `.env`
- No tables or data yet

---

## Instructions

---

### Step 1 — Verify Infrastructure is Running

Load `.env` and confirm all services are up:

```bash
source .env
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && docker compose ps"
```

All 4 containers should show `running` (postgres, redpanda, redpanda-console, debezium). If not, troubleshoot before continuing.

---

### Step 2 — Explain the Source Schema

Present the PostgreSQL schema across all 3 domains. Show tables grouped by domain, then list relationships separately below for clarity:

Present the tables as three separate lists by domain, not as an ASCII diagram. Use markdown tables:

**Financial Domain (2 tables):**

| Column | Type | Key |
|--------|------|-----|
| **transactions** | | |
| transaction_id | VARCHAR | PK |
| counterparty_id | VARCHAR | FK → counterparties |
| direction | VARCHAR | |
| instrument_id | VARCHAR | |
| instrument_type | VARCHAR | |
| amount | DECIMAL | |
| currency | VARCHAR | |
| transaction_date | DATE | |
| quantity | INTEGER | |
| updated_at | TIMESTAMP | |
| **market_prices** | | |
| instrument_id | VARCHAR | PK |
| trade_date | DATE | PK |
| instrument_type | VARCHAR | |
| open_price | DECIMAL | |
| high_price | DECIMAL | |
| low_price | DECIMAL | |
| close_price | DECIMAL | |
| volume | INTEGER | |
| currency | VARCHAR | |
| updated_at | TIMESTAMP | |

**Counterparty Domain (2 tables):**

| Column | Type | Key |
|--------|------|-----|
| **counterparties** | | |
| counterparty_id | VARCHAR | PK |
| name | VARCHAR | |
| sector | VARCHAR | |
| country | VARCHAR | |
| credit_rating | VARCHAR | |
| total_assets | DECIMAL | |
| total_liabilities | DECIMAL | |
| equity | DECIMAL | |
| revenue | DECIMAL | |
| net_income | DECIMAL | |
| interest_expense | DECIMAL | |
| current_assets | DECIMAL | |
| current_liabilities | DECIMAL | |
| inventory | DECIMAL | |
| updated_at | TIMESTAMP | |
| **credit_ratings_history** | | |
| rating_id | VARCHAR | PK |
| counterparty_id | VARCHAR | FK → counterparties |
| rating_agency | VARCHAR | |
| rating | VARCHAR | |
| outlook | VARCHAR | |
| effective_date | DATE | |
| previous_rating | VARCHAR | |
| updated_at | TIMESTAMP | |

**Operations Domain (3 tables):**

| Column | Type | Key |
|--------|------|-----|
| **office_locations** | | |
| office_id | VARCHAR | PK |
| city | VARCHAR | |
| country | VARCHAR | |
| region | VARCHAR | |
| timezone | VARCHAR | |
| capacity | INTEGER | |
| updated_at | TIMESTAMP | |
| **trading_desks** | | |
| desk_id | VARCHAR | PK |
| desk_name | VARCHAR | |
| office_id | VARCHAR | FK → office_locations |
| asset_class | VARCHAR | |
| head_trader | VARCHAR | |
| updated_at | TIMESTAMP | |
| **desk_assignments** | | |
| assignment_id | VARCHAR | PK |
| desk_id | VARCHAR | FK → trading_desks |
| counterparty_id | VARCHAR | FK → counterparties |
| assigned_date | DATE | |
| role | VARCHAR | |
| updated_at | TIMESTAMP | |

**Cross-domain relationships (5 foreign keys):**

| From | → To |
|------|------|
| transactions.counterparty_id | → counterparties.counterparty_id |
| credit_ratings_history.counterparty_id | → counterparties.counterparty_id |
| trading_desks.office_id | → office_locations.office_id |
| desk_assignments.desk_id | → trading_desks.desk_id |
| desk_assignments.counterparty_id | → counterparties.counterparty_id |

**Key points:**
- `updated_at` timestamps on all 7 tables enable Debezium to track changes
- The WAL (Write-Ahead Log) captures every operation regardless, but `updated_at` is useful for downstream deduplication
- Foreign keys connect tables across domains (e.g., `desk_assignments` references both `trading_desks` and `counterparties`)

Use `AskUserQuestion` to confirm understanding before creating tables.

---

### Step 3 — Create Tables

Run the DDL against PostgreSQL on the EC2:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f data/seed.sql
```

The `seed.sql` file:
1. Creates all 7 tables with proper types and constraints
2. Sets `REPLICA IDENTITY FULL` on each table (required for Debezium to capture UPDATE/DELETE with full row data)
3. Inserts seed data across all domains

After running, verify:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  SELECT 'counterparties' AS table_name, COUNT(*) FROM counterparties
  UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
  UNION ALL SELECT 'market_prices', COUNT(*) FROM market_prices
  UNION ALL SELECT 'credit_ratings_history', COUNT(*) FROM credit_ratings_history
  UNION ALL SELECT 'office_locations', COUNT(*) FROM office_locations
  UNION ALL SELECT 'trading_desks', COUNT(*) FROM trading_desks
  UNION ALL SELECT 'desk_assignments', COUNT(*) FROM desk_assignments;
"
```

Present results as a table:

| Domain | Table | Row Count |
|--------|-------|-----------|
| Financial | transactions | ~900 |
| Financial | market_prices | ~3,200 |
| Counterparty | counterparties | ~20 |
| Counterparty | credit_ratings_history | ~60 |
| Operations | office_locations | ~8 |
| Operations | trading_desks | ~12 |
| Operations | desk_assignments | ~30 |

---

### Step 4 — Explain Debezium CDC

Before registering connectors, explain what Debezium does:

```
  PostgreSQL WAL                    Debezium                         Redpanda Topics
 ┌─────────────────┐          ┌──────────────────┐          ┌──────────────────────────┐
 │ INSERT INTO     │          │ Reads WAL stream │          │ postgres.public.         │
 │  counterparties │─────────>│ Converts to JSON │─────────>│   counterparties         │
 │  VALUES (...)   │          │ event envelope   │          │ postgres.public.         │
 ├─────────────────┤          │                  │─────────>│   transactions           │
 │ UPDATE trades   │─────────>│ Tracks LSN       │          │ postgres.public.         │
 │  SET amount=... │          │ (Log Sequence #) │─────────>│   market_prices          │
 ├─────────────────┤          │                  │          │ postgres.public.         │
 │ DELETE FROM     │─────────>│ Emits before +   │─────────>│   credit_ratings_history │
 │  market_prices  │          │ after images     │          │ postgres.public.         │
 └─────────────────┘          │                  │─────────>│   office_locations       │
                              │ 7 tables tracked │          │ postgres.public.         │
                              └──────────────────┘─────────>│   trading_desks          │
                                                            │ postgres.public.         │
                                                   ────────>│   desk_assignments       │
                                                            └──────────────────────────┘
```

**Key concepts:**
- **WAL (Write-Ahead Log):** Postgres writes every change to the WAL before applying it. Debezium reads this log — zero impact on the application
- **LSN (Log Sequence Number):** Debezium tracks its position in the WAL. If it restarts, it resumes from the last LSN — no data loss, no duplicates
- **Event envelope:** Each CDC event contains `before` (old row), `after` (new row), `op` (c=create, u=update, d=delete), and metadata (timestamp, LSN, table)
- **Topic naming:** Debezium creates topics as `<server_name>.<schema>.<table>` — one topic per table (7 topics total)

Use `AskUserQuestion` to confirm understanding.

---

### Step 5 — Register Debezium Connectors

Register the PostgreSQL source connector via Debezium's REST API.

**First, check if the connector already exists** (it may exist from cloud-init or a previous tutorial run). If it does (HTTP 200), delete it and re-register to trigger a fresh snapshot of the newly seeded data:

```bash
# Check if connector exists (200 = exists, 404 = not found)
curl -s -o /dev/null -w "%{http_code}" http://$EC2_PUBLIC_IP:8083/connectors/financial-risk-source

# If 200: delete it first to get a clean snapshot
curl -X DELETE http://$EC2_PUBLIC_IP:8083/connectors/financial-risk-source
# Wait a few seconds for cleanup
sleep 5

# Register the connector
curl -X POST http://$EC2_PUBLIC_IP:8083/connectors \
  -H "Content-Type: application/json" \
  -d @infra/debezium-connector.json
```

Walk through the connector config:

```json
{
  "name": "financial-risk-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "financial_risk",
    "topic.prefix": "postgres",
    "table.include.list": "public.counterparties,public.transactions,public.market_prices,public.credit_ratings_history,public.office_locations,public.trading_desks,public.desk_assignments",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "dbz_publication",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": false,
    "value.converter.schemas.enable": false
  }
}
```

**Key change from before:** The `table.include.list` now includes all 7 tables across 3 domains.

Verify connector is running:

```bash
# Check connector status
curl -s http://$EC2_PUBLIC_IP:8083/connectors/financial-risk-source/status | python3 -m json.tool
```

Expected: `"state": "RUNNING"` for both the connector and its task.

---

### Step 6 — Verify Topics Created

Debezium should have created 7 topics in Redpanda (one per table):

```bash
# List topics via Redpanda's admin API or rpk
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "docker exec redpanda rpk topic list"
```

Expected topics:

| Topic | Source Table | Domain |
|-------|-------------|--------|
| `postgres.public.counterparties` | counterparties | Counterparty |
| `postgres.public.credit_ratings_history` | credit_ratings_history | Counterparty |
| `postgres.public.transactions` | transactions | Financial |
| `postgres.public.market_prices` | market_prices | Financial |
| `postgres.public.office_locations` | office_locations | Operations |
| `postgres.public.trading_desks` | trading_desks | Operations |
| `postgres.public.desk_assignments` | desk_assignments | Operations |

If topics are missing, check Debezium logs:
```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "cd ~/cdc-stack && docker compose logs debezium --tail 30"
```

---

### Step 7 — Verify Initial Snapshot

When Debezium first connects, it performs an **initial snapshot** — reading all existing rows and publishing them as INSERT events. This ensures the streaming pipeline starts with complete data.

Check message counts per topic:

```bash
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.counterparties --num 1 --format json | python3 -m json.tool
"
```

Show one sample CDC event and explain the envelope:

```json
{
  "before": null,
  "after": {
    "counterparty_id": "CP001",
    "name": "Meridian Capital Partners",
    "sector": "FINANCIALS",
    "credit_rating": "AA",
    ...
  },
  "source": {
    "version": "2.x",
    "connector": "postgresql",
    "db": "financial_risk",
    "schema": "public",
    "table": "counterparties",
    "lsn": 12345678,
    "txId": 100
  },
  "op": "r",
  "ts_ms": 1234567890
}
```

**Note:** `"op": "r"` means "read" — this is a snapshot event, not a live change. Live INSERTs will have `"op": "c"`.

Quick-check the new topics as well:

```bash
# Verify credit_ratings_history has snapshot data
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.credit_ratings_history --num 1 --format json | python3 -m json.tool
"

# Verify operations tables
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.office_locations --num 1 --format json | python3 -m json.tool
"
```

---

### Step 8 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| PostgreSQL tables | Created | 7 tables across 3 domains with REPLICA IDENTITY FULL |
| Seed data (financial) | Loaded | ~900 transactions, ~3,200 market prices |
| Seed data (counterparty) | Loaded | ~20 counterparties, ~60 credit ratings |
| Seed data (operations) | Loaded | ~8 offices, ~12 desks, ~30 assignments |
| Debezium connector | Running | Capturing WAL changes from all 7 tables |
| Redpanda topics | Created | 7 topics with initial snapshot data |
| Initial snapshot | Complete | All existing rows published as read events |

**Next:** Run `/silver-databricks-streaming:verify-cdc` to verify live CDC by making changes in Postgres and watching them appear in topics.
