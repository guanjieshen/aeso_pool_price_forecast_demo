# Databricks notebook source
# MAGIC %md
# MAGIC # Load AESO Wind Solar Metered History
# MAGIC The public wind/solar CSV only covers about 2 days back, too short to train Prophet's wind regressor or
# MAGIC to backtest. This notebook rebuilds **actual** hourly wind and solar generation from the AESO metered
# MAGIC volume API: it finds every WIND and SOLAR asset in the current supply/demand report, pulls their hourly
# MAGIC metered MWh, and sums them per hour. Metered data lags about 2 to 3 days; the CSV covers that gap.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("full_refresh", "false", ["false", "true"])  # true: re-pull everything from the bootstrap date
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TARGET = f"{CATALOG}.{SCHEMA}.aeso_wind_solar_metered"
BOOTSTRAP_DATE = "2026-01-01"
LOOKBACK_DAYS = 5          # re-pull recent days: metered volumes are revised after the fact
ASSETS_PER_CALL = 10       # the API rejects longer asset_ID lists (400 at 25)
API = "https://apimgw.aeso.ca/public/"
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import requests

headers = {"API-KEY": dbutils.secrets.get(catalog=CATALOG, schema=SCHEMA, key="aeso_api_key")}

def get(path, **params):
    r = requests.get(API + path, headers=headers, params=params, timeout=180)
    if not r.ok:
        raise RuntimeError(f"AESO {path} returned {r.status_code}: {r.text[:300]}")
    return r.json()["return"]

assets = get("currentsupplydemand-api/v1/csd/generation/assets/current")["asset_list"]
fuel_of = {a["asset"]: a["fuel_type"] for a in assets if a["fuel_type"] in ("WIND", "SOLAR")}
print(f"Wind assets: {sum(f == 'WIND' for f in fuel_of.values())}, solar assets: {sum(f == 'SOLAR' for f in fuel_of.values())}")

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET} (
  begin_datetime_utc TIMESTAMP NOT NULL COMMENT 'Hour start, UTC. Primary key.',
  begin_datetime_mpt TIMESTAMP COMMENT 'Hour start, Mountain Time wall clock (timezone-naive).',
  wind_mw DOUBLE COMMENT 'Sum of metered wind generation for the hour, MWh (= average MW).',
  solar_mw DOUBLE COMMENT 'Sum of metered solar generation for the hour, MWh (= average MW).',
  wind_solar_mw DOUBLE COMMENT 'wind_mw + solar_mw.',
  asset_count INT COMMENT 'Number of wind and solar assets reporting in the hour.',
  loaded_at TIMESTAMP COMMENT 'When this row was last written (UTC).'
) COMMENT 'Bronze: hourly wind and solar generation rebuilt from AESO metered volumes per asset.'
""")
last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) AS DATE) AS d FROM {TARGET}").first().d
today = datetime.now(ZoneInfo("America/Edmonton")).date()
full_refresh = dbutils.widgets.get("full_refresh") == "true"
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None or full_refresh else last - timedelta(days=LOOKBACK_DAYS)
print(f"Fetching metered volumes {start} .. {today}")

# COMMAND ----------

hourly = defaultdict(lambda: {"WIND": 0.0, "SOLAR": 0.0, "n": 0})
ids = sorted(fuel_of)
cursor = start
while cursor <= today:
    window_end = min(cursor + timedelta(days=30), today)
    for i in range(0, len(ids), ASSETS_PER_CALL):
        chunk = ids[i:i + ASSETS_PER_CALL]
        # endDate is exclusive on this endpoint (unlike the pool price report), so ask for one day past the window.
        for participant in get("meteredvolume-api/v1/meteredvolume/details", startDate=cursor.isoformat(),
                               endDate=(window_end + timedelta(days=1)).isoformat(), asset_ID=",".join(chunk)):
            for asset in participant["asset_list"]:
                fuel = fuel_of.get(asset["asset_ID"])
                for m in asset["metered_volume_list"]:
                    key = (m["begin_date_utc"], m["begin_date_mpt"])
                    hourly[key][fuel] += float(m["metered_volume"] or 0)
                    hourly[key]["n"] += 1
    print(f"  {cursor} .. {window_end}: {len(hourly)} hours so far")
    cursor = window_end + timedelta(days=1)

if not hourly:
    dbutils.notebook.exit("No metered volumes returned; nothing to merge.")

# COMMAND ----------

from pyspark.sql import functions as F

fmt = "%Y-%m-%d %H:%M"
rows = [(datetime.strptime(u, fmt), datetime.strptime(m, fmt), v["WIND"], v["SOLAR"], v["WIND"] + v["SOLAR"], v["n"])
        for (u, m), v in hourly.items()]
src = (spark.createDataFrame(rows, "begin_datetime_utc timestamp, begin_datetime_mpt timestamp, wind_mw double, "
                                   "solar_mw double, wind_solar_mw double, asset_count int")
       .withColumn("loaded_at", F.current_timestamp()))
src.createOrReplaceTempView("metered_updates")
result = spark.sql(f"""
MERGE INTO {TARGET} t USING metered_updates s ON t.begin_datetime_utc = s.begin_datetime_utc
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""").first()
print(f"MERGE: {result.asDict()}")

# COMMAND ----------

# MAGIC %md ## Verification

# COMMAND ----------

summary = spark.sql(f"""
SELECT COUNT(*) AS total_hours, MIN(begin_datetime_mpt) AS first_hour_mpt, MAX(begin_datetime_mpt) AS last_hour_mpt,
       ROUND(AVG(wind_mw), 1) AS avg_wind_mw, ROUND(AVG(solar_mw), 1) AS avg_solar_mw,
       ROUND(MAX(wind_solar_mw), 1) AS max_wind_solar_mw, ROUND(AVG(asset_count), 1) AS avg_assets_reporting
FROM {TARGET}""")
print(summary.toPandas().to_string(index=False))
