# Databricks notebook source
# MAGIC %md
# MAGIC # AESO supply and demand fundamentals: fetch and land raw
# MAGIC The pool price is set by the last offer needed to meet load, so it moves with the **supply cushion**:
# MAGIC available dispatchable MW + wind and solar + intertie imports - forecast load. This notebook fetches the public
# MAGIC AESO feeds behind it and **lands them raw** in the `raw/` volume. Everything else happens in the pipeline.
# MAGIC
# MAGIC | Feed | Source | Landed as | Pipeline bronze |
# MAGIC | --- | --- | --- | --- |
# MAGIC | Load, actual and AESO forecast (about 3 days ahead) | `actualforecast-api/v1/load/albertaInternalLoad` | records as returned | `bronze_load` |
# MAGIC | Capability by fuel, net of outages (forward hours too) | `aiesgencapacity-api/v1/AIESGenCapacity` | one record per fuel-hour (AESO's keys with spaces renamed) | `bronze_gen_capacity` |
# MAGIC | Intertie import/export capability (ATC) | `itc/v1/interchange` | one record per intertie-hour | `bronze_intertie` |
# MAGIC | AESO published wind and solar forecasts with actuals (refreshed monthly) | aeso.ca `Wind_Data_<year>.csv`, `Solar_Data_<year>.csv` | the CSV file, only when it changed | `bronze_wind_solar_published` |
# MAGIC
# MAGIC Every run lands the **forward hours as published at that moment**, so the pipeline can rebuild what was known
# MAGIC before any day began (`aeso_fundamentals_snapshots`): backtests never see the future.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("full_refresh", "false", ["false", "true"])
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
BOOTSTRAP_DATE = "2026-01-01"
LOOKBACK_DAYS = 3     # actual load and outages are revised for a few days
FORWARD_DAYS = 3      # AESO publishes forecast load and planned capability ahead
API = "https://apimgw.aeso.ca/public/"
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import hashlib, json, os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

headers = {"API-KEY": dbutils.secrets.get(catalog=CATALOG, schema=SCHEMA, key="aeso_api_key")}
FETCHED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get(path, **params):
    r = requests.get(API + path, headers=headers, params=params, timeout=300)
    if not r.ok:
        raise RuntimeError(f"AESO {path} returned {r.status_code}: {r.text[:300]}")
    return r.json()["return"]

def land(feed: str, records: list[dict]) -> str:
    folder = f"{LANDING}/{feed}/{FETCHED_AT[:10]}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{feed}_{FETCHED_AT.replace(':', '')}.jsonl"
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps({**r, "fetched_at": FETCHED_AT}) + "\n")
    return path

last = None
if dbutils.widgets.get("full_refresh") != "true" and spark.catalog.tableExists(f"{FQ}.aeso_supply_demand_hourly"):
    last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) FILTER (WHERE ail_mw IS NOT NULL) AS DATE) AS d FROM {FQ}.aeso_supply_demand_hourly").first().d
today = datetime.now(ZoneInfo("America/Edmonton")).date()
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None else last - timedelta(days=LOOKBACK_DAYS)
end = today + timedelta(days=FORWARD_DAYS)
print(f"Fetching load, capability and intertie capability {start} .. {end}")

# COMMAND ----------

load, capacity, intertie, cursor = [], [], [], start
while cursor <= end:
    window_end = min(cursor + timedelta(days=30), end)
    # Load report: endDate inclusive.
    load += get("actualforecast-api/v1/load/albertaInternalLoad", startDate=cursor.isoformat(),
                endDate=window_end.isoformat())["Actual Forecast Report"]
    # Capability report: endDate exclusive (like metered volumes), so ask for one day past the window.
    for fuel in get("aiesgencapacity-api/v1/AIESGenCapacity", startDate=cursor.isoformat(),
                    endDate=(window_end + timedelta(days=1)).isoformat()):
        for h in fuel["Hours"]:
            g = h["outage_grouping"]
            capacity.append({"fuel_type": fuel["fuel_type"], "sub_fuel_type": fuel.get("sub_fuel_type"),
                             "begin_datetime_utc": h["begin_datetime_utc"], "begin_datetime_mpt": h["begin_datetime_mpt"],
                             "MC": g.get("MC"), "MBO_OUT": g.get("MBO OUT"), "OP_OUT": g.get("OP OUT"), "AC": g.get("AC")})
    # Intertie report: dates as yyyyMMdd (ISO dates return 500), hour ending 1..24, both ends inclusive.
    ret = get("itc/v1/interchange", startDate=cursor.strftime("%Y%m%d"), endDate=window_end.strftime("%Y%m%d"),
              startHE="1", endHE="24", version="1")
    for tie, body in ret.items():
        for a in (body or {}).get("Allocations", []) if isinstance(body, dict) else []:
            intertie.append({"tie": tie, "flowgate": a.get("flowgate"), "date": a["date"], "he": a["he"],
                             "import_atc": (a.get("import") or {}).get("atc"), "export_atc": (a.get("export") or {}).get("atc")})
    print(f"  {cursor} .. {window_end}: {len(load)} load, {len(capacity)} capability, {len(intertie)} intertie records")
    cursor = window_end + timedelta(days=1)

for feed, records in (("load", load), ("gen_capacity", capacity), ("intertie", intertie)):
    print(f"Landed {len(records)} raw {feed} records -> {land(feed, records)}")

# COMMAND ----------

# MAGIC %md ## AESO's published wind and solar forecast files
# MAGIC Yearly files with each hour's forecast (min, most likely, max) and the actual. AESO refreshes them about
# MAGIC monthly, so the CSV is landed only when its content changed (hash in the file name).

# COMMAND ----------

for year in sorted({date.fromisoformat(BOOTSTRAP_DATE).year, today.year}):
    for fuel in ("Wind", "Solar"):
        r = requests.get(f"https://www.aeso.ca/download/listedfiles/{fuel}_Data_{year}.csv", timeout=120)
        if not r.ok:
            print(f"  {fuel} {year}: HTTP {r.status_code}, skipped")
            continue
        digest = hashlib.sha256(r.content).hexdigest()[:12]
        folder = f"{LANDING}/wind_solar_published/{fuel.lower()}"
        os.makedirs(folder, exist_ok=True)
        path = f"{folder}/{fuel}_Data_{year}_{digest}.csv"
        if os.path.exists(path):
            print(f"  {fuel} {year}: unchanged ({digest})")
            continue
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"  {fuel} {year}: landed {len(r.content):,} bytes -> {path}")
