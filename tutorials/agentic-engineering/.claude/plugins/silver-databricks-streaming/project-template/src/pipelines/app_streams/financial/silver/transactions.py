import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

transaction_schema = T.StructType(
    [
        T.StructField("transaction_id", T.StringType()),
        T.StructField("counterparty_id", T.StringType()),
        T.StructField("direction", T.StringType()),
        T.StructField("instrument_id", T.StringType()),
        T.StructField("instrument_type", T.StringType()),
        T.StructField("amount", T.DecimalType(18, 2)),
        T.StructField("currency", T.StringType()),
        T.StructField("transaction_date", T.DateType()),
        T.StructField("quantity", T.IntegerType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", transaction_schema),
        T.StructField("after", transaction_schema),
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
    name="bronze_cdc_transactions_parsed",
    comment="Parsed CDC events for transactions — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_transactions_parsed():
    return (
        sp.read_stream("bronze_cdc_transactions")
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
        .withColumn("direction", F.trim(F.upper(F.col("direction"))))
        .withColumn("instrument_type", F.trim(F.upper(F.col("instrument_type"))))
        .withColumn("currency", F.trim(F.upper(F.col("currency"))))
    )


sp.create_streaming_table("silver_transactions")

sp.apply_changes(
    target="silver_transactions",
    source="bronze_cdc_transactions_parsed",
    keys=["transaction_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
