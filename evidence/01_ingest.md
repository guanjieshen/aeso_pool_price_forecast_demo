# Ingest: AESO API + CSV into bronze Delta (Lakeflow Job tasks)

Exported 2026-11-22 19:10 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `683048180465385` · task run `264432538648731` · **SUCCESS** · 32s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
databricks-agents 1.11.0 requires urllib3<3,>=2.0, but you have urllib3 1.26.20 which is incompatible.
jupyterlab-server 2.28.0 requires requests>=2.31, but you have requests 2.26.0 which is incompatible.
databricks-sdk 0.122.0 requires requests<3,>=2.28.1, but you have requests 2.26.0 which is incompatible.

Last loaded MPT date: 2026-11-22  ->  fetching 2026-11-22 .. 2026-11-22

2026-11-22 .. 2026-11-22: 16 rows

MERGE: {'num_affected_rows': 16, 'num_updated_rows': 15, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  settled_hours first_hour_mpt       last_hour_mpt  avg_price_cad_mwh  max_price_cad_mwh
       7815           7812     2026-01-01 2026-11-22 15:00:00              33.75             999.99
```

## Task `ingest_wind_solar_forecast` (job `aeso-hourly`)

Job run `683048180465385` · task run `911076849646108` · **SUCCESS** · 34s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_forecast.md` (local)

```text
Parsed 216 rows from http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv

MERGE: {'num_affected_rows': 216, 'num_updated_rows': 215, 'num_deleted_rows': 0, 'num_inserted_rows': 1}

total_rows  hours_with_actual      first_hour_mpt       last_hour_mpt
        219                 51 2026-11-20 09:00:00 2026-11-29 11:00:00
forecast_transaction_date  min_mw  most_likely_mw  max_mw  actual_mw  mcr_mw  pct_min  pct_most_likely  pct_max
      2026-11-29 11:00:00  410.28         1025.61 3039.65        NaN  7576.0     5.42            13.54    40.12
      2026-11-29 10:00:00  328.39          849.38 2216.82        NaN  7576.0     4.33            11.21    29.26
      2026-11-29 09:00:00  239.65          607.61 1542.30        NaN  7576.0     3.16             8.02    20.36
      2026-11-29 08:00:00  206.63          527.09 1207.84        NaN  7576.0     2.73             6.96    15.94
      2026-11-29 07:00:00  175.69          524.47 1082.02        NaN  7576.0     2.32             6.92    14.28
      2026-11-29 06:00:00  145.30          528.81  957.27        NaN  7576.0     1.92             6.98    12.64
      2026-11-29 05:00:00  108.64          577.06 1002.82        NaN  7576.0     1.43             7.62    13.24
      2026-11-29 04:00:00   65.98          626.67  994.78        NaN  7576.0     0.87             8.27    13.13
      2026-11-29 03:00:00   23.22          668.20  995.08        NaN  7576.0     0.31             8.82    13.13
      2026-11-29 02:00:00    7.91          703.92 1004.17        NaN  7576.0     0.10             9.29    13.25
```

## Task `ingest_wind_solar_metered` (job `aeso-hourly`)

Job run `683048180465385` · task run `1099753695769660` · **SUCCESS** · 34s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_metered.md` (local)

```text
Wind assets: 50, solar assets: 49

Fetching metered volumes 2026-11-14 .. 2026-11-22

2026-11-14 .. 2026-11-22: 144 hours so far

MERGE: {'num_affected_rows': 144, 'num_updated_rows': 144, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_hours first_hour_mpt       last_hour_mpt  avg_wind_mw  avg_solar_mw  max_wind_solar_mw  avg_assets_reporting
        7751     2026-01-01 2026-11-19 23:00:00       1775.7         431.5             5070.9                  98.3
```

## Query: Bronze coverage

| table_name | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7815 | 2026-01-01T00:00:00.000Z | 2026-11-22T15:00:00.000Z |
| aeso_wind_solar_metered | 7751 | 2026-01-01T00:00:00.000Z | 2026-11-19T23:00:00.000Z |
| aeso_wind_solar_forecast | 219 | 2026-11-20T09:00:00.000Z | 2026-11-29T11:00:00.000Z |
