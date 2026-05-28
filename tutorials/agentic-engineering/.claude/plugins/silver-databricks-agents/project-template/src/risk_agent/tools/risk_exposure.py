"""Unity Catalog function wrapper for get_risk_exposure."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "356c99be7a00b406")


def get_risk_exposure(counterparty_name: str) -> dict[str, Any]:
    """Query risk exposure data for a given counterparty."""
    import time

    for attempt in range(3):
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()

            query = f"SELECT * FROM main.financial_risk.get_risk_exposure('{counterparty_name}')"

            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=query,
                wait_timeout="50s",
            )

            # Check execution status
            if result.status and result.status.state:
                state = str(result.status.state)
                if "FAILED" in state:
                    err = result.status.error.message if result.status.error else "Unknown error"
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return {"error": f"Query failed: {err}"}

            if not result.result or not result.result.data_array:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return {"error": f"No risk exposure data found for '{counterparty_name}'"}

            row = result.result.data_array[0]
            columns = [col.name for col in result.manifest.schema.columns]
            return dict(zip(columns, row))

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            logger.exception("Failed to query risk exposure for '%s'", counterparty_name)
            return {"error": str(e)}

    return {"error": f"No risk exposure data found for '{counterparty_name}' after retries"}
