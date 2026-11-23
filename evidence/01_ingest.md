# Lakeflow: Jobs (ingest, orchestration) and the Spark Declarative Pipeline, as deployed and run

Exported 2026-11-23 23:25 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Lakeflow build as deployed

### Lakeflow Jobs (deployed definitions, Jobs API)

| Job | Trigger | Tasks (depends on) |
|---|---|---|
| `aeso-hourly` | cron `0 20 * * * ?` America/Edmonton | forecast [notebook] (transform); governance [notebook] (lakebase_sync); ingest_outage_outlook [notebook]; ingest_pool_price [notebook]; ingest_supply_demand [notebook] (ingest_wind_solar_forecast); ingest_wind_solar_forecast [notebook]; ingest_wind_solar_metered [notebook]; lakebase_sync [notebook] (forecast); transform [pipeline] (ingest_pool_price,ingest_wind_solar_forecast,ingest_wind_solar_metered,ingest_supply_demand) |
| `aeso-weekly-retrain` | cron `0 30 5 ? * MON` America/Edmonton | train_challenger [notebook] |
| `aeso-evaluate-challenger` | model update trigger on `['challenger']` | business_value [notebook] (evaluate_and_promote); evaluate_and_promote [notebook]; governance [notebook] (business_value,rebaseline); rebaseline [notebook] (evaluate_and_promote) |
| `aeso-daily-monitor` | cron `0 45 6 * * ?` America/Edmonton | live_accuracy_and_drift [notebook]; price_drivers [notebook] |
| `aeso-rebaseline` | manual | rebaseline_windows [notebook] |

### Latest successful `aeso-hourly` run `398610988453239`

| Task | Result | Seconds |
|---|---|---|
| ingest_pool_price | SUCCESS | 27 |
| ingest_wind_solar_forecast | SUCCESS | 17 |
| ingest_wind_solar_metered | SUCCESS | 76 |
| ingest_outage_outlook | SUCCESS | 23 |
| ingest_supply_demand | SUCCESS | 112 |
| transform | SUCCESS | 133 |
| forecast | SUCCESS | 82 |
| lakebase_sync | SUCCESS | 58 |
| governance | SUCCESS | 44 |

### Lakeflow Spark Declarative Pipeline `aeso-transform`

Serverless: True · channel CURRENT · target `energy_canada_demos_catalog.aeso_price_forecast` · source `src/pipeline/ingest.py, src/pipeline/transformations.py` · latest update `242cef7e-063b-45d9-bb54-d07a26bb67fc`: **COMPLETED** (created 2026-11-23 23:16 UTC)

Expectations on the latest update (pipeline event log):

| dataset | expectation | passed_records | failed_records |
|---|---|---|---|
| energy_canada_demos_catalog.aeso_price_forecast.aeso_fundamentals_snapshots | forward_only | 335 | 15679 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_outage_outlook | valid_period | 864 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_pool_price | valid_hour | 7843 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_supply_demand_hourly | valid_hour | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_forecast | valid_hour | 247 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_metered | valid_hour | 7823 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.aeso_wind_solar_published | valid_hour | 7295 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_gen_capacity | has_fuel_hour | 71271 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_intertie | has_tie_hour | 39595 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_load | has_hour | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_outage_outlook | has_period | 144 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_pool_price | has_hour | 7843 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_wind_solar_forecast | has_hour | 215 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.bronze_wind_solar_metered | has_asset_hour | 768814 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | has_regressor | 8008 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | valid_hour | 8008 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | aeso_forecast_present | 7843 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | price_in_market_range | 7843 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | valid_hour | 7843 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | capability_present | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | dayahead_wind_present | 7367 | 552 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | load_in_range | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | valid_hour | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | regressor_present | 8008 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | valid_hour | 8008 | 0 |

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `398610988453239` · task run `192711719504626` · **SUCCESS** · 27s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
Last settled MPT date: None -> fetching 2026-01-01 .. 2026-11-23

2026-01-01 .. 2026-01-31: 744 records
  2026-02-01 .. 2026-03-03: 744 records
  2026-03-04 .. 2026-04-03: 743 records
  2026-04-04 .. 2026-05-04: 744 records
  2026-05-05 .. 2026-06-04: 744 records
  2026-06-05 .. 2026-07-05: 744 records
  2026-07-06 .. 2026-08-05: 744 records
  2026-08-06 .. 2026-09-05: 744 records
  2026-09-06 .. 2026-10-06: 744 records
  2026-10-07 .. 2026-11-06: 744 records
  2026-11-07 .. 2026-11-23: 404 records
Landed 7843 raw records -> /Volumes/energy_canada_demos_catalog/aeso_price_forecast/raw/pool_price/2026-11-23/pool_price_2026-11-23T231428Z.jsonl
First record as landed: {"begin_datetime_utc": "2026-01-01 07:00", "begin_datetime_mpt": "2026-01-01 00:00", "pool_price": "32.40", "forecast_pool_price": "28.46", "rolling_30day_avg": "39.49"}
```

## Query: Bronze streaming tables (Auto Loader from the raw landing volume): records and files landed

| bronze_table | records | files_landed | last_landed_utc |
|---|---|---|---|
| bronze_pool_price | 15685 | 2 | 2026-11-23T23:14:30.000Z |
| bronze_wind_solar_forecast | 509 | 3 | 2026-11-23T23:14:18.000Z |
| bronze_wind_solar_metered | 1537628 | 2 | 2026-11-23T23:14:30.000Z |
| bronze_load | 15838 | 2 | 2026-11-23T23:16:11.000Z |
| bronze_gen_capacity | 142542 | 2 | 2026-11-23T23:16:12.000Z |
| bronze_intertie | 79190 | 2 | 2026-11-23T23:16:12.000Z |
| bronze_wind_solar_published | 14592 | 2 | 2026-11-23T23:00:33.000Z |
| bronze_outage_outlook | 864 | 3 | 2026-11-23T23:14:26.000Z |

## Query: Conformed silver built by the pipeline from bronze

| silver_view | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7843 | 2026-01-01T00:00:00.000Z | 2026-11-23T19:00:00.000Z |
| aeso_wind_solar_metered | 7823 | 2026-01-01T00:00:00.000Z | 2026-11-22T23:00:00.000Z |
| aeso_supply_demand_hourly | 7919 | 2026-01-01T00:00:00.000Z | 2026-11-26T23:00:00.000Z |
| gold_price_features_hourly | 8008 | 2026-01-01T00:00:00.000Z | 2026-11-30T15:00:00.000Z |
