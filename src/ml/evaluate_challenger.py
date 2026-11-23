# Databricks notebook source
# MAGIC %md
# MAGIC # Evaluate challenger vs champion, promote if better
# MAGIC Self-improving loop, step 2 of 2. Runs when the **model update trigger** sees the `@challenger` alias set on
# MAGIC `pool_price_ensemble` (by the weekly retrain, or by anyone submitting a version). Both recipes are backtested
# MAGIC walk-forward on **the same** last `eval_days` complete days.
# MAGIC
# MAGIC **Promotion rule:** the challenger becomes `@champion` only if its load-shift **capture rate** beats the
# MAGIC champion's by at least `margin_pp` percentage points **and** its MAE is no more than `mae_guard` x the
# MAGIC champion's. Every decision is written to `aeso_model_promotions`. The backtest tables are then rewritten for
# MAGIC the resulting champion, so the app and Genie always describe the model in production.

# COMMAND ----------

# MAGIC %pip install -q hmmlearn==0.3.3 prophet==1.5.0
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("events", "")          # {{job.trigger.model.updates}} from the model update trigger
dbutils.widgets.text("eval_days", "14")
dbutils.widgets.text("margin_pp", "1.0")
dbutils.widgets.text("mae_guard", "1.05")
dbutils.widgets.text("experiment", "")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
EVAL_DAYS, MARGIN_PP = int(dbutils.widgets.get("eval_days")), float(dbutils.widgets.get("margin_pp"))
MAE_GUARD = float(dbutils.widgets.get("mae_guard"))
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{FQ}.pool_price_ensemble"
spark.conf.set("spark.sql.session.timeZone", "UTC")

import json, logging, warnings
from datetime import datetime, timezone
import mlflow
import pandas as pd
from mlflow import MlflowClient
import forecast_lib as fl
import ensemble_model as em
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)
client = MlflowClient(registry_uri="databricks-uc")

# COMMAND ----------

# Which version was submitted? The trigger passes a JSON list of updates; a manual run uses the current alias.
try:
    events = json.loads(dbutils.widgets.get("events") or "[]")
except json.JSONDecodeError:
    events = []
submitted = [e for e in events if e.get("full_name") == MODEL_NAME and e.get("alias_name") == "challenger"]
challenger_version = str(submitted[-1]["version"]) if submitted else em.config_for(MODEL_NAME, "challenger")[0]
champion_version, champion_cfg = em.config_for(MODEL_NAME, "champion")
print(f"Trigger events: {events or '(none: manual run)'}")
if challenger_version is None or challenger_version == champion_version:
    dbutils.notebook.exit(f"Nothing to evaluate (challenger v{challenger_version}, champion v{champion_version}).")
challenger_cfg = em.config_of_version(MODEL_NAME, challenger_version)
print(f"Champion   v{champion_version}: {json.dumps(champion_cfg, sort_keys=True)}")
print(f"Challenger v{challenger_version}: {json.dumps(challenger_cfg, sort_keys=True)}")

# COMMAND ----------

gold, history, _ = em.load_features(spark, FQ)
by_ds = gold.drop_duplicates("ds").set_index("ds")
cutoffs = em.complete_days(history, EVAL_DAYS)
detail = fl.walk_forward(history, by_ds, cutoffs, {"champion": champion_cfg, "challenger": challenger_cfg})
board = fl.leaderboard(detail, {"ensemble__champion": "model", "ensemble__challenger": "model",
                                "aeso_forecast": "baseline", "naive_yesterday": "baseline"})
print(f"Evaluation window {cutoffs[0].date()} .. {cutoffs[-1].date()} ({len(detail)} hours):\n"
      + board[["model_name", "model_type", "capture_rate_pct", "mae_cad_mwh", "rmse_cad_mwh", "mape_pct"]].round(2).to_string(index=False))

