import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

benchmark_rate_schema = T.StructType(
    [
        T.StructField("rate_id", T.StringType()),
        T.StructField("benchmark_name", T.StringType()),
        T.StructField("rate", T.DoubleType()),
        T.StructField("effective_date", T.StringType()),
        T.StructField("source", T.StringType()),
    ]
)


@sp.table(
    name="bronze_benchmark_rates",
    comment="Raw benchmark rates ingested from API landing zone via Auto Loader",
)
def bronze_benchmark_rates():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    catalog = spark.conf.get("pipeline.catalog", "main")  # noqa: F821

    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "json")
        .option(
            "cloudFiles.schemaLocation",
            f"/Volumes/{catalog}/{schema}/checkpoints/bronze_benchmark_rates",
        )
        .schema(benchmark_rate_schema)
        .load(f"/Volumes/{catalog}/{schema}/landing/market_reference/benchmark_rates/")
        .select("*", F.current_timestamp().alias("ingested_at"))
    )
