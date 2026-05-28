import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

office_location_schema = T.StructType(
    [
        T.StructField("office_id", T.StringType()),
        T.StructField("name", T.StringType()),
        T.StructField("city", T.StringType()),
        T.StructField("country", T.StringType()),
        T.StructField("region", T.StringType()),
        T.StructField("timezone", T.StringType()),
        T.StructField("is_active", T.BooleanType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", office_location_schema),
        T.StructField("after", office_location_schema),
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
    name="bronze_cdc_office_locations_parsed",
    comment="Parsed CDC events for office locations — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_office_locations_parsed():
    return (
        sp.read_stream("bronze_cdc_office_locations")
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
        .withColumn("region", F.trim(F.upper(F.col("region"))))
        .withColumn("country", F.trim(F.upper(F.col("country"))))
    )


sp.create_streaming_table("silver_office_locations")

sp.apply_changes(
    target="silver_office_locations",
    source="bronze_cdc_office_locations_parsed",
    keys=["office_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
