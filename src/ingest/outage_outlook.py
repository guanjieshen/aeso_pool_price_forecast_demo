# Databricks notebook source
# MAGIC %md
# MAGIC # Load AESO generation outage outlook (daily and monthly reports)
# MAGIC AESO publishes the generation MW expected to be **out on outage**, by fuel, from the outage records market
# MAGIC participants submit:
# MAGIC
# MAGIC | Report | Granularity | Horizon | URL |
# MAGIC | --- | --- | --- | --- |
# MAGIC | Daily Outage Report | MW out per day | this month to a few months ahead | `ets.aeso.ca/.../DailyOutageReportServlet` |
# MAGIC | Monthly Outage Report | average MW out per month | about 24 months ahead | `ets.aeso.ca/.../MonthlyOutageForecastReportServlet` |
# MAGIC
# MAGIC Every run **appends** a snapshot (`snapshot_at`) to `aeso_outage_outlook`, so the outlook as published on any
# MAGIC past day stays available, the same rule as the fundamentals archive. The hourly supply cushion already uses
# MAGIC the hourly outage data from the AIES capability API; this adds the longer view for planning.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TARGET = f"{CATALOG}.{SCHEMA}.aeso_outage_outlook"
BASE = "http://ets.aeso.ca/ets_web/ip/Market/Reports/"
REPORTS = {"daily": "DailyOutageReportServlet?contentType=html",
           "monthly": "MonthlyOutageForecastReportServlet?contentType=html"}
# Column order in both reports; the daily report adds Load. MBO = mothballed capacity.
FUELS = ["sc", "cogen", "cc", "gfs", "hydro", "wind", "solar", "energy_storage", "biomass_other", "mbo", "load"]
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import html, re
from datetime import datetime, timezone
import requests
from pyspark.sql import functions as F

def report_rows(kind: str) -> list[tuple]:
    r = requests.get(BASE + REPORTS[kind], timeout=120)
    r.raise_for_status()
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", r.text, flags=re.S)))
    text = re.sub(r"\s+", " ", text)
    # daily rows look like "01-Nov-2026 230 1439 ...", monthly rows like "Dec 2026 101 809 ..."
    pattern = r"(\d{2}-[A-Z][a-z]{2}-\d{4})((?: \d+){11})" if kind == "daily" else r"([A-Z][a-z]{2} \d{4})((?: \d+){10})(?= [A-Z]| *$)"
    fmt = "%d-%b-%Y" if kind == "daily" else "%b %Y"
    rows = []
    for period, numbers in re.findall(pattern, text):
        values = [float(v) for v in numbers.split()]
        values += [None] * (len(FUELS) - len(values))           # monthly has no Load column
        rows.append((kind, datetime.strptime(period, fmt).date(), *values))
    if not rows:
        raise RuntimeError(f"No rows parsed from the {kind} outage report; has its layout changed?")
    return rows

rows = report_rows("daily") + report_rows("monthly")
snapshot_at = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
df = (spark.createDataFrame(rows, "report string, period_start date, " + ", ".join(f"{f}_mw double" for f in FUELS))
      .withColumn("gas_out_mw", F.col("sc_mw") + F.col("cogen_mw") + F.col("cc_mw") + F.col("gfs_mw"))
      .withColumn("dispatchable_out_mw", F.col("gas_out_mw") + F.col("hydro_mw") + F.col("energy_storage_mw")
                  + F.col("biomass_other_mw"))
      .withColumn("snapshot_at", F.lit(snapshot_at)))
df.write.mode("append").option("mergeSchema", "true").saveAsTable(TARGET)
spark.sql(f"COMMENT ON TABLE {TARGET} IS 'Bronze, append-only: AESO daily and monthly generation outage outlook (MW expected out "
          "by fuel: SC simple cycle, cogen, CC combined cycle, GFS gas-fired steam, hydro, wind, solar, storage, biomass/other; "
          "MBO = mothballed). One snapshot per run (snapshot_at, UTC); the latest snapshot is the current outlook.'")

# COMMAND ----------

# MAGIC %md ## Verification

# COMMAND ----------

print(spark.sql(f"""
SELECT report, COUNT(*) AS periods, MIN(period_start) AS first_period, MAX(period_start) AS last_period,
       ROUND(AVG(gas_out_mw)) AS avg_gas_out_mw, ROUND(MAX(dispatchable_out_mw)) AS max_dispatchable_out_mw
FROM {TARGET} WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM {TARGET}) GROUP BY report ORDER BY report""").toPandas().to_string(index=False))
print(spark.sql(f"SELECT COUNT(DISTINCT snapshot_at) AS snapshots FROM {TARGET}").toPandas().to_string(index=False))
