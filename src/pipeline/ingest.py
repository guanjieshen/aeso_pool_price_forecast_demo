"""Lakeflow Spark Declarative Pipeline, part 1: raw landing files -> bronze streaming tables -> conformed silver.

The job's ingest notebooks only fetch from AESO and land raw files in the Unity Catalog volume `raw/`. This file
owns ingestion from there:

* **Bronze** (`bronze_*`): streaming tables, one per feed, read incrementally with Auto Loader (`cloudFiles`, the
  engine behind `read_files`). Every landed record is kept with its source file and landing time, so the raw history
  is replayable and auditable.
* **Conformed silver** (`aeso_*`): materialized views that type the raw strings, keep the latest landed record per
  key (late settlements and revisions flow through) and aggregate (metered assets per hour, capability by fuel,
  interties). They keep the table names the rest of the build reads.
* **As-known archive** (`aeso_fundamentals_snapshots`): every forward hour of load, capability, imports and the wind
  forecast as it stood at each landing, which is what day-ahead backtests use.

Times: `*_mpt` columns are naive Mountain Time wall clock; the session time zone is pinned to UTC.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

LANDING = spark.conf.get("aeso.landing")
spark.conf.set("spark.sql.session.timeZone", "UTC")

MPT = "yyyy-MM-dd HH:mm"
DISPATCHABLE = ["GAS", "HYDRO", "OTHER", "ENERGY STORAGE"]


def autoload(feed: str, fmt: str, schema: str, **options):
    """Incrementally read new files under raw/<feed>/ and keep where each record came from."""
    reader = spark.readStream.format("cloudFiles").option("cloudFiles.format", fmt).schema(schema)
    for key, value in options.items():
        reader = reader.option(key, value)
    return (reader.load(f"{LANDING}/{feed}/")
            .withColumn("source_file", F.col("_metadata.file_path"))
            .withColumn("landed_at", F.col("_metadata.file_modification_time")))


def num(col: str):
    return F.expr(f"try_cast(nullif(trim({col}), '') AS DOUBLE)")


def ts(col: str, fmt: str = MPT):
    return F.to_timestamp(F.col(col), fmt)


def latest(df, keys: list[str], order: str = "fetched_ts"):
    """Keep the most recently landed record per key."""
    w = Window.partitionBy(*keys).orderBy(F.col(order).desc())
    return df.withColumn("_rank", F.row_number().over(w)).filter("_rank = 1").drop("_rank")


def fetched(df):
    return df.withColumn("fetched_ts", F.to_timestamp("fetched_at", "yyyy-MM-dd'T'HH:mm:ss'Z'"))


# ---------------------------------------------------------------- bronze: raw files, as landed

@dp.table(comment="Bronze: AESO pool price report records exactly as returned by the API (strings), one row per landed record.")
@dp.expect("has_hour", "begin_datetime_utc IS NOT NULL")
def bronze_pool_price():
    return autoload("pool_price", "json", "begin_datetime_utc STRING, begin_datetime_mpt STRING, pool_price STRING, "
                    "forecast_pool_price STRING, rolling_30day_avg STRING, fetched_at STRING")


@dp.table(comment="Bronze: AESO wind + solar 7-day forecast CSV rows as downloaded, one file per hourly run.")
@dp.expect("has_hour", "forecast_transaction_date IS NOT NULL")
def bronze_wind_solar_forecast():
    return autoload("wind_solar_forecast", "csv", "forecast_transaction_date STRING, fc_min STRING, fc_most_likely STRING, "
                    "fc_max STRING, fc_actual STRING, fc_mcr STRING, pct_min STRING, pct_most_likely STRING, pct_max STRING",
                    header="true")


@dp.table(comment="Bronze: AESO metered volume records per wind/solar asset and hour, as returned, tagged with fuel type.")
@dp.expect("has_asset_hour", "asset_ID IS NOT NULL AND begin_date_utc IS NOT NULL")
def bronze_wind_solar_metered():
    return autoload("wind_solar_metered", "json", "pool_participant_ID STRING, asset_ID STRING, fuel_type STRING, "
                    "begin_date_utc STRING, begin_date_mpt STRING, metered_volume STRING, fetched_at STRING")


@dp.table(comment="Bronze: AESO actual/forecast Alberta internal load records, as returned (history and about 3 days ahead).")
@dp.expect("has_hour", "begin_datetime_utc IS NOT NULL")
def bronze_load():
    return autoload("load", "json", "begin_datetime_utc STRING, begin_datetime_mpt STRING, alberta_internal_load STRING, "
                    "forecast_alberta_internal_load STRING, fetched_at STRING")


@dp.table(comment="Bronze: AESO AIES generation capability per fuel and hour: maximum capability (MC), MW out on "
                  "planned (MBO) and operational (OP) outages, available capability (AC). History and forward hours.")
@dp.expect("has_fuel_hour", "fuel_type IS NOT NULL AND begin_datetime_utc IS NOT NULL")
def bronze_gen_capacity():
    return autoload("gen_capacity", "json", "fuel_type STRING, sub_fuel_type STRING, begin_datetime_utc STRING, "
                    "begin_datetime_mpt STRING, MC DOUBLE, MBO_OUT DOUBLE, OP_OUT DOUBLE, AC DOUBLE, fetched_at STRING")


@dp.table(comment="Bronze: AESO intertie transfer capability per intertie (or flowgate) and hour ending, as returned.")
@dp.expect("has_tie_hour", "tie IS NOT NULL AND date IS NOT NULL AND he IS NOT NULL")
def bronze_intertie():
    return autoload("intertie", "json", "tie STRING, flowgate BOOLEAN, date STRING, he STRING, import_atc DOUBLE, "
                    "export_atc DOUBLE, fetched_at STRING")


@dp.table(comment="Bronze: AESO published yearly wind and solar forecast-vs-actual CSV files, as downloaded.")
def bronze_wind_solar_published():
    return (autoload("wind_solar_published", "csv", "forecast_date_local STRING, forecast_date_gmt STRING, pub_max STRING, "
                     "pub_min STRING, pub_opt STRING, pub_mcr STRING, pub_actual STRING", header="true")
            .withColumn("fuel", F.when(F.col("source_file").contains("/wind/"), "WIND").otherwise("SOLAR")))


@dp.table(comment="Bronze: AESO daily and monthly generation outage report rows (MW out by fuel), one snapshot per run.")
@dp.expect("has_period", "report IS NOT NULL AND period_start IS NOT NULL")
def bronze_outage_outlook():
    fuels = ["sc", "cogen", "cc", "gfs", "hydro", "wind", "solar", "energy_storage", "biomass_other", "mbo", "load"]
    return autoload("outage_outlook", "json", "report STRING, period_start STRING, "
                    + ", ".join(f"{f}_mw DOUBLE" for f in fuels) + ", fetched_at STRING")


# ---------------------------------------------------------------- conformed silver: typed, latest per key

@dp.materialized_view(comment="Silver: AESO hourly pool price, typed, latest landed record per hour (late settlements win).")
@dp.expect_or_drop("valid_hour", "begin_datetime_utc IS NOT NULL AND begin_datetime_mpt IS NOT NULL")
def aeso_pool_price():
    df = fetched(spark.read.table("bronze_pool_price"))
    df = df.select(ts("begin_datetime_utc").alias("begin_datetime_utc"), ts("begin_datetime_mpt").alias("begin_datetime_mpt"),
                   num("pool_price").alias("pool_price"), num("forecast_pool_price").alias("forecast_pool_price"),
                   num("rolling_30day_avg").alias("rolling_30day_avg"), "fetched_ts")
    return latest(df, ["begin_datetime_utc"]).withColumnRenamed("fetched_ts", "loaded_at")


@dp.materialized_view(comment="Silver: AESO wind + solar forecast per hour: the latest forecast, and the last actual recorded.")
@dp.expect_or_drop("valid_hour", "forecast_transaction_date IS NOT NULL")
def aeso_wind_solar_forecast():
    df = spark.read.table("bronze_wind_solar_forecast").select(
        ts("forecast_transaction_date").alias("forecast_transaction_date"), "landed_at",
        *[num(c).alias(n) for c, n in [("fc_min", "min_mw"), ("fc_most_likely", "most_likely_mw"), ("fc_max", "max_mw"),
                                       ("fc_actual", "actual_mw"), ("fc_mcr", "mcr_mw"), ("pct_min", "pct_min"),
                                       ("pct_most_likely", "pct_most_likely"), ("pct_max", "pct_max")]])
    cols = ["min_mw", "most_likely_mw", "max_mw", "mcr_mw", "pct_min", "pct_most_likely", "pct_max"]
    return (df.groupBy("forecast_transaction_date")
            .agg(*[F.max_by(c, "landed_at").alias(c) for c in cols],
                 F.expr("max_by(actual_mw, CASE WHEN actual_mw IS NOT NULL THEN landed_at END)").alias("actual_mw"),
                 F.max("landed_at").alias("loaded_at")))


@dp.materialized_view(comment="Silver: hourly wind and solar generation summed from metered assets (latest landed volume per asset-hour).")
@dp.expect_or_drop("valid_hour", "begin_datetime_utc IS NOT NULL")
def aeso_wind_solar_metered():
    df = fetched(spark.read.table("bronze_wind_solar_metered"))
    df = latest(df.select("asset_ID", "fuel_type", ts("begin_date_utc").alias("begin_datetime_utc"),
                          ts("begin_date_mpt").alias("begin_datetime_mpt"), num("metered_volume").alias("mwh"), "fetched_ts"),
                ["asset_ID", "begin_datetime_utc"])
    return (df.groupBy("begin_datetime_utc", "begin_datetime_mpt").agg(
        F.sum(F.when(F.col("fuel_type") == "WIND", F.col("mwh")).otherwise(0)).alias("wind_mw"),
        F.sum(F.when(F.col("fuel_type") == "SOLAR", F.col("mwh")).otherwise(0)).alias("solar_mw"),
        F.sum(F.coalesce("mwh", F.lit(0))).alias("wind_solar_mw"),
        F.count("*").cast("int").alias("asset_count"), F.max("fetched_ts").alias("loaded_at")))


def _capability(df):
    """Per hour: dispatchable (gas, hydro, storage, other) capability, availability and outages; wind/solar capability."""
    disp = F.col("fuel_type").isin(DISPATCHABLE)
    return df.groupBy(*[c for c in df.columns if c in ("snapshot_at", "begin_datetime_utc", "begin_datetime_mpt")]).agg(
        F.sum(F.when(disp, F.col("MC"))).alias("dispatchable_capability_mw"),
        F.sum(F.when(disp, F.col("AC"))).alias("dispatchable_available_mw"),
        F.sum(F.when(F.col("fuel_type") == "GAS", F.col("AC"))).alias("gas_available_mw"),
        F.sum(F.when(disp, F.coalesce("MBO_OUT", F.lit(0)) + F.coalesce("OP_OUT", F.lit(0)))).alias("outage_mw"),
        F.sum(F.when(~disp, F.col("MC"))).alias("wind_solar_capability_mw"))


def _imports(df):
    """Per hour: BC + Montana import ATC (capped by their shared flowgate) + Saskatchewan."""
    keys = [c for c in df.columns if c == "snapshot_at"] + ["begin_datetime_mpt"]
    p = df.groupBy(*keys).pivot("tie", ["BcIntertie", "MatlIntertie", "SkIntertie", "BcMatlFlowgate"]).agg(F.first("import_atc"))
    bc_matl = F.coalesce("BcIntertie", F.lit(0)) + F.coalesce("MatlIntertie", F.lit(0))
    capped = F.when(F.col("BcMatlFlowgate").isNotNull(), F.least(bc_matl, F.col("BcMatlFlowgate"))).otherwise(bc_matl)
    return p.select(*keys, (capped + F.coalesce("SkIntertie", F.lit(0))).alias("import_atc_mw"))


def _intertie_hour(df):
    return df.withColumn("begin_datetime_mpt", F.expr("to_timestamp(date, 'yyyy-MM-dd') + make_interval(0, 0, 0, 0, cast(he AS INT) - 1, 0, 0)"))


@dp.materialized_view(comment=(
    "Silver: hourly Alberta load (actual and AESO forecast), generation capability net of outages and intertie import "
    "capability, latest landed values per hour. Includes future hours; see aeso_fundamentals_snapshots for as-known values."))
@dp.expect_or_drop("valid_hour", "begin_datetime_utc IS NOT NULL")
def aeso_supply_demand_hourly():
    load = latest(fetched(spark.read.table("bronze_load")).select(
        ts("begin_datetime_utc").alias("begin_datetime_utc"), ts("begin_datetime_mpt").alias("begin_datetime_mpt"),
        num("alberta_internal_load").alias("ail_mw"), num("forecast_alberta_internal_load").alias("ail_forecast_mw"),
        "fetched_ts"), ["begin_datetime_utc"])
    cap = latest(fetched(spark.read.table("bronze_gen_capacity")).select(
        "fuel_type", "sub_fuel_type", ts("begin_datetime_utc").alias("begin_datetime_utc"),
        ts("begin_datetime_mpt").alias("begin_datetime_mpt"), "MC", "MBO_OUT", "OP_OUT", "AC", "fetched_ts"),
        ["fuel_type", "sub_fuel_type", "begin_datetime_utc"])
    tie = _intertie_hour(latest(fetched(spark.read.table("bronze_intertie")), ["tie", "date", "he"]))
    hours = (load.drop("fetched_ts").join(_capability(cap.drop("fetched_ts")), ["begin_datetime_utc", "begin_datetime_mpt"], "full_outer")
             .join(_imports(tie), "begin_datetime_mpt", "left"))
    loaded = load.select(F.max("fetched_ts").alias("loaded_at"))
    return hours.filter("dispatchable_available_mw IS NOT NULL OR ail_forecast_mw IS NOT NULL").crossJoin(loaded)


@dp.materialized_view(comment="Silver: AESO published hourly wind and solar forecasts (most likely, min-max spread) with actuals, latest file per hour.")
@dp.expect_or_drop("valid_hour", "forecast_datetime_mpt IS NOT NULL")
def aeso_wind_solar_published():
    hour = F.coalesce(F.to_timestamp("forecast_date_local", MPT), F.to_timestamp("forecast_date_local", "yyyy-MM-dd"))
    df = spark.read.table("bronze_wind_solar_published").select(
        "fuel", hour.alias("forecast_datetime_mpt"), num("pub_opt").alias("opt"), num("pub_min").alias("lo"), num("pub_max").alias("hi"),
        num("pub_actual").alias("actual"), "landed_at").filter("forecast_datetime_mpt IS NOT NULL")   # drops the checksum line
    df = latest(df, ["fuel", "forecast_datetime_mpt"], order="landed_at")
    wind, solar = F.col("fuel") == "WIND", F.col("fuel") == "SOLAR"
    return (df.groupBy("forecast_datetime_mpt").agg(
        F.max(F.when(wind, F.col("opt"))).alias("wind_forecast_mw"), F.max(F.when(solar, F.col("opt"))).alias("solar_forecast_mw"),
        F.sum("opt").alias("wind_solar_forecast_mw"), F.sum(F.col("hi") - F.col("lo")).alias("wind_solar_spread_mw"),
        F.expr("CASE WHEN count(actual) = 2 THEN sum(actual) END").alias("wind_solar_actual_mw"),
        F.count("*").alias("_fuels"), F.max("landed_at").alias("loaded_at"))
        .filter("_fuels = 2").drop("_fuels"))


@dp.materialized_view(comment=(
    "Silver: as-known archive. Every forward hour of load forecast, available dispatchable MW, import capability and "
    "wind/solar forecast as it stood at each hourly landing (snapshot_at, UTC hour). Day-ahead backtests read the last "
    "snapshot taken before a day began, so they never see the future."))
@dp.expect_or_drop("forward_only", "begin_datetime_mpt >= snapshot_mpt")
def aeso_fundamentals_snapshots():
    snap = lambda df, col: df.withColumn("snapshot_at", F.date_trunc("HOUR", col))
    load = snap(fetched(spark.read.table("bronze_load")), F.col("fetched_ts")).groupBy(
        "snapshot_at", ts("begin_datetime_mpt").alias("begin_datetime_mpt")).agg(
        F.max_by(num("forecast_alberta_internal_load"), "fetched_ts").alias("ail_forecast_mw"))
    cap = _capability(snap(fetched(spark.read.table("bronze_gen_capacity")), F.col("fetched_ts"))
                      .withColumn("begin_datetime_mpt", ts("begin_datetime_mpt"))
                      .select("snapshot_at", "begin_datetime_mpt", "fuel_type", "MC", "AC", "MBO_OUT", "OP_OUT")
                      ).select("snapshot_at", "begin_datetime_mpt", "dispatchable_available_mw")
    tie = _imports(_intertie_hour(snap(fetched(spark.read.table("bronze_intertie")), F.col("fetched_ts"))))
    wind = (snap(spark.read.table("bronze_wind_solar_forecast"), F.col("landed_at"))
            .groupBy("snapshot_at", ts("forecast_transaction_date").alias("begin_datetime_mpt"))
            .agg(F.max_by(num("fc_most_likely"), "landed_at").alias("wind_solar_forecast_mw"),
                 F.max_by(num("fc_max") - num("fc_min"), "landed_at").alias("wind_solar_spread_mw")))
    keys = ["snapshot_at", "begin_datetime_mpt"]
    return (load.join(cap, keys, "full_outer").join(tie, keys, "full_outer").join(wind, keys, "full_outer")
            .withColumn("snapshot_mpt", F.date_trunc("HOUR", F.from_utc_timestamp("snapshot_at", "America/Edmonton"))))


@dp.materialized_view(comment=(
    "Silver: AESO daily and monthly generation outage outlook (MW expected out by fuel: SC simple cycle, cogen, CC combined "
    "cycle, GFS gas-fired steam, hydro, wind, solar, storage, biomass/other; MBO = mothballed). Every landed snapshot is "
    "kept (snapshot_at, UTC); the latest snapshot is the current outlook."))
@dp.expect_or_drop("valid_period", "period_start IS NOT NULL")
def aeso_outage_outlook():
    df = spark.read.table("bronze_outage_outlook")
    return (df.withColumn("period_start", F.to_date("period_start"))
            .withColumn("snapshot_at", F.to_timestamp("fetched_at", "yyyy-MM-dd'T'HH:mm:ss'Z'"))
            .withColumn("gas_out_mw", F.col("sc_mw") + F.col("cogen_mw") + F.col("cc_mw") + F.col("gfs_mw"))
            .withColumn("dispatchable_out_mw", F.col("gas_out_mw") + F.col("hydro_mw") + F.col("energy_storage_mw")
                        + F.col("biomass_other_mw"))
            .drop("fetched_at", "source_file", "landed_at"))
