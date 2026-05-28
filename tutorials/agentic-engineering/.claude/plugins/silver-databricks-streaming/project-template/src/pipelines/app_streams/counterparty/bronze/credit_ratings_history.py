import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="bronze_cdc_credit_ratings_history",
    comment="Raw CDC events from PostgreSQL credit_ratings_history table via Kafka",
)
def bronze_cdc_credit_ratings_history():
    bootstrap_servers = spark.conf.get("kafka_options.bootstrap_servers")  # noqa: F821

    return (
        spark.readStream.format("kafka")  # noqa: F821
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", "postgres.public.credit_ratings_history")
        .option("startingOffsets", "earliest")
        .option(
            "kafka.security.protocol",
            spark.conf.get("kafka_options.security_protocol", "PLAINTEXT"),  # noqa: F821
        )
        .load()
        .select(
            F.col("key").cast("string").alias("kafka_key"),
            F.col("value").cast("string").alias("kafka_value"),
            F.col("topic"),
            F.col("partition"),
            F.col("offset"),
            F.col("timestamp").alias("kafka_timestamp"),
            F.current_timestamp().alias("ingested_at"),
        )
    )
