"""OpenSearch Sink — PySpark JDBC reads from Databricks, opensearch-hadoop writes to OpenSearch.

Runs as a Docker container on EC2. Fully JVM-native: Spark reads Gold tables via
JDBC from the Databricks SQL warehouse, writes to OpenSearch via the opensearch-hadoop
connector. After each sync, writes stats back to gold_opensearch_sync via JDBC.

Environment variables:
  DATABRICKS_HOST          — Workspace URL (https://dbc-xxx.cloud.databricks.com)
  DATABRICKS_TOKEN         — Personal access token
  DATABRICKS_HTTP_PATH     — SQL warehouse HTTP path (/sql/1.0/warehouses/<id>)
  SCHEMA                   — Unity Catalog schema (e.g., financial_risk_unified_samlexrod)
  CATALOG                  — Unity Catalog catalog (default: main)
  OPENSEARCH_ENDPOINT      — OpenSearch domain (without https://)
  OPENSEARCH_USER          — Master username (default: admin)
  OPENSEARCH_PASSWORD      — Master password
  SINK_INTERVAL_SECONDS    — Seconds between sync runs (default: 900, 0 = one-shot)
"""

import glob
import os
import sys
import time
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql.types import DecimalType, LongType, StringType, StructField, StructType, TimestampType

# Gold table → (OpenSearch index, ID field for upsert)
GOLD_TO_INDEX = {
    # Cross-domain analytics
    "gold_risk_dashboard": ("risk-dashboard", "counterparty_id"),
    "gold_regulatory_report": ("regulatory-report", "counterparty_id"),
    "gold_desk_pnl_exposure": ("desk-pnl-exposure", "desk_id"),
    # Financial domain
    "gold_financial_ratios": ("financial-ratios", "counterparty_id"),
    "gold_portfolio_summary": ("portfolio-summary", "sector"),
    # Counterparty domain
    "gold_counterparty_health": ("counterparty-health", "counterparty_id"),
    # Operations domain
    "gold_desk_overview": ("desk-overview", "desk_id"),
    # Compliance domain
    "gold_compliance_status": ("compliance-status", "counterparty_id"),
    # Market reference domain
    "gold_reference_rates": ("reference-rates", "pair"),
    # Regulatory domain
    "gold_regulatory_metrics": ("regulatory-metrics", "regulation_name"),
}

SYNC_TABLE = "gold_opensearch_sync"

SYNC_SCHEMA = StructType(
    [
        StructField("gold_table", StringType(), False),
        StructField("opensearch_index", StringType(), False),
        StructField("doc_count", LongType(), False),
        StructField("status", StringType(), False),
        StructField("synced_at", TimestampType(), False),
    ]
)


def create_spark_session():
    """Create a local Spark session with JDBC + opensearch-hadoop JARs."""
    jars = glob.glob("/app/jars/*.jar")
    return (
        SparkSession.builder.master("local[*]")
        .appName("opensearch-sink")
        .config("spark.jars", ",".join(jars))
        .config("spark.driver.memory", "512m")
        .getOrCreate()
    )


def get_jdbc_options():
    """Build JDBC connection options for the Databricks SQL warehouse."""
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]
    return {
        "url": (
            f"jdbc:databricks://{host}:443/default;"
            f"transportMode=http;ssl=1;"
            f"httpPath={http_path};"
            f"AuthMech=3;UID=token;PWD={token}"
        ),
        "driver": "com.databricks.client.jdbc.Driver",
    }


def get_opensearch_options():
    """Build opensearch-hadoop connector options."""
    endpoint = os.environ["OPENSEARCH_ENDPOINT"]
    user = os.environ.get("OPENSEARCH_USER", "admin")
    password = os.environ["OPENSEARCH_PASSWORD"]
    return {
        "opensearch.nodes": endpoint,
        "opensearch.port": "443",
        "opensearch.net.ssl": "true",
        "opensearch.nodes.wan.only": "true",
        "opensearch.net.http.auth.user": user,
        "opensearch.net.http.auth.pass": password,
        "opensearch.write.operation": "upsert",
        "opensearch.nodes.resolve.hostname": "false",
        "opensearch.batch.size.entries": "1000",
        "opensearch.batch.write.refresh": "true",
    }


def cast_decimals(df):
    """Cast Decimal columns to Double — opensearch-hadoop can't handle BigDecimal."""
    for field in df.schema.fields:
        if isinstance(field.dataType, DecimalType):
            df = df.withColumn(field.name, df[field.name].cast("double"))
    return df


