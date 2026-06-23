"""Tiny SQL runner for the Free Edition Starter Warehouse — `mise run sql '<statement>'`.

Reads DATABRICKS_HOST + DATABRICKS_WAREHOUSE_ID from the environment (.env via mise). Auth is OAuth U2M by
default: it reuses the cached token from `databricks auth login` (the `free` profile) — no PAT needed. If
DATABRICKS_TOKEN is set in the shell, it uses that instead. Uses databricks-sql-connector; prints rows as TSV.
"""

from __future__ import annotations

import os
import sys

from databricks import sql


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: mise run sql '<SQL statement>'", file=sys.stderr)
        return 2
    statement = sys.argv[1]
    host = os.environ.get("DATABRICKS_HOST", "").strip().replace("https://", "").rstrip("/")
    wid = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if not (host and wid):
        print("✗ need DATABRICKS_HOST + DATABRICKS_WAREHOUSE_ID (.env)", file=sys.stderr)
        return 1

    http_path = f"/sql/1.0/warehouses/{wid}"
    catalog = os.environ.get("DATABRICKS_CATALOG", "silverline").strip()
    if token:
        conn_ctx = sql.connect(
            server_hostname=host, http_path=http_path, access_token=token, catalog=catalog
        )
    else:
        # OAuth U2M — reuse the cached creds from `databricks auth login --profile free`.
        from databricks.sdk.core import Config

        profile = os.environ.get("DATABRICKS_CONFIG_PROFILE", "free")
        cfg = Config(host=f"https://{host}", profile=profile)
        conn_ctx = sql.connect(
            server_hostname=host,
            http_path=http_path,
            credentials_provider=lambda: cfg.authenticate,
            catalog=catalog,
        )

    with conn_ctx as conn, conn.cursor() as cur:
        cur.execute(statement)
        if cur.description:
            cols = [c[0] for c in cur.description]
            print("\t".join(cols))
            for row in cur.fetchall():
                print("\t".join("" if v is None else str(v) for v in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
