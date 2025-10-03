CREATE OR REPLACE VIEW acd_derived.btc_ohlc_5s_v4 AS
WITH scoped AS (
  SELECT
    from_unixtime(
      CASE WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
           WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
           ELSE ts_exchange*1.0 END
    ) AS ts,
    last_px AS price,
    trade_sz AS volume,
    venue
  FROM acd_derived.btc_ticks_enriched_v4
  WHERE ts_exchange IS NOT NULL
),
b AS (
  SELECT
    from_unixtime(5 * floor(to_unixtime(ts)/5)) AS bucket_5s,
    price, volume, venue, ts
  FROM scoped
)
SELECT
  bucket_5s, venue,
  min_by(price, ts) AS open,
  max_by(price, ts) AS close,
  max(price)        AS high,
  min(price)        AS low,
  sum(volume)       AS volume
FROM b
GROUP BY 1, 2;
