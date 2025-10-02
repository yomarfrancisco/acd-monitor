-- Wave-2: Environment and shock flags
-- Computes session labels, transitions, NY-open, 2σ return flags, VWAP deviations
-- Output: CTAS to s3://acd-monitor-derived/env_flags/date=YYYYMMDD/

CREATE TABLE acd_derived.env_flags_20250929
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/env_flags/date=20250929/'
) AS
WITH panel_data AS (
    -- Load 1-second panel (assumes panel_1s_20250929 exists)
    SELECT 
        timestamp,
        venue,
        mid_px,
        best_bid,
        best_ask,
        spread_bps,
        bid_sz,
        ask_sz
    FROM acd_derived.panel_1s_20250929
),
-- Session labels based on UTC hour
session_labels AS (
    SELECT 
        timestamp,
        venue,
        mid_px,
        spread_bps,
        CASE 
            WHEN EXTRACT(hour FROM timestamp) BETWEEN 0 AND 7 THEN 'Asia'
            WHEN EXTRACT(hour FROM timestamp) BETWEEN 8 AND 12 THEN 'Europe' 
            WHEN EXTRACT(hour FROM timestamp) BETWEEN 13 AND 19 THEN 'US'
            ELSE 'Pacific'
        END as session_label,
        -- Session transition flag (within ±5 minutes of transition times)
        CASE 
            WHEN (EXTRACT(hour FROM timestamp) = 0 AND EXTRACT(minute FROM timestamp) <= 5) OR
                 (EXTRACT(hour FROM timestamp) = 7 AND EXTRACT(minute FROM timestamp) >= 55) OR
                 (EXTRACT(hour FROM timestamp) = 8 AND EXTRACT(minute FROM timestamp) <= 5) OR
                 (EXTRACT(hour FROM timestamp) = 12 AND EXTRACT(minute FROM timestamp) >= 55) OR
                 (EXTRACT(hour FROM timestamp) = 13 AND EXTRACT(minute FROM timestamp) <= 5) OR
                 (EXTRACT(hour FROM timestamp) = 19 AND EXTRACT(minute FROM timestamp) >= 55) OR
                 (EXTRACT(hour FROM timestamp) = 20 AND EXTRACT(minute FROM timestamp) <= 5)
            THEN 1 ELSE 0 
        END as is_session_transition,
        -- NY open window (13:30-13:45 UTC)
        CASE 
            WHEN EXTRACT(hour FROM timestamp) = 13 AND 
                 EXTRACT(minute FROM timestamp) BETWEEN 30 AND 44
            THEN 1 ELSE 0 
        END as is_ny_open
    FROM panel_data
),
-- Calculate returns and rolling statistics
returns_and_stats AS (
    SELECT 
        *,
        -- 1-second return
        (mid_px - LAG(mid_px, 1) OVER (PARTITION BY venue ORDER BY timestamp)) / 
        LAG(mid_px, 1) OVER (PARTITION BY venue ORDER BY timestamp) as ret_1s,
        -- Rolling 30-minute standard deviation (1800 observations)
        STDDEV(mid_px) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as rolling_std_30m
    FROM session_labels
),
-- 2σ return flags
sigma_flags AS (
    SELECT 
        *,
        CASE 
            WHEN ABS(ret_1s) > 2 * rolling_std_30m AND rolling_std_30m > 0 
            THEN 1 ELSE 0 
        END as is_return_2sigma
    FROM returns_and_stats
),
-- VWAP calculations
vwap_calc AS (
    SELECT 
        *,
        -- Daily VWAP (volume-weighted average price)
        AVG(mid_px) OVER (
            PARTITION BY venue, DATE(timestamp) 
            ORDER BY timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as daily_vwap,
        -- VWAP deviation
        ABS(mid_px - AVG(mid_px) OVER (
            PARTITION BY venue, DATE(timestamp) 
            ORDER BY timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )) as vwap_deviation
    FROM sigma_flags
),
-- Final flags
final_flags AS (
    SELECT 
        timestamp,
        venue,
        mid_px,
        spread_bps,
        session_label,
        is_session_transition,
        is_ny_open,
        is_return_2sigma,
        -- VWAP deviation 2σ flag (using rolling std of mid price changes)
        CASE 
            WHEN vwap_deviation > 2 * STDDEV(mid_px) OVER (
                PARTITION BY venue 
                ORDER BY timestamp 
                ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
            ) THEN 1 ELSE 0 
        END as is_vwap_dev_2sigma,
        -- VWAP reset jump (at midnight UTC)
        CASE 
            WHEN EXTRACT(hour FROM timestamp) = 0 AND EXTRACT(minute FROM timestamp) = 0
            THEN 1 ELSE 0 
        END as is_vwap_reset_jump
    FROM vwap_calc
)
SELECT 
    timestamp,
    venue,
    mid_px,
    spread_bps,
    session_label,
    is_session_transition,
    is_ny_open,
    is_return_2sigma,
    is_vwap_dev_2sigma,
    is_vwap_reset_jump
FROM final_flags
ORDER BY timestamp, venue;


