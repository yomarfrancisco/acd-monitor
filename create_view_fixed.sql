CREATE OR REPLACE VIEW acd_snapshots.btc_ticks_files_v2_view AS
SELECT
  '20250928' AS date,
  '0200-0230' AS window,
  regexp_extract("$path", '.*/ticks/([^/.]+)\\.parquet', 1) AS venue,
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  "$path" AS _path
FROM acd_snapshots.btc_ticks_files_v2;

