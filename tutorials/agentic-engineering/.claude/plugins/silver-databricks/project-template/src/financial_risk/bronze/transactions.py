from pyspark import pipelines as sp


@sp.table(
    name="bronze_transactions",
    comment="Raw financial transactions ingested from CSV source",
)
def bronze_transactions():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"/Volumes/main/{schema}/raw/transactions/")
    )
