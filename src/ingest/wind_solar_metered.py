# Databricks notebook source
# MAGIC %md
# MAGIC # AESO wind + solar metered volumes: fetch and land raw
# MAGIC The public wind/solar CSV holds only about 2 days of actuals, too short to train on. This notebook finds every
# MAGIC WIND and SOLAR asset in the current supply/demand report and **lands their hourly metered volume records as
# MAGIC returned** (one JSON line per asset-hour, tagged with the asset's fuel type) in `raw/wind_solar_metered/`.
# MAGIC The pipeline ingests them into `bronze_wind_solar_metered` and sums them per hour into `aeso_wind_solar_metered`.
# MAGIC Metered data lags about 2 to 3 days and is revised, so each run re-lands the last few days.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("full_refresh", "false", ["false", "true"])  # true: re-land everything from the bootstrap date
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
BOOTSTRAP_DATE = "2026-01-01"
LOOKBACK_DAYS = 5          # metered volumes are revised after the fact
ASSETS_PER_CALL = 10       # the API rejects longer asset_ID lists (400 at 25)
API = "https://apimgw.aeso.ca/public/"
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import json, os
from datetime import date, datetime, timedelta, timezone
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

last = None
if dbutils.widgets.get("full_refresh") != "true" and spark.catalog.tableExists(f"{FQ}.aeso_wind_solar_metered"):
    last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) AS DATE) AS d FROM {FQ}.aeso_wind_solar_metered").first().d
today = datetime.now(ZoneInfo("America/Edmonton")).date()
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None else last - timedelta(days=LOOKBACK_DAYS)
print(f"Fetching metered volumes {start} .. {today}")

# COMMAND ----------

fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
folder = f"{LANDING}/wind_solar_metered/{fetched_at[:10]}"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/wind_solar_metered_{fetched_at.replace(':', '')}.jsonl"
ids, n, cursor = sorted(fuel_of), 0, start
with open(path, "w") as out:
    while cursor <= today:
        window_end = min(cursor + timedelta(days=30), today)
        for i in range(0, len(ids), ASSETS_PER_CALL):
            # endDate is exclusive on this endpoint (unlike the pool price report), so ask for one day past the window.
            for participant in get("meteredvolume-api/v1/meteredvolume/details", startDate=cursor.isoformat(),
                                   endDate=(window_end + timedelta(days=1)).isoformat(),
                                   asset_ID=",".join(ids[i:i + ASSETS_PER_CALL])):
                for asset in participant["asset_list"]:
                    for m in asset["metered_volume_list"]:
                        out.write(json.dumps({"pool_participant_ID": participant["pool_participant_ID"],
                                              "asset_ID": asset["asset_ID"], "fuel_type": fuel_of.get(asset["asset_ID"]),
                                              **m, "fetched_at": fetched_at}) + "\n")
                        n += 1
        print(f"  {cursor} .. {window_end}: {n} asset-hour records so far")
        cursor = window_end + timedelta(days=1)
if n == 0:
    os.remove(path)
    dbutils.notebook.exit("No metered volumes returned; nothing landed.")
print(f"Landed {n} raw asset-hour records -> {path}")
