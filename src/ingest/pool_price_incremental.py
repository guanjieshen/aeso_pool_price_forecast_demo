# Databricks notebook source
# MAGIC %md
# MAGIC # AESO pool price: fetch and land raw
# MAGIC Calls the AESO pool price report API and **lands the records exactly as returned** (JSON lines, one file per
# MAGIC run) in the Unity Catalog volume `raw/pool_price/`. The Lakeflow Spark Declarative Pipeline ingests them with
# MAGIC Auto Loader into the bronze streaming table `bronze_pool_price`, then types and deduplicates them into
# MAGIC `aeso_pool_price` (latest landed record per hour wins, so late price settlements flow through).
# MAGIC
# MAGIC Bootstraps from 2026-01-01 when nothing has landed; otherwise re-fetches from the last loaded MPT date.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("full_refresh", "false", ["false", "true"])
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
BOOTSTRAP_DATE = "2026-01-01"
API = "https://apimgw.aeso.ca/public/"
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import json, os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

def land(feed: str, records: list[dict]) -> str:
    """Write records as JSON lines to the landing volume, stamped with the fetch time. Returns the file path."""
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder = f"{LANDING}/{feed}/{fetched_at[:10]}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{feed}_{fetched_at.replace(':', '')}.jsonl"
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps({**r, "fetched_at": fetched_at}) + "\n")
    return path

headers = {"API-KEY": dbutils.secrets.get(catalog=CATALOG, schema=SCHEMA, key="aeso_api_key")}
full_refresh = dbutils.widgets.get("full_refresh") == "true"
last = None
if not full_refresh and spark.catalog.tableExists(f"{FQ}.aeso_pool_price"):
    last = spark.sql(f"SELECT CAST(MAX(begin_datetime_mpt) FILTER (WHERE pool_price IS NOT NULL) AS DATE) AS d FROM {FQ}.aeso_pool_price").first().d
today_mpt = datetime.now(ZoneInfo("America/Edmonton")).date()
start = date.fromisoformat(BOOTSTRAP_DATE) if last is None else last
print(f"Last settled MPT date: {last} -> fetching {start} .. {today_mpt}")

# COMMAND ----------

records, cursor = [], start
while cursor <= today_mpt:  # 31-day windows keep each response small; endDate is inclusive on this report
    window_end = min(cursor + timedelta(days=30), today_mpt)
    r = requests.get(API + "poolprice-api/v1.1/price/poolPrice", headers=headers, timeout=120,
                     params={"startDate": cursor.isoformat(), "endDate": window_end.isoformat()})
    if not r.ok:
        raise RuntimeError(f"AESO pool price API returned {r.status_code}: {r.text[:300]}")
    batch = r.json()["return"]["Pool Price Report"]
    records.extend(batch)
    print(f"  {cursor} .. {window_end}: {len(batch)} records")
    cursor = window_end + timedelta(days=1)

if not records:
    dbutils.notebook.exit("No records returned by the AESO API; nothing landed.")
path = land("pool_price", records)
print(f"Landed {len(records)} raw records -> {path}")
print("First record as landed:", json.dumps(records[0]))
