import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="silver_positions",
    comment="Net positions per counterparty and instrument — derived from streaming Silver tables",
)
@sp.expect("valid_position", "net_quantity IS NOT NULL")
@sp.expect("valid_market_value", "market_value IS NOT NULL")
def silver_positions():
    transactions = sp.read("silver_transactions")
    market_prices = sp.read("silver_market_prices")

    # Compute signed quantity: BUY = positive, SELL = negative
    signed = transactions.withColumn(
        "signed_quantity",
        F.when(F.col("direction") == "BUY", F.col("quantity")).otherwise(-F.col("quantity")),
    )

    # Aggregate positions per counterparty + instrument
    positions = signed.groupBy(
        "counterparty_id", "instrument_id", "instrument_type", "currency"
    ).agg(
        F.sum("signed_quantity").alias("net_quantity"),
        F.sum("amount").alias("total_cost"),
        F.max("transaction_date").alias("last_trade_date"),
    )

    # Get latest price per instrument
    latest_prices = market_prices.groupBy("instrument_id").agg(
        F.max_by("close_price", "trade_date").alias("latest_price"),
    )

    # Join positions with latest prices, compute market value and P&L
    return (
        positions.join(latest_prices, "instrument_id", "left")
        .withColumn("market_value", F.round(F.col("net_quantity") * F.col("latest_price"), 2))
        .withColumn("unrealized_pnl", F.round(F.col("market_value") - F.col("total_cost"), 2))
    )