# Tables with ARRAY columns — JDBC can't handle ARRAY types, so we push down
# a query that casts them to strings server-side before JDBC reads the result
ARRAY_CAST_QUERIES = {
    "gold_counterparty_health": "SELECT * EXCEPT(trends), CAST(trends AS STRING) AS trends FROM {fqn}",
    "gold_desk_overview": "SELECT * EXCEPT(instruments_covered), CAST(instruments_covered AS STRING) AS instruments_covered FROM {fqn}",
}


def sync_table(spark, table_name, index_name, id_field, jdbc_opts, os_opts, catalog, schema):
    """Read a Gold table via JDBC and write to OpenSearch via opensearch-hadoop."""
    fqn = f"{catalog}.{schema}.{table_name}"

    if table_name in ARRAY_CAST_QUERIES:
        query = f"({ARRAY_CAST_QUERIES[table_name].format(fqn=fqn)}) AS t"
        df = spark.read.format("jdbc").options(**jdbc_opts).option("dbtable", query).load()
    else:
        df = spark.read.format("jdbc").options(**jdbc_opts).option("dbtable", fqn).load()

    df = cast_decimals(df)
    df = df.filter(f"{id_field} IS NOT NULL")

    count = df.count()
    if count == 0:
        return 0

    (
        df.write.format("opensearch")
        .options(**os_opts)
        .option("opensearch.mapping.id", id_field)
        .option("opensearch.resource", index_name)
        .mode("overwrite")
        .save()
    )

    return count


def write_sync_stats(spark, sync_results, jdbc_opts, catalog, schema):
    """Write sync results back to gold_opensearch_sync via JDBC."""
    fqn = f"{catalog}.{schema}.{SYNC_TABLE}"

    df = spark.createDataFrame(sync_results, SYNC_SCHEMA)

    (
        df.write.format("jdbc")
        .options(**jdbc_opts)
        .option("dbtable", fqn)
        .option("createTableColumnTypes", (
            "gold_table STRING, opensearch_index STRING, "
            "doc_count BIGINT, status STRING, synced_at TIMESTAMP"
        ))
        .mode("overwrite")
        .save()
    )


def run_sync(spark, jdbc_opts, os_opts, catalog, schema):
    """One sync pass: read all Gold tables, write to OpenSearch, record stats."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{ts}] Syncing Gold → OpenSearch", flush=True)
    print(f"  Source: {catalog}.{schema}", flush=True)
    print(f"  Target: {os_opts['opensearch.nodes']}", flush=True)

    total = 0
    sync_results = []

    for table_name, (index_name, id_field) in GOLD_TO_INDEX.items():
        try:
            count = sync_table(
                spark, table_name, index_name, id_field, jdbc_opts, os_opts, catalog, schema
            )
            total += count
            sync_results.append((table_name, index_name, count, "OK", now))
            print(f"  {table_name:35s} → {index_name:25s} {count:>4d} docs", flush=True)
        except Exception as exc:
            sync_results.append((table_name, index_name, -1, str(exc)[:200], now))
            print(f"  {table_name:35s} → FAILED: {exc}", flush=True)

    # Write sync stats back to Databricks
    try:
        write_sync_stats(spark, sync_results, jdbc_opts, catalog, schema)
        print(f"  Stats written to {catalog}.{schema}.{SYNC_TABLE}", flush=True)
    except Exception as exc:
        print(f"  Stats write failed: {exc}", flush=True)

    print(f"  Total: {total} docs indexed", flush=True)
    return total


def main():
    interval = int(os.getenv("SINK_INTERVAL_SECONDS", "900"))

    for var in [
        "DATABRICKS_HOST",
        "DATABRICKS_TOKEN",
        "DATABRICKS_HTTP_PATH",
        "SCHEMA",
        "OPENSEARCH_ENDPOINT",
        "OPENSEARCH_PASSWORD",
    ]:
        if not os.environ.get(var):
            print(f"ERROR: Missing env var: {var}", file=sys.stderr, flush=True)
            sys.exit(1)

    spark = create_spark_session()
    jdbc_opts = get_jdbc_options()
    os_opts = get_opensearch_options()
    catalog = os.getenv("CATALOG", "main")
    schema = os.environ["SCHEMA"]

    if interval == 0:
        run_sync(spark, jdbc_opts, os_opts, catalog, schema)
    else:
        print(f"OpenSearch Sink starting (interval: {interval}s)", flush=True)
        while True:
            try:
                run_sync(spark, jdbc_opts, os_opts, catalog, schema)
            except Exception as exc:
                print(f"Sync failed: {exc}", flush=True)
            time.sleep(interval)

    spark.stop()


if __name__ == "__main__":
    main()
