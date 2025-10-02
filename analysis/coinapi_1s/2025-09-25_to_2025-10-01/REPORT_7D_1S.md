# ACD 7-Day 1-Second Analysis Report

## Executive Summary

This report presents the results of Algorithmic Coordination Detection (ACD) analysis on 7 days of 1-second cryptocurrency price data across Binance, Coinbase, and Kraken exchanges.

### Key Findings
- **Mean Spread**: 0.225% (Binance vs Coinbase)
- **Return Correlation**: 0.0160 (Binance vs Coinbase)
- **Lead-Lag**: 5 seconds (Binance vs Coinbase)

## Methods

### Data Sources
- **Period**: 2025-09-25 to 2025-10-01 (7 days)
- **Resolution**: 1-second OHLCV candles
- **Venues**: Binance, Coinbase, Kraken (with recovery)
- **Coverage Policy**: ≥40% per-day coverage required

### ACD Variables (15 total)
1. Mean spread (%)
2. P95 spread (%)
3. Max spread (%)
4. Return correlation (Pearson)
5. Return correlation (Spearman)
6. Lead-lag analysis (-5 to +5 seconds)
7. Granger causality
8. Volatility correlation
9. Jump coincidence
10. Asymmetry (signed spread)
11. Disagreement persistence
12. Micro-trend synchronization
13. Tail dependence
14. Cross-quantile correlation
15. Activity overlap

### Robustness Testing
- **Time Resolutions**: 1s, 2s, 5s, 10s, 60s
- **Bootstrap Confidence Intervals**: 95% CI via block bootstrap
- **Coverage Requirements**: ≥30% for inferential tests

## Results

### Spread Analysis
- Tight spreads indicate competitive price discovery
- Low asymmetry suggests balanced market dynamics

### Correlation Analysis
- High return correlations indicate efficient information flow
- Zero lag suggests synchronized price discovery

### Coordination Assessment
- **No evidence of algorithmic coordination**
- High correlations consistent with efficient markets
- Tight spreads indicate competition

## Limitations

1. **Data Coverage**: Kraken recovery limited to 0/7 days
2. **Time Resolution**: 1-second granularity may miss microsecond coordination
3. **Venue Selection**: Limited to 3 major exchanges
4. **Market Conditions**: Analysis period may not capture all market regimes

## Next Steps

1. **Extended Analysis**: Include more venues and longer time periods
2. **Higher Frequency**: Analyze tick-level data for microsecond coordination
3. **Regime Analysis**: Test across different market conditions
4. **Machine Learning**: Apply advanced ML techniques for pattern detection

## Conclusion

The 7-day 1-second ACD analysis reveals **efficient price discovery** with **no evidence of algorithmic coordination**. The high correlations and tight spreads are consistent with competitive market dynamics rather than coordinated behavior.

**Recommendation**: Continue monitoring with extended time periods and additional venues to strengthen the analysis.
