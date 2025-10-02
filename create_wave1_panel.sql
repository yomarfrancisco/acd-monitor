CREATE OR REPLACE VIEW acd_derived.wave1_1s_panel_v1 AS
WITH p AS (SELECT * FROM acd_derived.wave1_1s_snap_v1)
SELECT
  sec,
  max(CASE WHEN venue='binance'  THEN price_last_le_3s END) AS px_binance,
  max(CASE WHEN venue='coinbase' THEN price_last_le_3s END) AS px_coinbase,
  max(CASE WHEN venue='kraken'   THEN price_last_le_3s END) AS px_kraken,
  max(CASE WHEN venue='okx'      THEN price_last_le_3s END) AS px_okx,
  max(CASE WHEN venue='bybit'    THEN price_last_le_3s END) AS px_bybit
FROM p
GROUP BY sec
HAVING
  px_binance IS NOT NULL
  AND px_coinbase IS NOT NULL
  AND px_kraken IS NOT NULL
ORDER BY sec;

