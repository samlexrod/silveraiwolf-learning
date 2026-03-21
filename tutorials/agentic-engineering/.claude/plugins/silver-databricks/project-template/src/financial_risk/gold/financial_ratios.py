from pyspark import pipelines as sp
from pyspark.sql import functions as F


@sp.table(
    name="gold_financial_ratios",
    comment="Key financial ratios per counterparty — liquidity, leverage, and profitability",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_financial_ratios():
    cp = sp.read("silver_counterparties")

    return cp.select(
        "counterparty_id",
        "name",
        "sector",
        "country",
        "credit_rating",
        # Liquidity ratios
        F.round(F.col("current_assets") / F.col("current_liabilities"), 4).alias("current_ratio"),
        F.round(
            (F.col("current_assets") - F.col("current_assets") * 0.3)
            / F.col("current_liabilities"),
            4,
        ).alias("quick_ratio"),
        # Leverage ratios
        F.round(F.col("total_debt") / F.col("total_equity"), 4).alias("debt_to_equity"),
        F.round(
            F.when(F.col("interest_expense") > 0, F.col("ebit") / F.col("interest_expense")),
            4,
        ).alias("interest_coverage"),
        # Profitability ratios
        F.round(F.col("net_income") / F.col("total_equity"), 4).alias("roe"),
        F.round(F.col("net_income") / F.col("total_assets"), 4).alias("roa"),
        F.round(
            F.when(F.col("revenue") > 0, F.col("net_income") / F.col("revenue")),
            4,
        ).alias("net_profit_margin"),
    )
