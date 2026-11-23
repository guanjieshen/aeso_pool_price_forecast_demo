# Databricks notebook source
# MAGIC %md
# MAGIC # Alberta Pool Price Forecasting - HMM Prophet Monte Carlo
# MAGIC Forecasts the next 24 hours of Alberta pool price (CAD/MWh, Mountain Time, AESO hour-ending).
# MAGIC
# MAGIC | Step | Model | Why |
# MAGIC | --- | --- | --- |
# MAGIC | 1 | 3-state Gaussian **HMM** | Labels every hour Low / Normal / Spike and learns how regimes switch |
# MAGIC | 2 | **Prophet** + wind/solar regressor | Daily and weekly shape of price, and how renewables push it down |
# MAGIC | 3 | **Monte Carlo** (500 paths) | Regime switching from the HMM, so spike risk shows up as a P10-P90 band |
# MAGIC | 4 | **Converge** | Regime-aware Prophet (no Spike hours, tight changepoints) and seasonal Monte Carlo |
# MAGIC | 5 | **Ensemble** | Blend weighted by the chance the current regime holds, bounded [0.3, 0.7] |
# MAGIC
# MAGIC Model code lives in `forecast_lib.py`. The training recipe comes from the `@champion` model version.
# MAGIC `run_backtest=true` adds the 5-day walk-forward backtest; the hourly job leaves it off.

# COMMAND ----------

# MAGIC %pip install -q hmmlearn==0.3.3 prophet==1.5.0
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.dropdown("run_backtest", "false", ["false", "true"])
dbutils.widgets.text("backtest_days", "14")
dbutils.widgets.text("experiment", "")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
RUN_BACKTEST = dbutils.widgets.get("run_backtest") == "true"
BACKTEST_DAYS = int(dbutils.widgets.get("backtest_days"))
FQ = f"{CATALOG}.{SCHEMA}"
spark.conf.set("spark.sql.session.timeZone", "UTC")   # *_mpt columns are naive Mountain Time wall clock

import logging, warnings
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

# COMMAND ----------

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import forecast_lib as fl

import ensemble_model
gold, history, future = ensemble_model.load_features(spark, FQ)
print(f"History: {len(history)} settled hours, {history.ds.min()} .. {history.ds.max()} MPT")
print(f"Forecast window: {future.ds.min()} .. {future.ds.max()} MPT ({len(future)} hours)")

# COMMAND ----------

# MAGIC %md ## 1-5. Fit every model and forecast the next 24 hours

# COMMAND ----------

import json

# The forecast uses the training recipe of the registered @champion (promoted by evaluate_challenger.py).
MODEL_NAME = f"{FQ}.pool_price_ensemble"
champion_version, config = ensemble_model.config_for(MODEL_NAME, "champion")
print(f"Champion: {MODEL_NAME} v{champion_version} config {json.dumps(config, sort_keys=True)}")

run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
forecast, fitted = fl.forecast_all(history, future, config=config)
states = fitted["states"]

regimes = pd.DataFrame({
    "regime": fl.REGIMES, "mean_cad_mwh": fitted["means"].round(2), "std_cad_mwh": fitted["stds"].round(2),
    "share_of_hours_pct": [round(100 * np.mean(states == s), 1) for s in range(3)],
    "p_stay_1h": np.diag(fitted["trans"]).round(3)})
print("HMM regimes (sorted by mean):\n" + regimes.to_string(index=False))
print("\nTransition matrix (rows = from, cols = to):\n" +
      pd.DataFrame(fitted["trans"].round(3), index=fl.REGIMES, columns=fl.REGIMES).to_string())
print(f"\nCurrent regime: {fl.REGIMES[fitted['start_state']]}")

# How far apart the models are, before and after convergence (mean absolute gap over 24h, CAD/MWh)
gap_before = float(np.mean(np.abs(forecast.prophet_forecast_price - forecast.mc_p50_price)))
gap_after = float(np.mean(np.abs(forecast.prophet_regime_price - forecast.mc_seasonal_p50_price)))
print(f"Prophet vs Monte Carlo gap: before {gap_before:.2f} -> after convergence {gap_after:.2f} CAD/MWh")

cols = ["forecast_datetime_mpt", "hour_ending", "prophet_forecast_price", "prophet_regime_price", "mc_p10_price",
        "mc_p90_price", "mc_seasonal_p50_price", "ensemble_forecast_price", "forecast_regime", "p_spike"]
print("\n" + forecast[cols].round(2).to_string(index=False))

# COMMAND ----------

# MAGIC %md ## Charts: last 7 days by regime, the 24h forecast, and convergence

# COMMAND ----------

import matplotlib.pyplot as plt

colors = {0: "#2ca02c", 1: "#1f77b4", 2: "#d62728"}
recent = history.assign(state=states).tail(24 * 7)
fig, ax = plt.subplots(figsize=(14, 5))
for s, part in recent.groupby("state"):
    ax.scatter(part.ds, part.y, s=8, color=colors[s], label=f"{fl.REGIMES[s]} regime")
