# Wave-2 Variable Preparation Summary - BTC-USD

## Overview
Successfully prepared variables for Wave-2 econometric deepening tests.

**Analysis Date**: 2025-09-30 12:30:24 UTC
**Symbol**: BTC-USD
**Panel Observations**: 9003

## Variables Prepared

### 6. Event Studies on Exogenous Shocks
- **Events Identified**: 1334
- **Event Windows**: 1334
- **Data File**: data/derived/btc_usd/event_study_data.parquet

### 7. Granger Causality Networks
- **Venues Available**: 5
- **Observations**: 7477
- **Max Lags**: 5

### 8. Cointegration & Error Correction Models
- **Venues Available**: 5
- **Observations**: 7478
- **Price Series**: ['binance', 'coinbase', 'kraken', 'okx', 'bybit']

### 9. Markov Switching Regimes
- **Venues Available**: 5
- **Observations**: 7476
- **Window Size**: 60

### 10. Variance Decomposition (Structural VAR)
- **Venues Available**: 5
- **Observations**: 7477
- **Max Lags**: 3
- **Exogenous Variables**: ['market_volatility', 'market_skewness', 'market_kurtosis']

## Data Files Generated
- `data/derived/btc_usd/event_study_data.parquet` - Event study data
- `data/derived/btc_usd/granger_causality_data.parquet` - Granger causality data
- `data/derived/btc_usd/cointegration_data.parquet` - Cointegration data
- `data/derived/btc_usd/markov_switching_data.parquet` - Markov switching data
- `data/derived/btc_usd/svar_data.parquet` - SVAR data

## Status: ✅ READY FOR WAVE-2 TESTING

All variables prepared and ready for econometric deepening tests.
