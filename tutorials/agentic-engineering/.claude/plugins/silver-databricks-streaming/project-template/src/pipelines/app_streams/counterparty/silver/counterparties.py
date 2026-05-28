import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

counterparty_schema = T.StructType(
    [
        T.StructField("counterparty_id", T.StringType()),
        T.StructField("name", T.StringType()),
        T.StructField("sector", T.StringType()),
        T.StructField("country", T.StringType()),
        T.StructField("credit_rating", T.StringType()),
        T.StructField("total_assets", T.DecimalType(18, 2)),
        T.StructField("total_liabilities", T.DecimalType(18, 2)),
        T.StructField("equity", T.DecimalType(18, 2)),
        T.StructField("revenue", T.DecimalType(18, 2)),
        T.StructField("net_income", T.DecimalType(18, 2)),
        T.StructField("interest_expense", T.DecimalType(18, 2)),
        T.StructField("current_assets", T.DecimalType(18, 2)),
        T.StructField("current_liabilities", T.DecimalType(18, 2)),
        T.StructField("inventory", T.DecimalType(18, 2)),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", counterparty_schema),
        T.StructField("after", counterparty_schema),
        T.StructField("op", T.StringType()),
        T.StructField("ts_ms", T.LongType()),
        T.StructField(
            "source",
            T.StructType(
                [
                    T.StructField("lsn", T.LongType()),
                    T.StructField("txId", T.LongType()),
                ]
            ),
        ),
    ]
)


@sp.table(
    name="bronze_cdc_counterparties_parsed",
    comment="Parsed CDC events — staging table for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_counterparties_parsed():
    return (
        sp.read_stream("bronze_cdc_counterparties")
        .select(F.from_json(F.col("kafka_value"), cdc_envelope_schema).alias("cdc"))
        .select(
            "cdc.op",
            "cdc.ts_ms",
            "cdc.source.lsn",
            F.coalesce("cdc.after", "cdc.before").alias("data"),
        )
        .select(
            "op",
            "ts_ms",
            "lsn",
            "data.*",
        )
        .withColumn("name", F.trim(F.upper(F.col("name"))))
        .withColumn("sector", F.trim(F.upper(F.col("sector"))))
        .withColumn("country", F.trim(F.upper(F.col("country"))))
        .withColumn("credit_rating", F.trim(F.upper(F.col("credit_rating"))))
    )


sp.create_streaming_table("silver_counterparties")

sp.apply_changes(
    target="silver_counterparties",
    source="bronze_cdc_counterparties_parsed",
    keys=["counterparty_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
