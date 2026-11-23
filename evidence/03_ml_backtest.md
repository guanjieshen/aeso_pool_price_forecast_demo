# ML: HMM + Prophet + Monte Carlo ensemble, walk-forward backtest of the champion, business value

Exported 2026-11-23 16:06 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `forecast` (job `aeso-hourly`)

Job run `1062095509219844` · task run `386289996421481` · **SUCCESS** · 55s · full output `evidence/raw/aeso-hourly__forecast.md` (local)

```text
History: 7832 settled hours, 2026-01-01 00:00:00 .. 2026-11-23 08:00:00 MPT
Forecast window: 2026-11-23 09:00:00 .. 2026-11-24 08:00:00 MPT (24 hours)

Champion: energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble v5 config {"n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "weight_high": 1.0, "weight_low": 0.7}


HMM regimes (sorted by mean):
regime  mean_cad_mwh  std_cad_mwh  share_of_hours_pct  p_stay_1h
   Low          7.64         6.66                44.6      0.943
Normal         27.41         8.85                45.8      0.892
 Spike        178.51       225.79                 9.6      0.753

Transition matrix (rows = from, cols = to):
          Low  Normal  Spike
Low     0.943   0.057  0.000
Normal  0.055   0.892  0.054
Spike   0.000   0.247  0.753

Current regime: Normal
Prophet vs Monte Carlo gap: before 18.09 -> after convergence 6.58 CAD/MWh

forecast_datetime_mpt  hour_ending  prophet_forecast_price  prophet_regime_price  mc_p10_price  mc_p90_price  mc_seasonal_p50_price  ensemble_forecast_price forecast_regime  p_spike
  2026-11-23 09:00:00           10                   10.19                 12.03         12.09         39.48                  25.50                    13.49          Normal     0.04
  2026-11-23 10:00:00           11                    4.52                 10.57          7.67         39.17                  24.66                    13.45          Normal     0.09
  2026-11-23 11:00:00           12                    4.83                 10.75          8.60         48.65                  25.55                    15.06          Normal     0.11
  2026-11-23 12:00:00           13                   11.03                 12.58          5.92         43.70                  23.54                    15.87          Normal     0.11
  2026-11-23 13:00:00           14                   17.77                 14.66          3.95         45.08                  23.41                    17.28          Normal     0.12
  2026-11-23 14:00:00           15                   21.79                 16.04          5.44         49.85                  24.72                    18.65          Normal     0.12
  2026-11-23 15:00:00           16                   28.33                 18.08          3.84         44.12                  23.67                    19.76          Normal     0.11
  2026-11-23 16:00:00           17                   41.13                 21.02          2.69         52.46                  22.22                    21.38          Normal     0.13
  2026-11-23 17:00:00           18                   55.48                 22.68          2.93         53.48                  25.40                    23.50          Normal     0.14
  2026-11-23 18:00:00           19                   64.82                 21.85          3.25         54.81                  24.58                    22.67          Normal     0.14
  2026-11-23 19:00:00           20                   68.55                 20.70          3.08         45.00                  25.17                    22.04          Normal     0.12
  2026-11-23 20:00:00           21                   62.69                 19.37          1.51         42.98                  24.89                    21.03          Normal     0.11
  2026-11-23 21:00:00           22                   47.27                 17.46          2.58         43.94                  23.72            
```

## Task `business_value` (job `aeso-evaluate-challenger`)

Job run `532658459632633` · task run `866687487334782` · **SUCCESS** · 17s · full output `evidence/raw/aeso-evaluate-challenger__business_value.md` (local)

