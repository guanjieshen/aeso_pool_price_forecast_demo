# Databricks notebook source
# MAGIC %md
# MAGIC # What drives the Alberta pool price?
# MAGIC Alberta is an **energy-only market**: every hour AESO stacks generator offers from cheapest to dearest and
# MAGIC the pool price is set by the last offer needed to meet load. So the price depends less on load itself than
# MAGIC on **how much supply is left over** once load is served:
# MAGIC
# MAGIC `supply cushion = available dispatchable MW (gas, hydro, storage, other; net of outages) + wind and solar + intertie import capability - forecast load`
# MAGIC
# MAGIC A wide cushion means cheap units set the price; a thin one reaches the expensive end of the stack, where a
# MAGIC few offers can set prices near the $999.99 cap. This notebook measures, on settled 2026 hours, how much of
# MAGIC the price each fundamental explains, and writes the result to `aeso_price_drivers` (for Genie and the app).
# MAGIC
# MAGIC **Explained variance (eta squared)** = share of price variance explained by the driver's deciles. It
# MAGIC captures non-linear effects (the cushion acts like a hockey stick), unlike a straight-line correlation.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
spark.conf.set("spark.sql.session.timeZone", "UTC")

from datetime import datetime, timezone
import numpy as np
import pandas as pd

gold = spark.sql(f"""
SELECT ds, y AS price, supply_cushion_mw, net_load_mw, load_mw, wind_solar_mw, outage_mw, dispatchable_available_mw, import_atc_mw,
       hour_ending, day_of_week
FROM {FQ}.gold_price_features_hourly
WHERE y IS NOT NULL AND supply_cushion_mw IS NOT NULL AND NOT is_imputed""").toPandas()
print(f"Settled hours with fundamentals: {len(gold)} ({gold.ds.min()} .. {gold.ds.max()} MPT)")

# COMMAND ----------

# MAGIC %md ## 1. Which fundamental explains the most price?

# COMMAND ----------

def eta_squared(x: pd.Series, y: pd.Series, bins: int = 10) -> float:
    groups = pd.qcut(x.rank(method="first"), bins, labels=False) if x.nunique() > bins else x
    means = y.groupby(groups).transform("mean")
    return float(((means - y.mean()) ** 2).sum() / ((y - y.mean()) ** 2).sum())

DRIVERS = {
    "supply_cushion_mw": "Supply cushion (available dispatchable + wind/solar + import capability - forecast load)",
    "net_load_mw": "Net load (forecast load - wind/solar - import capability)",
    "import_atc_mw": "Intertie import capability (ATC)",
    "wind_solar_mw": "Wind + solar generation",
    "dispatchable_available_mw": "Available dispatchable capability (net of outages)",
    "outage_mw": "Dispatchable MW on outage",
    "load_mw": "Forecast Alberta internal load",
    "hour_ending": "Hour of day",
    "day_of_week": "Day of week",
}
spike = gold.price > 150
rows = []
for col, label in DRIVERS.items():
    rows.append({"view": "driver_strength", "segment": col, "description": label,
                 "explained_variance_pct": 100 * eta_squared(gold[col], gold.price),
                 "spearman_corr": float(gold[col].corr(gold.price, method="spearman")),
                 "spike_explained_variance_pct": 100 * eta_squared(gold[col], spike.astype(float))})
strength = pd.DataFrame(rows).sort_values("explained_variance_pct", ascending=False)
print(strength[["segment", "explained_variance_pct", "spike_explained_variance_pct", "spearman_corr"]].round(3).to_string(index=False))

# COMMAND ----------

# MAGIC %md ## 2. The hockey stick: price by supply cushion

# COMMAND ----------

edges = [-np.inf, 1000, 1500, 2000, 2500, 3000, 4000, 5000, np.inf]
labels = ["< 1,000", "1,000-1,500", "1,500-2,000", "2,000-2,500", "2,500-3,000", "3,000-4,000", "4,000-5,000", "> 5,000"]
gold["cushion_band"] = pd.cut(gold.supply_cushion_mw, edges, labels=labels)
bands = (gold.groupby("cushion_band", observed=True)
         .agg(hours=("price", "size"), avg_price=("price", "mean"), median_price=("price", "median"),
              p_above_150_pct=("price", lambda p: 100 * (p > 150).mean()), max_price=("price", "max"))
         .reset_index())
bands["share_of_hours_pct"] = 100 * bands.hours / bands.hours.sum()
print(bands.round(1).to_string(index=False))

# COMMAND ----------

# MAGIC %md ## 3. Where the spike hours sit

# COMMAND ----------

spikes = gold[spike]
print(f"Spike hours (> $150): {len(spikes)}. Median cushion in spike hours {spikes.supply_cushion_mw.median():,.0f} MW "
      f"vs {gold[~spike].supply_cushion_mw.median():,.0f} MW otherwise.")
thin = gold.supply_cushion_mw < 2000
print(f"Hours with cushion under 2,000 MW: {thin.mean():.1%} of hours, holding {(spike & thin).sum() / max(spike.sum(), 1):.0%} "
      f"of spike hours.")

# COMMAND ----------

now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
band_rows = bands.rename(columns={"cushion_band": "segment"}).assign(view="price_by_cushion_band", segment=lambda d: d.segment.astype(str))
out = pd.concat([strength, band_rows], ignore_index=True).assign(computed_at=now, n_hours=len(gold))
spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.aeso_price_drivers")
spark.sql(f"COMMENT ON TABLE {FQ}.aeso_price_drivers IS 'What drives the pool price: explained variance per fundamental "
          "(view=driver_strength) and price by supply cushion band (view=price_by_cushion_band), settled 2026 hours.'")
print(f"Wrote {len(out)} rows to {FQ}.aeso_price_drivers")
