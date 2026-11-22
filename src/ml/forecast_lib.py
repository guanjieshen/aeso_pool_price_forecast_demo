"""Pool price models: 3-state HMM, Prophet, Monte Carlo, their converged variants and the ensemble.

Kept out of the notebook so the notebook reads as the story and this file as the method. Every function takes
pandas / numpy in and returns pandas / numpy out; nothing here touches Spark or MLflow.
Prices are CAD/MWh, `ds` is a naive Mountain Time hour start.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = ["Low", "Normal", "Spike"]
PRICE_CAP = 999.99            # AESO offer cap, CAD/MWh
HORIZON = 24
N_PATHS = 500
PROPHET_CPS = 0.05            # Prophet default changepoint prior
REGIME_PROPHET_CPS = 0.001    # much tighter: no chasing spikes once they are excluded
WEIGHT_BOUNDS = (0.3, 0.7)


# ---------- HMM ----------
def fit_hmm(prices: np.ndarray, seed: int = 42) -> dict:
    """3-state Gaussian HMM on price. States are re-ordered by ascending mean: 0 Low, 1 Normal, 2 Spike."""
    from hmmlearn.hmm import GaussianHMM

    x = prices.reshape(-1, 1)
    model = GaussianHMM(n_components=3, covariance_type="diag", n_iter=200, random_state=seed).fit(x)
    order = np.argsort(model.means_.ravel())
    rank = np.empty(3, dtype=int)
    rank[order] = np.arange(3)
    return {
        "states": rank[model.predict(x)],
        "means": model.means_.ravel()[order],
        "stds": np.sqrt(model.covars_.reshape(3, -1)[:, 0])[order],
        "trans": model.transmat_[np.ix_(order, order)],
    }


# ---------- Prophet ----------
def fit_prophet(train: pd.DataFrame, changepoint_prior_scale: float = PROPHET_CPS):
    """Daily + weekly seasonality, no yearly, wind + solar MW as a regressor."""
    import logging
    from prophet import Prophet

    logging.getLogger("cmdstanpy").disabled = True   # per-fit INFO lines drown the notebook output
    model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False,
                    changepoint_prior_scale=changepoint_prior_scale)
    model.add_regressor("wind_solar_mw")
    model.fit(train[["ds", "y", "wind_solar_mw"]])
    return model


def predict_prophet(model, future: pd.DataFrame) -> np.ndarray:
    return model.predict(future[["ds", "wind_solar_mw"]])["yhat"].clip(lower=0).to_numpy()   # floor at $0


# ---------- Monte Carlo ----------
def monte_carlo(hmm: dict, start_state: int, horizon: int = HORIZON, n_paths: int = N_PATHS, seed: int = 42):
    """Simulate price paths: transition with the HMM matrix, draw each hour from that state's Gaussian."""
    rng = np.random.default_rng(seed)
    cum = np.cumsum(hmm["trans"], axis=1)
    state = np.full(n_paths, start_state)
    states = np.empty((n_paths, horizon), dtype=int)
    prices = np.empty((n_paths, horizon))
    for h in range(horizon):
        state = np.minimum((rng.random(n_paths)[:, None] > cum[state]).sum(axis=1), 2)
        states[:, h] = state
        prices[:, h] = rng.normal(hmm["means"][state], hmm["stds"][state])
    return states, prices.clip(0, PRICE_CAP)


def seasonal_factors(ds: pd.Series, prices: np.ndarray, states: np.ndarray) -> np.ndarray:
    """factors[state, hour] = mean price in that state and hour of day / mean price in that state."""
    frame = pd.DataFrame({"hour": pd.to_datetime(ds).dt.hour.to_numpy(), "state": states, "y": prices})
    by_cell = frame.groupby(["state", "hour"])["y"].mean()
    by_state = frame.groupby("state")["y"].mean()
    factors = np.ones((3, 24))
    for (s, h), v in by_cell.items():
        if by_state[s] > 0:
            factors[s, h] = v / by_state[s]
    return factors


