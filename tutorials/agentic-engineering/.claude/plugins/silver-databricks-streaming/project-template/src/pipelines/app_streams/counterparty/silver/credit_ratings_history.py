import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

credit_rating_schema = T.StructType(
    [
        T.StructField("rating_id", T.StringType()),
        T.StructField("counterparty_id", T.StringType()),
        T.StructField("rating_agency", T.StringType()),
        T.StructField("rating", T.StringType()),
        T.StructField("outlook", T.StringType()),
        T.StructField("effective_date", T.DateType()),
        T.StructField("previous_rating", T.StringType()),
        T.StructField("updated_at", T.TimestampType()),
    ]
)

cdc_envelope_schema = T.StructType(
    [
        T.StructField("before", credit_rating_schema),
        T.StructField("after", credit_rating_schema),
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
    name="bronze_cdc_credit_ratings_history_parsed",
    comment="Parsed CDC events for credit ratings — staging for APPLY CHANGES INTO",
    temporary=True,
)
def bronze_cdc_credit_ratings_history_parsed():
    return (
        sp.read_stream("bronze_cdc_credit_ratings_history")
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
        .withColumn("rating_agency", F.trim(F.upper(F.col("rating_agency"))))
        .withColumn("outlook", F.trim(F.upper(F.col("outlook"))))
        .withColumn("rating", F.trim(F.upper(F.col("rating"))))
    )


sp.create_streaming_table("silver_credit_ratings_history")

sp.apply_changes(
    target="silver_credit_ratings_history",
    source="bronze_cdc_credit_ratings_history_parsed",
    keys=["rating_id"],
    sequence_by=F.col("ts_ms"),
    apply_as_deletes=F.expr("op = 'd'"),
    except_column_list=["op", "ts_ms", "lsn"],
)
