from pyspark import pipelines as sp
from pyspark.sql import functions as F


@sp.table(
    name="gold_risk_exposure",
    comment="Risk exposure per counterparty — position concentration and credit risk",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_risk_exposure():
    positions = sp.read("silver_positions")
    counterparties = sp.read("silver_counterparties")

    # Total portfolio value for concentration calculation
    total_portfolio = positions.agg(
        F.sum(F.abs(F.col("market_value"))).alias("total_portfolio_value")
    )

    # Aggregate exposure per counterparty
    exposure = (
        positions.groupBy("counterparty_id")
        .agg(
            F.sum(F.abs(F.col("market_value"))).alias("gross_exposure"),
            F.sum(F.col("market_value")).alias("net_exposure"),
            F.sum(F.col("unrealized_pnl")).alias("total_unrealized_pnl"),
            F.countDistinct("instrument_id").alias("instrument_count"),
            F.max("last_trade_date").alias("last_activity_date"),
        )
    )

    return (
        exposure.crossJoin(total_portfolio)
        .join(
            counterparties.select("counterparty_id", "name", "sector", "country", "credit_rating"),
            "counterparty_id",
            "left",
        )
        .withColumn(
            "concentration_pct",
            F.round(F.col("gross_exposure") / F.col("total_portfolio_value") * 100, 2),
        )
        .withColumn(
            "risk_tier",
            F.when(F.col("concentration_pct") > 20, "CRITICAL")
            .when(F.col("concentration_pct") > 10, "HIGH")
            .when(F.col("concentration_pct") > 5, "MEDIUM")
            .otherwise("LOW"),
        )
        .drop("total_portfolio_value")
    )
