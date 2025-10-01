-- ETH Ticks Reader View for 2025-10-01
-- This view provides read-only access to ETH-USD tick data for Wave-1 analysis
-- Location: s3://acd-monitor-snapshots/canonical/20251001/eth_ticks/

CREATE OR REPLACE VIEW acd_canonical.eth_ticks_20251001_v1 AS
SELECT
  symbol,
  venue,
  ts_exchange_ms,
  from_unixtime(ts_exchange_ms/1000) AS ts_exchange,
  last_px,
  best_bid,
  best_ask,
  trade_sz,
  vdate_ymd,
  vwindow,
  _path
FROM acd_snapshots.btc_ticks_files_v2
WHERE "$path" LIKE '%canonical/20251001/eth_ticks/%'
  AND symbol = 'ETH-USD'
  AND ts_exchange_ms IS NOT NULL
  AND last_px IS NOT NULL
  AND last_px >= 2000  -- Price sanity check for 2025+
  AND venue IN ('coinbase', 'kraken');  -- Exclude bybit, binance, okx
