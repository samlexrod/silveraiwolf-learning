import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_desk_overview",
    comment="Active desks per office with instruments covered and counterparties assigned",
)
@sp.expect("valid_desk", "desk_id IS NOT NULL")
def gold_desk_overview():
    desks = sp.read("silver_trading_desks")
    offices = sp.read("silver_office_locations")
    assignments = sp.read("silver_desk_assignments")

    # Aggregate assignments per desk
    desk_stats = (
        assignments.filter(F.col("end_date").isNull())  # Active assignments only
        .groupBy("desk_id")
        .agg(
            F.countDistinct("counterparty_id").alias("counterparty_count"),
            F.collect_set("instrument_type").alias("instruments_covered"),
        )
    )

    offices_renamed = offices.select(
        "office_id",
        F.col("name").alias("office_name"),
        "city",
        "region",
    )

    return (
        desks.filter(F.col("is_active") == True)  # noqa: E712
        .withColumnRenamed("name", "desk_name")
        .join(offices_renamed, "office_id", "left")
        .join(desk_stats, "desk_id", "left")
        .select(
            "desk_id",
            "desk_name",
            "asset_class",
            "head_trader",
            "office_name",
            "city",
            "region",
            "counterparty_count",
            "instruments_covered",
        )
    )
