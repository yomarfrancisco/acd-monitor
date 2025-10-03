CREATE OR REPLACE VIEW acd_snapshots.btc_ticks_files_v2_view_fixed AS
WITH parts AS (
  SELECT
    split("$path", '/') AS segs,
    ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
    "$path" AS _path
  FROM acd_snapshots.btc_ticks_files_v2
)
SELECT
  element_at(segs, -4)                                              AS date,
  element_at(segs, -3)                                              AS window,
  regexp_replace(element_at(segs, -1), '\\.parquet$', '')           AS venue,
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  _path
FROM parts;
