import pyspark.sql.functions as F
from pyspark import pipelines as sp


@sp.table(
    name="gold_desk_pnl_exposure",
    comment="P&L and exposure per desk, per office, per region",
)
@sp.expect("valid_desk", "desk_id IS NOT NULL")
def gold_desk_pnl_exposure():

    desks = sp.read("silver_trading_desks")
    assignments = sp.read("silver_desk_assignments")
    positions = sp.read("silver_positions")
    offices = sp.read("silver_office_locations")

    # Map counterparties to desks via active assignments
    desk_counterparties = (
        assignments.filter(F.col("end_date").isNull())
        .select("desk_id", "counterparty_id")
        .distinct()
    )

    # Aggregate positions per desk
    desk_positions = (
        desk_counterparties.join(positions, "counterparty_id", "inner")
        .groupBy("desk_id")
        .agg(
            F.sum("market_value").alias("net_market_value"),
            F.sum(F.abs("market_value")).alias("gross_exposure"),
            F.sum("unrealized_pnl").alias("total_pnl"),
            F.countDistinct("counterparty_id").alias("counterparty_count"),
            F.countDistinct("instrument_id").alias("instrument_count"),
        )
    )

    return (
        desks.filter(F.col("is_active") == True)  # noqa: E712
        .join(
            offices.select("office_id", F.col("name").alias("office_name"), "city", "region"),
            "office_id",
            "left",
        )
        .join(desk_positions, "desk_id", "left")
        .select(
            "desk_id",
            desks["name"].alias("desk_name"),
            "asset_class",
            "head_trader",
            "office_name",
            "city",
            "region",
            "net_market_value",
            "gross_exposure",
            "total_pnl",
            "counterparty_count",
            "instrument_count",
        )
        .fillna(0, subset=["net_market_value", "gross_exposure", "total_pnl"])
    )
