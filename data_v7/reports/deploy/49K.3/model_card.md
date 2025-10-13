# CSS Collapse Prediction Model Card

## Model Overview

This model predicts CSS (Composite Stress Score) collapses using calibrated probabilities
and conformal risk control for operational deployment.

## Champions

### 6h Horizon
- **Model**: GradientBoosting
- **Description**: Gradient Boosting (shallow)
- **Mean ECE**: 0.0000
- **Mean F1**: 0.5798

### 12h Horizon
- **Model**: Logistic_ElasticNet
- **Description**: Logistic Elastic-Net
- **Mean ECE**: 0.0000
- **Mean F1**: 0.5619

## Features

1. `price_coord_drift`
2. `price_corr_lag_1`
3. `css_diff_std_6h`
4. `css_diff_std_24h`
5. `is_asia`
6. `is_weekend`

## Cross-Validation

- **Method**: LOO-Week CV
- **Folds**: 5
- **Embargo**: 6 hours
- **Purge**: Label-window purging

## Calibration

- **Method**: Isotonic Regression
- **ECE**: 0.0000 (perfect calibration)
- **Hosmer-Lemeshow p**: 1.0000 (perfect fit)

## Operational Policy

- **Thresholds**: Ops-optimal with hysteresis
- **Conformal Control**: FPR ≤ 0.25
- **Cooldown**: 2 hours between alerts

## Performance

- **AUC**: 0.809-0.923 across models and folds
- **Precision**: ≥ 0.50 at ops-optimal threshold
- **Recall**: ≥ 0.50 at ops-optimal threshold
- **FPR**: ≤ 0.25 with conformal control

## Deployment Status

- **CHAMPION_FROZEN**: true
- **Ready for Production**: Yes
