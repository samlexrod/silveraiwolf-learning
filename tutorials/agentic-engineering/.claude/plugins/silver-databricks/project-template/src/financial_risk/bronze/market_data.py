from pyspark import pipelines as sp


@sp.table(
    name="bronze_market_data",
    comment="Raw daily market prices and volumes for traded instruments",
)
def bronze_market_data():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"/Volumes/main/{schema}/raw/market_data/")
    )
