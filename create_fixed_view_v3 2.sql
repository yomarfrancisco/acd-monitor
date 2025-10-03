CREATE OR REPLACE VIEW acd_snapshots.btc_ticks_files_v2_view_fixed AS
SELECT
  element_at(split("$path", '/'), -4) AS date,
  element_at(split("$path", '/'), -3) AS window,
  regexp_replace(element_at(split("$path", '/'), -1), '\\.parquet$', '') AS venue,
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  "$path" AS _path
FROM acd_snapshots.btc_ticks_files_v2;
