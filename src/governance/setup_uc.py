# Databricks notebook source
# MAGIC %md
# MAGIC # Unity Catalog governance
# MAGIC Idempotent: tags every table with **governed tags** from the metastore's tag policies (`domain`, `layer`,
# MAGIC `classification`, `data_product`) plus free-form `subject_area` and `data_source`, comments the schema
# MAGIC and the AESO key secret, grants the app's service principal read access, and prints what is in place.
# MAGIC Runs as the last task of the hourly job, so tables created by later phases are governed automatically.

# COMMAND ----------

dbutils.widgets.text("catalog", "energy_canada_demos_catalog")
dbutils.widgets.text("schema", "aeso_price_forecast")
dbutils.widgets.text("app_service_principal", "")  # filled once the app exists (phase 3)
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
APP_SP = dbutils.widgets.get("app_service_principal").strip()
FQ = f"{CATALOG}.{SCHEMA}"

# COMMAND ----------

# Table -> (layer, data_product, data_source). layer and data_product are governed tags (allowed values are
# enforced by tag policies). Tables that do not exist yet are skipped and governed on a later run.
TABLES = {
    "aeso_pool_price": ("bronze", "data_engineering", "aeso_api_public"),
    "aeso_wind_solar_forecast": ("bronze", "data_engineering", "aeso_csv_public"),
    "aeso_wind_solar_metered": ("bronze", "data_engineering", "aeso_api_public"),
    "silver_pool_price_hourly": ("silver", "data_engineering", "derived"),
    "silver_wind_solar_hourly": ("silver", "data_engineering", "derived"),
    "gold_price_features_hourly": ("gold", "analytics", "derived"),
    "aeso_price_forecast_output": ("gold", "machine_learning", "model_output"),
    "aeso_backtest_metrics": ("gold", "machine_learning", "model_output"),
    "aeso_backtest_detail": ("gold", "machine_learning", "model_output"),
    "aeso_business_value": ("gold", "analytics", "model_output"),
    "ops_actions_history": ("gold", "analytics", "app_write_back"),
}
existing = {r.tableName: r for r in spark.sql(f"SHOW TABLES IN {FQ}").collect()}

spark.sql(f"COMMENT ON SCHEMA {FQ} IS 'AESO pool price forecast for Enbridge Liquids Pipelines power cost. Public AESO data only. Prices CAD/MWh, times Mountain Time, AESO hour-ending.'")
spark.sql(f"ALTER SCHEMA {FQ} SET TAGS ('domain' = 'operations', 'classification' = 'public', 'subject_area' = 'power_market')")

for table, (layer, product, source) in TABLES.items():
    if table not in existing:
        print(f"skip (not created yet): {table}")
        continue
    kind = spark.sql(f"DESCRIBE TABLE EXTENDED {FQ}.{table}").filter("col_name = 'Type'").first()
    keyword = "MATERIALIZED VIEW" if kind and "MATERIALIZED" in kind.data_type.upper() else "TABLE"
    spark.sql(f"ALTER {keyword} {FQ}.{table} SET TAGS ('domain' = 'operations', 'layer' = '{layer}', "
              f"'classification' = 'public', 'data_product' = '{product}', 'subject_area' = 'power_market', "
              f"'data_source' = '{source}')")
    print(f"tagged {keyword.lower()}: {table} layer={layer} data_product={product} source={source}")

# Secret DDL is not enabled in Spark SQL on this workspace, so the secret is governed through the UC REST API.
# The API never returns the value unless include_value=true is asked for; this notebook never asks.
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
SECRET = f"{FQ}.aeso_api_key"
w.api_client.do("PATCH", f"/api/2.1/unity-catalog/secrets/{SECRET}", query={"update_mask": "comment"},
                body={"comment": "AESO API gateway key. Read by the ingest notebooks via dbutils.secrets; READ also granted to the AESO Market Pulse app service principal."})

# COMMAND ----------

# Least privilege for the app: read the tables it shows (secret READ is granted by scripts/grant_app_sp.py).
if APP_SP:
    spark.sql(f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{APP_SP}`")
    spark.sql(f"GRANT USE SCHEMA ON SCHEMA {FQ} TO `{APP_SP}`")
    for table in TABLES:
        if table in existing:
            spark.sql(f"GRANT SELECT ON TABLE {FQ}.{table} TO `{APP_SP}`")
    print(f"granted read on {sum(t in existing for t in TABLES)} tables to app SP {APP_SP}")

# COMMAND ----------

# MAGIC %md ## What is in place

# COMMAND ----------

print(spark.sql(f"""
SELECT table_name, tag_name, tag_value FROM {CATALOG}.information_schema.table_tags
WHERE schema_name = '{SCHEMA}' AND tag_name = 'layer' ORDER BY table_name""").toPandas().to_string(index=False))
print(spark.sql(f"SHOW GRANTS ON SCHEMA {FQ}").toPandas().to_string(index=False))
meta = w.api_client.do("GET", f"/api/2.1/unity-catalog/secrets/{SECRET}")
grants = w.api_client.do("GET", f"/api/2.1/unity-catalog/permissions/secret/{SECRET}").get("privilege_assignments", [])
print(f"Secret {SECRET}: owner={meta.get('effective_owner')} (READ via ownership; the jobs run as the owner), "
      f"comment={meta.get('comment')!r}")
print("Explicit secret grants: " + (", ".join(f"{g['principal']}: {g['privileges']}" for g in grants) or
      "none"))