ax.plot(recent.ds, recent.y, color="grey", lw=0.5, alpha=0.6)
f = forecast
ax.plot(f.forecast_datetime_mpt, f.prophet_forecast_price, "--", color="purple", label="Prophet")
ax.plot(f.forecast_datetime_mpt, f.mc_p50_price, color="orange", label="Monte Carlo median")
ax.fill_between(f.forecast_datetime_mpt, f.mc_p10_price, f.mc_p90_price, color="orange", alpha=0.2, label="MC P10-P90")
ax.set(title="Alberta pool price: 7-day history by HMM regime + 24h forecast", ylabel="CAD/MWh", xlabel="Mountain Time")
ax.legend(loc="upper left"); plt.tight_layout(); display(fig); plt.close(fig)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 4.5), sharey=True)
a1.plot(f.hour_ending, f.prophet_forecast_price, label="Prophet"); a1.plot(f.hour_ending, f.mc_p50_price, label="Monte Carlo median")
a1.set(title=f"Before: original models (gap {gap_before:.1f} $/MWh)", xlabel="Hour ending", ylabel="CAD/MWh"); a1.legend()
a2.plot(f.hour_ending, f.prophet_regime_price, label="Regime-aware Prophet")
a2.plot(f.hour_ending, f.mc_seasonal_p50_price, label="Seasonal Monte Carlo median")
a2.plot(f.hour_ending, f.ensemble_forecast_price, lw=3, color="black", label="Ensemble")
a2.set(title=f"After: converged + ensemble (gap {gap_after:.1f} $/MWh)", xlabel="Hour ending"); a2.legend()
plt.tight_layout(); display(fig); plt.close(fig)

# COMMAND ----------

# MAGIC %md ## Write the forecast (overwrite) and log the run to MLflow

# COMMAND ----------

import mlflow

user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(dbutils.widgets.get("experiment") or f"/Users/{user}/aeso_pool_price_forecast")
with mlflow.start_run(run_name=f"{'backtest' if RUN_BACKTEST else 'hourly'}-{run_ts:%Y%m%dT%H%M}") as run:
    mlflow.log_params({"history_hours": len(history), "history_start": str(history.ds.min()),
                       "history_end": str(history.ds.max()), "hmm_states": 3,
                       "champion_version": champion_version, "run_backtest": RUN_BACKTEST, **config})
    mlflow.log_metrics({**{f"hmm_mean_{r.lower()}": float(m) for r, m in zip(fl.REGIMES, fitted["means"])},
                        "gap_before_cad_mwh": gap_before, "gap_after_cad_mwh": gap_after,
                        "ensemble_mean_24h": float(forecast.ensemble_forecast_price.mean()),
                        "p_spike_max_24h": float(forecast.p_spike.max())})
    run_id = run.info.run_id

out = forecast.assign(model_run_timestamp=run_ts, mlflow_run_id=run_id)
(spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true")
 .saveAsTable(f"{FQ}.aeso_price_forecast_output"))
spark.sql(f"COMMENT ON TABLE {FQ}.aeso_price_forecast_output IS 'Latest 24h pool price forecast (CAD/MWh, MPT hour starts) from every model plus the ensemble. Overwritten each run; forecast_regime and p_spike come from the Monte Carlo paths.'")
print(f"Wrote {len(out)} forecast rows for run {run_ts} (MLflow run {run_id})")

# Keep every hourly forecast: daily_monitor.py scores them against prices once they settle (live accuracy).
(spark.createDataFrame(out.assign(champion_version=str(champion_version), config=json.dumps(config, sort_keys=True)))
 .write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_forecast_history"))

# COMMAND ----------

# MAGIC %md ## Backtest: rolling 5-day walk-forward (only when `run_backtest=true`)
# MAGIC For each of the last 5 complete days: train every model on the hours before midnight, forecast that day,
# MAGIC compare with settled prices. Two baselines anchor the scores: **AESO's own forecast** (published only a
# MAGIC few hours ahead, so a tough bar for a day-ahead model) and **same hour yesterday**.
# MAGIC The test day sees only what was known before it began: AESO's published wind/solar forecast and the supply
# MAGIC cushion built from it (the `*_dayahead_mw` gold columns), never the realised wind.

# COMMAND ----------

if not RUN_BACKTEST:
    dbutils.notebook.exit(f"Forecast written for run {run_ts}; backtest skipped (run_backtest=false).")

cutoffs = ensemble_model.complete_days(history, BACKTEST_DAYS)
by_ds = gold.drop_duplicates("ds").set_index("ds")
detail = (fl.walk_forward(history, by_ds, cutoffs, {"champion": config})
          .rename(columns={"prophet_regime__champion": "prophet_regime", "ensemble__champion": "ensemble"}))
SERIES = {"prophet": "model", "mc": "model", "prophet_regime": "model", "mc_seasonal": "model",
          "ensemble": "model", "aeso_forecast": "baseline", "naive_yesterday": "baseline"}
leaderboard = fl.leaderboard(detail, SERIES)
rows = leaderboard.to_dict("records")
print(f"Backtest {cutoffs[0].date()} .. {cutoffs[-1].date()} ({len(detail)} hours):\n" + leaderboard.round(2).to_string(index=False))

# COMMAND ----------

meta = {"run_timestamp": run_ts, "mlflow_run_id": run_id, "n_days": len(cutoffs), "champion_version": str(champion_version)}
spark.createDataFrame(leaderboard.assign(**meta)).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_backtest_metrics")
spark.createDataFrame(detail.assign(run_timestamp=run_ts, champion_version=str(champion_version))).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_backtest_detail")
with mlflow.start_run(run_id=run_id):
    for r in rows:
        mlflow.log_metrics({f"{r['model_name']}_{k}": v for k, v in r.items() if k in ("mae_cad_mwh", "rmse_cad_mwh", "mape_pct") and v is not None})
    mlflow.log_table(leaderboard, "backtest_leaderboard.json")

# COMMAND ----------

# MAGIC %md Registration and promotion live in the model lifecycle: `train_challenger.py` (weekly) registers a
# MAGIC challenger, and `evaluate_challenger.py` (model update trigger) promotes it only if it beats `@champion`.
