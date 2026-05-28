import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

kyc_schema = T.StructType(
    [
        T.StructField("kyc_id", T.StringType()),
        T.StructField("counterparty_id", T.StringType()),
        T.StructField("verification_status", T.StringType()),
        T.StructField("risk_level", T.StringType()),
        T.StructField("verification_date", T.StringType()),
        T.StructField("expiry_date", T.StringType()),
        T.StructField("verified_by", T.StringType()),
        T.StructField("notes", T.StringType()),
    ]
)


@sp.table(
    name="bronze_kyc_records",
    comment="Raw KYC records ingested from API landing zone via Auto Loader",
)
def bronze_kyc_records():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    catalog = spark.conf.get("pipeline.catalog", "main")  # noqa: F821

    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "json")
        .option(
            "cloudFiles.schemaLocation",
            f"/Volumes/{catalog}/{schema}/checkpoints/bronze_kyc_records",
        )
        .schema(kyc_schema)
        .load(f"/Volumes/{catalog}/{schema}/landing/compliance/kyc_records/")
        .select("*", F.current_timestamp().alias("ingested_at"))
    )
