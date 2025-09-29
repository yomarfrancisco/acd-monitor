# Environment Partition Notes - Spread v2 Calibration

**Date**: 2025-09-29  
**Scope**: BTC-USD calibration (Phase 0)  
**Data**: 4 high-quality windows (12:00-14:00 UTC)  

## Current Data Inventory

### Available Windows
| Window | Coverage | Venues | Status |
|--------|----------|--------|--------|
| 1200-1230 | 96.8% | 5 venues | ✅ Quality |
| 1230-1300 | 96.3% | 5 venues | ✅ Quality |
| 1300-1330 | 98.2% | 5 venues | ✅ Quality |
| 1330-1400 | 97.0% | 5 venues | ✅ Quality |

**Total**: 4 quality windows, 2-hour time span, 5 venues each

## Environment Partition Strategy

### Today's Pragmatic Partition (Phase 0)

Given the limited data (4 windows, 2-hour span), we use a simplified partition:

#### Volatility Environment
- **Partition**: 2 bins (instead of 3)
  - **Low Volatility**: Windows with realized volatility < median
  - **High Volatility**: Windows with realized volatility ≥ median
- **Rationale**: Insufficient data for 3 bins; 2 bins provide meaningful contrast
- **Future**: Expand to 3 bins (low/mid/high) when we have ≥12 windows

#### Liquidity Environment  
- **Partition**: 1 bin (all windows combined)
- **Rationale**: Insufficient data for meaningful liquidity partitioning
- **Future**: Add liquidity bins when we have ≥20 windows with volume data

#### Time-of-Day Environment
- **Partition**: 2 bins
  - **Early**: 1200-1300 UTC (2 windows)
  - **Late**: 1300-1400 UTC (2 windows)
- **Rationale**: Natural time-based partition with equal sample sizes
- **Future**: Add more time bins when we have extended capture

#### VWAP Environment
- **Partition**: 2 bins
  - **Below VWAP**: Windows with average price below daily VWAP
  - **Above VWAP**: Windows with average price above daily VWAP
- **Rationale**: VWAP provides daily anchor for price level analysis
- **Calculation**: Daily VWAP at 0h00 GMT as reference point

#### High/Low Environment
- **Partition**: 3 bins
  - **Near High**: Windows within 5% of daily high
  - **Mid Range**: Windows in middle 70% of daily range
  - **Near Low**: Windows within 5% of daily low
- **Rationale**: Price level relative to daily extremes affects spread behavior
- **Future**: Add weekly and monthly high/low references

#### Trading Session Environment
- **Partition**: 4 bins
  - **Asia**: 00:00-08:00 UTC (Asian trading hours)
  - **Europe**: 08:00-16:00 UTC (European trading hours)
  - **US**: 16:00-24:00 UTC (US trading hours)
  - **Overlap**: 08:00-16:00 UTC (Europe-US overlap)
- **Rationale**: Different trading sessions have distinct liquidity patterns
- **Future**: Add more granular session analysis

### Environment Bins Summary

| Environment | Bins | Rationale | Future Plan |
|-------------|------|-----------|-------------|
| **Volatility** | 2 (low/high) | Insufficient data for 3 bins | Expand to 3 bins with ≥12 windows |
| **Liquidity** | 1 (combined) | Insufficient data for partitioning | Add liquidity bins with ≥20 windows |
| **Time-of-Day** | 2 (early/late) | Natural partition with equal samples | Add more time bins with extended capture |
| **VWAP** | 2 (below/above) | Daily anchor for price level analysis | Add intraday VWAP references |
| **High/Low** | 3 (near high/mid/near low) | Price level relative to daily extremes | Add weekly/monthly references |
| **Trading Session** | 4 (Asia/Europe/US/Overlap) | Different liquidity patterns by session | Add more granular session analysis |

### Merging Strategy

If any bin has <2 windows, merge according to:
1. **Volatility**: Merge low+high if either has <2 windows
2. **Liquidity**: Keep as single bin (all windows combined)
3. **Time-of-Day**: Merge early+late if either has <2 windows

### Future Partition (Extended Data)

When we have richer data (≥30 windows, ≥7 days):

#### Volatility Environment
- **3 bins**: Low (bottom 33%), Mid (middle 33%), High (top 33%)
- **Threshold**: 20-day rolling realized volatility

#### Liquidity Environment
- **3 bins**: Low (bottom 33%), Mid (middle 33%), High (top 33%)
- **Threshold**: Average bid-ask spread, volume-weighted

#### Time-of-Day Environment
- **4 bins**: Morning (06:00-12:00), Afternoon (12:00-18:00), Evening (18:00-00:00), Night (00:00-06:00)
- **Rationale**: Capture intraday patterns and timezone effects

#### Policy/Regulatory Environment
- **2 bins**: Normal periods, Event periods
- **Events**: ETF approvals, regulatory announcements, major news
- **Rationale**: Test invariance across regulatory shocks

## Implementation Notes

### Current Limitations
- **Sample Size**: 4 windows is minimal for robust environment analysis
- **Time Span**: 2-hour window limits temporal pattern detection
- **Regime Coverage**: Single market regime (no stress testing)

### Calibration Approach
- **Baseline Estimation**: Use all 4 windows for baseline spread estimation
- **Environment Contrast**: Compare volatility bins (low vs high)
- **Synthetic Validation**: Use 36 synthetic datasets for detector calibration
- **Provisional Thresholds**: Mark all results as provisional until extended validation

### Next Steps
1. **Immediate**: Run baseline estimation on current 4 windows
2. **Short-term**: Extend capture to 30+ windows for robust environment analysis
3. **Medium-term**: Add liquidity and policy/regulatory environments
4. **Long-term**: Cross-asset validation (ETH-USD) and multi-regime testing

---
*This document reflects the pragmatic approach for Phase 0 calibration with limited data. All partitions and thresholds are provisional and will be refined with extended datasets.*
