# Phase 51K.6H-REARCH(A) — STAGGERED-DECISION CONTRACT (τ=3h) Results

## Contract Parameters

- **Horizon**: 6 hours
- **Stagger**: 3 hours
- **Epsilon**: 1 minute
- **Decision Time**: t+3h
- **Evaluation Time**: t+6h

## Acceptance Gates

| Gate | Status | Description |
|------|--------|-------------|
| 1. Integrity | ❌ FAIL | Window pass rate: 0.0% |
| 2. Robustness | ✅ PASS | Placebo/Inversion collapse |
| 3. OOS | ✅ PASS | P≥0.95, R≥0.70, FPR≤0.15 |
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

## Window Pass Table

| Fold | Alert | Passes Guard | Guard 1 | Guard 2 |
|------|-------|--------------|---------|---------|
| 0 | 0 | ❌ | ❌ | ✅ |
| 0 | 1 | ❌ | ❌ | ✅ |
| 1 | 0 | ❌ | ❌ | ✅ |
| 1 | 1 | ❌ | ❌ | ✅ |
| 2 | 0 | ❌ | ❌ | ✅ |
| 2 | 1 | ❌ | ❌ | ✅ |
| 3 | 0 | ❌ | ❌ | ✅ |
| 3 | 1 | ❌ | ❌ | ✅ |
| 4 | 0 | ❌ | ❌ | ✅ |
| 4 | 1 | ❌ | ❌ | ✅ |

**Total Alerts**: 10
**Passed**: 0
**Pass Rate**: 0.0%

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
| Precision | 0.960 | ≥0.95 | ✅ |
| Recall | 0.720 | ≥0.70 | ✅ |
| FPR | 0.120 | ≤0.15 | ✅ |
| Lead Time | 3.0h | ≥3h | ✅ |

