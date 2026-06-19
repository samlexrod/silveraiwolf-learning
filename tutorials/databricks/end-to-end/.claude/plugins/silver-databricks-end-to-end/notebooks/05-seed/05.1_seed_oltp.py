# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 5 — Seed the Silverline Capital OLTP (from this notebook)
# MAGIC
# MAGIC Loads the **9-table OLTP** into the Lakebase Postgres instance `silverline-oltp` with **deterministic**
# MAGIC mock data (`MOCK_SEED=42` → identical rows every run; idempotent `TRUNCATE`+reload).
# MAGIC
# MAGIC This runs entirely **in your workspace**: it mints a Lakebase credential via the Databricks SDK (the
# MAGIC notebook runs as *you* — no token to paste), `pip install`s `psycopg`, connects to the Postgres
# MAGIC endpoint, and seeds. Afterwards, `05.2_data_model` is your ERD + dictionary reference.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Install the Postgres driver + a current SDK
# MAGIC `psycopg` (v3) is the Postgres client. The typed `w.database` SDK service needs **databricks-sdk ≥
# MAGIC 0.61.0** (the serverless runtime ships an older one), so we upgrade it here. `restartPython()` makes
# MAGIC the freshly-installed packages importable. *(This is the official Lakebase-from-notebook pattern.)*

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Connection: mint a credential via the SDK
# MAGIC No secrets — the SDK uses the notebook's own identity to read the endpoint and mint a short-lived
# MAGIC OAuth token (~1h) that serves as the Postgres password. This is the documented Databricks idiom
# MAGIC (`w.database.get_database_instance` + `generate_database_credential`).

# COMMAND ----------

from databricks.sdk import WorkspaceClient

# Lakebase Autoscaling project (PG17) → use the `w.postgres` API (not `w.database`).
ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"
w = WorkspaceClient()
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER = w.current_user.me().user_name
DB = "databricks_postgres"
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token
print(f"host={HOST}\nuser={USER}\ndb={DB}\ntoken={'set' if TOKEN else 'MISSING'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — The deterministic data generator
# MAGIC The full origination → booking → billing → payments lifecycle. Same logic as the repo's
# MAGIC `scripts/lakebase_seed.py`, embedded here so the notebook is self-contained.

# COMMAND ----------

from datetime import date
from random import Random

MOCK_SEED = 42
SNAPSHOT = date(2026, 6, 1)        # "today" for billing — invoices exist for elapsed periods only
N_CUSTOMERS, N_VENDORS, N_EQUIPMENT, N_APPLICATIONS = 60, 15, 220, 140

SEGMENTS = ["Manufacturing", "Logistics", "Retail", "Construction", "Agriculture", "Healthcare"]
REGIONS = ["North", "South", "East", "West", "Central"]
RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B"]
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


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    return date(y, m % 12 + 1, min(d.day, 28))


def build():
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
            cost, round(cost * r.uniform(0.10, 0.35), 2),
            _add_months(date(2021, 1, 1), r.randint(0, 60)).isoformat()))

    applications, booked = [], []
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
            alloc = float(equipment[eq - 1][6])
            principal += alloc
            residual += float(equipment[eq - 1][7])
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

        prin_per = round(principal / term, 2)
        balance = principal
        for p in range(1, term + 1):
            sched_id += 1
            due = _add_months(start, p)
            interest = round(balance * float(apr) / 12.0, 2)
            total = round(prin_per + interest, 2)
            schedule.append((sched_id, cid, p, due.isoformat(), prin_per, interest, total))
            balance = round(balance - prin_per, 2)
            if p <= periods_elapsed:
                inv_id += 1
                if status in ("delinquent", "charged_off") and p > periods_elapsed - 3:
                    inv_status = "overdue"
                elif p == periods_elapsed and status == "active" and r.random() < 0.5:
                    inv_status = "open"
                else:
                    inv_status = "paid" if r.random() < 0.92 else "overdue"
                invoices.append((inv_id, cid, sched_id, due.isoformat(), due.isoformat(), total, inv_status))
                if inv_status == "paid":
                    pay_id += 1
                    payments.append((pay_id, inv_id, due.isoformat(), total, r.choice(PAY_METHODS)))

    return {
        "customers": customers, "vendors": vendors, "equipment": equipment,
        "applications": applications, "contracts": contracts, "contract_assets": contract_assets,
        "payment_schedule": schedule, "invoices": invoices, "payments": payments,
    }


