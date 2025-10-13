# Day-03 Data Prep & Align (2025-09-03)

## Overview
This directory contains the aligned 5s returns data for 2025-09-03 analysis.

## Files
- `aligned_5s.parquet`: Aligned 5s returns for all venue pairs
- `env_labels.csv`: Environment labels by session, volatility, and wash trading
- `spec_lock.json`: Specification lock with all parameters
- `manifest.json`: File manifest with hashes and metadata
- `README.md`: This file

## Data Sources
- Canonical views: data_v6/views/{VENUE}/20250903/ticks_canonical.parquet
- 1s bars: data_v6/bars_1s/{VENUE}/20250903/bars_v1.parquet

## Specifications
- Timezone: UTC-naive
- Frequency: 5s
- Lags: [1, 3, 6] (5s, 15s, 30s)
- Sessions: Tokyo (00:00-06:00), London (06:00-12:00), NewYork (12:00-18:00), Sydney (18:00-24:00)
- Environment regimes: volatility, wash trading

## Statistics
- Aligned rows: 189120
- Pairwise pairs: 12
- Venues processed: 4
- SHA256: 5800da2bdaddeaa1aad01012e9456765779f848724bc0be0a11a20246eeee963
