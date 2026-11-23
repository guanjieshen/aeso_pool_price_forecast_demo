"""MLflow pyfunc wrapper for the converged ensemble (UC model `pool_price_ensemble`), plus registry and data helpers
shared by the forecast, weekly retrain and evaluation notebooks.

Input: rows of `ds` (naive MPT hour) and `wind_solar_mw`, in time order starting the hour after the last
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

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        future = model_input[["ds", "wind_solar_mw"]].copy()
        future["ds"] = pd.to_datetime(future["ds"])
        regime = fl.predict_prophet(self.regime_prophet, future)
        states, prices = fl.monte_carlo(self.hmm, self.start_state, len(future))
        mc = np.median(fl.apply_seasonality(states, prices, future["ds"].dt.hour.to_numpy(), self.factors), axis=0)
        weight = fl.ensemble_weights(self.hmm["trans"], self.start_state, len(future))
        return pd.DataFrame({"ensemble_forecast_price": weight * regime + (1 - weight) * mc})


def save_artifacts(fitted: dict, directory: str) -> dict:
    """Write the fitted parts the pyfunc needs; returns the MLflow artifacts mapping."""
    from prophet.serialize import model_to_json

    config_path, prophet_path = f"{directory}/config.json", f"{directory}/regime_prophet.json"
    with open(config_path, "w") as f:
        json.dump({"means": fitted["means"].tolist(), "stds": fitted["stds"].tolist(),
                   "trans": fitted["trans"].tolist(), "start_state": fitted["start_state"],
                   "factors": fitted["factors"].tolist()}, f)
    with open(prophet_path, "w") as f:
        f.write(model_to_json(fitted["regime_prophet"]))
    return {"config": config_path, "regime_prophet": prophet_path}


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
            pip_requirements=["prophet==1.5.0", "numpy", "pandas", "mlflow"])
    version = str(info.registered_model_version)
    client = MlflowClient(registry_uri="databricks-uc")
    for key, value in {"config": json.dumps(fitted["config"], sort_keys=True), **tags}.items():
        client.set_model_version_tag(model_name, version, key, value)
    return version


def load_features(spark, fq: str, horizon: int = fl.HORIZON) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(gold, history, future): all gold hours, settled history, and the next `horizon` unsettled hours."""
    gold = (spark.table(f"{fq}.gold_price_features_hourly")
            .select("ds", "y", "wind_solar_mw", "forecast_pool_price").orderBy("ds").toPandas())
    gold["ds"] = pd.to_datetime(gold["ds"])
    gold["wind_solar_mw"] = gold["wind_solar_mw"].ffill().bfill()
    history = gold[gold["y"].notna()].drop_duplicates("ds").reset_index(drop=True)
    future = gold[gold["ds"] > history["ds"].max()].head(horizon).reset_index(drop=True)
    return gold, history, future


def complete_days(history: pd.DataFrame, n: int, skip_last: int = 0) -> list:
    """The last `n` days with at least 23 settled hours, optionally ending `skip_last` days earlier."""
    counts = history.groupby(history.ds.dt.date).size()
    days = [pd.Timestamp(d) for d in counts[counts >= 23].index]
    return days[-(n + skip_last):len(days) - skip_last]
