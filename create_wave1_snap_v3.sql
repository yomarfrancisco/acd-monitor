CREATE OR REPLACE VIEW acd_derived.wave1_1s_snap_v3 AS
WITH src AS (
  SELECT
    from_unixtime(
      CASE WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
           WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
           ELSE ts_exchange*1.0 END
    ) AS ts,
    lower(trim(venue)) AS venue_norm,
    coalesce(last_px, mid_px) AS price
  FROM acd_derived.btc_ticks_enriched_v4
),
bounds AS (
  SELECT venue_norm,
         date_trunc('second', MIN(ts)) AS min_ts,
         date_trunc('second', MAX(ts)) AS max_ts
  FROM src GROUP BY venue_norm
),
grid AS (
  SELECT b.venue_norm, t AS sec
  FROM bounds b
  CROSS JOIN UNNEST(sequence(b.min_ts, b.max_ts, INTERVAL '1' SECOND)) AS u(t)
)
SELECT
  g.venue_norm,
  g.sec,
  max_by(s.price, s.ts) AS price_last_le_3s
FROM grid g
LEFT JOIN src s
  ON s.venue_norm = g.venue_norm
 AND s.ts BETWEEN g.sec - INTERVAL '3' SECOND AND g.sec
GROUP BY g.venue_norm, g.sec;

