"""Create Gold tables with synthetic financial data.

Uses the Databricks SDK to create tables in Unity Catalog and insert
synthetic data from seed_gold_data.py. Idempotent: checks if tables
exist before creating.

Usage:
    python data/bootstrap/create_gold_tables.py --catalog main --schema financial_risk
"""

from __future__ import annotations

import argparse
import logging
import sys

from databricks.sdk import WorkspaceClient

from seed_gold_data import (
    FINANCIAL_RATIOS_DATA,
    PORTFOLIO_HOLDINGS_DATA,
    PORTFOLIO_SUMMARY_DATA,
    PORTFOLIOS_DATA,
    RISK_EXPOSURE_DATA,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _table_exists(w: WorkspaceClient, full_name: str) -> bool:
    """Check if a table exists in Unity Catalog."""
    try:
        w.tables.get(full_name)
        return True
    except Exception:
        return False


def _execute_sql(w: WorkspaceClient, sql: str) -> None:
    """Execute a SQL statement via the Databricks SDK."""
    w.statement_execution.execute_statement(
        warehouse_id=_get_warehouse_id(w),
        statement=sql,
    )


def _get_warehouse_id(w: WorkspaceClient) -> str:
    """Get the first available SQL warehouse ID."""
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found. Create one in the Databricks workspace.")
    return warehouses[0].id


def create_risk_exposure_table(w: WorkspaceClient, catalog: str, schema: str) -> None:
    """Create and populate the gold_risk_exposure table."""
    table_name = f"{catalog}.{schema}.gold_risk_exposure"

    if _table_exists(w, table_name):
        logger.info("Table %s already exists — skipping", table_name)
        return

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            counterparty_name STRING NOT NULL,
            risk_tier STRING NOT NULL,
            total_exposure_usd DOUBLE NOT NULL,
            credit_rating STRING NOT NULL,
            default_probability DOUBLE NOT NULL,
            sector STRING,
            country STRING,
            last_updated DATE
        )
        COMMENT 'Gold table: counterparty risk exposure metrics'
    """
    _execute_sql(w, create_sql)
    logger.info("Created table %s", table_name)

    # Insert rows
    for row in RISK_EXPOSURE_DATA:
        insert_sql = f"""
            INSERT INTO {table_name} VALUES (
                '{row["counterparty_name"]}',
                '{row["risk_tier"]}',
                {row["total_exposure_usd"]},
                '{row["credit_rating"]}',
                {row["default_probability"]},
                '{row["sector"]}',
                '{row["country"]}',
                '{row["last_updated"]}'
            )
        """
        _execute_sql(w, insert_sql)

    logger.info("Inserted %d rows into %s", len(RISK_EXPOSURE_DATA), table_name)


def create_financial_ratios_table(w: WorkspaceClient, catalog: str, schema: str) -> None:
    """Create and populate the gold_financial_ratios table."""
    table_name = f"{catalog}.{schema}.gold_financial_ratios"

    if _table_exists(w, table_name):
        logger.info("Table %s already exists — skipping", table_name)
        return

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            counterparty_name STRING NOT NULL,
            debt_to_equity DOUBLE NOT NULL,
            current_ratio DOUBLE NOT NULL,
            interest_coverage DOUBLE NOT NULL,
            return_on_equity DOUBLE NOT NULL,
            revenue_growth_pct DOUBLE NOT NULL,
            last_updated DATE
        )
        COMMENT 'Gold table: counterparty financial health ratios'
    """
    _execute_sql(w, create_sql)
    logger.info("Created table %s", table_name)

    for row in FINANCIAL_RATIOS_DATA:
        insert_sql = f"""
            INSERT INTO {table_name} VALUES (
                '{row["counterparty_name"]}',
                {row["debt_to_equity"]},
                {row["current_ratio"]},
                {row["interest_coverage"]},
                {row["return_on_equity"]},
                {row["revenue_growth_pct"]},
                '{row["last_updated"]}'
            )
        """
        _execute_sql(w, insert_sql)

    logger.info("Inserted %d rows into %s", len(FINANCIAL_RATIOS_DATA), table_name)


