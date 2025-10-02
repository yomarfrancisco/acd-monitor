-- Create 5-second OHLC bars from tick data
-- This query writes aggregated data to the derived bucket

CREATE TABLE acd_snapshots.btc_ohlc_5s
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/ohlc_5s/',
    partitioned_by = ARRAY['date', 'venue']
) AS
SELECT 
    venue,
    date,
    -- Create 5-second buckets from timestamp
    DATE_TRUNC('second', 
        FROM_UNIXTIME(ts_exchange / 1000000000)  -- Convert nanoseconds to seconds
    ) as bar_timestamp,
    -- OHLC calculations
    FIRST_VALUE(mid_px) OVER (
        PARTITION BY venue, date, 
        DATE_TRUNC('second', FROM_UNIXTIME(ts_exchange / 1000000000))
        ORDER BY ts_exchange
    ) as open_price,
    MAX(mid_px) as high_price,
    MIN(mid_px) as low_price,
    LAST_VALUE(mid_px) OVER (
        PARTITION BY venue, date,
        DATE_TRUNC('second', FROM_UNIXTIME(ts_exchange / 1000000000))
        ORDER BY ts_exchange
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) as close_price,
    -- Volume and spread metrics
    COUNT(*) as tick_count,
    AVG(best_ask - best_bid) as avg_spread,
    SUM(bid_sz + ask_sz) as total_depth
FROM acd_snapshots.btc_ticks
WHERE date = '20240929'  -- Single date for testing
  AND mid_px IS NOT NULL
  AND best_bid > 0 
  AND best_ask > 0
GROUP BY 
    venue,
    date,
    DATE_TRUNC('second', FROM_UNIXTIME(ts_exchange / 1000000000))
ORDER BY venue, bar_timestamp;
