# FE Bar: AESO pool price forecast for Enbridge Liquids Pipelines

**Industry:** energy, midstream oil and gas pipelines. **Customer:** Enbridge Liquids Pipelines. **Data:** public AESO market data only (no customer data).

## The business problem

Power is the **largest operating cost** for a liquids pipeline. Its Alberta pump stations buy electricity at the hourly **AESO pool price**, which runs from near $0 to the $999.99/MWh cap. In 2026 so far, the 200 hours priced above $150/MWh were **2.6% of hours but 35.8% of a flat load's power cost**, and the most expensive 5% of hours carried **43.5%** of it ([evidence](evidence/03_ml_backtest.md)). Pumping is partly flexible (line-pack and tankage), but nobody gives operations a forward, regime-aware view of when those spikes will land.

| Lever | Who acts | What the build gives them |
| --- | --- | --- |
| **Operate** | Pipeline ops / control centre | A 24h forecast and hour ranking to move flexible pumping out of expensive hours |
| **Protect** | Energy desk / power procurement | A day-ahead Spike-regime probability and alerts, to act before the price lands |

## The data journey (one integrated flow)

| Stage | What runs | Where | Status |
| --- | --- | --- | --- |
| **Lakeflow** ingest | Hourly Lakeflow Job: pool price API (incremental MERGE from 2026-01-01), wind/solar CSV, wind/solar **metered history rebuilt from 99 assets**, **supply fundamentals** (load, capability net of outages, intertie imports) with an **as-published snapshot archive** | `src/ingest/`, `resources/data_and_ml.yml` | ✅ |
| **Lakeflow** transform | Declarative pipeline: silver/gold materialized views with expectations (market price range, keys, regressor present) | `src/pipeline/transformations.py` | ✅ |
| **Unity Catalog** | Governed tags from the metastore's tag policies, table/column comments, lineage, AESO key as a **UC secret** (read by the job and the app identity), least-privilege grants | `src/governance/setup_uc.py` | ✅ |
| **ML** | 3-state HMM + Prophet + Monte Carlo, converged, ensemble, plus a **supply-cushion fundamentals model** for thin-cushion hours; walk-forward backtest on **day-ahead (as-known) features**; MLflow; UC model `pool_price_ensemble@champion` | `src/ml/` | ✅ |
| **ML lifecycle** | **Self-improving:** weekly challenger, **model update trigger** on `@challenger`, gated promotion on capture rate, forecast archive + daily drift monitor | `src/ml/train_challenger.py`, `evaluate_challenger.py`, `daily_monitor.py` | ✅ |
| **Lakebase** | Synced tables for the app's live cards + `ops_actions` write-back | `resources/serving.yml`, `src/lakebase/` | ✅ |
| **App** | AESO Market Pulse (FastAPI + Plotly.js), a plain-language accuracy score, 9 cards + ops action form | `app/`, `resources/serving.yml` | ✅ |
| **Genie** | Genie space with instructions and a scored benchmark; screen-aware "Analyze with Genie" links into Genie One | `src/genie/`, `scripts/genie_benchmark.py` | ✅ |

## Results (real runs, see `evidence/`)

**Ingest:** 7,839 hourly prices (2026-01-01 to today), 7,823 metered wind/solar hours; only **1 of 8,004 regressor hours is imputed** ([01](evidence/01_ingest.md), [02](evidence/02_pipeline_governance.md)).

**What drives the price.** Alberta clears the cheapest offers first, so the price follows the **supply cushion** (available gas, hydro and storage + wind/solar + intertie imports - forecast load). It explains **24.0% of 2026 price variance and 17.9% of spike variance**, against 12.2% and 5.7% for wind alone; hours under 2,000 MW of cushion are **6.1% of hours but 78% of spike hours** ([07](evidence/07_fundamentals.md)). Outages, load or capability on their own explain about 1 to 2%.

**No look-ahead.** Backtests feed the test day only what was known before it began: AESO's **published wind/solar forecast** (MAE 364 MW against actuals) and the cushion built from it, never the realised wind. Each hourly run also archives the forward fundamentals as published, so this holds after AESO's monthly file ends ([07](evidence/07_fundamentals.md)). Re-scored this way, the previous champion v5 averages **76.7% capture over three 14-day windows** (73.1% on the latest, Oct 18 to 31), not the 90.2% it showed on a quiet window with realised wind. The current champion v7 averages **87.3%**, against 91.7% for AESO's hours-ahead forecast ([06](evidence/06_model_lifecycle.md)).

