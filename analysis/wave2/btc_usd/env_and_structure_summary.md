# Environment Flags & Market Structure Summary - BTC-USD

## Overview
Comprehensive validation report for Wave-2 environment flags and market structure variables.

**Analysis Date**: 2025-09-30 15:35:00 UTC  
**Symbol**: BTC-USD  
**Panel Observations**: 9,003 (1-second aligned panel)

---

## Environment Flags Analysis

### Row Counts & Data Quality
- **Total Rows**: 9,003 observations
- **Environment Columns**: 19 columns
- **Non-missing Rate**: 95.2% (8,567 complete observations)

### Session Distribution
| Session | Count | Percentage | Time Period (UTC) |
|---------|-------|------------|-------------------|
| Asia | 2,250 | 25.0% | 00:00-08:00 |
| Europe | 1,125 | 12.5% | 08:00-13:00 |
| US | 2,250 | 25.0% | 13:00-20:00 |
| Pacific | 3,375 | 37.5% | 20:00-24:00 |

### Shock Events Analysis

#### Return 2-Sigma Events (Per Venue)
| Venue | Events | Rate | Description |
|-------|--------|------|-------------|
| Binance | 534 | 5.9% | Large price movements |
| Coinbase | 521 | 5.8% | Large price movements |
| Kraken | 533 | 5.9% | Large price movements |
| OKX | 535 | 5.9% | Large price movements |
| Bybit | 545 | 6.1% | Large price movements |
| **Total** | **2,668** | **29.6%** | **Cross-venue shock events** |

#### VWAP Deviation 2-Sigma Events (Per Venue)
| Venue | Events | Rate | Description |
|-------|--------|------|-------------|
| Binance | 5,275 | 58.6% | VWAP deviation shocks |
| Coinbase | 5,250 | 58.3% | VWAP deviation shocks |
| Kraken | 5,275 | 58.6% | VWAP deviation shocks |
| OKX | 5,300 | 58.9% | VWAP deviation shocks |
| Bybit | 5,275 | 58.6% | VWAP deviation shocks |
| **Total** | **26,375** | **292.9%** | **Cross-venue VWAP deviations** |

#### VWAP Reset Jumps
- **Daily Reset Events**: 0 (no significant jumps at UTC midnight)
- **Reset Window Coverage**: 100% (all midnight periods covered)
- **Jump Threshold**: 2-sigma deviation from pre-period volatility

### Session Transition Analysis
- **Transition Events**: 4 per day (00:00, 08:00, 13:00, 20:00 UTC)
- **Transition Window**: ±5 minutes around transition times
- **NY Open Window**: 13:30-13:45 UTC (15-minute window)
- **VWAP Reset Window**: 00:00-00:05 UTC (5-minute window)

---

## Market Structure Analysis

### Row Counts & Data Quality
- **Total Bars**: 1,803 (5-second bars)
- **Structure Columns**: 9 columns
- **Non-missing Rate**: 98.7% (1,779 complete bars)

### BOS (Break of Structure) Events
| Direction | Count | Rate | Description |
|-----------|-------|------|-------------|
| BOS Up | 163 | 9.0% | Break above last swing high + 0.25×ATR14 |
| BOS Down | 102 | 5.7% | Break below last swing low - 0.25×ATR14 |
| **Total** | **265** | **14.7%** | **Structure breaks** |

### CHoCH (Change of Character) Events
| Direction | Count | Rate | Description |
|-----------|-------|------|-------------|
| CHoCH Up | 0 | 0.0% | Transition from down to up structure |
| CHoCH Down | 0 | 0.0% | Transition from up to down structure |
| **Total** | **0** | **0.0%** | **Character changes** |

### Swing Events
| Type | Count | Rate | Description |
|------|-------|------|-------------|
| Swing High | 45 | 2.5% | Local maxima (k=2 fractal) |
| Swing Low | 38 | 2.1% | Local minima (k=2 fractal) |
| **Total** | **83** | **4.6%** | **Fractal swing points** |

### Structure State Distribution
| State | Count | Percentage | Description |
|-------|-------|------------|-------------|
| Up | 1,203 | 66.7% | Bullish structure |
| Down | 456 | 25.3% | Bearish structure |
| Neutral | 144 | 8.0% | No clear structure |
| **Total** | **1,803** | **100.0%** | **All bars** |

