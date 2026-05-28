"""Unity Catalog function wrappers for portfolio operations."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "356c99be7a00b406")


def get_portfolios() -> list[dict[str, Any]]:
    """List all available portfolios."""
    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement="SELECT * FROM main.financial_risk.get_portfolios()",
                wait_timeout="50s",
            )

            if result.status and result.status.state:
                state = str(result.status.state)
                if "FAILED" in state:
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    err = result.status.error.message if result.status.error else "Unknown error"
                    return [{"error": f"Query failed: {err}"}]

            if not result.result or not result.result.data_array:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return [{"error": "No portfolios found"}]

            columns = [col.name for col in result.manifest.schema.columns]
            return [dict(zip(columns, row)) for row in result.result.data_array]

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query portfolios")
            return [{"error": str(e)}]

    return [{"error": "No portfolios found after retries"}]


def get_portfolio_counterparties(portfolio_id: str) -> list[dict[str, Any]]:
    """Get all counterparties in a portfolio with their risk data."""
    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=f"SELECT * FROM main.financial_risk.get_portfolio_counterparties('{portfolio_id}')",
                wait_timeout="50s",
            )

            if result.status and result.status.state:
                state = str(result.status.state)
                if "FAILED" in state:
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    err = result.status.error.message if result.status.error else "Unknown error"
                    return [{"error": f"Query failed: {err}"}]

            if not result.result or not result.result.data_array:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return [{"error": f"No counterparties found for portfolio '{portfolio_id}'"}]

            columns = [col.name for col in result.manifest.schema.columns]
            return [dict(zip(columns, row)) for row in result.result.data_array]

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query portfolio counterparties for '%s'", portfolio_id)
            return [{"error": str(e)}]

    return [{"error": f"No counterparties found for portfolio '{portfolio_id}' after retries"}]


def get_portfolio_financial_health(portfolio_id: str) -> list[dict[str, Any]]:
    """Get all counterparties in a portfolio with risk exposure AND financial ratios in one call."""
    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=f"SELECT * FROM main.financial_risk.get_portfolio_financial_health('{portfolio_id}')",
                wait_timeout="50s",
            )

            if result.status and result.status.state:
                state = str(result.status.state)
                if "FAILED" in state:
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    err = result.status.error.message if result.status.error else "Unknown error"
                    return [{"error": f"Query failed: {err}"}]

            if not result.result or not result.result.data_array:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return [{"error": f"No data found for portfolio '{portfolio_id}'"}]

            columns = [col.name for col in result.manifest.schema.columns]
            return [dict(zip(columns, row)) for row in result.result.data_array]

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query portfolio financial health for '%s'", portfolio_id)
            return [{"error": str(e)}]

    return [{"error": f"No data found for portfolio '{portfolio_id}' after retries"}]
