-- Count records by date and venue
-- This query demonstrates basic aggregation over the partitioned table

SELECT 
    date,
    venue,
    COUNT(*) as record_count,
    MIN(ts_exchange) as earliest_ts,
    MAX(ts_exchange) as latest_ts,
    COUNT(DISTINCT window) as windows_covered
FROM acd_snapshots.btc_ticks
WHERE date >= '20240901'  -- Adjust date range as needed
GROUP BY date, venue
ORDER BY date DESC, venue;