```text
settled_hours_2026: 7,832.00
avg_price_cad_mwh: 33.73
top5pct_hours: 392.00
top5pct_cost_share_pct: 43.55
hours_above_150_pct: 2.55
cost_share_above_150_pct: 35.77
max_price_cad_mwh: 999.99
Perfect foresight, 4h/day, 1 MW: $115,776 over 325 days ($356.23/MW/day)

Backtest days: 2026-11-09, 2026-11-10, 2026-11-11, 2026-11-12, 2026-11-13, 2026-11-14, 2026-11-15, 2026-11-16, 2026-11-17, 2026-11-18, 2026-11-19, 2026-11-20, 2026-11-21, 2026-11-22
         strategy  days  savings_cad_per_mw_day  capture_rate_pct  annualized_cad_at_5mw  annualized_cad_at_10mw  annualized_cad_at_20mw
perfect_foresight    14                   157.6             100.0               287618.7                575237.4               1150474.8
         ensemble    14                   142.2              90.2               259529.3                519058.7               1038117.4
    aeso_forecast    14                   147.4              93.5               269036.3                538072.6               1076145.1
  naive_yesterday    14                    -6.3              -4.0               -11454.5                -22909.0                -45817.9
   prophet_regime    14                   142.7              90.6               260440.5                520881.1               1041762.1
      mc_seasonal    14                    25.3              16.1                46172.5                 92345.0                184690.0

Indicative 2026-to-date value (ceiling $115,776/MW x capture rate):
         strategy  scenario_mw  capture_rate_pct  indicative_ytd_value_cad
perfect_foresight            5             100.0                  578877.8
perfect_foresight           10             100.0                 1157755.5
perfect_foresight           20             100.0                 2315511.0
         ensemble            5              90.2                  522343.5
         ensemble           10              90.2                 1044687.0
         ensemble           20              90.2                 2089374.0
   prophet_regime            5              90.6                  524177.4
   prophet_regime           10              90.6                 1048354.9
   prophet_regime           20              90.6                 2096709.8

Wrote 36 rows to energy_canada_demos_catalog.aeso_price_forecast.aeso_business_value
```

## Query: Latest backtest leaderboard (current @champion, same 14 days for every series)

| model_name | model_type | mae | rmse | mape_pct | capture_pct | n_days | champion_version |
|---|---|---|---|---|---|---|---|
| aeso_forecast | baseline | 3.86 | 14.39 | 12.4 | 93.5 | 14 | 5 |
| ensemble | model | 6.61 | 18.28 | 20.3 | 90.2 | 14 | 5 |
| prophet_regime | model | 6.73 | 17.53 | 21.9 | 90.6 | 14 | 5 |
| mc_seasonal | model | 11.27 | 22.3 | 42.0 | 16.1 | 14 | 5 |
| mc | model | 11.47 | 22.64 | 41.5 | -9.2 | 14 | 5 |
| naive_yesterday | baseline | 18.2 | 30.14 | 75.4 | -4.0 | 14 | 5 |
| prophet | model | 25.01 | 34.41 | 109.4 | 74.6 | 14 | 5 |

## Query: Business value (latest run)

| metric | strategy | scenario_mw | value |
|---|---|---|---|
| avg_price_cad_mwh |  |  | 33.73 |
| cost_share_above_150_pct |  |  | 35.77 |
| hours_above_150_pct |  |  | 2.55 |
| max_price_cad_mwh |  |  | 999.99 |
| perfect_foresight_days |  |  | 325.0 |
| perfect_foresight_shift_cad_per_mw_ytd |  |  | 115775.55 |
| settled_hours_2026 |  |  | 7832.0 |
| top5pct_cost_share_pct |  |  | 43.55 |
| top5pct_hours |  |  | 392.0 |
| capture_rate_pct | aeso_forecast | 1.0 | 93.54 |
| capture_rate_pct | ensemble | 1.0 | 90.23 |
| indicative_ytd_value_cad | ensemble | 10.0 | 1044687.02 |
| capture_rate_pct | mc_seasonal | 1.0 | 16.05 |
| capture_rate_pct | naive_yesterday | 1.0 | -3.98 |
| capture_rate_pct | perfect_foresight | 1.0 | 100.0 |
| indicative_ytd_value_cad | perfect_foresight | 10.0 | 1157755.5 |
| capture_rate_pct | prophet_regime | 1.0 | 90.55 |
| indicative_ytd_value_cad | prophet_regime | 10.0 | 1048354.88 |
