import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_compliance_status",
    comment="Per-counterparty compliance status — sanctions matches, KYC status, overall risk",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_compliance_status():
    kyc = sp.read("silver_kyc_records")

    # Latest KYC per counterparty
    latest_kyc = kyc.dropDuplicates(["counterparty_id"]).select(
        "counterparty_id",
        "verification_status",
        "risk_level",
        "verification_date",
        "expiry_date",
    )

    # Overall compliance risk level
    return latest_kyc.withColumn(
        "kyc_expired",
        F.when(F.col("expiry_date") < F.current_date(), True).otherwise(False),
    ).withColumn(
        "compliance_risk",
        F.when(F.col("verification_status") == "FAILED", "CRITICAL")
        .when(F.col("kyc_expired") == True, "HIGH")  # noqa: E712
        .when(F.col("risk_level") == "CRITICAL", "CRITICAL")
        .when(F.col("risk_level") == "HIGH", "HIGH")
        .when(F.col("verification_status") == "PENDING", "MEDIUM")
        .otherwise("LOW"),
    )
