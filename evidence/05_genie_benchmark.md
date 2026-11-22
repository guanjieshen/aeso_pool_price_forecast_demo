# Genie benchmark: 8/8 correct

Space `01f1e6a1b931196f80593b589abbc529` (AESO Market Pulse Genie), run 2026-11-22 18:25 UTC by `scripts/genie_benchmark.py`. Ground truth comes from SQL written by hand; a question passes when every expected value appears in Genie's result (numbers within 1%).

| # | Question | Expected | Genie returned | Result |
|---|---|---|---|---|
| 1 | What was the average settled pool price in October 2026? | 51.33 | 51.33 | PASS |
| 2 | What was the highest pool price so far in 2026? | 999.99 | 999.99, 2026-05-25T20:00:00.000Z, 999.99, 2026-05-28T20:00:00.000Z | PASS |
| 3 | How many hours in 2026 settled above $150/MWh? | 200 | 200 | PASS |
| 4 | Which model (not a baseline) had the lowest MAE in the latest backtest, and what was its MAE? | ensemble, 9.7 | ensemble, 9.7 | PASS |
| 5 | What is the average ensemble forecast price over the next 24 hours? | 23.81 | 23.81 | PASS |
| 6 | Which hour-ending had the highest average pool price over the last 90 days? | 20 | 20, 110.58 | PASS |
| 7 | What was the average pool price in 2026 in hours when actual wind and solar generation was above 3,000 MW? | 6.73 | 6.73, 2234 | PASS |
| 8 | How many spike alerts have operators logged? | 2 | 2 | PASS |

## SQL Genie generated

**1. What was the average settled pool price in October 2026?**

```sql
SELECT ROUND(AVG(`pool_price`), 2) AS `avg_settled_pool_price_cad_mwh`
FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price`
WHERE `pool_price` IS NOT NULL
  AND `begin_datetime_mpt` >= TIMESTAMP('2026-10-01 00:00:00')
  AND `begin_datetime_mpt` < TIMESTAMP('2026-11-01 00:00:00')
```

**2. What was the highest pool price so far in 2026?**

```sql
WITH ranked_prices AS (
  SELECT
    `begin_datetime_mpt`,
    `pool_price`,
    RANK() OVER (ORDER BY `pool_price` DESC) AS `price_rank`
  FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price`
  WHERE `pool_price` IS NOT NULL
    AND `begin_datetime_mpt` IS NOT NULL
    AND `begin_datetime_mpt` >= TIMESTAMP('2026-01-01 00:00:00')
    AND `begin_datetime_mpt` < TIMESTAMP('2027-01-01 00:00:00')
)
SELECT
  ROUND(`pool_price`, 2) AS `highest_pool_price_cad_mwh`,
  `begin_datetime_mpt`
FROM ranked_prices
WHERE `price_rank` <= 1
ORDER BY `begin_datetime_mpt`
```

**3. How many hours in 2026 settled above $150/MWh?**

```sql
SELECT COUNT(*) AS `hours_above_150`
FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price`
WHERE `pool_price` IS NOT NULL
  AND `pool_price` > 150
  AND `begin_datetime_mpt` >= TIMESTAMP('2026-01-01 00:00:00')
  AND `begin_datetime_mpt` < TIMESTAMP('2027-01-01 00:00:00')
```

**4. Which model (not a baseline) had the lowest MAE in the latest backtest, and what was its MAE?**

```sql
WITH `latest_models` AS (
  SELECT
    `model_name`,
    `mae_cad_mwh`,
    RANK() OVER (ORDER BY `mae_cad_mwh` ASC) AS `mae_rank`
  FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_backtest_metrics`
  WHERE `run_timestamp` = (
    SELECT MAX(`run_timestamp`)
    FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_backtest_metrics`
  )
    AND `model_type` = 'model'
    AND `mae_cad_mwh` IS NOT NULL
)
SELECT `model_name`, ROUND(`mae_cad_mwh`, 2) AS `mae_cad_mwh`
FROM `latest_models`
WHERE `mae_rank` <= 1
ORDER BY `mae_cad_mwh` ASC, `model_name` ASC
```

**5. What is the average ensemble forecast price over the next 24 hours?**

```sql
SELECT ROUND(AVG(`ensemble_forecast_price`), 2) AS `avg_ensemble_forecast_price_cad_mwh`
FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_price_forecast_output`
WHERE `ensemble_forecast_price` IS NOT NULL
```

**6. Which hour-ending had the highest average pool price over the last 90 days?**

```sql
WITH `hourly_avg` AS (
  SELECT
    HOUR(`begin_datetime_mpt`) + 1 AS `hour_ending`,
    ROUND(AVG(`pool_price`), 2) AS `avg_pool_price`
  FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price`
  WHERE `pool_price` IS NOT NULL
    AND `begin_datetime_mpt` IS NOT NULL
    AND `begin_datetime_mpt` >= (
      SELECT MAX(`begin_datetime_mpt`)
      FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price`
      WHERE `pool_price` IS NOT NULL
    ) - INTERVAL 90 DAYS
  GROUP BY HOUR(`begin_datetime_mpt`) + 1
), `ranked` AS (
  SELECT
    `hour_ending`,
    `avg_pool_price`,
    RANK() OVER (ORDER BY `avg_pool_price` DESC) AS `price_rank`
  FROM `hourly_avg`
)

```

**7. What was the average pool price in 2026 in hours when actual wind and solar generation was above 3,000 MW?**

```sql
SELECT ROUND(AVG(`aeso_pool_price`.`pool_price`), 2) AS `avg_pool_price_cad_mwh`, COUNT(*) AS `hours`
FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`aeso_pool_price` AS `aeso_pool_price`
INNER JOIN `energy_canada_demos_catalog`.`aeso_price_forecast`.`silver_wind_solar_hourly` AS `silver_wind_solar_hourly`
  ON `aeso_pool_price`.`begin_datetime_mpt` = `silver_wind_solar_hourly`.`forecast_transaction_date`
WHERE `aeso_pool_price`.`pool_price` IS NOT NULL
  AND `silver_wind_solar_hourly`.`actual_mw` IS NOT NULL
  AND `silver_wind_solar_hourly`.`actual_mw` > 3000
  AND `aeso_pool_price`.`begin_datetime_mpt` >= TIMESTAMP('2026-01-01 00:00:00')
  AND `aeso_pool_price`.`begin_datetime_mp
```

**8. How many spike alerts have operators logged?**

```sql
SELECT COUNT(*) AS `spike_alert_count`
FROM `energy_canada_demos_catalog`.`aeso_price_forecast`.`ops_actions_history`
WHERE `action_type` ILIKE '%spike_alert%'
```
