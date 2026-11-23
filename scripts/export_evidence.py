"""Export execution evidence as text: notebook outputs from the latest successful job runs plus live queries.

Usage (from the repo root, signed in with the Databricks CLI):
    uv run --with databricks-sdk python scripts/export_evidence.py [--profile fevm-energy-canada]

Writes evidence/raw/<job>__<task>.md (full cell output) and evidence/0N_*.md (curated, each under 9,000
characters so the FE Bar scorer reads it whole). Never prints secrets: the notebooks never output them.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import time
import urllib.parse
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import ViewsToExport

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
FQ = "energy_canada_demos_catalog.aeso_price_forecast"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
NOISE = re.compile(r"Downloading artifacts|Uploading artifacts|widget-view|View Logged Model|Validating input example|already exists. Creating|cmdstanpy|Importing plotly|FutureWarning|you may need to restart the kernel|^\s*\S+ = .*groupby|include_groups|UserWarning|pd.read_sql")
MAX_CHARS = 8800
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")   # public repo: never publish people's emails


def redact(text: str) -> str:
    return EMAIL.sub("<user>", text)

# Curated file -> (title, [(job name, task key)], [(label, SQL)])
SECTIONS = {
    "01_ingest.md": ("Ingest: AESO API + CSV into bronze Delta (Lakeflow Job tasks)", [
        ("aeso-hourly", "ingest_pool_price"), ("aeso-hourly", "ingest_wind_solar_forecast"),
        ("aeso-hourly", "ingest_wind_solar_metered"), ("aeso-hourly", "ingest_outage_outlook")], [
        ("Bronze coverage", f"""SELECT 'aeso_pool_price' AS table_name, COUNT(*) AS rows, MIN(begin_datetime_mpt) AS first_mpt, MAX(begin_datetime_mpt) AS last_mpt FROM {FQ}.aeso_pool_price
