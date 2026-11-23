"""AESO Market Pulse: FastAPI backend.

Hot cards (current price, 48h curve, direction, regime, 24h forecast) read from **Lakebase** synced tables.
History cards (wind vs price, heatmap, backtest, leaderboard) read Delta through the **SQL warehouse**.
Ops actions (spike alerts, load shifts) are written to Lakebase `ops.ops_actions`.

Every timestamp leaves this file as a "YYYY-MM-DD HH:MM" string in Mountain Time wall clock, because the
`*_mpt` columns are timezone-naive. The browser parses the string; it never calls `new Date()` on it.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

CATALOG = os.getenv("AESO_CATALOG", "energy_canada_demos_catalog")
SCHEMA = os.getenv("AESO_SCHEMA", "aeso_price_forecast")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "fd18e0ef46eba09f")
PG_ENDPOINT = os.getenv("LAKEBASE_ENDPOINT", "projects/aeso-market-pulse/branches/production/endpoints/primary")
PG_DATABASE = os.getenv("PGDATABASE", "databricks_postgres")
FQ = f"{CATALOG}.{SCHEMA}"

w = WorkspaceClient()
app = FastAPI(title="AESO Market Pulse")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------- connections ----------
def warehouse_rows(query: str) -> list[dict]:
    """Delta through the SQL warehouse, authenticated as the app's service principal (no personal tokens)."""
    token = w.config.authenticate()["Authorization"].removeprefix("Bearer ")
    with dbsql.connect(server_hostname=w.config.host.removeprefix("https://"),
                       http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}", access_token=token) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


_pg = {"token": None, "expires": 0.0, "host": None, "user": None}


def pg_connect() -> psycopg.Connection:
    """Lakebase with a short-lived OAuth credential, refreshed before it expires."""
    if time.time() > _pg["expires"]:
        _pg["token"] = w.postgres.generate_database_credential(endpoint=PG_ENDPOINT).token
        _pg["expires"] = time.time() + 40 * 60
        _pg["host"] = os.getenv("PGHOST") or w.postgres.get_endpoint(PG_ENDPOINT).status.hosts.host
        _pg["user"] = os.getenv("PGUSER") or w.current_user.me().user_name
    conn = psycopg.connect(host=_pg["host"], dbname=PG_DATABASE, user=_pg["user"], password=_pg["token"],
                           sslmode="require", autocommit=True)
    conn.execute("SET TIME ZONE 'UTC'")   # naive MPT values were stored as UTC instants; keep the wall clock
    return conn


def pg_rows(query: str, params: tuple = ()) -> list[dict]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------- card queries ----------
PG_TS = "to_char({0}, 'YYYY-MM-DD HH24:MI')"
DB_TS = "date_format({0}, 'yyyy-MM-dd HH:mm')"
LATEST_RUN = "model_run_timestamp = (SELECT MAX(model_run_timestamp) FROM aeso_price_forecast.forecast_latest_synced)"

