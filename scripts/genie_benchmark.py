"""Score the AESO Market Pulse Genie space against ground truth and write evidence/05_genie_benchmark.md.

Each question has a ground-truth SQL query. A question passes when every expected value appears in Genie's
result (numbers within 1%, or text found). The report shows Genie's SQL so a reviewer can judge it.

Usage: uv run --with databricks-sdk python scripts/genie_benchmark.py [--profile fevm-energy-canada]
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient

FQ = "energy_canada_demos_catalog.aeso_price_forecast"
OUT = Path(__file__).resolve().parents[1] / "evidence" / "05_genie_benchmark.md"

QUESTIONS = [
    ("What was the average settled pool price in October 2026?",
     f"SELECT ROUND(AVG(pool_price), 2) FROM {FQ}.aeso_pool_price WHERE pool_price IS NOT NULL AND begin_datetime_mpt >= '2026-10-01' AND begin_datetime_mpt < '2026-11-01'"),
    ("What was the highest pool price so far in 2026?",
     f"SELECT MAX(pool_price) FROM {FQ}.aeso_pool_price WHERE YEAR(begin_datetime_mpt) = 2026"),
    ("How many hours in 2026 settled above $150/MWh?",
     f"SELECT COUNT(*) FROM {FQ}.aeso_pool_price WHERE pool_price > 150 AND YEAR(begin_datetime_mpt) = 2026"),
    ("Which model (not a baseline) had the lowest MAE in the latest backtest, and what was its MAE?",
     f"SELECT model_name, ROUND(mae_cad_mwh, 2) FROM {FQ}.aeso_backtest_metrics WHERE model_type = 'model' AND run_timestamp = (SELECT MAX(run_timestamp) FROM {FQ}.aeso_backtest_metrics) ORDER BY mae_cad_mwh LIMIT 1"),
    ("What is the average ensemble forecast price over the next 24 hours?",
     f"SELECT ROUND(AVG(ensemble_forecast_price), 2) FROM {FQ}.aeso_price_forecast_output"),
    ("Which hour-ending had the highest average pool price over the last 90 days?",
     f"SELECT HOUR(begin_datetime_mpt) + 1 FROM {FQ}.aeso_pool_price WHERE pool_price IS NOT NULL AND begin_datetime_mpt >= (SELECT MAX(begin_datetime_mpt) FROM {FQ}.aeso_pool_price) - INTERVAL 90 DAYS GROUP BY 1 ORDER BY AVG(pool_price) DESC LIMIT 1"),
    ("What was the average pool price in 2026 in hours when actual wind and solar generation was above 3,000 MW?",
     f"SELECT ROUND(AVG(p.pool_price), 2) FROM {FQ}.aeso_pool_price p JOIN {FQ}.silver_wind_solar_hourly w ON p.begin_datetime_mpt = w.forecast_transaction_date WHERE p.pool_price IS NOT NULL AND w.actual_mw > 3000 AND YEAR(p.begin_datetime_mpt) = 2026"),
    ("How many spike alerts have operators logged?",
     f"SELECT COUNT(*) FROM {FQ}.ops_actions_history WHERE action_type = 'spike_alert'"),
]


def sql_values(w: WorkspaceClient, wh: str, sql: str) -> list[str]:
    r = w.statement_execution.execute_statement(statement=sql, warehouse_id=wh, wait_timeout="50s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    return [v for v in (r.result.data_array or [[]])[0] if v is not None]


def matches(expected: str, cells: list[str], text: str) -> bool:
    try:
        target = float(expected)
    except ValueError:
        return expected.lower() in (" ".join(cells) + " " + text).lower()
    nums = [float(x) for c in cells + [text] for x in re.findall(r"-?\d+(?:\.\d+)?", str(c).replace(",", ""))]
    return any(abs(n - target) <= max(0.01 * abs(target), 0.05) for n in nums)


def ask(w: WorkspaceClient, space_id: str, question: str) -> tuple[str, list[str], str]:
    """Returns (Genie's SQL, flattened result cells, Genie's text)."""
    msg = w.genie.start_conversation_and_wait(space_id, question)
    sql, cells, text = "", [], ""
    for att in msg.attachments or []:
        if att.text and att.text.content:
            text += att.text.content + " "
        if att.query:
            sql = att.query.query or ""
            res = w.genie.get_message_attachment_query_result(space_id, msg.conversation_id, msg.message_id, att.attachment_id)
            rows = res.statement_response.result.data_array if res.statement_response and res.statement_response.result else []
            cells = [str(v) for row in (rows or [])[:50] for v in row if v is not None]
    return sql, cells, text.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="fevm-energy-canada")
    ap.add_argument("--warehouse-id", default="fd18e0ef46eba09f")
    ap.add_argument("--space-id", default="01f1e6a1b931196f80593b589abbc529")
    args = ap.parse_args()
    w = WorkspaceClient(profile=args.profile)
    results = []
    for q, truth_sql in QUESTIONS:
        expected = sql_values(w, args.warehouse_id, truth_sql)
        sql, cells, text = ask(w, args.space_id, q)
        ok = bool(expected) and all(matches(e, cells, text) for e in expected)
        results.append((q, expected, ok, sql, cells[:6], text))
        print(f"{'PASS' if ok else 'FAIL'}  {q}  expected={expected} genie={cells[:4]}")
    score = sum(r[2] for r in results)
    lines = [f"# Genie benchmark: {score}/{len(results)} correct", "",
             f"Space `{args.space_id}` (AESO Market Pulse Genie), run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} "
             "by `scripts/genie_benchmark.py`. Ground truth comes from SQL written by hand; a question passes when every "
             "expected value appears in Genie's result (numbers within 1%).", "",
             "| # | Question | Expected | Genie returned | Result |", "|---|---|---|---|---|"]
    for i, (q, exp, ok, _, cells, _) in enumerate(results, 1):
        lines.append(f"| {i} | {q} | {', '.join(exp)} | {', '.join(cells) or '(no table)'} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", "## SQL Genie generated", ""]
    for i, (q, _, _, sql, _, text) in enumerate(results, 1):
        lines += [f"**{i}. {q}**", "", "```sql", (sql or "(no SQL)").strip()[:700], "```", ""]
    OUT.write_text("\n".join(lines)[:8800])
    print(f"wrote {OUT} ({score}/{len(results)})")


if __name__ == "__main__":
    main()
