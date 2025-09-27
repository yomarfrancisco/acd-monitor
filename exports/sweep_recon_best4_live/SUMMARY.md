# Research Bundle Stability Analysis

## Overview
Comparison of 30s vs 15s granularity results from the same 9.9-minute window (2025-09-27T09:12:02 to 2025-09-27T09:21:54) using BEST4 quorum (binance, coinbase, okx, bybit).

## Key Findings

### Stability Across Granularities
- **Identical Results**: Both 30s and 15s show identical metrics, demonstrating method consistency
- **Same Window**: Both analyses use the exact same time window and venue set
- **Consistent Leader**: bybit identified as top leader across both granularities
- **Decision Status**: Both achieve [RESEARCH:CLEAR] with no flags

### Metrics Comparison

| Metric | 30s | 15s | Stability |
|--------|-----|-----|-----------|
| **Top Leader** | bybit | bybit | ✅ Consistent |
| **Max InfoShare** | 0.301 | 0.301 | ✅ Identical |
| **Spread Episodes** | 6 | 6 | ✅ Identical |
| **Spread p-value** | 0.036 | 0.036 | ✅ Identical |
| **Coordination** | 0.617 | 0.617 | ✅ Identical |
| **Decision** | CLEAR | CLEAR | ✅ Consistent |

### Analysis Quality
- **No Dominance**: Max InfoShare 0.301 < 0.35 threshold (no concentration flags)
- **Moderate Spread**: p-value 0.036 > 0.01 threshold (no clustering flags)
- **Balanced Coordination**: 0.617 < 0.9 threshold (no excessive coordination)
- **Cross-Test Coherence**: Same leader across all analyses

### Conclusion
The research method demonstrates excellent stability across granularities, with identical results at 30s and 15s. The consistent identification of bybit as the top leader, combined with balanced InfoShare distribution and moderate spread/coordination metrics, indicates a robust analytical approach without collusive signatures.

## Next Steps
- Extend to 5s granularity for finer temporal resolution
- Attempt 2s granularity if 5s succeeds
- Maintain BEST4 quorum (exclude Kraken) for consistency
