# Databricks notebook source
# MAGIC %md
# MAGIC # Load AESO Wind Solar Forecast
# MAGIC Downloads the AESO wind + solar long-term forecast CSV (about 2 days of actuals plus 7 days ahead) and
# MAGIC MERGEs it into `aeso_wind_solar_forecast`, upserting on `forecast_transaction_date`. Run hourly, the
# MAGIC table accumulates a history of forecasts and actuals that the public file alone does not keep.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TARGET = f"{CATALOG}.{SCHEMA}.aeso_wind_solar_forecast"
CSV_URL = ("http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/"
           "wind_solar_forecast/windsolar_rpt_longterm.csv")
spark.conf.set("spark.sql.session.timeZone", "UTC")  # keep naive MPT wall-clock values as-is

# COMMAND ----------

import csv, io
from datetime import datetime
import requests

resp = requests.get(CSV_URL, timeout=60)
resp.raise_for_status()
reader = csv.DictReader(io.StringIO(resp.text))

# CSV header -> column name. All numeric columns are cast to DoubleType; empty strings become nulls.
COLUMNS = {
    "Min": "min_mw", "Most Likely": "most_likely_mw", "Max": "max_mw", "Actual": "actual_mw",
    "MCR": "mcr_mw", "Pct Min": "pct_min", "Pct Most Likely": "pct_most_likely", "Pct Max": "pct_max",
}

def to_double(value):
    value = (value or "").strip()
    return float(value) if value else None

records = []
for row in reader:
    ts = (row.get("Forecast Transaction Date") or "").strip()
    if not ts:
        continue
    records.append((datetime.strptime(ts, "%Y-%m-%d %H:%M"), *[to_double(row.get(h)) for h in COLUMNS]))
print(f"Parsed {len(records)} rows from {CSV_URL}")
if not records:
    dbutils.notebook.exit("CSV had no rows; nothing to merge.")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, TimestampType, DoubleType

schema = StructType([StructField("forecast_transaction_date", TimestampType())] +
                    [StructField(c, DoubleType()) for c in COLUMNS.values()])
src = (spark.createDataFrame(records, schema).dropDuplicates(["forecast_transaction_date"])
       .withColumn("loaded_at", F.current_timestamp()))
src.createOrReplaceTempView("wind_solar_updates")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET} (
  forecast_transaction_date TIMESTAMP NOT NULL COMMENT 'Forecast hour start, Mountain Time wall clock (timezone-naive). Primary key.',
  min_mw DOUBLE COMMENT 'Low-case wind + solar generation forecast, MW.',
  most_likely_mw DOUBLE COMMENT 'Most likely wind + solar generation forecast, MW.',
  max_mw DOUBLE COMMENT 'High-case wind + solar generation forecast, MW.',
  actual_mw DOUBLE COMMENT 'Actual wind + solar generation, MW. Null for future hours.',
  mcr_mw DOUBLE COMMENT 'Maximum capability rating of the wind + solar fleet, MW.',
  pct_min DOUBLE COMMENT 'min_mw as a percent of MCR.',
  pct_most_likely DOUBLE COMMENT 'most_likely_mw as a percent of MCR.',
  pct_max DOUBLE COMMENT 'max_mw as a percent of MCR.',
  loaded_at TIMESTAMP COMMENT 'When this row was last written (UTC).'
) COMMENT 'Bronze: AESO wind + solar long-term forecast CSV, merged hourly.'
""")

# Keep a previously recorded actual if a later file drops it.
result = spark.sql(f"""
MERGE INTO {TARGET} t USING wind_solar_updates s ON t.forecast_transaction_date = s.forecast_transaction_date
WHEN MATCHED THEN UPDATE SET
  min_mw = s.min_mw, most_likely_mw = s.most_likely_mw, max_mw = s.max_mw,
  actual_mw = COALESCE(s.actual_mw, t.actual_mw), mcr_mw = s.mcr_mw, pct_min = s.pct_min,
  pct_most_likely = s.pct_most_likely, pct_max = s.pct_max, loaded_at = s.loaded_at
WHEN NOT MATCHED THEN INSERT *
""").first()
print(f"MERGE: {result.asDict()}")

# COMMAND ----------

# MAGIC %md ## Verification

# COMMAND ----------

summary = spark.sql(f"""
SELECT COUNT(*) AS total_rows, COUNT(actual_mw) AS hours_with_actual,
       MIN(forecast_transaction_date) AS first_hour_mpt, MAX(forecast_transaction_date) AS last_hour_mpt
FROM {TARGET}""")
print(summary.toPandas().to_string(index=False))
preview = spark.sql(f"SELECT * EXCEPT (loaded_at) FROM {TARGET} ORDER BY forecast_transaction_date DESC LIMIT 10")
print(preview.toPandas().to_string(index=False))
