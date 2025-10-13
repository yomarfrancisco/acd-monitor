# Phase 49K.1b — STABILITY RECHECK (Multi-Fold) Results

## Table 1: Stability Summary (Multi-Fold)

| Feature | Mean Rank | Std Rank | RSI | VIF | Status |
|---------|-----------|----------|-----|-----|--------|
| price_coord_drift | 5.5 | 0.5 | 0.983 | 1.1 | ✅ Selected |
| price_corr_lag_2 | 5.5 | 3.5 | 0.883 | 1.1 | ✅ Selected |
| is_asia | 7.5 | 0.5 | 0.983 | 1.1 | ✅ Selected |
| css_diff_std_6h | 7.5 | 1.5 | 0.950 | 1.1 | ✅ Selected |
| ofi_variance_1h | 12.0 | 0.0 | 1.000 | 11.1 | ❌ Dropped |
| price_last | 12.0 | 1.0 | 0.967 | inf | ❌ Dropped |
| is_weekend | 12.0 | 2.0 | 0.933 | 1.1 | ✅ Selected |
| css_diff_std_24h | 9.5 | 8.5 | 0.717 | 1.1 | ✅ Selected |
| ofi_variance_6h | 12.5 | 2.5 | 0.917 | 38.9 | ❌ Dropped |
| price_corr_lag_1 | 14.5 | 0.5 | 0.983 | 1.1 | ✅ Selected |
| price_corr_3h | 14.0 | 3.0 | 0.900 | 1.1 | ✅ Selected |
| is_europe | 12.0 | 7.0 | 0.767 | 1.1 | ❌ Dropped |
| weekday_sin | 18.0 | 1.0 | 0.967 | 1.1 | ❌ Dropped |
| ofi | 18.0 | 2.0 | 0.933 | 3.3 | ❌ Dropped |
| price_corr_1h | 13.0 | 10.0 | 0.667 | 1.1 | ❌ Dropped |
| price_corr_6h | 15.0 | 7.0 | 0.767 | 1.1 | ❌ Dropped |
| vol_proxy | 18.5 | 2.5 | 0.917 | 1.1 | ❌ Dropped |
| ofi_variance_3h | 13.0 | 11.0 | 0.633 | 46.8 | ❌ Dropped |
| volume_sum | 17.5 | 4.5 | 0.850 | 1.1 | ❌ Dropped |
| price_impact | 13.0 | 12.0 | 0.600 | 1.1 | ❌ Dropped |
| leadership_entropy_12h | 22.0 | 1.0 | 0.967 | 1.1 | ❌ Dropped |
| css_volatility | 15.0 | 11.0 | 0.633 | 1.1 | ❌ Dropped |
| hour_cos | 15.0 | 12.0 | 0.600 | 1.1 | ❌ Dropped |
| spread_proxy | 23.0 | 3.0 | 0.900 | inf | ❌ Dropped |
| leadership_entropy_6h | 17.5 | 10.5 | 0.650 | 1.1 | ❌ Dropped |
| adverse_selection_proxy | 26.5 | 1.5 | 0.950 | 1.1 | ❌ Dropped |
| hour_sin | 23.5 | 5.5 | 0.817 | 1.1 | ❌ Dropped |
| weekday_cos | 26.5 | 2.5 | 0.917 | 1.1 | ❌ Dropped |
| css_diff_std_12h | 28.5 | 1.5 | 0.950 | 1.1 | ❌ Dropped |
| is_us | 17.0 | 13.0 | 0.567 | 1.1 | ❌ Dropped |

## Table 2: High Correlation Pairs (|r| > 0.90)

| Feature 1 | Feature 2 | Pearson r | Spearman r | Max r |
|-----------|-----------|-----------|------------|-------|
| price_last | spread_proxy | 1.000 | 1.000 | 1.000 |
| ofi_variance_1h | ofi_variance_3h | 0.940 | 0.924 | 0.940 |
| ofi_variance_1h | ofi_variance_6h | 0.927 | 0.910 | 0.927 |
| ofi_variance_3h | ofi_variance_6h | 0.986 | 0.983 | 0.986 |

## Table 3: Final Retained Features

| Rank | Feature | Mean Rank | RSI | VIF | Combined Score |
|------|---------|-----------|-----|-----|----------------|
| 1 | price_coord_drift | 5.5 | 0.983 | 1.1 | 0.179 |
| 2 | price_corr_lag_2 | 5.5 | 0.883 | 1.1 | 0.161 |
| 3 | is_asia | 7.5 | 0.983 | 1.1 | 0.131 |
| 4 | css_diff_std_6h | 7.5 | 0.950 | 1.1 | 0.127 |
| 5 | is_weekend | 12.0 | 0.933 | 1.1 | 0.078 |
| 6 | css_diff_std_24h | 9.5 | 0.717 | 1.1 | 0.075 |
| 7 | price_corr_lag_1 | 14.5 | 0.983 | 1.1 | 0.068 |
| 8 | price_corr_3h | 14.0 | 0.900 | 1.1 | 0.064 |

## Acceptance Gates

- Gate 1 (≥3 folds completed): ❌ FAIL
- Gate 2 (Mean RSI ≥0.80): ✅ PASS
- Gate 3 (No |r|>0.85): ✅ PASS

## Final Status

- FEATURE_PRUNE_OK: false
