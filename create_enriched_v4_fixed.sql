CREATE TABLE acd_derived.btc_ticks_enriched_v4
WITH (
  format='PARQUET',
  partitioned_by = ARRAY['date','window','venue'],
  external_location='s3://acd-monitor-derived/enriched_v4/'
) AS
SELECT
  ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  (best_bid + best_ask)/2.0                                       AS mid_px,
  (best_ask - best_bid) / NULLIF((best_ask + best_bid)/2.0, 0) * 10000.0 AS spread_bps,
  date, window, venue
FROM acd_snapshots.btc_ticks_files_v2_view_fixed
WHERE ts_exchange IS NOT NULL;

