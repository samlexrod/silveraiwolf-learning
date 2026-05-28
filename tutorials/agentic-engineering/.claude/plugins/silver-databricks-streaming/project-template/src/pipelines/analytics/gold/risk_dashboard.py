import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_risk_dashboard",
    comment="Per-counterparty risk score — financial exposure, credit rating, compliance flags",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
@sp.expect("valid_risk_tier", "risk_tier IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')")
def gold_risk_dashboard():

    positions = sp.read("silver_positions")
    counterparties = sp.read("silver_counterparties")
    ratings = sp.read("silver_credit_ratings_history")
    sanctions = sp.read("silver_sanctions_watchlist")
    kyc = sp.read("silver_kyc_records")

    # Aggregate exposure per counterparty
    exposure = positions.groupBy("counterparty_id").agg(
        F.sum(F.abs("market_value")).alias("gross_exposure"),
        F.sum("unrealized_pnl").alias("total_pnl"),
    )

    # Latest credit rating per counterparty (any agency)
    latest_rating = ratings.dropDuplicates(["counterparty_id"]).select(
        "counterparty_id",
        F.col("rating").alias("latest_credit_rating"),
        F.col("outlook").alias("latest_outlook"),
    )

    # KYC risk per counterparty
    kyc_risk = kyc.dropDuplicates(["counterparty_id"]).select(
        "counterparty_id", "verification_status", "risk_level"
    )

    # Active sanctions flag count
    sanctions_flags = (
        sanctions.filter(F.col("status") == "ACTIVE")
        .groupBy("entity_name")
        .agg(F.count("*").alias("sanctions_flag_count"))
    )

    # Assemble risk dashboard
    result = (
        counterparties.select("counterparty_id", "name", "sector", "country")
        .join(exposure, "counterparty_id", "left")
        .join(latest_rating, "counterparty_id", "left")
        .join(kyc_risk, "counterparty_id", "left")
        .join(sanctions_flags, F.col("name") == sanctions_flags["entity_name"], "left")
        .drop("entity_name")
        .fillna(0, subset=["gross_exposure", "total_pnl", "sanctions_flag_count"])
        .withColumn(
            "risk_tier",
            F.when(F.col("verification_status") == "FAILED", "CRITICAL")
            .when(F.col("risk_level") == "CRITICAL", "CRITICAL")
            .when(F.col("latest_outlook") == "NEGATIVE", "HIGH")
            .when(F.col("risk_level") == "HIGH", "HIGH")
            .when(F.col("gross_exposure") > 5000000, "HIGH")
            .when(F.col("risk_level") == "MEDIUM", "MEDIUM")
            .otherwise("LOW"),
        )
    )

    return result
