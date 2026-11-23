# Fundamentals: supply cushion drivers, day-ahead (as-known) features, snapshot archive

Exported 2026-11-23 19:23 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_supply_demand` (job `aeso-hourly`)

Job run `362081059053813` · task run `252878111033472` · **SUCCESS** · 42s · full output `evidence/raw/aeso-hourly__ingest_supply_demand.md` (local)

```text
Fetching load, capability and intertie capability 2026-11-20 .. 2026-11-26

2026-11-20 .. 2026-11-26: 168 hours so far

MERGE: {'num_affected_rows': 168, 'num_updated_rows': 168, 'num_deleted_rows': 0, 'num_inserted_rows': 0}

Published wind/solar forecast hours: 7293 (2026-01-01 00:00:00 .. 2026-10-31 23:00:00)

total_hours first_hour_mpt       last_hour_mpt  future_hours  avg_load_mw  avg_dispatchable_available_mw  avg_outage_mw  avg_import_atc_mw  min_import_atc_mw
        7919     2026-01-01 2026-11-26 23:00:00            83      10474.0                        11609.0         4208.0              602.0                0.0
 snapshots  rows      first_hour_mpt       last_hour_mpt
         3   503 2026-11-23 12:00:00 2026-11-30 11:00:00
```

## Task `price_drivers` (job `aeso-daily-monitor`)

Job run `969496076854403` · task run `625174033809296` · **SUCCESS** · 27s · full output `evidence/raw/aeso-daily-monitor__price_drivers.md` (local)

```text
Settled hours with fundamentals: 7835 (2026-01-01 00:00:00 .. 2026-11-23 11:00:00 MPT)

segment  explained_variance_pct  spike_explained_variance_pct  spearman_corr
        supply_cushion_mw                  24.006                        17.889         -0.811
              net_load_mw                  17.232                        10.337          0.867
            wind_solar_mw                  12.217                         5.718         -0.815
              hour_ending                   3.995                         2.789          0.159
            import_atc_mw                   2.748                         2.542         -0.166
                  load_mw                   2.402                         1.542          0.234
              day_of_week                   1.331                         1.056          0.041
                outage_mw                   1.031                         0.611         -0.075
dispatchable_available_mw                   0.978                         0.580          0.078

cushion_band  hours  avg_price  median_price  p_above_150_pct  max_price  share_of_hours_pct
     < 1,000     25      774.2         833.5             92.0     1000.0                 0.3
 1,000-1,500    130      329.4         148.6             50.0     1000.0                 1.7
 1,500-2,000    326      124.1          56.7             20.9      948.6                 4.2
 2,000-2,500    689       55.1          36.0              4.9      648.6                 8.8
 2,500-3,000    976       40.5          31.1              0.9      547.7                12.5
 3,000-4,000   1992       23.8          23.1              0.1      215.0                25.4
 4,000-5,000   1898       13.2          13.8              0.0       57.8                24.2
     > 5,000   1799        6.3           4.4              0.0       30.2                23.0

Spike hours (> $150): 200. Median cushion in spike hours 1,593 MW vs 3,944 MW otherwise.
Hours with cushion under 2,000 MW: 6.1% of hours, holding 78% of spike hours.

