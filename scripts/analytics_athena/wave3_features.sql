-- Wave-3: Advanced features and marginals
-- Computes ICP design matrix, VMM moments, copula marginals, clustering features
-- Output: CTAS to s3://acd-monitor-derived/wave3/date=YYYYMMDD/

CREATE TABLE acd_derived.wave3_features_20250929
WITH (
    format = 'PARQUET',
    external_location = 's3://acd-monitor-derived/wave3/date=20250929/'
) AS
WITH panel_data AS (
    -- Load 1-second panel with environment flags
    SELECT 
        p.timestamp,
        p.venue,
        p.mid_px,
        p.spread_bps,
        p.bid_sz,
        p.ask_sz,
        e.session_label,
        e.is_session_transition,
        e.is_ny_open,
        e.is_return_2sigma,
        e.is_vwap_dev_2sigma
    FROM acd_derived.panel_1s_20250929 p
    LEFT JOIN acd_derived.env_flags_20250929 e 
        ON p.timestamp = e.timestamp AND p.venue = e.venue
),
-- Cross-venue equal-weighted metrics
cross_venue_metrics AS (
    SELECT 
        timestamp,
        AVG(mid_px) as mid_eq,
        AVG(spread_bps) as spread_eq,
        STDDEV(mid_px) as cross_venue_dispersion,
        COUNT(DISTINCT venue) as venue_count
    FROM panel_data
    GROUP BY timestamp
),
-- Per-venue features with cross-venue context
venue_features AS (
    SELECT 
        p.timestamp,
        p.venue,
        p.mid_px,
        p.spread_bps,
        p.bid_sz,
        p.ask_sz,
        p.session_label,
        p.is_session_transition,
        p.is_ny_open,
        p.is_return_2sigma,
        p.is_vwap_dev_2sigma,
        c.mid_eq,
        c.spread_eq,
        c.cross_venue_dispersion,
        c.venue_count,
        -- Per-venue returns
        (p.mid_px - LAG(p.mid_px, 1) OVER (PARTITION BY p.venue ORDER BY p.timestamp)) / 
        LAG(p.mid_px, 1) OVER (PARTITION BY p.venue ORDER BY p.timestamp) as ret_1s,
        -- Spread changes
        p.spread_bps - LAG(p.spread_bps, 1) OVER (PARTITION BY p.venue ORDER BY p.timestamp) as delta_spread,
        -- Cross-venue basis (venue vs equal-weighted)
        p.mid_px - c.mid_eq as basis_vs_eq,
        -- Imbalance proxy
        (p.bid_sz - p.ask_sz) / NULLIF(p.bid_sz + p.ask_sz, 0) as imbalance_proxy
    FROM panel_data p
    LEFT JOIN cross_venue_metrics c ON p.timestamp = c.timestamp
),
-- Rolling statistics for VMM moments
rolling_stats AS (
    SELECT 
        *,
        -- 30-minute rolling windows (1800 observations)
        AVG(ret_1s) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as mean_ret_30m,
        STDDEV(ret_1s) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as std_ret_30m,
        AVG(spread_bps) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as mean_spread_30m,
        STDDEV(spread_bps) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as std_spread_30m,
        AVG(cross_venue_dispersion) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as mean_dispersion_30m
    FROM venue_features
),
-- Event intensities
event_intensities AS (
    SELECT 
        *,
        -- Rolling event counts (30-minute windows)
        SUM(is_return_2sigma) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as return_2sigma_count_30m,
        SUM(is_vwap_dev_2sigma) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as vwap_dev_count_30m,
        SUM(is_session_transition) OVER (
            PARTITION BY venue 
            ORDER BY timestamp 
            ROWS BETWEEN 1799 PRECEDING AND CURRENT ROW
        ) as session_transition_count_30m
    FROM rolling_stats
),
-- Copula marginals (empirical CDF ranks)
copula_marginals AS (
    SELECT 
        *,
        -- Rank-based uniforms for returns
        RANK() OVER (
            PARTITION BY venue, session_label 
            ORDER BY ret_1s
        ) / COUNT(*) OVER (PARTITION BY venue, session_label) as u_ret,
        -- Rank-based uniforms for spreads  
        RANK() OVER (
            PARTITION BY venue, session_label 
            ORDER BY spread_bps
        ) / COUNT(*) OVER (PARTITION BY venue, session_label) as u_spread,
        -- Rank-based uniforms for dispersion
        RANK() OVER (
            PARTITION BY session_label 
            ORDER BY cross_venue_dispersion
        ) / COUNT(*) OVER (PARTITION BY session_label) as u_dispersion
    FROM event_intensities
),
-- Clustering features (5-minute windows)
clustering_features AS (
    SELECT 
        date_trunc('minute', timestamp) as ts_5m,
        venue,
        session_label,
        -- Feature vector components
        AVG(ret_1s) as mean_ret,
        STDDEV(ret_1s) as std_ret,
        AVG(spread_bps) as mean_spread,
        STDDEV(spread_bps) as std_spread,
        AVG(cross_venue_dispersion) as mean_dispersion,
        STDDEV(cross_venue_dispersion) as std_dispersion,
        AVG(imbalance_proxy) as mean_imbalance,
        STDDEV(imbalance_proxy) as std_imbalance,
        AVG(return_2sigma_count_30m) as mean_event_intensity,
        AVG(session_transition_count_30m) as mean_transition_intensity,
        -- Session indicators
        CASE WHEN session_label = 'Asia' THEN 1 ELSE 0 END as is_asia,
        CASE WHEN session_label = 'Europe' THEN 1 ELSE 0 END as is_europe,
        CASE WHEN session_label = 'US' THEN 1 ELSE 0 END as is_us,
        CASE WHEN session_label = 'Pacific' THEN 1 ELSE 0 END as is_pacific
    FROM copula_marginals
    GROUP BY date_trunc('minute', timestamp), venue, session_label
)
SELECT 
    ts_5m as timestamp,
    venue,
    session_label,
    -- ICP design matrix components
    mean_ret,
    std_ret,
    mean_spread,
    std_spread,
    mean_dispersion,
    std_dispersion,
    mean_imbalance,
    std_imbalance,
    mean_event_intensity,
    mean_transition_intensity,
    -- VMM moment proxies
    mean_ret * mean_spread as ret_spread_moment,
    std_ret * std_spread as ret_spread_vol_moment,
    mean_dispersion * mean_event_intensity as dispersion_event_moment,
    -- Copula marginals (simplified)
    mean_ret as u_ret_proxy,
    mean_spread as u_spread_proxy,
    mean_dispersion as u_dispersion_proxy,
    -- Clustering features
    is_asia,
    is_europe,
    is_us,
    is_pacific
FROM clustering_features
ORDER BY ts_5m, venue;


