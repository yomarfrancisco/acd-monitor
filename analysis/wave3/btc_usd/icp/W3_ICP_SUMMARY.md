# Wave-3 ICP Analysis Summary

**Analysis Date**: 2025-09-30T20:00:25.412894
**Method**: Invariant Causal Prediction (ICP)
**Hypothesis**: Competitive markets show environment-dependent relationships; coordination shows invariant relationships

## Environment-Specific Results

| Session | Observations | R² | Status |
|---------|-------------|----|--------|
| Asia | 1,800 | 0.3344 | ✅ |
| Europe | 16,204 | 0.3072 | ✅ |
| US | 3,600 | 0.0248 | ✅ |

## Invariance Test Results

- **Total predictors tested**: 31
- **Invariant predictors**: 31 (100.0%)
- **Variant predictors**: 0 (0.0%)

### Top Variant Predictors (p < 0.05)


### Top Invariant Predictors (p > 0.05)

- **coinbase_return_5**: p = 0.3534, F = 1.5009
- **okx_spread**: p = 0.3328, F = 1.6237
- **kraken_spread_change**: p = 0.3050, F = 1.8107
- **binance_spread_change**: p = 0.2855, F = 1.9597
- **okx_spread_change**: p = 0.2853, F = 1.9611
- **kraken_spread**: p = 0.2843, F = 1.9693
- **bybit_spread**: p = 0.2827, F = 1.9827
- **binance_spread**: p = 0.2813, F = 1.9937
- **bybit_spread_change**: p = 0.2811, F = 1.9960
- **coinbase_spread_change**: p = 0.2809, F = 1.9970

## Interpretation

**Result**: High proportion of invariant predictors suggests **coordinated behavior**
- Many predictors show similar relationships across environments
- This is consistent with coordinated market making

## Limitations

- Single-day analysis limits generalizability
- Ridge regression may mask some relationships
- Session definitions may not capture all relevant environments
- No causal identification beyond correlation
