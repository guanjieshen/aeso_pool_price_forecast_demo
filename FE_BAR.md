# FE Bar: AESO pool price forecast for Enbridge Liquids Pipelines

**Industry:** midstream oil and gas pipelines. **Customer:** Enbridge Liquids Pipelines. **Data:** public AESO market data only.

## The business problem, and whose scorecard it moves

Power is the **largest operating cost** of a liquids pipeline. Its Alberta pump stations pay the hourly **AESO pool price** ($0 to the $999.99/MWh cap). In 2026 so far, the 200 hours above $150/MWh were **2.6% of hours but 35.8% of a flat load's power cost**; the top 5% of hours carried **43.5%** ([03](evidence/03_ml_backtest.md)). Pumping is partly flexible (line-pack, tankage), but nobody gives operations a day-ahead view of when spikes will land.

| Who | Scorecard metric | What the build moves |
| --- | --- | --- |
| **VP Operations, Liquids Pipelines** (executive sponsor) | **Power cost per barrel delivered**, operating cost vs budget | Indicative **$0.93M a year to date per 10 MW** of flexible pumping moved out of spike hours, straight off the largest opex line |
| Control centre (Operate) | Flexible MWh run in spike hours | 24h forecast and hour ranking: which hours to avoid |
| Energy desk (Protect) | Spike exposure (MWh bought above $150) | Day-ahead spike probability, alerts, outage outlook |

**Why it matters beyond the opex line (to validate with Enbridge):** how much of Alberta power cost flows through to shippers in tolls versus sitting in Enbridge's margin, and how a lower, more predictable power cost per barrel strengthens toll competitiveness against rival pipes and rail and frees cash for capital allocation. These are discovery questions for the VP, not claims we make for them.

## Lakeflow build (code in this repo)

**Raw landing, then the pipeline owns ingestion.** The hourly **Lakeflow Job** (`resources/data_and_ml.yml`, cron `0 20 * * * ?` America/Edmonton, serverless) only fetches from AESO and lands raw files in the Unity Catalog volume `raw/<feed>/`: pool price, wind/solar CSV, metered assets, load, capability, interties, published forecasts, outage reports. The **Lakeflow Spark Declarative Pipeline** `aeso-transform` does the rest, raw to bronze to silver to gold:

```python
# src/pipeline/ingest.py: bronze streaming tables read the raw files incrementally with Auto Loader
@dp.table(comment="Bronze: AESO pool price report records exactly as returned by the API ...")
@dp.expect("has_hour", "begin_datetime_utc IS NOT NULL")
def bronze_pool_price():
    return autoload("pool_price", "json", "begin_datetime_utc STRING, ... fetched_at STRING")  # cloudFiles

@dp.materialized_view(comment="Silver: AESO hourly pool price, typed, latest landed record per hour ...")
@dp.expect_or_drop("valid_hour", "begin_datetime_utc IS NOT NULL AND begin_datetime_mpt IS NOT NULL")
def aeso_pool_price(): ...
```

| Layer | Datasets |
| --- | --- |
| Bronze (streaming tables, Auto Loader) | `bronze_pool_price`, `bronze_wind_solar_forecast`, `bronze_wind_solar_metered`, `bronze_load`, `bronze_gen_capacity`, `bronze_intertie`, `bronze_wind_solar_published`, `bronze_outage_outlook` |
| Silver (materialized views) | Conformed `aeso_*` (typed, latest per key), the as-known `aeso_fundamentals_snapshots`, and `silver_*` modelling views (`src/pipeline/transformations.py`) |
| Gold | `gold_price_features_hourly`, read by the model, the app and Genie |

Job tasks: five land tasks, then `transform` (pipeline_task), `forecast`, `lakebase_sync`, `governance`. Other jobs: `aeso-weekly-retrain`, `aeso-evaluate-challenger` (**model update trigger** on `@challenger`), `aeso-daily-monitor`, `aeso-rebaseline`.

## The data journey

