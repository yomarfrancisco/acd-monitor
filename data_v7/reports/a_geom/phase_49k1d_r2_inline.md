# Phase 49K.1d-R2 — GEOMETRY + THRESHOLD REMEDIATION Results

## Fold Configuration

| Fold | Train Size | Val Size | Test Size | Total |
|------|------------|----------|-----------|-------|
| 1 | 143 | 143 | 143 | 429 |
| 2 | 143 | 143 | 143 | 429 |

## Threshold Optimization Results

| Horizon | Fold | Threshold | Recall | FPR | Precision | F1 | AUC |
|---------|------|-----------|--------|-----|-----------|----|----|
| 6h | 1 | default | 0.000 | 0.000 | 0.000 | 0.000 | 0.761 |
| 6h | 1 | roc_optimal | 0.758 | 0.376 | 0.276 | 0.405 | 0.761 |
| 6h | 1 | ops_optimal | 0.582 | 0.212 | 0.342 | 0.431 | 0.761 |
| 6h | 2 | default | 0.000 | 0.000 | 0.000 | 0.000 | 0.694 |
| 6h | 2 | roc_optimal | 0.644 | 0.332 | 0.266 | 0.377 | 0.694 |
| 6h | 2 | ops_optimal | 0.433 | 0.124 | 0.394 | 0.413 | 0.694 |
| 12h | 1 | default | 0.000 | 0.000 | 0.000 | 0.000 | 0.735 |
| 12h | 1 | roc_optimal | 0.706 | 0.398 | 0.236 | 0.354 | 0.735 |
| 12h | 1 | ops_optimal | 0.706 | 0.398 | 0.236 | 0.354 | 0.735 |
| 12h | 2 | default | 0.000 | 0.000 | 0.000 | 0.000 | 0.723 |
| 12h | 2 | roc_optimal | 0.730 | 0.395 | 0.254 | 0.377 | 0.723 |
| 12h | 2 | ops_optimal | 0.360 | 0.130 | 0.337 | 0.348 | 0.723 |

## Success Criteria

- ≥3 folds created: 2 - ❌ FAIL
- Recall ≥ 0.30 and FPR ≤ 0.25: ❌ FAIL
- Leakage = 0: ✅ PASS
- Base-rate stability ± 3 pp: ✅ PASS

## Overall Success

- All criteria passed: ❌ FAIL