def create_portfolio_summary_table(w: WorkspaceClient, catalog: str, schema: str) -> None:
    """Create and populate the gold_portfolio_summary table."""
    table_name = f"{catalog}.{schema}.gold_portfolio_summary"

    if _table_exists(w, table_name):
        logger.info("Table %s already exists — skipping", table_name)
        return

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            sector STRING NOT NULL,
            num_counterparties INT NOT NULL,
            total_exposure_usd DOUBLE NOT NULL,
            concentration_pct DOUBLE NOT NULL,
            avg_risk_score DOUBLE NOT NULL,
            dominant_risk_tier STRING NOT NULL
        )
        COMMENT 'Gold table: portfolio concentration by sector'
    """
    _execute_sql(w, create_sql)
    logger.info("Created table %s", table_name)

    for row in PORTFOLIO_SUMMARY_DATA:
        insert_sql = f"""
            INSERT INTO {table_name} VALUES (
                '{row["sector"]}',
                {row["num_counterparties"]},
                {row["total_exposure_usd"]},
                {row["concentration_pct"]},
                {row["avg_risk_score"]},
                '{row["dominant_risk_tier"]}'
            )
        """
        _execute_sql(w, insert_sql)

    logger.info("Inserted %d rows into %s", len(PORTFOLIO_SUMMARY_DATA), table_name)


def create_portfolios_table(w: WorkspaceClient, catalog: str, schema: str) -> None:
    """Create and populate the gold_portfolios table."""
    table_name = f"{catalog}.{schema}.gold_portfolios"

    if _table_exists(w, table_name):
        logger.info("Table %s already exists — skipping", table_name)
        return

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            portfolio_id STRING NOT NULL,
            portfolio_name STRING NOT NULL,
            strategy STRING NOT NULL,
            manager STRING,
            created_date DATE
        )
        COMMENT 'Gold table: portfolio definitions'
    """
    _execute_sql(w, create_sql)
    logger.info("Created table %s", table_name)

    for row in PORTFOLIOS_DATA:
        insert_sql = f"""
            INSERT INTO {table_name} VALUES (
                '{row["portfolio_id"]}',
                '{row["portfolio_name"]}',
                '{row["strategy"]}',
                '{row["manager"]}',
                '{row["created_date"]}'
            )
        """
        _execute_sql(w, insert_sql)

    logger.info("Inserted %d rows into %s", len(PORTFOLIOS_DATA), table_name)


def create_portfolio_holdings_table(w: WorkspaceClient, catalog: str, schema: str) -> None:
    """Create and populate the gold_portfolio_holdings table."""
    table_name = f"{catalog}.{schema}.gold_portfolio_holdings"

    if _table_exists(w, table_name):
        logger.info("Table %s already exists — skipping", table_name)
        return

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            portfolio_id STRING NOT NULL,
            counterparty_name STRING NOT NULL,
            allocation_pct DOUBLE NOT NULL,
            position_type STRING NOT NULL
        )
        COMMENT 'Gold table: portfolio-to-counterparty holdings with allocation percentages'
    """
    _execute_sql(w, create_sql)
    logger.info("Created table %s", table_name)

    for row in PORTFOLIO_HOLDINGS_DATA:
        insert_sql = f"""
            INSERT INTO {table_name} VALUES (
                '{row["portfolio_id"]}',
                '{row["counterparty_name"]}',
                {row["allocation_pct"]},
                '{row["position_type"]}'
            )
        """
        _execute_sql(w, insert_sql)

    logger.info("Inserted %d rows into %s", len(PORTFOLIO_HOLDINGS_DATA), table_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Gold tables with synthetic data")
    parser.add_argument("--catalog", default="main", help="Unity Catalog name (default: main)")
    parser.add_argument("--schema", default="financial_risk", help="Schema name (default: financial_risk)")
    args = parser.parse_args()

    w = WorkspaceClient()
    logger.info("Connected to Databricks workspace")

    # Ensure schema exists
    _execute_sql(w, f"CREATE SCHEMA IF NOT EXISTS {args.catalog}.{args.schema}")
    logger.info("Schema %s.%s ready", args.catalog, args.schema)

    create_risk_exposure_table(w, args.catalog, args.schema)
    create_financial_ratios_table(w, args.catalog, args.schema)
    create_portfolio_summary_table(w, args.catalog, args.schema)
    create_portfolios_table(w, args.catalog, args.schema)
    create_portfolio_holdings_table(w, args.catalog, args.schema)

    logger.info("All Gold tables created successfully")


if __name__ == "__main__":
    main()
