# BTC Single-Day Baseline - FROZEN ARTIFACTS

**Freeze Date**: 2025-09-30T17:20:00Z  
**Git SHA**: 9f47766365321c65e106cc41c77177274cf7f3f4  
**Purpose**: Baseline artifacts for Wave-2 single-day BTC-USD analysis (no recompute)

## Core Data Files

### Panel Data
- **File**: `data/derived/btc_usd/panel_1s_inner_real_single_date.parquet`
- **Size**: 1.2MB
- **SHA256**: `ff321bea9575fea326b6e0e04af453d44cb766a3c6e3b91d36b4c0f27a6fb3f5`
- **Content**: 21,854 observations, 1-second aligned panel across 5 venues

### Environment Flags
- **File**: `data/derived/btc_usd/env_flags_1s_real_single_date.parquet`
- **Size**: 156KB
- **SHA256**: `e02300ff4db7d18401519d633d8ee3e8c0b87cae0e5729783a6962a5b3c3159f`
- **Content**: Session labels, shock flags, liquidity proxies

### Market Structure
- **File**: `data/derived/btc_usd/market_structure_real_single_date.parquet`
- **Size**: 89KB
- **SHA256**: `06a91cdc6725aab6779db8f8bee90ab39e83699d75a16e4020f11973e2af4cdc`
- **Content**: 5-second bars, fractal swings, BOS/CHoCH events

## Analysis Reports

### Comprehensive Report
- **File**: `analysis/wave2/btc_usd_comprehensive/COMPREHENSIVE_WAVE2_REPORT.md`
- **Size**: 2.5KB
- **Content**: Executive summary, key findings, coordination vs competition assessment

### Detailed Analysis Files
- **Directory**: `analysis/wave2/btc_usd_comprehensive/detailed_analysis/`
- **Files**:
  - `coordination_competition_analysis.json` (1.6KB)
  - `data_quality_metrics.json` (950B)
  - `venue_performance_metrics.json` (1.9KB)
  - `session_analysis.json` (734B)
  - `market_structure_analysis.json` (645B)
  - `advanced_econometrics.json` (4.4KB)

## Key Findings (Frozen)

### Primary Conclusion: COMPETITIVE MARKET STRUCTURE
- **Competition Score**: 2/3 indicators ✅
- **Coordination Score**: 0/3 indicators ❌
- **Overall Assessment**: **COMPETITIVE**

### Evidence Supporting Competition
1. **Low Cross-Venue Correlations**: Only 1 strong correlation (Binance-Kraken: 0.305)
2. **Independent Volatility Patterns**: Wide dispersion (2x difference between highest/lowest)
3. **Venue-Specific Risk Management**: Different risk profiles across venues

### Secondary Finding: Market-Wide Synchronization
- Some evidence of synchronized behavior during systematic events
- NY open, session transitions show coordination patterns
- Long-run alignment via universal cointegration

## Reproducibility Notes

- **Data Source**: Authentic BTC-USD data from S3 (2025-09-29)
- **Processing**: 1-second alignment, LOCF fill, winsorization
- **Venues**: Binance, Coinbase, Kraken, OKX, Bybit
- **Time Coverage**: 14.5 hours continuous data
- **Memory Constraints**: Multi-day extension attempted but failed due to memory limits

## Usage

This baseline represents the definitive Wave-2 analysis on real BTC-USD data. All artifacts are frozen and should not be recomputed. Use this as the foundation for:

1. **Wave-3 Analysis**: Advanced econometric modeling
2. **Multi-Day Extension**: When memory resources allow
3. **Comparative Studies**: Against synthetic data findings
4. **Reproducibility**: Exact checksums for verification

## Warning

**DO NOT RECOMPUTE** - These artifacts represent the final, validated state of the Wave-2 single-day analysis. Any modifications should create new files with different names.
