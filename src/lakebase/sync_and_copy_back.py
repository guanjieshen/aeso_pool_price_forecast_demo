# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase: refresh synced tables, copy ops actions back to Delta
# MAGIC 1. Refreshes the snapshot synced tables (forecast + pool price) that serve the app's live cards.
# MAGIC 2. Copies `ops.ops_actions` (spike alerts and load shifts written by the app) into the Delta table
# MAGIC    `ops_actions_history`, so Genie and analysts can join decisions to prices.

# COMMAND ----------

# MAGIC %pip install -q "databricks-sdk>=0.60" "psycopg[binary]>=3.2"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("lakebase_endpoint", "projects/aeso-market-pulse/branches/production/endpoints/primary")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
ENDPOINT = dbutils.widgets.get("lakebase_endpoint")
FQ = f"{CATALOG}.{SCHEMA}"
SYNCED = ["forecast_latest_synced", "pool_price_hourly_synced"]
spark.conf.set("spark.sql.session.timeZone", "UTC")

import time
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# COMMAND ----------

updates = {}
for name in SYNCED:
    pipeline_id = w.postgres.get_synced_table(f"synced_tables/{FQ}.{name}").status.pipeline_id
    updates[name] = (pipeline_id, w.pipelines.start_update(pipeline_id).update_id)
for name, (pipeline_id, update_id) in updates.items():
    for _ in range(120):   # up to 20 minutes
        state = w.pipelines.get_update(pipeline_id, update_id).update.state.value
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            break
        time.sleep(10)
    print(f"{name}: refresh {state}")
    assert state == "COMPLETED", f"synced table {name} refresh ended {state}"

# COMMAND ----------

import psycopg
import pandas as pd

host = w.postgres.get_endpoint(ENDPOINT).status.hosts.host
token = w.postgres.generate_database_credential(endpoint=ENDPOINT).token
with psycopg.connect(host=host, dbname="databricks_postgres", user=w.current_user.me().user_name,
                     password=token, sslmode="require") as conn:
    conn.execute("SET TIME ZONE 'UTC'")
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{t}").fetchone()[0] for t in SYNCED}
    exists = conn.execute("SELECT to_regclass('ops.ops_actions') IS NOT NULL").fetchone()[0]
    actions = pd.read_sql("SELECT * FROM ops.ops_actions ORDER BY action_id", conn) if exists else pd.DataFrame()

delta_counts = {"forecast_latest_synced": spark.table(f"{FQ}.aeso_price_forecast_output").count(),
                "pool_price_hourly_synced": spark.table(f"{FQ}.silver_pool_price_hourly").count()}
for t in SYNCED:
    print(f"{t}: Lakebase rows {counts[t]} | Delta source rows {delta_counts[t]} | match {counts[t] == delta_counts[t]}")

# COMMAND ----------

if len(actions):
    actions["created_at"] = pd.to_datetime(actions["created_at"], utc=True).dt.tz_localize(None)
    (spark.createDataFrame(actions).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{FQ}.ops_actions_history"))
    spark.sql(f"COMMENT ON TABLE {FQ}.ops_actions_history IS 'Copy of Lakebase ops.ops_actions: spike alerts and load shifts logged in AESO Market Pulse. window_*_mpt are Mountain Time wall clock.'")
    print(f"Copied {len(actions)} ops actions to {FQ}.ops_actions_history:")
    print(actions.drop(columns=["created_by"]).tail(10).to_string(index=False))
else:
    print("No ops actions yet; nothing to copy.")
