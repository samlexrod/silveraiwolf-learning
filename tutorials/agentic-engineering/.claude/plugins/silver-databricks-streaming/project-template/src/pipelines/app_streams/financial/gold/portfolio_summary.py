import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_portfolio_summary",
    comment="Portfolio summary by sector, instrument type, and currency — real-time aggregates",
)
def gold_portfolio_summary():
    positions = sp.read("silver_positions")
    counterparties = sp.read("silver_counterparties")

    return (
        positions.join(
            counterparties.select("counterparty_id", "sector"),
            "counterparty_id",
            "left",
        )
        .groupBy("sector", "instrument_type", "currency")
        .agg(
            F.sum("market_value").alias("total_market_value"),
            F.sum(F.abs("market_value")).alias("gross_market_value"),
            F.sum("unrealized_pnl").alias("total_unrealized_pnl"),
            F.sum("net_quantity").alias("total_net_quantity"),
            F.countDistinct("counterparty_id").alias("counterparty_count"),
            F.countDistinct("instrument_id").alias("instrument_count"),
        )
        .withColumn(
            "avg_pnl_per_counterparty",
            F.round(F.col("total_unrealized_pnl") / F.col("counterparty_count"), 2),
        )
        .orderBy(F.desc("gross_market_value"))
    )
