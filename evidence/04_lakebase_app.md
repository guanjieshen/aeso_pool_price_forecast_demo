# Lakebase serving + AESO Market Pulse app (deployed)

Exported 2026-11-23 23:25 UTC by `scripts/export_evidence.py` from the live workspace. Full cell output regenerates into the git-ignored `evidence/raw/`.

## Task `lakebase_sync` (job `aeso-hourly`)

Job run `398610988453239` · task run `958091964533914` · **SUCCESS** · 58s · full output `evidence/raw/aeso-hourly__lakebase_sync.md` (local)

```text
forecast_latest_synced: refresh COMPLETED
pool_price_hourly_synced: refresh COMPLETED

forecast_latest_synced: Lakebase rows 24 | Delta source rows 24 | match True
pool_price_hourly_synced: Lakebase rows 7843 | Delta source rows 7843 | match True

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
| forecast_latest_synced | FOREIGN |  |

## Deployed app API (what the 9 cards and the ops form render)

`GET https://aeso-market-pulse-7474654566745717.aws.databricksapps.com/api/dashboard` -> HTTP 200 in 1.7s; card errors: none

| Feed | Source | Rows | First row |
|---|---|---|---|
| prices | Lakebase | 48 | `{"ts": "2026-11-21 17:00", "pool_price": 35.35, "rolling_30day_avg": 36.06}` |
| forecast | Lakebase | 24 | `{"ts": "2026-11-23 17:00", "hour_ending": 18, "prophet_forecast_price": 66.83613135414106, "mc_p10_price": 12.133760407613826, "mc_p90_price": 39.41166485901793, "ensemble_forecast_price": 27.094695784708748, "forecast_regime": "N` |
| wind | SQL warehouse | 169 | `{"ts": "2026-11-16 16:00", "pool_price": 57.54, "actual_mw": 1391.2444242000001, "most_likely_mw": null}` |
| heatmap | SQL warehouse | 168 | `{"dow": 1, "hour": 0, "avg_price": 17.99}` |
| backtest | SQL warehouse | 24 | `{"ts": "2026-10-31 00:00", "hour_ending": 1, "actual": 56.35, "prophet_regime": 31.635434032868076, "mc_seasonal": 26.497943387634926, "ensemble": 31.06376803374425, "aeso_forecast": 34.42, "naive_yesterday": 37.99, "cutoff_date":` |
| leaderboard | SQL warehouse | 3 | `{"model_name": "aeso_forecast", "model_type": "baseline", "mae_cad_mwh": 16.24, "rmse_cad_mwh": 55.3, "mape_pct": 21.5, "n_days": 14}` |
| accuracy | SQL warehouse | 16 | `{"window_label": "2026-10-18..2026-10-31", "model_name": "aeso_forecast", "capture_pct": 91.0, "mae": 16.24, "n_days": 14, "champion": "v7"}` |
| outages | SQL warehouse | 43 | `{"report": "daily", "period": "2026-11-23", "gas": 2457.0, "hydro": 362.0, "other": 220.0, "wind_solar": 193.0, "dispatchable": 3039.0, "snapshot_at": "2026-11-23 23:14:25"}` |
| actions | Lakebase | 3 | `{"action_id": 3, "created_utc": "2026-11-22 18:14", "created_by": "<user>", "action_type": "spike_alert", "window_start": "2026-11-22 17:00", "window_end": "2026-11-22 21:00", "mw": null, "threshold": 0.12, "n` |
