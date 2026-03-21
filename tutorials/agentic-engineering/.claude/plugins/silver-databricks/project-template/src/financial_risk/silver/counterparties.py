from pyspark import pipelines as sp
from pyspark.sql import functions as F


@sp.table(
    name="silver_counterparties",
    comment="Cleaned counterparty data with standardized fields and validated financials",
)
@sp.expect("valid_counterparty_id", "counterparty_id IS NOT NULL")
@sp.expect("valid_name", "name IS NOT NULL AND length(name) > 0")
@sp.expect(
    "valid_credit_rating",
    "credit_rating IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','D')",
)
@sp.expect("positive_assets", "total_assets > 0")
@sp.expect("positive_equity", "total_equity > 0")
def silver_counterparties():
    return (
        sp.read("bronze_counterparties")
        .withColumn("name", F.trim(F.upper(F.col("name"))))
        .withColumn("sector", F.trim(F.upper(F.col("sector"))))
        .withColumn("country", F.trim(F.upper(F.col("country"))))
        .withColumn("total_assets", F.col("total_assets").cast("decimal(18,2)"))
        .withColumn("current_assets", F.col("current_assets").cast("decimal(18,2)"))
        .withColumn("total_liabilities", F.col("total_liabilities").cast("decimal(18,2)"))
        .withColumn("current_liabilities", F.col("current_liabilities").cast("decimal(18,2)"))
        .withColumn("total_equity", F.col("total_equity").cast("decimal(18,2)"))
        .withColumn("total_debt", F.col("total_debt").cast("decimal(18,2)"))
        .withColumn("revenue", F.col("revenue").cast("decimal(18,2)"))
        .withColumn("net_income", F.col("net_income").cast("decimal(18,2)"))
        .withColumn("ebit", F.col("ebit").cast("decimal(18,2)"))
        .withColumn("interest_expense", F.col("interest_expense").cast("decimal(18,2)"))
        .dropDuplicates(["counterparty_id"])
    )
