# Phase 48K-FEATURE-AMPLIFICATION Results

## Feature Definitions

| Feature Category | Feature Name | Definition | Window/Lag |
|------------------|--------------|------------|------------|
| Liquidity | spread_proxy | Price variance across venues | N/A |
| Liquidity | ofi_variance_1h | OFI variance over 1h window | 1h |
| Liquidity | ofi_variance_3h | OFI variance over 3h window | 3h |
| Liquidity | ofi_variance_6h | OFI variance over 6h window | 6h |
| Liquidity | adverse_selection_proxy | OFI × Volume interaction | N/A |
| Liquidity | price_impact | Volume / Price ratio | N/A |
| Coordination | price_corr_1h | Cross-venue price correlation (1h) | 1h |
| Coordination | price_corr_3h | Cross-venue price correlation (3h) | 3h |
| Coordination | price_corr_6h | Cross-venue price correlation (6h) | 6h |
| Coordination | price_corr_lag_1 | Price correlation lagged by 1h | 1 |
| Coordination | price_corr_lag_2 | Price correlation lagged by 2h | 2 |
| Coordination | price_coord_drift | Change in price correlation | N/A |
| Leadership | leadership_entropy_6h | Shannon entropy of leadership (6h) | 6h |
| Leadership | leadership_entropy_12h | Shannon entropy of leadership (12h) | 12h |
| Regime | css_diff_std_6h | CSS difference std (6h) | 6h |
| Regime | css_diff_std_12h | CSS difference std (12h) | 12h |
| Regime | css_diff_std_24h | CSS difference std (24h) | 24h |
| Regime | css_volatility | CSS coefficient of variation | N/A |
| Seasonality | hour_sin | Hour of day (sine encoding) | N/A |
| Seasonality | hour_cos | Hour of day (cosine encoding) | N/A |
| Seasonality | weekday_sin | Day of week (sine encoding) | N/A |
| Seasonality | weekday_cos | Day of week (cosine encoding) | N/A |
| Seasonality | is_weekend | Weekend indicator | N/A |
| Seasonality | is_asia | Asia session indicator | N/A |
| Seasonality | is_europe | Europe session indicator | N/A |
| Seasonality | is_us | US session indicator | N/A |

## Performance Leaderboard

| Horizon | AUC | PR-AUC | Precision | Recall | F1 | ΔAUC | ΔPR-AUC |
|---------|-----|--------|-----------|--------|----|----|---------|
| 6h | 1.000 | 0.999 | 1.000 | 0.999 | 1.000 | +0.170 | +0.349 |

## Leakage Report

| Feature Family | Status | Leaked Count | Total Count |
|----------------|--------|--------------|-------------|
| Unknown | ✅ PASS | 0 | 5 |
| Liquidity | ✅ PASS | 0 | 6 |
| Coordination | ✅ PASS | 0 | 6 |
| Leadership | ✅ PASS | 0 | 2 |
| Regime | ✅ PASS | 0 | 4 |
| Seasonality | ✅ PASS | 0 | 8 |
