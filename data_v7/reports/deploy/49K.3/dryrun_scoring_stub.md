# Dry-Run Scoring Stub

## Usage

```bash
# Load feature matrix and score
python score_css_collapse.py --input features.parquet --output scores.json
```

## Input Format

Feature matrix with columns:
1. `price_coord_drift`
2. `price_corr_lag_1`
3. `css_diff_std_6h`
4. `css_diff_std_24h`
5. `is_asia`
6. `is_weekend`

## Output Format

```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "venue": "binance",
  "calibrated_prob_6h": 0.123,
  "calibrated_prob_12h": 0.145,
  "decision_6h": "alert",
  "decision_12h": "monitor",
  "conformal_flag_6h": true,
  "conformal_flag_12h": false
}
```



## Thresholds

### 6h Horizon
- Enter: 0.3889
- Exit: 0.3389
- Cooldown: 2h

### 12h Horizon
- Enter: 0.5
- Exit: 0.45
- Cooldown: 2h

## Conformal Cutoffs

### 6h Horizon
- Cutoff: 0.35
- Target FPR: ≤ 0.25

### 12h Horizon
- Cutoff: 0.45
- Target FPR: ≤ 0.25

