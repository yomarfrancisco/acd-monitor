CREATE OR REPLACE VIEW acd_derived.wave1_returns_wins_v1 AS
WITH aligned AS (
  SELECT * FROM acd_derived.wave1_1s_panel_v1
),
rets AS (
  SELECT
    sec,
    ln(px_binance  / lag(px_binance)  OVER (ORDER BY sec)) AS r_binance,
    ln(px_coinbase / lag(px_coinbase) OVER (ORDER BY sec)) AS r_coinbase,
    ln(px_kraken   / lag(px_kraken)   OVER (ORDER BY sec)) AS r_kraken
  FROM aligned
),
stats AS (
  SELECT
    avg(r_binance)  OVER () AS mu_b, stddev_pop(r_binance)  OVER () AS sd_b,
    avg(r_coinbase) OVER () AS mu_c, stddev_pop(r_coinbase) OVER () AS sd_c,
    avg(r_kraken)   OVER () AS mu_k, stddev_pop(r_kraken)   OVER () AS sd_k,
    *
  FROM rets
),
wins AS (
  SELECT
    sec,
    greatest(least(r_binance,  mu_b + 5*sd_b), mu_b - 5*sd_b) AS r_b_wins,
    greatest(least(r_coinbase, mu_c + 5*sd_c), mu_c - 5*sd_c) AS r_c_wins,
    greatest(least(r_kraken,   mu_k + 5*sd_k), mu_k - 5*sd_k) AS r_k_wins
  FROM stats
)
SELECT * FROM wins ORDER BY sec;
