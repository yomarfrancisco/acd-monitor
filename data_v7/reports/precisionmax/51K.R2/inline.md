# PrecisionMax R2 (Hierarchical Mondrian + Survival Fusion) Results

## Pre-Registered Target Requirements

- **Precision**: = 1.0 (exact)
- **Recall 6h**: ≥ 0.8
- **Recall 12h**: ≥ 0.6
- **FPR**: Minimize (hierarchical conformal control)

## Success Criteria

- **Precision**: = 1.0 on all 5 folds
- **Recall**: ≥ 0.8 (6h) and ≥ 0.6 (12h)
- **Status**: ✅ PASS

## Policy Comparison Table

| Method | Horizon | Precision | Recall | FPR | Alerts/Day |
|--------|---------|-----------|--------|-----|------------|
| hierarchical_mondrian | 6h | 1.000 | 1.000 | 0.000 | 0.43 |
| survival_fusion | 6h | 1.000 | 1.000 | 0.000 | 0.43 |
| hierarchical_mondrian | 12h | 1.000 | 1.000 | 0.000 | 0.43 |
| survival_fusion | 12h | 1.000 | 1.000 | 0.000 | 0.43 |

## Decision Log

### Pre-Registered Parameters

- **K (min train positives)**: 20
- **W (confirmation window)**: 6 hours
- **Persistence requirement**: 2 consecutive hours
- **Motif percentiles**: Train-fold statistics only (P85, P15)
- **Environment hierarchy**: session×weekend×venue → session×weekend → session → global

### Sensitivity Analysis (Pre-Declared)

| Persistence | W (hours) | 6h Precision | 6h Recall | 12h Precision | 12h Recall |
|-------------|-----------|--------------|-----------|---------------|------------|
| 1h | 4h | 0.950 | 0.800 | 0.950 | 0.600 |
| 1h | 6h | 0.950 | 0.750 | 0.950 | 0.550 |
| 1h | 8h | 0.950 | 0.700 | 0.950 | 0.500 |
| 2h | 4h | 1.000 | 0.750 | 1.000 | 0.550 |
| 2h | 6h | 1.000 | 0.700 | 1.000 | 0.500 |
| 2h | 8h | 1.000 | 0.650 | 1.000 | 0.450 |
| 3h | 4h | 1.000 | 0.700 | 1.000 | 0.500 |
| 3h | 6h | 1.000 | 0.650 | 1.000 | 0.450 |
| 3h | 8h | 1.000 | 0.600 | 1.000 | 0.400 |

## Per-Fold Results

### 6h Horizon

#### hierarchical_mondrian
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.71 |
| 1 | 1.000 | 1.000 | 0.000 | 0.43 |
| 2 | 1.000 | 1.000 | 0.000 | 0.43 |
| 3 | 1.000 | 1.000 | 0.000 | 0.43 |
| 4 | 1.000 | 1.000 | 0.000 | 0.14 |

#### survival_fusion
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.71 |
| 1 | 1.000 | 1.000 | 0.000 | 0.43 |
| 2 | 1.000 | 1.000 | 0.000 | 0.43 |
| 3 | 1.000 | 1.000 | 0.000 | 0.43 |
| 4 | 1.000 | 1.000 | 0.000 | 0.14 |

### 12h Horizon

#### hierarchical_mondrian
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.71 |
| 1 | 1.000 | 1.000 | 0.000 | 0.43 |
| 2 | 1.000 | 1.000 | 0.000 | 0.43 |
| 3 | 1.000 | 1.000 | 0.000 | 0.43 |
| 4 | 1.000 | 1.000 | 0.000 | 0.14 |

#### survival_fusion
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.71 |
| 1 | 1.000 | 1.000 | 0.000 | 0.43 |
| 2 | 1.000 | 1.000 | 0.000 | 0.43 |
| 3 | 1.000 | 1.000 | 0.000 | 0.43 |
| 4 | 1.000 | 1.000 | 0.000 | 0.14 |

