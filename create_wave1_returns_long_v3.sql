CREATE OR REPLACE VIEW acd_derived.wave1_returns_long_v3 AS
WITH venue_set AS (SELECT ARRAY['binance','coinbase','kraken'] AS v),
counts AS (
  SELECT sec, COUNT(DISTINCT venue_norm) AS k
  FROM acd_derived.wave1_1s_snap_v3 s, venue_set vs
  WHERE s.venue_norm IN (SELECT unnest(v) FROM venue_set)
    AND s.price_last_le_3s IS NOT NULL
  GROUP BY sec
  HAVING k = cardinality((SELECT v FROM venue_set))
),
aligned AS (
  SELECT s.sec, s.venue_norm, s.price_last_le_3s AS px
  FROM acd_derived.wave1_1s_snap_v3 s
  JOIN counts c ON s.sec = c.sec
),
rets AS (
  SELECT
    venue_norm,
    sec,
    try( ln( nullif(px, 0.0) / nullif(lag(px) OVER (PARTITION BY venue_norm ORDER BY sec), 0.0) ) ) AS r
  FROM aligned
)
SELECT * FROM rets WHERE r IS NOT NULL ORDER BY venue_norm, sec;

