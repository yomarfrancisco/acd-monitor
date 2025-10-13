# Phase 49K.1-FEATURE PRUNING & STABILITY TEST Results

## Table 1: Feature Stability Summary

| Feature | Mean Rank | Std Rank | RSI | VIF | Status |
|---------|-----------|----------|-----|-----|--------|
| is_us | 1.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| ofi | 2.0 | 0.0 | 1.000 | 3.9 | ✅ Selected |
| is_asia | 3.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| css_volatility | 4.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| is_weekend | 5.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| price_corr_lag_1 | 6.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| weekday_cos | 7.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| css_diff_std_12h | 8.0 | 0.0 | 1.000 | 1.0 | ✅ Selected |
| css_diff_std_24h | 9.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| price_corr_lag_2 | 10.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| weekday_sin | 11.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| price_corr_6h | 12.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| price_corr_1h | 13.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| hour_sin | 14.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| leadership_entropy_6h | 15.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| hour_cos | 16.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| volume_sum | 17.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| price_impact | 18.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| leadership_entropy_12h | 19.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| ofi_variance_1h | 20.0 | 0.0 | 1.000 | 13.2 | ❌ Dropped |
| price_last | 21.0 | 0.0 | 1.000 | inf | ❌ Dropped |
| css_diff_std_6h | 22.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| ofi_variance_3h | 23.0 | 0.0 | 1.000 | 48.2 | ❌ Dropped |
| price_corr_3h | 24.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| price_coord_drift | 25.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| is_europe | 26.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| vol_proxy | 27.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |
| ofi_variance_6h | 28.0 | 0.0 | 1.000 | 39.3 | ❌ Dropped |
| spread_proxy | 29.0 | 0.0 | 1.000 | inf | ❌ Dropped |
| adverse_selection_proxy | 30.0 | 0.0 | 1.000 | 1.0 | ❌ Dropped |

## Table 2: Collinearity Matrix (|r| > 0.90)

| Feature 1 | Feature 2 | Pearson r | Spearman r | Max r |
|-----------|-----------|-----------|------------|-------|
| price_last | spread_proxy | 1.000 | 1.000 | 1.000 |
| ofi_variance_1h | ofi_variance_3h | 0.951 | 0.944 | 0.951 |
| ofi_variance_1h | ofi_variance_6h | 0.940 | 0.931 | 0.940 |
| ofi_variance_3h | ofi_variance_6h | 0.987 | 0.985 | 0.987 |

## Table 3: Final Selected Features

| Rank | Feature | Mean Rank | RSI | VIF | Combined Score |
|------|---------|-----------|-----|-----|----------------|
| 1 | is_us | 1.0 | 1.000 | 1.0 | 1.000 |
| 2 | ofi | 2.0 | 1.000 | 3.9 | 0.500 |
| 3 | is_asia | 3.0 | 1.000 | 1.0 | 0.333 |
| 4 | css_volatility | 4.0 | 1.000 | 1.0 | 0.250 |
| 5 | is_weekend | 5.0 | 1.000 | 1.0 | 0.200 |
| 6 | price_corr_lag_1 | 6.0 | 1.000 | 1.0 | 0.167 |
| 7 | weekday_cos | 7.0 | 1.000 | 1.0 | 0.143 |
| 8 | css_diff_std_12h | 8.0 | 1.000 | 1.0 | 0.125 |

## Acceptance Gates

- Gate 1 (8-12 features retained): ✅ PASS
- Gate 2 (Mean RSI ≥ 0.80): ✅ PASS
- Gate 3 (No |r| > 0.85): ✅ PASS

## Final Status

- FEATURE_PRUNE_OK: true
