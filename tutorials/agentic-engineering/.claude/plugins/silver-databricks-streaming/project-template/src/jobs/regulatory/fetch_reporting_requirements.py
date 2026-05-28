"""Fetch regulatory reporting requirements and write to landing zone.

Schedule: hourly
Landing zone: /Volumes/{catalog}/{schema}/landing/regulatory/reporting_requirements/
"""

import io
import json
import os
import random
from datetime import UTC, datetime, timedelta

from databricks.sdk import WorkspaceClient


def fetch_data():
    """Fetch regulatory requirements from compliance feed.

    In production, this would call a regulatory data provider API.
    For the tutorial, we generate realistic sample data.
    """
    regulations = [
        {
            "name": "MiFID II",
            "jurisdiction": "EU",
            "type": "Transaction Reporting",
            "frequency": "DAILY",
        },
        {
            "name": "MiFID II",
            "jurisdiction": "EU",
            "type": "Best Execution",
            "frequency": "QUARTERLY",
        },
        {"name": "EMIR", "jurisdiction": "EU", "type": "Trade Repository", "frequency": "DAILY"},
        {"name": "EMIR", "jurisdiction": "EU", "type": "Risk Mitigation", "frequency": "MONTHLY"},
        {
            "name": "Dodd-Frank",
            "jurisdiction": "US",
            "type": "Swap Data Reporting",
            "frequency": "DAILY",
        },
        {"name": "Dodd-Frank", "jurisdiction": "US", "type": "Large Trader", "frequency": "WEEKLY"},
        {
            "name": "Basel III",
            "jurisdiction": "GLOBAL",
            "type": "Capital Adequacy",
            "frequency": "QUARTERLY",
        },
        {
            "name": "Basel III",
            "jurisdiction": "GLOBAL",
            "type": "Liquidity Coverage",
            "frequency": "MONTHLY",
        },
        {"name": "SFTR", "jurisdiction": "EU", "type": "SFT Reporting", "frequency": "DAILY"},
        {
            "name": "MAR",
            "jurisdiction": "EU",
            "type": "Suspicious Transaction",
            "frequency": "DAILY",
        },
        {
            "name": "SOX",
            "jurisdiction": "US",
            "type": "Internal Controls",
            "frequency": "QUARTERLY",
        },
        {
            "name": "AML/CFT",
            "jurisdiction": "GLOBAL",
            "type": "Suspicious Activity",
            "frequency": "DAILY",
        },
        {
            "name": "FATCA",
            "jurisdiction": "US",
            "type": "Foreign Account",
            "frequency": "QUARTERLY",
        },
        {
            "name": "CRS",
            "jurisdiction": "GLOBAL",
            "type": "Common Reporting",
            "frequency": "QUARTERLY",
        },
        {"name": "FRTB", "jurisdiction": "GLOBAL", "type": "Market Risk", "frequency": "MONTHLY"},
    ]

    statuses = ["COMPLIANT", "NON_COMPLIANT", "PENDING"]
    desk_groups = [
        "EQ-NYC,FI-NYC",
        "FX-LDN,DRV-LDN",
        "EQ-TKY",
        "ALL",
        "FI-NYC,FI-LDN",
        "DRV-NYC,DRV-LDN,DRV-TKY",
        "EQ-LDN",
    ]

    records = []
    for i, reg in enumerate(regulations, 1):
        now = datetime.now(UTC)
        freq_days = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30, "QUARTERLY": 90}
        next_due = now + timedelta(days=random.randint(-5, freq_days[reg["frequency"]]))

        records.append(
            {
                "requirement_id": f"REG{i:04d}",
                "regulation_name": reg["name"],
                "jurisdiction": reg["jurisdiction"],
                "report_type": reg["type"],
                "frequency": reg["frequency"],
                "next_due_date": next_due.strftime("%Y-%m-%d"),
                "status": random.choices(statuses, weights=[60, 25, 15])[0],
                "affected_desks": random.choice(desk_groups),
            }
        )

    return records


def write_to_landing_zone(records, catalog="main", schema="financial_risk_streaming"):
    """Write records as JSON Lines to the landing zone volume."""
    w = WorkspaceClient()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = f"/Volumes/{catalog}/{schema}/landing/regulatory/reporting_requirements/{timestamp}.json"

    content = "\n".join(json.dumps(r) for r in records)
    w.files.upload(path, io.BytesIO(content.encode()))

    print(f"Wrote {len(records)} regulatory requirement records to {path}")


def main():
    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    records = fetch_data()
    write_to_landing_zone(records, catalog, schema)


if __name__ == "__main__":
    main()
