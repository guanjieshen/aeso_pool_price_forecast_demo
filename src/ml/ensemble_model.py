"""MLflow pyfunc wrapper for the converged ensemble (UC model `pool_price_ensemble`), plus registry and data helpers
shared by the forecast, weekly retrain and evaluation notebooks.

Input: rows of `ds` (naive MPT hour) and the gold fundamentals (`wind_solar_mw`, and when the version's recipe has a
`fundamentals_gate`: `supply_cushion_mw`, `net_load_mw`, `load_mw`), in time order starting the hour after the last
settled price. Output: `ensemble_forecast_price` (CAD/MWh) per row.
"""
import json

import mlflow
import numpy as np
import pandas as pd

import forecast_lib as fl


class PoolPriceEnsemble(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        from prophet.serialize import model_from_json

        with open(context.artifacts["config"]) as f:
            cfg = json.load(f)
        with open(context.artifacts["regime_prophet"]) as f:
            self.regime_prophet = model_from_json(f.read())
        self.hmm = {k: np.array(cfg[k]) for k in ("means", "stds", "trans")}
        self.start_state = int(cfg["start_state"])
        self.factors = np.array(cfg["factors"])
        self.bounds = (cfg.get("weight_low", fl.WEIGHT_BOUNDS[0]), cfg.get("weight_high", fl.WEIGHT_BOUNDS[1]))
        self.gate = cfg.get("fundamentals_gate")
        self.fundamentals = None
        if self.gate:
            import pickle
            with open(context.artifacts["fundamentals"], "rb") as f:
                self.fundamentals = pickle.load(f)

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        future = model_input.copy()
        future["ds"] = pd.to_datetime(future["ds"])
        regime = fl.predict_prophet(self.regime_prophet, future)
        states, prices = fl.monte_carlo(self.hmm, self.start_state, len(future))
        mc = np.median(fl.apply_seasonality(states, prices, future["ds"].dt.hour.to_numpy(), self.factors), axis=0)
        weight = fl.ensemble_weights(self.hmm["trans"], self.start_state, len(future), self.bounds)
        price = weight * regime + (1 - weight) * mc
        if self.fundamentals is not None:
            g = fl.gate_weight(future["supply_cushion_mw"].to_numpy(), self.gate)
            price = (1 - g) * price + g * fl.predict_fundamentals(self.fundamentals, future)
        return pd.DataFrame({"ensemble_forecast_price": price})


def save_artifacts(fitted: dict, directory: str) -> dict:
    """Write the fitted parts the pyfunc needs; returns the MLflow artifacts mapping."""
    from prophet.serialize import model_to_json

    config_path, prophet_path = f"{directory}/config.json", f"{directory}/regime_prophet.json"
    with open(config_path, "w") as f:
        json.dump({"means": fitted["means"].tolist(), "stds": fitted["stds"].tolist(),
                   "trans": fitted["trans"].tolist(), "start_state": fitted["start_state"],
                   "factors": fitted["factors"].tolist(), "weight_low": fitted["config"]["weight_low"],
                   "weight_high": fitted["config"]["weight_high"],
                   "fundamentals_gate": fitted["config"].get("fundamentals_gate")}, f)
    with open(prophet_path, "w") as f:
        f.write(model_to_json(fitted["regime_prophet"]))
    artifacts = {"config": config_path, "regime_prophet": prophet_path}
    if fitted.get("fundamentals") is not None:
        import pickle
        artifacts["fundamentals"] = f"{directory}/fundamentals.pkl"
        with open(artifacts["fundamentals"], "wb") as f:
            pickle.dump(fitted["fundamentals"], f)
    return artifacts


# ---------- Registry helpers (Unity Catalog) ----------
def config_for(model_name: str, alias: str) -> tuple[str | None, dict]:
    """(version, training config) of the version holding `alias`. Versions registered before configs were
    tagged, or a missing alias, fall back to the default recipe."""
    from mlflow import MlflowClient

    client = MlflowClient(registry_uri="databricks-uc")
    try:
        mv = client.get_model_version_by_alias(model_name, alias)
    except Exception:
        return None, fl.resolve(None)
    return mv.version, fl.resolve(json.loads(mv.tags["config"]) if "config" in mv.tags else None)


def config_of_version(model_name: str, version: str) -> dict:
    from mlflow import MlflowClient

    mv = MlflowClient(registry_uri="databricks-uc").get_model_version(model_name, str(version))
    return fl.resolve(json.loads(mv.tags["config"]) if "config" in mv.tags else None)


def register(fitted: dict, example: pd.DataFrame, output: pd.DataFrame, model_name: str, run_id: str,
             tags: dict[str, str]) -> str:
    """Log the fitted ensemble as a pyfunc in `run_id`, register it, tag it with its config. Returns the version."""
    import tempfile
    from mlflow import MlflowClient
    from mlflow.models import infer_signature

    mlflow.set_registry_uri("databricks-uc")
    with tempfile.TemporaryDirectory() as tmp, mlflow.start_run(run_id=run_id):
        info = mlflow.pyfunc.log_model(
            name="pool_price_ensemble", python_model=PoolPriceEnsemble(), artifacts=save_artifacts(fitted, tmp),
            code_paths=["forecast_lib.py", "ensemble_model.py"], input_example=example.head(3),
            signature=infer_signature(example, output), registered_model_name=model_name,
            pip_requirements=["prophet==1.5.0", "scikit-learn", "numpy", "pandas", "mlflow"])
    version = str(info.registered_model_version)
    client = MlflowClient(registry_uri="databricks-uc")
    for key, value in {"config": json.dumps(fitted["config"], sort_keys=True), **tags}.items():
        client.set_model_version_tag(model_name, version, key, value)
    return version


def load_features(spark, fq: str, horizon: int = fl.HORIZON) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(gold, history, future): all gold hours, settled history, and the next `horizon` unsettled hours."""
    gold = (spark.table(f"{fq}.gold_price_features_hourly")
            .select("ds", "y", "forecast_pool_price", *fl.FEATURES, *fl.DAYAHEAD.values()).orderBy("ds").toPandas())
    gold["ds"] = pd.to_datetime(gold["ds"])
    # As-recorded features are filled across small gaps; day-ahead ones are not (a gap means "not known then").
    gold[fl.FEATURES] = gold[fl.FEATURES].ffill().bfill()
    history = gold[gold["y"].notna()].drop_duplicates("ds").reset_index(drop=True)
    future = gold[gold["ds"] > history["ds"].max()].head(horizon).reset_index(drop=True)
    return gold, history, future


def complete_days(history: pd.DataFrame, n: int, skip_last: int = 0, dayahead: bool = True) -> list:
    """The last `n` days with at least 23 settled hours (and, by default, a day-ahead cushion for at least 23 of
    them, so the backtest never falls back to realised wind), optionally ending `skip_last` days earlier."""
    ok = history["supply_cushion_dayahead_mw"].notna() if dayahead else pd.Series(True, index=history.index)
    counts = history[ok].groupby(history.ds.dt.date).size()
    days = [pd.Timestamp(d) for d in counts[counts >= 23].index]
    return days[-(n + skip_last):len(days) - skip_last]
