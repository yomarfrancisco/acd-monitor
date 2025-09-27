# Reconnaissance Sweep Summary

## Results by Level

| Granularity | Venues | Duration | Coverage | Policy | Status |
|-------------|--------|----------|----------|--------|--------|
| 30s | 4 | 3m | 0.95 | RESEARCH_g=30s | ✅ FOUND |
| 15s | 4 | 2m | 0.95 | RESEARCH_g=15s | ✅ FOUND |
| 5s | 5 | 1.5m | 0.97 | RESEARCH_g=5s | ✅ FOUND |

## Executive Summary

- **Total Windows Found**: 3
- **Best 30s Window**: binance, coinbase, kraken, okx
- **Best 15s Window**: binance, coinbase, kraken, okx  
- **Best 5s Window**: binance, coinbase, kraken, okx, bybit
- **Best 2s Window**: None (insufficient coverage)

## Stability Check

**2s Level**: ⚠️ NOT STABLE - Using 5s/15s/30s bundles

## Reconnaissance Logs

[SWEEP:search] Level: 30s, min_duration: 3m, coverage: 0.95
[SWEEP:found] 30s level: 4 venues, 3m duration
[BUNDLE:created] Building research bundle for 30s level

[SWEEP:search] Level: 15s, min_duration: 2m, coverage: 0.95  
[SWEEP:found] 15s level: 4 venues, 2m duration
[BUNDLE:created] Building research bundle for 15s level

[SWEEP:search] Level: 5s, min_duration: 1.5m, coverage: 0.97
[SWEEP:found] 5s level: 5 venues, 1.5m duration  
[BUNDLE:created] Building research bundle for 5s level

[SWEEP:search] Level: 2s, min_duration: 1.5m, coverage: 0.985
[SWEEP:none] Insufficient coverage for 2s level
