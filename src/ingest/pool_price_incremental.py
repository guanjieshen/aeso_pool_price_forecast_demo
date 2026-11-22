# Databricks notebook source
# MAGIC %md
# MAGIC # AESO Pool Price Incremental Pipeline
# MAGIC Fetches hourly Alberta pool prices from the AESO API (`aeso-python-api`) and MERGEs them into
# MAGIC `aeso_pool_price`. Bootstraps from 2026-01-01 when the table is empty; otherwise re-fetches from the
# MAGIC last loaded date through today (MPT), so late price revisions are picked up. Exits early on zero rows.

# COMMAND ----------

# MAGIC %pip install -q aeso-python-api==0.2.1

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TARGET = f"{CATALOG}.{SCHEMA}.aeso_pool_price"
BOOTSTRAP_DATE = "2026-01-01"
spark.conf.set("spark.sql.session.timeZone", "UTC")  # keep naive MPT wall-clock values as-is

# COMMAND ----------

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from aeso import AESOAPI

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TARGET} (
  begin_datetime_utc TIMESTAMP NOT NULL COMMENT 'Settlement hour start, UTC. Primary key (MPT repeats an hour at DST end).',
  begin_datetime_mpt TIMESTAMP COMMENT 'Settlement hour start, Mountain Time wall clock (timezone-naive).',
  pool_price DOUBLE COMMENT 'Settled hourly pool price, CAD/MWh. Null until the hour settles.',
  forecast_pool_price DOUBLE COMMENT 'AESO published forecast pool price, CAD/MWh.',
  rolling_30day_avg DOUBLE COMMENT 'AESO 30-day rolling average pool price, CAD/MWh.',
  loaded_at TIMESTAMP COMMENT 'When this row was last written by the pipeline (UTC).'
) COMMENT 'Bronze: AESO hourly pool price report, incrementally merged from the AESO API.'
""")

last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) AS DATE) AS d FROM {TARGET}").first().d
today_mpt = datetime.now(ZoneInfo("America/Edmonton")).date()
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None else last
print(f"Last loaded MPT date: {last}  ->  fetching {start} .. {today_mpt}")

# COMMAND ----------

api_key = dbutils.secrets.get(catalog=CATALOG, schema=SCHEMA, key="aeso_api_key")
client = AESOAPI(api_key)

rows, cursor = [], start
while cursor <= today_mpt:  # 31-day windows keep each API response small
    window_end = min(cursor + timedelta(days=30), today_mpt)
    batch = client.get_pool_price_report(cursor.isoformat(), window_end.isoformat())
    rows.extend(batch)
    print(f"  {cursor} .. {window_end}: {len(batch)} rows")
    cursor = window_end + timedelta(days=1)

if not rows:
    dbutils.notebook.exit("No rows returned by the AESO API; nothing to merge.")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, TimestampType, DoubleType

schema = StructType([
    StructField("begin_datetime_utc", TimestampType()), StructField("begin_datetime_mpt", TimestampType()),
    StructField("pool_price", DoubleType()), StructField("forecast_pool_price", DoubleType()),
    StructField("rolling_30day_avg", DoubleType()),
])
src = (spark.createDataFrame([(r.begin_datetime_utc, r.begin_datetime_mpt, r.pool_price, r.forecast_pool_price,
                               r.rolling_30day_avg) for r in rows], schema)
       .dropDuplicates(["begin_datetime_utc"]).withColumn("loaded_at", F.current_timestamp()))
src.createOrReplaceTempView("pool_price_updates")

result = spark.sql(f"""
MERGE INTO {TARGET} t USING pool_price_updates s ON t.begin_datetime_utc = s.begin_datetime_utc
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""").first()
print(f"MERGE: {result.asDict()}")

# COMMAND ----------

# MAGIC %md ## Verification

# COMMAND ----------

verify = spark.sql(f"""
SELECT COUNT(*) AS total_rows, COUNT(pool_price) AS settled_hours,
       MIN(begin_datetime_mpt) AS first_hour_mpt, MAX(begin_datetime_mpt) AS last_hour_mpt,
       ROUND(AVG(pool_price), 2) AS avg_price_cad_mwh, MAX(pool_price) AS max_price_cad_mwh
FROM {TARGET}""")
print(verify.toPandas().to_string(index=False))  # text output, kept in the run export as evidence
