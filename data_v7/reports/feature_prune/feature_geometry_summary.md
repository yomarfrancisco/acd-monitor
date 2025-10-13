# Phase 49K.1c — DATA GEOMETRY EXPANSION Results

## Table 1: Fold Structure

| Fold | Train Size | Val Size | Test Size | Total |
|------|------------|----------|-----------|-------|
| 1 | 450 | 450 | 450 | 1350 |
| 2 | 900 | 450 | 448 | 1798 |

## Table 2: Feature Stability (Candidate Features)

| Feature | Mean Rank | Std Rank | RSI | Mean VIF | Max VIF | Status |
|---------|-----------|----------|-----|----------|---------|--------|
| price_coord_drift | 24.0 | 5.0 | 0.833 | 1.0 | 1.1 | ✅ Kept |
| price_corr_lag_2 | 15.0 | 13.0 | 0.567 | 1.0 | 1.1 | ❌ Dropped |
| is_asia | 8.5 | 4.5 | 0.850 | 1.0 | 1.1 | ✅ Kept |
| css_diff_std_6h | 8.0 | 3.0 | 0.900 | 1.1 | 1.1 | ✅ Kept |
| is_weekend | 3.0 | 2.0 | 0.933 | 1.1 | 1.1 | ✅ Kept |
| css_diff_std_24h | 15.5 | 1.5 | 0.950 | 1.0 | 1.1 | ✅ Kept |
| price_corr_lag_1 | 24.5 | 2.5 | 0.917 | 1.0 | 1.1 | ✅ Kept |
| price_corr_3h | 18.5 | 7.5 | 0.750 | 1.0 | 1.0 | ❌ Dropped |

## Acceptance Gates

- Gate 1 (≥3 folds completed): ❌ FAIL
- Gate 2 (Mean RSI ≥0.80): ✅ PASS
- Gate 3 (No |r|>0.85): ✅ PASS

## Final Status

- FEATURE_PRUNE_OK: false
