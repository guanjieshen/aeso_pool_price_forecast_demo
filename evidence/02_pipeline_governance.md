# Declarative pipeline (silver/gold, expectations) and Unity Catalog governance

Exported 2026-11-22 19:13 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `governance` (job `aeso-hourly`)

Job run `683048180465385` · task run `588131077961485` · **SUCCESS** · 30s · full output `evidence/raw/aeso-hourly__governance.md` (local)

```text
tagged table: aeso_pool_price layer=bronze data_product=data_engineering source=aeso_api_public
tagged table: aeso_wind_solar_forecast layer=bronze data_product=data_engineering source=aeso_csv_public
tagged table: aeso_wind_solar_metered layer=bronze data_product=data_engineering source=aeso_api_public
tagged materialized view: silver_pool_price_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: silver_wind_solar_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: gold_price_features_hourly layer=gold data_product=analytics source=derived
tagged table: aeso_price_forecast_output layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_metrics layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_detail layer=gold data_product=machine_learning source=model_output
tagged table: aeso_business_value layer=gold data_product=analytics source=model_output
tagged table: ops_actions_history layer=gold data_product=analytics source=app_write_back

table_name tag_name tag_value
      aeso_backtest_detail    layer      gold
     aeso_backtest_metrics    layer      gold
       aeso_business_value    layer      gold
           aeso_pool_price    layer    bronze
aeso_price_forecast_output    layer      gold
  aeso_wind_solar_forecast    layer    bronze
   aeso_wind_solar_metered    layer    bronze
gold_price_features_hourly    layer      gold
       ops_actions_history    layer      gold
  silver_pool_price_hourly    layer    silver
  silver_wind_solar_hourly    layer    silver
                           Principal          ActionType ObjectType                                       ObjectKey
695a6514-643a-49d4-b236-17c163ced289      ALL PRIVILEGES    CATALOG                     energy_canada_demos_catalog
    <user>      ALL PRIVILEGES    CATALOG                     energy_canada_demos_catalog
    <user>              MANAGE    CATALOG                     energy_canada_demos_catalog
ce289c66-8347-4eea-a427-6b4f20fe6b76          USE SCHEMA     SCHEMA energy_canada_demos_catalog.aeso_price_forecast
                    energy-canada-sa              MANAGE    CATALOG                     energy_canada_demos_catalog
                    energy-canada-sa              MODIFY    CATALOG                     energy_canada_demos_catalog
                    energy-canada-sa              SELECT    CATALOG                     energy_canada_demos_catalog
                    energy-canada-sa          USE SCHEMA    CATALOG                     energy_canada_demos_catalog
              field-energy-canada-ae              SELECT    CATALOG                     energy_canada_demos_catalog
              field-energy-canada-ae          USE SCHEMA    CATALOG                     energy_canada_demos_catalog
              field-energy-canada-sa      ALL PRIVILEGES    CATALOG                     energy_canada_demos_catalog
              field-energy-canada-sa              SELECT    CATALOG                     energy_canada_demos_catalog
              field-energy-canada-sa          USE SCHEMA    CATALOG                     energy_canada_demos_catalog
                          canada-dsa       CREATE VOLUME    CATALOG                     energy_canada_demos_catalog
                          canada-dsa              MODIFY    CATALOG          
```

## Query: Wind/solar regressor source (how much is imputed)

| regressor_source | hours |
|---|---|
| metered | 7751 |
| csv_forecast | 168 |
| csv_actual | 51 |
| imputed | 10 |

## Query: Gold features

| rows | settled | first_mpt | last_mpt | imputed_hours |
|---|---|---|---|---|
| 7980 | 7812 | 2026-01-01T00:00:00.000Z | 2026-11-29T11:00:00.000Z | 10 |

## Query: Governed tags per table

| table_name | tag_name | tag_value |
|---|---|---|
| aeso_backtest_detail | data_product | machine_learning |
| aeso_backtest_detail | domain | operations |
| aeso_backtest_detail | layer | gold |
| aeso_backtest_metrics | data_product | machine_learning |
| aeso_backtest_metrics | domain | operations |
| aeso_backtest_metrics | layer | gold |
| aeso_business_value | data_product | analytics |
| aeso_business_value | domain | operations |
| aeso_business_value | layer | gold |
| aeso_pool_price | data_product | data_engineering |
| aeso_pool_price | domain | operations |
| aeso_pool_price | layer | bronze |
| aeso_price_forecast_output | data_product | machine_learning |
| aeso_price_forecast_output | domain | operations |
| aeso_price_forecast_output | layer | gold |
| aeso_wind_solar_forecast | data_product | data_engineering |
| aeso_wind_solar_forecast | domain | operations |
| aeso_wind_solar_forecast | layer | bronze |
| aeso_wind_solar_metered | data_product | data_engineering |
| aeso_wind_solar_metered | domain | operations |
| aeso_wind_solar_metered | layer | bronze |
| gold_price_features_hourly | data_product | analytics |
| gold_price_features_hourly | domain | operations |
| gold_price_features_hourly | layer | gold |
| ops_actions_history | data_product | analytics |
| ops_actions_history | domain | operations |
| ops_actions_history | layer | gold |
| silver_pool_price_hourly | data_product | data_engineering |
| silver_pool_price_hourly | domain | operations |
| silver_pool_price_hourly | layer | silver |
| silver_wind_solar_hourly | data_product | data_engineering |
| silver_wind_solar_hourly | domain | operations |
| silver_wind_solar_hourly | layer | silver |

## Query: Lineage: what reads the gold table

| source_table_full_name | target_table_full_name | entity_type |
|---|---|---|
| energy_canada_demos_catalog.aeso_price_forecast.aeso_pool_price | energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_pool_price | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_price_forecast_output | energy_canada_demos_catalog.aeso_price_forecast.forecast_latest_synced | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_forecast | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_metered | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | energy_canada_demos_catalog.aeso_price_forecast.pool_price_hourly_synced | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | PIPELINE |

## UC secret governance (REST, value never read)

Secret `energy_canada_demos_catalog.aeso_price_forecast.aeso_api_key`: type `SECRET_STANDARD`, owner `<user>`, comment: 'AESO API gateway key. Read by the ingest notebooks via dbutils.secrets; READ also granted to the AESO Market Pulse app service principal.'

| Principal | Privileges |
|---|---|
| `ce289c66-8347-4eea-a427-6b4f20fe6b76` (app service principal) | READ_SECRET |
