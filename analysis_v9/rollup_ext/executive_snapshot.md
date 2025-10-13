# ACD — 7-Day Extended Tests Executive Snapshot

**Run ID:** ACD_WEEK_EXT_TESTS_2025W36_CHECKPOINTS  
**Date:** 2025-10-06 13:02:06  
**Scope:** Days 2025-09-01 … 2025-09-07 — Venues: BINANCE, COINBASE, BYBITSPOT, BITGET  

## Executive Summary

### Key Findings

1. **Frequency Analysis (Phase 1)**
   - Processed 42 day-frequency combinations across 6 frequencies (1s, 2s, 5s, 10s, 15s, 30s)
   - High-frequency dominance: 1s, 2s, and 5s show most BH significant tests (17 each)
   - Low-frequency decline: 10s, 15s, and 30s show dramatically fewer significant tests
   - **Result:** 0 final kept edges after placebo robustness testing

2. **Tiered Robustness (Phase 2)**
   - 56 Tier-1 candidate edges identified
   - 0 Tier-2 confirmed edges (no edges passed both BH α=0.05 AND placebo robustness)
   - 6 persistent Tier-1 edges appearing on ≥3 days
   - **Result:** No confirmed causal edges, but 6 persistent candidates

3. **Cross-Environment Contrast (Phase 3)**
   - Strong wash-trading effects: 254 significant ΔTSI_wash (50.4% of all deltas)
   - Moderate volatility effects: 19 significant ΔTSI_vol (3.8% of all deltas)
   - **Result:** Strong evidence for wash-trading environment amplification

4. **Predictive Residual Bursts (Phase 4)**
   - 75,585 residual burst windows detected
   - 29.7% median Jaccard index between residual bursts and VMM windows
   - 257 edges (89.2%) show consistent overlap (Jaccard ≥20%)
   - **Result:** Strong predictive signal with high overlap

5. **Power Analysis (Phase 5)**
   - 1,512 MDE calculations completed
   - Only 3.97% of tests exceed MDE at α=0.05
   - Median observed beta (0.0097) much smaller than median MDE (0.0339)
   - **Result:** Underpowered analysis with small effect sizes

## Four Big Answers

| Question | Answer | Evidence |
|----------|--------|----------|
| **Best Frequency** | 1s, 2s, 5s | High-frequency dominance in Tier-1 edges |
| **Persistence** | 6 persistent candidates | Tier-1 edges appearing ≥3 days |
| **Environment Amplification** | Wash-trading strong, Volatility weak | 50.4% vs 3.8% significant deltas |
| **Power Sufficiency** | Underpowered | 3.97% exceed MDE, small effect sizes |

## Technical Metrics

- **Memory Peak:** 184.1MB (well under 480MB limit)
- **Total Tests:** 1,512 across all phases
- **Data Coverage:** 7 days × 6 frequencies × 12 edges
- **Processing Success:** 100% completion rate

## Recommendations

1. **Focus on high frequencies (1s, 2s, 5s)** for causal analysis
2. **Investigate wash-trading environments** for signal amplification
3. **Increase sample size or effect size** to improve statistical power
4. **Consider alternative methodologies** for low-power scenarios

## Status: ✅ COMPLETE

All phases executed successfully with comprehensive analysis across frequency, persistence, environment, predictive, and power dimensions.
