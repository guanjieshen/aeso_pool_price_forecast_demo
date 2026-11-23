# ML: HMM + Prophet + Monte Carlo ensemble, walk-forward backtest of the champion, business value

Exported 2026-11-23 19:23 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `forecast` (job `aeso-hourly`)

Job run `362081059053813` · task run `434030294808643` · **SUCCESS** · 54s · full output `evidence/raw/aeso-hourly__forecast.md` (local)

```text
History: 7835 settled hours, 2026-01-01 00:00:00 .. 2026-11-23 11:00:00 MPT
Forecast window: 2026-11-23 12:00:00 .. 2026-11-24 11:00:00 MPT (24 hours)

Champion: energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble v7 config {"fundamentals_gate": [1000, 2500], "n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "regressors": ["wind_solar_mw"], "weight_high": 1.0, "weight_low": 0.7}


HMM regimes (sorted by mean):
regime  mean_cad_mwh  std_cad_mwh  share_of_hours_pct  p_stay_1h
   Low          7.63         6.65                44.3      0.943
Normal         27.39         8.85                46.1      0.892
 Spike        178.37       225.71                 9.6      0.753

Transition matrix (rows = from, cols = to):
          Low  Normal  Spike
Low     0.943   0.057  0.000
Normal  0.055   0.892  0.054
Spike   0.000   0.247  0.753

Current regime: Normal
Prophet vs Monte Carlo gap: before 19.19 -> after convergence 6.09 CAD/MWh

forecast_datetime_mpt  hour_ending  prophet_forecast_price  prophet_regime_price  mc_p10_price  mc_p90_price  mc_seasonal_p50_price  ensemble_forecast_price forecast_regime  p_spike
  2026-11-23 12:00:00           13                   13.14                 13.37         12.07         39.45                  24.69                    14.60          Normal     0.04
  2026-11-23 13:00:00           14                   23.88                 17.00          7.66         39.14                  24.28                    18.49          Normal     0.09
  2026-11-23 14:00:00           15                   27.68                 18.32          8.59         48.62                  25.66                    20.45          Normal     0.11
  2026-11-23 15:00:00           16                   32.36                 19.63          5.91         43.67                  24.98                    21.23          Normal     0.11
  2026-11-23 16:00:00           17                   43.98                 22.07          3.93         45.05                  24.40                    22.77          Normal     0.12
  2026-11-23 17:00:00           18                   57.73                 23.45          5.43         49.82                  27.24                    24.58          Normal     0.12
  2026-11-23 18:00:00           19                   67.09                 22.60          3.82         44.09                  25.76                    23.55          Normal     0.11
  2026-11-23 19:00:00           20                   70.86                 21.48          2.69         52.42                  24.88                    22.50          Normal     0.13
  2026-11-23 20:00:00           21                   64.83                 20.13          2.93         53.39                  27.62                    22.38          Normal     0.14
  2026-11-23 21:00:00           22                   50.01                 18.51          3.24         54.77                  25.36                    20.56          Normal     0.14
  2026-11-23 22:00:00           23                   32.12                 16.54          3.08         44.97                  23.54                    18.64          Normal     0.12
  2026-11-23 23:00:00           24                   19.12                 14.94          1.51         42.95                  20.28                    16.54          Normal     0.11
  2026-11-24 00:00:00            1                   15.06                 
```

## Task `business_value` (job `aeso-evaluate-challenger`)

Job run `141830568499861` · task run `297088278921311` · **SUCCESS** · 17s · full output `evidence/raw/aeso-evaluate-challenger__business_value.md` (local)