| Stage | What runs | Where |
| --- | --- | --- |
| **Lakeflow** | Job lands raw AESO files (from 2026-01-01; wind/solar history **rebuilt from 99 metered assets**; load, capability, interties, outage outlook); the declarative pipeline ingests them raw to bronze to silver to gold, including the **as-known snapshot archive** | `resources/data_and_ml.yml`, `src/ingest/`, `src/pipeline/` |
| **Unity Catalog** | Governed tags from the metastore's tag policies, comments, lineage, AESO key as a **UC secret**, least-privilege grants | `src/governance/setup_uc.py` |
| **ML** | 3-state HMM + Prophet + Monte Carlo ensemble plus a **supply-cushion model** for tight hours; walk-forward backtests on **day-ahead features**; MLflow; UC model `pool_price_ensemble@champion`; weekly challenger, gated promotion, drift monitor | `src/ml/` |
| **Lakebase** | Synced tables for the live cards + `ops_actions` write-back | `resources/serving.yml`, `src/lakebase/` |
| **App** | AESO Market Pulse: cards ordered Now, Plan, Act, Why, Check; forecast score badge; outage outlook | `app/` |
| **Genie** | Genie space, scored benchmark, screen-aware links into Genie One | `src/genie/`, `scripts/genie_benchmark.py` |

## Results (real runs, see `evidence/`)

> **Re-baselined accuracy: about 77%.** Our published 90.2% capture was scored with realised wind on a quiet fortnight. On day-ahead information over three 14-day windows that model captures **76.7%** of perfect-foresight savings; the supply-cushion model since promoted lifts it to **87.3%**, against 91.7% for AESO's 2-hours-ahead forecast ([06](evidence/06_model_lifecycle.md)).

- **Data:** 7,839 hourly prices from 2026-01-01; only **1 of 8,004** regressor hours imputed ([01](evidence/01_ingest.md), [02](evidence/02_pipeline_governance.md)).
- **What drives the price:** the **supply cushion** (available gas, hydro, storage + wind/solar + imports - forecast load) explains **24.0% of price variance and 17.9% of spike variance** (wind alone: 12.2%, 5.7%). Hours under 2,000 MW of cushion are **6.1% of hours but 78% of spike hours** ([07](evidence/07_fundamentals.md)).
- **Self-improving:** the gate promoted the cushion model (v7) over v5 on Oct 18 to 31, capture **73.1% to 80.3%**, MAE **31.79 to 27.37**, and rejected a Prophet-only v6 the same day ([06](evidence/06_model_lifecycle.md)).
- **Champion v7 on Oct 18 to 31 (336 h):** MAE 27.37 (AESO 16.24, same hour yesterday 59.85: **54% better**); regime-aware Prophet 30.36 vs plain Prophet 44.53 ([03](evidence/03_ml_backtest.md)).
- **Decision value:** perfect foresight is worth **$115,776 per flexible MW** in 2026 so far (4 shifted hours a day); at 80.3% capture, **$0.93M per 10 MW** ([03](evidence/03_ml_backtest.md)).
- **Serving and AI:** Lakebase synced rows match Delta; an app-written ops action round-tripped to Delta; the deployed app's API returns every feed ([04](evidence/04_lakebase_app.md)). Genie scored **8/8** against ground-truth SQL ([05](evidence/05_genie_benchmark.md)).

## Decisions and trade-offs

Full log with alternatives: [docs/decisions.md](docs/decisions.md). The ones that mattered most:

1. **Metered backfill over imputation:** the public wind CSV holds about 2 days of actuals; 99 metered assets made the regressor real.
2. **Converge before blending:** Prophet chased spikes; dropping Spike hours and a 50x tighter changepoint prior fixed it.
3. **Promote on decision value, guard on accuracy:** the best-MAE model was not the best at ranking expensive hours, so promotion uses capture rate with an MAE guard.
4. **Fundamentals over curve-fitting:** five research rounds found the cushion is the driver; a linear regressor cannot use its hockey-stick shape, a gated gradient-boosted model can; 60-day-late merit-order data failed.
5. **No look-ahead, honest baselines:** we re-scored our own champion when we found the backtest saw realised wind, and we show AESO's forecast beating us on MAE.
6. **Governance fits the customer:** the first run failed on a governed tag, so the build uses the metastore's tag policies.

## AI workflow

Claude Code: plan mode first (gap analysis against the FE Bar, my answers), then phased builds (data engineering, ML, app, AI, self-improving models, fundamentals) with a `/goal` and per-phase PRs. AI-written code was run and fixed against the live workspace (for example the metered API's exclusive `endDate`, found from a 250-hour imputation gap); every number is read from committed run output.

## How to run it

`databricks bundle deploy && databricks bundle run aeso_hourly` ([README](README.md)). The upload holds the 30 files that carry the build (scorer limit); the full repo with agent guides, scripts and every notebook is on GitHub `main`: github.com/guanjieshen/aeso_pool_price_forecast_demo. Evidence: `uv run --with databricks-sdk python scripts/export_evidence.py`.
