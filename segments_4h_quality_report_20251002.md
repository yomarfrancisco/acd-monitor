# 4-Hour Rolling Segment Analysis Report
**Generated**: 2025-10-02T16:51:28.476248+00:00

## Executive Summary

This report provides 4-hour rolling segment analysis for captured cryptocurrency exchange data.
Each venue's data is partitioned into 4-hour blocks (00:00-04:00, 04:00-08:00, etc.) for detailed analysis.

## COINBASE Analysis

| Segment | Trades | Mean Price | Std Dev | Min | Max | Drift | Volume | Duplicates | Outliers |
|---------|--------|------------|---------|-----|-----|-------|--------|------------|----------|
| 12:00-16:00 | 100 | $119,669.63 | $4.06 | $119,654.36 | $119,679.12 | $+24.76 | 3.01 | 21.0% | 1.0% |

## KRAKEN Analysis

| Segment | Trades | Mean Price | Std Dev | Min | Max | Drift | Volume | Duplicates | Outliers |
|---------|--------|------------|---------|-----|-----|-------|--------|------------|----------|
| 00:00-04:00 | 50 | $118,621.77 | $18.18 | $118,600.00 | $118,637.60 | $+37.50 | 0.21 | 0.0% | 0.0% |
| 12:00-16:00 | 50 | $118,809.37 | $5.21 | $118,800.10 | $118,812.30 | $+12.20 | 0.11 | 2.0% | 0.0% |

## BINANCE Analysis

| Segment | Trades | Mean Price | Std Dev | Min | Max | Drift | Volume | Duplicates | Outliers |
|---------|--------|------------|---------|-----|-----|-------|--------|------------|----------|
| 00:00-04:00 | 50 | $118,596.10 | $0.85 | $118,594.98 | $118,598.87 | $+3.88 | 0.26 | 4.0% | 2.0% |
| 12:00-16:00 | 50 | $118,765.72 | $0.00 | $118,765.72 | $118,765.73 | $+0.00 | 0.19 | 44.0% | 0.0% |

## Cross-Venue Spread Analysis

| Segment | Spread ($) | Spread (%) | Arbitrage Anomaly |
|---------|------------|------------|-------------------|
| 00:00-04:00 | $25.67 | 0.02% | ✅ NO |
| 12:00-16:00 | $903.90 | 0.76% | ✅ NO |

## Schema Validation

| Venue | Data Type | Bid/Ask Fields | Orderbook Fields |
|-------|-----------|----------------|------------------|
| COINBASE | trade_prints_only | 0 | 0 |
| KRAKEN | trade_prints_only | 0 | 0 |
| BINANCE | trade_prints_only | 0 | 0 |

## Quality Flags

✅ **All venues have acceptable duplicate ratios (< 50%)**
