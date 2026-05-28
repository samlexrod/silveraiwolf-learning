---
description: "[Stage 5] Verify CDC events flow from Postgres -> Debezium -> Redpanda for all 7 topics"
---

# Verify CDC — Live Change Capture

Make changes in PostgreSQL and verify they appear as CDC events in Redpanda topics. This confirms the full CDC pipeline works for all 7 tables before connecting Databricks.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 2 (seed-postgres), the learner has:
- PostgreSQL with 7 tables and seed data across 3 domains
- Debezium connector running and capturing WAL for all 7 tables
- Redpanda with 7 topics containing initial snapshot data

---

## Instructions

---

### Step 1 — Set Up a Topic Consumer

Open a consumer on one topic to watch events arrive in real time:

```bash
# In a separate terminal (or tmux pane), consume from the counterparties topic
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.counterparties --format '%v\n---\n'
"
```

This will show all existing snapshot events, then wait for new ones. Leave this running.

**Tip:** You can also browse topics visually in the **Redpanda Console**. Present the resolved URL as a clickable link: `http://<actual-ip>:8080/topics` (substitute `$EC2_PUBLIC_IP` from `.env`). Click any topic to see messages, partitions, and consumer groups in real time.

Use `AskUserQuestion` to confirm the consumer is running and showing events.

---

### Step 2 — Test INSERT

Insert a new counterparty in Postgres and watch it appear in the topic:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO counterparties (counterparty_id, name, sector, country, credit_rating,
    total_assets, total_liabilities, equity, revenue, net_income,
    interest_expense, current_assets, current_liabilities, inventory)
  VALUES ('CP_TEST', 'CDC Test Corp', 'TECHNOLOGY', 'US', 'BBB',
    1000000, 500000, 500000, 200000, 50000,
    10000, 400000, 200000, 50000);
"
```

The consumer should show a new event with:
- `"op": "c"` — create (INSERT)
- `"before": null` — no previous state
- `"after": { "counterparty_id": "CP_TEST", "name": "CDC Test Corp", ... }`

Explain the difference: `"op": "r"` (snapshot read) vs `"op": "c"` (live INSERT).

---

### Step 3 — Test UPDATE

Update the test row and observe the event:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  UPDATE counterparties SET credit_rating = 'A', total_assets = 1500000
  WHERE counterparty_id = 'CP_TEST';
"
```

The consumer should show:
- `"op": "u"` — update
- `"before": { ..., "credit_rating": "BBB", "total_assets": 1000000, ... }` — old values
- `"after": { ..., "credit_rating": "A", "total_assets": 1500000, ... }` — new values

**Key insight:** Because we set `REPLICA IDENTITY FULL`, the `before` field contains the complete old row. Without it, `before` would only contain the primary key — making it impossible to know what changed.

---

### Step 4 — Test DELETE

Delete the test row:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  DELETE FROM counterparties WHERE counterparty_id = 'CP_TEST';
"
```

The consumer should show:
- `"op": "d"` — delete
- `"before": { "counterparty_id": "CP_TEST", ... }` — the deleted row
- `"after": null` — no new state

Followed by a **tombstone event** (key = CP_TEST, value = null) — this is Kafka's way of signaling downstream consumers that this key has been deleted. Important for compacted topics.

---

### Step 5 — Test Transactions Topic

Verify CDC works for the transactions table (higher volume):

```bash
# Insert a test transaction
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO transactions (transaction_id, counterparty_id, direction, instrument_id,
    instrument_type, amount, currency, transaction_date, quantity)
  VALUES ('TXN_TEST', 'CP001', 'BUY', 'AAPL', 'EQUITY', 150000.00, 'USD', CURRENT_DATE, 100);
"

# Consume one message from the transactions topic
ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.transactions --num 1 --offset end --format '%v\n'
" | python3 -m json.tool
```

Clean up:
```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  DELETE FROM transactions WHERE transaction_id = 'TXN_TEST';
"
```

---

### Step 6 — Test New Domain Topics

Verify CDC works for the 4 new tables added in this version:

#### 6a — Credit Ratings History

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO credit_ratings_history (rating_id, counterparty_id, rating_agency, rating, outlook, effective_date)
  VALUES ('CR_TEST', 'CP001', 'S&P', 'A+', 'STABLE', CURRENT_DATE);
"

ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.credit_ratings_history --num 1 --offset end --format '%v\n'
" | python3 -m json.tool
```

