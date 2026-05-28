"""Fetch benchmark interest rates (SOFR, ESTR, SONIA, TONAR) and write to landing zone.

Schedule: hourly
Landing zone: /Volumes/{catalog}/{schema}/landing/market_reference/benchmark_rates/
"""

import io
import json
import os
import random
from datetime import UTC, datetime

from databricks.sdk import WorkspaceClient


def fetch_data():
    """Fetch benchmark rates from external API.

    In production, this would call the NY Fed SOFR API, ECB ESTR, etc.
    For the tutorial, we generate realistic sample data.
    """
    benchmarks = {
        "SOFR": {"base_rate": 5.31, "source": "FED"},
        "ESTR": {"base_rate": 3.90, "source": "ECB"},
        "SONIA": {"base_rate": 5.19, "source": "BOE"},
        "TONAR": {"base_rate": -0.02, "source": "BOJ"},
    }

    effective_date = datetime.now(UTC).strftime("%Y-%m-%d")

    records = []
    rate_id = 1
    for name, info in benchmarks.items():
        # Add tiny jitter (1-2 bps)
        jitter = random.uniform(-0.02, 0.02)
        rate = round(info["base_rate"] + jitter, 4)

        records.append(
            {
                "rate_id": f"BM{rate_id:04d}",
                "benchmark_name": name,
                "rate": rate,
                "effective_date": effective_date,
                "source": info["source"],
            }
        )
        rate_id += 1

    return records


def write_to_landing_zone(records, catalog="main", schema="financial_risk_streaming"):
    """Write records as JSON Lines to the landing zone volume."""
    w = WorkspaceClient()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = f"/Volumes/{catalog}/{schema}/landing/market_reference/benchmark_rates/{timestamp}.json"

    content = "\n".join(json.dumps(r) for r in records)
    w.files.upload(path, io.BytesIO(content.encode()))

    print(f"Wrote {len(records)} benchmark rate records to {path}")


def main():
    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    records = fetch_data()
    write_to_landing_zone(records, catalog, schema)


if __name__ == "__main__":
    main()
