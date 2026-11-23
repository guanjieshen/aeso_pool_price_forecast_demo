# AESO pool price forecast for pipeline power cost

A day-ahead, regime-aware Alberta pool price forecast that helps **Enbridge Liquids Pipelines** protect its largest operating cost: electricity for pump stations. Built end to end on Databricks from public AESO data.

> **Start here.** [FE_BAR.md](FE_BAR.md) is the one-page tour with results. [AGENTS.md](AGENTS.md) explains how to work on the repo. The build plan and status are in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Overview

| Stage | Databricks feature | What it does |
| --- | --- | --- |
| Ingest | **Lakeflow Jobs** | Hourly: AESO pool price API, wind/solar CSV and metered history into bronze Delta (MERGE) |
| Transform | **Lakeflow declarative pipeline** | Silver/gold materialized views with data-quality expectations |
| Govern | **Unity Catalog** | Governed tags, comments, lineage, the AESO key as a UC secret, least-privilege grants |
| Predict | **MLflow + UC model registry** | HMM + Prophet + Monte Carlo ensemble plus a supply-cushion fundamentals model, 14-day walk-forward backtest on day-ahead features, self-improving `@champion` model |
| Serve | **Lakebase** | Synced tables for the app's live cards, `ops_actions` write-back |
| Surface | **Databricks Apps** | AESO Market Pulse, a terminal-style dashboard for ops and the energy desk |
| Ask | **Genie** | A governed Genie space, plus "Analyze with Genie" links into Genie One from each card |

## Workspace and data

| Item | Value |
| --- | --- |
| Workspace | `https://fevm-energy-canada-demos.cloud.databricks.com` (CLI profile `fevm-energy-canada`) |
| Schema | `energy_canada_demos_catalog.aeso_price_forecast` |
| AESO API key | UC secret `energy_canada_demos_catalog.aeso_price_forecast.aeso_api_key` (create it before the first run) |
| SQL warehouse | `fd18e0ef46eba09f` (variable `warehouse_id`) |
| External data | [AESO API](https://api.aeso.ca) (pool price, metered volumes, supply/demand) and the public [wind/solar forecast CSV](http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv) |

## Deploy

```bash
databricks bundle validate
databricks bundle deploy
```

## Run

| Step | Command | Takes |
| --- | --- | --- |
| 1. Ingest, transform, forecast, govern | `databricks bundle run aeso_hourly` | about 4 min (first run bootstraps from 2026-01-01) |
| 2. Propose a challenger model (it is evaluated and promoted automatically by the model update trigger) | `databricks bundle run aeso_weekly_retrain` | about 2 min, then about 3 min for `aeso-evaluate-challenger` |
| 3. Refresh the text evidence | `uv run --with databricks-sdk python scripts/export_evidence.py` | 1 min |

Once deployed: `aeso-hourly` runs at :20 every hour, `aeso-weekly-retrain` on Mondays at 05:30 MPT, `aeso-daily-monitor` daily at 06:45 MPT, and `aeso-evaluate-challenger` whenever `@challenger` is set on the model.

## Teardown

`databricks bundle destroy` removes the jobs, pipeline, experiment, app and Lakebase project. Tables written by notebooks stay in the schema; drop them by hand if needed.

## Status

**Active.** All four phases (data engineering, ML, app + Lakebase, Genie + story) verified in the workspace on 2026-11-22. See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