QUERIES = {
    # 1 + 2 + 5 (now): last 48 settled hours, newest last
    "prices": ("pg", f"""
        SELECT {PG_TS.format('begin_datetime_mpt')} AS ts, pool_price, rolling_30day_avg FROM (
          SELECT begin_datetime_mpt, pool_price, rolling_30day_avg FROM aeso_price_forecast.pool_price_hourly_synced
          WHERE pool_price IS NOT NULL ORDER BY begin_datetime_mpt DESC LIMIT 48) t ORDER BY begin_datetime_mpt"""),
    # 5, 6, 7: latest model run
    "forecast": ("pg", f"""
        SELECT {PG_TS.format('forecast_datetime_mpt')} AS ts, hour_ending, prophet_forecast_price, mc_p10_price,
               mc_p90_price, ensemble_forecast_price, forecast_regime, p_spike, hmm_current_regime,
               {PG_TS.format('model_run_timestamp')} AS run_ts
        FROM aeso_price_forecast.forecast_latest_synced WHERE {LATEST_RUN} ORDER BY forecast_datetime_mpt"""),
    # 3: wind vs price, last 7 days
    "wind": ("dbsql", f"""
        SELECT {DB_TS.format('p.begin_datetime_mpt')} AS ts, p.pool_price, w.actual_mw, w.most_likely_mw
        FROM {FQ}.aeso_pool_price p JOIN {FQ}.silver_wind_solar_hourly w
          ON DATE_TRUNC('hour', p.begin_datetime_mpt) = DATE_TRUNC('hour', w.forecast_transaction_date)
        WHERE p.pool_price IS NOT NULL
          AND p.begin_datetime_mpt >= (SELECT MAX(begin_datetime_mpt) FROM {FQ}.aeso_pool_price WHERE pool_price IS NOT NULL) - INTERVAL 7 DAYS
        ORDER BY p.begin_datetime_mpt"""),
    # 4: 7 x 24 heatmap, last 90 days. DAYOFWEEK: 1 = Sunday
    "heatmap": ("dbsql", f"""
        SELECT DAYOFWEEK(begin_datetime_mpt) AS dow, HOUR(begin_datetime_mpt) AS hour, ROUND(AVG(pool_price), 2) AS avg_price
        FROM {FQ}.aeso_pool_price
        WHERE pool_price IS NOT NULL AND begin_datetime_mpt >= (SELECT MAX(begin_datetime_mpt) FROM {FQ}.aeso_pool_price) - INTERVAL 90 DAYS
        GROUP BY 1, 2 ORDER BY 1, 2"""),
    # 8: latest backtest day of the latest run
    "backtest": ("dbsql", f"""
        SELECT {DB_TS.format('forecast_hour')} AS ts, hour_ending, actual, prophet_regime, mc_seasonal, ensemble,
               aeso_forecast, naive_yesterday, CAST(cutoff_date AS STRING) AS cutoff_date
        FROM {FQ}.aeso_backtest_detail
        WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_detail)
          AND cutoff_date = (SELECT MAX(cutoff_date) FROM {FQ}.aeso_backtest_detail)
        ORDER BY forecast_hour"""),
    # 9: leaderboard
    "leaderboard": ("dbsql", f"""
        SELECT model_name, model_type, ROUND(mae_cad_mwh, 2) AS mae_cad_mwh, ROUND(rmse_cad_mwh, 2) AS rmse_cad_mwh,
               ROUND(mape_pct, 1) AS mape_pct, n_days
        FROM {FQ}.aeso_backtest_metrics
        WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_metrics)
        ORDER BY mae_cad_mwh ASC LIMIT 3"""),
    # 0: plain-language accuracy score: the champion re-scored on several 14-day windows (rebaseline_windows.py)
    "accuracy": ("dbsql", f"""
        SELECT `window` AS window_label, model_name, ROUND(capture_rate_pct, 1) AS capture_pct, ROUND(mae_cad_mwh, 2) AS mae,
               n_days, (SELECT CONCAT('v', MAX_BY(champion_version, run_timestamp)) FROM {FQ}.aeso_backtest_metrics) AS champion
        FROM {FQ}.aeso_backtest_windows
        WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_windows)"""),
    # ops actions written by this app
    "actions": ("pg", f"""
        SELECT action_id, {PG_TS.format('created_at')} AS created_utc, created_by, action_type,
               {PG_TS.format('window_start_mpt')} AS window_start, {PG_TS.format('window_end_mpt')} AS window_end,
               mw, threshold, note FROM ops.ops_actions ORDER BY action_id DESC LIMIT 8"""),
}


def run_query(name: str) -> list[dict]:
    kind, query = QUERIES[name]
    return pg_rows(query) if kind == "pg" else warehouse_rows(query)


@app.on_event("startup")
def create_ops_table() -> None:
    """Make sure the write-back table exists (scripts/grant_app_sp.py creates and grants it on deploy)."""
    try:
        _create_ops_table()
    except psycopg.Error as exc:   # e.g. no CREATE on the database yet: the grant script fixes it
        print(f"ops.ops_actions not created at startup: {exc}")


def _create_ops_table() -> None:
    with pg_connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
        conn.execute("""CREATE TABLE IF NOT EXISTS ops.ops_actions (
            action_id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by TEXT,
            action_type TEXT NOT NULL CHECK (action_type IN ('spike_alert', 'load_shift')),
            window_start_mpt TIMESTAMP NOT NULL, window_end_mpt TIMESTAMP NOT NULL,
            mw DOUBLE PRECISION, threshold DOUBLE PRECISION, note TEXT)""")


# ---------- API ----------
@app.get("/api/dashboard")
def dashboard() -> dict:
    """Everything the page needs in one round trip; queries run in parallel."""
    with ThreadPoolExecutor(max_workers=len(QUERIES)) as pool:
        futures = {name: pool.submit(run_query, name) for name in QUERIES}
    data, errors = {}, {}
    for name, fut in futures.items():
        try:
            data[name] = fut.result()
        except Exception as exc:   # one failing card must not blank the whole terminal
            data[name], errors[name] = [], str(exc)[:300]
    return {"data": data, "errors": errors, "genie": genie_config()}


class OpsAction(BaseModel):
    action_type: str = Field(pattern="^(spike_alert|load_shift)$")
    window_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
    window_end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
    mw: float | None = Field(default=None, ge=0, le=500)
    threshold: float | None = Field(default=None, ge=0, le=1)
    note: str | None = Field(default=None, max_length=500)


@app.post("/api/ops_actions")
def add_action(action: OpsAction, request: Request) -> dict:
    if action.window_end <= action.window_start:
        raise HTTPException(400, "window_end must be after window_start")
    user = request.headers.get("X-Forwarded-Email") or request.headers.get("X-Forwarded-User") or "local"
    rows = pg_rows("""INSERT INTO ops.ops_actions (created_by, action_type, window_start_mpt, window_end_mpt, mw, threshold, note)
                      VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING action_id""",
                   (user, action.action_type, action.window_start, action.window_end, action.mw, action.threshold,
                    action.note))
    return {"action_id": rows[0]["action_id"]}


def genie_config() -> dict:
    return {"host": w.config.host.rstrip("/"), "workspace_id": str(w.get_workspace_id()), "fq": FQ}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
