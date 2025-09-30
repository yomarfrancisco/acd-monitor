# Wave-1 Variable Preparation Summary

## Overview
Successfully prepared variables for Wave-1 econometric tests (Baseline Statistical Screens) for both BTC-USD and ETH-USD.

## Data Coverage
- **BTC-USD**: 5 venues, ~23K ticks per venue
- **ETH-USD**: 5 venues, ~22K ticks per venue
- **Time Range**: Last 7 days of capture data
- **Data Quality**: All venues present with sufficient tick data

## Variables Prepared

### 1. Variance Ratio Test Variables
- **Purpose**: Test for random walk vs mean reversion patterns
- **Metrics**: Variance ratios for lags 2, 4, 8, 16, 32
- **Status**: ✅ Complete for all venues

### 2. Autocorrelation & AR(1) Decay Variables  
- **Purpose**: Measure persistence in price movements
- **Metrics**: Autocorrelations for lags 1, 2, 3, 5, 10, 20; AR(1) coefficients
- **Status**: ✅ Complete for all venues

### 3. Cross-Correlation Variables
- **Purpose**: Measure synchronization across venues
- **Metrics**: Price and spread correlations between venue pairs
- **Status**: ⚠️ Limited by data alignment requirements

### 4. PCA Loadings / Common Factor Analysis
- **Purpose**: Identify dominant coordination factors
- **Metrics**: Explained variance ratios, component loadings, first component analysis
- **Status**: ⚠️ Limited by data alignment requirements

### 5. Rolling Volatility & Spread Convergence
- **Purpose**: Measure artificial stability in spreads/volatility
- **Metrics**: Rolling volatility statistics, spread convergence metrics
- **Status**: ✅ Complete for all venues

## Key Findings

### BTC-USD Variance Ratios
- **Binance/Kraken/OKX/Bybit**: Low variance ratios (0.3-0.9) suggesting mean reversion
- **Coinbase**: High variance ratios (1.5-18.4) suggesting trending behavior
- **Interpretation**: Coinbase shows different price dynamics than other venues

### ETH-USD Variance Ratios  
- **All Venues**: Consistent low variance ratios (0.3-0.6) across all lags
- **Interpretation**: More uniform behavior across venues compared to BTC-USD

### Data Quality
- **Schema Alignment**: ✅ Canonical tick schema enforced
- **Timezone Handling**: ✅ All timestamps normalized to UTC
- **Venue Coverage**: ✅ 5/5 venues present for both symbols
- **Data Volume**: ✅ Sufficient tick data for statistical analysis

## Next Steps
1. **Review Variables**: Validate that prepared variables align with econometric test requirements
2. **Run Wave-1 Tests**: Execute the 5 baseline statistical screens
3. **Prepare Wave-2**: Move to econometric deepening tests (6-10)
4. **Prepare Wave-3**: Advanced ML & collusion screens (11-15)

## Files Generated
- `reports/wave1_variables_btc_usd.json` - BTC-USD variables
- `reports/wave1_variables_eth_usd.json` - ETH-USD variables  
- `scripts/analytics/prepare_wave1_variables.py` - Preparation script

## Status: ✅ READY FOR WAVE-1 TESTING