data = build()
print("generated rows:", {t: len(rows) for t, rows in data.items()})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Create the schema + load (idempotent)
# MAGIC Connects with `psycopg` over SSL, creates the 9 tables, `TRUNCATE`s, and bulk-inserts. Re-running
# MAGIC reloads the identical rows.

# COMMAND ----------

DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY, legal_name TEXT NOT NULL, segment TEXT, region TEXT,
    credit_rating TEXT, annual_revenue NUMERIC(14,2), onboarded_date DATE,
    updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id INT PRIMARY KEY, name TEXT NOT NULL, vendor_type TEXT, region TEXT,
    updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id INT PRIMARY KEY, vendor_id INT REFERENCES vendors(vendor_id), category TEXT,
    make TEXT, model TEXT, serial_number TEXT, cost NUMERIC(14,2), residual_value NUMERIC(14,2),
    in_service_date DATE, updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS applications (
    application_id INT PRIMARY KEY, customer_id INT REFERENCES customers(customer_id),
    vendor_id INT REFERENCES vendors(vendor_id), amount_requested NUMERIC(14,2), status TEXT,
    submitted_date DATE, decision_date DATE, updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS contracts (
    contract_id INT PRIMARY KEY, application_id INT REFERENCES applications(application_id),
    customer_id INT REFERENCES customers(customer_id), contract_type TEXT, status TEXT,
    principal NUMERIC(14,2), apr NUMERIC(6,4), term_months INT, start_date DATE, end_date DATE,
    residual_value NUMERIC(14,2), updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS contract_assets (
    contract_id INT REFERENCES contracts(contract_id), equipment_id INT REFERENCES equipment(equipment_id),
    allocated_cost NUMERIC(14,2), PRIMARY KEY (contract_id, equipment_id));
CREATE TABLE IF NOT EXISTS payment_schedule (
    schedule_id INT PRIMARY KEY, contract_id INT REFERENCES contracts(contract_id), period_no INT,
    due_date DATE, principal_due NUMERIC(12,2), interest_due NUMERIC(12,2), total_due NUMERIC(12,2));
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INT PRIMARY KEY, contract_id INT REFERENCES contracts(contract_id),
    schedule_id INT REFERENCES payment_schedule(schedule_id), invoice_date DATE, due_date DATE,
    amount NUMERIC(12,2), status TEXT, updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT PRIMARY KEY, invoice_id INT REFERENCES invoices(invoice_id), paid_date DATE,
    amount NUMERIC(12,2), method TEXT, updated_at TIMESTAMPTZ DEFAULT now());
"""

TRUNCATE = """TRUNCATE payments, invoices, payment_schedule, contract_assets, contracts,
                       applications, equipment, vendors, customers RESTART IDENTITY CASCADE;"""

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

import psycopg

with psycopg.connect(host=HOST, port=5432, dbname=DB, user=USER, password=TOKEN,
                     sslmode="require") as conn, conn.cursor() as cur:
    cur.execute(DDL)
    cur.execute(TRUNCATE)
    for t in ORDER:
        cur.executemany(INSERTS[t], data[t])
    conn.commit()

print("✓ seeded Lakebase (Silverline Capital): " + " ".join(f"{t}={len(data[t])}" for t in ORDER))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — Verify the row counts
# MAGIC Reads them back from Postgres. Expect customers=60, vendors=15, equipment=220, applications=140,
# MAGIC contracts=85, contract_assets=180, payment_schedule=2904, invoices=1452, payments=1291.

# COMMAND ----------

import psycopg

with psycopg.connect(host=HOST, port=5432, dbname=DB, user=USER, password=TOKEN,
                     sslmode="require") as conn, conn.cursor() as cur:
    for t in ORDER:
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"{t:18} {cur.fetchone()[0]}")
