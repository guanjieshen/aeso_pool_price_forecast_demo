# Ingest: AESO API + CSV into bronze Delta (Lakeflow Job tasks)

Exported 2026-11-23 20:25 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `507774967868631` · task run `82784872663730` · **SUCCESS** · 37s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
databricks-agents 1.11.0 requires urllib3<3,>=2.0, but you have urllib3 1.26.20 which is incompatible.
jupyterlab-server 2.28.0 requires requests>=2.31, but you have requests 2.26.0 which is incompatible.
databricks-sdk 0.122.0 requires requests<3,>=2.28.1, but you have requests 2.26.0 which is incompatible.

Last loaded MPT date: 2026-11-23  ->  fetching 2026-11-23 .. 2026-11-23

2026-11-23 .. 2026-11-23: 17 rows

MERGE: {'num_affected_rows': 17, 'num_updated_rows': 16, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  settled_hours first_hour_mpt       last_hour_mpt  avg_price_cad_mwh  max_price_cad_mwh
       7840           7836     2026-01-01 2026-11-23 16:00:00              33.72             999.99
```

## Task `ingest_wind_solar_forecast` (job `aeso-hourly`)

Job run `507774967868631` · task run `170613122224227` · **SUCCESS** · 39s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_forecast.md` (local)

```text
Parsed 215 rows from http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv

MERGE: {'num_affected_rows': 215, 'num_updated_rows': 214, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  hours_with_actual      first_hour_mpt       last_hour_mpt
        244                 76 2026-11-20 09:00:00 2026-11-30 12:00:00
forecast_transaction_date  min_mw  most_likely_mw  max_mw  actual_mw  mcr_mw  pct_min  pct_most_likely  pct_max
      2026-11-30 12:00:00  200.43          757.02 4642.79        NaN  7576.0     2.65             9.99    61.28
      2026-11-30 11:00:00  143.41          715.25 4312.83        NaN  7576.0     1.89             9.44    56.93
      2026-11-30 10:00:00   76.30          629.51 3950.75        NaN  7576.0     1.01             8.31    52.15
      2026-11-30 09:00:00   31.32          526.17 3558.31        NaN  7576.0     0.41             6.95    46.97
      2026-11-30 08:00:00   27.26          510.02 3424.87        NaN  7576.0     0.36             6.73    45.21
      2026-11-30 07:00:00   34.29          530.74 3374.87        NaN  7576.0     0.45             7.01    44.55
      2026-11-30 06:00:00   46.69          556.29 3369.12        NaN  7576.0     0.62             7.34    44.47
      2026-11-30 05:00:00  109.32          614.71 3315.49        NaN  7576.0     1.44             8.11    43.76
      2026-11-30 04:00:00  165.57          659.30 3216.60        NaN  7576.0     2.19             8.70    42.46
      2026-11-30 03:00:00  194.62          690.97 3117.51        NaN  7576.0     2.57             9.12    41.15
```

## Task `ingest_wind_solar_metered` (job `aeso-hourly`)

Job run `507774967868631` · task run `727479697857030` · **SUCCESS** · 38s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_metered.md` (local)

```text
Wind assets: 50, solar assets: 49

Fetching metered volumes 2026-11-17 .. 2026-11-23

2026-11-17 .. 2026-11-23: 144 hours so far

MERGE: {'num_affected_rows': 144, 'num_updated_rows': 144, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_hours first_hour_mpt       last_hour_mpt  avg_wind_mw  avg_solar_mw  max_wind_solar_mw  avg_assets_reporting
        7823     2026-01-01 2026-11-22 23:00:00       1760.8         427.8             5070.9                  98.3
```

## Task `ingest_outage_outlook` (job `aeso-hourly`)

Job run `507774967868631` · task run `656329686196679` · **SUCCESS** · 37s · full output `evidence/raw/aeso-hourly__ingest_outage_outlook.md` (local)

```text
report  periods first_period last_period  avg_gas_out_mw  max_dispatchable_out_mw
  daily      120   2026-11-01  2027-02-28          1270.0                   3886.0
monthly       24   2026-12-01  2028-11-01           762.0                   2193.0
 snapshots
         1
```

## Query: Bronze coverage

| table_name | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7840 | 2026-01-01T00:00:00.000Z | 2026-11-23T16:00:00.000Z |
| aeso_wind_solar_metered | 7823 | 2026-01-01T00:00:00.000Z | 2026-11-22T23:00:00.000Z |
| aeso_wind_solar_forecast | 245 | 2026-11-20T09:00:00.000Z | 2026-11-30T13:00:00.000Z |
