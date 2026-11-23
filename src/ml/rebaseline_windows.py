# Databricks notebook source
# MAGIC %md
# MAGIC # Re-baseline: the same model versions on several 14-day windows, day-ahead features only
# MAGIC One 14-day window is a small sample: a quiet fortnight flatters a model and a spiky one punishes it. This
# MAGIC notebook scores registered versions walk-forward on several windows, feeding each test day only what was
# MAGIC known before it began (AESO's published wind/solar forecast and the cushion built from it).
# MAGIC
# MAGIC Default windows: the **latest** 14 days with day-ahead coverage, plus the two windows the fundamentals
# MAGIC research used for robustness, **Aug 20 to Sep 2** (BC/Montana intertie outage) and **May 15 to 28** (the
# MAGIC spikiest fortnight before August). Two of the three are spiky by choice; the per-window rows show it.

# COMMAND ----------

# MAGIC %pip install -q hmmlearn==0.3.3 prophet==1.5.0
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("versions", "5,champion")         # registered versions or aliases to score
dbutils.widgets.text("windows", "latest,2026-08-20,2026-05-15")   # start dates of 14-day windows ("latest" = last covered)
dbutils.widgets.text("days", "14")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{FQ}.pool_price_ensemble"
DAYS = int(dbutils.widgets.get("days"))
spark.conf.set("spark.sql.session.timeZone", "UTC")

import json, logging, warnings
from datetime import datetime, timezone
import pandas as pd
import forecast_lib as fl
import ensemble_model as em
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

gold, history, _ = em.load_features(spark, FQ)
by_ds = gold.drop_duplicates("ds").set_index("ds")
configs = {}
for v in [x.strip() for x in dbutils.widgets.get("versions").split(",") if x.strip()]:
    version, cfg = em.config_for(MODEL_NAME, v) if not v.isdigit() else (v, em.config_of_version(MODEL_NAME, v))
    configs[f"v{version}"] = cfg
    print(f"{v} -> v{version}: {json.dumps(cfg, sort_keys=True)}")

covered = em.complete_days(history, 10_000)          # every day with settled prices and day-ahead features
windows = {}
for w in [x.strip() for x in dbutils.widgets.get("windows").split(",") if x.strip()]:
    days = covered[-DAYS:] if w == "latest" else [d for d in covered if pd.Timestamp(w) <= d < pd.Timestamp(w) + pd.Timedelta(days=DAYS)]
    windows[f"{days[0].date()}..{days[-1].date()}"] = days

# COMMAND ----------

run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
rows = []
for label, cutoffs in windows.items():
    detail = fl.walk_forward(history, by_ds, cutoffs, configs)
    series = {f"ensemble__{n}": "model" for n in configs}
    series.update({"aeso_forecast": "baseline", "naive_yesterday": "baseline"})
    board = fl.leaderboard(detail, series)
    board["window"], board["n_days"], board["hours_above_100"] = label, len(cutoffs), int((detail.actual > 100).sum())
    rows.append(board)
result = pd.concat(rows, ignore_index=True)
result["model_name"] = result.model_name.str.removeprefix("ensemble__")
mean = (result.groupby("model_name")[["capture_rate_pct", "mae_cad_mwh"]].mean().reset_index()
        .assign(window="mean of windows", n_days=sum(len(c) for c in windows.values()), hours_above_100=None))
out = pd.concat([result, mean], ignore_index=True).assign(run_timestamp=run_ts)
cols = ["window", "model_name", "capture_rate_pct", "mae_cad_mwh", "n_days", "hours_above_100"]
print(out[cols].round(2).to_string(index=False))
spark.createDataFrame(out[cols + ["run_timestamp"]]).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_backtest_windows")
spark.sql(f"COMMENT ON TABLE {FQ}.aeso_backtest_windows IS 'Re-baseline: registered model versions scored walk-forward on several "
          "14-day windows with day-ahead features only (rebaseline_windows.py); window = mean of windows is the average.'")
