# Working on this repository

Guidance for **coding agents and people** changing the AESO pool price forecast: the ingest notebooks, the pipeline, the models, the app, Lakebase and Genie. If you only want to see what it does, read [FE_BAR.md](FE_BAR.md) and the [README](README.md).

> **Start here.** Read this file (the rules and the workflow), then the guide for the part you are changing. For any request, the skill [`start-here`](agents/skills/start-here/SKILL.md) turns it into a precise task.

## What this repository is

A day-ahead Alberta pool price forecast that helps Enbridge Liquids Pipelines protect its largest operating cost: power for pump stations. It is **one data journey**, deployed by **one Databricks Asset Bundle**:

| Stage | What it is | Folders | Guide |
| --- | --- | --- | --- |
| **Ingest + transform** | Hourly Lakeflow Job: AESO API and CSV into bronze (MERGE), declarative pipeline to silver/gold | `src/ingest/`, `src/pipeline/`, `resources/data_and_ml.yml` | [agents/data.md](agents/data.md) |
| **Governance** | Governed tags, comments, grants, the AESO key as a UC secret | `src/governance/` | [agents/data.md](agents/data.md) |
| **ML** | HMM + Prophet + Monte Carlo ensemble, walk-forward backtest, MLflow, UC model, business value, and the **self-improving lifecycle** (weekly challenger, model update trigger, gated promotion, drift monitor) | `src/ml/`, `resources/data_and_ml.yml` | [agents/ml.md](agents/ml.md) |
| **Serving** | Lakebase synced tables and `ops_actions` write-back, the AESO Market Pulse app | `app/`, `src/lakebase/`, `resources/serving.yml` | [agents/app.md](agents/app.md) |
| **AI** | Genie space, benchmark, Genie One deep links | `src/genie/`, `resources/serving.yml`, `scripts/genie_benchmark.py` | [agents/genie.md](agents/genie.md) |
| **Evidence** | Text output of real runs, for reviewers | `evidence/`, `scripts/export_evidence.py` | [agents/evidence.md](agents/evidence.md) |

**Where the stages meet** (change both sides in one pull request when you touch these):

- **Table contracts.** The app's cards and the Genie space read columns by name (`aeso_price_forecast_output.ensemble_forecast_price`, `forecast_regime`, `p_spike`, `aeso_backtest_detail.cutoff_date`, ...). Renaming a column means changing the producer, `app/app.py`, `src/genie/` and `src/governance/setup_uc.py` together.
- **Time.** Every `*_mpt` column is a **naive Mountain Time wall clock**. Every Spark session pins `spark.sql.session.timeZone=UTC` so the values are stored as-is. The app never passes them to `new Date()`.
- **New tables** must be added to `TABLES` in `src/governance/setup_uc.py` so they get tags and app grants.

## Where the docs are

| File | For | Holds |
| --- | --- | --- |
| `FE_BAR.md` | Reviewers, first | The problem, the journey, results, decisions, AI workflow |
| `README.md` | Everyone | What it does, deploy, run, tear down |
| `docs/IMPLEMENTATION_PLAN.md` | Maintainers | Phases, status, table list, conventions |
| `docs/decisions.md` | Maintainers, reviewers | Every decision with the alternative and why |
| `AGENTS.md`, `agents/*.md` | Coding agents | How to change each part, and its gotchas |
| `agents/skills/*/SKILL.md` | Coding agents | Step-by-step workflows (linked into `.claude/skills/`) |
| `evidence/` | Reviewers | Real run output as text (full per-task output regenerates into the git-ignored `evidence/raw/`) |

## How to update this project

1. **Branch from `main`**, one phase or topic per pull request.
2. **Change the code, its guide and its evidence together** (table below).
3. **Deploy and run it for real:** `databricks bundle deploy`, then `databricks bundle run <job>`. A change is not done until it ran green in the workspace.
4. **Refresh the evidence** with the skill [`refresh-evidence`](agents/skills/refresh-evidence/SKILL.md), and update any number in `FE_BAR.md` or `docs/decisions.md` that changed.
5. **Open a pull request** into `main`; a person merges.

| You change | Also change |
| --- | --- |
| An ingest notebook or the pipeline | `agents/data.md` if a rule or gotcha changed; rerun `aeso_hourly`; refresh `evidence/01_*`, `02_*` |
| A model, weight or metric | `agents/ml.md`, `docs/decisions.md` (new row); submit it as a challenger (skill `retrain-and-backtest`); refresh `evidence/03_ml_backtest.md` and `06_model_lifecycle.md`; update the numbers in `FE_BAR.md` |
| A column the app or Genie reads | Producer + `app/app.py` + `src/genie/` + `src/governance/setup_uc.py` in one PR |
| A new table | `TABLES` in `src/governance/setup_uc.py`; the table list in `docs/IMPLEMENTATION_PLAN.md` |
| An app card | `agents/app.md` (card to query map and design rules), the card's Genie One prompt |
| The Genie space | `src/genie/`, then rerun `scripts/genie_benchmark.py` and commit the score |

## Rules

1. **No secrets in code, output or chat.** The AESO key lives only in the UC secret `aeso_price_forecast.aeso_api_key`, read with `dbutils.secrets.get(catalog=, schema=, key=)`. Never print it, never request `include_value=true`.
2. **Public and synthetic data only.** No customer data, ever. Customer-stated figures stay out of this public repo (keep them in the git-ignored `private/`).
3. **Every number traces to a run.** A number in `FE_BAR.md`, the deck or a doc must appear in `evidence/` or a query you ran. If it does not exist, query for it or write around it.
4. **Deploy only through the bundle.** No hand-made jobs, pipelines or apps in the workspace.
5. **Least privilege.** The app's service principal reads only the tables it shows, plus `READ SECRET` on the AESO key (an owner decision, `docs/decisions.md` #5). Grant nothing else.
6. **Never bypass git hooks.**

## Writing style

Lead with what matters. Tables for anything with more than two parts. **Bold the key phrase**, not whole sentences. Short sentences, sentence-case headings, no em dashes. One home per topic: link instead of repeating. Code comments explain why, not what.

## Gotchas learned the hard way

- **The metered volume API's `endDate` is exclusive**; the pool price report's is inclusive. Getting this wrong silently drops the last day of every window (it showed up as 250 imputed hours).
- **The metered volume API rejects long `asset_ID` lists** (400 at 25 IDs); 10 per call works.
- **The wind/solar CSV holds only about 2 days of actuals**; history comes from metered volumes.
- **`domain` and `layer` are governed tags** in this metastore with fixed value lists; an unlisted value fails the whole statement.
- **Secret DDL is not enabled in Spark SQL** here (`UC_SECRETS_NOT_ENABLED` on `COMMENT ON SECRET`); use the UC REST API. `dbutils.secrets.get` works on serverless.
- **DAYOFWEEK returns 1 = Sunday.**
- **Notebook output is evidence.** Print results as text (`toPandas().to_string()`); charts alone are images the reviewer cannot read.
