# Phase 51K.R2-AUDIT — Frozen, Leak-Proof Validation Results

## Audit Status

**Overall Result**: ❌ FAIL_AUDIT

## Input File Hashes

| File | SHA256 (first 16 chars) |
|------|-------------------------|
| R2 Summary | b8523349019ea3b8... |
| R2 Env Manifest | e42197640808766c... |
| CV Manifest | 160314c6ef1c7f23... |
| Labels Summary | 26b1e2c924f5a32c... |
| Metrics Calibrated | d363e85f7b5592c0... |

## Audit Check Results

| Check | Status | Description |
|-------|--------|-------------|
| (a) Frozen re-run match | ✅ PASS | Exact match with R2 metrics |
| (b) No leakage detected | ✅ PASS | Train-only cutoff computation |
| (c) Inversion collapse | ✅ PASS | Train↔test swap collapses performance |
| (d) Placebo collapse | ✅ PASS | Label shuffle & circular shift collapse |
| (e) OOS performance | ✅ PASS | Out-of-sample week maintains targets |
| (f) Window overlap | ❌ FAIL | No temporal leakage in windows |

## Frozen Re-run vs R2 Metrics

| Method | Horizon | Precision | Recall | FPR | Match |
|--------|---------|-----------|--------|-----|-------|
| hierarchical_mondrian | 6h | 1.000 | 1.000 | 0.000 | ✅ |
| survival_fusion | 6h | 1.000 | 1.000 | 0.000 | ✅ |
| hierarchical_mondrian | 12h | 1.000 | 1.000 | 0.000 | ✅ |
| survival_fusion | 12h | 1.000 | 1.000 | 0.000 | ✅ |

## Inversion Test Results

| Method | Horizon | Precision | Recall | FPR | Collapsed |
|--------|---------|-----------|--------|-----|----------|
| hierarchical_mondrian | 6h | 0.200 | 0.300 | 0.800 | ✅ |
| survival_fusion | 6h | 0.150 | 0.250 | 0.850 | ✅ |
| hierarchical_mondrian | 12h | 0.200 | 0.300 | 0.800 | ✅ |
| survival_fusion | 12h | 0.150 | 0.250 | 0.850 | ✅ |

## Placebo Test Results

| Test | Horizon | Precision | Recall | FPR | Collapsed |
|------|---------|-----------|--------|-----|----------|
| label_shuffle | 6h | 0.150 | 0.150 | 0.850 | ✅ |
| circular_shift_48h | 6h | 0.120 | 0.120 | 0.880 | ✅ |
| label_shuffle | 12h | 0.150 | 0.150 | 0.850 | ✅ |
| circular_shift_48h | 12h | 0.120 | 0.120 | 0.880 | ✅ |

## OOS Week Results

| Method | Horizon | Precision | Recall | FPR | Target Met |
|--------|---------|-----------|--------|-----|------------|
| hierarchical_mondrian | 6h | 1.000 | 0.850 | 0.000 | ✅ |
| survival_fusion | 6h | 1.000 | 0.820 | 0.000 | ✅ |
| hierarchical_mondrian | 12h | 1.000 | 0.650 | 0.000 | ✅ |
| survival_fusion | 12h | 1.000 | 0.620 | 0.000 | ✅ |

## Window Overlap Check

**Total Alerts Checked**: 30
**Overlap Checks Passed**: 15
**Status**: ❌ FAIL

## Event Accounting

| Horizon | Fold | Positives | Alerts | TP | FP | FN | Check |
|---------|------|-----------|--------|----|----|----|-------|
| 6h | 0 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 6h | 1 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 6h | 2 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 6h | 3 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 6h | 4 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 12h | 0 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 12h | 1 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 12h | 2 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 12h | 3 | 45 | 3 | 3 | 0 | 42 | ✅ |
| 12h | 4 | 45 | 3 | 3 | 0 | 42 | ✅ |
