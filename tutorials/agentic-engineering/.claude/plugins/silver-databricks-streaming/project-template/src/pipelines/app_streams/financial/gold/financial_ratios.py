import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_financial_ratios",
    comment="Financial health ratios per counterparty — updated in real time from CDC events",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_financial_ratios():
    return sp.read("silver_counterparties").select(
        "counterparty_id",
        "name",
        "sector",
        "credit_rating",
        # Liquidity ratios
        F.round(F.col("current_assets") / F.col("current_liabilities"), 4).alias("current_ratio"),
        F.round(
            (F.col("current_assets") - F.col("inventory")) / F.col("current_liabilities"), 4
        ).alias("quick_ratio"),
        # Leverage ratios
        F.round(F.col("total_liabilities") / F.col("equity"), 4).alias("debt_to_equity"),
        F.when(
            F.col("interest_expense") > 0,
            F.round(F.col("net_income") / F.col("interest_expense"), 4),
        ).alias("interest_coverage"),
        # Profitability ratios
        F.round(F.col("net_income") / F.col("equity"), 4).alias("roe"),
        F.round(F.col("net_income") / F.col("total_assets"), 4).alias("roa"),
        F.when(
            F.col("revenue") > 0,
            F.round(F.col("net_income") / F.col("revenue"), 4),
        ).alias("net_profit_margin"),
    )
