# AESO pool price forecast for pipeline power cost

A day-ahead Alberta pool price forecast that helps **Enbridge Liquids Pipelines** protect its largest operating cost, power for pump stations. Built end to end on Databricks from public AESO data, deployed by one Databricks Asset Bundle.

> **For the reviewer.** [FE_BAR.md](FE_BAR.md) is the one-page tour with results. The map below points each required layer to its code and its run evidence.

## Layer, code and evidence

| Layer | Code | Evidence |
| --- | --- | --- |
| **Lakeflow** (ingest the raw data) | Jobs `resources/data_and_ml.yml`: hourly job lands raw AESO files in the UC volume `raw/` (`src/ingest/`). **Spark Declarative Pipeline** `src/pipeline/ingest.py`: Auto Loader (`cloudFiles`) **bronze streaming tables** from the raw files, then conformed silver; `src/pipeline/transformations.py`: silver to gold with expectations | `evidence/01_ingest.md` |
| **Unity Catalog** | `src/governance/setup_uc.py`: governed tags, comments, UC secret, grants | `evidence/02_pipeline_governance.md` |
| **Lakebase** | `resources/serving.yml` (project, synced tables), `src/lakebase/sync_and_copy_back.py` | `evidence/04_lakebase_app.md` |
| **ML** | `src/ml/`: HMM + Prophet + Monte Carlo + supply-cushion model, UC model `@champion`, challenger promotion (`evaluate_challenger.py`) | `evidence/03_ml_backtest.md`, `evidence/06_model_lifecycle.md` |
| **Genie** | `src/genie/`, Genie space in `resources/serving.yml` | `evidence/05_genie_benchmark.md` |
| **App** | `app/`, app resource in `resources/serving.yml` | `evidence/04_lakebase_app.md` |

## Data flow

```
AESO API + CSV --(job: fetch, land raw)--> UC volume raw/<feed>/
  --(pipeline: Auto Loader)--> bronze_* streaming tables --> conformed silver (aeso_*) --> silver_* --> gold
  --> forecast + model lifecycle (MLflow, UC) --> Lakebase synced tables --> AESO Market Pulse app, Genie
```

## Deploy and run

`databricks bundle deploy`, then `databricks bundle run aeso_hourly` (first run lands from 2026-01-01). Weekly challenger: `databricks bundle run aeso_weekly_retrain`. Evidence: `uv run --with databricks-sdk python scripts/export_evidence.py`. Workspace `fevm-energy-canada-demos`, schema `energy_canada_demos_catalog.aeso_price_forecast`, AESO key in the UC secret `aeso_price_forecast.aeso_api_key`.
