# Phase 49K.1d-R: GEOMETRY EXPANSION (AUDIT-GRADE, FIXED TARGET + FOLDS) Results

## Fold Configuration

| Fold | Train Size | Val Size | Test Size | Total |
|------|------------|----------|-----------|-------|
| 1 | 150 | 150 | 150 | 450 |

## Base Rate Diagnostics

| Horizon | Mean Base Rate | Std Base Rate | Min | Max | Status |
|---------|----------------|---------------|-----|-----|--------|
| 6h | 0.175 | 0.000 | 0.175 | 0.175 | ✅ PASS |
| 12h | 0.152 | 0.000 | 0.152 | 0.152 | ✅ PASS |

## Model Evaluation

| Horizon | Mean AUC | Mean Recall | Valid Folds | Status |
|---------|----------|-------------|-------------|--------|
| 6h | 0.751 | 0.000 | 1/1 | ❌ FAIL |
| 12h | 0.734 | 0.000 | 1/1 | ❌ FAIL |

## Gate Summary

- Integrity Gate: ❌ FAIL
- Base Rate Gate: ✅ PASS
- Model Gate: ❌ FAIL

## Final Status

- FEATURE_PRUNE_OK: false
