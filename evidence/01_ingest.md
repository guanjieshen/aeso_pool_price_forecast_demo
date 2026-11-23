# Ingest: AESO API + CSV into bronze Delta (Lakeflow Job tasks)

Exported 2026-11-23 16:06 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_pool_price` (job `aeso-hourly`)

Job run `1062095509219844` · task run `88766344160378` · **SUCCESS** · 34s · full output `evidence/raw/aeso-hourly__ingest_pool_price.md` (local)

```text
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
databricks-agents 1.11.0 requires urllib3<3,>=2.0, but you have urllib3 1.26.20 which is incompatible.
jupyterlab-server 2.28.0 requires requests>=2.31, but you have requests 2.26.0 which is incompatible.
databricks-sdk 0.122.0 requires requests<3,>=2.28.1, but you have requests 2.26.0 which is incompatible.

Last loaded MPT date: 2026-11-23  ->  fetching 2026-11-23 .. 2026-11-23

2026-11-23 .. 2026-11-23: 12 rows

MERGE: {'num_affected_rows': 12, 'num_updated_rows': 12, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_rows  settled_hours first_hour_mpt       last_hour_mpt  avg_price_cad_mwh  max_price_cad_mwh
       7835           7832     2026-01-01 2026-11-23 11:00:00              33.73             999.99
```

## Task `ingest_wind_solar_forecast` (job `aeso-hourly`)

Job run `1062095509219844` · task run `83546515538691` · **SUCCESS** · 34s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_forecast.md` (local)

```text
Parsed 215 rows from http://ets.aeso.ca/Market/Reports/Manual/Operations/prodweb_reports/wind_solar_forecast/windsolar_rpt_longterm.csv

MERGE: {'num_affected_rows': 215, 'num_updated_rows': 215, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_rows  hours_with_actual      first_hour_mpt       last_hour_mpt
        240                 72 2026-11-20 09:00:00 2026-11-30 08:00:00
forecast_transaction_date  min_mw  most_likely_mw  max_mw  actual_mw  mcr_mw  pct_min  pct_most_likely  pct_max
      2026-11-30 08:00:00     0.0          192.39 3665.90        NaN  7576.0      0.0             2.54    48.39
      2026-11-30 07:00:00     0.0          204.39 3296.24        NaN  7576.0      0.0             2.70    43.51
      2026-11-30 06:00:00     0.0          226.80 3119.60        NaN  7576.0      0.0             2.99    41.18
      2026-11-30 05:00:00     0.0          324.88 3015.51        NaN  7576.0      0.0             4.29    39.80
      2026-11-30 04:00:00     0.0          358.44 2947.01        NaN  7576.0      0.0             4.73    38.90
      2026-11-30 03:00:00     0.0          380.20 2878.51        NaN  7576.0      0.0             5.02    38.00
      2026-11-30 02:00:00     0.0          408.10 2904.88        NaN  7576.0      0.0             5.39    38.34
      2026-11-30 01:00:00     0.0          443.14 2988.37        NaN  7576.0      0.0             5.85    39.45
      2026-11-30 00:00:00     0.0          484.84 3064.52        NaN  7576.0      0.0             6.40    40.45
      2026-11-29 23:00:00     0.0          557.23 3098.40        NaN  7576.0      0.0             7.36    40.90
```

## Task `ingest_wind_solar_metered` (job `aeso-hourly`)

Job run `1062095509219844` · task run `408972227608935` · **SUCCESS** · 34s · full output `evidence/raw/aeso-hourly__ingest_wind_solar_metered.md` (local)

```text
Wind assets: 50, solar assets: 49

Fetching metered volumes 2026-11-14 .. 2026-11-23

2026-11-14 .. 2026-11-23: 144 hours so far

MERGE: {'num_affected_rows': 144, 'num_updated_rows': 144, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

total_hours first_hour_mpt       last_hour_mpt  avg_wind_mw  avg_solar_mw  max_wind_solar_mw  avg_assets_reporting
        7751     2026-01-01 2026-11-19 23:00:00       1775.7         431.5             5070.9                  98.3
```

## Query: Bronze coverage

| table_name | rows | first_mpt | last_mpt |
|---|---|---|---|
| aeso_pool_price | 7835 | 2026-01-01T00:00:00.000Z | 2026-11-23T11:00:00.000Z |
| aeso_wind_solar_metered | 7751 | 2026-01-01T00:00:00.000Z | 2026-11-19T23:00:00.000Z |
| aeso_wind_solar_forecast | 240 | 2026-11-20T09:00:00.000Z | 2026-11-30T08:00:00.000Z |
