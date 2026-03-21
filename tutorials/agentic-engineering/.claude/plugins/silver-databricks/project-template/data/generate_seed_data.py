"""Generate synthetic financial data for the medallion pipeline tutorial.

Creates realistic-looking CSVs for counterparties, transactions, and market data.
Output goes to data/seed/ — upload these to a Databricks Volume.

Usage:
    uv run python data/generate_seed_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

SEED_DIR = os.path.join(os.path.dirname(__file__), "seed")
RANDOM_SEED = 42

SECTORS = ["TECHNOLOGY", "FINANCE", "ENERGY", "HEALTHCARE", "INDUSTRIALS"]
COUNTRIES = ["US", "UK", "DE", "JP", "SG"]
CREDIT_RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
CURRENCIES = ["USD", "EUR", "GBP", "JPY"]
INSTRUMENT_TYPES = ["EQUITY", "BOND", "DERIVATIVE", "FX"]
DIRECTIONS = ["BUY", "SELL"]

NUM_COUNTERPARTIES = 20
NUM_INSTRUMENTS = 50
NUM_DAYS = 90
TRANSACTIONS_PER_DAY = 15


def generate_counterparties():
    """Generate counterparty master data with balance sheet figures."""
    rows = []
    names = [
        "Apex Capital", "Vertex Holdings", "Meridian Finance", "Pinnacle Group",
        "Horizon Partners", "Summit Investments", "Vanguard Systems", "Atlas Trading",
        "Quantum Dynamics", "Nordic Securities", "Pacific Ventures", "Sterling Corp",
        "Cobalt Industries", "Nexus Financial", "Prism Technologies", "Titan Energy",
        "Echo Pharmaceuticals", "Delta Manufacturing", "Sigma Analytics", "Omega Research",
    ]

    random.seed(RANDOM_SEED)
    for i, name in enumerate(names[:NUM_COUNTERPARTIES]):
        total_assets = round(random.uniform(50_000_000, 5_000_000_000), 2)
        current_pct = random.uniform(0.2, 0.6)
        liability_pct = random.uniform(0.3, 0.8)
        current_liability_pct = random.uniform(0.3, 0.7)

        total_liabilities = round(total_assets * liability_pct, 2)
        total_equity = round(total_assets - total_liabilities, 2)
        current_assets = round(total_assets * current_pct, 2)
        current_liabilities = round(total_liabilities * current_liability_pct, 2)
        total_debt = round(total_liabilities * random.uniform(0.4, 0.9), 2)
        revenue = round(total_assets * random.uniform(0.1, 0.5), 2)
        net_income = round(revenue * random.uniform(-0.1, 0.25), 2)
        ebit = round(net_income * random.uniform(1.2, 2.0), 2)
        interest_expense = round(total_debt * random.uniform(0.02, 0.08), 2)

        rows.append({
            "counterparty_id": f"CP-{i + 1:03d}",
            "name": name,
            "sector": random.choice(SECTORS),
            "country": random.choice(COUNTRIES),
            "credit_rating": random.choices(
                CREDIT_RATINGS, weights=[5, 10, 20, 30, 20, 10, 5]
            )[0],
            "total_assets": total_assets,
            "current_assets": current_assets,
            "total_liabilities": total_liabilities,
            "current_liabilities": current_liabilities,
            "total_equity": total_equity,
            "total_debt": total_debt,
            "revenue": revenue,
            "net_income": net_income,
            "ebit": ebit,
            "interest_expense": interest_expense,
        })
    return rows


def generate_instruments():
    """Generate instrument master list."""
    random.seed(RANDOM_SEED + 1)
    instruments = []
    for i in range(NUM_INSTRUMENTS):
        inst_type = random.choice(INSTRUMENT_TYPES)
        prefix = {"EQUITY": "EQ", "BOND": "BD", "DERIVATIVE": "DV", "FX": "FX"}[inst_type]
        instruments.append({
            "instrument_id": f"{prefix}-{i + 1:04d}",
            "instrument_type": inst_type,
            "base_price": round(random.uniform(10, 500), 2),
            "volatility": random.uniform(0.005, 0.05),
        })
    return instruments


def generate_market_data(instruments):
    """Generate daily market prices with realistic random walks."""
    random.seed(RANDOM_SEED + 2)
    rows = []
    start_date = datetime(2025, 1, 1)

    for inst in instruments:
        price = inst["base_price"]
        for day in range(NUM_DAYS):
            date = start_date + timedelta(days=day)
            if date.weekday() >= 5:  # skip weekends
                continue

            change = price * random.gauss(0, inst["volatility"])
            price = max(0.01, price + change)
            high = price * (1 + abs(random.gauss(0, 0.01)))
            low = price * (1 - abs(random.gauss(0, 0.01)))

            rows.append({
                "instrument_id": inst["instrument_id"],
                "instrument_type": inst["instrument_type"],
                "trade_date": date.strftime("%Y-%m-%d"),
                "open_price": round(price + random.gauss(0, 0.5), 4),
                "high_price": round(high, 4),
                "low_price": round(low, 4),
                "close_price": round(price, 4),
                "volume": random.randint(1000, 1_000_000),
            })
    return rows


def generate_transactions(counterparties, instruments):
    """Generate daily trading transactions."""
    random.seed(RANDOM_SEED + 3)
    rows = []
    start_date = datetime(2025, 1, 1)
    tx_id = 0

    cp_ids = [cp["counterparty_id"] for cp in counterparties]
    inst_list = [(i["instrument_id"], i["instrument_type"], i["base_price"]) for i in instruments]

    for day in range(NUM_DAYS):
        date = start_date + timedelta(days=day)
        if date.weekday() >= 5:
            continue

        for _ in range(TRANSACTIONS_PER_DAY):
            tx_id += 1
            inst_id, inst_type, base_price = random.choice(inst_list)
            price = base_price * random.uniform(0.9, 1.1)
            quantity = random.randint(10, 10000)

            rows.append({
                "transaction_id": f"TX-{tx_id:06d}",
                "transaction_date": date.strftime("%Y-%m-%d"),
                "counterparty_id": random.choice(cp_ids),
                "instrument_id": inst_id,
                "instrument_type": inst_type,
                "direction": random.choice(DIRECTIONS),
                "quantity": quantity,
                "price": round(price, 4),
                "amount": round(price * quantity, 2),
                "currency": random.choice(CURRENCIES),
            })
    return rows


def write_csv(filename, rows):
    """Write rows to a CSV file in the seed directory."""
    filepath = os.path.join(SEED_DIR, filename)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")


def main():
    os.makedirs(SEED_DIR, exist_ok=True)
    print("Generating seed data...")

    counterparties = generate_counterparties()
    write_csv("counterparties.csv", counterparties)

    instruments = generate_instruments()
    market_data = generate_market_data(instruments)
    write_csv("market_data.csv", market_data)

    transactions = generate_transactions(counterparties, instruments)
    write_csv("transactions.csv", transactions)

    print(f"\nSeed data written to {SEED_DIR}/")
    print("Next: upload these CSVs to /Volumes/main/financial_risk/raw/ in Databricks")


if __name__ == "__main__":
    main()
