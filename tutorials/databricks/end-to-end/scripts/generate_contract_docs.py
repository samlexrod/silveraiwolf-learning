"""Generate Silverline Capital's UNSTRUCTURED documents and land them in the UC volume.

The structured seed (`lakebase_seed.py`) loads Lakebase. This is its unstructured counterpart: for each
booked contract it renders a one-page lease/loan **agreement PDF**, and for a handful of customers a
**credit-memo `.md`** (to show the volume holds any format). Files are named with the contract_id /
customer_id so a later phase (the `agents` track) can parse → embed → index them in Vector Search and join
unstructured hits back to the structured tables.

Built from the SAME deterministic seed data (`lakebase_seed.build()`), so no DB connection is needed to
generate — only to upload.

Local output:  seed_docs/contracts/contract_<id>.pdf  +  seed_docs/memos/credit_memo_<customer_id>.md
Volume target: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{contracts,memos}/

Auth for upload (same as run_sql): DATABRICKS_HOST + DATABRICKS_TOKEN in the environment.
Usage:  mise run docs:seed                 # generate locally + upload to the volume
        mise run docs:seed -- --local-only # generate only (inspect before uploading)
Env:    DOCS_LIMIT=N   cap the number of contract PDFs (0 = all)   ·   MEMO_LIMIT=N (default 10)
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import lakebase_seed as seed   # same scripts/ dir; build() is the deterministic data source

CATALOG = os.environ.get("FREE_CATALOG", "silverline")
SCHEMA = os.environ.get("FREE_SCHEMA", "bronze")
VOLUME = os.environ.get("FREE_VOLUME", "files")
OUTDIR = Path(__file__).resolve().parent.parent / "seed_docs"
VOL_BASE = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

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


def _render_pdf(contract, customer, vendor, assets) -> bytes:
    """One-page lease/loan agreement PDF for a contract (reportlab)."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    cid, app_id, cust_id, ctype, status, principal, apr, term, start, end, residual = contract
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    x, y = inch, height - inch

    def line(text, dy=15, font="Helvetica", size=10):
        nonlocal y
        c.setFont(font, size)
        c.drawString(x, y, text[:110])
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
        # equipment: (id, vendor_id, category, make, model, serial, cost, residual, in_service)
        line(f"  • {eq[3]} {eq[4]} — {eq[2]}  (serial {eq[5]})   cost ${eq[6]:,.2f}")
    y -= 6
    line("FINANCIAL TERMS", dy=16, font="Helvetica-Bold", size=11)
    line(f"  Principal financed: ${principal:,.2f}    APR: {float(apr) * 100:.2f}%    Term: {term} months")
    line(f"  Commencement: {start}    Maturity: {end}")
    line(f"  Residual / purchase option: ${residual:,.2f}")
    y -= 10
    line("TERMS & CONDITIONS", dy=16, font="Helvetica-Bold", size=11)
    from reportlab.lib.utils import simpleSplit
    for clause in CLAUSES:
        for seg in simpleSplit(clause, "Helvetica", 9, width - 2 * inch):
            c.setFont("Helvetica", 9)
            c.drawString(x, y, seg)
            y -= 12
        y -= 3
    c.showPage()
    c.save()
    return buf.getvalue()


def _render_memo(customer, contracts_for_cust) -> str:
    """A short credit memo (markdown) for a customer — demonstrates non-PDF formats in the volume."""
    cust_id, name, segment, region, rating, revenue, onboarded = customer
    exposure = sum(float(c[5]) for c in contracts_for_cust)
    lines = [
        f"# Credit Memo — {name}",
        "",
        f"- **Customer ID:** {cust_id}",
        f"- **Segment / Region:** {segment} / {region}",
        f"- **Credit rating:** {rating}",
        f"- **Annual revenue:** ${revenue:,.2f}",
        f"- **Onboarded:** {onboarded}",
        f"- **Active relationships:** {len(contracts_for_cust)} contract(s), "
        f"${exposure:,.2f} total principal financed",
        "",
        "## Underwriting note",
        f"{name} operates in the {segment.lower()} sector. Based on a {rating} internal rating and the "
        f"current ${exposure:,.2f} of financed equipment, the relationship is within Silverline Capital's "
        "concentration limits. Recommend continued monitoring of payment performance.",
        "",
        "_Fictional sample document for the Silverline Capital tutorial._",
        "",
    ]
    return "\n".join(lines)


def _upload(client, local: Path, vol_path: str):
    with local.open("rb") as fh:
        client.files.upload(vol_path, fh, overwrite=True)


def main() -> int:
    local_only = "--local-only" in sys.argv
    docs_limit = int(os.environ.get("DOCS_LIMIT", "0"))
    memo_limit = int(os.environ.get("MEMO_LIMIT", "10"))

    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("✗ reportlab not installed — run `mise run setup`", file=sys.stderr)
        return 1

    data = seed.build()
    cust_by = {c[0]: c for c in data["customers"]}
    vend_by = {v[0]: v for v in data["vendors"]}
    equip_by = {e[0]: e for e in data["equipment"]}
    app_by = {a[0]: a for a in data["applications"]}
    assets_by: dict[int, list] = {}
    for ca in data["contract_assets"]:
        assets_by.setdefault(ca[0], []).append(equip_by[ca[1]])
    custs_contracts: dict[int, list] = {}
    for ct in data["contracts"]:
        custs_contracts.setdefault(ct[2], []).append(ct)

    (OUTDIR / "contracts").mkdir(parents=True, exist_ok=True)
    (OUTDIR / "memos").mkdir(parents=True, exist_ok=True)

    contracts = data["contracts"][:docs_limit] if docs_limit else data["contracts"]
    n_pdf = 0
    for ct in contracts:
        cid, app_id, cust_id = ct[0], ct[1], ct[2]
        vendor = vend_by.get(app_by[app_id][2]) if app_id in app_by else None
        pdf = _render_pdf(ct, cust_by[cust_id], vendor, assets_by.get(cid, []))
        (OUTDIR / "contracts" / f"contract_{cid}.pdf").write_bytes(pdf)
        n_pdf += 1

    memo_custs = data["customers"][:memo_limit]
    n_memo = 0
    for cu in memo_custs:
        memo = _render_memo(cu, custs_contracts.get(cu[0], []))
        (OUTDIR / "memos" / f"credit_memo_{cu[0]}.md").write_text(memo)
        n_memo += 1

    print(f"✓ generated {n_pdf} contract PDFs + {n_memo} credit memos → {OUTDIR}")

    if local_only:
        print("  (--local-only: skipped upload)")
        return 0

    host = os.environ.get("DATABRICKS_HOST", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if not (host and token):
        print("✗ need DATABRICKS_HOST (.env) + DATABRICKS_TOKEN (shell) to upload; or use --local-only",
              file=sys.stderr)
        return 1
    try:
        from databricks.sdk import WorkspaceClient
    except ImportError:
        print("✗ databricks-sdk not installed — run `mise run setup`", file=sys.stderr)
        return 1
    w = WorkspaceClient(host=host, token=token)
    for sub in ("contracts", "memos"):
        for f in sorted((OUTDIR / sub).glob("*")):
            _upload(w, f, f"{VOL_BASE}/{sub}/{f.name}")
    print(f"✓ uploaded {n_pdf + n_memo} files → {VOL_BASE}/{{contracts,memos}}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
