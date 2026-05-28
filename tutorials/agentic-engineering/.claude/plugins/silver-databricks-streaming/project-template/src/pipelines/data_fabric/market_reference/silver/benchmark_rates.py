import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_benchmark_rates",
    comment="Cleaned benchmark rates — validated benchmark names and sources",
)
@sp.expect("valid_rate_id", "rate_id IS NOT NULL")
@sp.expect("valid_rate", "rate IS NOT NULL")
@sp.expect("valid_benchmark", "benchmark_name IN ('SOFR', 'ESTR', 'SONIA', 'TONAR')")
def silver_benchmark_rates():
    return (
        sp.read_stream("bronze_benchmark_rates")
        .select(
            F.col("rate_id").cast("string"),
            F.trim(F.upper(F.col("benchmark_name"))).alias("benchmark_name"),
            F.col("rate").cast("double"),
            F.col("effective_date").cast("date"),
            F.trim(F.upper(F.col("source"))).alias("source"),
            F.col("ingested_at"),
        )
        .dropDuplicates(["rate_id"])
    )
