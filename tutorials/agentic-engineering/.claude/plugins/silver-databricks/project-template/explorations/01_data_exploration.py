# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # 01 — Data Exploration
# MAGIC
# MAGIC Explore the raw seed data before building the pipeline.
# MAGIC Upload the CSVs from `data/seed/` to a Databricks Volume, then run this notebook.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Counterparties

# COMMAND ----------

counterparties = spark.read.csv(
    "/Volumes/main/financial_risk/raw/counterparties/",
    header=True,
    inferSchema=True,
)
display(counterparties)

# COMMAND ----------

print(f"Total counterparties: {counterparties.count()}")
counterparties.groupBy("sector").count().orderBy("count", ascending=False).display()

# COMMAND ----------

counterparties.groupBy("credit_rating").count().orderBy("credit_rating").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transactions

# COMMAND ----------

transactions = spark.read.csv(
    "/Volumes/main/financial_risk/raw/transactions/",
    header=True,
    inferSchema=True,
)
display(transactions.limit(20))

# COMMAND ----------

print(f"Total transactions: {transactions.count()}")
print(f"Date range: {transactions.selectExpr('min(transaction_date)', 'max(transaction_date)').first()}")

# COMMAND ----------

transactions.groupBy("instrument_type", "direction").count().orderBy("instrument_type").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Market Data

# COMMAND ----------

market = spark.read.csv(
    "/Volumes/main/financial_risk/raw/market_data/",
    header=True,
    inferSchema=True,
)
display(market.limit(20))

# COMMAND ----------

print(f"Total records: {market.count()}")
print(f"Instruments: {market.select('instrument_id').distinct().count()}")
print(f"Date range: {market.selectExpr('min(trade_date)', 'max(trade_date)').first()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Quick Check

# COMMAND ----------

from pyspark.sql import functions as F

# Check for nulls in key columns
for df_name, df, key_cols in [
    ("counterparties", counterparties, ["counterparty_id", "name", "total_assets"]),
    ("transactions", transactions, ["transaction_id", "counterparty_id", "amount"]),
    ("market", market, ["instrument_id", "trade_date", "close_price"]),
]:
    null_counts = {col: df.filter(F.col(col).isNull()).count() for col in key_cols}
    print(f"\n{df_name} null counts: {null_counts}")
