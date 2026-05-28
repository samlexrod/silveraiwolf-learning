import pyspark.sql.functions as F
from pyspark import pipelines as sp
from pyspark.sql import Window


@sp.table(
    name="gold_counterparty_health",
    comment="Counterparty health — latest rating per agency, rating trend, days since last review",
)
@sp.expect("valid_counterparty", "counterparty_id IS NOT NULL")
def gold_counterparty_health():
    counterparties = sp.read("silver_counterparties")
    ratings = sp.read("silver_credit_ratings_history")

    # Latest rating per counterparty per agency
    w = Window.partitionBy("counterparty_id", "rating_agency").orderBy(F.desc("effective_date"))
    latest_ratings = (
        ratings.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") == 1).drop("rn")
    )

    # Determine rating trend based on previous_rating vs current rating
    rated = latest_ratings.withColumn(
        "rating_trend",
        F.when(F.col("previous_rating").isNull(), "INITIAL")
        .when(F.col("rating") > F.col("previous_rating"), "UPGRADE")
        .when(F.col("rating") < F.col("previous_rating"), "DOWNGRADE")
        .otherwise("STABLE"),
    ).withColumn(
        "days_since_review",
        F.datediff(F.current_date(), F.col("effective_date")),
    )

    # Pivot to one row per counterparty with columns per agency
    pivoted = rated.groupBy("counterparty_id").agg(
        F.max(F.when(F.col("rating_agency") == "S&P", F.col("rating"))).alias("sp_rating"),
        F.max(F.when(F.col("rating_agency") == "MOODY'S", F.col("rating"))).alias("moodys_rating"),
        F.max(F.when(F.col("rating_agency") == "FITCH", F.col("rating"))).alias("fitch_rating"),
        F.max(F.when(F.col("rating_agency") == "S&P", F.col("outlook"))).alias("sp_outlook"),
        F.min("days_since_review").alias("min_days_since_review"),
        F.collect_set("rating_trend").alias("trends"),
    )

    return counterparties.select("counterparty_id", "name", "sector", "country").join(
        pivoted, "counterparty_id", "left"
    )
