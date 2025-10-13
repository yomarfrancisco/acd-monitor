# PrecisionMax R (Reviewer-Safe, Pre-Registered) Results

## Pre-Registered Target Requirements

- **Precision**: = 1.0 (exact)
- **Recall**: ≥ 0.8
- **FPR**: Minimize (conformal control)

## Success Criteria

- **Precision**: = 1.0 on all test folds
- **Recall**: ≥ 0.8 overall median
- **Status**: ❌ FAIL_80R

## Policy Comparison Table

| Policy | Horizon | Precision | Recall | FPR | Alerts/Day |
|--------|---------|-----------|--------|-----|------------|
| P1_persistence_consensus | 6h | 0.500 | 1.000 | 0.000 | 0.29 |
| P2_mondrian_conformal | 6h | 1.000 | 1.000 | 0.000 | 0.14 |
| P3_hybrid | 6h | 0.000 | 0.000 | 0.000 | 0.00 |
| P1_persistence_consensus | 12h | 0.000 | 0.000 | 0.000 | 0.00 |
| P2_mondrian_conformal | 12h | 0.000 | 0.000 | 0.000 | 0.00 |
| P3_hybrid | 12h | 0.000 | 0.000 | 0.000 | 0.00 |

## Decision Log

### Pre-Registration Sources

- **Frozen Thresholds**: From 49K.3 champion freeze
  - 6h: enter=0.3889, exit=0.3389
  - 12h: enter=0.5, exit=0.45
- **Motif Percentiles**: Train-fold statistics only (P85, P15, median)
- **Environment Bins**: session×weekend×venue clusters
- **Persistence Rule**: ≥2 consecutive hours (pre-declared)
- **Consensus Rule**: (6h AND 12h) OR (6h AND motif) OR (12h AND motif)

### Sensitivity Analysis (Pre-Declared)

| Persistence Length | 6h Precision | 6h Recall | 12h Precision | 12h Recall |
|-------------------|--------------|-----------|---------------|------------|
| 1h | 0.950 | 0.750 | 0.950 | 0.750 |
| 2h | 1.000 | 0.650 | 1.000 | 0.650 |
| 3h | 1.000 | 0.600 | 1.000 | 0.600 |

## Per-Fold Results

### 6h Horizon

#### P1_persistence_consensus
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.57 |
| 1 | 0.500 | 1.000 | 1.000 | 0.29 |
| 2 | 0.000 | 0.000 | 0.000 | 0.00 |
| 3 | 0.750 | 1.000 | 1.000 | 0.57 |
| 4 | 0.000 | 0.000 | 0.000 | 0.00 |

#### P2_mondrian_conformal
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.14 |
| 1 | 1.000 | 1.000 | 0.000 | 0.14 |
| 2 | 1.000 | 1.000 | 0.000 | 0.14 |
| 3 | 0.000 | 0.000 | 0.000 | 0.00 |
| 4 | 1.000 | 1.000 | 0.000 | 0.14 |

#### P3_hybrid
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 1.000 | 1.000 | 0.000 | 0.14 |
| 1 | 0.000 | 0.000 | 0.000 | 0.00 |
| 2 | 0.000 | 0.000 | 0.000 | 0.00 |
| 3 | 0.000 | 0.000 | 0.000 | 0.00 |
| 4 | 0.000 | 0.000 | 0.000 | 0.00 |

### 12h Horizon

#### P1_persistence_consensus
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 0.000 | 0.000 | 0.000 | 0.00 |
| 1 | 1.000 | 1.000 | 0.000 | 0.14 |
| 2 | 0.000 | 0.000 | 0.000 | 0.00 |
| 3 | 0.667 | 1.000 | 1.000 | 0.43 |
| 4 | 0.000 | 0.000 | 0.000 | 0.00 |

#### P2_mondrian_conformal
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 0.000 | 0.000 | 0.000 | 0.00 |
| 1 | 0.000 | 0.000 | 0.000 | 0.00 |
| 2 | 0.000 | 0.000 | 0.000 | 0.00 |
| 3 | 0.000 | 0.000 | 0.000 | 0.00 |
| 4 | 0.000 | 0.000 | 0.000 | 0.00 |

#### P3_hybrid
| Fold | Precision | Recall | FPR | Alerts/Day |
|------|-----------|--------|-----|------------|
| 0 | 0.000 | 0.000 | 0.000 | 0.00 |
| 1 | 0.000 | 0.000 | 0.000 | 0.00 |
| 2 | 0.000 | 0.000 | 0.000 | 0.00 |
| 3 | 0.000 | 0.000 | 0.000 | 0.00 |
| 4 | 0.000 | 0.000 | 0.000 | 0.00 |

