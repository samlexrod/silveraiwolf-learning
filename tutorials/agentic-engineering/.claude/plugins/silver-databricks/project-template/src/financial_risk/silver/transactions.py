from pyspark import pipelines as sp
from pyspark.sql import functions as F


@sp.table(
    name="silver_transactions",
    comment="Validated and enriched financial transactions",
)
@sp.expect("valid_transaction_id", "transaction_id IS NOT NULL")
@sp.expect("valid_date", "transaction_date IS NOT NULL")
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
@sp.expect("positive_amount", "amount > 0")
@sp.expect_or_drop(
    "valid_direction", "direction IN ('BUY', 'SELL')"
)
@sp.expect_or_drop(
    "valid_instrument_type", "instrument_type IN ('EQUITY', 'BOND', 'DERIVATIVE', 'FX')"
)
def silver_transactions():
    return (
        sp.read_stream("bronze_transactions")
        .withColumn("direction", F.upper(F.trim(F.col("direction"))))
        .withColumn("instrument_type", F.upper(F.trim(F.col("instrument_type"))))
        .withColumn("transaction_date", F.to_date(F.col("transaction_date")))
        .withColumn("amount", F.col("amount").cast("decimal(18,2)"))
        .withColumn("price", F.col("price").cast("decimal(18,4)"))
        .withColumn("quantity", F.col("quantity").cast("decimal(18,4)"))
        .withColumn("currency", F.upper(F.trim(F.col("currency"))))
        .dropDuplicates(["transaction_id"])
    )
