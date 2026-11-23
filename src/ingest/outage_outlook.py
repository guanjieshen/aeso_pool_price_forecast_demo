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
# MAGIC The reports are HTML pages, so this notebook parses each table row into a record and **lands one JSON lines
# MAGIC file per run** in `raw/outage_outlook/`. The pipeline ingests it into `bronze_outage_outlook`; every run is a
# MAGIC snapshot (`snapshot_at`), so the outlook as published on any past day stays available. The hourly supply
# MAGIC cushion already uses the hourly outage data from the AIES capability API; this adds the longer view.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
BASE = "http://ets.aeso.ca/ets_web/ip/Market/Reports/"
REPORTS = {"daily": "DailyOutageReportServlet?contentType=html",
           "monthly": "MonthlyOutageForecastReportServlet?contentType=html"}
# Column order in both reports; the daily report adds Load. MBO = mothballed capacity.
FUELS = ["sc", "cogen", "cc", "gfs", "hydro", "wind", "solar", "energy_storage", "biomass_other", "mbo", "load"]
spark.conf.set("spark.sql.session.timeZone", "UTC")

# COMMAND ----------

import html, json, os, re
from datetime import datetime, timezone
import requests

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
        rows.append({"report": kind, "period_start": datetime.strptime(period, fmt).date().isoformat(),
                     **{f"{fuel}_mw": v for fuel, v in zip(FUELS, values)}})
    if not rows:
        raise RuntimeError(f"No rows parsed from the {kind} outage report; has its layout changed?")
    return rows

rows = report_rows("daily") + report_rows("monthly")
fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
folder = f"{LANDING}/outage_outlook/{fetched_at[:10]}"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/outage_outlook_{fetched_at.replace(':', '')}.jsonl"
with open(path, "w") as f:
    for r in rows:
        f.write(json.dumps({**r, "fetched_at": fetched_at}) + "\n")
daily = [r for r in rows if r["report"] == "daily"]
monthly = [r for r in rows if r["report"] == "monthly"]
print(f"Landed {len(rows)} records -> {path}")
print(f"daily: {len(daily)} days {daily[0]['period_start']} .. {daily[-1]['period_start']}; "
      f"monthly: {len(monthly)} months {monthly[0]['period_start']} .. {monthly[-1]['period_start']}")
