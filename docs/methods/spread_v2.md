# Spread Compression Detection v2

## Overview

Spread v2 introduces a z-score based dispersion detector with matched controls to address threshold artifacts and provide more robust episode detection. This method avoids the fixed percentile thresholds that can create artificial episode patterns.

## Z-Score Dispersion Detector

### Method

The z-score detector computes rolling z-scores of dispersion against a baseline:

```
dispersion_z(t) = (D_t - median_roll(D, k)) / MAD_roll(D, k)
```

Where:
- `D_t` is dispersion at time t
- `median_roll(D, k)` is rolling median over k-second window
- `MAD_roll(D, k)` is rolling median absolute deviation over k-second window

### Parameters

- `--roll 60s`: Rolling window size for baseline (default: 60 seconds)
- `--z-thresh -1.5`: Z-score threshold for episode detection (default: -1.5)
- `--merge-gap 2s`: Maximum gap to merge nearby episodes (default: 2 seconds)
- `--min-dur 10s`: Minimum episode duration (default: 10 seconds)

### Episode Detection

1. Compute rolling z-scores vs baseline
2. Find regions where z-score < threshold
3. Merge episodes within merge-gap tolerance
4. Filter by minimum duration

## Matched Controls

### Features

Controls are matched on economic features:
- `vol30s`: Realized volatility over last 30 seconds
- `volrate`: Instantaneous volume rate
- `t_in_window`: Time position in window (0 to 1)

### Parameters

- `--mc-features vol30s,volrate,t_in_window`: Features for matching
- `--mc-k 5`: kNN parameter for nearest neighbors
- `--mc-per-episode 100`: Number of controls per episode
- `--mc-gap 10s`: Exclusion gap around episodes (default: 10 seconds)
- `--mc-standardize`: Standardize features for kNN

### Sampling Process

1. Extract features for all time points
2. Exclude episode region ± buffer
3. Standardize features
4. Find k-nearest neighbors to episode features
5. Return control indices

## Block Bootstrap

### Method

Block bootstrap preserves time series structure:

1. Divide data into blocks of size `--bb-size` (default: 10 seconds)
2. Sample blocks with replacement
3. Compute test statistic on bootstrap sample
4. Repeat `--bb-n` times (default: 1000)

### Parameters

- `--bb-size 10s`: Block size for bootstrap
- `--bb-n 1000`: Number of bootstrap samples

## Determinism

All random operations use `--seed` parameter for reproducibility:
- kNN tie-breaking
- Bootstrap sampling
- Control selection

## Outputs

### Per-Episode JSON

```json
{
  "episode": {
    "start_time": "2025-01-01T01:00:00Z",
    "end_time": "2025-01-01T01:00:10Z",
    "duration": 10,
    "min_zscore": -2.5,
    "detector": "zscore"
  },
  "comparison": {
    "delta_z": -1.8,
    "cohens_d": -1.5,
    "p_value": 0.001,
    "delta_auc": 0.85
  },
  "matched_controls": [100, 150, 200, ...],
  "provenance": "REAL",
  "regulatory_grade": true
}
```

### Provenance Tagging

- `provenance`: "REAL" for real data, "DEMO" for synthetic
- `regulatory_grade`: true for real data, false for demos
- `detector_type`: "zscore" or "percentile"

## Phase 5 Gates

### Gate 1: Episode vs Controls

Requires:
- Δz ≤ -0.75 (episode significantly lower than controls)
- p < 0.10 (block bootstrap)
- Duration ≥ 10 seconds
- **Only applies to real data, not demos**

### Gate 2: Lead-Lag Edges

- |ρ| ≥ 0.12 and p < 0.10
- Edge vanishes under time-shift placebo (±30-60s)

### Gate 3: InfoShare Stability

- Top venue stable across 1m vs 500ms resampling
- Remains top-1 after volume-share normalization

## Defaults & Backward Compatibility

- Default detector: `percentile` (original method)
- Z-score detector: `--detector zscore`
- All parameters configurable via CLI
- Original percentile detector unchanged

## Caveats

1. **Demo Data**: Never use demo/synthetic data for regulatory conclusions
2. **Sample Size**: Z-score detector requires sufficient baseline data
3. **Feature Selection**: Matched control features may need adjustment for different markets
4. **Bootstrap**: Block size should match expected episode duration

## ⚠️ Important: Demo Data Usage

**Demos are never used in court workflows. Passing --allow-demo tags outputs with "provenance":"DEMO" and "regulatory_grade": false.**

Demo data is strictly for method development and testing. All court-ready evidence must use real market data with proper provenance tracking.

## Usage

```bash
# Original percentile detector (default)
python scripts/gold_hunt_control_v2.py --snapshot-dir court/1s --export-dir results/

# Z-score detector with custom parameters
python scripts/gold_hunt_control_v2.py \
  --detector zscore \
  --snapshot-dir court/1s \
  --export-dir results/ \
  --roll 60 \
  --z-thresh -1.5 \
  --merge-gap 2 \
  --min-dur 10 \
  --mc-per-episode 100 \
  --bb-n 1000 \
  --seed 42

# Demo data (for testing only)
python scripts/gold_hunt_control_v2.py \
  --snapshot-dir demos/spread_v2_demo/ \
  --export-dir results/ \
  --allow-demo
```
