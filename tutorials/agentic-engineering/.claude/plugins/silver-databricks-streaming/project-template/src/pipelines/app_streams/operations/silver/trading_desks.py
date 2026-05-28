import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

trading_desk_schema = T.StructType(
    [
        T.StructField("desk_id", T.StringType()),
        T.StructField("name", T.StringType()),
        T.StructField("office_id", T.StringType()),
        T.StructField("asset_class", T.StringType()),
        T.StructField("head_trader", T.StringType()),
        T.StructField("is_active", T.BooleanType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", trading_desk_schema),
        T.StructField("after", trading_desk_schema),
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
    name="bronze_cdc_trading_desks_parsed",
    comment="Parsed CDC events for trading desks — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_trading_desks_parsed():
    return (
        sp.read_stream("bronze_cdc_trading_desks")
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
        .withColumn("asset_class", F.trim(F.upper(F.col("asset_class"))))
    )


sp.create_streaming_table("silver_trading_desks")

sp.apply_changes(
    target="silver_trading_desks",
    source="bronze_cdc_trading_desks_parsed",
    keys=["desk_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
