-- Analyze venue coverage and data quality
-- Shows which venues have data for each date/window combination

SELECT 
    date,
    window,
    COUNT(DISTINCT venue) as venues_present,
    COLLECT_LIST(venue) as venue_list,
    AVG(record_count) as avg_records_per_venue
FROM (
    SELECT 
        date,
        window,
        venue,
        COUNT(*) as record_count
    FROM acd_snapshots.btc_ticks
    WHERE date >= '20240901'  -- Adjust date range as needed
    GROUP BY date, window, venue
) venue_stats
GROUP BY date, window
HAVING COUNT(DISTINCT venue) >= 3  -- Only show windows with 3+ venues
ORDER BY date DESC, window;
