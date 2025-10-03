CREATE OR REPLACE VIEW acd_snapshots.btc_ticks_files_v2_view AS
SELECT
  regexp_extract("$path", '.*/BTC-USD/([^/]+)/', 1)                           AS date,
  regexp_extract("$path", '.*/BTC-USD/[^/]+/([^/]+)/', 1)                     AS window,
  regexp_extract("$path", '.*/BTC-USD/[^/]+/[^/]+/ticks/([^/.]+)\\.parquet', 1) AS venue,
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  "$path" AS _path
FROM acd_snapshots.btc_ticks_files_v2;
