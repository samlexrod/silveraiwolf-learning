import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_regulatory_metrics",
    comment="Regulatory compliance metrics — deadlines, status by regulation, overdue count",
)
def gold_regulatory_metrics():
    reqs = sp.read("silver_reporting_requirements")

    return (
        reqs.withColumn(
            "is_overdue",
            F.when(
                (F.col("next_due_date") < F.current_date()) & (F.col("status") != "COMPLIANT"),
                True,
            ).otherwise(False),
        )
        .withColumn(
            "days_until_due",
            F.datediff(F.col("next_due_date"), F.current_date()),
        )
        .groupBy("regulation_name", "jurisdiction")
        .agg(
            F.count("*").alias("total_requirements"),
            F.sum(F.when(F.col("status") == "COMPLIANT", 1).otherwise(0)).alias("compliant_count"),
            F.sum(F.when(F.col("status") == "NON_COMPLIANT", 1).otherwise(0)).alias(
                "non_compliant_count"
            ),
            F.sum(F.when(F.col("is_overdue") == True, 1).otherwise(0)).alias("overdue_count"),  # noqa: E712
            F.min("days_until_due").alias("next_deadline_days"),
        )
        .withColumn(
            "compliance_pct",
            F.round(F.col("compliant_count") / F.col("total_requirements") * 100, 1),
        )
    )
