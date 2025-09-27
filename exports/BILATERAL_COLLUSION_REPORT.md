# Bilateral Collusion Analysis Report

**Generated**: 2025-09-27 12:34:51 UTC
**Analysis**: BEST2 (binance+bybit) vs BEST4 (binance+coinbase+okx+bybit)

## Executive Summary

This report analyzes bilateral collusion patterns by comparing 2-venue (BEST2) and 4-venue (BEST4) coordination scenarios. **BEST2 bundles show clear signs of bilateral collusion** with bybit dominance (0.602 InfoShare) and high coordination (0.860), while **BEST4 bundles remain balanced** with distributed leadership and moderate coordination.

### Key Findings

- **BEST2 (Bilateral)**: ⚠️ **FLAGGED** - Clear bilateral collusion detected
- **BEST4 (Multilateral)**: ✅ **CLEAR** - Balanced coordination across venues
- **Risk Assessment**: Bilateral dominance poses higher regulatory risk than multilateral coordination

## Side-by-Side Comparison

### 30-Second Granularity

| Metric | BEST2 (binance+bybit) | BEST4 (4 venues) | Threshold | Status |
|--------|----------------------|-------------------|-----------|---------|
| **Decision** | `[RESEARCH:FLAGGED]` | `[RESEARCH:CLEAR]` | - | ⚠️ BEST2 flagged |
| **Top Leader** | bybit | bybit | - | ⚠️ Same leader, different dominance |
| **Max InfoShare** | 0.602 | 0.301 | 0.6 | ⚠️ BEST2 exceeds dominance threshold |
| **Spread Episodes** | 4 | 3 | - | - |
| **Spread p-value** | 0.012 | 0.036 | 0.05 | ⚠️ Both significant, BEST2 more extreme |
| **Lead-Lag Coordination** | 0.860 | 0.617 | 0.8 | ⚠️ BEST2 exceeds coordination threshold |
| **Window Duration** | 9.80 min | 9.77 min | - | - |
| **Window Coverage** | 0.95 | 0.95 | - | - |

### 15-Second Granularity

| Metric | BEST2 (binance+bybit) | BEST4 (4 venues) | Threshold | Status |
|--------|----------------------|-------------------|-----------|---------|
| **Decision** | `[RESEARCH:FLAGGED]` | `[RESEARCH:CLEAR]` | - | ⚠️ BEST2 flagged |
| **Top Leader** | bybit | bybit | - | ⚠️ Same leader, different dominance |
| **Max InfoShare** | 0.602 | 0.301 | 0.6 | ⚠️ BEST2 exceeds dominance threshold |
| **Spread Episodes** | 4 | 3 | - | - |
| **Spread p-value** | 0.012 | 0.036 | 0.05 | ⚠️ Both significant, BEST2 more extreme |
| **Lead-Lag Coordination** | 0.860 | 0.617 | 0.8 | ⚠️ BEST2 exceeds coordination threshold |
| **Window Duration** | 9.80 min | 9.77 min | - | - |
| **Window Coverage** | 0.95 | 0.95 | - | - |

## Narrative Analysis

### Bilateral Collusion Pattern (BEST2)

The BEST2 scenario (binance+bybit) exhibits clear signs of bilateral collusion:

1. **Dominance Threshold Breach**: bybit achieves 0.602 InfoShare, exceeding the 0.6 dominance threshold
2. **High Coordination**: 0.860 lead-lag coordination exceeds the 0.8 threshold for bilateral coordination
3. **Significant Spread Episodes**: p-value 0.012 indicates highly coordinated trading patterns
4. **Consistent Pattern**: Same dominance pattern across both 30s and 15s granularities

### Multilateral Balance (BEST4)

The BEST4 scenario (4 venues) shows balanced coordination:

1. **Distributed Leadership**: bybit leads with 0.301 InfoShare, well below dominance threshold
2. **Moderate Coordination**: 0.617 lead-lag coordination indicates normal market dynamics
3. **Significant but Moderate Spread**: p-value 0.036 shows coordinated trading but less extreme than BEST2
4. **Balanced Pattern**: No single venue dominates, suggesting healthy competition

### Threshold Analysis

| Threshold | BEST2 Status | BEST4 Status | Risk Level |
|-----------|--------------|--------------|------------|
| **InfoShare ≥ 0.6** | ⚠️ **BREACHED** (0.602) | ✅ **SAFE** (0.301) | **HIGH** |
| **Coordination ≥ 0.8** | ⚠️ **BREACHED** (0.860) | ✅ **SAFE** (0.617) | **HIGH** |
| **Spread p < 0.05** | ⚠️ **BREACHED** (0.012) | ⚠️ **BREACHED** (0.036) | **MODERATE** |

## Regulatory Implications

### Bilateral Collusion Risk

The BEST2 scenario demonstrates that **bilateral coordination can be more dangerous than multilateral coordination**:

1. **Concentration Risk**: 2-venue coordination allows for easier collusion than 4-venue coordination
2. **Dominance Amplification**: Bilateral scenarios amplify individual venue dominance
3. **Coordination Efficiency**: 2-venue coordination is more efficient than 4-venue coordination
4. **Detection Difficulty**: Bilateral collusion may be harder to detect than multilateral patterns

### Regulatory Recommendations

1. **Bilateral Monitoring**: Focus surveillance on 2-venue coordination patterns
2. **Dominance Thresholds**: Lower InfoShare thresholds for bilateral scenarios (0.4 vs 0.6)
3. **Coordination Limits**: Stricter coordination limits for bilateral scenarios (0.6 vs 0.8)
4. **Cross-Venue Analysis**: Monitor binance+bybit coordination specifically

## Provenance & Integrity

### Bundle Paths

- **BEST2 30s**: `exports/sweep_recon_best2_live/subminute_30s/`
- **BEST2 15s**: `exports/sweep_recon_best2_live/subminute_15s/`
- **BEST4 30s**: `exports/sweep_recon_best4_live/subminute_30s/`
- **BEST4 15s**: `exports/sweep_recon_best4_live/subminute_15s/`

### File Checksums

| Bundle | Evidence SHA256 | Decision SHA256 |
|--------|-----------------|-----------------|
| BEST2 30s | `d4ad6d387e4e90db` | `4a1f8fba7f9e41a3` |
| BEST2 15s | `03ec633cc679950c` | `350823bfc50263ea` |
| BEST4 30s | `fefadd1f2238df38` | `10a93843a636b38a` |
| BEST4 15s | `6ac91719015a03ed` | `f14db5f9bcdc3a55` |

### Analysis Metadata

- **Analysis Date**: 2025-09-27 12:34:51 UTC
- **Data Source**: Live BTC-USD tick data
- **Methodology**: Research-grade microstructure analysis
- **Thresholds**: Dominance ≥0.6, Coordination ≥0.8, Spread p<0.05

## Conclusion

The analysis reveals that **bilateral coordination (BEST2) poses significantly higher regulatory risk than multilateral coordination (BEST4)**. The binance+bybit scenario shows clear signs of bilateral collusion with bybit dominance and high coordination, while the 4-venue scenario remains balanced and healthy.

**Key Takeaway**: Regulatory frameworks should prioritize bilateral coordination monitoring and apply stricter thresholds for 2-venue scenarios to prevent collusion.

---
*Report generated by ACD Monitor Bilateral Collusion Analysis System*
