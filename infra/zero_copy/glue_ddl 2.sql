-- Glue Database and Table DDL for ACD Monitor Zero-Copy Analytics
-- Database: acd_snapshots
-- Table: btc_ticks (with partition projection)

-- 1. Create Database
CREATE DATABASE IF NOT EXISTS acd_snapshots
COMMENT 'ACD Monitor snapshot data warehouse'
LOCATION 's3://acd-monitor-snapshots/';

-- 2. Create External Table with Partition Projection
CREATE EXTERNAL TABLE IF NOT EXISTS acd_snapshots.btc_ticks (
    ts_exchange TIMESTAMP COMMENT 'Exchange timestamp (UTC)',
    best_bid DOUBLE COMMENT 'Best bid price',
    best_ask DOUBLE COMMENT 'Best ask price', 
    bid_sz DOUBLE COMMENT 'Bid size',
    ask_sz DOUBLE COMMENT 'Ask size',
    last_px DOUBLE COMMENT 'Last trade price',
    last_sz DOUBLE COMMENT 'Last trade size',
    mid_px DOUBLE COMMENT 'Computed mid price',
    spread_bps DOUBLE COMMENT 'Spread in basis points',
    depth_5bps_bid DOUBLE COMMENT 'Depth at 5bps bid',
    depth_5bps_ask DOUBLE COMMENT 'Depth at 5bps ask',
    depth_10bps_bid DOUBLE COMMENT 'Depth at 10bps bid', 
    depth_10bps_ask DOUBLE COMMENT 'Depth at 10bps ask',
    imbalance DOUBLE COMMENT 'Order book imbalance',
    imbalance_5bps DOUBLE COMMENT 'Imbalance at 5bps',
    imbalance_10bps DOUBLE COMMENT 'Imbalance at 10bps',
    rv_5s DOUBLE COMMENT 'Realized volatility 5s',
    rv_30s DOUBLE COMMENT 'Realized volatility 30s',
    ret_1s DOUBLE COMMENT '1-second return',
    ret_5s DOUBLE COMMENT '5-second return', 
    ret_30s DOUBLE COMMENT '30-second return',
    trade_sign BIGINT COMMENT 'Trade sign indicator',
    notional_traded DOUBLE COMMENT 'Notional volume traded',
    maker_fee_bps DOUBLE COMMENT 'Maker fee in bps',
    taker_fee_bps DOUBLE COMMENT 'Taker fee in bps',
    fee_tier STRING COMMENT 'Fee tier',
    venue_id STRING COMMENT 'Venue identifier',
    coverage_flag BOOLEAN COMMENT 'Data coverage flag',
    clock_skew_ms DOUBLE COMMENT 'Clock skew in milliseconds',
    seed BIGINT COMMENT 'Random seed',
    code_version STRING COMMENT 'Code version',
    commit STRING COMMENT 'Git commit hash',
    timestamp TIMESTAMP COMMENT 'Processing timestamp'
)
PARTITIONED BY (
    date STRING COMMENT 'Date partition (YYYYMMDD)',
    window STRING COMMENT 'Time window (HHMM-HHMM)', 
    venue STRING COMMENT 'Exchange venue'
)
STORED AS PARQUET
LOCATION 's3://acd-monitor-snapshots/snapshots/BTC-USD/'
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.date.type' = 'date',
    'projection.date.range' = '2024/01/01,NOW',
    'projection.date.format' = 'yyyyMMdd',
    'projection.date.interval' = '1',
    'projection.date.interval.unit' = 'DAYS',
    'projection.window.type' = 'enum',
    'projection.window.values' = '0000-2359,0000-0015,0015-0030,0030-0045,0045-0100,0100-0115,0115-0130,0130-0145,0145-0200,0200-0215,0215-0230,0230-0245,0245-0300,0300-0315,0315-0330,0330-0345,0345-0400,0400-0415,0415-0430,0430-0445,0445-0500,0500-0515,0515-0530,0530-0545,0545-0600,0600-0615,0615-0630,0630-0645,0645-0700,0700-0715,0715-0730,0730-0745,0745-0800,0800-0815,0815-0830,0830-0845,0845-0900,0900-0915,0915-0930,0930-0945,0945-1000,1000-1015,1015-1030,1030-1045,1045-1100,1100-1115,1115-1130,1130-1145,1145-1200,1200-1215,1215-1230,1230-1245,1245-1300,1300-1315,1315-1330,1330-1345,1345-1400,1400-1415,1415-1430,1430-1445,1445-1500,1500-1515,1515-1530,1530-1545,1545-1600,1600-1615,1615-1630,1630-1645,1645-1700,1700-1715,1715-1730,1730-1745,1745-1800,1800-1815,1815-1830,1830-1845,1845-1900,1900-1915,1915-1930,1930-1945,1945-2000,2000-2015,2015-2030,2030-2045,2045-2100,2100-2115,2115-2130,2130-2145,2145-2200,2200-2215,2215-2230,2230-2245,2245-2300,2300-2315,2315-2330,2330-2345,2345-2359',
    'projection.venue.type' = 'enum',
    'projection.venue.values' = 'binance,coinbase,kraken,okx,bybit',
    'storage.location.template' = 's3://acd-monitor-snapshots/snapshots/BTC-USD/${date}/${window}/ticks/${venue}/',
    'classification' = 'parquet',
    'compressionType' = 'none'
);
