"""Apply a deterministic, idempotent change-set to Lakebase — the cdc-sim lesson.

A fixed INSERT/UPDATE/DELETE on the Silverline Capital OLTP (customers + invoices) that converges to ONE
state (re-runnable). FK-safe. After running, re-ingest (re-run the bronze CTAS for the changed tables) +
re-run the medallion to watch it propagate bronze → silver → gold.

Connection: LAKEBASE_HOST / LAKEBASE_DB / LAKEBASE_USER (.env) + PGPASSWORD (minted token) — same as the seed.
Usage:  export PGPASSWORD="<token>" ;  mise run lakebase:simulate
"""

from __future__ import annotations

import os
import sys

try:
    import psycopg
except ImportError:
    print("✗ psycopg not installed — run `mise run setup`", file=sys.stderr)
    raise SystemExit(1)

# The deterministic change set (matches the assertions the cdc-sim stage checks):
DML = """
-- UPDATE: customer 1's revenue + invoice 1 (amount + status), and push contract 1 delinquent
UPDATE customers SET annual_revenue = 123456789.00 WHERE customer_id = 1;
UPDATE invoices  SET amount = 987654.00, status = 'overdue' WHERE invoice_id = 1;
UPDATE contracts SET status = 'delinquent' WHERE contract_id = 1;
-- INSERT: a new customer + a new invoice on contract 1 (idempotent)
INSERT INTO customers (customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date)
  VALUES (9001, 'Simulated Logistics Co', 'Logistics', 'West', 'BBB', 4242.00, DATE '2026-06-01')
  ON CONFLICT (customer_id) DO NOTHING;
INSERT INTO invoices (invoice_id, contract_id, schedule_id, invoice_date, due_date, amount, status)
  VALUES (900001, 1, NULL, DATE '2026-06-01', DATE '2026-07-01', 4242.00, 'open')
  ON CONFLICT (invoice_id) DO NOTHING;
-- DELETE: drop invoice 3 (idempotent) — remove its dependent payment first (FK payments.invoice_id)
DELETE FROM payments WHERE invoice_id = 3;
DELETE FROM invoices WHERE invoice_id = 3;
"""


def main() -> int:
    host = os.environ.get("LAKEBASE_HOST", "").strip()
    db = os.environ.get("LAKEBASE_DB", "databricks_postgres").strip()
    user = os.environ.get("LAKEBASE_USER", "").strip()
    pwd = os.environ.get("PGPASSWORD", "").strip()
    if not (host and user and pwd):
        print("✗ need LAKEBASE_HOST + LAKEBASE_USER (.env) and PGPASSWORD (minted token)", file=sys.stderr)
        return 1
    with psycopg.connect(host=host, port=5432, dbname=db, user=user, password=pwd, sslmode="require") as conn, \
            conn.cursor() as cur:
        cur.execute(DML)
        conn.commit()
        cur.execute("SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM invoices)")
        c, i = cur.fetchone()
    print(f"✓ simulated change-set applied — customers={c} invoices={i} "
          f"(customer 1 revenue=123456789.00; invoice 1 overdue/987654.00; contract 1 delinquent; "
          f"+customer 9001; +invoice 900001; -invoice 3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
