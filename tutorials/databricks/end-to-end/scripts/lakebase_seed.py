"""Seed the Lakebase (Postgres 17) OLTP with the Silverline Capital application model.

Silverline Capital is a *fictional* equipment lease & loan finance company. This script stands up its
full operational schema in Lakebase and loads a deterministic dataset (same MOCK_SEED → identical rows
every run, so re-running is idempotent). Connects via psycopg.

The application model (9 tables, full origination → booking → billing → payments lifecycle):
  customers ── applications ──> contracts ──< contract_assets >── equipment ──> vendors
                                   │                                              ▲
                                   ├──< payment_schedule                          │
                                   └──< invoices ──< payments       equipment.vendor_id ┘

Connection (from `.env` via mise + a minted credential):
  LAKEBASE_HOST, LAKEBASE_DB (default databricks_postgres), LAKEBASE_USER (your email)
  PGPASSWORD = the short-lived Lakebase OAuth token (mint it: Connect dialog, or
               `databricks --profile free database generate-database-credential ...`)

Usage:  export PGPASSWORD="<token>" ;  mise run lakebase:seed
"""

from __future__ import annotations

import os
import sys
from datetime import date
from random import Random

try:
    import psycopg
except ImportError:
    print("✗ psycopg not installed — run `mise run setup` (adds psycopg[binary])", file=sys.stderr)
    raise SystemExit(1)

MOCK_SEED = 42
SNAPSHOT = date(2026, 6, 1)        # "today" for the billing run — invoices exist for elapsed periods only
N_CUSTOMERS = 60
N_VENDORS = 15
N_EQUIPMENT = 220
N_APPLICATIONS = 140

SEGMENTS = ["Manufacturing", "Logistics", "Retail", "Construction", "Agriculture", "Healthcare"]
REGIONS = ["North", "South", "East", "West", "Central"]
RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B"]          # weighted toward the middle below
SUFFIXES = ["LLC", "Inc", "Corp", "Group", "Partners", "Co"]
SURNAMES = ["Campos", "Lynch", "Martinez", "Whitfield", "Hartford", "Rodriguez", "Zuniga",
            "Valencia", "Nielsen", "Hernandez", "Farmer", "Wong", "Delacroix", "Baker", "Okafor"]
VENDOR_NAMES = ["Apex", "Summit", "Ironclad", "Vanguard", "Northgate", "Redwood", "Pioneer",
                "Cornerstone", "Bluepeak", "Granite", "Sierra", "Meridian", "Coastal", "Frontier", "Titan"]
VENDOR_TYPES = ["Dealer", "Manufacturer", "Broker"]
CATEGORIES = ["Forklift", "Excavator", "Diesel Generator", "Air Compressor", "Wheel Loader",
              "Bulldozer", "Reach Truck", "CNC Machine"]
MAKES = ["Caterpillar", "Komatsu", "Toyota", "John Deere", "Hyster", "Bobcat", "Volvo", "Doosan"]
PAY_METHODS = ["ACH", "Wire", "Check", "Card"]
TERMS = [12, 24, 36, 48, 60]

DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id    INT PRIMARY KEY,
    legal_name     TEXT NOT NULL,
    segment        TEXT,
    region         TEXT,
    credit_rating  TEXT,
    annual_revenue NUMERIC(14,2),
    onboarded_date DATE,
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id    INT PRIMARY KEY,
    name         TEXT NOT NULL,
    vendor_type  TEXT,
    region       TEXT,
    updated_at   TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id    INT PRIMARY KEY,
    vendor_id       INT REFERENCES vendors(vendor_id),
    category        TEXT,
    make            TEXT,
    model           TEXT,
    serial_number   TEXT,
    cost            NUMERIC(14,2),
    residual_value  NUMERIC(14,2),
    in_service_date DATE,
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS applications (
    application_id   INT PRIMARY KEY,
    customer_id      INT REFERENCES customers(customer_id),
    vendor_id        INT REFERENCES vendors(vendor_id),
    amount_requested NUMERIC(14,2),
    status           TEXT,                 -- submitted | approved | declined | booked
    submitted_date   DATE,
    decision_date    DATE,
    updated_at       TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS contracts (
    contract_id     INT PRIMARY KEY,
    application_id  INT REFERENCES applications(application_id),
    customer_id     INT REFERENCES customers(customer_id),
    contract_type   TEXT,                  -- lease | loan
    status          TEXT,                  -- active | paid_off | delinquent | charged_off
    principal       NUMERIC(14,2),
    apr             NUMERIC(6,4),
    term_months     INT,
    start_date      DATE,
    end_date        DATE,
    residual_value  NUMERIC(14,2),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS contract_assets (
    contract_id    INT REFERENCES contracts(contract_id),
    equipment_id   INT REFERENCES equipment(equipment_id),
    allocated_cost NUMERIC(14,2),
    PRIMARY KEY (contract_id, equipment_id)
);
CREATE TABLE IF NOT EXISTS payment_schedule (
    schedule_id    INT PRIMARY KEY,
    contract_id    INT REFERENCES contracts(contract_id),
    period_no      INT,
    due_date       DATE,
    principal_due  NUMERIC(12,2),
    interest_due   NUMERIC(12,2),
    total_due      NUMERIC(12,2)
);
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id    INT PRIMARY KEY,
    contract_id   INT REFERENCES contracts(contract_id),
    schedule_id   INT REFERENCES payment_schedule(schedule_id),
    invoice_date  DATE,
    due_date      DATE,
    amount        NUMERIC(12,2),
    status        TEXT,                    -- open | paid | overdue
    updated_at    TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id   INT PRIMARY KEY,
    invoice_id   INT REFERENCES invoices(invoice_id),
    paid_date    DATE,
    amount       NUMERIC(12,2),
    method       TEXT,
    updated_at   TIMESTAMPTZ DEFAULT now()
);
"""

TRUNCATE = """TRUNCATE payments, invoices, payment_schedule, contract_assets, contracts,
                       applications, equipment, vendors, customers RESTART IDENTITY CASCADE;"""


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    return date(y, m % 12 + 1, min(d.day, 28))


def _conn():
    host = os.environ.get("LAKEBASE_HOST", "").strip()
    db = os.environ.get("LAKEBASE_DB", "databricks_postgres").strip()
    user = os.environ.get("LAKEBASE_USER", "").strip()
    pwd = os.environ.get("PGPASSWORD", "").strip()
    if not (host and user and pwd):
        print("✗ need LAKEBASE_HOST + LAKEBASE_USER (.env) and PGPASSWORD (minted token in your shell)",
              file=sys.stderr)
        raise SystemExit(1)
    return psycopg.connect(host=host, port=5432, dbname=db, user=user, password=pwd, sslmode="require")


def build() -> dict[str, list[tuple]]:
    """Generate the whole dataset deterministically. Returns {table: rows}."""
    r = Random(MOCK_SEED)

    customers = [
        (i,
         f"{r.choice(SURNAMES)} {r.choice(SEGMENTS)} {r.choice(SUFFIXES)}",
         r.choice(SEGMENTS), r.choice(REGIONS),
         r.choices(RATINGS, weights=[3, 6, 10, 12, 8, 4])[0],
         round(r.uniform(5e5, 8e7), 2),
         _add_months(date(2019, 1, 1), r.randint(0, 72)).isoformat())
        for i in range(1, N_CUSTOMERS + 1)
    ]

    vendors = [
        (i, f"{VENDOR_NAMES[i - 1]} Equipment", r.choice(VENDOR_TYPES), r.choice(REGIONS))
        for i in range(1, N_VENDORS + 1)
    ]

    equipment = []
    for i in range(1, N_EQUIPMENT + 1):
        cost = round(r.uniform(1.5e4, 6e5), 2)
        equipment.append((
            i, r.randint(1, N_VENDORS), r.choice(CATEGORIES), r.choice(MAKES),
            f"M{r.randint(100, 999)}", f"SN-{r.randint(10_000_000, 99_999_999)}",
            cost, round(cost * r.uniform(0.10, 0.35), 2),      # residual = 10–35% of cost
            _add_months(date(2021, 1, 1), r.randint(0, 60)).isoformat()))

    # Applications: a credit pipeline. ~60% booked (those become contracts).
    applications: list[tuple] = []
    booked: list[tuple] = []                                   # (app_id, customer_id, submitted_date)
    for i in range(1, N_APPLICATIONS + 1):
        cust = r.randint(1, N_CUSTOMERS)
        vend = r.randint(1, N_VENDORS)
        amt = round(r.uniform(2e4, 1.2e6), 2)
        submitted = _add_months(date(2023, 1, 1), r.randint(0, 40))
        roll = r.random()
        status = ("booked" if roll < 0.60 else "approved" if roll < 0.72
                  else "declined" if roll < 0.85 else "submitted")
        decision = _add_months(submitted, 1).isoformat() if status != "submitted" else None
        applications.append((i, cust, vend, amt, status, submitted.isoformat(), decision))
        if status == "booked":
            booked.append((i, cust, submitted))

    contracts, contract_assets, schedule, invoices, payments = [], [], [], [], []
    sched_id = inv_id = pay_id = 0
    equip_cursor = 0
    for cid, (app_id, cust, submitted) in enumerate(booked, start=1):
        n_assets = r.randint(1, 3)
        assets = [(equip_cursor + k) % N_EQUIPMENT + 1 for k in range(n_assets)]
        equip_cursor += n_assets
        principal = residual = 0.0
        for eq in assets:
            alloc = float(equipment[eq - 1][6])                # equipment.cost
            principal += alloc
            residual += float(equipment[eq - 1][7])            # equipment.residual_value
            contract_assets.append((cid, eq, round(alloc, 2)))
        principal = round(principal, 2)
        ctype = r.choice(["lease", "loan"])
        apr = round(r.uniform(0.055, 0.135), 4)
        term = r.choice(TERMS)
        start = _add_months(submitted, 1)
        end = _add_months(start, term)
        elapsed = max(0, (SNAPSHOT.year - start.year) * 12 + (SNAPSHOT.month - start.month))
        periods_elapsed = min(elapsed, term)
        if elapsed >= term:
            status = "paid_off"
        else:
            roll = r.random()
            status = "charged_off" if roll < 0.04 else "delinquent" if roll < 0.16 else "active"
        contracts.append((cid, app_id, cust, ctype, status, principal, apr, term,
                          start.isoformat(), end.isoformat(), round(residual, 2)))

        # Amortization: equal-principal; interest on the declining balance.
        prin_per = round(principal / term, 2)
        balance = principal
        for p in range(1, term + 1):
            sched_id += 1
            due = _add_months(start, p)
            interest = round(balance * float(apr) / 12.0, 2)
            total = round(prin_per + interest, 2)
            schedule.append((sched_id, cid, p, due.isoformat(), prin_per, interest, total))
            balance = round(balance - prin_per, 2)

            # Invoice only periods already billed (due on/before the snapshot).
            if p <= periods_elapsed:
                inv_id += 1
                if status in ("delinquent", "charged_off") and p > periods_elapsed - 3:
                    inv_status = "overdue"
                elif p == periods_elapsed and status == "active" and r.random() < 0.5:
                    inv_status = "open"
                else:
                    inv_status = "paid" if r.random() < 0.92 else "overdue"
                invoices.append((inv_id, cid, sched_id, due.isoformat(), due.isoformat(),
                                 total, inv_status))
                if inv_status == "paid":
                    pay_id += 1
                    payments.append((pay_id, inv_id, due.isoformat(), total, r.choice(PAY_METHODS)))

    return {
        "customers": customers, "vendors": vendors, "equipment": equipment,
        "applications": applications, "contracts": contracts, "contract_assets": contract_assets,
        "payment_schedule": schedule, "invoices": invoices, "payments": payments,
    }


INSERTS = {
    "customers": "INSERT INTO customers VALUES (%s,%s,%s,%s,%s,%s,%s, now())",
    "vendors": "INSERT INTO vendors VALUES (%s,%s,%s,%s, now())",
    "equipment": "INSERT INTO equipment VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, now())",
    "applications": "INSERT INTO applications VALUES (%s,%s,%s,%s,%s,%s,%s, now())",
    "contracts": "INSERT INTO contracts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())",
    "contract_assets": "INSERT INTO contract_assets VALUES (%s,%s,%s)",
    "payment_schedule": "INSERT INTO payment_schedule VALUES (%s,%s,%s,%s,%s,%s,%s)",
    "invoices": "INSERT INTO invoices VALUES (%s,%s,%s,%s,%s,%s,%s, now())",
    "payments": "INSERT INTO payments VALUES (%s,%s,%s,%s,%s, now())",
}
ORDER = ["customers", "vendors", "equipment", "applications", "contracts",
         "contract_assets", "payment_schedule", "invoices", "payments"]


def main() -> int:
    data = build()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute(TRUNCATE)
        for t in ORDER:
            cur.executemany(INSERTS[t], data[t])
        conn.commit()
    counts = " ".join(f"{t}={len(data[t])}" for t in ORDER)
    print(f"✓ seeded Lakebase (Silverline Capital): {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
