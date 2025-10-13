# Phase 49K.1d — GEOMETRY EXPANSION (AUDIT-GRADE) Results

## Fold Structure

| Fold | Train Size | Val Size | Test Size | Total |
|------|------------|----------|-----------|-------|
| 1 | 145 | 145 | 145 | 435 |
| 2 | 290 | 145 | 124 | 559 |

## Model Performance Summary

| Model | Mean AUC | Std AUC | Gate A | Gate B |
|-------|----------|---------|--------|--------|
| Logistic L1 | 0.000 | 0.000 | ❌ | ❌ |
| Logistic L2 | 0.000 | 0.000 | ❌ | ❌ |
| GBM | 0.000 | 0.000 | ❌ | ❌ |

## Gate Results

- Gate A (AUC ≥ 0.70, std ≤ 0.05): ❌ FAIL
- Gate B (Recall ≥ 0.40, FPR ≤ 0.25 in ≥ 2/3 folds): ❌ FAIL
- Integrity Gate (leakage = 0, ≥ 3 folds): ❌ FAIL

## Final Status

- FEATURE_PRUNE_OK: false
