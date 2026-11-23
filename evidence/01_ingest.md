# Lakeflow: Jobs (ingest, orchestration) and the Spark Declarative Pipeline, as deployed and run

Exported 2026-11-23 21:54 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Lakeflow build as deployed

### Lakeflow Jobs (deployed definitions, Jobs API)

| Job | Trigger | Tasks (depends on) |
|---|---|---|
| `aeso-hourly` | cron `0 20 * * * ?` America/Edmonton | forecast [notebook] (transform); governance [notebook] (lakebase_sync); ingest_outage_outlook [notebook]; ingest_pool_price [notebook]; ingest_supply_demand [notebook] (ingest_wind_solar_forecast); ingest_wind_solar_forecast [notebook]; ingest_wind_solar_metered [notebook]; lakebase_sync [notebook] (forecast); transform [pipeline] (ingest_pool_price,ingest_wind_solar_forecast,ingest_wind_solar_metered,ingest_supply_demand) |
| `aeso-weekly-retrain` | cron `0 30 5 ? * MON` America/Edmonton | train_challenger [notebook] |
| `aeso-evaluate-challenger` | model update trigger on `['challenger']` | business_value [notebook] (evaluate_and_promote); evaluate_and_promote [notebook]; governance [notebook] (business_value,rebaseline); rebaseline [notebook] (evaluate_and_promote) |
| `aeso-daily-monitor` | cron `0 45 6 * * ?` America/Edmonton | live_accuracy_and_drift [notebook]; price_drivers [notebook] |
| `aeso-rebaseline` | manual | rebaseline_windows [notebook] |

### Latest successful `aeso-hourly` run `338879449112685`

| Task | Result | Seconds |
|---|---|---|
| ingest_pool_price | SUCCESS | 36 |
| ingest_wind_solar_forecast | SUCCESS | 37 |
| ingest_wind_solar_metered | SUCCESS | 36 |
| ingest_outage_outlook | SUCCESS | 40 |
| ingest_supply_demand | SUCCESS | 25 |
| transform | SUCCESS | 82 |
| forecast | SUCCESS | 55 |
| lakebase_sync | SUCCESS | 57 |
| governance | SUCCESS | 33 |

### Lakeflow Spark Declarative Pipeline `aeso-transform`

Serverless: True · channel CURRENT · target `energy_canada_demos_catalog.aeso_price_forecast` · source `src/pipeline/transformations.py` · latest update `2af14aab-c7fa-4769-9ff6-3bd8d687df0d`: **COMPLETED** (created 2026-11-23 21:21 UTC)

Expectations on the latest update (pipeline event log):

| dataset | expectation | passed_records | failed_records |
|---|---|---|---|
| energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | has_regressor | 8006 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.gold_price_features_hourly | valid_hour | 8006 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | aeso_forecast_present | 7841 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | price_in_market_range | 7841 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_pool_price_hourly | valid_hour | 7841 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | capability_present | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | dayahead_wind_present | 7365 | 554 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | load_in_range | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_supply_demand_hourly | valid_hour | 7919 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | regressor_present | 8006 | 0 |
| energy_canada_demos_catalog.aeso_price_forecast.silver_wind_solar_hourly | valid_hour | 8006 | 0 |

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `338879449112685` · task run `667693972042684` · **SUCCESS** · 36s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
Last loaded MPT date: 2026-11-23  ->  fetching 2026-11-23 .. 2026-11-23

2026-11-23 .. 2026-11-23: 18 rows

MERGE: {'num_affected_rows': 18, 'num_updated_rows': 17, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  settled_hours first_hour_mpt       last_hour_mpt  avg_price_cad_mwh  max_price_cad_mwh
       7841           7838     2026-01-01 2026-11-23 17:00:00              33.72             999.99
```

## Task `ingest_wind_solar_forecast` (job `aeso-hourly`)

Job run `338879449112685` · task run `557074067594023` · **SUCCESS** · 37s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_forecast.md` (local)

```text
Parsed 215 rows from http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv

MERGE: {'num_affected_rows': 215, 'num_updated_rows': 215, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_rows  hours_with_actual      first_hour_mpt       last_hour_mpt
        245                 77 2026-11-20 09:00:00 2026-11-30 13:00:00
forecast_transaction_date  min_mw  most_likely_mw  max_mw  actual_mw  mcr_mw  pct_min  pct_most_likely  pct_max
      2026-11-30 13:00:00  242.57          871.89 5067.28        NaN  7576.0     3.20            11.51    66.89
      2026-11-30 12:00:00  213.38          848.17 4460.10        NaN  7576.0     2.82            11.20    58.87
      2026-11-30 11:00:00  143.79          787.19 4064.76        NaN  7576.0     1.90            10.39    53.65
      2026-11-30 10:00:00   78.27          694.92 3758.00        NaN  7576.0     1.03             9.17    49.60
      2026-11-30 09:00:00   34.38          591.37 3567.03        NaN  7576.0     0.45             7.81    47.08
      2026-11-30 08:00:00   30.81          569.80 3376.07        NaN  7576.0     0.41             7.52    44.56
      2026-11-30 07:00:00   36.90          581.98 3371.85        NaN  7576.0     0.49             7.68    44.51
      2026-11-30 06:00:00   49.76          599.28 3366.51        NaN  7576.0     0.66             7.91    44.44
      2026-11-30 05:00:00  116.49          643.11 3313.62        NaN  7576.0     1.54             8.49    43.74
      2026-11-30 04:00:00  157.23          664.86 3215.50        NaN  7576.0     2.08             8.78    42.44
```

## Task `ingest_wind_solar_metered` (job `aeso-hourly`)

Job run `338879449112685` · task run `67633103066227` · **SUCCESS** · 36s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_metered.md` (local)

```text
Wind assets: 50, solar assets: 49

Fetching metered volumes 2026-11-17 .. 2026-11-23

2026-11-17 .. 2026-11-23: 144 hours so far

MERGE: {'num_affected_rows': 144, 'num_updated_rows': 144, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_hours first_hour_mpt       last_hour_mpt  avg_wind_mw  avg_solar_mw  max_wind_solar_mw  avg_assets_reporting
        7823     2026-01-01 2026-11-22 23:00:00       1760.8         427.8             5070.9                  98.3
```

## Task `ingest_outage_outlook` (job `aeso-hourly`)

Job run `338879449112685` · task run `767877898214113` · **SUCCESS** · 40s · full output `evidence/raw/aeso-hourly__ingest_outage_outlook.md` (local)

```text
report  periods first_period last_period  avg_gas_out_mw  max_dispatchable_out_mw
  daily      120   2026-11-01  2027-02-28          1270.0                   3886.0
monthly       24   2026-12-01  2028-11-01           762.0                   2193.0
 snapshots
         3
```

## Query: Bronze coverage

| table_name | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7841 | 2026-01-01T00:00:00.000Z | 2026-11-23T17:00:00.000Z |
| aeso_wind_solar_metered | 7823 | 2026-01-01T00:00:00.000Z | 2026-11-22T23:00:00.000Z |
| aeso_wind_solar_forecast | 245 | 2026-11-20T09:00:00.000Z | 2026-11-30T13:00:00.000Z |
