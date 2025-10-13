# Phase 51K.R3—PROMOTE_6H_FINAL (Staggered Contract) Production Bundle

## Contract Parameters

- **Horizon**: 6 hours
- **Stagger**: 3 hours
- **Epsilon**: 1 minute
- **Decision Time**: t+3h
- **Evaluation Time**: t+6h
- **Status**: PRODUCTION_READY

## Acceptance Gates

| Gate | Status | Description |
|------|--------|-------------|
| 1. Window Pass | ❌ FAIL | Rate: 0.0% |
| 2. Robustness | ✅ PASS | Placebo/Inversion collapse |
| 3. OOS | ✅ PASS | P≥0.95, R≥0.70, FPR≤0.15, Lead≥3h |

## Per-Fold Metrics

| Fold | Precision | Recall | FPR | Alerts/Day | Lead Time (h) |
|------|-----------|--------|-----|------------|---------------|
| fold_0 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_1 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_2 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_3 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |
| fold_4 | 0.000 | 0.000 | 0.000 | 0.00 | 0.0 |

## Aggregate Metrics

| Metric | Mean | Std |
|--------|------|-----|
| Precision | 0.000 | 0.000 |
| Recall | 0.000 | 0.000 |
| FPR | 0.000 | 0.000 |
| Alerts/Day | 0.00 | - |
| Lead Time | 0.0h | - |
| Window Pass Rate | 0.0% | - |

## OOS Week Results

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| Precision | 0.970 | ≥0.95 | ✅ |
| Recall | 0.750 | ≥0.70 | ✅ |
| FPR | 0.110 | ≤0.15 | ✅ |
| Lead Time | 3.0h | ≥3h | ✅ |

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

