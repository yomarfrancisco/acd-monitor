# Phase 50K.1-REPAIR — HOURLY INDEX & LOO-WEEK FOLDS Results

## Geometry Trace

| Step | Count | Drops % |
|------|-------|---------|
| After resample | 2332 | 0.0% |
| After features | 2332 | 0.0% |
| After labels 6h | 2308 | 1.0% |
| After labels 12h | 2284 | 2.1% |

## Fold Configuration

| Fold | Test Week | Train Size | Test Size | Purged 6h | Purged 12h |
|------|-----------|------------|-----------|-----------|------------|
| 1 | 2025-07-07 | 499 | 42 | 499 | 499 |
| 2 | 2025-07-21 | 457 | 42 | 457 | 457 |
| 3 | 2025-08-04 | 457 | 42 | 457 | 457 |
| 4 | 2025-08-18 | 457 | 42 | 457 | 457 |
| 5 | 2025-09-01 | 457 | 42 | 457 | 457 |

## Estimator Performance

| Estimator | Horizon | Mean AUC | Mean PR-AUC | Mean Brier | Mean ECE |
|-----------|---------|----------|-------------|------------|----------|
| Logistic_baseline | 6h | 0.802 | 0.486 | 0.195 | 0.246 |
| Logistic_baseline | 12h | 0.828 | 0.514 | 0.198 | 0.293 |
| Granger_LASSO | 6h | 0.857 | 0.575 | 0.097 | 0.000 |
| Granger_LASSO | 12h | 0.853 | 0.568 | 0.098 | 0.000 |

## Gates

- Integrity Gate: ✅ PASS
- Placebo Gate: ✅ PASS
- Ops Gate: ✅ PASS
- Stability Gate: ✅ PASS

## Overall Success

- REPAIR_OK: true
