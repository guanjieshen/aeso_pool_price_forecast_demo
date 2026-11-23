# Data engineering and governance

How the ingest notebooks, the declarative pipeline and the governance task work, and what to watch for. Rules for the whole repo are in [AGENTS.md](../AGENTS.md).

## The flow

| Step | File | Writes | Key | Logic |
| --- | --- | --- | --- | --- |
| 1 | `src/ingest/pool_price_incremental.py` | `aeso_pool_price` | `begin_datetime_utc` | Max loaded MPT date (or **2026-01-01** if empty) to today, 31-day windows, MERGE. Exits early on zero rows |
| 2 | `src/ingest/wind_solar_forecast.py` | `aeso_wind_solar_forecast` | `forecast_transaction_date` | Downloads the long-term CSV, `csv` module, empty strings to null, MERGE. Keeps a recorded actual if a later file drops it |
| 3 | `src/ingest/wind_solar_metered.py` | `aeso_wind_solar_metered` | `begin_datetime_utc` | Wind and solar asset IDs from the supply/demand report, hourly metered MWh per asset, summed per hour. Re-pulls the last 5 days (revisions); `full_refresh=true` re-pulls everything |
| 3b | `src/ingest/supply_demand.py` | `aeso_supply_demand_hourly`, `aeso_wind_solar_published`, `aeso_fundamentals_snapshots` | `begin_datetime_utc` | Load (actual + AESO forecast), capability by fuel net of outages, intertie import ATC, from 2026-01-01 to 3 days ahead, MERGE. Reloads AESO's yearly published wind/solar forecast files. **Appends every forward hour as known now** (`snapshot_at`) to the snapshot archive. Runs after step 2 |
| 4 | `src/pipeline/transformations.py` | `silver_*`, `gold_price_features_hourly` | | Materialized views with expectations; see below |
| 5 | `src/governance/setup_uc.py` | tags, comments, grants | | Idempotent; runs last in both jobs |

Steps 1 to 3 run in parallel (3b after 2) in the `aeso_hourly` job at 20 past each hour (MPT), then 4, then the forecast, then 5.

## Silver and gold

- `silver_pool_price_hourly`: drops rows with no keys or a price outside **[0, 999.99]**; warns when AESO's forecast is missing. Adds `hour_ending` (AESO HE01 to HE24) and `day_of_week` (1 = Sunday).
- `silver_wind_solar_hourly`: an hourly spine from the first price hour to the last forecast hour. `actual_mw` = CSV actual, else metered. `regressor_mw` = actual, else the CSV's most likely forecast, else an hour-of-day x month average (`is_imputed = true`). `regressor_source` says which.
- `silver_supply_demand_hourly`: fundamentals per hour. `*_mw` = as last published; `*_dayahead_mw` = **as known before the hour's day began**: last snapshot taken before that midnight, else the published wind/solar file, else capability 24 hours earlier. `dayahead_source` says which.
- `gold_price_features_hourly`: one row per MPT hour: `y` (settled price, null for future hours), AESO forecast, `wind_solar_mw`, and the fundamentals: `supply_cushion_mw` (dispatchable available + wind/solar + import ATC - forecast load), `net_load_mw`, `load_mw`, `import_atc_mw`, and their `*_dayahead_mw` twins. This is the only table the model reads; backtests swap in the day-ahead twins for the test day.

## Governance

- **Governed tags** (the metastore enforces the values): `domain=operations`, `layer` (bronze/silver/gold), `classification=public`, `data_product` (data_engineering / analytics / machine_learning). Free-form: `subject_area=power_market`, `data_source`.
- **Comments** on every bronze column (units, time zone, key) and every pipeline table.
- **The secret** `aeso_api_key`: commented and checked through the UC REST API (Spark SQL secret DDL is not enabled here). Read access: the owner (the jobs run as the owner) and the app's service principal (`READ_SECRET`, granted by `scripts/grant_app_sp.py`).
- **App grants:** pass `app_service_principal` to the governance task; it grants `USE CATALOG`, `USE SCHEMA` and `SELECT` on every table in `TABLES`.

## Gotchas

See the list in [AGENTS.md](../AGENTS.md#gotchas-learned-the-hard-way): exclusive `endDate` on metered volumes and AIES capability, 10 asset IDs per call, `yyyyMMdd` dates on the intertie API, the checksum line at the end of AESO's yearly forecast files, governed tag values, secret DDL.