def apply_seasonality(states: np.ndarray, prices: np.ndarray, hours: np.ndarray, factors: np.ndarray) -> np.ndarray:
    return (prices * factors[states, hours[None, :]]).clip(0, PRICE_CAP)


# ---------- Ensemble ----------
def ensemble_weights(trans: np.ndarray, start_state: int, horizon: int = HORIZON) -> np.ndarray:
    """Prophet weight per hour = probability the regime has not changed after h hours, bounded [0.3, 0.7].

    A stable regime favours the seasonal Prophet curve; as the chance of a regime switch grows with the
    horizon, weight shifts to the Monte Carlo paths, which model the switching.
    """
    stay = trans[start_state, start_state] ** np.arange(1, horizon + 1)
    return np.clip(stay, *WEIGHT_BOUNDS)


def forecast_all(history: pd.DataFrame, future: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Fit every model on `history` (ds, y, wind_solar_mw) and forecast the `future` hours.

    Returns one row per future hour with every model's prediction, plus the fitted parts (HMM, seasonal
    factors, regime-aware Prophet) that the registered ensemble model needs.
    """
    y = history["y"].to_numpy()
    hmm = fit_hmm(y, seed)
    start_state = int(hmm["states"][-1])
    hours = pd.to_datetime(future["ds"]).dt.hour.to_numpy()
    horizon = len(future)

    prophet = predict_prophet(fit_prophet(history), future)
    regime_model = fit_prophet(history[hmm["states"] != 2], REGIME_PROPHET_CPS)   # exclude Spike hours
    regime_prophet = predict_prophet(regime_model, future)

    factors = seasonal_factors(history["ds"], y, hmm["states"])
    mc_states, mc_prices = monte_carlo(hmm, start_state, horizon, seed=seed)
    mc_seasonal = apply_seasonality(mc_states, mc_prices, hours, factors)
    weight = ensemble_weights(hmm["trans"], start_state, horizon)
    mc_seasonal_p50 = np.median(mc_seasonal, axis=0)

    modal_state = np.array([np.bincount(mc_states[:, h], minlength=3).argmax() for h in range(horizon)])
    out = pd.DataFrame({
        "forecast_datetime_mpt": pd.to_datetime(future["ds"]).to_numpy(),
        "hour_ending": hours + 1,
        "wind_solar_mw": future["wind_solar_mw"].to_numpy(),
        "prophet_forecast_price": prophet,
        "prophet_regime_price": regime_prophet,
        "mc_p10_price": np.percentile(mc_prices, 10, axis=0),
        "mc_p50_price": np.median(mc_prices, axis=0),
        "mc_p90_price": np.percentile(mc_prices, 90, axis=0),
        "mc_seasonal_p10_price": np.percentile(mc_seasonal, 10, axis=0),
        "mc_seasonal_p50_price": mc_seasonal_p50,
        "mc_seasonal_p90_price": np.percentile(mc_seasonal, 90, axis=0),
        "ensemble_weight_prophet": weight,
        "ensemble_forecast_price": weight * regime_prophet + (1 - weight) * mc_seasonal_p50,
        "forecast_regime": [REGIMES[s] for s in modal_state],
        "p_spike": (mc_states == 2).mean(axis=0),
        "hmm_current_regime": REGIMES[start_state],
    })
    fitted = {**hmm, "start_state": start_state, "factors": factors, "regime_prophet": regime_model}
    return out, fitted


# ---------- Accuracy ----------
def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """MAE, RMSE and MAPE. MAPE skips hours priced under $1/MWh, where percentage error is meaningless."""
    err = predicted - actual
    priced = actual >= 1.0
    return {
        "mae_cad_mwh": float(np.mean(np.abs(err))),
        "rmse_cad_mwh": float(np.sqrt(np.mean(err ** 2))),
        "mape_pct": float(np.mean(np.abs(err[priced] / actual[priced])) * 100) if priced.any() else None,
        "n_hours": int(len(actual)),
    }
