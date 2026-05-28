import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

sanctions_schema = T.StructType(
    [
        T.StructField("entity_id", T.StringType()),
        T.StructField("entity_name", T.StringType()),
        T.StructField("entity_type", T.StringType()),
        T.StructField("source_list", T.StringType()),
        T.StructField("country", T.StringType()),
        T.StructField("match_score", T.DoubleType()),
        T.StructField("status", T.StringType()),
        T.StructField("listed_date", T.StringType()),
        T.StructField("delisted_date", T.StringType()),
        T.StructField("last_checked", T.StringType()),
    ]
)


@sp.table(
    name="bronze_sanctions_watchlist",
    comment="Raw sanctions watchlist ingested from API landing zone via Auto Loader",
)
def bronze_sanctions_watchlist():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    catalog = spark.conf.get("pipeline.catalog", "main")  # noqa: F821

    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "json")
        .option(
            "cloudFiles.schemaLocation",
            f"/Volumes/{catalog}/{schema}/checkpoints/bronze_sanctions_watchlist",
        )
        .schema(sanctions_schema)
        .load(f"/Volumes/{catalog}/{schema}/landing/compliance/sanctions_watchlist/")
        .select("*", F.current_timestamp().alias("ingested_at"))
    )
