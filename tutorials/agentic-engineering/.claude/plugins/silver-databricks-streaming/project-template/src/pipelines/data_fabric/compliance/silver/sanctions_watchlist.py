import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_sanctions_watchlist",
    comment="Cleaned sanctions watchlist — validated entity types, statuses, and source lists",
)
@sp.expect("valid_entity_id", "entity_id IS NOT NULL")
@sp.expect("valid_entity_type", "entity_type IN ('INDIVIDUAL', 'ORGANIZATION')")
@sp.expect("valid_source_list", "source_list IN ('OFAC', 'EU', 'UN')")
@sp.expect("valid_status", "status IN ('ACTIVE', 'DELISTED')")
def silver_sanctions_watchlist():
    return (
        sp.read_stream("bronze_sanctions_watchlist")
        .select(
            F.col("entity_id").cast("string"),
            F.trim(F.col("entity_name")).alias("entity_name"),
            F.trim(F.upper(F.col("entity_type"))).alias("entity_type"),
            F.trim(F.upper(F.col("source_list"))).alias("source_list"),
            F.trim(F.upper(F.col("country"))).alias("country"),
            F.col("match_score").cast("double"),
            F.trim(F.upper(F.col("status"))).alias("status"),
            F.col("listed_date").cast("date"),
            F.col("delisted_date").cast("date"),
            F.col("last_checked").cast("timestamp"),
            F.col("ingested_at"),
        )
        .dropDuplicates(["entity_id"])
    )