UNION ALL SELECT 'aeso_wind_solar_metered', COUNT(*), MIN(begin_datetime_mpt), MAX(begin_datetime_mpt) FROM {FQ}.aeso_wind_solar_metered
UNION ALL SELECT 'aeso_wind_solar_forecast', COUNT(*), MIN(forecast_transaction_date), MAX(forecast_transaction_date) FROM {FQ}.aeso_wind_solar_forecast""")]),
    "02_pipeline_governance.md": ("Declarative pipeline (silver/gold, expectations) and Unity Catalog governance", [
        ("aeso-hourly", "governance")], [
        ("Wind/solar regressor source (how much is imputed)", f"SELECT regressor_source, COUNT(*) AS hours FROM {FQ}.silver_wind_solar_hourly GROUP BY 1 ORDER BY 2 DESC"),
        ("Gold features", f"SELECT COUNT(*) AS rows, COUNT(y) AS settled, MIN(ds) AS first_mpt, MAX(ds) AS last_mpt, SUM(CAST(is_imputed AS INT)) AS imputed_hours FROM {FQ}.gold_price_features_hourly"),
        ("Governed tags per table", f"SELECT table_name, tag_name, tag_value FROM energy_canada_demos_catalog.information_schema.table_tags WHERE schema_name = 'aeso_price_forecast' AND tag_name IN ('layer','data_product','domain') ORDER BY table_name, tag_name"),
        ("Lineage: what reads the gold table", f"SELECT DISTINCT source_table_full_name, target_table_full_name, entity_type FROM system.access.table_lineage WHERE source_table_full_name LIKE '{FQ}.%' AND target_table_full_name IS NOT NULL AND event_date >= current_date() - INTERVAL 2 DAYS ORDER BY 1, 2")]),
    "03_ml_backtest.md": ("ML: HMM + Prophet + Monte Carlo ensemble, walk-forward backtest of the champion, business value", [
        ("aeso-hourly", "forecast"), ("aeso-evaluate-challenger", "business_value")], [
        ("Latest backtest leaderboard (current @champion, same 14 days for every series)", f"SELECT model_name, model_type, ROUND(mae_cad_mwh,2) AS mae, ROUND(rmse_cad_mwh,2) AS rmse, ROUND(mape_pct,1) AS mape_pct, ROUND(capture_rate_pct,1) AS capture_pct, n_days, champion_version FROM {FQ}.aeso_backtest_metrics WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_metrics) ORDER BY mae"),
        ("Business value (latest run)", f"SELECT metric, strategy, scenario_mw, ROUND(value,2) AS value FROM {FQ}.aeso_business_value WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_business_value) AND (strategy IS NULL OR metric = 'capture_rate_pct' OR (metric = 'indicative_ytd_value_cad' AND scenario_mw = 10)) ORDER BY strategy NULLS FIRST, metric")]),
    "04_lakebase_app.md": ("Lakebase serving + AESO Market Pulse app (deployed)", [("aeso-hourly", "lakebase_sync")], [
        ("Ops actions copied back to Delta (written by the app into Lakebase)", f"SELECT action_id, action_type, window_start_mpt, window_end_mpt, mw, threshold, note FROM {FQ}.ops_actions_history ORDER BY action_id"),
        ("Synced tables registered in Unity Catalog", f"SELECT table_name, table_type, comment FROM energy_canada_demos_catalog.information_schema.tables WHERE table_schema = 'aeso_price_forecast' AND table_name LIKE '%_synced'")]),
    "06_model_lifecycle.md": ("Self-improving models: weekly challenger, model update trigger, gated promotion", [
        ("aeso-weekly-retrain", "train_challenger"), ("aeso-evaluate-challenger", "evaluate_and_promote"),
        ("aeso-rebaseline", "rebaseline_windows")], [
        ("Promotion decisions", f"SELECT evaluated_at, champion_version, challenger_version, decision, ROUND(champion_capture_rate_pct,1) AS champ_capture, ROUND(challenger_capture_rate_pct,1) AS chall_capture, ROUND(champion_mae_cad_mwh,2) AS champ_mae, ROUND(challenger_mae_cad_mwh,2) AS chall_mae, eval_start, eval_end FROM {FQ}.aeso_model_promotions ORDER BY evaluated_at"),
        ("Hourly forecasts archived per champion version (live accuracy input)", f"SELECT champion_version, COUNT(DISTINCT model_run_timestamp) AS runs, COUNT(*) AS forecast_hours, MIN(model_run_timestamp) AS first_run_utc, MAX(model_run_timestamp) AS last_run_utc FROM {FQ}.aeso_forecast_history GROUP BY 1 ORDER BY 1")]),
    "07_fundamentals.md": ("Fundamentals: supply cushion drivers, day-ahead (as-known) features, snapshot archive", [
        ("aeso-hourly", "ingest_supply_demand"), ("aeso-daily-monitor", "price_drivers")], [
        ("Day-ahead feature coverage by month (backtests use only these)", f"SELECT date_format(ds, 'yyyy-MM') AS month, COUNT(y) AS settled_hours, COUNT(supply_cushion_dayahead_mw) AS dayahead_hours, MAX_BY(dayahead_source, ds) AS source, ROUND(AVG(supply_cushion_mw)) AS avg_cushion_mw, ROUND(AVG(import_atc_mw)) AS avg_import_atc_mw FROM {FQ}.gold_price_features_hourly GROUP BY 1 ORDER BY 1"),
        ("Published wind/solar forecast accuracy (AESO file vs actual)", f"SELECT COUNT(*) AS hours, ROUND(AVG(ABS(wind_solar_forecast_mw - wind_solar_actual_mw))) AS mae_mw, ROUND(AVG(wind_solar_forecast_mw - wind_solar_actual_mw)) AS bias_mw, ROUND(AVG(wind_solar_actual_mw)) AS avg_actual_mw, MAX(forecast_datetime_mpt) AS last_hour_mpt FROM {FQ}.aeso_wind_solar_published WHERE wind_solar_actual_mw IS NOT NULL"),
        ("Snapshot archive (what was known at each run)", f"SELECT COUNT(DISTINCT snapshot_at) AS snapshots, COUNT(*) AS rows, MIN(snapshot_at) AS first_snapshot_utc, MAX(snapshot_at) AS last_snapshot_utc, MAX(begin_datetime_mpt) AS furthest_hour_mpt FROM {FQ}.aeso_fundamentals_snapshots"),
        ("Live forecast: cushion, fundamentals weight and P(price > $150), next 24 h", f"SELECT forecast_datetime_mpt, ROUND(supply_cushion_mw) AS cushion_mw, ROUND(fundamentals_weight, 2) AS fund_weight, ROUND(fundamentals_price, 2) AS fund_price, ROUND(ensemble_forecast_price, 2) AS ensemble, ROUND(p_above_150, 3) AS p_above_150 FROM {FQ}.aeso_price_forecast_output ORDER BY 1")]),
}
APP_URL = "https://aeso-market-pulse-7474654566745717.aws.databricksapps.com"


def app_capture(w: WorkspaceClient) -> str:
    """Call the deployed app's API as the signed-in user (SDK auth; the token is never printed)."""
    import requests
    started = time.time()
    resp = requests.get(f"{APP_URL}/api/dashboard", headers=w.config.authenticate(), timeout=180)
    secs = time.time() - started
    d = resp.json()
    lines = [f"`GET {APP_URL}/api/dashboard` -> HTTP {resp.status_code} in {secs:.1f}s; card errors: {d.get('errors') or 'none'}", "",
             "| Feed | Source | Rows | First row |", "|---|---|---|---|"]
    for name, rows in d["data"].items():
        first = json.dumps(rows[0], default=str)[:230] if rows else ""
        lines.append(f"| {name} | {'Lakebase' if name in ('prices', 'forecast', 'actions') else 'SQL warehouse'} | {len(rows)} | `{first}` |")
    return "\n".join(lines)


