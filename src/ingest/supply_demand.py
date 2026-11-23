# Databricks notebook source
# MAGIC %md
# MAGIC # Load AESO supply and demand fundamentals, and archive them as published
# MAGIC The pool price is set by the last offer needed to meet load, so it moves with the **supply cushion**:
# MAGIC available dispatchable MW + wind and solar + intertie imports - forecast load. This notebook loads the public
# MAGIC AESO feeds behind it and keeps a record of what was **known at each run**, so backtests cannot see the future.
# MAGIC
# MAGIC | Feed | Source | Table |
# MAGIC | --- | --- | --- |
# MAGIC | Load, actual and AESO forecast (about 3 days ahead) | `actualforecast-api/v1/load/albertaInternalLoad` | `aeso_supply_demand_hourly` |
# MAGIC | Capability by fuel, net of outages (forward hours too) | `aiesgencapacity-api/v1/AIESGenCapacity` | `aeso_supply_demand_hourly` |
# MAGIC | Intertie import capability (ATC) | `itc/v1/interchange` | `aeso_supply_demand_hourly` |
# MAGIC | Published wind and solar forecasts with actuals (monthly files) | aeso.ca `Wind_Data_<year>.csv`, `Solar_Data_<year>.csv` | `aeso_wind_solar_published` |
# MAGIC | Every forward hour as known at this run | the rows above + the 7-day wind/solar CSV | `aeso_fundamentals_snapshots` (append) |

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("full_refresh", "false", ["false", "true"])
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
TARGET = f"{FQ}.aeso_supply_demand_hourly"
BOOTSTRAP_DATE = "2026-01-01"
LOOKBACK_DAYS = 3     # actual load and outages are revised for a few days
FORWARD_DAYS = 3      # AESO publishes forecast load and planned capability ahead
API = "https://apimgw.aeso.ca/public/"
DISPATCHABLE = {"GAS", "HYDRO", "OTHER", "ENERGY STORAGE"}   # wind and solar come from the forecast/metered regressor
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import csv, io
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from pyspark.sql import functions as F

headers = {"API-KEY": dbutils.secrets.get(catalog=CATALOG, schema=SCHEMA, key="aeso_api_key")}

