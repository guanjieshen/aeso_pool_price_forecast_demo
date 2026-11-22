# Implementation plan

The build plan for the AESO pool price forecast, kept current as each phase lands. Why things are built this way is in [decisions.md](decisions.md); how to work on each part is in [../agents/](../agents/).

> **Status legend:** ✅ done and verified in the workspace · 🚧 in progress · ⬜ not started

## The customer problem

Power is the **largest operating cost** for Enbridge Liquids Pipelines. In Alberta, pump stations buy electricity at the hourly **AESO pool price**, which swings from near $0 to the $999.99/MWh cap. A handful of spike hours drives an outsized share of the bill. Pumping is partly flexible (line-pack and tankage), so a day-ahead, regime-aware price forecast gives the business two levers:

| Lever | Who | What changes |
| --- | --- | --- |
| **Operate** | Pipeline ops / control centre | Shift flexible pumping out of forecast spike hours |
| **Protect** | Energy desk / power procurement | See Spike-regime risk a day ahead and act on alerts |

All data is **public AESO data**. The flexible-load size is a labelled assumption, shown as a range.

## Phases

Each phase is one GitHub milestone, one tracking issue and one pull request into `main`.

| Phase | Scope | Done when | Status |
| --- | --- | --- | --- |
| **1. Data engineering** | Ingest (pool price, wind/solar forecast, wind/solar metered history), Lakeflow declarative pipeline (silver/gold, expectations), UC governance, hourly Lakeflow job | Hourly job green end to end; row counts and expectations in `evidence/` | ✅ |
| **2. ML** | HMM + Prophet + Monte Carlo, converged models, ensemble, 5-day walk-forward backtest with AESO and naive baselines, MLflow + UC model registry, business value | Backtest metrics written, model `@champion` registered | ✅ |
| **3. App + Lakebase** | Lakebase project, synced tables, `ops_actions` write-back, AESO Market Pulse app (9 cards + ops action form) | App deployed, reads Lakebase, write-back round trip verified | 🚧 |
| **4. AI + story** | Genie space (instructions, benchmark), screen-aware "Analyze with Genie" links to Genie One, evidence export, deck | Benchmark scored, evidence and deck committed | ⬜ |

## Architecture

```
AESO API (pool price)  ─┐
AESO API (metered MWh) ─┼─► Lakeflow Job (hourly, serverless)
AESO CSV (wind/solar)  ─┘     1. ingest notebooks ─► bronze Delta (MERGE)
                              2. declarative pipeline ─► silver / gold (expectations)
                              3. forecast notebook ─► forecast + backtest tables, MLflow, UC model
                              4. Lakebase sync ─► synced tables (+ ops_actions copied back to Delta)
                                      │
             Unity Catalog: comments, tags, grants, lineage, UC secret for the AESO key
                                      │
          ┌───────────────────────────┼──────────────────────────┐
   AESO Market Pulse app        Genie space               Genie One deep links
   (Lakebase hot reads,         (governed tables,         (screen-aware prompts
    warehouse history,           benchmark N/8)            from each app card)
    ops action write-back)
```

## Tables (`energy_canada_demos_catalog.aeso_price_forecast`)

| Table | Layer | Written by | Key |
| --- | --- | --- | --- |
| `aeso_pool_price` | bronze | `src/ingest/pool_price_incremental.py` | `begin_datetime_utc` |
| `aeso_wind_solar_forecast` | bronze | `src/ingest/wind_solar_forecast.py` | `forecast_transaction_date` |
| `aeso_wind_solar_metered` | bronze | `src/ingest/wind_solar_metered.py` | `begin_datetime_utc` |
| `silver_pool_price_hourly` | silver | pipeline | `begin_datetime_utc` |
| `silver_wind_solar_hourly` | silver | pipeline | `forecast_transaction_date` |
| `gold_price_features_hourly` | gold | pipeline | `ds` (MPT hour) |
| `aeso_price_forecast_output` | gold | `src/ml/pool_price_forecast.py` (overwrite) | `forecast_datetime_mpt` |
| `aeso_backtest_metrics` | gold | forecast notebook (append) | `run_timestamp, model_name` |
| `aeso_backtest_detail` | gold | forecast notebook (append) | `run_timestamp, cutoff_date, forecast_hour` |
| `aeso_business_value` | gold | `src/ml/business_value.py` | `run_timestamp, scenario` |
| `ops_actions_history` | gold | Lakebase copy-back task | `action_id` |

## Conventions

- **Prices** in CAD/MWh. **Times** in Mountain Time (`America/Edmonton`), stored as naive `*_mpt` timestamps with the session time zone pinned to UTC so wall-clock values are kept. Keys use UTC, because MPT repeats an hour when daylight saving time ends.
- **AESO hour-ending:** `hour_ending = HOUR(begin_datetime_mpt) + 1` (HE01 to HE24).
- **Secrets:** the AESO key is the UC secret `aeso_price_forecast.aeso_api_key`, read with `dbutils.secrets.get(catalog=..., schema=..., key=...)` on serverless environment 4+. It is never printed.
- **Deploy:** one Databricks Asset Bundle (`databricks.yml`), target `dev`.

## Verification per phase

| Phase | Check |
| --- | --- |
| 1 | `aeso_pool_price` hours ≈ hours since 2026-01-01; metered history covers 2026-01-01 to about T-3 days; pipeline expectations pass; hourly job run green |
| 2 | Latest forecast has 24 rows; backtest metrics cover 5 models + 2 baselines; UC model alias `champion` exists |
| 3 | Synced table row counts equal Delta; an app-written `ops_actions` row is read back and appears in `ops_actions_history` |
| 4 | Genie benchmark N/8 committed; every app card's "Analyze with Genie" link opens Genie One with the prompt filled in |
