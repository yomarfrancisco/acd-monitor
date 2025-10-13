# Model Card Addendum - Robust Ops Refreeze

## Changes Made

### Stricter Operational Gates
- **Previous**: Precision ≥ 0.50, Recall ≥ 0.50, FPR ≤ 0.25
- **New**: Precision ≥ 0.55, Recall ≥ 0.50, FPR ≤ 0.20
- **Rationale**: Higher precision requirements for production deployment

### Threshold Refinement

#### 6h Horizon (GradientBoosting)
- **Enter Threshold**: 0.4
- **Exit Threshold**: 0.34
- **Conformal Cutoff**: 0.4
- **Cooldown**: 3h
- **Status**: PILOT/SHADOW

#### 12h Horizon (Logistic_ElasticNet)
- **Enter Threshold**: 0.5
- **Exit Threshold**: 0.45
- **Conformal Cutoff**: 0.45
- **Cooldown**: 2h
- **Status**: PRODUCTION

### Calibration Sanity Check

#### 6h Horizon
- **Mean ECE**: 0.0
- **Min HL p-value**: 1.0
- **Calibration**: ✅ PASS

#### 12h Horizon
- **Mean ECE**: 0.0
- **Min HL p-value**: 1.0
- **Calibration**: ✅ PASS

### Stress & Stability Results

#### 6h Horizon
- **Placebo Test**: ✅ PASS
- **Subgroup Analysis**: ✅ PASS
- **Feature Ablation**: ✅ PASS

#### 12h Horizon
- **Placebo Test**: ✅ PASS
- **Subgroup Analysis**: ✅ PASS
- **Feature Ablation**: ✅ PASS

### Flags and Warnings

- ⚠️ 6h horizon marked as PILOT/SHADOW due to failed gates
