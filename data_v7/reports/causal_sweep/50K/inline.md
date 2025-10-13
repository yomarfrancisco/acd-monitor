# Phase 50K-CAUSAL-SWEEP Results

## Fold Configuration

| Fold | Train Size | Val Size | Test Size | Total |
|------|------------|----------|-----------|-------|
| 1 | 143 | 143 | 143 | 429 |
| 2 | 143 | 143 | 143 | 429 |

## Causal Estimator Performance

| Estimator | Horizon | Mean AUC | Mean PR-AUC | Mean Brier | Stable Drivers |
|-----------|---------|----------|-------------|------------|----------------|
| Granger_LASSO | 6h | 0.791 | 0.463 | 0.114 | Yes |
| Granger_LASSO | 12h | 0.799 | 0.466 | 0.110 | Yes |
| PCMCI_surrogate | 6h | 0.725 | 0.339 | 0.128 | Yes |
| PCMCI_surrogate | 12h | 0.703 | 0.332 | 0.124 | Yes |
| ICP | 6h | 0.722 | 0.360 | 0.127 | Yes |
| ICP | 12h | 0.726 | 0.367 | 0.121 | Yes |
| Transfer_Entropy | 6h | 0.726 | 0.341 | 0.128 | Yes |
| Transfer_Entropy | 12h | 0.704 | 0.334 | 0.124 | Yes |
| Logistic_baseline | 6h | 0.748 | 0.416 | 0.217 | No |
| Logistic_baseline | 12h | 0.747 | 0.404 | 0.216 | No |

## Success Gates

- Integrity Gate: ❌ FAIL
- Placebo Gate: ✅ PASS
- Causal Gate: ✅ PASS
- Ops Gate: ✅ PASS

## Overall Success

- CAUSAL_SWEEP_OK: false
