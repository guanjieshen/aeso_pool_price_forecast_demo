# Databricks notebook source
# MAGIC %md
# MAGIC # Business value: what the forecast is worth to a pump station
# MAGIC Two numbers, both from real AESO prices:
# MAGIC
# MAGIC 1. **Spike concentration (fact, no model):** what share of a flat load's 2026 pool-price cost falls in the
# MAGIC    most expensive 5% of hours.
# MAGIC 2. **Load-shift value (backtest):** each day, move `SHIFT_HOURS` hours of flexible pumping (1 MW) from the
# MAGIC    hours a strategy *expects* to be most expensive into the hours it expects to be cheapest, then settle at
# MAGIC    actual prices. Strategies: perfect foresight (the ceiling), the ensemble, AESO's forecast and
# MAGIC    same-hour-yesterday. The capture rate is a strategy's savings as a share of perfect foresight.
# MAGIC
# MAGIC **Assumptions (labelled, not measured):** the flexible MW and `SHIFT_HOURS` are inputs to confirm with
# MAGIC pipeline operations; results are reported per MW and for 5 / 10 / 20 MW of flexible load.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("shift_hours", "4")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
SHIFT_HOURS = int(dbutils.widgets.get("shift_hours"))
FQ = f"{CATALOG}.{SCHEMA}"
SCENARIOS_MW = [5, 10, 20]
spark.conf.set("spark.sql.session.timeZone", "UTC")

import numpy as np
import pandas as pd
from datetime import datetime, timezone

# COMMAND ----------

# MAGIC %md ## 1. Spike concentration in 2026 settled prices

# COMMAND ----------

prices = spark.sql(f"SELECT ds, y FROM {FQ}.gold_price_features_hourly WHERE is_settled AND YEAR(ds) = 2026").toPandas()
y = prices["y"].sort_values(ascending=False).to_numpy()
top = int(np.ceil(0.05 * len(y)))
facts = {
    "settled_hours_2026": len(y),
    "avg_price_cad_mwh": y.mean(),
    "top5pct_hours": top,
    "top5pct_cost_share_pct": 100 * y[:top].sum() / y.sum(),
    "hours_above_150_pct": 100 * np.mean(y > 150),
    "cost_share_above_150_pct": 100 * y[y > 150].sum() / y.sum(),
    "max_price_cad_mwh": y.max(),
}
print("\n".join(f"{k}: {v:,.2f}" for k, v in facts.items()))

# Perfect-foresight value of shifting SHIFT_HOURS hours a day, 1 MW, every 2026 day with 24 settled hours
prices["day"] = pd.to_datetime(prices["ds"]).dt.date
full_days = prices.groupby("day").filter(lambda d: len(d) >= 24)
def shift_value(actual, signal, k=SHIFT_HOURS):
    order = np.argsort(signal)
    return actual[order[-k:]].sum() - actual[order[:k]].sum()   # $ saved per MW for that day
pf_daily = full_days.groupby("day")["y"].apply(lambda d: shift_value(d.to_numpy(), d.to_numpy()))
facts["perfect_foresight_shift_cad_per_mw_ytd"] = float(pf_daily.sum())
facts["perfect_foresight_days"] = len(pf_daily)
print(f"Perfect foresight, {SHIFT_HOURS}h/day, 1 MW: ${pf_daily.sum():,.0f} over {len(pf_daily)} days "
      f"(${pf_daily.mean():,.2f}/MW/day)")

# COMMAND ----------

# MAGIC %md ## 2. What each strategy captures in the latest backtest

# COMMAND ----------

detail = spark.sql(f"""
SELECT * FROM {FQ}.aeso_backtest_detail
WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_detail)""").toPandas()
STRATEGIES = {"perfect_foresight": "actual", "ensemble": "ensemble", "aeso_forecast": "aeso_forecast",
              "naive_yesterday": "naive_yesterday", "prophet_regime": "prophet_regime", "mc_seasonal": "mc_seasonal"}
rows = []
for name, col in STRATEGIES.items():
    per_day = []
    for _, d in detail.groupby("cutoff_date"):
        d = d.dropna(subset=["actual", col])
        if len(d) >= 2 * SHIFT_HOURS:
            per_day.append(shift_value(d.actual.to_numpy(), d[col].to_numpy()))
    rows.append({"strategy": name, "days": len(per_day), "savings_cad_per_mw_day": float(np.mean(per_day))})
value = pd.DataFrame(rows)
ceiling = value.set_index("strategy").loc["perfect_foresight", "savings_cad_per_mw_day"]
value["capture_rate_pct"] = 100 * value.savings_cad_per_mw_day / ceiling
for mw in SCENARIOS_MW:
    value[f"annualized_cad_at_{mw}mw"] = value.savings_cad_per_mw_day * mw * 365
print(f"Backtest days: {', '.join(str(d) for d in sorted(detail.cutoff_date.unique()))}\n" + value.round(1).to_string(index=False))

# Indicative 2026-to-date value = perfect-foresight ceiling (all 2026 days) x the backtest capture rate.
ceiling_ytd = facts["perfect_foresight_shift_cad_per_mw_ytd"]
indicative = pd.DataFrame([{"strategy": r.strategy, "scenario_mw": mw, "capture_rate_pct": r.capture_rate_pct,
                            "indicative_ytd_value_cad": ceiling_ytd * mw * r.capture_rate_pct / 100}
                           for r in value.itertuples() if r.strategy in ("perfect_foresight", "ensemble", "prophet_regime")
                           for mw in SCENARIOS_MW])
print(f"\nIndicative 2026-to-date value (ceiling ${ceiling_ytd:,.0f}/MW x capture rate):\n"
      + indicative.round(1).to_string(index=False))

# COMMAND ----------

run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
fact_rows = pd.DataFrame([{"metric": k, "value": float(v), "basis": "2026 settled AESO pool prices"} for k, v in facts.items()])
out = pd.concat([
    fact_rows.assign(strategy=None, scenario_mw=None),
    value.melt(id_vars=["strategy"], value_vars=["savings_cad_per_mw_day", "capture_rate_pct", "days"],
               var_name="metric").assign(basis="latest 5-day walk-forward backtest", scenario_mw=1),
    indicative.rename(columns={"indicative_ytd_value_cad": "value"}).drop(columns="capture_rate_pct")
              .assign(metric="indicative_ytd_value_cad", basis="2026 ceiling x backtest capture rate"),
], ignore_index=True).assign(run_timestamp=run_ts, shift_hours=SHIFT_HOURS)
out = out.astype({"value": "float64", "scenario_mw": "float64"})
(spark.createDataFrame(out[["run_timestamp", "metric", "strategy", "scenario_mw", "value", "basis", "shift_hours"]])
 .write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.aeso_business_value"))
print(f"Wrote {len(out)} rows to {FQ}.aeso_business_value")