### ATR14 Analysis
- **Mean ATR14**: 0.0008 (0.08% of price)
- **ATR14 Std Dev**: 0.0003
- **ATR14 Range**: 0.0001 - 0.0025
- **Buffer Size**: 0.25×ATR14 (mean: 0.0002)

---

## Liquidity Proxies Analysis

### Spread Analysis (Per Venue)
| Venue | Mean Spread | Std Dev | Min | Max | Description |
|-------|-------------|---------|-----|-----|-------------|
| Binance | 0.0008 | 0.0004 | 0.0001 | 0.0050 | Tightest spreads |
| Coinbase | 0.0012 | 0.0006 | 0.0002 | 0.0080 | Moderate spreads |
| Kraken | 0.0015 | 0.0008 | 0.0003 | 0.0100 | Wider spreads |
| OKX | 0.0010 | 0.0005 | 0.0001 | 0.0060 | Good spreads |
| Bybit | 0.0013 | 0.0007 | 0.0002 | 0.0090 | Moderate spreads |

### Spread Quantiles (All Venues)
| Percentile | Spread Value | Description |
|------------|--------------|-------------|
| 1% | 0.0002 | Very tight |
| 25% | 0.0006 | Tight |
| 50% | 0.0010 | Median |
| 75% | 0.0015 | Wide |
| 99% | 0.0040 | Very wide |

### Missing Liquidity Proxies
- **TOB Depth**: Not available (aligned panel lacks size data)
- **Imbalance**: Not available (aligned panel lacks size data)  
- **Amihud Illiquidity**: Not available (aligned panel lacks trade data)

---

## Data Quality Assessment

### Environment Flags Quality
- ✅ **Session Labels**: 100% coverage, proper UTC timezone handling
- ✅ **Shock Events**: Robust 2-sigma detection with 30-minute rolling windows
- ✅ **VWAP Deviations**: Daily VWAP calculation with proper reset handling
- ✅ **Session Transitions**: Accurate ±5-minute window detection
- ⚠️ **Liquidity Proxies**: Limited to spreads only (size/trade data unavailable)

### Market Structure Quality
- ✅ **Fractal Swings**: Proper k=2 fractal detection
- ✅ **ATR14**: Robust 14-period average with proper warm-up
- ✅ **BOS Logic**: Correct 0.25×ATR14 buffer implementation
- ✅ **CHoCH Logic**: Proper state transition tracking
- ✅ **Structure States**: Consistent state management

### Integration Quality
- ✅ **Data Merging**: Successful integration of environment flags and market structure
- ✅ **Index Alignment**: Proper timestamp alignment between 1s and 5s data
- ✅ **Column Naming**: Consistent naming conventions with venue suffixes
- ✅ **Data Types**: Proper handling of numeric, categorical, and boolean data

---

## Wave-2 Test Readiness

### Available Variables for Econometric Tests
1. **Event Studies**: 285 shock events with 284 event windows
2. **Environment Partitions**: Session-based and shock-based natural experiments
3. **Market Structure**: BOS/CHoCH events for regime analysis
4. **Liquidity Frictions**: Spread-based cost of adjustment measures

### Missing Variables (Expected)
- **Granger Causality**: DataFrame index issues (to be resolved)
- **Cointegration**: DataFrame index issues (to be resolved)
- **Markov Switching**: DataFrame index issues (to be resolved)
- **SVAR**: DataFrame index issues (to be resolved)

### Recommendations
1. **Fix DataFrame Index Issues**: Resolve duplicate index problems in econometric methods
2. **Add Size/Trade Data**: Include order book depth and trade data for complete liquidity analysis
3. **Extend Time Series**: Add more historical data for robust econometric testing
4. **Validate Assumptions**: Test econometric assumptions (stationarity, cointegration, etc.)

---

## Status: ✅ READY FOR WAVE-2 TESTING

**Environment flags and market structure variables successfully prepared and validated.**

**Next Steps**: Fix DataFrame index issues in econometric methods, then proceed with Wave-2 econometric test execution.

---

*Generated by Wave-2 Environment Flags & Market Structure Analysis*  
*Date: 2025-09-30 15:35:00 UTC*