score = board.set_index("model_name")
champ, chall = score.loc["ensemble__champion"], score.loc["ensemble__challenger"]
better_capture = chall.capture_rate_pct >= champ.capture_rate_pct + MARGIN_PP
mae_ok = chall.mae_cad_mwh <= champ.mae_cad_mwh * MAE_GUARD
promote = bool(better_capture and mae_ok)
reason = (f"capture {chall.capture_rate_pct:.1f}% vs {champ.capture_rate_pct:.1f}% (needs +{MARGIN_PP:.1f} pp: "
          f"{'yes' if better_capture else 'no'}); MAE {chall.mae_cad_mwh:.2f} vs {champ.mae_cad_mwh:.2f} "
          f"(guard x{MAE_GUARD}: {'ok' if mae_ok else 'too high'})")
print(("PROMOTE: " if promote else "KEEP CHAMPION: ") + reason)

# COMMAND ----------

# MAGIC %md ## Act on the decision and record it

# COMMAND ----------

eval_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
if promote:
    client.set_registered_model_alias(MODEL_NAME, "champion", challenger_version)
    client.set_model_version_tag(MODEL_NAME, challenger_version, "role", "champion")
    client.set_model_version_tag(MODEL_NAME, str(champion_version), "role", "retired")
client.set_model_version_tag(MODEL_NAME, challenger_version, "evaluation", reason)
new_champion = challenger_version if promote else str(champion_version)

record = pd.DataFrame([{
    "evaluated_at": eval_ts, "champion_version": str(champion_version), "challenger_version": challenger_version,
    "decision": "promoted" if promote else "kept_champion", "reason": reason,
    "champion_capture_rate_pct": champ.capture_rate_pct, "challenger_capture_rate_pct": chall.capture_rate_pct,
    "champion_mae_cad_mwh": champ.mae_cad_mwh, "challenger_mae_cad_mwh": chall.mae_cad_mwh,
    "eval_start": cutoffs[0].date(), "eval_end": cutoffs[-1].date(), "eval_days": len(cutoffs),
    "champion_config": json.dumps(champion_cfg, sort_keys=True), "challenger_config": json.dumps(challenger_cfg, sort_keys=True)}])
spark.createDataFrame(record).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_model_promotions")

user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(dbutils.widgets.get("experiment") or f"/Users/{user}/aeso_pool_price_forecast")
with mlflow.start_run(run_name=f"evaluate-v{challenger_version}-vs-v{champion_version}") as run:
    mlflow.log_params({"champion_version": champion_version, "challenger_version": challenger_version,
                       "decision": record.decision[0], "eval_days": len(cutoffs), "margin_pp": MARGIN_PP, "mae_guard": MAE_GUARD})
    mlflow.log_metrics({"champion_capture_rate_pct": champ.capture_rate_pct, "challenger_capture_rate_pct": chall.capture_rate_pct,
                        "champion_mae_cad_mwh": champ.mae_cad_mwh, "challenger_mae_cad_mwh": chall.mae_cad_mwh})
    mlflow.log_table(board, "evaluation_leaderboard.json")
    run_id = run.info.run_id

# The backtest tables (app cards 8 and 9, business value, Genie) always describe the model now in production.
winner = "challenger" if promote else "champion"
current = detail.rename(columns={f"prophet_regime__{winner}": "prophet_regime", f"ensemble__{winner}": "ensemble"})
current = current[[c for c in current.columns if "__" not in c]]
series = {"prophet": "model", "mc": "model", "prophet_regime": "model", "mc_seasonal": "model", "ensemble": "model",
          "aeso_forecast": "baseline", "naive_yesterday": "baseline"}
meta = {"run_timestamp": eval_ts, "mlflow_run_id": run_id, "n_days": len(cutoffs), "champion_version": new_champion}
spark.createDataFrame(fl.leaderboard(current, series).assign(**meta)).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_backtest_metrics")
spark.createDataFrame(current.assign(run_timestamp=eval_ts, champion_version=new_champion)).write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_backtest_detail")
print(f"@champion is now v{new_champion}. Promotion history:")
print(spark.sql(f"SELECT evaluated_at, champion_version, challenger_version, decision, ROUND(champion_capture_rate_pct,1) AS champ_capture, "
                f"ROUND(challenger_capture_rate_pct,1) AS chall_capture, ROUND(champion_mae_cad_mwh,2) AS champ_mae, "
                f"ROUND(challenger_mae_cad_mwh,2) AS chall_mae FROM {FQ}.aeso_model_promotions ORDER BY evaluated_at").toPandas().to_string(index=False))
