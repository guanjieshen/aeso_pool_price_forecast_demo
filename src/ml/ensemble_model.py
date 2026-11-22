"""MLflow pyfunc wrapper for the converged ensemble, registered in Unity Catalog as `pool_price_ensemble`.

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
