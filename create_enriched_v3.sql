CREATE TABLE acd_derived.btc_ticks_enriched_v3
WITH (
  format='PARQUET',
  partitioned_by = ARRAY['date','window','venue'],
  external_location='s3://acd-monitor-derived/enriched_v3/'
) AS
SELECT
  date, window, venue,
  ts_exchange,
  best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  (best_bid + best_ask)/2.0 AS mid_px,
  (best_ask - best_bid) / NULLIF((best_ask + best_bid)/2.0, 0) * 10000.0 AS spread_bps
FROM acd_snapshots.btc_ticks_files_v2_view
WHERE ts_exchange IS NOT NULL;

