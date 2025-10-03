# CoinAPI Flat Files → 7-Day 1-Second Panel

This document describes the process for downloading and processing CoinAPI Flat Files data to build a 7-day, 1-second BTC panel for comparison with REST-based data.

## Overview

- **Source**: CoinAPI Flat Files (S3-compatible API)
- **Data Type**: Trade-level data (T-TRADES)
- **Venues**: E-BINANCE, E-COINBASE, E-KRAKEN
- **Symbols**: BTC/USDT, BTC/USD
- **Period**: 7 full UTC days (2025-09-25 to 2025-10-01)
- **Output**: 1-second OHLCV candles, aligned cross-venue panel

## API Details

- **Base URL**: `https://s3.flatfiles.coinapi.io`
- **Authentication**: `Authorization: ${COINAPI_KEY}` header
- **Format**: S3-compatible LIST/GET operations
- **Data**: Compressed CSV files (.csv.gz)

## Manual Testing Commands

```bash
# LIST objects for Binance, 2025-09-25
curl -sS -H "Accept: application/xml" \
     -H "Authorization: ${COINAPI_KEY}" \
  "https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-20250925/E-BINANCE/"

# GET a specific object
curl -sS -H "Authorization: ${COINAPI_KEY}" \
  -o trades.csv.gz \
  "https://s3.flatfiles.coinapi.io/bucket/<Key>"

# AWS CLI (alternative)
aws --endpoint-url https://s3.flatfiles.coinapi.io s3 cp \
  s3://coinapi/T-TRADES/D-20250925/E-COINBASE/<Key> .
```

## Symbol Mapping

| Venue | Symbol Pattern | Description |
|-------|----------------|-------------|
| E-BINANCE | S-BTC__002DUSDT | BTC/USDT |
| E-BINANCE | S-BTC__002DUSD | BTC/USD (if present) |
| E-COINBASE | S-BTC__002DUSD | BTC/USD |
| E-KRAKEN | S-XBT__002DUSD | XBT/USD (mapped to BTC) |
| E-KRAKEN | S-BTC__002DUSD | BTC/USD (if present) |

## Data Quality Gates

- **Irregularity**: ≥5 unique time deltas (not synthetic)
- **Duplicates**: ≤5% exact duplicate rows
- **Price Variance**: ≥$0.10 standard deviation
- **Coverage**: ≥40% of 86,400 seconds per day
- **Timestamp Range**: Within UTC day boundaries

## Output Structure

```
analysis/flatfiles_1s/
├── panel/
│   └── flatfiles_panel_7d_1s.parquet    # Aligned cross-venue panel
├── qc/
│   ├── coverage_table.md                # Coverage statistics
│   └── qc_summary.json                  # Quality control summary
└── _sum/                                # Summary statistics
└── _sig/                                # Signal analysis
```

## Processing Steps

1. **LIST**: Query S3-compatible API for available files
2. **GET**: Download compressed CSV files with rate limiting
3. **QC**: Validate trade data quality (irregularity, duplicates, variance)
4. **Resample**: Convert to 1-second OHLCV candles
5. **Align**: Inner-join timestamps across venues
6. **Analyze**: Compute 15 core ACD variables with bootstrap CIs

## Rate Limiting

- **Concurrent Downloads**: ≤4 simultaneous
- **Batch Delay**: 200-400ms between batches
- **Error Handling**: Stop on 401/403/5xx responses

## Comparison with REST Data

The Flat Files panel will be compared against the existing REST-based panel on:

- **Spreads**: Mean, median, P95 cross-venue spreads
- **Correlations**: Pearson/Spearman return correlations
- **Lead-Lag**: Cross-correlogram analysis (±5s)
- **Granger Causality**: ≤5s lag relationships
- **Volatility**: Realized volatility and clustering
- **Coverage**: Data availability and quality metrics

## Usage

```bash
# Set API key
export COINAPI_KEY="your-api-key-here"

# Run the processor
python make_flatfiles_panel.py
```

## Expected Outputs

- **Coverage Table**: Per-venue and aligned coverage statistics
- **Pooled Statistics**: 7-day aggregated metrics with 95% CIs
- **REST vs FLAT Comparison**: Side-by-side metrics and deltas
- **Quality Report**: Data provenance and validation results
