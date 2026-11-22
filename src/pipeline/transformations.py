"""Lakeflow Spark Declarative Pipeline: bronze AESO tables -> silver -> gold features.

Materialized views, recomputed on every hourly job run. Expectations drop rows that cannot be right
(missing keys, prices outside the AESO market range) and record soft warnings for the rest.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

CATALOG = spark.conf.get("aeso.catalog")
SCHEMA = spark.conf.get("aeso.schema")
spark.conf.set("spark.sql.session.timeZone", "UTC")  # *_mpt columns are naive Mountain Time wall clock

def bronze(name):
    return spark.read.table(f"{CATALOG}.{SCHEMA}.{name}")


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
    "Gold: one row per Mountain Time hour with the settled pool price (y), AESO forecast and the wind + solar "
    "regressor. Future hours have y = NULL and a forecast regressor. Feeds the forecast notebook and Genie."))
@dp.expect_or_drop("valid_hour", "ds IS NOT NULL")
@dp.expect("has_regressor", "wind_solar_mw IS NOT NULL")
def gold_price_features_hourly():
    price = spark.read.table("silver_pool_price_hourly")
    wind = spark.read.table("silver_wind_solar_hourly").select(
        F.col("forecast_transaction_date").alias("ds"), F.col("regressor_mw").alias("wind_solar_mw"),
        "most_likely_mw", "actual_mw", "regressor_source", "is_imputed")
    return (price.withColumnRenamed("begin_datetime_mpt", "ds").join(wind, "ds", "full_outer")
            .select("ds", "begin_datetime_utc", F.col("pool_price").alias("y"), "forecast_pool_price",
                    "rolling_30day_avg", "wind_solar_mw", "most_likely_mw", "actual_mw", "regressor_source",
                    "is_imputed",
                    (F.hour("ds") + 1).alias("hour_ending"), F.dayofweek("ds").alias("day_of_week"),
                    F.col("pool_price").isNotNull().alias("is_settled")))
