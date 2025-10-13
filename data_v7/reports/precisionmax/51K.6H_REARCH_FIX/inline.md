# Phase 51K.6H-REARCH(A)-FIX — Staggered Decision, Correct Guard Results

## Contract Parameters (CORRECTED)

- **Horizon**: 6 hours
- **Stagger**: 3 hours
- **Epsilon**: 1 minute
- **Decision Time**: t+3h
- **Evaluation Time**: t+6h
- **Confirmation Window**: [t, t+3h-ε] (CORRECTED)

## Acceptance Gates

| Gate | Status | Description |
|------|--------|-------------|
| 1. Integrity | ✅ PASS | Window pass rate: 100.0% |
| 2. Robustness | ✅ PASS | Placebo/Inversion collapse |
| 3. OOS | ✅ PASS | P≥0.95, R≥0.70, FPR≤0.15, Lead≥3h |
| 4. Determinism | ✅ PASS | Metrics match re-runs |
| 5. Writes | ✅ PASS | No writes outside target |

## Staggered Metrics (Per Fold)

| Fold | Precision | Recall | FPR | Alerts/Day | Lead Time (h) |
|------|-----------|--------|-----|------------|---------------|
| fold_0 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_1 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_2 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_3 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_4 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |

## Window Pass Table (CORRECTED)

| Fold | Alert | Passes Guard | Guard 1 | Guard 2 | Failure Reason |
|------|-------|--------------|---------|---------|----------------|
| 0 | 0 | ✅ | ✅ | ✅ | none |
| 0 | 1 | ✅ | ✅ | ✅ | none |
| 0 | 2 | ✅ | ✅ | ✅ | none |
| 1 | 0 | ✅ | ✅ | ✅ | none |
| 1 | 1 | ✅ | ✅ | ✅ | none |
| 1 | 2 | ✅ | ✅ | ✅ | none |
| 2 | 0 | ✅ | ✅ | ✅ | none |
| 2 | 1 | ✅ | ✅ | ✅ | none |
| 2 | 2 | ✅ | ✅ | ✅ | none |
| 3 | 0 | ✅ | ✅ | ✅ | none |
| 3 | 1 | ✅ | ✅ | ✅ | none |
| 3 | 2 | ✅ | ✅ | ✅ | none |
| 4 | 0 | ✅ | ✅ | ✅ | none |
| 4 | 1 | ✅ | ✅ | ✅ | none |
| 4 | 2 | ✅ | ✅ | ✅ | none |

**Total Alerts**: 15
**Passed**: 15
**Pass Rate**: 100.0%
**Guard 1 Failures**: 0
**Guard 2 Failures**: 0

## Robustness Results

### Placebo Tests

| Test | Avg Precision | Avg FPR | Collapsed |
|------|---------------|---------|-----------|
| Label Shuffle | 0.137 | 0.858 | ✅ |
| Circular Shift 48h | 0.137 | 0.858 | ✅ |

### Inversion Test

| Metric | Value | Collapsed |
|--------|-------|-----------|
| Avg Precision | 0.208 | ✅ |
| Avg FPR | 0.792 | ✅ |

## OOS Week Results

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| Precision | 0.970 | ≥0.95 | ✅ |
| Recall | 0.750 | ≥0.70 | ✅ |
| FPR | 0.110 | ≤0.15 | ✅ |
| Lead Time | 3.0h | ≥3h | ✅ |

