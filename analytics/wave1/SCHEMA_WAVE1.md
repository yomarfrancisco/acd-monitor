# Wave-1 Variables Schema for Competitive Behavior Analysis

This document describes the Wave-1 variables computed for competitive behavior screening and coordination risk detection.

## Overview

Wave-1 variables are designed to detect abnormal comovement and coordination patterns in cryptocurrency exchange data. The analysis focuses on:

- **H₀ (Null Hypothesis)**: Prices/spreads behave competitively (expected variance & cross-venue dynamics)
- **H₁ (Alternative Hypothesis)**: Patterns show abnormal comovement/stability (coordination risk)

## Data Sources

- **Canonical Data**: `s3://acd-monitor-snapshots/canonical/20251001/`
- **Symbols**: BTC-USD, ETH-USD
- **Venues**: BTC {coinbase, kraken, okx}, ETH {coinbase, kraken}
- **Date**: 2025-10-01 (single canonical day)

## Variable Families

### 1. Returns & Variance Ratios (`variance_ratios.parquet`)

**Purpose**: Detect abnormal return patterns and variance structure

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue` | STRING | Exchange venue identifier |
| `n_obs` | INTEGER | Number of observations |
| `var_1s` | DOUBLE | Variance of 1-second returns |
| `var_5s` | DOUBLE | Variance of 5-second returns |
| `vr_ratio` | DOUBLE | Variance ratio (1s/5s) |
| `mean_return_1s` | DOUBLE | Mean 1-second return |
| `mean_return_5s` | DOUBLE | Mean 5-second return |
| `std_return_1s` | DOUBLE | Standard deviation of 1-second returns |
| `std_return_5s` | DOUBLE | Standard deviation of 5-second returns |

**Interpretation**:
- `vr_ratio > 1`: Higher short-term variance (potential manipulation)
- `vr_ratio < 1`: Lower short-term variance (potential coordination)
- Expected competitive range: 0.8-1.2

### 2. Autocorrelation (`autocorr.parquet`)

**Purpose**: Detect serial correlation in returns (market efficiency test)

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue` | STRING | Exchange venue identifier |
| `n_obs` | INTEGER | Number of observations |
| `ar1_coef` | DOUBLE | AR(1) autocorrelation coefficient |
| `ar2_coef` | DOUBLE | AR(2) autocorrelation coefficient |
| `ar3_coef` | DOUBLE | AR(3) autocorrelation coefficient |
| `ar5_coef` | DOUBLE | AR(5) autocorrelation coefficient |

**Interpretation**:
- `ar1_coef ≈ 0`: Efficient market (competitive)
- `ar1_coef > 0.1`: Potential momentum/trend following
- `ar1_coef < -0.1`: Potential mean reversion/coordination

### 3. Cross-Correlation (`xcorr.parquet`)

**Purpose**: Detect abnormal comovement between venues

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue1` | STRING | First venue identifier |
| `venue2` | STRING | Second venue identifier |
| `n_aligned` | INTEGER | Number of aligned observations |
| `cross_corr` | DOUBLE | Cross-correlation coefficient |

**Note**: This artifact has a pairwise schema (venue1/venue2) rather than per-venue schema.

**Interpretation**:
- `cross_corr ≈ 0`: Independent venues (competitive)
- `cross_corr > 0.5`: High comovement (potential coordination)
- `cross_corr < -0.5`: Negative comovement (potential manipulation)

### 4. PCA Analysis (`pca.parquet`)

**Purpose**: Detect common factors and systematic risk

**Note**: This artifact is optional and may be skipped if insufficient common timestamps exist.

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue` | STRING | Exchange venue identifier |
| `n_obs` | INTEGER | Number of observations |
| `explained_variance_ratio` | DOUBLE | Explained variance ratio for this venue |
| `component_1` | DOUBLE | Loading on first principal component |
| `component_2` | DOUBLE | Loading on second principal component |
| `component_3` | DOUBLE | Loading on third principal component |

**When skipped**: Contains metadata with `status: "skipped"`, `reason`, and `n_common` fields.

**Interpretation**:
- High `explained_variance_ratio` on first component: Common factor dominance
- Similar `component_1` across venues: Systematic coordination
- Expected competitive: Balanced loadings across components

### 5. Rolling Volatility & Spread Convergence (`rolling.parquet`)