Wrote 17 rows to energy_canada_demos_catalog.aeso_price_forecast.aeso_price_drivers
```

## Query: Day-ahead feature coverage by month (backtests use only these)

| month | settled_hours | dayahead_hours | source | avg_cushion_mw | avg_import_atc_mw |
|---|---|---|---|---|---|
| 2026-01 | 744 | 720 | published_file | 4741.0 | 560.0 |
| 2026-02 | 672 | 672 | published_file | 4923.0 | 627.0 |
| 2026-03 | 743 | 742 | published_file | 4300.0 | 634.0 |
| 2026-04 | 720 | 720 | published_file | 3409.0 | 595.0 |
| 2026-05 | 744 | 744 | published_file | 3422.0 | 660.0 |
| 2026-06 | 720 | 720 | published_file | 3860.0 | 578.0 |
| 2026-07 | 744 | 742 | published_file | 3860.0 | 625.0 |
| 2026-08 | 744 | 744 | published_file | 3531.0 | 517.0 |
| 2026-09 | 720 | 720 | published_file | 3865.0 | 597.0 |
| 2026-10 | 744 | 744 | published_file | 3497.0 | 605.0 |
| 2026-11 | 540 | 72 |  | 4114.0 | 625.0 |

## Query: Published wind/solar forecast accuracy (AESO file vs actual)

| hours | mae_mw | bias_mw | avg_actual_mw | last_hour_mpt |
|---|---|---|---|---|
| 7293 | 364.0 | 124.0 | 2199.0 | 2026-10-31T23:00:00.000Z |

## Query: Snapshot archive (what was known at each run)

| snapshots | rows | first_snapshot_utc | last_snapshot_utc | furthest_hour_mpt |
|---|---|---|---|---|
| 4 | 670 | 2026-11-23T18:28:14.000Z | 2026-11-23T19:21:37.000Z | 2026-11-30T11:00:00.000Z |

## Query: Live forecast: cushion, fundamentals weight and P(price > $150), next 24 h

| forecast_datetime_mpt | cushion_mw | fund_weight | fund_price | ensemble | p_above_150 |
|---|---|---|---|---|---|
| 2026-11-23T12:00:00.000Z | 3832.0 | 0.0 | 21.47 | 14.6 | 0.018 |
| 2026-11-23T13:00:00.000Z | 3540.0 | 0.0 | 22.78 | 18.49 | 0.03 |
| 2026-11-23T14:00:00.000Z | 3558.0 | 0.0 | 22.89 | 20.45 | 0.064 |
| 2026-11-23T15:00:00.000Z | 3446.0 | 0.0 | 22.96 | 21.23 | 0.07 |
| 2026-11-23T16:00:00.000Z | 3082.0 | 0.0 | 27.31 | 22.77 | 0.066 |
| 2026-11-23T17:00:00.000Z | 2910.0 | 0.0 | 29.8 | 24.58 | 0.082 |
| 2026-11-23T18:00:00.000Z | 3254.0 | 0.0 | 26.05 | 23.55 | 0.064 |
| 2026-11-23T19:00:00.000Z | 3483.0 | 0.0 | 23.25 | 22.5 | 0.08 |
| 2026-11-23T20:00:00.000Z | 3671.0 | 0.0 | 22.68 | 22.38 | 0.086 |
| 2026-11-23T21:00:00.000Z | 3910.0 | 0.0 | 18.43 | 20.56 | 0.084 |
| 2026-11-23T22:00:00.000Z | 4113.0 | 0.0 | 17.74 | 18.64 | 0.07 |
| 2026-11-23T23:00:00.000Z | 4321.0 | 0.0 | 17.64 | 16.54 | 0.046 |
| 2026-11-24T00:00:00.000Z | 4674.0 | 0.0 | 17.35 | 16.13 | 0.006 |
| 2026-11-24T01:00:00.000Z | 4619.0 | 0.0 | 18.15 | 16.46 | 0.014 |
| 2026-11-24T02:00:00.000Z | 4524.0 | 0.0 | 18.86 | 17.06 | 0.026 |
| 2026-11-24T03:00:00.000Z | 4377.0 | 0.0 | 19.83 | 17.4 | 0.018 |
| 2026-11-24T04:00:00.000Z | 4114.0 | 0.0 | 21.53 | 19.19 | 0.018 |
| 2026-11-24T05:00:00.000Z | 3742.0 | 0.0 | 23.93 | 21.55 | 0.018 |
| 2026-11-24T06:00:00.000Z | 3206.0 | 0.0 | 24.44 | 23.72 | 0.034 |
| 2026-11-24T07:00:00.000Z | 2651.0 | 0.0 | 26.92 | 26.33 | 0.056 |
| 2026-11-24T08:00:00.000Z | 2453.0 | 0.03 | 28.32 | 27.63 | 0.054 |
| 2026-11-24T09:00:00.000Z | 2574.0 | 0.0 | 28.47 | 27.35 | 0.056 |
| 2026-11-24T10:00:00.000Z | 2982.0 | 0.0 | 29.02 | 25.16 | 0.07 |
| 2026-11-24T11:00:00.000Z | 3382.0 | 0.0 | 25.01 | 22.72 | 0.048 |
