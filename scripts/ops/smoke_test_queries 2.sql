-- Smoke test queries for Glue table validation
-- All queries use Athena only - no downloads

-- A) Pointed count for a single file
SELECT count(*) AS n
FROM acd_snapshots.btc_ticks
WHERE date='20250929' AND window='0200-0230' AND venue='binance';

-- B) Minimal preview to prove schema alignment
SELECT ts_exchange, best_bid, best_ask, last_px, mid_px
FROM acd_snapshots.btc_ticks
WHERE date='20250929' AND window='0200-0230' AND venue='binance'
ORDER BY ts_exchange
LIMIT 5;

-- C) Multi-venue coverage for a day (uses projection; no partition registration)
SELECT venue, COUNT(1) AS rows
FROM acd_snapshots.btc_ticks
WHERE date='20250929'
GROUP BY venue
ORDER BY venue;

