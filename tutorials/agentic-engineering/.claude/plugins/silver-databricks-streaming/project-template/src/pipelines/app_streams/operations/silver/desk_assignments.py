import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

desk_assignment_schema = T.StructType(
    [
        T.StructField("assignment_id", T.StringType()),
        T.StructField("desk_id", T.StringType()),
        T.StructField("counterparty_id", T.StringType()),
        T.StructField("instrument_type", T.StringType()),
        T.StructField("effective_date", T.DateType()),
        T.StructField("end_date", T.DateType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", desk_assignment_schema),
        T.StructField("after", desk_assignment_schema),
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
    name="bronze_cdc_desk_assignments_parsed",
    comment="Parsed CDC events for desk assignments — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_desk_assignments_parsed():
    return (
        sp.read_stream("bronze_cdc_desk_assignments")
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


sp.create_streaming_table("silver_desk_assignments")

sp.apply_changes(
    target="silver_desk_assignments",
    source="bronze_cdc_desk_assignments_parsed",
    keys=["assignment_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
