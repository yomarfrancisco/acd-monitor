# Wave-3 Variables Final Audit Report

**Audit Date**: 2025-09-30T19:50:22.154227
**Purpose**: Comprehensive audit of all Wave-3 variables

## Summary Table

| File | Rows | Columns | Non-Missing % | Status |
|------|------|---------|---------------|--------|
| ICP Design | 21,853 | 51 | 95.6% | ✅ |
| VMM Moments | 79 | 67 | 96.3% | ✅ |
| Copula Marginals | 21,878 | 13 | 94.2% | ✅ |
| Clustering Features | 74 | 77 | 96.4% | ✅ |
| Composite Inputs | 74 | 16 | 100.0% | ✅ |

## Detailed Audits

### ICP Design Matrix

- **Rows**: 21,853
- **Columns**: 51
- **Non-missing %**: 95.6%
- **Y variable**: 21,853 obs, mean=-0.0000
- **Environment variables**: 3 found

### VMM Moments

- **Windows**: 79
- **Columns**: 67
- **Non-missing %**: 96.3%
- **Window duration**: 30.0 min average
- **Moment columns**: 5 analyzed
- **Instrument columns**: 5 analyzed

### Copula Marginals

- **Rows**: 21,878
- **Columns**: 13
- **Non-missing %**: 94.2%
- **Session distribution**:
  - Europe: 16,222 rows
  - US: 3,541 rows
  - Asia: 1,866 rows
  - Pacific: 249 rows
- **Marginal statistics**:
  - u_ret_coinbase: [0.001, 0.999] range, 18,275 obs
  - u_ret_okx: [0.001, 0.999] range, 18,030 obs
  - u_spr_coinbase: [0.001, 0.999] range, 18,278 obs
  - u_spr_okx: [0.001, 0.999] range, 18,035 obs
  - u_dispersion: [0.001, 0.999] range, 21,878 obs
  - u_ret_binance: [0.001, 0.999] range, 21,628 obs
  - u_ret_kraken: [0.001, 0.999] range, 21,628 obs
  - u_ret_bybit: [0.001, 0.999] range, 21,628 obs
  - u_spr_binance: [0.001, 0.999] range, 21,629 obs
  - u_spr_kraken: [0.001, 0.999] range, 21,629 obs
  - u_spr_bybit: [0.001, 0.999] range, 21,629 obs
- **Tail statistics**:
  - u_ret_coinbase: 10.0% in tails (u<0.05 or u>0.95)
  - u_ret_okx: 10.0% in tails (u<0.05 or u>0.95)
  - u_spr_coinbase: 9.9% in tails (u<0.05 or u>0.95)
  - u_spr_okx: 10.0% in tails (u<0.05 or u>0.95)
  - u_dispersion: 9.9% in tails (u<0.05 or u>0.95)
  - u_ret_binance: 10.0% in tails (u<0.05 or u>0.95)
  - u_ret_kraken: 10.0% in tails (u<0.05 or u>0.95)
  - u_ret_bybit: 10.0% in tails (u<0.05 or u>0.95)
  - u_spr_binance: 10.0% in tails (u<0.05 or u>0.95)
  - u_spr_kraken: 10.0% in tails (u<0.05 or u>0.95)
  - u_spr_bybit: 10.0% in tails (u<0.05 or u>0.95)

### Clustering Features

- **Windows**: 74
- **Columns**: 77
- **Non-missing %**: 96.4%
- **Top features by variance**:
  - dispersion_95th: variance=3490610.257349
  - dispersion_mean: variance=2222837.198675
  - binance_vwap_count: variance=7195.257312
  - kraken_vwap_count: variance=7097.498704
  - bybit_vwap_count: variance=6799.449833
- **Z-score standardization**: 2,636 values, mean=0.000

### Composite Inputs

- **Windows**: 74
- **Columns**: 16
- **Non-missing %**: 100.0%
- **Signal statistics**:
  - dispersion_mean: mean=3040.1795, std=1490.9182
  - dispersion_95th: mean=4099.7205, std=1868.3175
  - spread_mean: mean=1.2436, std=0.0668
  - spread_95th: mean=1.6330, std=0.3720
  - shock_intensity: mean=23.8730, std=33.2217
  - vwap_intensity: mean=40.7027, std=37.4319
  - structure_instability: mean=71.9865, std=26.9223
- **Z-score standardization**: 518 values, mean=0.000

## Overall Assessment

- **Files audited**: 5/5
- **Total rows across all files**: 43,958
- **Average non-missing %**: 96.5%

## Recommendations

1. **ICP Design**: Ready for ICP model fitting with environment partitions
2. **VMM Moments**: Ready for VMM model fitting with comprehensive moment set
3. **Copula Marginals**: Ready for copula fitting with uniform marginals
4. **Clustering Features**: Ready for clustering analysis with standardized features
5. **Composite Inputs**: Ready for composite index construction

## Next Steps

All Wave-3 variables are ready for model execution:
- ICP models can be fitted on the design matrix
- VMM models can be fitted on the moment set
- Copulas can be fitted on the marginals
- Clustering can be performed on the features
- Composite index can be constructed from the inputs
