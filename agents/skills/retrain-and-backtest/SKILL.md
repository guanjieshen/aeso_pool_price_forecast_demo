---
name: retrain-and-backtest
description: Use to change a model, ensemble weight, metric or tuning grid, propose a challenger, check a promotion decision, or roll back @champion.
---

# Retrain, evaluate, promote

The models improve themselves: a weekly challenger, a model update trigger, a gated promotion. Read [agents/ml.md](../../ml.md) first.

| You want to | Do |
| --- | --- |
| Change the method (a model, the blend, a metric) | Edit `src/ml/forecast_lib.py`; smoke-test it locally on synthetic data with `uv run --with prophet --with hmmlearn --with pandas` |
| Try new settings | Edit `GRID` in `src/ml/train_challenger.py` |
| Propose a challenger now | `databricks bundle run aeso_weekly_retrain`. It sets `@challenger`, and `aeso-evaluate-challenger` starts by itself within about a minute |
| Submit your own version | Register it with `ensemble_model.register(...)` (it writes the `config` tag) and set the `challenger` alias |
| See why the model changed | `SELECT * FROM energy_canada_demos_catalog.aeso_price_forecast.aeso_model_promotions ORDER BY evaluated_at DESC`, or ask Genie |
| Roll back | `MlflowClient().set_registered_model_alias(name, "champion", <old version>)` |

After a change: deploy, run it, refresh evidence (skill **refresh-evidence**: `03_ml_backtest.md`, `06_model_lifecycle.md`), add a row to `docs/decisions.md` with the before and after numbers, and update `FE_BAR.md`.
