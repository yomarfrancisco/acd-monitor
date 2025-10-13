# Phase 49K-MODEL_ZOO Results

## Model Zoo Leaderboard

### 6h Horizon Results:
| Model | AUC | PR-AUC | Precision | Recall | F1 | FPR | Alerts/Day | Lead Time |
|-------|-----|--------|-----------|--------|----|----|-----------|-----------|
| Logistic Regression | 0.511±0.021 | 0.169±0.029 | 0.000±0.000 | 0.000±0.000 | 0.000±0.000 | 0.009±0.003 | 0.0±0.0 | 6.0±0.0 |
| Gradient Boosting | 0.469±0.000 | 0.203±0.000 | 0.000±0.000 | 0.000±0.000 | 0.000±0.000 | 0.006±0.000 | 0.0±0.0 | 6.0±0.0 |
| Extra Trees | 0.446±0.000 | 0.125±0.000 | 0.000±0.000 | 0.000±0.000 | 0.000±0.000 | 0.006±0.000 | 0.0±0.0 | 6.0±0.0 |

### 12h Horizon Results:
| Model | AUC | PR-AUC | Precision | Recall | F1 | FPR | Alerts/Day | Lead Time |
|-------|-----|--------|-----------|--------|----|----|-----------|-----------|
| Random Forest | 0.506±0.000 | 0.206±0.000 | 1.000±0.000 | 0.029±0.000 | 0.056±0.000 | 0.000±0.000 | 0.0±0.0 | 12.0±0.0 |
| Extra Trees | 0.473±0.000 | 0.158±0.000 | 0.143±0.000 | 0.030±0.000 | 0.050±0.000 | 0.036±0.000 | 0.2±0.0 | 12.0±0.0 |

## Acceptance Gates

- Gate 1 (AUC ≥ 0.90 on ≥3 models): ❌ FAIL
- Gate 2 (Excellent model with all constraints): ❌ FAIL
- Gate 3 (Fold variance ≤ 0.05): ❌ FAIL

## Final Status

- MODEL_ZOO_OK: false
- EXCELLENT_CORE_CANDIDATE: false
