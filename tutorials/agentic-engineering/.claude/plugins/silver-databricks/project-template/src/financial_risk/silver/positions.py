from pyspark import pipelines as sp
from pyspark.sql import functions as F


@sp.table(
    name="silver_positions",
    comment="Net positions per counterparty and instrument with current market values",
)
@sp.expect("valid_position", "net_quantity IS NOT NULL")
@sp.expect("valid_market_value", "market_value IS NOT NULL")
def silver_positions():
    txns = sp.read("silver_transactions")
    market = sp.read("silver_market_data")

    # Calculate net position per counterparty + instrument
    positions = (
        txns.withColumn(
            "signed_quantity",
            F.when(F.col("direction") == "BUY", F.col("quantity")).otherwise(-F.col("quantity")),
        )
        .groupBy("counterparty_id", "instrument_id", "instrument_type", "currency")
        .agg(
            F.sum("signed_quantity").alias("net_quantity"),
            F.sum("amount").alias("total_cost"),
            F.max("transaction_date").alias("last_trade_date"),
        )
    )

    # Get latest market price per instrument
    latest_prices = (
        market.groupBy("instrument_id")
        .agg(F.max_by("close_price", "trade_date").alias("latest_price"))
    )

    # Join positions with latest prices to get market value
    return (
        positions.join(latest_prices, "instrument_id", "left")
        .withColumn(
            "market_value",
            F.round(F.col("net_quantity") * F.col("latest_price"), 2),
        )
        .withColumn(
            "unrealized_pnl",
            F.round(F.col("market_value") - F.col("total_cost"), 2),
        )
    )
