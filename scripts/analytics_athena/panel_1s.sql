-- Wave-1: Create 1-second aligned panel
-- Resamples tick data to 1-second grid using SQL window functions
-- Forward-fills within 3 seconds, inner joins across venues
-- Output: CTAS to s3://acd-monitor-derived/panel_1s/date=YYYYMMDD/

CREATE TABLE acd_derived.panel_1s_20250929
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/panel_1s/date=20250929/',
    partitioned_by = ARRAY['venue']
) AS
WITH venue_data AS (
    SELECT 
        venue,
        ts_exchange,
        (best_bid + best_ask) / 2 as mid_px,
        best_bid,
        best_ask,
        bid_sz,
        ask_sz,
        last_px,
        last_sz,
        spread_bps,
        imbalance
    FROM acd_snapshots.btc_ticks
    WHERE date = '20250929'
),
-- Create 1-second grid
second_grid AS (
    SELECT DISTINCT 
        date_trunc('second', ts_exchange) as ts_1s
    FROM venue_data
    ORDER BY ts_1s
),
-- Forward-fill within 3 seconds per venue
forward_filled AS (
    SELECT 
        v.venue,
        s.ts_1s,
        LAST_VALUE(v.mid_px) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as mid_px,
        LAST_VALUE(v.best_bid) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as best_bid,
        LAST_VALUE(v.best_ask) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as best_ask,
        LAST_VALUE(v.bid_sz) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as bid_sz,
        LAST_VALUE(v.ask_sz) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as ask_sz,
        LAST_VALUE(v.last_px) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as last_px,
        LAST_VALUE(v.spread_bps) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as spread_bps,
        LAST_VALUE(v.imbalance) OVER (
            PARTITION BY v.venue 
            ORDER BY v.ts_exchange 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as imbalance
    FROM second_grid s
    CROSS JOIN (SELECT DISTINCT venue FROM venue_data) venues
    LEFT JOIN venue_data v ON s.ts_1s = date_trunc('second', v.ts_exchange) 
        AND venues.venue = v.venue
),
-- Filter to valid forward-fills (within 3 seconds)
valid_fills AS (
    SELECT *
    FROM forward_filled
    WHERE mid_px IS NOT NULL
)
SELECT 
    ts_1s as timestamp,
    venue,
    mid_px,
    best_bid,
    best_ask,
    bid_sz,
    ask_sz,
    last_px,
    spread_bps,
    imbalance
FROM valid_fills
ORDER BY ts_1s, venue;


