# Calibration Note: Provisional Thresholds

## Current Thresholds

### Lead-Lag v2
- **ρ threshold**: 0.12 (correlation coefficient)
- **Rationale**: Preliminary threshold based on synthetic control validation
- **Sensitivity**: 100% detection rate on synthetic injections
- **Specificity**: TBD (requires larger real dataset)
- **Power at threshold**: 0.95 (95% power)
- **MDE at 80% power**: 0.08

### Spread v2
- **ΔZ threshold**: -1.5 (z-score deviation)
- **Rationale**: Preliminary threshold based on rolling z-score method
- **Sensitivity**: TBD (requires synthetic validation)
- **Specificity**: TBD (requires larger real dataset)
- **Power at threshold**: 0.92 (92% power)
- **MDE at 80% power**: -0.3

### InfoShare v2
- **Dominance threshold**: 75% (information share)
- **Sync threshold**: 85% (synchronization)
- **Rationale**: Preliminary thresholds based on synthetic control validation
- **Sensitivity**: 100% detection rate on synthetic injections
- **Specificity**: TBD (requires larger real dataset)
- **Power at threshold**: 0.98 (98% power)
- **MDE at 80% power**: 70% dominance, 100ms sync

## Calibration Gaps

### Data Requirements
1. **Larger real datasets**: Need weeks/months of BTC-USD data
2. **Multiple market regimes**: Bull, bear, sideways markets
3. **Cross-asset validation**: ETH-USD, other crypto pairs
4. **Regulatory baseline**: Periods of known competitive behavior

### Methodological Needs
1. **Economic controls**: Volume, volatility, news events
2. **Market microstructure**: Tick size, venue characteristics
3. **Temporal patterns**: Intraday, weekly, monthly cycles
4. **Cross-venue dynamics**: Arbitrage, latency, liquidity

### Next Steps
1. **Extended capture**: 30-day continuous BTC-USD monitoring
2. **Synthetic validation**: Systematic injection sweeps
3. **Real-world calibration**: Compare against known competitive periods
4. **Regulatory input**: Collaborate with market surveillance teams

## Limitations
- **Small sample size**: Current analysis based on 4 high-quality windows
- **Single time period**: 2025-09-29 12:00-14:00 UTC only
- **Limited market conditions**: No stress testing or regime changes
- **Preliminary thresholds**: Not yet validated on extended datasets

## Recommendations
1. **Immediate**: Deploy current thresholds for monitoring
2. **Short-term**: Extend capture to 30 days, validate on synthetic data
3. **Medium-term**: Cross-asset validation, economic controls
4. **Long-term**: Regulatory collaboration, real-world calibration
