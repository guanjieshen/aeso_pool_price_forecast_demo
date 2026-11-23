# Databricks notebook source
# MAGIC %md
# MAGIC # Weekly retrain: propose a challenger
# MAGIC Self-improving loop, step 1 of 2. Tries a small grid of training recipes on a **tuning window** that ends
# MAGIC before the evaluation window, so the challenger is never chosen on the days it is judged on.
# MAGIC The best recipe is retrained on all history, registered as a new `pool_price_ensemble` version and given the
# MAGIC `@challenger` alias. Setting that alias fires the model update trigger on `aeso-evaluate-challenger`.
# MAGIC
# MAGIC | Window | Days | Used for |
# MAGIC | --- | --- | --- |
# MAGIC | Tuning | `tune_days` before the evaluation window | Pick the challenger recipe |
# MAGIC | Evaluation | last `eval_days` complete days | Challenger vs champion (next job) |

# COMMAND ----------

# MAGIC %pip install -q hmmlearn==0.3.3 prophet==1.5.0
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("tune_days", "7")
dbutils.widgets.text("eval_days", "14")
dbutils.widgets.text("mae_guard", "1.05")   # a candidate's MAE may be at most 5% worse than the champion's
dbutils.widgets.text("experiment", "")
dbutils.widgets.text("candidate", "")      # submit this grid recipe as the challenger (skip the tuning pick)
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TUNE_DAYS, EVAL_DAYS = int(dbutils.widgets.get("tune_days")), int(dbutils.widgets.get("eval_days"))
MAE_GUARD = float(dbutils.widgets.get("mae_guard"))
CANDIDATE = dbutils.widgets.get("candidate").strip()
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{FQ}.pool_price_ensemble"
spark.conf.set("spark.sql.session.timeZone", "UTC")

import json, logging, warnings
from datetime import datetime, timezone
import mlflow
import pandas as pd
import forecast_lib as fl
import ensemble_model as em
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

# COMMAND ----------

gold, history, future = em.load_features(spark, FQ)
by_ds = gold.drop_duplicates("ds").set_index("ds")
tune_cutoffs = em.complete_days(history, TUNE_DAYS, skip_last=EVAL_DAYS)
champion_version, champion_cfg = em.config_for(MODEL_NAME, "champion")
print(f"Champion v{champion_version}: {json.dumps(champion_cfg, sort_keys=True)}")
print(f"Tuning window: {tune_cutoffs[0].date()} .. {tune_cutoffs[-1].date()} ({len(tune_cutoffs)} days)")

# The grid moves what matters most for decisions: how tightly the regime-aware Prophet follows trend changes and
# how far the blend may lean on it, plus the fundamentals gate (research: the supply cushion is the strongest
# public driver of spikes, so below a cushion threshold the forecast blends towards the fundamentals model).
GRID = {f"cps{cps}_w{lo}-{hi}": {**champion_cfg, "regime_cps": cps, "weight_low": lo, "weight_high": hi}
        for cps in (0.0005, 0.001, 0.005) for lo, hi in ((0.3, 0.7), (0.5, 0.9), (0.7, 1.0))}
GRID.update({f"cushion_gate_{lo}-{hi}": {**champion_cfg, "fundamentals_gate": [lo, hi]}
             for lo, hi in ((1000, 2500), (1500, 3000))})
candidates = {"champion": champion_cfg, **GRID}
detail = fl.walk_forward(history, by_ds, tune_cutoffs, candidates)
board = fl.leaderboard(detail, {f"ensemble__{n}": "model" for n in candidates})
board["candidate"] = board.model_name.str.removeprefix("ensemble__")
print("Tuning results (ensemble per candidate):\n" + board[["candidate", "capture_rate_pct", "mae_cad_mwh", "rmse_cad_mwh"]]
      .sort_values("capture_rate_pct", ascending=False).round(2).to_string(index=False))

# COMMAND ----------

champ = board.set_index("candidate").loc["champion"]
eligible = board[(board.candidate != "champion") & (board.mae_cad_mwh <= champ.mae_cad_mwh * MAE_GUARD)]
best = eligible.sort_values(["capture_rate_pct", "mae_cad_mwh"], ascending=[False, True]).head(1)
if CANDIDATE:   # a person submits an idea; the evaluation job's gate still decides
    if CANDIDATE not in GRID:
        raise ValueError(f"Unknown candidate {CANDIDATE!r}; choose from {sorted(GRID)}")
    best = board[board.candidate == CANDIDATE]
elif best.empty or best.iloc[0].capture_rate_pct <= champ.capture_rate_pct or \
        fl.resolve(candidates[best.iloc[0].candidate]) == champion_cfg:
    dbutils.notebook.exit(f"No candidate beat the champion on the tuning window "
                          f"(champion capture {champ.capture_rate_pct:.1f}%); no challenger this week.")
best = best.iloc[0]
challenger_cfg = fl.resolve(candidates[best.candidate])
print(f"Challenger recipe {best.candidate}: tuning capture {best.capture_rate_pct:.1f}% vs champion "
      f"{champ.capture_rate_pct:.1f}%, MAE {best.mae_cad_mwh:.2f} vs {champ.mae_cad_mwh:.2f}")

# COMMAND ----------

# MAGIC %md ## Retrain on all history, register, and submit as `@challenger`

# COMMAND ----------

user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(dbutils.widgets.get("experiment") or f"/Users/{user}/aeso_pool_price_forecast")
run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
forecast, fitted = fl.forecast_all(history, future, config=challenger_cfg)
with mlflow.start_run(run_name=f"challenger-{run_ts:%Y%m%dT%H%M}") as run:
    mlflow.log_params({**challenger_cfg, "candidate": best.candidate, "history_hours": len(history),
                       "tune_window": f"{tune_cutoffs[0].date()}..{tune_cutoffs[-1].date()}"})
    mlflow.log_metrics({"tune_capture_rate_pct": best.capture_rate_pct, "tune_mae_cad_mwh": best.mae_cad_mwh,
                        "champion_tune_capture_rate_pct": champ.capture_rate_pct})
    mlflow.log_table(board, "tuning_leaderboard.json")
    run_id = run.info.run_id

version = em.register(fitted, future[["ds", *fl.FEATURES]], forecast[["ensemble_forecast_price"]], MODEL_NAME, run_id,
                      {"role": "challenger", "proposed_by": "aeso-weekly-retrain", "candidate": best.candidate})
from mlflow import MlflowClient
MlflowClient(registry_uri="databricks-uc").set_registered_model_alias(MODEL_NAME, "challenger", version)
print(f"Registered {MODEL_NAME} v{version} as @challenger ({best.candidate}); the evaluation job will compare it with "
      f"@champion v{champion_version}.")
