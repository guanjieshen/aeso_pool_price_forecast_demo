# Ingest: AESO API + CSV into bronze Delta (Lakeflow Job tasks)

Exported 2026-11-23 19:23 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `362081059053813` · task run `1084655225099105` · **SUCCESS** · 35s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
databricks-agents 1.11.0 requires urllib3<3,>=2.0, but you have urllib3 1.26.20 which is incompatible.
jupyterlab-server 2.28.0 requires requests>=2.31, but you have requests 2.26.0 which is incompatible.
databricks-sdk 0.122.0 requires requests<3,>=2.28.1, but you have requests 2.26.0 which is incompatible.

Last loaded MPT date: 2026-11-23  ->  fetching 2026-11-23 .. 2026-11-23

2026-11-23 .. 2026-11-23: 16 rows

MERGE: {'num_affected_rows': 16, 'num_updated_rows': 15, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  settled_hours first_hour_mpt       last_hour_mpt  avg_price_cad_mwh  max_price_cad_mwh
       7839           7835     2026-01-01 2026-11-23 15:00:00              33.72             999.99
```

## Task `ingest_wind_solar_forecast` (job `aeso-hourly`)

Job run `362081059053813` · task run `227673156037068` · **SUCCESS** · 36s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_forecast.md` (local)

```text
Parsed 215 rows from http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv

MERGE: {'num_affected_rows': 215, 'num_updated_rows': 215, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_rows  hours_with_actual      first_hour_mpt       last_hour_mpt
        243                 75 2026-11-20 09:00:00 2026-11-30 11:00:00
forecast_transaction_date  min_mw  most_likely_mw  max_mw  actual_mw  mcr_mw  pct_min  pct_most_likely  pct_max
      2026-11-30 11:00:00  135.75          732.17 4503.24        NaN  7576.0     1.79             9.66    59.44
      2026-11-30 10:00:00   76.08          649.05 4026.17        NaN  7576.0     1.00             8.57    53.14
      2026-11-30 09:00:00   30.89          547.94 3593.28        NaN  7576.0     0.41             7.23    47.43
      2026-11-30 08:00:00   26.64          536.81 3407.55        NaN  7576.0     0.35             7.09    44.98
      2026-11-30 07:00:00   33.57          563.65 3351.52        NaN  7576.0     0.44             7.44    44.24
      2026-11-30 06:00:00   45.86          596.01 3295.79        NaN  7576.0     0.61             7.87    43.50
      2026-11-30 05:00:00  108.43          659.66 3277.75        NaN  7576.0     1.43             8.71    43.26
      2026-11-30 04:00:00  167.38          706.93 3259.91        NaN  7576.0     2.21             9.33    43.03
      2026-11-30 03:00:00  208.99          742.42 3240.74        NaN  7576.0     2.76             9.80    42.78
      2026-11-30 02:00:00  245.77          787.94 3284.72        NaN  7576.0     3.24            10.40    43.36
```

## Task `ingest_wind_solar_metered` (job `aeso-hourly`)

Job run `362081059053813` · task run `63475109935593` · **SUCCESS** · 35s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_metered.md` (local)

```text
Wind assets: 50, solar assets: 49

Fetching metered volumes 2026-11-17 .. 2026-11-23

2026-11-17 .. 2026-11-23: 144 hours so far

MERGE: {'num_affected_rows': 144, 'num_updated_rows': 144, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_hours first_hour_mpt       last_hour_mpt  avg_wind_mw  avg_solar_mw  max_wind_solar_mw  avg_assets_reporting
        7823     2026-01-01 2026-11-22 23:00:00       1760.8         427.8             5070.9                  98.3
```

## Query: Bronze coverage

| table_name | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7839 | 2026-01-01T00:00:00.000Z | 2026-11-23T15:00:00.000Z |
| aeso_wind_solar_metered | 7823 | 2026-01-01T00:00:00.000Z | 2026-11-22T23:00:00.000Z |
| aeso_wind_solar_forecast | 243 | 2026-11-20T09:00:00.000Z | 2026-11-30T11:00:00.000Z |
