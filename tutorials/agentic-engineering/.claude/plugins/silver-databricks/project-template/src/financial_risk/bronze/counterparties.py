from pyspark import pipelines as sp


@sp.table(
    name="bronze_counterparties",
    comment="Raw counterparty master data with financial statements",
)
def bronze_counterparties():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    return (
        spark.read.format("csv")  # noqa: F821
        .option("header", "true")
        .option("inferSchema", "true")
        .load(f"/Volumes/main/{schema}/raw/counterparties/")
    )
