CREATE OR REPLACE VIEW acd_derived.market_last_px_v4 AS
WITH t AS (
  SELECT
    from_unixtime(
      CASE
        WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
        WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
        ELSE ts_exchange*1.0
      END
    ) AS ts,
    venue,
    last_px, best_bid, best_ask
  FROM acd_derived.btc_ticks_enriched_v4
)
SELECT
  venue,
  max_by(last_px, ts)  AS last_px,
  max_by(best_bid, ts) AS last_bid,
  max_by(best_ask, ts) AS last_ask,
  MAX(ts)              AS ts
FROM t
GROUP BY venue;

