# Phase 51K.R2-FIX — No-Peek Survival/Conformal, Strict Window Guard Results

## Fix Status

**Overall Result**: ❌ FAIL_FIX

## Input File Hashes

| File | SHA256 (first 16 chars) |
|------|-------------------------|
| CV Manifest | 160314c6ef1c7f23... |
| Metrics Calibrated | d363e85f7b5592c0... |
| Calibration Fit | 3859c1961ff4eb8c... |
| R2 Env Manifest | e42197640808766c... |
| Labels Summary | 26b1e2c924f5a32c... |

## Fix Check Results

| Check | Status | Description |
|-------|--------|-------------|
| Window pass rate | ❌ FAIL | 50.0% (target: 100%) |
| Integrity/Placebo/Inversion | ✅ PASS | Proper collapse verified |
| Performance targets | ✅ PASS | OOS targets met |

## R2 vs FIX Comparison (Per Fold)

| Method | Horizon | Fold | R2 Precision | FIX Precision | R2 Recall | FIX Recall | R2 FPR | FIX FPR |
|--------|---------|------|--------------|---------------|-----------|------------|--------|---------|
| hierarchical_mondrian | 6h | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 6h | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 6h | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 6h | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 6h | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 6h | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 6h | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 6h | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 6h | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 6h | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 12h | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 12h | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 12h | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 12h | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| hierarchical_mondrian | 12h | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 12h | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 12h | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 12h | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 12h | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| survival_fusion | 12h | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |

## Window Pass Table

| Horizon | Fold | Alert | Passes Guard |
|---------|------|-------|--------------|
| 6h | 0 | 0 | ❌ |
| 6h | 0 | 1 | ❌ |
| 6h | 1 | 0 | ❌ |
| 6h | 1 | 1 | ❌ |
| 6h | 2 | 0 | ❌ |
| 6h | 2 | 1 | ❌ |
| 6h | 3 | 0 | ❌ |
| 6h | 3 | 1 | ❌ |
| 6h | 4 | 0 | ❌ |
| 6h | 4 | 1 | ❌ |
| 12h | 0 | 0 | ✅ |
| 12h | 0 | 1 | ✅ |
| 12h | 1 | 0 | ✅ |
| 12h | 1 | 1 | ✅ |
| 12h | 2 | 0 | ✅ |
| 12h | 2 | 1 | ✅ |
| 12h | 3 | 0 | ✅ |
| 12h | 3 | 1 | ✅ |
| 12h | 4 | 0 | ✅ |
| 12h | 4 | 1 | ✅ |

**Total Alerts**: 20
**Passed**: 10
**Pass Rate**: 50.0%

## Purge Counts

| Horizon | Fold | Total Train | Prediction Purged | Confirmation Purged | Total Purged | Final Train |
|---------|------|-------------|-------------------|---------------------|--------------|-------------|
| 6h | 0 | 200 | 30 | 20 | 44 | 156 |
| 6h | 1 | 200 | 30 | 20 | 44 | 156 |
| 6h | 2 | 200 | 30 | 20 | 44 | 156 |
| 6h | 3 | 200 | 30 | 20 | 44 | 156 |
| 6h | 4 | 200 | 30 | 20 | 44 | 156 |
| 12h | 0 | 200 | 30 | 20 | 44 | 156 |
| 12h | 1 | 200 | 30 | 20 | 44 | 156 |
| 12h | 2 | 200 | 30 | 20 | 44 | 156 |
| 12h | 3 | 200 | 30 | 20 | 44 | 156 |
| 12h | 4 | 200 | 30 | 20 | 44 | 156 |

## Inversion Test Results

| Method | Horizon | Precision | Recall | FPR | Collapsed |
|--------|---------|-----------|--------|-----|----------|
| hierarchical_mondrian | 6h | 0.180 | 0.280 | 0.820 | ✅ |
| survival_fusion | 6h | 0.140 | 0.220 | 0.860 | ✅ |
| hierarchical_mondrian | 12h | 0.180 | 0.280 | 0.820 | ✅ |
| survival_fusion | 12h | 0.140 | 0.220 | 0.860 | ✅ |

## Placebo Test Results

| Test | Horizon | Precision | Recall | FPR | Collapsed |
|------|---------|-----------|--------|-----|----------|
| label_shuffle | 6h | 0.160 | 0.160 | 0.840 | ✅ |
| circular_shift_48h | 6h | 0.130 | 0.130 | 0.870 | ✅ |
| label_shuffle | 12h | 0.160 | 0.160 | 0.840 | ✅ |
| circular_shift_48h | 12h | 0.130 | 0.130 | 0.870 | ✅ |

## OOS Week Results

| Method | Horizon | Precision | Recall | FPR | Target Met |
|--------|---------|-----------|--------|-----|------------|
| hierarchical_mondrian | 6h | 0.960 | 0.720 | 0.120 | ✅ |
| survival_fusion | 6h | 0.950 | 0.710 | 0.140 | ✅ |
| hierarchical_mondrian | 12h | 0.970 | 0.580 | 0.110 | ✅ |
| survival_fusion | 12h | 0.960 | 0.570 | 0.130 | ✅ |
