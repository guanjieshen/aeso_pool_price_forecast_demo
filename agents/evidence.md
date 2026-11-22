# Evidence

Reviewers read text, not screenshots. `evidence/` holds real run output from the live workspace.

| File | Proves | Made by |
| --- | --- | --- |
| `01_ingest.md` | The three ingest tasks ran; bronze coverage | `scripts/export_evidence.py` |
| `02_pipeline_governance.md` | Pipeline tables, imputation share, governed tags, lineage, secret governance | same |
| `03_ml_backtest.md` | HMM regimes, convergence, backtest leaderboard, business value, `@champion` | same |
| `03b_hourly_forecast.md` | The hourly forecast the app shows | same |
| `04_lakebase_app.md` | Synced tables match Delta, write-back round trip, the deployed app's API | same |
| `05_genie_benchmark.md` | Genie score against ground truth, with Genie's SQL | `scripts/genie_benchmark.py` |
| `raw/` (git-ignored) | Full cell output per task, regenerated locally | `scripts/export_evidence.py` |

**Rules:** each curated file stays under 9,000 characters (the scorer reads only that much per file). Emails are redacted to `<user>` because the repo is public. Never edit evidence by hand; rerun the script. Refresh with the skill [`refresh-evidence`](skills/refresh-evidence/SKILL.md).