```text
settled_hours_2026: 7,835.00
avg_price_cad_mwh: 33.72
top5pct_hours: 392.00
top5pct_cost_share_pct: 43.54
hours_above_150_pct: 2.55
cost_share_above_150_pct: 35.76
max_price_cad_mwh: 999.99
Perfect foresight, 4h/day, 1 MW: $115,776 over 325 days ($356.23/MW/day)

Backtest days: 2026-10-18, 2026-10-19, 2026-10-20, 2026-10-21, 2026-10-22, 2026-10-23, 2026-10-24, 2026-10-25, 2026-10-26, 2026-10-27, 2026-10-28, 2026-10-29, 2026-10-30, 2026-10-31
         strategy  days  savings_cad_per_mw_day  capture_rate_pct  annualized_cad_at_5mw  annualized_cad_at_10mw  annualized_cad_at_20mw
perfect_foresight    14                   451.6             100.0               824179.1               1648358.2               3296716.5
         ensemble    14                   362.8              80.3               662175.2               1324350.4               2648700.7
    aeso_forecast    14                   411.1              91.0               750346.1               1500692.3               3001384.6
  naive_yesterday    14                   103.7              23.0               189246.0                378492.0                756983.9
   prophet_regime    14                   362.9              80.4               662263.8               1324527.6               2649055.3
      mc_seasonal    14                   -29.9              -6.6               -54493.2               -108986.4               -217972.8

Indicative 2026-to-date value (ceiling $115,776/MW x capture rate):
         strategy  scenario_mw  capture_rate_pct  indicative_ytd_value_cad
perfect_foresight            5             100.0                  578877.8
perfect_foresight           10             100.0                 1157755.5
perfect_foresight           20             100.0                 2315511.0
         ensemble            5              80.3                  465091.2
         ensemble           10              80.3                  930182.4
         ensemble           20              80.3                 1860364.9
   prophet_regime            5              80.4                  465153.5
   prophet_regime           10              80.4                  930307.0
   prophet_regime           20              80.4                 1860613.9

Wrote 36 rows to energy_canada_demos_catalog.aeso_price_forecast.aeso_business_value
```

## Query: Latest backtest leaderboard (current @champion, same 14 days for every series)

| model_name | model_type | mae | rmse | mape_pct | capture_pct | n_days | champion_version |
|---|---|---|---|---|---|---|---|
| aeso_forecast | baseline | 16.24 | 55.3 | 21.5 | 91.0 | 14 | 7 |
| ensemble | model | 27.37 | 78.13 | 36.1 | 80.3 | 14 | 7 |
| prophet_regime | model | 30.36 | 109.05 | 28.7 | 80.4 | 14 | 7 |
| mc_seasonal | model | 37.25 | 113.96 | 45.7 | -6.6 | 14 | 7 |
| mc | model | 37.33 | 114.26 | 45.6 | -29.2 | 14 | 7 |
| prophet | model | 44.53 | 99.8 | 102.4 | 69.6 | 14 | 7 |
| naive_yesterday | baseline | 59.85 | 153.73 | 124.5 | 23.0 | 14 | 7 |

## Query: Business value (latest run)

| metric | strategy | scenario_mw | value |
|---|---|---|---|
| avg_price_cad_mwh |  |  | 33.72 |
| cost_share_above_150_pct |  |  | 35.76 |
| hours_above_150_pct |  |  | 2.55 |
| max_price_cad_mwh |  |  | 999.99 |
| perfect_foresight_days |  |  | 325.0 |
| perfect_foresight_shift_cad_per_mw_ytd |  |  | 115775.55 |
| settled_hours_2026 |  |  | 7835.0 |
| top5pct_cost_share_pct |  |  | 43.54 |
| top5pct_hours |  |  | 392.0 |
| capture_rate_pct | aeso_forecast | 1.0 | 91.04 |
| capture_rate_pct | ensemble | 1.0 | 80.34 |
| indicative_ytd_value_cad | ensemble | 10.0 | 930182.45 |
| capture_rate_pct | mc_seasonal | 1.0 | -6.61 |
| capture_rate_pct | naive_yesterday | 1.0 | 22.96 |
| capture_rate_pct | perfect_foresight | 1.0 | 100.0 |
| indicative_ytd_value_cad | perfect_foresight | 10.0 | 1157755.5 |
| capture_rate_pct | prophet_regime | 1.0 | 80.35 |
| indicative_ytd_value_cad | prophet_regime | 10.0 | 930306.97 |
