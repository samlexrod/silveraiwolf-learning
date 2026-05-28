"""Fetch KYC records from verification provider and write to landing zone.

Schedule: daily (06:00 UTC)
Landing zone: /Volumes/{catalog}/{schema}/landing/compliance/kyc_records/
"""

import io
import json
import os
import random
from datetime import UTC, datetime, timedelta

from databricks.sdk import WorkspaceClient


def fetch_data():
    """Fetch KYC data from verification provider.

    In production, this would call a real KYC/AML provider API.
    For the tutorial, we generate realistic sample data for CP001-CP020.
    """
    statuses = ["VERIFIED", "PENDING", "FAILED", "EXPIRED"]
    risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    verifiers = ["ComplianceBot-v3", "J. Martinez", "A. Singh", "KYC-Auto", "M. Chen"]

    records = []
    for i in range(1, 21):
        cp_id = f"CP{i:03d}"
        status = random.choices(statuses, weights=[60, 20, 10, 10])[0]
        risk = random.choices(risk_levels, weights=[40, 30, 20, 10])[0]
        verification_date = datetime.now(UTC) - timedelta(days=random.randint(1, 365))
        expiry_date = verification_date + timedelta(days=365)

        if status == "EXPIRED":
            expiry_date = datetime.now(UTC) - timedelta(days=random.randint(1, 60))

        records.append(
            {
                "kyc_id": f"KYC{i:04d}",
                "counterparty_id": cp_id,
                "verification_status": status,
                "risk_level": risk,
                "verification_date": verification_date.strftime("%Y-%m-%d"),
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "verified_by": random.choice(verifiers),
                "notes": f"Periodic review for {cp_id}"
                if status == "VERIFIED"
                else f"Review pending for {cp_id}",
            }
        )

    return records


def write_to_landing_zone(records, catalog="main", schema="financial_risk_streaming"):
    """Write records as JSON Lines to the landing zone volume."""
    w = WorkspaceClient()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = f"/Volumes/{catalog}/{schema}/landing/compliance/kyc_records/{timestamp}.json"

    content = "\n".join(json.dumps(r) for r in records)
    w.files.upload(path, io.BytesIO(content.encode()))

    print(f"Wrote {len(records)} KYC records to {path}")


def main():
    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    records = fetch_data()
    write_to_landing_zone(records, catalog, schema)


if __name__ == "__main__":
    main()
