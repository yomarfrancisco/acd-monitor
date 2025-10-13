# Candidate Model Card

## Data

- **Source**: CSS timeline (2,332 rows)
- **Features**: 6 stable features
- **Horizons**: 6h and 12h
- **Labels**: P15 percentile thresholds (train-only)

## Features

1. price_coord_drift
2. price_corr_lag_1
3. css_diff_std_6h
4. css_diff_std_24h
5. is_asia
6. is_weekend

## Cross-Validation

- **Method**: LOO-Week CV
- **Folds**: 5
- **Embargo**: 6 hours
- **Purge**: Label-window purging

## Models

- **Logistic_L2**: Logistic L2 (balanced)
- **Logistic_ElasticNet**: Logistic Elastic-Net
- **GradientBoosting**: Gradient Boosting (shallow)

## Gates

- **Integrity Gate**: ✅ PASS
- **Placebo Gate**: ✅ PASS
- **Ops Gate**: ✅ PASS
- **Calibration Gate**: ❌ FAIL
- **Stability Gate**: ✅ PASS

## Ops Policy

- **Threshold**: Ops-optimal (minimize FPR s.t. Recall ≥ 0.50/0.40)
- **Hysteresis**: Enter=Thigh, Exit=Tlow=Thigh-0.05, Cool-down=2h
- **Calibration**: Post-calibration ECE ≤ 0.10

## Caveats

- **Data Coverage**: Limited to 3-month window
- **Feature Stability**: Monitor sign consistency
- **Threshold Sensitivity**: Validate on new data

## Overall Status

- **RETRAIN_OK**: false
