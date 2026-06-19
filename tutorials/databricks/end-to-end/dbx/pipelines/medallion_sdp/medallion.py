# Databricks notebook source
# SDP (Lakeflow Declarative Pipeline) medallion — the "other way" vs dbt, for the parity comparison.
# Reads the landed bronze (silverline.bronze.*) → silver → gold, with `_sdp` names so it sits beside
# the dbt gold for a parity diff. On Free Edition this runs as the ONE allowed declarative pipeline
# (target catalog=silverline, schema=gold). Create it in the UI (one pipeline) pointing at this file.
#
# Domain: Silverline Capital (fictional equipment lease & loan finance). Mirrors the dbt models:
#   silver_customers · silver_contracts · silver_invoices  →  gold segment_portfolio · contract_aging
import dlt  # noqa: F401
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@dlt.table(name="silver_customers_sdp", comment="SDP silver — current-state customers (latest per id).")
def silver_customers_sdp():
    w = Window.partitionBy("customer_id").orderBy(F.col("updated_at").desc_nulls_last())
    return (
        spark.read.table("silverline.bronze.customers")  # noqa: F821
        .withColumn("_rn", F.row_number().over(w)).where("_rn = 1")
        .selectExpr("customer_id", "legal_name", "segment", "region", "credit_rating",
                    "cast(annual_revenue as decimal(14,2)) as annual_revenue",
                    "cast(onboarded_date as date) as onboarded_date")
    )


@dlt.table(name="silver_contracts_sdp", comment="SDP silver — current-state lease/loan contracts.")
def silver_contracts_sdp():
    w = Window.partitionBy("contract_id").orderBy(F.col("updated_at").desc_nulls_last())
    return (
        spark.read.table("silverline.bronze.contracts")  # noqa: F821
        .withColumn("_rn", F.row_number().over(w)).where("_rn = 1")
        .selectExpr("contract_id", "customer_id", "contract_type", "status",
                    "cast(principal as decimal(14,2)) as principal",
                    "cast(apr as decimal(6,4)) as apr", "term_months",
                    "cast(start_date as date) as start_date", "cast(end_date as date) as end_date",
                    "cast(residual_value as decimal(14,2)) as residual_value")
    )


@dlt.table(name="silver_invoices_sdp", comment="SDP silver — invoices conformed with their contract.")
@dlt.expect_or_drop("valid", "invoice_id IS NOT NULL AND contract_id IS NOT NULL")
def silver_invoices_sdp():
    inv = spark.read.table("silverline.bronze.invoices")  # noqa: F821
    ct = dlt.read("silver_contracts_sdp").select("contract_id", "customer_id", "contract_type")
    return (
        inv.join(ct, "contract_id")
        .selectExpr("invoice_id", "contract_id", "customer_id", "contract_type",
                    "cast(invoice_date as date) as invoice_date", "cast(due_date as date) as due_date",
                    "cast(amount as decimal(12,2)) as amount", "status")
    )


@dlt.table(name="segment_portfolio_sdp", comment="SDP gold — financing portfolio by segment.")
def segment_portfolio_sdp():
    ct = dlt.read("silver_contracts_sdp")
    cu = dlt.read("silver_customers_sdp")
    return (ct.join(cu, "customer_id")
            .groupBy("segment")
            .agg(F.count(F.lit(1)).alias("contract_count"),
                 F.sum(F.when(F.col("status") == "active", 1).otherwise(0)).alias("active_contracts"),
                 F.sum("principal").alias("total_principal"),
                 F.round(F.avg("apr"), 4).alias("avg_apr"),
                 F.sum("residual_value").alias("total_residual")))


@dlt.table(name="contract_aging_sdp", comment="SDP gold — AR aging per contract.")
def contract_aging_sdp():
    inv = dlt.read("silver_invoices_sdp")
    return inv.groupBy("contract_id").agg(
        F.sum(F.when(F.col("status") == "overdue", F.col("amount")).otherwise(0)).alias("overdue_amount"),
        F.sum(F.when(F.col("status") == "open", F.col("amount")).otherwise(0)).alias("open_amount"),
        F.sum(F.when(F.col("status") == "paid", F.col("amount")).otherwise(0)).alias("paid_amount"),
        F.sum("amount").alias("total_billed"),
    )
