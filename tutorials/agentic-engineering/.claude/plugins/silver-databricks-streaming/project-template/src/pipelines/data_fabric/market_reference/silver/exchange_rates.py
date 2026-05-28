import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_exchange_rates",
    comment="Cleaned exchange rates — validated currencies and sources",
)
@sp.expect("valid_rate_id", "rate_id IS NOT NULL")
@sp.expect("valid_rate", "rate > 0")
@sp.expect("valid_source", "source IN ('ECB', 'FED', 'BOE')")
def silver_exchange_rates():
    return (
        sp.read_stream("bronze_exchange_rates")
        .select(
            F.col("rate_id").cast("string"),
            F.trim(F.upper(F.col("base_currency"))).alias("base_currency"),
            F.trim(F.upper(F.col("quote_currency"))).alias("quote_currency"),
            F.col("rate").cast("double"),
            F.col("rate_date").cast("date"),
            F.trim(F.upper(F.col("source"))).alias("source"),
            F.col("ingested_at"),
        )
        .dropDuplicates(["rate_id"])
    )
