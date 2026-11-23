# ML: forecast, backtest, business value

How the forecast notebook and its models work. The method is in `src/ml/forecast_lib.py` (pure pandas/numpy); the notebook `src/ml/pool_price_forecast.py` tells the story and writes the tables.

## Models

| Model | Function | Detail |
| --- | --- | --- |
| HMM | `fit_hmm` | 3-state Gaussian on price, states sorted by mean: 0 Low, 1 Normal, 2 Spike. Gives states per hour and the transition matrix |
| Prophet | `fit_prophet` | Daily + weekly seasonality, no yearly, `wind_solar_mw` regressor, floored at $0 |
| Monte Carlo | `monte_carlo` | 500 paths from the last HMM state; each hour transitions with the matrix and draws from that state's Gaussian, clipped to [0, 999.99] |
| Regime-aware Prophet | `forecast_all` | Prophet without Spike-state hours, `changepoint_prior_scale` 0.001 (default 0.05) |
| Seasonal Monte Carlo | `seasonal_factors`, `apply_seasonality` | Per-state hour-of-day factors (state-hour mean / state mean) applied to each draw |
| Ensemble | `ensemble_weights` | Prophet weight at hour h = P(regime unchanged after h hours) = A[s,s]^h, clipped to `[weight_low, weight_high]`; the rest goes to the seasonal MC median |
| Fundamentals model | `fit_fundamentals`, `gate_weight` | Gradient-boosted price (absolute-error loss, last 120 days) on `FUND_X`: supply cushion, net load, wind/solar, load, hour, day of week. Only when the recipe has `fundamentals_gate` [low, high]: the forecast blends towards it below `high` MW of cushion, fully at `low` |

`forecast_regime` per hour is the most common state across the paths; `p_spike` is the share of paths in Spike; `p_above_150` is the share of seasonal MC paths above $150. `fundamentals_price` and `fundamentals_weight` show the cushion model's part.

**Why the cushion model is gated, not a Prophet regressor:** price against cushion is a hockey stick (flat above about 2,500 MW, steep below 1,500). A linear Prophet regressor cannot use it, and the fundamentals model used everywhere hurt quiet days. See `docs/decisions.md` #20 to #22.

## Jobs: the self-improving lifecycle

| Job | When | What |
| --- | --- | --- |
| `aeso-hourly` → task `forecast` | Hourly | Refit with the **`@champion`'s config** (version tag `config`), overwrite `aeso_price_forecast_output`, append to `aeso_forecast_history` |
| `aeso-weekly-retrain` | Mondays 05:30 MPT | `train_challenger.py`: try a grid of recipes (Prophet settings and cushion gates) on the 7 days before the evaluation window, retrain the best on all history, register it, set **`@challenger`**. Job parameter `candidate` submits a named grid recipe instead |
| `aeso-evaluate-challenger` | **Model update trigger**: `MODEL_ALIAS_SET` on `pool_price_ensemble`, alias `challenger` | `evaluate_challenger.py`: walk-forward on the same last 14 days for both recipes; promote if capture +1 pp **and** MAE ≤ 1.05x; log to `aeso_model_promotions`; rewrite the backtest tables for the resulting champion; then business value and governance |
| `aeso-daily-monitor` | 06:45 MPT | `daily_monitor.py`: score archived forecasts once prices settle (`aeso_live_accuracy`); fail the job (email) if live MAE > 1.5x the champion's evaluation MAE. `price_drivers.py`: explained variance per fundamental and price by cushion band (`aeso_price_drivers`) |

**Re-baseline on several windows:** `rebaseline_windows.py` scores versions on the latest covered 14 days plus Aug 20 and May 15 windows (`aeso_backtest_windows`; the app's accuracy score). It runs after every evaluation for `@champion`; `databricks bundle run aeso_rebaseline --params versions=5,champion` compares any versions.

**A model version is a recipe plus its fit.** The config (`regime_cps`, `weight_low`, `weight_high`, `prophet_cps`, `n_paths`, `regressors`, `fundamentals_gate`) is stored as the version tag `config`; versions without it mean the defaults in `forecast_lib.DEFAULT_CONFIG`. Evaluation compares recipes walk-forward (retrain at every cutoff), which is the honest test for time series.

**Submitting your own challenger:** `databricks bundle run aeso_weekly_retrain --params candidate=<grid name>`, or register a version with a `config` tag (`ensemble_model.register`) and set the `challenger` alias. The trigger does the rest. Never set `@champion` by hand except to roll back.

**Rollback:** `MlflowClient().set_registered_model_alias(name, "champion", <old version>)`; the next hourly run uses it.

## Backtest

`walk_forward()` in `forecast_lib.py` (shared by all three notebooks). The hourly job's `run_backtest=true` parameter re-scores `@champion` on 14 days; evaluation uses the same 14 days for both recipes. Windows are the last days with **day-ahead coverage** (`ensemble_model.complete_days`). For each, train on hours before midnight, forecast the day, compare with settled prices. Seven series are scored: the five model variants plus **AESO's forecast** and **same hour yesterday**. MAPE skips hours under $1/MWh.

**No look-ahead:** the test day sees the `DAYAHEAD` columns (published wind/solar forecast and the cushion built from it), never realised wind; training uses realised values. Until AESO posts a month's forecast file, the snapshot archive is the only day-ahead source, so the window can lag by up to a month. AESO's forecast is published only hours ahead, so it is a reference, not a fair day-ahead competitor.

## Business value

`src/ml/business_value.py`: (1) spike concentration from 2026 settled prices, no model; (2) the value of shifting `shift_hours` (4) hours a day of 1 MW from a strategy's expected top hours to its expected bottom hours, settled at actual prices, as a share of perfect foresight. MW and hours are **assumptions**, reported per MW and at 5 / 10 / 20 MW.

## Registered model

`energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble`, a pyfunc (`src/ml/ensemble_model.py`) holding the HMM parameters, seasonal factors and the serialized regime-aware Prophet. Input `ds` and `forecast_lib.FEATURES` (`wind_solar_mw`, `supply_cushion_mw`, `net_load_mw`, `load_mw`); output `ensemble_forecast_price`. A gated version also pickles the fundamentals model. Aliases: `@champion` (in production), `@challenger` (last submitted). Version tags: `config`, `role`, `evaluation`.

## Gotchas

- `%pip install` then `%restart_python` must be the first cells; widgets survive the restart.
- Prophet logs a line per fit through `cmdstanpy`; it is disabled in `fit_prophet` so the run output stays readable as evidence.
- The fundamentals model needs `scikit-learn` (serverless has it; it is in the model's `pip_requirements`).
- Keep `hmmlearn` and `prophet` versions pinned in the notebook and in `pip_requirements` of the registered model.
