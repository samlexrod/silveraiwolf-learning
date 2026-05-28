"""Unity Catalog function wrapper for get_financial_ratios."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "356c99be7a00b406")


def get_financial_ratios(counterparty_name: str) -> dict[str, Any]:
    """Query financial ratios for a given counterparty."""
    import time

    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()

            query = f"SELECT * FROM main.financial_risk.get_financial_ratios('{counterparty_name}')"

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
                    return {"error": f"Query failed: {err}"}

            if not result.result or not result.result.data_array:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return {"error": f"No financial ratio data found for '{counterparty_name}'"}

            row = result.result.data_array[0]
            columns = [col.name for col in result.manifest.schema.columns]
            return dict(zip(columns, row))

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query financial ratios for '%s'", counterparty_name)
            return {"error": str(e)}

    return {"error": f"No financial ratio data found for '{counterparty_name}' after retries"}
