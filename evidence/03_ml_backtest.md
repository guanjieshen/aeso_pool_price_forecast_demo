# ML: HMM + Prophet + Monte Carlo ensemble, walk-forward backtest, UC model

Exported 2026-11-22 19:11 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `backtest_and_register` (job `aeso-daily-backtest`)

Job run `411561968306788` · task run `352460623927743` · **SUCCESS** · 96s · full output `evidence/raw/aeso-daily-backtest__backtest_and_register.md` (local)

```text
History: 7811 settled hours, 2026-01-01 00:00:00 .. 2026-11-22 11:00:00 MPT
Forecast window: 2026-11-22 12:00:00 .. 2026-11-23 11:00:00 MPT (24 hours)

HMM regimes (sorted by mean):
regime  mean_cad_mwh  std_cad_mwh  share_of_hours_pct  p_stay_1h
   Low          7.69         6.68                44.8      0.944
Normal         27.52         8.89                45.7      0.891
 Spike        179.35       226.29                 9.5      0.752

Transition matrix (rows = from, cols = to):
          Low  Normal  Spike
Low     0.944   0.056  0.000
Normal  0.055   0.891  0.054
Spike   0.000   0.248  0.752

Current regime: Normal
Prophet vs Monte Carlo gap: before 24.50 -> after convergence 4.88 CAD/MWh

forecast_datetime_mpt  hour_ending  prophet_forecast_price  prophet_regime_price  mc_p10_price  mc_p90_price  mc_seasonal_p50_price  ensemble_forecast_price forecast_regime  p_spike
  2026-11-22 12:00:00           13                   59.90                 34.60         12.13         39.74                  24.97                    31.71          Normal     0.04
  2026-11-22 13:00:00           14                   59.38                 33.92          7.31         39.65                  24.51                    31.10          Normal     0.10
  2026-11-22 14:00:00           15                   58.93                 33.59          8.65         49.53                  25.93                    31.29          Normal     0.11
  2026-11-22 15:00:00           16                   60.74                 33.75          6.11         43.88                  25.05                    30.53          Normal     0.11
  2026-11-22 16:00:00           17                   70.16                 35.32          3.96         45.26                  24.44                    30.54          Normal     0.12
  2026-11-22 17:00:00           18                   83.08                 36.35          5.48         50.06                  27.42                    31.89          Normal     0.12
  2026-11-22 18:00:00           19                   90.97                 34.91          3.85         44.30                  26.05                    29.99          Normal     0.11
  2026-11-22 19:00:00           20                   94.30                 33.52          2.70         52.71                  25.00                    28.38          Normal     0.13
  2026-11-22 20:00:00           21                   87.33                 31.63          2.68         49.93                  27.37                    28.88          Normal     0.13
  2026-11-22 21:00:00           22                   70.14                 28.86          3.02         55.07                  25.13                    26.30          Normal     0.14
  2026-11-22 22:00:00           23                   49.78                 25.70          2.99         45.19                  23.58                    24.22          Normal     0.12
  2026-11-22 23:00:00           24                   34.94                 23.15          1.46         42.63                  20.38                    21.21          Normal     0.11
  2026-11-23 00:00:00            1                   27.20                 20.98          2.62         44.13                  20.08                    20.35          Normal     0.11
  2026-11-23 01:00:00            2                   24.67                 19.42          3.78         44.64                  20.48                  
```

## Task `business_value` (job `aeso-daily-backtest`)

Job run `411561968306788` · task run `890921778962887` · **SUCCESS** · 15s · full output `evidence/raw/aeso-daily-backtest__business_value.md` (local)

```text
settled_hours_2026: 7,811.00
avg_price_cad_mwh: 33.75
top5pct_hours: 391.00
top5pct_cost_share_pct: 43.59
hours_above_150_pct: 2.56
cost_share_above_150_pct: 35.84
max_price_cad_mwh: 999.99
Perfect foresight, 4h/day, 1 MW: $115,688 over 324 days ($357.06/MW/day)

Backtest days: 2026-11-17, 2026-11-18, 2026-11-19, 2026-11-20, 2026-11-21
         strategy  days  savings_cad_per_mw_day  capture_rate_pct  annualized_cad_at_5mw  annualized_cad_at_10mw  annualized_cad_at_20mw
perfect_foresight     5                   204.2             100.0               372654.0                745308.1               1490616.2
         ensemble     5                   131.7              64.5               240316.0                480632.0                961264.0
    aeso_forecast     5                   192.3              94.2               351009.6                702019.1               1404038.2
  naive_yesterday     5                   -30.9             -15.2               -56469.2               -112938.3               -225876.6
   prophet_regime     5                   192.6              94.3               351498.6                702997.3               1405994.6
      mc_seasonal     5                     3.6               1.8                 6537.1                 13074.3                 26148.6

Indicative 2026-to-date value (ceiling $115,688/MW x capture rate):
         strategy  scenario_mw  capture_rate_pct  indicative_ytd_value_cad
perfect_foresight            5             100.0                  578441.8
perfect_foresight           10             100.0                 1156883.7
perfect_foresight           20             100.0                 2313767.4
         ensemble            5              64.5                  373023.8
         ensemble           10              64.5                  746047.6
         ensemble           20              64.5                 1492095.2
   prophet_regime            5              94.3                  545604.0
   prophet_regime           10              94.3                 1091207.9
   prophet_regime           20              94.3                 2182415.9

Wrote 36 rows to energy_canada_demos_catalog.aeso_price_forecast.aeso_business_value
```

## Query: Latest backtest leaderboard

| model_name | model_type | mae | rmse | mape_pct | n_hours | n_days |
|---|---|---|---|---|---|---|
| aeso_forecast | baseline | 3.37 | 8.08 | 7.8 | 120 | 5 |
| ensemble | model | 9.7 | 23.63 | 18.5 | 120 | 5 |
| prophet_regime | model | 11.21 | 20.54 | 30.2 | 120 | 5 |
| mc_seasonal | model | 12.85 | 26.11 | 30.5 | 120 | 5 |
| mc | model | 13.31 | 27.04 | 31.7 | 120 | 5 |
| naive_yesterday | baseline | 21.9 | 34.3 | 68.5 | 120 | 5 |
| prophet | model | 34.91 | 43.36 | 123.9 | 120 | 5 |

## Query: Business value (latest run)

| metric | strategy | scenario_mw | value |
|---|---|---|---|
| avg_price_cad_mwh |  |  | 33.75 |
| cost_share_above_150_pct |  |  | 35.84 |
| hours_above_150_pct |  |  | 2.56 |
| max_price_cad_mwh |  |  | 999.99 |
| perfect_foresight_days |  |  | 324.0 |
| perfect_foresight_shift_cad_per_mw_ytd |  |  | 115688.37 |
| settled_hours_2026 |  |  | 7811.0 |
| top5pct_cost_share_pct |  |  | 43.59 |
| top5pct_hours |  |  | 391.0 |
| capture_rate_pct | aeso_forecast | 1.0 | 94.19 |
| capture_rate_pct | ensemble | 1.0 | 64.49 |
| indicative_ytd_value_cad | ensemble | 10.0 | 746047.61 |
| capture_rate_pct | mc_seasonal | 1.0 | 1.75 |
| capture_rate_pct | naive_yesterday | 1.0 | -15.15 |
| capture_rate_pct | perfect_foresight | 1.0 | 100.0 |
| indicative_ytd_value_cad | perfect_foresight | 10.0 | 1156883.7 |
| capture_rate_pct | prophet_regime | 1.0 | 94.32 |
| indicative_ytd_value_cad | prophet_regime | 10.0 | 1091207.94 |
