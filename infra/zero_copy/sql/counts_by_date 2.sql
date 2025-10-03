-- Count records by date and venue
-- Demonstrates basic aggregation over the partitioned table
-- Output: Record counts, time ranges, and coverage per venue/date

SELECT 
    date,
    venue,
    COUNT(*) as record_count,
    MIN(ts_exchange) as earliest_ts,
    MAX(ts_exchange) as latest_ts,
    COUNT(DISTINCT window) as windows_covered,
    COUNT(DISTINCT date) as days_covered
FROM acd_snapshots.btc_ticks
WHERE date >= '20240901'  -- Adjust date range as needed
GROUP BY date, venue
ORDER BY date DESC, venue;

