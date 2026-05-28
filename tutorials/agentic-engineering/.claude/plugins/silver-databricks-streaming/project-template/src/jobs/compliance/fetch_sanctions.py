"""Fetch sanctions watchlist from OFAC-like sanctions API and write to landing zone.

Schedule: daily (06:00 UTC)
Landing zone: /Volumes/{catalog}/{schema}/landing/compliance/sanctions_watchlist/
"""

import io
import json
import os
import random
from datetime import UTC, datetime, timedelta

from databricks.sdk import WorkspaceClient


def fetch_data():
    """Fetch sanctions data from external API.

    In production, this would call a real sanctions screening API (e.g., OFAC SDN list).
    For the tutorial, we generate realistic sample data.
    """
    countries = ["IR", "KP", "SY", "RU", "BY", "VE", "CU", "MM", "SD", "LY"]
    source_lists = ["OFAC", "EU", "UN"]

    individuals = [
        "Ahmad Al-Rashid",
        "Viktor Petrov",
        "Kim Yong-su",
        "Hassan Mahmoud",
        "Sergei Volkov",
        "Ali Kazemi",
        "Park Chul-soo",
        "Omar Farouk",
        "Dmitri Sokolov",
        "Reza Mohammadi",
        "Andrei Kuznetsov",
        "Farid Hosseini",
        "Nikolai Ivanov",
        "Jang Min-ho",
        "Karim El-Sayed",
        "Boris Fedorov",
        "Amir Tehrani",
        "Choe Sung-il",
        "Yusuf Al-Bakri",
        "Pavel Smirnov",
    ]

    organizations = [
        "Petrostan Energy Corp",
        "Dragon Star Trading Co",
        "Golden Bridge Shipping Ltd",
        "Meridian Defense Industries",
        "Volga Industrial Group",
        "Pacific Rim Holdings",
        "Al-Noor Financial Services",
        "Red Star Minerals LLC",
        "Caspian Oil & Gas",
        "Eastern Promise Trading",
        "Thunder Bay Logistics",
        "Silk Road Ventures",
        "Falcon Aerospace Systems",
        "Diamond Coast Mining",
        "Atlas Maritime Services",
        "Pinnacle Arms Manufacturing",
        "Oasis Petroleum",
        "Iron Curtain Metals",
        "Crescent Financial Group",
        "Typhoon Shipping International",
        "Northern Light Energy",
        "Desert Storm Industries",
        "Black Sea Trading",
        "Golden Eagle Exports",
        "Sunrise Capital Holdings",
        "Arctic Wolf Resources",
        "Phoenix Global Trading",
        "Storm Shield Defense",
        "River Delta Logistics",
        "Mountain Peak Mining",
    ]

    records = []
    entity_id = 1

    for name in individuals:
        records.append(
            {
                "entity_id": f"SAN{entity_id:04d}",
                "entity_name": name,
                "entity_type": "INDIVIDUAL",
                "source_list": random.choice(source_lists),
                "country": random.choice(countries),
                "match_score": round(random.uniform(0.75, 1.0), 2),
                "status": random.choice(["ACTIVE"] * 4 + ["DELISTED"]),
                "listed_date": (
                    datetime.now(UTC) - timedelta(days=random.randint(30, 1800))
                ).strftime("%Y-%m-%d"),
                "delisted_date": None,
                "last_checked": datetime.now(UTC).isoformat(),
            }
        )
        entity_id += 1

    for name in organizations:
        records.append(
            {
                "entity_id": f"SAN{entity_id:04d}",
                "entity_name": name,
                "entity_type": "ORGANIZATION",
                "source_list": random.choice(source_lists),
                "country": random.choice(countries),
                "match_score": round(random.uniform(0.70, 1.0), 2),
                "status": random.choice(["ACTIVE"] * 4 + ["DELISTED"]),
                "listed_date": (
                    datetime.now(UTC) - timedelta(days=random.randint(30, 1800))
                ).strftime("%Y-%m-%d"),
                "delisted_date": None,
                "last_checked": datetime.now(UTC).isoformat(),
            }
        )
        entity_id += 1

    # Set delisted_date for DELISTED entries
    for r in records:
        if r["status"] == "DELISTED":
            r["delisted_date"] = (
                datetime.now(UTC) - timedelta(days=random.randint(1, 90))
            ).strftime("%Y-%m-%d")

    return records


def write_to_landing_zone(records, catalog="main", schema="financial_risk_streaming"):
    """Write records as JSON Lines to the landing zone volume."""
    w = WorkspaceClient()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = f"/Volumes/{catalog}/{schema}/landing/compliance/sanctions_watchlist/{timestamp}.json"

    content = "\n".join(json.dumps(r) for r in records)
    w.files.upload(path, io.BytesIO(content.encode()))

    print(f"Wrote {len(records)} sanctions records to {path}")


def main():
    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    records = fetch_data()
    write_to_landing_zone(records, catalog, schema)


if __name__ == "__main__":
    main()
