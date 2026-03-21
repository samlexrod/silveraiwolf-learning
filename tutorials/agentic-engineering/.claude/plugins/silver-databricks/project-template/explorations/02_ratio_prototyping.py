# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # 02 — Ratio Prototyping
# MAGIC
# MAGIC Prototype the financial ratio calculations before encoding them in the pipeline.
# MAGIC Run this after exploring the data in `01_data_exploration`.

# COMMAND ----------

from pyspark.sql import functions as F

counterparties = spark.read.csv(
    "/Volumes/main/financial_risk/raw/counterparties/",
    header=True,
    inferSchema=True,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Liquidity Ratios
# MAGIC
# MAGIC - **Current Ratio** = Current Assets / Current Liabilities (>1.0 is healthy)
# MAGIC - **Quick Ratio** = (Current Assets - Inventory) / Current Liabilities

# COMMAND ----------

liquidity = counterparties.select(
    "counterparty_id",
    "name",
    "current_assets",
    "current_liabilities",
    F.round(F.col("current_assets") / F.col("current_liabilities"), 4).alias("current_ratio"),
    F.round(
        (F.col("current_assets") - F.col("current_assets") * 0.3)
        / F.col("current_liabilities"),
        4,
    ).alias("quick_ratio"),
)
display(liquidity.orderBy("current_ratio"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Leverage Ratios
# MAGIC
# MAGIC - **Debt-to-Equity** = Total Debt / Total Equity (lower is less leveraged)
# MAGIC - **Interest Coverage** = EBIT / Interest Expense (>1.0 means earnings cover interest)

# COMMAND ----------

leverage = counterparties.select(
    "counterparty_id",
    "name",
    "total_debt",
    "total_equity",
    "ebit",
    "interest_expense",
    F.round(F.col("total_debt") / F.col("total_equity"), 4).alias("debt_to_equity"),
    F.round(
        F.when(F.col("interest_expense") > 0, F.col("ebit") / F.col("interest_expense")),
        4,
    ).alias("interest_coverage"),
)
display(leverage.orderBy(F.desc("debt_to_equity")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Profitability Ratios
# MAGIC
# MAGIC - **ROE** = Net Income / Total Equity
# MAGIC - **ROA** = Net Income / Total Assets
# MAGIC - **Net Profit Margin** = Net Income / Revenue

# COMMAND ----------

profitability = counterparties.select(
    "counterparty_id",
    "name",
    F.round(F.col("net_income") / F.col("total_equity"), 4).alias("roe"),
    F.round(F.col("net_income") / F.col("total_assets"), 4).alias("roa"),
    F.round(
        F.when(F.col("revenue") > 0, F.col("net_income") / F.col("revenue")),
        4,
    ).alias("net_profit_margin"),
)
display(profitability.orderBy(F.desc("roe")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Risk Flags
# MAGIC
# MAGIC Flag counterparties with concerning ratios.

# COMMAND ----------

all_ratios = counterparties.select(
    "counterparty_id",
    "name",
    "credit_rating",
    F.round(F.col("current_assets") / F.col("current_liabilities"), 4).alias("current_ratio"),
    F.round(F.col("total_debt") / F.col("total_equity"), 4).alias("debt_to_equity"),
    F.round(F.col("net_income") / F.col("total_equity"), 4).alias("roe"),
)

flagged = all_ratios.withColumn(
    "risk_flags",
    F.array_compact(
        F.array(
            F.when(F.col("current_ratio") < 1.0, F.lit("LOW_LIQUIDITY")),
            F.when(F.col("debt_to_equity") > 3.0, F.lit("HIGH_LEVERAGE")),
            F.when(F.col("roe") < 0, F.lit("NEGATIVE_ROE")),
        )
    ),
)

display(flagged.filter(F.size("risk_flags") > 0).orderBy(F.size("risk_flags"), ascending=False))
