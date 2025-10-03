CREATE EXTERNAL TABLE acd_snapshots.btc_ticks_files_v2 (
  ts_exchange bigint,
  best_bid    double,
  best_ask    double,
  last_px     double,
  bid_sz      double,
  ask_sz      double,
  trade_sz    double
)
STORED AS PARQUET
LOCATION 's3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks/';
