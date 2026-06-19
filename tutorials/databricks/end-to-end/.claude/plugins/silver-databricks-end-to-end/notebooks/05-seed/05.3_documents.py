# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 5 — Land Silverline's unstructured documents
# MAGIC
# MAGIC Silverline's reality isn't only rows: every booked contract has a signed **agreement PDF**, and
# MAGIC underwriters keep **credit memos**. These are the *unstructured* source the later **`agents`** phase
# MAGIC embeds for Vector Search. We render them **from the already-seeded Postgres data** (single source of
# MAGIC truth) and write them to the Unity Catalog volume **`silverline.bronze.files`**.
# MAGIC
# MAGIC > 🔁 **Run `05.1_seed_oltp` first** — this reads the contracts/customers/equipment it created.
# MAGIC > 🔗 Files are named with the id (`contract_<id>.pdf`, `credit_memo_<customer_id>.md`) so the `agents`
# MAGIC > phase can join an unstructured hit back to the structured rows.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]" "databricks-sdk>=0.61.0" reportlab -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Connect to the seeded Postgres + pull the data
# MAGIC Same documented Lakebase pattern (SDK credential → psycopg). We fetch the tables the documents need.

# COMMAND ----------

import uuid
import psycopg
from databricks.sdk import WorkspaceClient

ENDPOINT = "projects/silverline-oltp/branches/production/endpoints/primary"  # Autoscaling project (PG17)
w = WorkspaceClient()
HOST = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
USER = w.current_user.me().user_name
TOKEN = w.postgres.generate_database_credential(ENDPOINT).token


def fetch(sql):
    with psycopg.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER,
                         password=TOKEN, sslmode="require") as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


# Column order matches how the renderers below index each row.
customers = {r[0]: r for r in fetch(
    "SELECT customer_id, legal_name, segment, region, credit_rating, annual_revenue, onboarded_date FROM customers")}
vendors = {r[0]: r for r in fetch("SELECT vendor_id, name, vendor_type, region FROM vendors")}
equipment = {r[0]: r for r in fetch(
    "SELECT equipment_id, vendor_id, category, make, model, serial_number, cost, residual_value, in_service_date FROM equipment")}
applications = {r[0]: r for r in fetch(
    "SELECT application_id, customer_id, vendor_id, amount_requested, status, submitted_date, decision_date FROM applications")}
contracts = fetch(
    "SELECT contract_id, application_id, customer_id, contract_type, status, principal, apr, term_months, start_date, end_date, residual_value FROM contracts ORDER BY contract_id")

assets_by = {}
for cid, eid in fetch("SELECT contract_id, equipment_id FROM contract_assets ORDER BY contract_id"):
    assets_by.setdefault(cid, []).append(equipment[eid])
custs_contracts = {}
for ct in contracts:
    custs_contracts.setdefault(ct[2], []).append(ct)

