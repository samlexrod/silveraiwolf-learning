"""Fetch exchange rates from ECB-like FX rate API and write to landing zone.

Schedule: hourly
Landing zone: /Volumes/{catalog}/{schema}/landing/market_reference/exchange_rates/
"""

import io
import json
import os
import random
from datetime import UTC, datetime

from databricks.sdk import WorkspaceClient


def fetch_data():
    """Fetch FX rates from external API.

    In production, this would call the ECB SDMX API or similar.
    For the tutorial, we generate realistic sample data.
    """
    base_rates = {
        ("EUR", "USD"): 1.0870,
        ("GBP", "USD"): 1.2710,
        ("USD", "JPY"): 149.50,
        ("AUD", "USD"): 0.6620,
        ("USD", "CHF"): 0.8840,
        ("EUR", "GBP"): 0.8550,
        ("EUR", "JPY"): 162.50,
        ("GBP", "JPY"): 190.00,
        ("USD", "CAD"): 1.3560,
        ("NZD", "USD"): 0.6140,
    }

    sources = ["ECB", "FED", "BOE"]
    rate_date = datetime.now(UTC).strftime("%Y-%m-%d")

    records = []
    rate_id = 1
    for (base, quote), mid_rate in base_rates.items():
        # Add small random jitter to simulate real-time rates
        jitter = random.uniform(-0.005, 0.005) * mid_rate
        rate = round(mid_rate + jitter, 4)

        records.append(
            {
                "rate_id": f"FX{rate_id:04d}",
                "base_currency": base,
                "quote_currency": quote,
                "rate": rate,
                "rate_date": rate_date,
                "source": random.choice(sources),
            }
        )
        rate_id += 1

    return records


def write_to_landing_zone(records, catalog="main", schema="financial_risk_streaming"):
    """Write records as JSON Lines to the landing zone volume."""
    w = WorkspaceClient()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = f"/Volumes/{catalog}/{schema}/landing/market_reference/exchange_rates/{timestamp}.json"

    content = "\n".join(json.dumps(r) for r in records)
    w.files.upload(path, io.BytesIO(content.encode()))

    print(f"Wrote {len(records)} exchange rate records to {path}")


def main():
    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    records = fetch_data()
    write_to_landing_zone(records, catalog, schema)


if __name__ == "__main__":
    main()