def get(path, **params):
    r = requests.get(API + path, headers=headers, params=params, timeout=300)
    if not r.ok:
        raise RuntimeError(f"AESO {path} returned {r.status_code}: {r.text[:300]}")
    return r.json()["return"]

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET} (
  begin_datetime_utc TIMESTAMP NOT NULL COMMENT 'Hour start, UTC. Primary key.',
  begin_datetime_mpt TIMESTAMP COMMENT 'Hour start, Mountain Time wall clock (timezone-naive).',
  ail_mw DOUBLE COMMENT 'Actual Alberta internal load, MW. NULL for future hours.',
  ail_forecast_mw DOUBLE COMMENT 'AESO forecast Alberta internal load, MW.',
  dispatchable_capability_mw DOUBLE COMMENT 'Maximum capability of gas, hydro, storage and other generation, MW.',
  dispatchable_available_mw DOUBLE COMMENT 'Available capability (maximum minus outages) of gas, hydro, storage and other, MW.',
  gas_available_mw DOUBLE COMMENT 'Available capability of gas generation, MW.',
  outage_mw DOUBLE COMMENT 'Dispatchable MW out on planned (MBO) and operational (OP) outages.',
  wind_solar_capability_mw DOUBLE COMMENT 'Installed (maximum) wind and solar capability, MW.',
  import_atc_mw DOUBLE COMMENT 'Intertie import capability (ATC), BC + Montana (capped by their flowgate) + Saskatchewan, MW.',
  loaded_at TIMESTAMP COMMENT 'When this row was last written (UTC).'
) COMMENT 'Bronze: hourly Alberta load (actual and forecast), generation capability net of outages and intertie import capability, from the AESO API. Includes future hours; values are as last published (see aeso_fundamentals_snapshots for as-known history).'
""")
if "import_atc_mw" not in spark.table(TARGET).columns:
    spark.sql(f"ALTER TABLE {TARGET} ADD COLUMNS (import_atc_mw DOUBLE COMMENT 'Intertie import capability (ATC), MW.')")
last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) FILTER (WHERE ail_mw IS NOT NULL AND import_atc_mw IS NOT NULL) AS DATE) AS d FROM {TARGET}").first().d
now_mpt = datetime.now(ZoneInfo("America/Edmonton"))
today = now_mpt.date()
full_refresh = dbutils.widgets.get("full_refresh") == "true"
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None or full_refresh else last - timedelta(days=LOOKBACK_DAYS)
end = today + timedelta(days=FORWARD_DAYS)
print(f"Fetching load, capability and intertie capability {start} .. {end}")

# COMMAND ----------

hours = defaultdict(lambda: defaultdict(float))
num = lambda v: float(v) if v not in (None, "") else None
fmt = "%Y-%m-%d %H:%M"
cursor = start
while cursor <= end:
    window_end = min(cursor + timedelta(days=30), end)
    # Load report: endDate inclusive.
    for r in get("actualforecast-api/v1/load/albertaInternalLoad", startDate=cursor.isoformat(),
                 endDate=window_end.isoformat())["Actual Forecast Report"]:
        h = hours[r["begin_datetime_mpt"]]
        h["utc"] = r["begin_datetime_utc"]
        h["ail_mw"], h["ail_forecast_mw"] = num(r["alberta_internal_load"]), num(r["forecast_alberta_internal_load"])
    # Capability report: endDate exclusive (like metered volumes), so ask for one day past the window.
    for fuel in get("aiesgencapacity-api/v1/AIESGenCapacity", startDate=cursor.isoformat(),
                    endDate=(window_end + timedelta(days=1)).isoformat()):
        kind = fuel["fuel_type"]
        for r in fuel["Hours"]:
            g, h = r["outage_grouping"], hours[r["begin_datetime_mpt"]]
            h["utc"] = r["begin_datetime_utc"]
            if kind in DISPATCHABLE:
                h["dispatchable_capability_mw"] += g["MC"]
                h["dispatchable_available_mw"] += g["AC"]
                h["outage_mw"] += g["MBO OUT"] + g["OP OUT"]
                if kind == "GAS":
                    h["gas_available_mw"] += g["AC"]
            else:
                h["wind_solar_capability_mw"] += g["MC"]
    # Intertie report: dates as yyyyMMdd (other formats return 500), hour ending 1..24, both ends inclusive.
    ties = defaultdict(dict)
    ret = get("itc/v1/interchange", startDate=cursor.strftime("%Y%m%d"), endDate=window_end.strftime("%Y%m%d"),
              startHE="1", endHE="24", version="1")
    for tie, body in ret.items():
        for a in (body or {}).get("Allocations", []) if isinstance(body, dict) else []:
            hour = (datetime.strptime(a["date"], "%Y-%m-%d") + timedelta(hours=int(a["he"]) - 1)).strftime(fmt)
            ties[hour][tie] = float((a.get("import") or {}).get("atc") or 0)
    for hour, t in ties.items():
        bc_matl = t.get("BcIntertie", 0) + t.get("MatlIntertie", 0)
        if "BcMatlFlowgate" in t:                 # BC and Montana share a flowgate limit
            bc_matl = min(bc_matl, t["BcMatlFlowgate"])
        hours[hour]["import_atc_mw"] = bc_matl + t.get("SkIntertie", 0)
    print(f"  {cursor} .. {window_end}: {len(hours)} hours so far")
    cursor = window_end + timedelta(days=1)

# COMMAND ----------

cols = ["ail_mw", "ail_forecast_mw", "dispatchable_capability_mw", "dispatchable_available_mw", "gas_available_mw",
        "outage_mw", "wind_solar_capability_mw", "import_atc_mw"]
rows = [(datetime.strptime(v["utc"], fmt), datetime.strptime(m, fmt), *[v.get(c) for c in cols])
        for m, v in hours.items() if "utc" in v and (v.get("dispatchable_available_mw") or v.get("ail_forecast_mw"))]
src = (spark.createDataFrame(rows, "begin_datetime_utc timestamp, begin_datetime_mpt timestamp, "
                                   + ", ".join(f"{c} double" for c in cols))
       .withColumn("loaded_at", F.current_timestamp()))
src.createOrReplaceTempView("supply_demand_updates")
print("MERGE:", spark.sql(f"""
MERGE INTO {TARGET} t USING supply_demand_updates s ON t.begin_datetime_utc = s.begin_datetime_utc
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""").first().asDict())

# COMMAND ----------

# MAGIC %md ## AESO's published wind and solar forecasts (history)
# MAGIC AESO posts a yearly file per fuel with each hour's forecast (min, most likely, max) next to the actual. It is
# MAGIC refreshed about monthly, so it lags; the snapshot archive below covers the hours since.

# COMMAND ----------

PUBLISHED = f"{FQ}.aeso_wind_solar_published"
def published(fuel, year):
    r = requests.get(f"https://www.aeso.ca/download/listedfiles/{fuel}_Data_{year}.csv", timeout=120)
    if not r.ok:
        return {}
    out = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        ts = row.get("FORECAST_DATE_LOCAL", "")
        try:
            ds = datetime.strptime(ts, fmt) if len(ts) > 10 else datetime.strptime(ts, "%Y-%m-%d")
        except ValueError:
            continue                              # the files end with a non-date checksum line
        out[ds] = tuple(num(row.get(k)) for k in ("MIN", "OPT", "MAX", "ACTUAL"))
    return out
pub = defaultdict(dict)
for year in sorted({date.fromisoformat(BOOTSTRAP_DATE).year, today.year}):
    for fuel in ("Wind", "Solar"):
        for ds, vals in published(fuel, year).items():
            pub[ds][fuel] = vals
prow = []
for ds, f in pub.items():
    w, s = f.get("Wind"), f.get("Solar")
    if not w or not s or w[1] is None or s[1] is None:
        continue
    prow.append((ds, w[1], s[1], w[1] + s[1], (w[2] or 0) - (w[0] or 0) + (s[2] or 0) - (s[0] or 0),
                 None if w[3] is None or s[3] is None else w[3] + s[3]))
if prow:
    (spark.createDataFrame(prow, "forecast_datetime_mpt timestamp, wind_forecast_mw double, solar_forecast_mw double, "
                                 "wind_solar_forecast_mw double, wind_solar_spread_mw double, wind_solar_actual_mw double")
     .withColumn("loaded_at", F.current_timestamp())
     .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(PUBLISHED))
    spark.sql(f"COMMENT ON TABLE {PUBLISHED} IS 'Bronze: AESO published hourly wind and solar forecasts (most likely, min-max spread) "
              "with actuals, from the yearly files on aeso.ca. Used as the day-ahead wind regressor in backtests.'")
print(f"Published wind/solar forecast hours: {len(prow)}"
      + (f" ({min(r[0] for r in prow)} .. {max(r[0] for r in prow)})" if prow else ""))

# COMMAND ----------

# MAGIC %md ## Snapshot archive: what was known at this run
# MAGIC Every run appends the forward hours (from now) with `snapshot_at`. A backtest for day D reads the last
# MAGIC snapshot taken before D began, which is exactly what a day-ahead forecaster had.

# COMMAND ----------

SNAPSHOTS = f"{FQ}.aeso_fundamentals_snapshots"
snapshot_at = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
now_naive = now_mpt.replace(tzinfo=None, minute=0, second=0, microsecond=0)
wind = (spark.table(f"{FQ}.aeso_wind_solar_forecast")
        .select(F.col("forecast_transaction_date").alias("begin_datetime_mpt"),
                F.col("most_likely_mw").alias("wind_solar_forecast_mw"),
                (F.col("max_mw") - F.col("min_mw")).alias("wind_solar_spread_mw")))
snap = (spark.table(TARGET).filter(F.col("begin_datetime_mpt") >= F.lit(now_naive))
        .select("begin_datetime_mpt", "ail_forecast_mw", "dispatchable_available_mw", "import_atc_mw")
        .join(wind, "begin_datetime_mpt", "full_outer")
        .filter(F.col("begin_datetime_mpt") >= F.lit(now_naive))
        .withColumn("snapshot_at", F.lit(snapshot_at)))
snap.write.mode("append").option("mergeSchema", "true").saveAsTable(SNAPSHOTS)
spark.sql(f"COMMENT ON TABLE {SNAPSHOTS} IS 'Bronze, append-only: every forward hour of load forecast, available dispatchable MW, "
          "import capability and wind/solar forecast as published at each hourly run (snapshot_at, UTC). Source of the "
          "day-ahead (as-known) features for backtests.'")

# COMMAND ----------

# MAGIC %md ## Verification

# COMMAND ----------

print(spark.sql(f"""
SELECT COUNT(*) AS total_hours, MIN(begin_datetime_mpt) AS first_hour_mpt, MAX(begin_datetime_mpt) AS last_hour_mpt,
       COUNT_IF(ail_mw IS NULL) AS future_hours, ROUND(AVG(ail_mw)) AS avg_load_mw,
       ROUND(AVG(dispatchable_available_mw)) AS avg_dispatchable_available_mw, ROUND(AVG(outage_mw)) AS avg_outage_mw,
       ROUND(AVG(import_atc_mw)) AS avg_import_atc_mw, ROUND(MIN(import_atc_mw)) AS min_import_atc_mw
FROM {TARGET}""").toPandas().to_string(index=False))
print(spark.sql(f"""
SELECT COUNT(DISTINCT snapshot_at) AS snapshots, COUNT(*) AS rows, MIN(begin_datetime_mpt) AS first_hour_mpt,
       MAX(begin_datetime_mpt) AS last_hour_mpt FROM {SNAPSHOTS}""").toPandas().to_string(index=False))
