# Declarative pipeline (silver/gold, expectations) and Unity Catalog governance

Exported 2026-11-23 19:23 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `governance` (job `aeso-hourly`)

Job run `362081059053813` · task run `488948664773368` · **SUCCESS** · 30s · full output `evidence/raw/aeso-hourly__governance.md` (local)

```text
tagged table: aeso_pool_price layer=bronze data_product=data_engineering source=aeso_api_public
tagged table: aeso_wind_solar_forecast layer=bronze data_product=data_engineering source=aeso_csv_public
tagged table: aeso_wind_solar_metered layer=bronze data_product=data_engineering source=aeso_api_public
tagged table: aeso_supply_demand_hourly layer=bronze data_product=data_engineering source=aeso_api_public
tagged table: aeso_wind_solar_published layer=bronze data_product=data_engineering source=aeso_csv_public
tagged table: aeso_fundamentals_snapshots layer=bronze data_product=data_engineering source=aeso_api_public
tagged materialized view: silver_supply_demand_hourly layer=silver data_product=data_engineering source=derived
skip (not created yet): aeso_price_drivers
tagged materialized view: silver_pool_price_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: silver_wind_solar_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: gold_price_features_hourly layer=gold data_product=analytics source=derived
tagged table: aeso_price_forecast_output layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_metrics layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_detail layer=gold data_product=machine_learning source=model_output
tagged table: aeso_business_value layer=gold data_product=analytics source=model_output
tagged table: ops_actions_history layer=gold data_product=analytics source=app_write_back
tagged table: aeso_forecast_history layer=gold data_product=machine_learning source=model_output
tagged table: aeso_model_promotions layer=gold data_product=machine_learning source=model_lifecycle
skip (not created yet): aeso_live_accuracy

table_name tag_name tag_value
       aeso_backtest_detail    layer      gold
      aeso_backtest_metrics    layer      gold
        aeso_business_value    layer      gold
      aeso_forecast_history    layer      gold
aeso_fundamentals_snapshots    layer    bronze
      aeso_model_promotions    layer      gold
            aeso_pool_price    layer    bronze
 aeso_price_forecast_output    layer      gold
  aeso_supply_demand_hourly    layer    bronze
   aeso_wind_solar_forecast    layer    bronze
    aeso_wind_solar_metered    layer    bronze
  aeso_wind_solar_published    layer    bronze
 gold_price_features_hourly    layer      gold
        ops_actions_history    layer      gold
   silver_pool_price_hourly    layer    silver
silver_supply_demand_hourly    layer    silver
   silver_wind_solar_hourly    layer    silver
                           Principal          ActionType ObjectType                                       ObjectKey
695a6514-643a-49d4-b236-17c163ced289      ALL PRIVILEGES    CATALOG                     energy_canada_demos_catalog
    <user>      ALL PRIVILEGES    CATALOG                     energy_canada_demos_catalog
    <user>              MANAGE    CATALOG                     energy_canada_demos_catalog
ce289c66-8347-4eea-a427-6b4f20fe6b76          USE SCHEMA     SCHEMA energy_canada_demos_catalog.aeso_price_forecast
                    energy-canada-sa              MANAGE    CATALOG                     energy_canada_demos_catalog
                    energy-canada-sa              MODIFY    CATALOG                     energy_canada_demos_catal
```

## Query: Wind/solar regressor source (how much is imputed)

| regressor_source | hours |
|---|---|
| metered | 7760 |
| csv_forecast | 168 |
| csv_actual | 75 |
| imputed | 1 |

## Query: Gold features

| rows | settled | first_mpt | last_mpt | imputed_hours |
|---|---|---|---|---|
| 8004 | 7835 | 2026-01-01T00:00:00.000Z | 2026-11-30T11:00:00.000Z | 1 |

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
| aeso_forecast_history | data_product | machine_learning |
| aeso_forecast_history | domain | operations |
| aeso_forecast_history | layer | gold |
| aeso_fundamentals_snapshots | data_product | data_engineering |
| aeso_fundamentals_snapshots | domain | operations |
| aeso_fundamentals_snapshots | layer | bronze |
| aeso_model_promotions | data_product | machine_learning |
| aeso_model_promotions | domain | operations |
| aeso_model_promotions | layer | gold |
| aeso_pool_price | data_product | data_engineering |
| aeso_pool_price | domain | operations |
| aeso_pool_price | layer | bronze |
| aeso_price_forecast_output | data_product | machine_learning |
| aeso_price_forecast_output | domain | operations |
| aeso_price_forecast_output | layer | gold |
| aeso_supply_demand_hourly | data_product | data_engineering |
| aeso_supply_demand_hourly | domain | operations |
| aeso_supply_demand_hourly | layer | bronze |
| aeso_wind_solar_forecast | data_product | data_engineering |
| aeso_wind_solar_forecast | domain | operations |
| aeso_wind_solar_forecast | layer | bronze |
| aeso_wind_solar_metered | data_product | data_engineering |
| aeso_wind_solar_metered | domain | operations |
| aeso_wind_solar_metered | layer | bronze |
| aeso_wind_solar_published | data_product | data_engineering |
| aeso_wind_solar_published | domain | operations |
| aeso_wind_solar_published | layer | bronze |
| gold_price_features_hourly | data_product | analytics |
| gold_price_features_hourly | domain | operations |
| gold_price_features_hourly | layer | gold |
| ops_actions_history | data_product | analytics |
| ops_actions_history | domain | operations |
| ops_actions_history | layer | gold |
| silver_pool_price_hourly | data_product | data_engineering |
| silver_pool_price_hourly | domain | operations |
| silver_pool_price_hourly | layer | silver |
| silver_supply_demand_hourly | data_product | data_engineering |
| silver_supply_demand_hourly | domain | operations |
| silver_supply_demand_hourly | layer | silver |
| silver_wind_solar_hourly | data_product | data_engineering |
| silver_wind_solar_hourly | domain | operations |
| silver_wind_solar_hourly | layer | silver |

## Query: Lineage: what reads the gold table

| source_table_full_name | target_table_full_name | entity_type |
|---|---|---|
| energy_canada_demos_catalog.aeso_price_forecast.aeso_fundamentals_snapshots | energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_pool_price | energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_pool_price | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_price_forecast_output | energy_canada_demos_catalog.aeso_price_forecast.forecast_latest_synced | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_supply_demand_hourly | energy_canada_demos_catalog.aeso_price_forecast.aeso_fundamentals_snapshots | JOB |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_supply_demand_hourly | energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_forecast | energy_canada_demos_catalog.aeso_price_forecast.aeso_fundamentals_snapshots | JOB |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_forecast | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_metered | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_published | energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | PIPELINE |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly |

(truncated; full output in evidence/raw/ after a local export)