#### 6b — Office Locations

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO office_locations (office_id, city, country, region, timezone, capacity)
  VALUES ('OFF_TEST', 'Tokyo', 'JP', 'APAC', 'Asia/Tokyo', 200);
"

ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.office_locations --num 1 --offset end --format '%v\n'
" | python3 -m json.tool
```

#### 6c — Trading Desks

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO trading_desks (desk_id, desk_name, office_id, asset_class, head_trader)
  VALUES ('DSK_TEST', 'Test FX Desk', 'OFF_TEST', 'FX', 'Jane Doe');
"

ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.trading_desks --num 1 --offset end --format '%v\n'
" | python3 -m json.tool
```

#### 6d — Desk Assignments

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO desk_assignments (assignment_id, desk_id, counterparty_id, assigned_date, role)
  VALUES ('ASGN_TEST', 'DSK_TEST', 'CP001', CURRENT_DATE, 'PRIMARY');
"

ssh -i <key_path> ec2-user@$EC2_PUBLIC_IP "
  docker exec redpanda rpk topic consume postgres.public.desk_assignments --num 1 --offset end --format '%v\n'
" | python3 -m json.tool
```

Clean up all test data:

```bash
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "
  DELETE FROM desk_assignments WHERE assignment_id = 'ASGN_TEST';
  DELETE FROM trading_desks WHERE desk_id = 'DSK_TEST';
  DELETE FROM office_locations WHERE office_id = 'OFF_TEST';
  DELETE FROM credit_ratings_history WHERE rating_id = 'CR_TEST';
"
```

Use `AskUserQuestion` to confirm all 4 new topics are receiving events.

---

### Step 7 — Understand CDC Event Flow Timing

Present the end-to-end latency breakdown:

```
  Postgres COMMIT          Debezium reads WAL        Event in Redpanda topic
       │                         │                          │
       ├── ~10ms ───────────────>├── ~50ms ────────────────>│
       │   (WAL flush)           │   (parse + serialize)    │
       │                         │                          │
       └────────── ~60-100ms total ────────────────────────>│
```

**Key point:** CDC latency is typically under 100ms from commit to topic. Databricks streaming will add its own micro-batch interval on top of this (configurable, default ~10-30 seconds for Spark Structured Streaming in DLT).

---

### Step 8 — Summary

| Test | Operation | Debezium `op` | Result |
|------|-----------|---------------|--------|
| INSERT | Create new row | `c` | `before: null`, `after: {new row}` |
| UPDATE | Modify existing row | `u` | `before: {old row}`, `after: {new row}` |
| DELETE | Remove row | `d` | `before: {deleted row}`, `after: null` |
| Snapshot | Initial data load | `r` | `before: null`, `after: {existing row}` |

All 7 topics verified:

| Topic | Domain | Verified |
|-------|--------|----------|
| `postgres.public.counterparties` | Counterparty | Snapshot + INSERT/UPDATE/DELETE |
| `postgres.public.credit_ratings_history` | Counterparty | Snapshot + INSERT |
| `postgres.public.transactions` | Financial | Snapshot + INSERT |
| `postgres.public.market_prices` | Financial | Snapshot |
| `postgres.public.office_locations` | Operations | Snapshot + INSERT |
| `postgres.public.trading_desks` | Operations | Snapshot + INSERT |
| `postgres.public.desk_assignments` | Operations | Snapshot + INSERT |

The CDC pipeline is verified end-to-end:
- PostgreSQL WAL captures every change across all 7 tables
- Debezium reads the WAL and produces JSON events
- Redpanda stores events in per-table topics
- Events contain full before/after images for all operation types

**Browse visually:** Present the Redpanda Console URL as a clickable link: `http://<actual-ip>:8080/topics` (substitute `$EC2_PUBLIC_IP` from `.env`). Inspect messages, partitions, and consumer lag for all 7 topics.

**Next:** Run `/silver-databricks-streaming:stream-bronze` to connect Databricks to these topics with `readStream("kafka")` and deploy Auto Loader Bronze tables.
