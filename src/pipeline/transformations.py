"""Lakeflow Spark Declarative Pipeline, part 2: conformed silver (ingest.py) -> modelling silver -> gold features.

Materialized views, recomputed on every hourly job run. Expectations drop rows that cannot be right
(missing keys, prices outside the AESO market range) and record soft warnings for the rest.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

CATALOG = spark.conf.get("aeso.catalog")
SCHEMA = spark.conf.get("aeso.schema")
spark.conf.set("spark.sql.session.timeZone", "UTC")  # *_mpt columns are naive Mountain Time wall clock

def bronze(name):
    """A conformed silver dataset from ingest.py (same pipeline), built from the raw landing files."""
    return spark.read.table(name)


@dp.materialized_view(comment="Silver: hourly AESO pool price, deduplicated and range-checked, with AESO hour-ending.")
@dp.expect_or_drop("valid_hour", "begin_datetime_utc IS NOT NULL AND begin_datetime_mpt IS NOT NULL")
@dp.expect_or_drop("price_in_market_range", "pool_price IS NULL OR pool_price BETWEEN 0 AND 999.99")
@dp.expect("aeso_forecast_present", "forecast_pool_price IS NOT NULL")
def silver_pool_price_hourly():
    return (bronze("aeso_pool_price")
            .withColumn("hour_ending", F.hour("begin_datetime_mpt") + 1)        # AESO HE01..HE24
            .withColumn("day_of_week", F.dayofweek("begin_datetime_mpt"))     # 1 = Sunday
            .withColumn("is_settled", F.col("pool_price").isNotNull())
            .drop("loaded_at"))


@dp.materialized_view(comment=(
    "Silver: hourly wind + solar generation. actual_mw comes from the forecast CSV when it has an actual, else "
    "from metered volumes. regressor_mw fills the remaining gaps with the forecast, then an hour-of-day x month "
    "average; is_imputed flags the averaged hours."))
@dp.expect_or_drop("valid_hour", "forecast_transaction_date IS NOT NULL")
@dp.expect("regressor_present", "regressor_mw IS NOT NULL")
def silver_wind_solar_hourly():
    csv = bronze("aeso_wind_solar_forecast").drop("loaded_at")
    metered = (bronze("aeso_wind_solar_metered")
               .select(F.col("begin_datetime_mpt").alias("forecast_transaction_date"),
                       F.col("wind_solar_mw").alias("metered_mw")))
    bounds = (bronze("aeso_pool_price").select(F.min("begin_datetime_mpt").alias("lo"))
              .crossJoin(csv.select(F.max("forecast_transaction_date").alias("hi"))))
    spine = bounds.select(F.explode(F.sequence("lo", "hi", F.expr("INTERVAL 1 HOUR"))).alias("forecast_transaction_date"))

    joined = (spine.join(csv.withColumnRenamed("actual_mw", "csv_actual_mw"), "forecast_transaction_date", "left")
              .join(metered, "forecast_transaction_date", "left")
              .withColumn("actual_mw", F.coalesce("csv_actual_mw", "metered_mw")))
    by_hour_month = Window.partitionBy(F.hour("forecast_transaction_date"), F.month("forecast_transaction_date"))
    return (joined
            .withColumn("climatology_mw", F.avg("actual_mw").over(by_hour_month))
            .withColumn("regressor_mw", F.coalesce("actual_mw", "most_likely_mw", "climatology_mw"))
            .withColumn("regressor_source",
                        F.when(F.col("csv_actual_mw").isNotNull(), "csv_actual")
                         .when(F.col("metered_mw").isNotNull(), "metered")
                         .when(F.col("most_likely_mw").isNotNull(), "csv_forecast")
                         .otherwise("imputed"))
            .withColumn("is_imputed", F.col("regressor_source") == "imputed")
            .drop("climatology_mw", "csv_actual_mw"))


@dp.materialized_view(comment=(
    "Silver: hourly Alberta fundamentals. *_mw columns are as last published (training and live forecast); "
    "*_dayahead_mw columns are what was known before the hour's day began (backtests): the last archived snapshot "
    "taken before that midnight, else the published wind/solar forecast file, else capability as of 24 hours "
    "earlier. load_mw is AESO's forecast load, so past and future hours share one definition."))
@dp.expect_or_drop("valid_hour", "begin_datetime_mpt IS NOT NULL")
@dp.expect("load_in_range", "load_mw BETWEEN 5000 AND 15000")
@dp.expect("capability_present", "dispatchable_available_mw > 0")
@dp.expect("dayahead_wind_present", "wind_solar_dayahead_mw IS NOT NULL")
def silver_supply_demand_hourly():
    sd = (bronze("aeso_supply_demand_hourly")
          .withColumn("load_mw", F.coalesce("ail_forecast_mw", "ail_mw")).drop("loaded_at"))
    lag24 = sd.select((F.col("begin_datetime_mpt") + F.expr("INTERVAL 24 HOURS")).alias("begin_datetime_mpt"),
                      F.col("dispatchable_available_mw").alias("dispatchable_lag24_mw"))
    snaps = (bronze("aeso_fundamentals_snapshots")
             .withColumn("snapshot_mpt", F.from_utc_timestamp("snapshot_at", "America/Edmonton"))
             .filter(F.col("snapshot_mpt") < F.date_trunc("DAY", "begin_datetime_mpt"))   # known before the day began
             .groupBy("begin_datetime_mpt")
             .agg(*[F.max_by(c, "snapshot_at").alias(f"snap_{c}") for c in
                    ("ail_forecast_mw", "dispatchable_available_mw", "import_atc_mw", "wind_solar_forecast_mw")]))
    published = bronze("aeso_wind_solar_published").select(
        F.col("forecast_datetime_mpt").alias("begin_datetime_mpt"),
        F.col("wind_solar_forecast_mw").alias("published_wind_solar_mw"))
    return (sd.join(lag24, "begin_datetime_mpt", "left").join(snaps, "begin_datetime_mpt", "left")
            .join(published, "begin_datetime_mpt", "left")
            .withColumn("load_dayahead_mw", F.coalesce("snap_ail_forecast_mw", "load_mw"))
            .withColumn("dispatchable_dayahead_mw", F.coalesce("snap_dispatchable_available_mw", "dispatchable_lag24_mw"))
            .withColumn("import_atc_dayahead_mw", F.coalesce("snap_import_atc_mw", "import_atc_mw"))
            .withColumn("wind_solar_dayahead_mw", F.coalesce("snap_wind_solar_forecast_mw", "published_wind_solar_mw"))
            .withColumn("dayahead_source", F.when(F.col("snap_wind_solar_forecast_mw").isNotNull(), "snapshot")
                        .when(F.col("published_wind_solar_mw").isNotNull(), "published_file").otherwise(None))
            .drop("snap_ail_forecast_mw", "snap_dispatchable_available_mw", "snap_import_atc_mw",
                  "snap_wind_solar_forecast_mw", "published_wind_solar_mw", "dispatchable_lag24_mw"))


@dp.materialized_view(comment=(
    "Gold: one row per Mountain Time hour with the settled pool price (y), AESO forecast, the wind + solar "
    "regressor and the supply fundamentals (forecast load, available dispatchable MW, supply cushion). Future hours have y = NULL and a forecast regressor. Feeds the forecast notebook and Genie."))
@dp.expect_or_drop("valid_hour", "ds IS NOT NULL")
@dp.expect("has_regressor", "wind_solar_mw IS NOT NULL")
def gold_price_features_hourly():
    price = spark.read.table("silver_pool_price_hourly")
    wind = spark.read.table("silver_wind_solar_hourly").select(
        F.col("forecast_transaction_date").alias("ds"), F.col("regressor_mw").alias("wind_solar_mw"),
        "most_likely_mw", "actual_mw", "regressor_source", "is_imputed")
    supply = spark.read.table("silver_supply_demand_hourly").select(
        F.col("begin_datetime_mpt").alias("ds"), "load_mw", "ail_mw", "dispatchable_available_mw", "outage_mw",
        "import_atc_mw", "load_dayahead_mw", "dispatchable_dayahead_mw", "import_atc_dayahead_mw",
        "wind_solar_dayahead_mw", "dayahead_source")
    return (price.withColumnRenamed("begin_datetime_mpt", "ds").join(wind, "ds", "full_outer")
            .join(supply, "ds", "left")
            # Supply cushion: MW left once forecast load is served by available dispatchable generation, wind and
            # solar, and intertie imports. A thin cushion reaches the expensive end of the offer stack (spikes).
            .withColumn("supply_cushion_mw", F.col("dispatchable_available_mw") + F.col("wind_solar_mw")
                        + F.coalesce("import_atc_mw", F.lit(0)) - F.col("load_mw"))
            .withColumn("net_load_mw", F.col("load_mw") - F.col("wind_solar_mw") - F.coalesce("import_atc_mw", F.lit(0)))
            # The same, as known before the day began: what backtests feed the model for the test day.
            .withColumn("supply_cushion_dayahead_mw", F.col("dispatchable_dayahead_mw") + F.col("wind_solar_dayahead_mw")
                        + F.coalesce("import_atc_dayahead_mw", F.lit(0)) - F.col("load_dayahead_mw"))
            .withColumn("net_load_dayahead_mw", F.col("load_dayahead_mw") - F.col("wind_solar_dayahead_mw")
                        - F.coalesce("import_atc_dayahead_mw", F.lit(0)))
            .select("ds", "begin_datetime_utc", F.col("pool_price").alias("y"), "forecast_pool_price",
                    "rolling_30day_avg", "wind_solar_mw", "most_likely_mw", "actual_mw", "regressor_source",
                    "is_imputed", "load_mw", "ail_mw", "dispatchable_available_mw", "outage_mw", "import_atc_mw",
                    "supply_cushion_mw", "net_load_mw", "wind_solar_dayahead_mw", "supply_cushion_dayahead_mw",
                    "net_load_dayahead_mw", "dayahead_source",
                    (F.hour("ds") + 1).alias("hour_ending"), F.dayofweek("ds").alias("day_of_week"),
                    F.col("pool_price").isNotNull().alias("is_settled")))
