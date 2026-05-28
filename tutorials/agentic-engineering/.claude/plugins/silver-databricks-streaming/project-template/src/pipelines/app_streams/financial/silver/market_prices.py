import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

market_price_schema = T.StructType(
    [
        T.StructField("instrument_id", T.StringType()),
        T.StructField("trade_date", T.DateType()),
        T.StructField("instrument_type", T.StringType()),
        T.StructField("open_price", T.DecimalType(18, 2)),
        T.StructField("high_price", T.DecimalType(18, 2)),
        T.StructField("low_price", T.DecimalType(18, 2)),
        T.StructField("close_price", T.DecimalType(18, 2)),
        T.StructField("volume", T.LongType()),
        T.StructField("currency", T.StringType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", market_price_schema),
        T.StructField("after", market_price_schema),
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
    name="bronze_cdc_market_prices_parsed",
    comment="Parsed CDC events for market prices — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_market_prices_parsed():
    return (
        sp.read_stream("bronze_cdc_market_prices")
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
        .withColumn("instrument_type", F.trim(F.upper(F.col("instrument_type"))))
    )


sp.create_streaming_table("silver_market_prices")

sp.apply_changes(
    target="silver_market_prices",
    source="bronze_cdc_market_prices_parsed",
    keys=["instrument_id", "trade_date"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
