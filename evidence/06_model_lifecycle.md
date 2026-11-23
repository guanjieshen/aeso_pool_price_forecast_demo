# Self-improving models: weekly challenger, model update trigger, gated promotion

Exported 2026-11-23 16:06 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `train_challenger` (job `aeso-weekly-retrain`)

Job run `144570702045405` · task run `661338974933044` · **SUCCESS** · 102s · full output `evidence/raw/aeso-weekly-retrain__train_challenger.md` (local)

```text
Champion v4: {"n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "weight_high": 0.7, "weight_low": 0.3}
Tuning window: 2026-11-02 .. 2026-11-08 (7 days)


Tuning results (ensemble per candidate):
         candidate  capture_rate_pct  mae_cad_mwh  rmse_cad_mwh
 cps0.001_w0.7-1.0             88.42         4.76          8.81
 cps0.005_w0.7-1.0             88.42         5.03          8.61
cps0.0005_w0.7-1.0             87.17         5.18          9.25
 cps0.001_w0.5-0.9             80.47         5.81          9.98
cps0.0005_w0.5-0.9             80.32         6.08         10.25
 cps0.005_w0.5-0.9             74.49         5.86          9.84
cps0.0005_w0.3-0.7             74.21         7.14         11.28
 cps0.005_w0.3-0.7             66.86         6.96         11.01
          champion             65.73         6.97         11.10
 cps0.001_w0.3-0.7             65.73         6.97         11.10

Challenger recipe cps0.001_w0.7-1.0: tuning capture 88.4% vs champion 65.7%, MAE 4.76 vs 6.97

🔗 Created version '5' of model 'energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble': https://fevm-energy-canada-demos.cloud.databricks.com/explore/data/models/energy_canada_demos_catalog/aeso_price_forecast/pool_price_ensemble/version/5?o=7474654566745717

Registered energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble v5 as @challenger (cps0.001_w0.7-1.0); the evaluation job will compare it with @champion v4.
```

## Task `evaluate_and_promote` (job `aeso-evaluate-challenger`)

Job run `532658459632633` · task run `172665350063897` · **SUCCESS** · 116s · full output `evidence/raw/aeso-evaluate-challenger__evaluate_and_promote.md` (local)

```text
Trigger events: [{'full_name': 'energy_canada_demos_catalog.aeso_price_forecast.pool_price_ensemble', 'version': 5, 'alias_name': 'challenger'}]
Champion   v4: {"n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "weight_high": 0.7, "weight_low": 0.3}
Challenger v5: {"n_paths": 500, "prophet_cps": 0.05, "regime_cps": 0.001, "weight_high": 1.0, "weight_low": 0.7}

Evaluation window 2026-11-09 .. 2026-11-22 (336 hours):
          model_name model_type  capture_rate_pct  mae_cad_mwh  rmse_cad_mwh  mape_pct
       aeso_forecast   baseline             93.54         3.86         14.39     12.36
ensemble__challenger      model             90.23         6.61         18.28     20.27
  ensemble__champion      model             71.97         7.79         19.86     24.98
     naive_yesterday   baseline             -3.98        18.20         30.14     75.37
PROMOTE: capture 90.2% vs 72.0% (needs +1.0 pp: yes); MAE 6.61 vs 7.79 (guard x1.05: ok)

@champion is now v5. Promotion history:
       evaluated_at champion_version challenger_version decision  champ_capture  chall_capture  champ_mae  chall_mae
2026-11-23 15:57:35                4                  5 promoted           72.0           90.2       7.79       6.61
```

## Query: Promotion decisions

| evaluated_at | champion_version | challenger_version | decision | champ_capture | chall_capture | champ_mae | chall_mae | eval_start | eval_end |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-23T15:57:35.000Z | 4 | 5 | promoted | 72.0 | 90.2 | 7.79 | 6.61 | 2026-11-09 | 2026-11-22 |

## Query: Hourly forecasts archived per champion version (live accuracy input)

| champion_version | runs | forecast_hours | first_run_utc | last_run_utc |
|---|---|---|---|---|
| 4 | 1 | 24 | 2026-11-23T15:51:44.000Z | 2026-11-23T15:51:44.000Z |
| 5 | 1 | 24 | 2026-11-23T16:02:32.000Z | 2026-11-23T16:02:32.000Z |