print(f"pulled {len(contracts)} contracts, {len(customers)} customers, {len(equipment)} equipment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Renderers (PDF agreement + Markdown credit memo)

# COMMAND ----------

import io

CLAUSES = [
    "1. PAYMENT. Obligor shall pay each scheduled installment on or before its due date per the amortization "
    "schedule of record. Amounts not received within 10 days of the due date accrue a late charge.",
    "2. DEFAULT. Failure to pay, or breach of any covenant, constitutes an event of default, upon which "
    "Silverline Capital may declare the unpaid balance immediately due and repossess the financed equipment.",
    "3. EQUIPMENT. Title and risk of loss are governed by the agreement type (lease vs loan). Obligor shall "
    "maintain and insure the equipment and keep it free of liens.",
    "4. END OF TERM. At maturity, Obligor may satisfy the residual / purchase option shown below, renew, or "
    "return the equipment in good condition, per the agreement type.",
    "5. GOVERNING LAW. This agreement is governed by the laws of the State of Nebraska. (Fictional sample "
    "document for the Silverline Capital tutorial — not a real contract.)",
]


def render_pdf(contract, customer, vendor, assets) -> bytes:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    cid, app_id, cust_id, ctype, status, principal, apr, term, start, end, residual = contract
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    x, y = inch, height - inch

    def line(text, dy=15, font="Helvetica", size=10):
        nonlocal y
        c.setFont(font, size)
        c.drawString(x, y, str(text)[:110])
        y -= dy

    line("SILVERLINE CAPITAL — EQUIPMENT FINANCE AGREEMENT", dy=22, font="Helvetica-Bold", size=15)
    line(f"Agreement No. CONTRACT-{cid}   ·   Type: {ctype.upper()}   ·   Status: {status}",
         dy=20, font="Helvetica-Bold", size=10)
    line(f"Obligor: {customer[1]}", font="Helvetica-Bold")
    line(f"  Segment: {customer[2]}   Region: {customer[3]}   Credit rating: {customer[4]}")
    if vendor:
        line(f"Originating vendor: {vendor[1]} ({vendor[2]})")
    y -= 6
    line("FINANCED EQUIPMENT", dy=16, font="Helvetica-Bold", size=11)
    for eq in assets:
        line(f"  • {eq[3]} {eq[4]} — {eq[2]}  (serial {eq[5]})   cost ${eq[6]:,.2f}")
    y -= 6
    line("FINANCIAL TERMS", dy=16, font="Helvetica-Bold", size=11)
    line(f"  Principal financed: ${principal:,.2f}    APR: {float(apr) * 100:.2f}%    Term: {term} months")
    line(f"  Commencement: {start}    Maturity: {end}")
    line(f"  Residual / purchase option: ${residual:,.2f}")
    y -= 10
    line("TERMS & CONDITIONS", dy=16, font="Helvetica-Bold", size=11)
    for clause in CLAUSES:
        for seg in simpleSplit(clause, "Helvetica", 9, width - 2 * inch):
            c.setFont("Helvetica", 9)
            c.drawString(x, y, seg)
            y -= 12
        y -= 3
    c.showPage()
    c.save()
    return buf.getvalue()


def render_memo(customer, contracts_for_cust) -> str:
    cust_id, name, segment, region, rating, revenue, onboarded = customer
    exposure = sum(float(c[5]) for c in contracts_for_cust)
    return "\n".join([
        f"# Credit Memo — {name}", "",
        f"- **Customer ID:** {cust_id}",
        f"- **Segment / Region:** {segment} / {region}",
        f"- **Credit rating:** {rating}",
        f"- **Annual revenue:** ${revenue:,.2f}",
        f"- **Onboarded:** {onboarded}",
        f"- **Active relationships:** {len(contracts_for_cust)} contract(s), ${exposure:,.2f} total principal financed",
        "", "## Underwriting note",
        f"{name} operates in the {segment.lower()} sector. Based on a {rating} internal rating and the current "
        f"${exposure:,.2f} of financed equipment, the relationship is within Silverline Capital's concentration "
        "limits. Recommend continued monitoring of payment performance.",
        "", "_Fictional sample document for the Silverline Capital tutorial._", "",
    ])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Write the documents straight to the volume
# MAGIC A notebook can write to a UC volume via its `/Volumes/...` path. One PDF per contract; a credit memo
# MAGIC for the first 10 customers (to show the volume holds any format).

# COMMAND ----------

import os

VOL_BASE = "/Volumes/silverline/bronze/files"
os.makedirs(f"{VOL_BASE}/contracts", exist_ok=True)
os.makedirs(f"{VOL_BASE}/memos", exist_ok=True)

n_pdf = 0
for ct in contracts:
    cid, app_id, cust_id = ct[0], ct[1], ct[2]
    vendor = vendors.get(applications[app_id][2]) if app_id in applications else None
    pdf = render_pdf(ct, customers[cust_id], vendor, assets_by.get(cid, []))
    with open(f"{VOL_BASE}/contracts/contract_{cid}.pdf", "wb") as fh:
        fh.write(pdf)
    n_pdf += 1

n_memo = 0
for cu in list(customers.values())[:10]:
    memo = render_memo(cu, custs_contracts.get(cu[0], []))
    with open(f"{VOL_BASE}/memos/credit_memo_{cu[0]}.md", "w") as fh:
        fh.write(memo)
    n_memo += 1

print(f"✓ wrote {n_pdf} contract PDFs + {n_memo} credit memos → {VOL_BASE}/{{contracts,memos}}/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Verify they landed

# COMMAND ----------

print("contracts/:", len(dbutils.fs.ls(f"{VOL_BASE}/contracts")), "files")
print("memos/:    ", len(dbutils.fs.ls(f"{VOL_BASE}/memos")), "files")
for f in dbutils.fs.ls(f"{VOL_BASE}/memos")[:3]:
    print("  ", f.name)

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Silverline's unstructured documents are in `silverline.bronze.files`. Browse them in **Catalog →
# MAGIC silverline → bronze → files**. This completes the **seed** stage — structured (Lakebase OLTP) **and**
# MAGIC unstructured (volume) sources are loaded. Next phase: **Lakehouse** (`06-data-api`, then `07-ingest`).