**The models improve themselves.** Every Monday a challenger recipe is tuned on an earlier window and registered as `@challenger`; the **model update trigger** backtests it against `@champion` on the same days and promotes it only if it captures more load-shift value without worse accuracy. The supply-cushion recipe (v7) was promoted over v5 on Oct 18 to 31: capture **73.1% to 80.3%**, MAE **31.79 to 27.37**. A Prophet-only tweak (v6) was rejected the same day ([06](evidence/06_model_lifecycle.md)).

**Backtest of the current champion (v7), 14 days walk-forward on day-ahead features (336 hours, Oct 18 to 31):**

| Model | MAE $/MWh | Capture | Note |
| --- | --- | --- | --- |
| AESO forecast (baseline) | 16.24 | 91.0% | Published only hours ahead, so not a day-ahead forecast |
| **Ensemble + cushion model (champion v7)** | **27.37** | **80.3%** | Best day-ahead model, **54% better than same-hour-yesterday** |
| Regime-aware Prophet | 30.36 | 80.4% | Plain Prophet: 44.53. Excluding Spike hours fixes it |
| Same hour yesterday (baseline) | 59.85 | 23.0% | |

**Models:** the HMM finds Low (mean $7.63, 44.3% of hours), Normal ($27.39, 46.1%) and Spike ($178.37, 9.6%) regimes. Convergence cuts the Prophet vs Monte Carlo gap from **19.2 to 6.1 $/MWh** (latest run) ([03](evidence/03_ml_backtest.md)).

**Decision value:** perfect foresight is worth **$115,776 per flexible MW** over 2026 so far (4 shifted hours a day). At the champion's 80.3% capture that is an indicative **$0.93M per 10 MW** ([03](evidence/03_ml_backtest.md)).

**Serving:** Lakebase synced tables match Delta exactly (24 forecast rows, 7,839 price rows); an ops action written by the deployed app was read back and copied to Delta; the deployed app's API returns all 10 feeds with no errors ([04](evidence/04_lakebase_app.md)).

**Genie:** **8/8** benchmark questions matched hand-written ground-truth SQL ([05](evidence/05_genie_benchmark.md)). Each app card's "Analyze with Genie" link opens Genie One with a question built from what is on screen.

## Decisions and trade-offs

The full log, with alternatives, is in [docs/decisions.md](docs/decisions.md). The ones that mattered most:

1. **Metered-volume backfill instead of imputation.** The public wind CSV holds about 2 days of actuals. Rebuilding history from 99 metered assets made the Prophet regressor real.
2. **Converge before blending.** The original Prophet chased spikes (MAE 34.9). Training it without Spike hours and with a 50x tighter changepoint prior brought it to 11.2.
3. **Promote on decision value, guard on accuracy.** The first backtest showed the best-MAE model was not the best at ranking expensive hours ([decision #10](docs/decisions.md)). So the champion is chosen on capture rate with an MAE guard; both promotions so far led on both.
4. **Fundamentals over more curve-fitting.** Five rounds of research on public AESO data found one strong driver (the cushion), that a linear Prophet regressor cannot use it (the price-cushion curve is a hockey stick), and that a gradient-boosted model switched in below 2,500 MW of cushion can. Merit-order snapshots (published 60 days late) failed as a predictor ([decisions #20 to #22](docs/decisions.md)).
5. **Honest baselines and no look-ahead.** AESO's own forecast beats us on MAE because it is hours-ahead. We show it rather than hide it, and we re-scored our own champion on day-ahead wind when we found the backtest was seeing realised wind.
6. **Governance fits the customer's policies.** The first run failed on a governed `domain` tag; the build now uses the metastore's tag policies.
7. **Self-improvement without a babysitter.** A model update trigger (not a cron poll) evaluates any version given `@challenger`, so a data scientist can submit an idea and the same gate judges it.

## AI workflow

Built with Claude Code: plan mode first (gap analysis against the FE Bar, questions answered by me), then phased builds (data engineering, ML, app, AI, self-improving models, fundamentals) with a `/goal` and per-phase PRs. Every number above is read from committed run output; AI-written code was run, checked and fixed against the live workspace (for example the metered API's exclusive `endDate`, found from a 250-hour imputation gap).

## How to run it

`databricks bundle deploy && databricks bundle run aeso_hourly` (see [README](README.md)). Evidence: `uv run --with databricks-sdk python scripts/export_evidence.py`.
