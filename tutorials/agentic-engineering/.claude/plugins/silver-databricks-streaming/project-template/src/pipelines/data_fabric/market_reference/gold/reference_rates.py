import pyspark.sql.functions as F
from pyspark import pipelines as sp
from pyspark.sql import Window


@sp.table(
    name="gold_reference_rates",
    comment="Latest FX and benchmark rates with rate changes",
)
def gold_reference_rates():
    fx = sp.read("silver_exchange_rates")
    benchmarks = sp.read("silver_benchmark_rates")

    # Latest FX rate per currency pair
    fx_window = Window.partitionBy("base_currency", "quote_currency").orderBy(F.desc("rate_date"))
    latest_fx = (
        fx.withColumn("rn", F.row_number().over(fx_window))
        .filter(F.col("rn") == 1)
        .select(
            F.concat_ws("/", "base_currency", "quote_currency").alias("pair"),
            F.lit("FX").alias("rate_type"),
            "rate",
            F.col("rate_date").alias("effective_date"),
            "source",
        )
    )

    # Latest benchmark rate per benchmark
    bm_window = Window.partitionBy("benchmark_name").orderBy(F.desc("effective_date"))
    latest_bm = (
        benchmarks.withColumn("rn", F.row_number().over(bm_window))
        .filter(F.col("rn") == 1)
        .select(
            F.col("benchmark_name").alias("pair"),
            F.lit("BENCHMARK").alias("rate_type"),
            "rate",
            "effective_date",
            "source",
        )
    )

    return latest_fx.unionByName(latest_bm)
