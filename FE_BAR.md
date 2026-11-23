# FE Bar: AESO pool price forecast for Enbridge Liquids Pipelines

**Industry:** energy, midstream oil and gas pipelines. **Customer:** Enbridge Liquids Pipelines. **Data:** public AESO market data only (no customer data).

## The business problem

Power is the **largest operating cost** for a liquids pipeline. Its Alberta pump stations buy electricity at the hourly **AESO pool price**, which runs from near $0 to the $999.99/MWh cap. In 2026 so far, hours priced above $150/MWh were **2.6% of hours but 35.8% of a flat load's power cost**, and the most expensive 5% of hours carried **43.6%** of it ([evidence](evidence/03_ml_backtest.md)). Pumping is partly flexible (line-pack and tankage), but nobody gives operations a forward, regime-aware view of when those spikes will land.

| Lever | Who acts | What the build gives them |
| --- | --- | --- |
| **Operate** | Pipeline ops / control centre | A 24h forecast and hour ranking to move flexible pumping out of expensive hours |
| **Protect** | Energy desk / power procurement | A day-ahead Spike-regime probability and alerts, to act before the price lands |

## The data journey (one integrated flow)

| Stage | What runs | Where | Status |
| --- | --- | --- | --- |
| **Lakeflow** ingest | Hourly Lakeflow Job: pool price API (incremental MERGE from 2026-01-01), wind/solar CSV, wind/solar **metered history rebuilt from 99 assets** | `src/ingest/`, `resources/data_and_ml.yml` | ✅ |
| **Lakeflow** transform | Declarative pipeline: silver/gold materialized views with expectations (market price range, keys, regressor present) | `src/pipeline/transformations.py` | ✅ |
| **Unity Catalog** | Governed tags from the metastore's tag policies, table/column comments, lineage, AESO key as a **UC secret** (read by the job and the app identity), least-privilege grants | `src/governance/setup_uc.py` | ✅ |
| **ML** | 3-state HMM + Prophet + Monte Carlo, converged, ensemble; 5-day walk-forward backtest; MLflow; UC model `pool_price_ensemble@champion` | `src/ml/` | ✅ |
| **Lakebase** | Synced tables for the app's live cards + `ops_actions` write-back | `resources/serving.yml`, `src/lakebase/` | ✅ |
| **App** | AESO Market Pulse (FastAPI + Plotly.js), 9 cards + ops action form | `app/`, `resources/serving.yml` | ✅ |
| **Genie** | Genie space with instructions and a scored benchmark; screen-aware "Analyze with Genie" links into Genie One | `src/genie/`, `scripts/genie_benchmark.py` | ✅ |

## Results (real runs, see `evidence/`)

**Ingest:** 7,814 hourly prices (2026-01-01 to today), 7,751 metered wind/solar hours; only **10 of 7,979 regressor hours are imputed** ([01](evidence/01_ingest.md), [02](evidence/02_pipeline_governance.md)).

**Models:** the HMM finds Low (mean $7.69, 44.8% of hours), Normal ($27.52, 45.7%) and Spike ($179.35, 9.5%) regimes. Convergence cuts the Prophet vs Monte Carlo gap from **24.5 to 4.9 $/MWh** (latest run).

**Backtest, 5 days walk-forward (120 hours):**

| Model | MAE $/MWh | Note |
| --- | --- | --- |
| AESO forecast (baseline) | 3.37 | Published only hours ahead, so not a day-ahead forecast |
| **Ensemble** | **9.70** | Best day-ahead model, **56% better than same-hour-yesterday** |
| Regime-aware Prophet | 11.21 | Original Prophet was 34.91: excluding Spike hours fixes it |
| Same hour yesterday (baseline) | 21.90 | |

**Decision value:** shifting 4 h/day of flexible load by the forecast's ranking captured **64%** (ensemble) and **94%** (regime-aware Prophet) of the perfect-foresight savings on the backtest days. Perfect foresight is worth $115,688 per flexible MW over 2026 so far ([03](evidence/03_ml_backtest.md)).

**Serving:** Lakebase synced tables match Delta exactly (24 forecast rows, 7,814 price rows); an ops action written by the deployed app was read back and copied to Delta; the deployed app's API returns all 10 feeds with no errors ([04](evidence/04_lakebase_app.md)).

**Genie:** **8/8** benchmark questions matched hand-written ground-truth SQL ([05](evidence/05_genie_benchmark.md)). Each app card's "Analyze with Genie" link opens Genie One with a question built from what is on screen.

## Decisions and trade-offs

The full log, with alternatives, is in [docs/decisions.md](docs/decisions.md). The ones that mattered most:

1. **Metered-volume backfill instead of imputation.** The public wind CSV holds about 2 days of actuals. Rebuilding history from 99 metered assets made the Prophet regressor real.
2. **Converge before blending.** The original Prophet chased spikes (MAE 34.9). Training it without Spike hours and with a 50x tighter changepoint prior brought it to 11.2.
3. **Accuracy is not decision value.** The ensemble has the best MAE, but the regime-aware Prophet ranks expensive hours better (94% vs 64% capture). Scheduling should use the ranking.
4. **Honest baselines.** AESO's own forecast beats us on MAE because it is hours-ahead. We show it rather than hide it.
5. **Governance fits the customer's policies.** The first run failed on a governed `domain` tag; the build now uses the metastore's tag policies.

## AI workflow

Built with Claude Code: plan mode first (gap analysis against the FE Bar, questions answered by me), then phased builds (data engineering, ML, app, AI) with a `/goal` and per-phase PRs. Every number above is read from committed run output; AI-written code was run, checked and fixed against the live workspace (for example the metered API's exclusive `endDate`, found from a 250-hour imputation gap).

## How to run it

`databricks bundle deploy && databricks bundle run aeso_hourly` (see [README](README.md)). Evidence: `uv run --with databricks-sdk python scripts/export_evidence.py`.
