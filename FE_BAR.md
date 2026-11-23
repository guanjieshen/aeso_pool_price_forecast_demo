# FE Bar: AESO pool price forecast for Enbridge Liquids Pipelines

**Industry:** midstream oil and gas pipelines. **Customer:** Enbridge Liquids Pipelines. **Data:** public AESO market data only.

## The business problem, and whose scorecard it moves

Power is the **largest operating cost** of a liquids pipeline. Its Alberta pump stations pay the hourly **AESO pool price** ($0 to the $999.99/MWh cap). In 2026 so far, the 200 hours above $150/MWh were **2.6% of hours but 35.8% of a flat load's power cost**; the top 5% of hours carried **43.5%** ([03](evidence/03_ml_backtest.md)). Pumping is partly flexible (line-pack, tankage), but nobody gives operations a day-ahead view of when spikes will land.

| Who | Scorecard metric | What the build moves |
| --- | --- | --- |
| **VP Operations, Liquids Pipelines** (executive sponsor) | **Power cost per barrel delivered**, operating cost vs budget | Indicative **$0.93M a year to date per 10 MW** of flexible pumping moved out of spike hours, straight off the largest opex line |
| Control centre (Operate) | Flexible MWh run in spike hours | 24h forecast and hour ranking: which hours to avoid |
| Energy desk (Protect) | Spike exposure (MWh bought above $150) | Day-ahead spike probability, alerts, outage outlook |

## Lakeflow build (code in this repo)

**Lakeflow Jobs** (`resources/data_and_ml.yml`, deployed by the bundle): job `aeso-hourly`, cron `0 20 * * * ?` America/Edmonton, serverless. Task graph:

```yaml
tasks:
  - task_key: ingest_pool_price        # notebook ../src/ingest/pool_price_incremental.py (MERGE)
  - task_key: ingest_wind_solar_forecast
  - task_key: ingest_wind_solar_metered
  - task_key: ingest_outage_outlook
  - task_key: ingest_supply_demand     # depends_on ingest_wind_solar_forecast; archives as published
  - task_key: transform                # depends_on all ingests
    pipeline_task: { pipeline_id: ${resources.pipelines.aeso_transform.id} }
  - task_key: forecast                 # then lakebase_sync, then governance
```

Plus `aeso-weekly-retrain`, `aeso-evaluate-challenger` (**model update trigger** on `@challenger`), `aeso-daily-monitor` and `aeso-rebaseline`.

**Lakeflow Spark Declarative Pipeline** `aeso-transform` (`src/pipeline/transformations.py`): four materialized views from bronze to gold, with expectations:

```python
from pyspark import pipelines as dp
@dp.materialized_view(comment="Silver: hourly AESO pool price, deduplicated and range-checked ...")
@dp.expect_or_drop("price_in_market_range", "pool_price IS NULL OR pool_price BETWEEN 0 AND 999.99")
def silver_pool_price_hourly(): ...
# also silver_wind_solar_hourly, silver_supply_demand_hourly (day-ahead as-known columns), gold_price_features_hourly
```

Run evidence: the job's task graph as deployed, each task's state, and the pipeline update with its expectation results ([01](evidence/01_ingest.md), [02](evidence/02_pipeline_governance.md)).

## The data journey

| Stage | What runs | Where |
| --- | --- | --- |
| **Lakeflow** | Jobs above: AESO API + CSV ingest (incremental MERGE from 2026-01-01; wind/solar history **rebuilt from 99 metered assets**; load, capability net of outages, interties, outage outlook; **as-published snapshot archive**) then the declarative pipeline | `resources/data_and_ml.yml`, `src/ingest/`, `src/pipeline/` |
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
