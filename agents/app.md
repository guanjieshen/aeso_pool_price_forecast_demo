# App and Lakebase: AESO Market Pulse

A FastAPI backend (`app/app.py`) and one page (`app/static/index.html`, Plotly.js) deployed as a Databricks App by the bundle (`resources/serving.yml`). It refreshes every 5 minutes.

## Layout: ordered by decision

| Section | Cards | The question it answers |
| --- | --- | --- |
| Header | Out-today chip (from `outages`), forecast score badge + popover (card 0) | Can I trust this, and is supply tight today? |
| Now | 1 Pool price, 5 Next 6 hours | What is the market doing? |
| Plan the next 24 hours | 7 24-hour forecast (wide), 6 Regime / spike risk, 2 48-hour curve | Which hours to avoid, how likely is a spike? |
| Act | 10 Ops actions (wide) | Log a spike alert or load shift |
| Why | 11 Outage outlook (wide), 3 Wind vs price, 4 Heatmap | What on the supply side is driving it? |
| Check the model | 8 Backtest day, 9 Leaderboard | How did it do on past days? |

Keep this order when adding a card: put it in the section whose question it answers.

**Responsive:** two columns on desktop, one below 900px; below 700px the header wraps, the score popover becomes a fixed panel, the ops form uses two columns and tables scroll inside their card. Grid items have `min-width: 0` so a wide table or form never widens the page.

## Where each card reads from

| # | Card | Feed | Source | Filter |
| --- | --- | --- | --- | --- |
| 0 | Forecast score badge (header, click for the popover) | `accuracy` | Warehouse: `aeso_backtest_windows` | Latest re-baseline run: champion's mean capture over three 14-day windows as a 0 to 100 score (STRONG ≥ 85, FAIR ≥ 70), vs AESO and same hour yesterday, typical error = MAE. Refreshed after every promotion by `rebaseline_windows.py` |
| 1 | Pool price right now | `prices` | **Lakebase** `aeso_price_forecast.pool_price_hourly_synced` | Latest non-null `pool_price` |
| 2 | 48-hour price curve | `prices` | Lakebase | Last 48 settled rows |
| 3 | Wind + solar vs price (7 days) | `wind` | Warehouse: `aeso_pool_price` x `silver_wind_solar_hourly` | `DATE_TRUNC('hour', ...)` join |
| 4 | Peak hour heatmap | `heatmap` | Warehouse: `aeso_pool_price` | Last 90 days, `DAYOFWEEK` 1 = Sunday |
| 5 | Price direction (next 6h) | `prices` + `forecast` | Lakebase | Avg of first 6 ensemble rows vs now; ±5% = stable |
| 6 | 24h regime forecast | `forecast` | **Lakebase** `forecast_latest_synced` | `model_run_timestamp = MAX(...)` |
| 7 | 24h price forecast | `forecast` | Lakebase | Same; background tinted by `forecast_regime` |
| 8 | Backtest actual vs predicted | `backtest` | Warehouse: `aeso_backtest_detail` | Latest run, and its last `cutoff_date` (not the max over all runs: day-ahead windows can end earlier than older runs) |
| 9 | Leaderboard | `leaderboard` | Warehouse: `aeso_backtest_metrics` | Latest run, top 3 by MAE |
| 11 | Generation outage outlook (wide) | `outages` | Warehouse: `aeso_outage_outlook` | Latest snapshot: daily MW out by fuel group for the next 30 days (stacked bars), monthly averages for the next 12 months |
| 10 | Ops actions | `actions` | **Lakebase** `ops.ops_actions` (read/write) | Latest 8 |

One call, `GET /api/dashboard`, runs every feed in parallel; a failing feed returns `[]` plus an entry in `errors`, so one bad card never blanks the page. `POST /api/ops_actions` validates and inserts a spike alert or load shift.

## Auth and permissions

- **Warehouse:** `WorkspaceClient().config.authenticate()["Authorization"]`, minus `Bearer `, as `access_token` for `databricks-sql-connector`; HTTP path `/sql/1.0/warehouses/{id}`. The app's service principal, never a personal token.
- **Lakebase:** `w.postgres.generate_database_credential(endpoint=...)`, refreshed every 40 minutes; the app resource `postgres` (`CAN_CONNECT_AND_CREATE`) creates the service principal's Postgres role.
- **After every first deploy:** `uv run --with databricks-sdk --with "psycopg[binary]" python scripts/grant_app_sp.py`. It grants `USE SCHEMA` + `SELECT` on the five tables the app reads, and Postgres `SELECT` on the synced tables plus `SELECT, INSERT` on `ops.ops_actions`. It also grants `READ SECRET` on the AESO key. `USE CATALOG` is inherited from `account users` here (we cannot grant it: no MANAGE on the shared catalog).

## Lakebase flow

1. The hourly job's `lakebase_sync` task refreshes both **snapshot synced tables** after the forecast is written, and prints Lakebase vs Delta row counts.
2. It then copies `ops.ops_actions` into Delta `ops_actions_history`, so Genie can join decisions to prices.

## Design rules (Bloomberg terminal)

- Background `#05070d`, cards `#0a0f1c` with 1px `#1c2740` borders, monospace numerics, uppercase card titles.
- **Price colors:** green under $50, amber $50 to $150, red above $150. **Regimes:** Low green, Normal blue, Spike red.
- Header: pulsing green LIVE dot, "Updated <latest settled hour> MPT".
- **Time:** the API returns `"YYYY-MM-DD HH:MM"` strings. `parseTs()` splits them with a regex; never `new Date()` on an MPT value.
- Two columns, one below 900px. Every card has an **ANALYZE WITH GENIE** link (see [genie.md](genie.md)).

## Run locally

`cd app && DATABRICKS_CONFIG_PROFILE=fevm-energy-canada uv run --with-requirements requirements.txt uvicorn app:app --port 8765`, then open `http://localhost:8765`. Locally the app runs as you.
