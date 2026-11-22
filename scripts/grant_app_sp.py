"""Grant the AESO Market Pulse app's service principal exactly what it reads and writes. Run after deploy.

Unity Catalog (on the SQL warehouse): USE CATALOG, USE SCHEMA, SELECT on each table the app queries.
UC secret: READ SECRET on the AESO key (owner decision, see docs/decisions.md #5).
Lakebase (Postgres): read the synced tables, read/write ops.ops_actions.

Usage: uv run --with databricks-sdk --with "psycopg[binary]" python scripts/grant_app_sp.py [--profile ...]
"""
import argparse
import time

import psycopg
from databricks.sdk import WorkspaceClient

APP_TABLES = ["aeso_pool_price", "silver_wind_solar_hourly", "aeso_price_forecast_output",
              "aeso_backtest_metrics", "aeso_backtest_detail"]
ENDPOINT = "projects/aeso-market-pulse/branches/production/endpoints/primary"


def run_sql(w: WorkspaceClient, warehouse_id: str, statement: str) -> None:
    resp = w.statement_execution.execute_statement(statement=statement, warehouse_id=warehouse_id, wait_timeout="50s")
    while resp.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state.value != "SUCCEEDED":
        raise RuntimeError(f"{statement}: {resp.status.error.message if resp.status.error else resp.status.state}")
    print(f"ok  {statement}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="fevm-energy-canada")
    ap.add_argument("--app", default="aeso-market-pulse")
    ap.add_argument("--catalog", default="energy_canada_demos_catalog")
    ap.add_argument("--schema", default="aeso_price_forecast")
    ap.add_argument("--warehouse-id", default="fd18e0ef46eba09f")
    args = ap.parse_args()
    w = WorkspaceClient(profile=args.profile)
    app = w.apps.get(args.app)
    sp_name, sp_role = app.service_principal_name, app.service_principal_client_id
    print(f"App {args.app}: service principal {sp_name} ({sp_role})")

    fq = f"{args.catalog}.{args.schema}"
    catalog_grant = f"GRANT USE CATALOG ON CATALOG {args.catalog} TO `{sp_role}`"
    try:
        run_sql(w, args.warehouse_id, catalog_grant)
    except RuntimeError:   # a shared catalog: only its admins (MANAGE) can grant; check it is inherited instead
        held = w.statement_execution.execute_statement(
            statement=f"SHOW GRANTS `{sp_role}` ON CATALOG {args.catalog}", warehouse_id=args.warehouse_id,
            wait_timeout="50s").result.data_array or []
        via = sorted({row[0] for row in held if row[1] == "USE CATALOG"})
        if not via:
            raise SystemExit(f"Ask a catalog admin to run: {catalog_grant}")
        print(f"ok  USE CATALOG already held via {', '.join(via)} (cannot grant directly: no MANAGE on the catalog)")
    run_sql(w, args.warehouse_id, f"GRANT USE SCHEMA ON SCHEMA {fq} TO `{sp_role}`")
    for table in APP_TABLES:
        run_sql(w, args.warehouse_id, f"GRANT SELECT ON TABLE {fq}.{table} TO `{sp_role}`")

    secret = f"{fq}.aeso_api_key"
    w.api_client.do("PATCH", f"/api/2.1/unity-catalog/permissions/secret/{secret}",
                    body={"changes": [{"principal": sp_role, "add": ["READ_SECRET"]}]})
    print(f"ok  READ SECRET on {secret} to {sp_role}")

    host = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
    token = w.postgres.generate_database_credential(endpoint=ENDPOINT).token
    with psycopg.connect(host=host, dbname="databricks_postgres", user=w.current_user.me().user_name,
                         password=token, sslmode="require", autocommit=True) as conn:
        for stmt in [
            f'GRANT USAGE ON SCHEMA {args.schema} TO "{sp_role}"',
            f'GRANT SELECT ON ALL TABLES IN SCHEMA {args.schema} TO "{sp_role}"',
            "CREATE SCHEMA IF NOT EXISTS ops",
            f'GRANT USAGE ON SCHEMA ops TO "{sp_role}"',
            "CREATE TABLE IF NOT EXISTS ops.ops_actions (action_id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "created_by TEXT, action_type TEXT NOT NULL CHECK (action_type IN ('spike_alert', 'load_shift')), "
            "window_start_mpt TIMESTAMP NOT NULL, window_end_mpt TIMESTAMP NOT NULL, mw DOUBLE PRECISION, "
            "threshold DOUBLE PRECISION, note TEXT)",
            f'GRANT SELECT, INSERT ON ops.ops_actions TO "{sp_role}"',
            f'GRANT USAGE ON SEQUENCE ops.ops_actions_action_id_seq TO "{sp_role}"',
        ]:
            conn.execute(stmt)
            print(f"ok  (postgres) {stmt[:90]}")


if __name__ == "__main__":
    main()
