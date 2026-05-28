import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark import pipelines as sp

reporting_schema = T.StructType(
    [
        T.StructField("requirement_id", T.StringType()),
        T.StructField("regulation_name", T.StringType()),
        T.StructField("jurisdiction", T.StringType()),
        T.StructField("report_type", T.StringType()),
        T.StructField("frequency", T.StringType()),
        T.StructField("next_due_date", T.StringType()),
        T.StructField("status", T.StringType()),
        T.StructField("affected_desks", T.StringType()),
    ]
)


@sp.table(
    name="bronze_reporting_requirements",
    comment="Raw reporting requirements ingested from API landing zone via Auto Loader",
)
def bronze_reporting_requirements():
    schema = spark.conf.get("pipeline.schema")  # noqa: F821
    catalog = spark.conf.get("pipeline.catalog", "main")  # noqa: F821

    return (
        spark.readStream.format("cloudFiles")  # noqa: F821
        .option("cloudFiles.format", "json")
        .option(
            "cloudFiles.schemaLocation",
            f"/Volumes/{catalog}/{schema}/checkpoints/bronze_reporting_requirements",
        )
        .schema(reporting_schema)
        .load(f"/Volumes/{catalog}/{schema}/landing/regulatory/reporting_requirements/")
        .select("*", F.current_timestamp().alias("ingested_at"))
    )
