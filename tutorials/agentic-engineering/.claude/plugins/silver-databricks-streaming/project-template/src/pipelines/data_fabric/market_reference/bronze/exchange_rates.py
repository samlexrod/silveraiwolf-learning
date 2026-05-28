import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

exchange_rate_schema = T.StructType(
    [
        T.StructField("rate_id", T.StringType()),
        T.StructField("base_currency", T.StringType()),
        T.StructField("quote_currency", T.StringType()),
        T.StructField("rate", T.DoubleType()),
        T.StructField("rate_date", T.StringType()),
        T.StructField("source", T.StringType()),
    ]
)


@sp.table(
    name="bronze_exchange_rates",
    comment="Raw exchange rates ingested from API landing zone via Auto Loader",
)
def bronze_exchange_rates():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    catalog = spark.conf.get("pipeline.catalog", "main")  # noqa: F821

    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "json")
        .option(
            "cloudFiles.schemaLocation",
            f"/Volumes/{catalog}/{schema}/checkpoints/bronze_exchange_rates",
        )
        .schema(exchange_rate_schema)
        .load(f"/Volumes/{catalog}/{schema}/landing/market_reference/exchange_rates/")
        .select("*", F.current_timestamp().alias("ingested_at"))
    )
