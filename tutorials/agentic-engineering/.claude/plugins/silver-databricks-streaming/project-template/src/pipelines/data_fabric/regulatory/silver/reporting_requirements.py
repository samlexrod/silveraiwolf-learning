import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_reporting_requirements",
    comment="Cleaned reporting requirements — validated statuses and frequencies",
)
@sp.expect("valid_requirement_id", "requirement_id IS NOT NULL")
@sp.expect("valid_frequency", "frequency IN ('DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY')")
@sp.expect("valid_status", "status IN ('COMPLIANT', 'NON_COMPLIANT', 'PENDING')")
def silver_reporting_requirements():
    return (
        sp.read_stream("bronze_reporting_requirements")
        .select(
            F.col("requirement_id").cast("string"),
            F.trim(F.col("regulation_name")).alias("regulation_name"),
            F.trim(F.upper(F.col("jurisdiction"))).alias("jurisdiction"),
            F.trim(F.col("report_type")).alias("report_type"),
            F.trim(F.upper(F.col("frequency"))).alias("frequency"),
            F.col("next_due_date").cast("date"),
            F.trim(F.upper(F.col("status"))).alias("status"),
            F.trim(F.col("affected_desks")).alias("affected_desks"),
            F.col("ingested_at"),
        )
        .dropDuplicates(["requirement_id"])
    )
