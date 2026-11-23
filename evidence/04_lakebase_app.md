# Lakebase serving + AESO Market Pulse app (deployed)

Exported 2026-11-23 16:06 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `lakebase_sync` (job `aeso-hourly`)

Job run `1062095509219844` · task run `1100316728163800` · **SUCCESS** · 58s · full output `evidence/raw/aeso-hourly__lakebase_sync.md` (local)

```text
forecast_latest_synced: refresh COMPLETED
pool_price_hourly_synced: refresh COMPLETED

forecast_latest_synced: Lakebase rows 24 | Delta source rows 24 | match True
pool_price_hourly_synced: Lakebase rows 7835 | Delta source rows 7835 | match True

Copied 3 ops actions to energy_canada_demos_catalog.aeso_price_forecast.ops_actions_history:
 action_id                 created_at action_type    window_start_mpt      window_end_mpt   mw  threshold                            note
         1 2026-11-22 18:08:43.915103 spike_alert 2026-11-22 16:00:00 2026-11-22 20:00:00  NaN       0.10                      local test
         2 2026-11-22 18:08:45.208644  load_shift 2026-11-22 17:00:00 2026-11-22 20:00:00 10.0        NaN                            None
         3 2026-11-22 18:14:59.940770 spike_alert 2026-11-22 17:00:00 2026-11-22 21:00:00  NaN       0.12 energy desk: watch evening peak
```

## Query: Ops actions copied back to Delta (written by the app into Lakebase)

| action_id | action_type | window_start_mpt | window_end_mpt | mw | threshold | note |
|---|---|---|---|---|---|---|
| 1 | spike_alert | 2026-11-22T16:00:00.000Z | 2026-11-22T20:00:00.000Z |  | 0.1 | local test |
| 2 | load_shift | 2026-11-22T17:00:00.000Z | 2026-11-22T20:00:00.000Z | 10.0 |  |  |
| 3 | spike_alert | 2026-11-22T17:00:00.000Z | 2026-11-22T21:00:00.000Z |  | 0.12 | energy desk: watch evening peak |

## Query: Synced tables registered in Unity Catalog

| table_name | table_type | comment |
|---|---|---|
| pool_price_hourly_synced | FOREIGN | Database table synced from another UC table |
| forecast_latest_synced | FOREIGN | Database table synced from another UC table |

## Deployed app API (what the 9 cards and the ops form render)

`GET https://aeso-market-pulse-7474654566745717.aws.databricksapps.com/api/dashboard` -> HTTP 200 in 1.7s; card errors: none

| Feed | Source | Rows | First row |
|---|---|---|---|
| prices | Lakebase | 48 | `{"ts": "2026-11-21 09:00", "pool_price": 22.16, "rolling_30day_avg": 36.59}` |
| forecast | Lakebase | 24 | `{"ts": "2026-11-23 09:00", "hour_ending": 10, "prophet_forecast_price": 10.18895594225766, "mc_p10_price": 12.08823421922342, "mc_p90_price": 39.48096651192209, "ensemble_forecast_price": 13.48909378835539, "forecast_regime": "Nor` |
| wind | SQL warehouse | 169 | `{"ts": "2026-11-16 08:00", "pool_price": 15.37, "actual_mw": 3186.7927712999995, "most_likely_mw": null}` |
| heatmap | SQL warehouse | 168 | `{"dow": 1, "hour": 0, "avg_price": 17.99}` |
| backtest | SQL warehouse | 24 | `{"ts": "2026-11-22 00:00", "hour_ending": 1, "actual": 34.76, "prophet_regime": 35.52837505735482, "mc_seasonal": 26.373155926326348, "ensemble": 34.52736763229451, "aeso_forecast": 35.38, "naive_yesterday": 17.32, "cutoff_date": ` |
| leaderboard | SQL warehouse | 3 | `{"model_name": "aeso_forecast", "model_type": "baseline", "mae_cad_mwh": 3.86, "rmse_cad_mwh": 14.39, "mape_pct": 12.4, "n_days": 14}` |
| actions | Lakebase | 3 | `{"action_id": 3, "created_utc": "2026-11-22 18:14", "created_by": "<user>", "action_type": "spike_alert", "window_start": "2026-11-22 17:00", "window_end": "2026-11-22 21:00", "mw": null, "threshold": 0.12, "n` |
