# Gold Hunt Phase 1 - Section B: Null Baselines

## Summary

### Timestamp Shuffle

- **Real Episodes**: 6
- **Shuffle Mean**: 3.00 ± 1.69
- **Episodes Percentile**: 94.9%
- **Real Avg Lift**: 0.828
- **Shuffle Lift Mean**: 0.200 ± 0.058
- **Lift Percentile**: 100.0%

**⚠️ CAUTION**: Real episodes within normal range of null
**Interpretation**: Cannot distinguish from random variation

### Venue Relabel

- **Real Episodes**: 6
- **Shuffle Mean**: 3.07 ± 1.82
- **Episodes Percentile**: 93.3%
- **Real Leaders**: {'coinbase': 3, 'binance': 1, 'okx': 1, 'kraken': 1}
- **Shuffle Leaders**: {'coinbase': 298, 'bybit': 334, 'okx': 304, 'binance': 288, 'kraken': 313}

**✅ GOOD**: Real episodes within normal range of null
**Interpretation**: No venue-specific coordination

### Low Activity

- **Real Episodes**: 6
- **Low-Vol Episodes**: 4
- **Episodes Ratio**: 0.67
- **Real Avg Lift**: 0.828
- **Low-Vol Avg Lift**: 0.579
- **Lift Ratio**: 0.70

**⚠️ WARNING**: Episodes persist in low-vol
**Interpretation**: Episodes may be genuine coordination
