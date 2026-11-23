# Declarative pipeline (silver/gold, expectations) and Unity Catalog governance

Exported 2026-11-23 23:24 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `governance` (job `aeso-hourly`)

Job run `398610988453239` · task run `276345202863885` · **SUCCESS** · 44s · full output `evidence/raw/aeso-hourly__governance.md` (local)

```text
tagged streaming table: bronze_pool_price layer=bronze data_product=data_engineering source=aeso_api_public
tagged streaming table: bronze_wind_solar_forecast layer=bronze data_product=data_engineering source=aeso_csv_public
tagged streaming table: bronze_wind_solar_metered layer=bronze data_product=data_engineering source=aeso_api_public
tagged streaming table: bronze_load layer=bronze data_product=data_engineering source=aeso_api_public
tagged streaming table: bronze_gen_capacity layer=bronze data_product=data_engineering source=aeso_api_public
tagged streaming table: bronze_intertie layer=bronze data_product=data_engineering source=aeso_api_public
tagged streaming table: bronze_wind_solar_published layer=bronze data_product=data_engineering source=aeso_csv_public
tagged streaming table: bronze_outage_outlook layer=bronze data_product=data_engineering source=aeso_report_public
tagged materialized view: aeso_pool_price layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_wind_solar_forecast layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_wind_solar_metered layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_supply_demand_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_wind_solar_published layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_fundamentals_snapshots layer=silver data_product=data_engineering source=derived
tagged materialized view: aeso_outage_outlook layer=silver data_product=data_engineering source=derived
tagged materialized view: silver_pool_price_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: silver_wind_solar_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: silver_supply_demand_hourly layer=silver data_product=data_engineering source=derived
tagged materialized view: gold_price_features_hourly layer=gold data_product=analytics source=derived
tagged table: aeso_price_forecast_output layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_metrics layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_detail layer=gold data_product=machine_learning source=model_output
tagged table: aeso_backtest_windows layer=gold data_product=machine_learning source=model_output
tagged table: aeso_business_value layer=gold data_product=analytics source=model_output
tagged table: aeso_price_drivers layer=gold data_product=analytics source=derived
tagged table: ops_actions_history layer=gold data_product=analytics source=app_write_back
tagged table: aeso_forecast_history layer=gold data_product=machine_learning source=model_output
tagged table: aeso_model_promotions layer=gold data_product=machine_learning source=model_lifecycle
skip (not created yet): aeso_live_accuracy

table_name tag_name tag_value
       aeso_backtest_detail    layer      gold
      aeso_backtest_metrics    layer      gold
      aeso_backtest_windows    layer      gold
        aeso_business_value    layer      gold
      aeso_forecast_history    layer      gold
aeso_fundamentals_snapshots    layer    silver
      aeso_model_promotions    layer      gold
        aeso_outage_outlook    layer    silver
            aeso_pool_pr
```

## Query: Wind/solar regressor source (how much is imputed)

| regressor_source | hours |
|---|---|
| metered | 7760 |
| csv_forecast | 168 |
| csv_actual | 79 |
| imputed | 1 |

## Query: Gold features

| rows | settled | first_mpt | last_mpt | imputed_hours |
|---|---|---|---|---|
| 8008 | 7840 | 2026-01-01T00:00:00.000Z | 2026-11-30T15:00:00.000Z | 1 |

## Query: Governed tags per table

| table_name | tag_name | tag_value |
|---|---|---|
| aeso_backtest_detail | data_product | machine_learning |
| aeso_backtest_detail | domain | operations |
| aeso_backtest_detail | layer | gold |
| aeso_backtest_metrics | data_product | machine_learning |
| aeso_backtest_metrics | domain | operations |
| aeso_backtest_metrics | layer | gold |
| aeso_backtest_windows | data_product | machine_learning |
| aeso_backtest_windows | domain | operations |
| aeso_backtest_windows | layer | gold |
| aeso_business_value | data_product | analytics |
| aeso_business_value | domain | operations |
| aeso_business_value | layer | gold |
| aeso_forecast_history | data_product | machine_learning |
| aeso_forecast_history | domain | operations |
| aeso_forecast_history | layer | gold |
| aeso_fundamentals_snapshots | data_product | data_engineering |
| aeso_fundamentals_snapshots | domain | operations |
| aeso_fundamentals_snapshots | layer | silver |
| aeso_model_promotions | data_product | machine_learning |
| aeso_model_promotions | domain | operations |
| aeso_model_promotions | layer | gold |
| aeso_outage_outlook | data_product | data_engineering |
| aeso_outage_outlook | domain | operations |
| aeso_outage_outlook | layer | silver |
| aeso_pool_price | data_product | data_engineering |
| aeso_pool_price | domain | operations |
| aeso_pool_price | layer | silver |
| aeso_price_drivers | data_product | analytics |
| aeso_price_drivers | domain | operations |
| aeso_price_drivers | layer | gold |
| aeso_price_forecast_output | data_product | machine_learning |
| aeso_price_forecast_output | domain | operations |
| aeso_price_forecast_output | layer | gold |
| aeso_supply_demand_hourly | data_product | data_engineering |
| aeso_supply_demand_hourly | domain | operations |
| aeso_supply_demand_hourly | layer | silver |
| aeso_wind_solar_forecast | data_product | data_engineering |
| aeso_wind_solar_forecast | domain | operations |
| aeso_wind_solar_forecast | layer | silver |
| aeso_wind_solar_metered | data_product | data_engineering |
| aeso_wind_solar_metered | domain | operations |
| aeso_wind_solar_metered | layer | silver |
| aeso_wind_solar_published | data_product | data_engineering |
| aeso_wind_solar_published | domain | operations |
| aeso_wind_solar_published | layer | silver |
| bronze_gen_capacity | data_product | data_engineering |
| bronze_gen_capacity | domain | operations |
| bronze_gen_capacity | layer | bronze |
| bronze_intertie | data_product | data_engineering |
| bronze_intertie | domain | operations |
| bronze_intertie | layer | bronze |
| bronze_load | data_product | data_engineering |
| bronze_load | domain | operations |
| bronze_load | layer | bronze |
| bronze_outage_outlook | data_product | data_engineering |
| bronze_outage_outlook | domain | operations |
| bronze_outage_outlook | layer | bronze |
| bronze_pool_price | data_product | data_engineering |
| bronze_pool_price | domain | operations |
| bronze_pool_price | layer | bronze |

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
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_metered | energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly

(truncated; full output in evidence/raw/ after a local export)
