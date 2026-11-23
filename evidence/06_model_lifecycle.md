# Self-improving models: weekly challenger, model update trigger, gated promotion

Exported 2026-11-23 19:23 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `train_challenger` (job `aeso-weekly-retrain`)

Job run `779731612988091` · task run `272219357728378` · **SUCCESS** · 111s · full output `evidence/raw/aeso-weekly-retrain__train_challenger.md` (local)

```text
Champion v5: {"fundamentals_gate": null, "n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "regressors": ["wind_solar_mw"], "weight_high": 1.0, "weight_low": 0.7}
Tuning window: 2026-10-11 .. 2026-10-17 (7 days)


Tuning results (ensemble per candidate):
             candidate  capture_rate_pct  mae_cad_mwh  rmse_cad_mwh
     cps0.005_w0.7-1.0             90.86        24.50         88.11
cushion_gate_1000-2500             90.78        24.61         84.54
              champion             90.78        25.39         88.74
     cps0.001_w0.7-1.0             90.78        25.39         88.74
    cps0.0005_w0.7-1.0             90.78        25.84         89.06
     cps0.001_w0.5-0.9             90.07        26.22         89.51
    cps0.0005_w0.5-0.9             90.07        26.52         89.74
     cps0.005_w0.5-0.9             90.02        25.57         89.04
cushion_gate_1500-3000             89.73        23.90         81.41
     cps0.005_w0.3-0.7             86.88        26.27         89.92
     cps0.001_w0.3-0.7             86.88        26.82         90.23
    cps0.0005_w0.3-0.7             86.88        27.07         90.39

Challenger recipe cushion_gate_1000-2500: tuning capture 90.8% vs champion 90.8%, MAE 24.61 vs 25.39

🔗 Created version '7' of model 'energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble': https://fevm-energy-canada-demos.cloud.databricks.com/explore/data/models/energy_canada_demos_catalog/aeso_price_forecast/pool_price_ensemble/version/7?o=7474654566745717

Registered energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble v7 as @challenger (cushion_gate_1000-2500); the evaluation job will compare it with @champion v5.
```

## Task `evaluate_and_promote` (job `aeso-evaluate-challenger`)

Job run `141830568499861` · task run `786018014136328` · **SUCCESS** · 127s · full output `evidence/raw/aeso-evaluate-challenger__evaluate_and_promote.md` (local)

```text
Trigger events: [{'full_name': 'energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble', 'version': 7, 'alias_name': 'challenger'}]
Champion   v5: {"fundamentals_gate": null, "n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "regressors": ["wind_solar_mw"], "weight_high": 1.0, "weight_low": 0.7}
Challenger v7: {"fundamentals_gate": [1000, 2500], "n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "regressors": ["wind_solar_mw"], "weight_high": 1.0, "weight_low": 0.7}

Evaluation window 2026-10-18 .. 2026-10-31 (336 hours):
          model_name model_type  capture_rate_pct  mae_cad_mwh  rmse_cad_mwh  mape_pct
       aeso_forecast   baseline             91.04        16.24         55.30     21.52
ensemble__challenger      model             80.34        27.37         78.13     36.14
  ensemble__champion      model             73.06        31.79        110.44     29.96
     naive_yesterday   baseline             22.96        59.85        153.73    124.47
PROMOTE: capture 80.3% vs 73.1% (needs +1.0 pp: yes); MAE 27.37 vs 31.79 (guard x1.05: ok)

@champion is now v7. Promotion history:
       evaluated_at champion_version challenger_version      decision  champ_capture  chall_capture  champ_mae  chall_mae
2026-11-23 15:57:35                4                  5      promoted           72.0           90.2       7.79       6.61
2026-11-23 18:50:24                5                  6 kept_champion           73.1           72.5      31.79      30.50
2026-11-23 19:13:49                5                  7      promoted           73.1           80.3      31.79      27.37
```

## Query: Promotion decisions

| evaluated_at | champion_version | challenger_version | decision | champ_capture | chall_capture | champ_mae | chall_mae | eval_start | eval_end |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-23T15:57:35.000Z | 4 | 5 | promoted | 72.0 | 90.2 | 7.79 | 6.61 | 2026-11-09 | 2026-11-22 |
| 2026-11-23T18:50:24.000Z | 5 | 6 | kept_champion | 73.1 | 72.5 | 31.79 | 30.5 | 2026-10-18 | 2026-10-31 |
| 2026-11-23T19:13:49.000Z | 5 | 7 | promoted | 73.1 | 80.3 | 31.79 | 27.37 | 2026-10-18 | 2026-10-31 |

## Query: Hourly forecasts archived per champion version (live accuracy input)

| champion_version | runs | forecast_hours | first_run_utc | last_run_utc |
|---|---|---|---|---|
| 4 | 1 | 24 | 2026-11-23T15:51:44.000Z | 2026-11-23T15:51:44.000Z |
| 5 | 6 | 144 | 2026-11-23T16:02:32.000Z | 2026-11-23T18:36:17.000Z |
| 7 | 1 | 24 | 2026-11-23T19:18:57.000Z | 2026-11-23T19:18:57.000Z |