**Purpose**: Detect volatility clustering and spread dynamics

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue` | STRING | Exchange venue identifier |
| `n_obs` | INTEGER | Number of observations |
| `mean_vol_60s` | DOUBLE | Mean 60-second rolling volatility |
| `std_vol_60s` | DOUBLE | Standard deviation of rolling volatility |
| `min_vol_60s` | DOUBLE | Minimum rolling volatility |
| `max_vol_60s` | DOUBLE | Maximum rolling volatility |
| `mean_spread_60s` | DOUBLE | Mean 60-second rolling spread (%) |
| `std_spread_60s` | DOUBLE | Standard deviation of rolling spread |

**Interpretation**:
- High `std_vol_60s`: Volatility clustering (normal market behavior)
- Low `std_vol_60s`: Smooth volatility (potential coordination)
- Converging spreads: Competitive behavior
- Diverging spreads: Potential manipulation

## Data Quality Constraints

### Price Sanity Rules
- **BTC-USD**: `last_px >= 80000` for 2025+ dates
- **ETH-USD**: `last_px >= 2000` for 2025+ dates

### Uniqueness Constraints
- Primary key: `(symbol, venue, ts_exchange_ms)`
- No duplicate records allowed

### Venue Coverage
- **BTC-USD**: coinbase, kraken, okx
- **ETH-USD**: coinbase, kraken
- **Excluded**: bybit (epoch-0 timestamps), binance (geofence issues)

## Expected Data Volumes (2025-10-01)

### BTC-USD
- **coinbase**: 9,737 records
- **kraken**: 3,753 records  
- **okx**: 14,484 records
- **Total**: 27,974 records

### ETH-USD
- **coinbase**: 4,170 records
- **kraken**: 1,198 records
- **Total**: 5,368 records

## Competitive Behavior Indicators

### Normal Competitive Behavior
- **Variance Ratios**: 0.8-1.2 (efficient price discovery)
- **Autocorrelation**: |ar1_coef| < 0.1 (efficient market)
- **Cross-Correlation**: 0.2-0.6 (normal comovement)
- **PCA**: Balanced explained variance across components
- **Volatility**: Natural clustering and mean reversion

### Coordination Risk Indicators
- **Variance Ratios**: < 0.5 or > 2.0 (abnormal variance structure)
- **Autocorrelation**: |ar1_coef| > 0.3 (strong serial correlation)
- **Cross-Correlation**: > 0.8 (excessive comovement)
- **PCA**: First component explains > 80% of variance
- **Volatility**: Unusually smooth or synchronized patterns

### Manipulation Risk Indicators
- **Variance Ratios**: Extreme values (< 0.2 or > 5.0)
- **Autocorrelation**: Strong negative correlation (< -0.3)
- **Cross-Correlation**: Negative correlation (< -0.5)
- **PCA**: Unusual component loadings
- **Volatility**: Artificial patterns or sudden changes

## Storage and Access

### S3 Location
```
s3://acd-monitor-snapshots/analysis/20251001/wave1/
├── btc_usd/
│   ├── variance_ratios.parquet
│   ├── autocorr.parquet
│   ├── xcorr.parquet
│   ├── pca.parquet
│   └── rolling.parquet
├── eth_usd/
│   ├── variance_ratios.parquet
│   ├── autocorr.parquet
│   ├── xcorr.parquet
│   ├── pca.parquet
│   └── rolling.parquet
└── _checks/
    └── manifest.json
```

### Manifest Schema
```json
{
  "timestamp": "2025-10-01T...",
  "stage": "F",
  "date": "20251001",
  "wave1_analysis": true,
  "symbols": ["BTC-USD", "ETH-USD"],
  "artifacts": {
    "BTC-USD": {
      "variance_ratios": {
        "rows": 3,
        "columns": 9,
        "sha256": "...",
        "venues": ["coinbase", "kraken", "okx"]
      }
    }
  }
}
```

## Usage Examples

### Load Wave-1 Data
```python
import boto3
import pandas as pd
import io

s3 = boto3.client('s3')
key = 'analysis/20251001/wave1/btc_usd/variance_ratios.parquet'
file_obj = s3.get_object(Bucket='acd-monitor-snapshots', Key=key)
df = pd.read_parquet(io.BytesIO(file_obj['Body'].read()))
```

### Competitive Behavior Screening
```python
# Check for coordination risk
high_corr = df[df['cross_corr'] > 0.8]
if len(high_corr) > 0:
    print("⚠️ High cross-correlation detected - potential coordination")

# Check for manipulation risk
extreme_vr = df[(df['vr_ratio'] < 0.2) | (df['vr_ratio'] > 5.0)]
if len(extreme_vr) > 0:
    print("⚠️ Extreme variance ratios detected - potential manipulation")
```

## Related Files

- `analytics/wave1/compute_wave1.py` - Computation script
- `analytics/reader_checks/reader_validate.py` - Canonical data validation
- `analytics/reader_checks/SCHEMA.md` - Canonical data schema
- `.github/workflows/wave1-variables.yml` - CI validation workflow
