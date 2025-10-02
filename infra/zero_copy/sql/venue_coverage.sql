-- Venue coverage analysis
-- Shows data availability, gaps, and quality metrics per venue
-- Output: Coverage statistics and data quality indicators

SELECT 
    venue,
    date,
    COUNT(*) as total_records,
    COUNT(DISTINCT window) as windows_available,
    MIN(ts_exchange) as data_start,
    MAX(ts_exchange) as data_end,
    COUNT(CASE WHEN best_bid IS NULL OR best_ask IS NULL THEN 1 END) as null_price_count,
    COUNT(CASE WHEN best_bid <= 0 OR best_ask <= 0 THEN 1 END) as invalid_price_count,
    COUNT(CASE WHEN best_bid > best_ask THEN 1 END) as crossed_book_count,
    AVG(best_bid) as avg_bid,
    AVG(best_ask) as avg_ask,
    AVG(best_ask - best_bid) as avg_spread,
    STDDEV(best_ask - best_bid) as spread_volatility
FROM acd_snapshots.btc_ticks
WHERE date >= '20240901'
GROUP BY venue, date
ORDER BY venue, date DESC;


