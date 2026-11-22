---
name: deploy-and-run
description: Use to deploy the bundle, run or debug the hourly and daily jobs, re-bootstrap data, point at another workspace, or tear everything down.
---

# Deploy and run

| Step | Command | Check |
| --- | --- | --- |
| 1. Sign in | `databricks auth login --profile fevm-energy-canada` | `databricks current-user me` |
| 2. Validate | `databricks bundle validate` | Prints host and `/Workspace/Users/<you>/aeso-market-pulse` |
| 3. Deploy | `databricks bundle deploy` | `Resources: ... created/changed` |
| 4. Hourly run | `databricks bundle run aeso_hourly` | `TERMINATED SUCCESS`; about 4 minutes |
| 5. Backtest run | `databricks bundle run aeso_daily_backtest` | `TERMINATED SUCCESS`; new `@champion` version |

## Common tasks

| You want to | Do |
| --- | --- |
| Rebuild metered wind/solar history | `databricks bundle run aeso_hourly --params full_refresh=true` |
| Rebuild everything from 2026-01-01 | Drop the three bronze tables (ask first: this deletes data), then run step 4 |
| Use another workspace or schema | Change `targets.dev.workspace` in `databricks.yml` or pass `--var catalog=... --var schema=...`; create the UC secret `aeso_api_key` in the new schema first |
| Tear down | `databricks bundle destroy` (removes jobs, pipeline, app, Lakebase; tables written by notebooks stay) |

## When a task fails

1. Find the task's error: `databricks jobs get-run-output <task_run_id>` (`error` and `error_trace`).
2. Fix the cause in the repo, redeploy, rerun. Never patch the workspace copy by hand.
3. If you learned something, add it to **Gotchas** in `AGENTS.md`.