def secret_capture(w: WorkspaceClient) -> str:
    """Metadata and grants of the AESO key secret. The value is never requested (no include_value)."""
    name = f"{FQ}.aeso_api_key"
    meta = w.api_client.do("GET", f"/api/2.1/unity-catalog/secrets/{name}")
    grants = w.api_client.do("GET", f"/api/2.1/unity-catalog/permissions/secret/{name}").get("privilege_assignments", [])
    lines = [f"Secret `{name}`: type `{meta.get('securable_kind')}`, owner `<user>`, comment: {meta.get('comment')!r}", "",
             "| Principal | Privileges |", "|---|---|"]
    lines += [f"| `{g['principal']}` (app service principal) | {', '.join(g['privileges'])} |" for g in grants]
    return "\n".join(lines)


def notebook_text(w: WorkspaceClient, task_run_id: int) -> str:
    """All text output of a notebook task run, cell by cell."""
    export = w.jobs.export_run(task_run_id, views_to_export=ViewsToExport.CODE)
    html = export.views[0].content
    model = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html).group(1)
    nb = json.loads(urllib.parse.unquote(base64.b64decode(model).decode()))
    parts = []
    for cmd in nb.get("commands", []):
        res = cmd.get("results") or {}
        data = res.get("data")
        texts = []
        if isinstance(data, str):
            texts.append(data)
        elif isinstance(data, list):
            texts += [str(d.get("data", "")) for d in data if d.get("type") in (None, "ansi", "text", "html") and isinstance(d.get("data"), str)]
        if res.get("type") == "table" and isinstance(data, list):
            texts = ["\t".join(map(str, row)) for row in data[:30]]
        text = ANSI.sub("", "\n".join(t for t in texts if t and not t.lstrip().startswith("<")))
        text = "\n".join(line for line in text.splitlines() if not NOISE.search(line)).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def latest_success(w: WorkspaceClient, job_name: str):
    job = next(j for j in w.jobs.list(name=job_name))
    for run in w.jobs.list_runs(job_id=job.job_id, completed_only=True, limit=10):
        if run.state and str(run.state.result_state).endswith("SUCCESS"):
            return w.jobs.get_run(run.run_id)
    raise RuntimeError(f"No successful run for {job_name}")


def query(w: WorkspaceClient, warehouse_id: str, sql: str) -> str:
    resp = w.statement_execution.execute_statement(statement=sql, warehouse_id=warehouse_id, wait_timeout="50s")
    while resp.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state.value != "SUCCEEDED":
        return f"(query failed: {resp.status.error.message if resp.status.error else resp.status.state})"
    cols = [c.name for c in resp.manifest.schema.columns]
    rows = (resp.result.data_array if resp.result else None) or []
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows[:60]]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="fevm-energy-canada")
    ap.add_argument("--warehouse-id", default="fd18e0ef46eba09f")
    ap.add_argument("--only", nargs="*", help="curated file names to rebuild")
    args = ap.parse_args()
    w = WorkspaceClient(profile=args.profile)
    (EVIDENCE / "raw").mkdir(parents=True, exist_ok=True)
    runs = {}
    for name, (title, tasks, queries) in SECTIONS.items():
        if args.only and name not in args.only:
            continue
        body = [f"# {title}", "", f"Exported {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `scripts/export_evidence.py` "
                "from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.", ""]
        for job_name, task_key in tasks:
            run = runs.setdefault(job_name, latest_success(w, job_name))
            task = next(t for t in run.tasks if t.task_key == task_key)
            secs = (task.end_time - task.start_time) // 1000 if task.end_time and task.start_time else None
            text = redact(notebook_text(w, task.run_id))
            raw_name = f"{job_name}__{task_key}.md"
            (EVIDENCE / "raw" / raw_name).write_text(
                f"# {job_name} / {task_key}\n\njob run {run.run_id}, task run {task.run_id}, "
                f"{task.state.result_state.value}, {secs}s\n\n```text\n{text}\n```\n")
            body += [f"## Task `{task_key}` (job `{job_name}`)", "",
                     f"Job run `{run.run_id}` · task run `{task.run_id}` · **{task.state.result_state.value}** · {secs}s "
                     f"· full output `evidence/raw/{raw_name}` (local)", "", "```text", text[:3400], "```", ""]
        for label, sql in queries:
            body += [f"## Query: {label}", "", redact(query(w, args.warehouse_id, sql)), ""]
        if name == "02_pipeline_governance.md":
            body += ["## UC secret governance (REST, value never read)", "", secret_capture(w), ""]
        if name == "04_lakebase_app.md":
            body += ["## Deployed app API (what the 9 cards and the ops form render)", "", redact(app_capture(w)), ""]
        doc = "\n".join(body)
        (EVIDENCE / name).write_text(doc[:MAX_CHARS] + ("\n\n(truncated; full output in evidence/raw/ after a local export)\n" if len(doc) > MAX_CHARS else ""))
        print(f"wrote evidence/{name} ({min(len(doc), MAX_CHARS)} chars)")


if __name__ == "__main__":
    main()
