CREATE OR REPLACE VIEW acd_derived.market_last_1m_ohlc_v4 AS
WITH m AS (
  SELECT MAX(bucket_1m) AS max_minute
  FROM acd_derived.btc_ohlc_1m_v4
)
SELECT o.*
FROM acd_derived.btc_ohlc_1m_v4 o
JOIN m ON o.bucket_1m = m.max_minute
ORDER BY o.venue;
