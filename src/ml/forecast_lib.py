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
SHIFT_HOURS = 4               # flexible hours moved per day in the decision-value metric (an assumption)

# A model "config" is the training recipe a registered version carries (as the version tag `config`).
# The weekly retrain proposes a challenger config; the evaluation job compares recipes walk-forward.
DEFAULT_CONFIG = {"prophet_cps": PROPHET_CPS, "regime_cps": REGIME_PROPHET_CPS,
                  "weight_low": WEIGHT_BOUNDS[0], "weight_high": WEIGHT_BOUNDS[1], "n_paths": N_PATHS}


def resolve(config: dict | None) -> dict:
    return {**DEFAULT_CONFIG, **(config or {})}


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
def ensemble_weights(trans: np.ndarray, start_state: int, horizon: int = HORIZON,
                     bounds: tuple[float, float] = WEIGHT_BOUNDS) -> np.ndarray:
    """Prophet weight per hour = probability the regime has not changed after h hours, bounded [0.3, 0.7].

    A stable regime favours the seasonal Prophet curve; as the chance of a regime switch grows with the
    horizon, weight shifts to the Monte Carlo paths, which model the switching.
    """
    stay = trans[start_state, start_state] ** np.arange(1, horizon + 1)
    return np.clip(stay, *bounds)


def forecast_all(history: pd.DataFrame, future: pd.DataFrame, seed: int = 42,
                 config: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Fit every model on `history` (ds, y, wind_solar_mw) and forecast the `future` hours with `config`.

    Returns one row per future hour with every model's prediction, plus the fitted parts (HMM, seasonal
    factors, regime-aware Prophet) that the registered ensemble model needs.
    """
    cfg = resolve(config)
    y = history["y"].to_numpy()
    hmm = fit_hmm(y, seed)
    start_state = int(hmm["states"][-1])
    hours = pd.to_datetime(future["ds"]).dt.hour.to_numpy()
    horizon = len(future)

    prophet = predict_prophet(fit_prophet(history, cfg["prophet_cps"]), future)
    regime_model = fit_prophet(history[hmm["states"] != 2], cfg["regime_cps"])   # exclude Spike hours
    regime_prophet = predict_prophet(regime_model, future)

    factors = seasonal_factors(history["ds"], y, hmm["states"])
    mc_states, mc_prices = monte_carlo(hmm, start_state, horizon, n_paths=int(cfg["n_paths"]), seed=seed)
    mc_seasonal = apply_seasonality(mc_states, mc_prices, hours, factors)
    weight = ensemble_weights(hmm["trans"], start_state, horizon, (cfg["weight_low"], cfg["weight_high"]))
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
    fitted = {**hmm, "start_state": start_state, "factors": factors, "regime_prophet": regime_model, "config": cfg}
    return out, fitted


# ---------- Walk-forward backtest (shared by the notebook, the weekly retrain and the evaluation) ----------
def walk_forward(history: pd.DataFrame, by_ds: pd.DataFrame, cutoffs: list, configs: dict[str, dict],
                 seed: int = 42) -> pd.DataFrame:
    """For each cutoff day: train on hours before midnight, forecast that day, keep actuals and baselines.

    Pieces every config shares (HMM, plain Prophet, Monte Carlo, seasonal factors) are fit once per day;
    only the regime-aware Prophet (per distinct `regime_cps`) and the blend (per weight bounds) vary.
    Columns: actual, prophet, mc, mc_seasonal, aeso_forecast, naive_yesterday, and per config `<name>`:
    `prophet_regime__<name>`, `ensemble__<name>`.
    """
    cfgs = {name: resolve(c) for name, c in configs.items()}
    days = []
    for cutoff in cutoffs:
        train = history[history.ds < cutoff]
        test = history[(history.ds >= cutoff) & (history.ds < cutoff + pd.Timedelta(days=1))].reset_index(drop=True)
        future = test[["ds", "wind_solar_mw"]]
        y = train["y"].to_numpy()
        hmm = fit_hmm(y, seed)
        start = int(hmm["states"][-1])
        hours = test.ds.dt.hour.to_numpy()
        states, prices = monte_carlo(hmm, start, len(test), n_paths=max(int(c["n_paths"]) for c in cfgs.values()), seed=seed)
        mc_seasonal = np.median(apply_seasonality(states, prices, hours, seasonal_factors(train.ds, y, hmm["states"])), axis=0)
        no_spikes = train[hmm["states"] != 2]
        regime = {cps: predict_prophet(fit_prophet(no_spikes, cps), future) for cps in {c["regime_cps"] for c in cfgs.values()}}
        day = pd.DataFrame({
            "cutoff_date": cutoff.date(), "forecast_hour": test.ds, "hour_ending": hours + 1, "actual": test.y,
            "prophet": predict_prophet(fit_prophet(train, DEFAULT_CONFIG["prophet_cps"]), future),
            "mc": np.median(prices, axis=0), "mc_seasonal": mc_seasonal,
            "aeso_forecast": test.forecast_pool_price.to_numpy(),
            "naive_yesterday": by_ds["y"].reindex(test.ds - pd.Timedelta(days=1)).to_numpy()})
        for name, c in cfgs.items():
            w = ensemble_weights(hmm["trans"], start, len(test), (c["weight_low"], c["weight_high"]))
            day[f"prophet_regime__{name}"] = regime[c["regime_cps"]]
            day[f"ensemble__{name}"] = w * regime[c["regime_cps"]] + (1 - w) * mc_seasonal
        days.append(day)
    return pd.concat(days, ignore_index=True)


# ---------- Decision value ----------
def shift_value(actual: np.ndarray, signal: np.ndarray, k: int = SHIFT_HOURS) -> float:
    """$ saved per MW in a day by moving k hours of load from the k highest-`signal` hours to the k lowest."""
    order = np.argsort(signal)
    return float(actual[order[-k:]].sum() - actual[order[:k]].sum())


def capture_rate(detail: pd.DataFrame, column: str, k: int = SHIFT_HOURS) -> float:
    """Share (%) of perfect-foresight shifting savings a forecast column captures, over all backtest days."""
    got, best = 0.0, 0.0
    for _, d in detail.dropna(subset=["actual", column]).groupby("cutoff_date"):
        if len(d) >= 2 * k:
            got += shift_value(d.actual.to_numpy(), d[column].to_numpy(), k)
            best += shift_value(d.actual.to_numpy(), d.actual.to_numpy(), k)
    return 100 * got / best if best else float("nan")


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


def leaderboard(detail: pd.DataFrame, series: dict[str, str]) -> pd.DataFrame:
    """MAE / RMSE / MAPE / capture rate per forecast column. `series` maps column -> 'model' or 'baseline'."""
    rows = []
    for column, kind in series.items():
        ok = detail[column].notna()
        rows.append({"model_name": column, "model_type": kind, "capture_rate_pct": capture_rate(detail, column),
                     **metrics(detail.actual[ok].to_numpy(), detail[column][ok].to_numpy())})
    return pd.DataFrame(rows).sort_values("mae_cad_mwh").reset_index(drop=True)
