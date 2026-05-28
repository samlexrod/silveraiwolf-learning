"""Index Gold tables into OpenSearch using the opensearch-hadoop Spark connector.

Uses df.write.format("opensearch") — the Spark-native approach via opensearch-spark-30_2.12.
No Python REST client needed. Spark handles serialization, partitioning, and bulk indexing.

Schedule: Triggered after pipeline completes (or on a 15-minute interval)
Requires: opensearch-spark-30_2.12 JAR (added via Maven coordinates in databricks.yml)

Indexes:
  - risk-dashboard     ← gold_risk_dashboard
  - regulatory-report  ← gold_regulatory_report
  - desk-pnl-exposure  ← gold_desk_pnl_exposure
  - financial-ratios   ← gold_financial_ratios
  - compliance-status  ← gold_compliance_status
"""

import os

from pyspark.sql import SparkSession

# Gold table → OpenSearch index mapping with ID fields for upsert
GOLD_TABLES = {
    "gold_risk_dashboard": {
        "index": "risk-dashboard",
        "id_field": "counterparty_id",
    },
    "gold_regulatory_report": {
        "index": "regulatory-report",
        "id_field": "counterparty_id",
    },
    "gold_desk_pnl_exposure": {
        "index": "desk-pnl-exposure",
        "id_field": "desk_id",
    },
    "gold_financial_ratios": {
        "index": "financial-ratios",
        "id_field": "counterparty_id",
    },
    "gold_compliance_status": {
        "index": "compliance-status",
        "id_field": "entity_id",
    },
}


def get_opensearch_options():
    """Build opensearch-hadoop connector options from environment variables."""
    endpoint = os.environ["OPENSEARCH_ENDPOINT"]
    user = os.environ.get("OPENSEARCH_USER", "admin")
    password = os.environ["OPENSEARCH_PASSWORD"]

    # Parse host from endpoint URL (opensearch-hadoop expects host without scheme)
    host = endpoint.replace("https://", "").replace("http://", "").rstrip("/")

    return {
        "opensearch.nodes": host,
        "opensearch.port": "443",
        "opensearch.net.ssl": "true",
        "opensearch.nodes.wan.only": "true",
        "opensearch.net.http.auth.user": user,
        "opensearch.net.http.auth.pass": password,
        # Write settings
        "opensearch.write.operation": "upsert",
        "opensearch.nodes.resolve.hostname": "false",
        "opensearch.batch.size.entries": "1000",
        "opensearch.batch.write.refresh": "true",
    }


def index_gold_table(spark, table_name, config, catalog, schema, os_options):
    """Read a Gold table and write to OpenSearch via opensearch-hadoop connector."""
    index_name = config["index"]
    id_field = config["id_field"]

    df = spark.sql(f"SELECT * FROM {catalog}.{schema}.{table_name}")
    row_count = df.count()

    if row_count == 0:
        print(f"  Skipping {table_name} — no data")
        return 0

    # Cast Decimal columns to Double (opensearch-hadoop doesn't handle Java BigDecimal)
    from pyspark.sql.types import DecimalType

    for field in df.schema.fields:
        if isinstance(field.dataType, DecimalType):
            df = df.withColumn(field.name, df[field.name].cast("double"))

    # Write to OpenSearch using the opensearch-hadoop Spark connector
    (
        df.write.format("opensearch")
        .options(**os_options)
        .option("opensearch.mapping.id", id_field)
        .option("opensearch.resource", index_name)
        .mode("overwrite")
        .save()
    )

    print(f"  Indexed {row_count} rows → {index_name}")
    return row_count


def main():
    """Index all Gold tables into OpenSearch via opensearch-hadoop Spark connector."""
    spark = SparkSession.builder.getOrCreate()

    catalog = os.getenv("CATALOG", "main")
    schema = os.getenv("SCHEMA", "financial_risk_streaming")
    os_options = get_opensearch_options()

    host = os_options["opensearch.nodes"]
    print(f"OpenSearch target: {host}")
    print(f"Source: {catalog}.{schema}\n")

    total = 0
    for table_name, config in GOLD_TABLES.items():
        print(f"Indexing {table_name} → {config['index']}...")
        try:
            count = index_gold_table(spark, table_name, config, catalog, schema, os_options)
            total += count
        except Exception as e:
            print(f"  Failed: {e}")

    print(f"\nDone. Indexed {total} total documents across {len(GOLD_TABLES)} indices.")


if __name__ == "__main__":
    main()
