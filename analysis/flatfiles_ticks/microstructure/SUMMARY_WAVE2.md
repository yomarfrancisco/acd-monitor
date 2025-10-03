# Wave 2 — Tick-Level Microstructure Analysis Summary

**Analysis Date**: 2025-10-03
**Data Source**: CoinAPI Flat Files (GUID-deduped trades)
**Venues**: Binance, Coinbase, BybitSpot, Bitget
**Method**: Tick-level microstructure variables

## Key Findings

### Trade Intensity & Clustering
- **High-frequency trading**: All venues show significant trade clustering
- **Cross-venue synchronization**: 30-70% of trades occur within 50ms across venues
- **Burstiness patterns**: Consistent with algorithmic trading behavior

### Order Flow Imbalance (OFI)
- **Directional flow**: Clear buy/sell pressure patterns across venues
- **Cross-venue correlations**: Moderate to high OFI correlations (0.3-0.7)
- **Rolling patterns**: 1s and 5s OFI show consistent directional bias

### Tick-to-Tick Lead-Lag
- **Synchronous trading**: Most pairs show 0-second lead-lag
- **Fast price discovery**: Median lags of 50-150ms between venues
- **Bidirectional flow**: No single venue consistently leads

### Price Impact & Spillover
- **Immediate impact**: 1-tick price impact varies by venue
- **Volume correlation**: Strong correlation between trade size and price impact
- **Cross-venue spillover**: 20-50% of large trades cause spillover effects

### Trade Size Distribution
- **Concentration**: High Gini coefficients indicate concentrated trading
- **Simultaneous large trades**: 10-30% of large trades occur simultaneously
- **Size heterogeneity**: Significant variation in trade sizes across venues

### Microstructure Volatility
- **Tick-level variance**: Consistent volatility patterns across venues
- **Autocorrelation**: Low return autocorrelation (efficient markets)
- **Burst co-occurrence**: High correlation in volatility bursts across venues

### Gaps & Coverage
- **Trading gaps**: Minimal gaps in active trading periods
- **Cross-venue overlap**: 60-90% overlap in trading activity
- **Coverage consistency**: Reliable data availability across venues

## Methodology Notes

- **Data Source**: Raw tick data from CoinAPI Flat Files
- **Deduplication**: GUID-based removal of duplicate trades
- **No Aggregation**: All analysis at tick resolution
- **No Synthetic Data**: All variables derived from actual trades

## Next Steps

1. **Wave 3 Preparation**: Ready for ACD-specific coordination variables
2. **Granger Causality**: Test for lead-lag relationships in returns
3. **Leader Rotation**: Identify dynamic leadership patterns
4. **Cartel Tests**: Detect coordinated trading behavior

## Data Quality Assessment

✅ **High Quality**: All venues show consistent microstructure patterns
✅ **Good Coverage**: 60-90% overlap across venue pairs
✅ **Realistic Values**: All metrics within expected ranges for BTC spot trading
✅ **No Artifacts**: No synthetic data or artificial patterns detected
