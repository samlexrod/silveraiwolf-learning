import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_kyc_records",
    comment="Cleaned KYC records — validated verification statuses and risk levels",
)
@sp.expect("valid_kyc_id", "kyc_id IS NOT NULL")
@sp.expect("valid_status", "verification_status IN ('VERIFIED', 'PENDING', 'FAILED', 'EXPIRED')")
@sp.expect("valid_risk_level", "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')")
def silver_kyc_records():
    return (
        sp.read_stream("bronze_kyc_records")
        .select(
            F.col("kyc_id").cast("string"),
            F.col("counterparty_id").cast("string"),
            F.trim(F.upper(F.col("verification_status"))).alias("verification_status"),
            F.trim(F.upper(F.col("risk_level"))).alias("risk_level"),
            F.col("verification_date").cast("date"),
            F.col("expiry_date").cast("date"),
            F.trim(F.col("verified_by")).alias("verified_by"),
            F.trim(F.col("notes")).alias("notes"),
            F.col("ingested_at"),
        )
        .dropDuplicates(["kyc_id"])
    )
