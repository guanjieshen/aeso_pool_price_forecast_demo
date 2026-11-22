---
name: retrain-and-backtest
description: Use to change a model, ensemble weight, metric or backtest setting, rerun the walk-forward backtest, and promote a new pool_price_ensemble @champion.
---

# Retrain and backtest

1. **Read** [agents/ml.md](../../ml.md). Change method code in `src/ml/forecast_lib.py`; keep the notebook as the story.
2. **Smoke-test locally** on synthetic data if the change is in `forecast_lib.py`:
   `uv run --with prophet --with hmmlearn --with pandas python -c "import sys; sys.path.insert(0,'src/ml'); import forecast_lib"` plus a small `forecast_all` call.
3. **Deploy and run** `databricks bundle run aeso_daily_backtest`.
4. **Compare** the new leaderboard with the previous run:
   `SELECT run_timestamp, model_name, mae_cad_mwh FROM energy_canada_demos_catalog.aeso_price_forecast.aeso_backtest_metrics ORDER BY run_timestamp DESC, mae_cad_mwh`.
5. **Record the decision** as a new row in `docs/decisions.md`: what changed, the alternative, the before/after numbers.
6. **Refresh evidence** (skill **refresh-evidence**) and update the results table in `FE_BAR.md`.

The daily job always moves `@champion` to the new version. To roll back: `MlflowClient().set_registered_model_alias(name, "champion", <old version>)`.
