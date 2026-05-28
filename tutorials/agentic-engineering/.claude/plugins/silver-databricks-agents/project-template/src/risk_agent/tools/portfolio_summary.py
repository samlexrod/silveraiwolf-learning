"""Unity Catalog function wrapper for get_portfolio_summary."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "356c99be7a00b406")


def get_portfolio_summary() -> list[dict[str, Any]]:
    """Query the full portfolio summary grouped by sector."""
    import time

    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()

            query = "SELECT * FROM main.financial_risk.get_portfolio_summary()"

            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=query,
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
                return [{"error": "No portfolio summary data found"}]

            columns = [col.name for col in result.manifest.schema.columns]
            return [dict(zip(columns, row)) for row in result.result.data_array]

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query portfolio summary")
            return [{"error": str(e)}]

    return [{"error": "No portfolio summary data found after retries"}]
