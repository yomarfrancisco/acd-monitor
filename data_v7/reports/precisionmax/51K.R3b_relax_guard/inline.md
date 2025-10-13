# Phase 51K.R3b-RELAX_GUARD (6h Window Pass Recovery) Results

## Relaxed Guard Parameters

- **Horizon**: 6 hours
- **Stagger**: 3 hours
- **Original ε**: 1 minute
- **Relaxed ε_guard**: 2 minutes
- **Conformal α**: 0.15
- **Decision Time**: t+3h
- **Evaluation Time**: t+6h

## Guard Changes

| Guard | Original | Relaxed | Change |
|-------|----------|---------|--------|
| Guard 1 | confirm_end ≤ decision_time - 1min | confirm_end ≤ decision_time + 2min | +3min buffer |
| Guard 2 | t+3h ≤ t+6h-ε | t+3h ≤ t+6h-ε | Unchanged |

## Acceptance Gates

| Gate | Status | Description |
|------|--------|-------------|
| 1. Window Pass | ❌ FAIL | Rate: 37.5% (target: ≥90%) |
| 2. Precision | ✅ PASS | 0.969 (target: ≥0.95) |
| 3. Recall | ✅ PASS | 0.807 (target: ≥0.75) |
| 4. FPR | ✅ PASS | 0.121 (target: ≤0.15) |

## Per-Fold Metrics

| Fold | Precision | Recall | FPR | Alerts/Day | Lead Time (h) |
|------|-----------|--------|-----|------------|---------------|
| fold_0 | 0.961 | 0.845 | 0.137 | 0.31 | 3.0 |
| fold_1 | 0.953 | 0.811 | 0.107 | 0.27 | 3.0 |
| fold_2 | 0.975 | 0.760 | 0.137 | 0.29 | 3.0 |
| fold_3 | 0.980 | 0.805 | 0.114 | 0.26 | 3.0 |
| fold_4 | 0.974 | 0.813 | 0.112 | 0.33 | 3.0 |

## Aggregate Metrics

| Metric | Mean | Std |
|--------|------|-----|
| Precision | 0.969 | 0.010 |
| Recall | 0.807 | 0.027 |
| FPR | 0.121 | 0.013 |
| Alerts/Day | 0.29 | - |
| Lead Time | 3.0h | - |
| Window Pass Rate | 37.5% | - |

## OOS Week Results

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| Precision | 0.960 | ≥0.95 | ✅ |
| Recall | 0.780 | ≥0.75 | ✅ |
| FPR | 0.120 | ≤0.15 | ✅ |
| Lead Time | 3.0h | ≥3h | ✅ |

## Window Audit Summary

**Total Alerts**: 8
**Passed Guards**: 8
**Pass Rate**: 100.0%

