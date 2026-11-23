# Databricks notebook source
# MAGIC %md
# MAGIC # Daily monitor: live accuracy and drift
# MAGIC The backtest says how a recipe *would* have done; this says how the forecasts we actually published *did*.
# MAGIC It scores every archived hourly forecast (`aeso_forecast_history`) against prices once they settle:
# MAGIC
# MAGIC - **By horizon** (1-6 h, 7-12 h, 13-24 h ahead): MAE of the ensemble, Prophet and the Monte Carlo median.
# MAGIC - **Day-ahead decision value:** for each settled day, the last forecast issued before that day starts, scored
# MAGIC   as load-shift capture against perfect foresight.
# MAGIC
# MAGIC **Drift check:** if the last 7 days' live ensemble MAE is more than `drift_ratio` x the champion's latest
# MAGIC evaluation MAE, this task fails, so the job's failure email reaches the owner.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("drift_ratio", "1.5")
dbutils.widgets.text("min_hours", "48")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
DRIFT_RATIO, MIN_HOURS = float(dbutils.widgets.get("drift_ratio")), int(dbutils.widgets.get("min_hours"))
FQ = f"{CATALOG}.{SCHEMA}"
spark.conf.set("spark.sql.session.timeZone", "UTC")

import numpy as np
import pandas as pd
from datetime import datetime, timezone
import forecast_lib as fl

# COMMAND ----------

if not spark.catalog.tableExists(f"{FQ}.aeso_forecast_history"):
    dbutils.notebook.exit("No archived forecasts yet; the hourly job starts the archive.")
scored = spark.sql(f"""
SELECT h.model_run_timestamp, h.forecast_datetime_mpt, h.champion_version, h.ensemble_forecast_price AS ensemble,
       h.prophet_forecast_price AS prophet, h.mc_p50_price AS mc, g.y AS actual, g.forecast_pool_price AS aeso_forecast,
       ROW_NUMBER() OVER (PARTITION BY h.model_run_timestamp ORDER BY h.forecast_datetime_mpt) AS hours_ahead
FROM {FQ}.aeso_forecast_history h
JOIN {FQ}.gold_price_features_hourly g ON g.ds = h.forecast_datetime_mpt AND g.y IS NOT NULL""").toPandas()
print(f"Settled forecast hours: {len(scored)} from {scored.model_run_timestamp.nunique()} forecast runs")
if len(scored) < MIN_HOURS:
    dbutils.notebook.exit(f"Only {len(scored)} settled forecast hours so far (need {MIN_HOURS}); monitoring starts once "
                          "the archive has history.")

# COMMAND ----------

scored["bucket"] = pd.cut(scored.hours_ahead, [0, 6, 12, 24], labels=["01-06h", "07-12h", "13-24h"])
rows = []
for bucket, part in scored.groupby("bucket", observed=True):
    for model in ("ensemble", "prophet", "mc", "aeso_forecast"):
        ok = part[model].notna()
        m = fl.metrics(part.actual[ok].to_numpy(), part[model][ok].to_numpy())
        rows.append({"view": "by_horizon", "segment": str(bucket), "model_name": model, **m})

# Day-ahead: per settled day, the last run issued before that day's midnight MPT (runs are stamped in UTC;
# MPT is UTC-7 or UTC-6, so a 7-hour shift picks a run issued before midnight in either season).
scored["target_day"] = pd.to_datetime(scored.forecast_datetime_mpt).dt.normalize()
scored["issued_mpt"] = pd.to_datetime(scored.model_run_timestamp) - pd.Timedelta(hours=7)
day_ahead = scored[scored.issued_mpt < scored.target_day]
day_ahead = day_ahead[day_ahead.model_run_timestamp == day_ahead.groupby("target_day").model_run_timestamp.transform("max")]
if len(day_ahead):
    detail = day_ahead.rename(columns={"target_day": "cutoff_date"})
    for model in ("ensemble", "prophet", "aeso_forecast"):
        ok = detail[model].notna()
        rows.append({"view": "day_ahead", "segment": "all settled days", "model_name": model,
                     "capture_rate_pct": fl.capture_rate(detail, model),
                     **fl.metrics(detail.actual[ok].to_numpy(), detail[model][ok].to_numpy())})

recent = scored[pd.to_datetime(scored.forecast_datetime_mpt) >= pd.to_datetime(scored.forecast_datetime_mpt).max() - pd.Timedelta(days=7)]
live_mae = fl.metrics(recent.actual.to_numpy(), recent.ensemble.to_numpy())["mae_cad_mwh"]
rows.append({"view": "last_7_days", "segment": "all horizons", "model_name": "ensemble", "mae_cad_mwh": live_mae, "n_hours": len(recent)})
live = pd.DataFrame(rows).assign(computed_at=datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None))
spark.createDataFrame(live).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.aeso_live_accuracy")
print(live.drop(columns="computed_at").round(2).to_string(index=False))

# COMMAND ----------

# MAGIC %md ## Drift check

# COMMAND ----------

ref = spark.sql(f"""SELECT mae_cad_mwh FROM {FQ}.aeso_backtest_metrics WHERE model_name = 'ensemble'
                   ORDER BY run_timestamp DESC LIMIT 1""").first()
if ref is None:
    dbutils.notebook.exit("No champion evaluation yet; drift check skipped.")
ratio = live_mae / ref.mae_cad_mwh
print(f"Live ensemble MAE (last 7 days, {len(recent)} h): {live_mae:.2f} vs champion evaluation MAE {ref.mae_cad_mwh:.2f} "
      f"-> ratio {ratio:.2f} (alert above {DRIFT_RATIO})")
if len(recent) >= MIN_HOURS and ratio > DRIFT_RATIO:
    raise RuntimeError(f"DRIFT: live MAE {live_mae:.2f} is {ratio:.2f}x the champion's evaluation MAE {ref.mae_cad_mwh:.2f}. "
                       "Check the data feeds, then run aeso-weekly-retrain to propose a new challenger.")
