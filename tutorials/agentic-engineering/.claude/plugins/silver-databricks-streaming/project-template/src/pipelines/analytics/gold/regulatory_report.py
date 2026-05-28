import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_regulatory_report",
    comment="Regulatory readiness per counterparty — KYC, sanctions, txn volume, regulations",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_regulatory_report():

    counterparties = sp.read("silver_counterparties")
    transactions = sp.read("silver_transactions")
    kyc = sp.read("silver_kyc_records")
    reqs = sp.read("silver_reporting_requirements")

    # Transaction volume per counterparty
    txn_volume = transactions.groupBy("counterparty_id").agg(
        F.count("*").alias("transaction_count"),
        F.sum("amount").alias("total_transaction_value"),
    )

    # Latest KYC per counterparty
    latest_kyc = kyc.dropDuplicates(["counterparty_id"]).select(
        "counterparty_id",
        F.col("verification_status").alias("kyc_status"),
        F.col("risk_level").alias("kyc_risk_level"),
        "expiry_date",
    )

    # Total applicable regulations
    reg_count = reqs.select(
        F.countDistinct("regulation_name").alias("total_regulations"),
        F.sum(F.when(F.col("status") == "COMPLIANT", 1).otherwise(0)).alias(
            "compliant_regulations"
        ),
    )

    return (
        counterparties.select("counterparty_id", "name", "sector", "country")
        .join(txn_volume, "counterparty_id", "left")
        .join(latest_kyc, "counterparty_id", "left")
        .crossJoin(reg_count)
        .withColumn(
            "kyc_expired",
            F.when(F.col("expiry_date") < F.current_date(), True).otherwise(False),
        )
        .withColumn(
            "regulatory_readiness",
            F.when(F.col("kyc_status") == "VERIFIED", "READY")
            .when(F.col("kyc_status") == "PENDING", "IN_PROGRESS")
            .otherwise("NOT_READY"),
        )
        .fillna(0, subset=["transaction_count", "total_transaction_value"])
    )
