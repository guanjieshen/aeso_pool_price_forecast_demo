# Genie: the space, the benchmark, the Genie One links

## The Genie space

`AESO Market Pulse Genie`, deployed by the bundle from `src/genie/aeso_market_pulse.geniespace.json` (`resources/serving.yml`). It covers 8 tables: gold features, pool price, wind/solar, forecast, backtest metrics and detail, business value, ops actions.

| Part | What it carries |
| --- | --- |
| Text instructions | Units, Mountain Time, hour-ending, `DAYOFWEEK` 1 = Sunday, settled-only filters, "spike" (price > $150) vs "Spike regime" (HMM), latest-run filters, the AESO-forecast caveat, assumptions in business value |
| Example SQL | 6 trusted queries: 24h forecast, leaderboard, hourly profile, wind bands, spike cost share, fired alerts |
| Join | `aeso_pool_price.begin_datetime_mpt = silver_wind_solar_hourly.forecast_transaction_date` (one to one) |
| Sample questions | 6 starter questions shown in the UI |

**Editing it:** change the JSON (IDs are 32 lowercase hex characters, lists sorted by ID, tables sorted by identifier; join specs need a `--rt=...--` relationship line), then `databricks bundle deploy`. Table and column **comments in Unity Catalog** are part of what Genie reads, so keep them accurate.

## The benchmark

`scripts/genie_benchmark.py` asks 8 questions through the Genie conversation API and checks each answer against ground-truth SQL written by hand (numbers within 1%, text found). It writes `evidence/05_genie_benchmark.md` with the score and the SQL Genie generated. Rerun it after any change to the space or to a table Genie reads.

## Genie One deep links (screen-aware)

Each app card's **ANALYZE WITH GENIE** link opens Genie One with a question already typed:

`https://<host>/one/chat?o=<workspace-id>&q=<url-encoded prompt>`

`genieLink(cardId, prompt)` in `app/static/index.html` builds it. Prompts carry what is on screen (the price, the hour, the spike hours, the backtest day) and always end with the schema, units and time convention. There is no custom chat UI to maintain, and people get the native, governed Genie experience. The pattern is a field tip, not a documented API. Verified by hand on 2026-11-22 (the link opens Genie One with the question filled in); check again after a Databricks release.
