-- Create 5-second OHLC bars from median mid prices
-- Uses (best_bid + best_ask) / 2 as mid price
-- Output: CTAS to s3://acd-monitor-derived/ohlc_5s/date=YYYYMMDD/

CREATE TABLE acd_derived.ohlc_5s_20250929
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/ohlc_5s/date=20250929/',
    partitioned_by = ARRAY['venue']
) AS
SELECT 
    venue,
    date_trunc('second', ts_exchange) as timestamp_5s,
    AVG((best_bid + best_ask) / 2) as mid_price,
    MIN((best_bid + best_ask) / 2) as low_price,
    MAX((best_bid + best_ask) / 2) as high_price,
    FIRST_VALUE((best_bid + best_ask) / 2) OVER (
        PARTITION BY venue, date_trunc('second', ts_exchange) 
        ORDER BY ts_exchange 
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) as open_price,
    LAST_VALUE((best_bid + best_ask) / 2) OVER (
        PARTITION BY venue, date_trunc('second', ts_exchange) 
        ORDER BY ts_exchange 
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) as close_price,
    COUNT(*) as tick_count,
    SUM(bid_sz + ask_sz) as total_depth,
    AVG(best_ask - best_bid) as avg_spread
FROM acd_snapshots.btc_ticks
WHERE date = '20250929'  -- Single date for initial test
GROUP BY venue, date_trunc('second', ts_exchange)
ORDER BY venue, timestamp_5s;

