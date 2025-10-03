-- Create canary view for validation
CREATE OR REPLACE VIEW acd_snapshots.btc_ticks_canary_v1 AS
SELECT 
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  "$path" AS _path
FROM acd_snapshots.btc_ticks_files_v2
WHERE "$path" LIKE '%/BTC-USD/20250928/0200-0230/ticks_canary/%';
