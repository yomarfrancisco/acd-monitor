-- Wave-2: Market structure analysis (5-second bars)
-- Creates OHLC bars, fractal swings, BOS/CHoCH patterns
-- Output: CTAS to s3://acd-monitor-derived/market_structure/date=YYYYMMDD/

CREATE TABLE acd_derived.market_structure_20250929
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/market_structure/date=20250929/'
) AS
WITH panel_data AS (
    -- Load 1-second panel
    SELECT 
        timestamp,
        venue,
        mid_px
    FROM acd_derived.panel_1s_20250929
),
-- Create 5-second bars from median mid across venues
five_sec_bars AS (
    SELECT 
        date_trunc('second', timestamp) as ts_5s,
        AVG(mid_px) as median_mid,  -- Using AVG as proxy for median
        MIN(mid_px) as low_price,
        MAX(mid_px) as high_price,
        FIRST_VALUE(mid_px) OVER (
            PARTITION BY date_trunc('second', timestamp) 
            ORDER BY timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as open_price,
        LAST_VALUE(mid_px) OVER (
            PARTITION BY date_trunc('second', timestamp) 
            ORDER BY timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as close_price,
        COUNT(*) as tick_count
    FROM panel_data
    GROUP BY date_trunc('second', timestamp)
),
-- Calculate ATR14 (14-period Average True Range)
atr_calc AS (
    SELECT 
        *,
        -- True Range calculation
        GREATEST(
            high_price - low_price,
            ABS(high_price - LAG(close_price, 1) OVER (ORDER BY ts_5s)),
            ABS(low_price - LAG(close_price, 1) OVER (ORDER BY ts_5s))
        ) as true_range,
        -- 14-period ATR
        AVG(GREATEST(
            high_price - low_price,
            ABS(high_price - LAG(close_price, 1) OVER (ORDER BY ts_5s)),
            ABS(low_price - LAG(close_price, 1) OVER (ORDER BY ts_5s))
        )) OVER (
            ORDER BY ts_5s 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) as atr_14
    FROM five_sec_bars
),
-- Fractal swings (k=2) - simplified version
fractal_swings AS (
    SELECT 
        *,
        -- Swing high: higher than 2 periods before and after
        CASE 
            WHEN high_price > LAG(high_price, 2) OVER (ORDER BY ts_5s) AND
                 high_price > LAG(high_price, 1) OVER (ORDER BY ts_5s) AND
                 high_price > LEAD(high_price, 1) OVER (ORDER BY ts_5s) AND
                 high_price > LEAD(high_price, 2) OVER (ORDER BY ts_5s)
            THEN 1 ELSE 0 
        END as swing_high,
        -- Swing low: lower than 2 periods before and after  
        CASE 
            WHEN low_price < LAG(low_price, 2) OVER (ORDER BY ts_5s) AND
                 low_price < LAG(low_price, 1) OVER (ORDER BY ts_5s) AND
                 low_price < LEAD(low_price, 1) OVER (ORDER BY ts_5s) AND
                 low_price < LEAD(low_price, 2) OVER (ORDER BY ts_5s)
            THEN 1 ELSE 0 
        END as swing_low
    FROM atr_calc
),
-- BOS (Break of Structure) - simplified
bos_patterns AS (
    SELECT 
        *,
        -- BOS Up: close breaks above previous swing high
        CASE 
            WHEN close_price > LAG(high_price, 1) OVER (ORDER BY ts_5s) AND
                 LAG(swing_high, 1) OVER (ORDER BY ts_5s) = 1
            THEN 1 ELSE 0 
        END as bos_up,
        -- BOS Down: close breaks below previous swing low
        CASE 
            WHEN close_price < LAG(low_price, 1) OVER (ORDER BY ts_5s) AND
                 LAG(swing_low, 1) OVER (ORDER BY ts_5s) = 1
            THEN 1 ELSE 0 
        END as bos_down
    FROM fractal_swings
),
-- CHoCH (Change of Character) - simplified
choch_patterns AS (
    SELECT 
        *,
        -- CHoCH Up: swing low followed by swing high
        CASE 
            WHEN swing_low = 1 AND LEAD(swing_high, 1) OVER (ORDER BY ts_5s) = 1
            THEN 1 ELSE 0 
        END as choch_up,
        -- CHoCH Down: swing high followed by swing low
        CASE 
            WHEN swing_high = 1 AND LEAD(swing_low, 1) OVER (ORDER BY ts_5s) = 1
            THEN 1 ELSE 0 
        END as choch_down
    FROM bos_patterns
)
SELECT 
    ts_5s as timestamp,
    median_mid,
    open_price,
    high_price,
    low_price,
    close_price,
    tick_count,
    true_range,
    atr_14,
    swing_high,
    swing_low,
    bos_up,
    bos_down,
    choch_up,
    choch_down,
    -- Structure state summary
    CASE 
        WHEN swing_high = 1 THEN 'swing_high'
        WHEN swing_low = 1 THEN 'swing_low'
        WHEN bos_up = 1 THEN 'bos_up'
        WHEN bos_down = 1 THEN 'bos_down'
        WHEN choch_up = 1 THEN 'choch_up'
        WHEN choch_down = 1 THEN 'choch_down'
        ELSE 'normal'
    END as structure_state
FROM choch_patterns
ORDER BY ts_5s;

