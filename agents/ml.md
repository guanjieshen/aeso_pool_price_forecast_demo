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
| Ensemble | `ensemble_weights` | Prophet weight at hour h = P(regime unchanged after h hours) = A[s,s]^h, clipped to [0.3, 0.7]; the rest goes to the seasonal MC median |

`forecast_regime` per hour is the most common state across the paths; `p_spike` is the share of paths in Spike.

## Jobs

| Job | When | What |
| --- | --- | --- |
| `aeso_hourly` → task `forecast` | Hourly | Refit everything, overwrite `aeso_price_forecast_output`, log an MLflow run |
| `aeso_daily_backtest` | 06:45 MPT | Same plus the backtest (`run_backtest=true`), `business_value.py`, and registering `pool_price_ensemble` as `@champion` |

## Backtest

The last `backtest_days` (5) complete days. For each, train on hours before midnight, forecast the day, compare with settled prices. Seven series are scored: the five model variants plus **AESO's forecast** and **same hour yesterday**. MAPE skips hours under $1/MWh.

**Know the bias:** the test day's wind/solar is the observed value (a perfect wind forecast), so Prophet looks a little better than it would live. AESO's forecast is published only hours ahead, so it is a reference, not a fair day-ahead competitor.

## Business value

`src/ml/business_value.py`: (1) spike concentration from 2026 settled prices, no model; (2) the value of shifting `shift_hours` (4) hours a day of 1 MW from a strategy's expected top hours to its expected bottom hours, settled at actual prices, as a share of perfect foresight. MW and hours are **assumptions**, reported per MW and at 5 / 10 / 20 MW.

## Registered model

`energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble`, a pyfunc (`src/ml/ensemble_model.py`) holding the HMM parameters, seasonal factors and the serialized regime-aware Prophet. Input `ds`, `wind_solar_mw`; output `ensemble_forecast_price`. The notebook reloads `@champion` and predicts as a check.

## Gotchas

- `%pip install` then `%restart_python` must be the first cells; widgets survive the restart.
- Prophet logs a line per fit through `cmdstanpy`; it is disabled in `fit_prophet` so the run output stays readable as evidence.
- Keep `hmmlearn` and `prophet` versions pinned in the notebook and in `pip_requirements` of the registered model.
