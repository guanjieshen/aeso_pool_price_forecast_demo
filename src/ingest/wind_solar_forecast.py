# Databricks notebook source
# MAGIC %md
# MAGIC # AESO wind + solar forecast CSV: fetch and land raw
# MAGIC Downloads the AESO wind + solar 7-day forecast CSV (about 2 days of actuals plus 7 days ahead) and **lands the
# MAGIC file unchanged** in `raw/wind_solar_forecast/`, one file per run. The pipeline ingests it with Auto Loader into
# MAGIC `bronze_wind_solar_forecast`; `aeso_wind_solar_forecast` keeps the latest forecast per hour and the last
# MAGIC recorded actual. Because every run's file is kept, the forecast as it stood at each run is also kept (the
# MAGIC day-ahead wind forecast for backtests).

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
CSV_URL = ("http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/"
           "wind_solar_forecast/windsolar_rpt_longterm.csv")

# COMMAND ----------

import os
from datetime import datetime, timezone
import requests

resp = requests.get(CSV_URL, timeout=60)
resp.raise_for_status()
lines = [l for l in resp.text.splitlines() if l.strip()]
if len(lines) < 2:
    dbutils.notebook.exit("CSV had no rows; nothing landed.")

fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
folder = f"{LANDING}/wind_solar_forecast/{fetched_at[:10]}"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/windsolar_rpt_longterm_{fetched_at.replace(':', '')}.csv"
with open(path, "w") as f:
    f.write(resp.text)
print(f"Landed {len(lines) - 1} CSV rows -> {path}")
print("Header:", lines[0])
print("First row:", lines[1])
