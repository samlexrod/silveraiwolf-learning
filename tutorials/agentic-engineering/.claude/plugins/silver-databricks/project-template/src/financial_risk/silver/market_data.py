from pyspark import pipelines as sp
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@sp.table(
    name="silver_market_data",
    comment="Cleaned market data with forward-filled gaps and validated prices",
)
@sp.expect("valid_instrument", "instrument_id IS NOT NULL")
@sp.expect("valid_date", "trade_date IS NOT NULL")
@sp.expect("positive_close", "close_price > 0")
def silver_market_data():
    window = Window.partitionBy("instrument_id").orderBy("trade_date")

    return (
        sp.read("bronze_market_data")
        .withColumn("trade_date", F.to_date(F.col("trade_date")))
        .withColumn("close_price", F.col("close_price").cast("decimal(18,4)"))
        .withColumn("open_price", F.col("open_price").cast("decimal(18,4)"))
        .withColumn("high_price", F.col("high_price").cast("decimal(18,4)"))
        .withColumn("low_price", F.col("low_price").cast("decimal(18,4)"))
        .withColumn("volume", F.col("volume").cast("bigint"))
        .withColumn("instrument_type", F.upper(F.trim(F.col("instrument_type"))))
        # Forward-fill missing close prices within each instrument
        .withColumn(
            "close_price",
            F.coalesce(F.col("close_price"), F.last("close_price", ignorenulls=True).over(window)),
        )
        .dropDuplicates(["instrument_id", "trade_date"])
    )
