# Fundamentals: supply cushion drivers, day-ahead (as-known) features, snapshot archive

Exported 2026-11-23 23:25 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `ingest_supply_demand` (job `aeso-hourly`)

Job run `398610988453239` · task run `374950965050970` · **SUCCESS** · 112s · full output `evidence/raw/aeso-hourly__ingest_supply_demand.md` (local)

```text
Fetching load, capability and intertie capability 2026-01-01 .. 2026-11-26

2026-01-01 .. 2026-01-31: 744 load, 6696 capability, 3720 intertie records
  2026-02-01 .. 2026-03-03: 1488 load, 13392 capability, 7440 intertie records
  2026-03-04 .. 2026-04-03: 2231 load, 20079 capability, 11155 intertie records
  2026-04-04 .. 2026-05-04: 2975 load, 26775 capability, 14875 intertie records
  2026-05-05 .. 2026-06-04: 3719 load, 33471 capability, 18595 intertie records
  2026-06-05 .. 2026-07-05: 4463 load, 40167 capability, 22315 intertie records
  2026-07-06 .. 2026-08-05: 5207 load, 46863 capability, 26035 intertie records
  2026-08-06 .. 2026-09-05: 5951 load, 53559 capability, 29755 intertie records
  2026-09-06 .. 2026-10-06: 6695 load, 60255 capability, 33475 intertie records
  2026-10-07 .. 2026-11-06: 7439 load, 66951 capability, 37195 intertie records
  2026-11-07 .. 2026-11-26: 7919 load, 71271 capability, 39595 intertie records
Landed 7919 raw load records -> /Volumes/energy_canada_demos_catalog/aeso_price_forecast/raw/load/2026-11-23/load_2026-11-23T231428Z.jsonl
Landed 71271 raw gen_capacity records -> /Volumes/energy_canada_demos_catalog/aeso_price_forecast/raw/gen_capacity/2026-11-23/gen_capacity_2026-11-23T231428Z.jsonl
Landed 39595 raw intertie records -> /Volumes/energy_canada_demos_catalog/aeso_price_forecast/raw/intertie/2026-11-23/intertie_2026-11-23T231428Z.jsonl

Wind 2026: unchanged (463bb0dd899a)
  Solar 2026: unchanged (188fa5738f6c)
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
| 2026-07 | 744 | 744 | published_file | 3860.0 | 625.0 |
| 2026-08 | 744 | 744 | published_file | 3531.0 | 517.0 |
| 2026-09 | 720 | 720 | published_file | 3865.0 | 597.0 |
| 2026-10 | 744 | 744 | published_file | 3497.0 | 605.0 |
| 2026-11 | 545 | 72 |  | 4111.0 | 625.0 |

## Query: Published wind/solar forecast accuracy (AESO file vs actual)

| hours | mae_mw | bias_mw | avg_actual_mw | last_hour_mpt |
|---|---|---|---|---|
| 7295 | 365.0 | 124.0 | 2199.0 | 2026-10-31T23:00:00.000Z |

## Query: Snapshot archive (what was known at each run)

| snapshots | rows | first_snapshot_utc | last_snapshot_utc | furthest_hour_mpt |
|---|---|---|---|---|
| 2 | 335 | 2026-11-23T22:00:00.000Z | 2026-11-23T23:00:00.000Z | 2026-11-30T15:00:00.000Z |

## Query: Live forecast: cushion, fundamentals weight and P(price > $150), next 24 h

| forecast_datetime_mpt | cushion_mw | fund_weight | fund_price | ensemble | p_above_150 |
|---|---|---|---|---|---|
| 2026-11-23T17:00:00.000Z | 2820.0 | 0.0 | 31.88 | 27.09 | 0.024 |
| 2026-11-23T18:00:00.000Z | 3159.0 | 0.0 | 28.39 | 26.17 | 0.044 |
| 2026-11-23T19:00:00.000Z | 3439.0 | 0.0 | 26.16 | 25.38 | 0.086 |
| 2026-11-23T20:00:00.000Z | 3672.0 | 0.0 | 22.15 | 24.18 | 0.07 |
| 2026-11-23T21:00:00.000Z | 3940.0 | 0.0 | 19.25 | 22.22 | 0.074 |
| 2026-11-23T22:00:00.000Z | 4156.0 | 0.0 | 17.1 | 20.32 | 0.084 |
| 2026-11-23T23:00:00.000Z | 4397.0 | 0.0 | 17.34 | 18.16 | 0.036 |
| 2026-11-24T00:00:00.000Z | 4742.0 | 0.0 | 17.85 | 16.78 | 0.03 |
| 2026-11-24T01:00:00.000Z | 4706.0 | 0.0 | 17.8 | 17.1 | 0.028 |
| 2026-11-24T02:00:00.000Z | 4569.0 | 0.0 | 19.42 | 17.25 | 0.034 |
| 2026-11-24T03:00:00.000Z | 4360.0 | 0.0 | 20.59 | 18.43 | 0.028 |
| 2026-11-24T04:00:00.000Z | 4104.0 | 0.0 | 21.97 | 19.57 | 0.012 |
| 2026-11-24T05:00:00.000Z | 3719.0 | 0.0 | 23.41 | 21.85 | 0.006 |
| 2026-11-24T06:00:00.000Z | 3185.0 | 0.0 | 24.3 | 24.71 | 0.046 |
| 2026-11-24T07:00:00.000Z | 2637.0 | 0.0 | 27.67 | 26.99 | 0.05 |
| 2026-11-24T08:00:00.000Z | 2450.0 | 0.03 | 28.1 | 28.43 | 0.06 |
| 2026-11-24T09:00:00.000Z | 2571.0 | 0.0 | 29.39 | 27.76 | 0.058 |
| 2026-11-24T10:00:00.000Z | 2973.0 | 0.0 | 28.95 | 25.38 | 0.052 |
| 2026-11-24T11:00:00.000Z | 3374.0 | 0.0 | 25.98 | 22.32 | 0.044 |
| 2026-11-24T12:00:00.000Z | 3739.0 | 0.0 | 22.37 | 20.37 | 0.052 |
| 2026-11-24T13:00:00.000Z | 3981.0 | 0.0 | 21.0 | 18.53 | 0.04 |
| 2026-11-24T14:00:00.000Z | 4371.0 | 0.0 | 16.7 | 16.68 | 0.05 |
| 2026-11-24T15:00:00.000Z | 4707.0 | 0.0 | 13.54 | 15.09 | 0.078 |
| 2026-11-24T16:00:00.000Z | 4707.0 | 0.0 | 15.49 | 14.19 | 0.056 |
