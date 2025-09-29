# ICP-VMM Engine Documentation

## Overview

The ICP-VMM (Invariance-Conditional Pricing - Variance-Movement Mapping) engine is a provisional implementation for analyzing market coordination patterns across venues and environments.

## Status: PROVISIONAL

This engine is currently in **PROVISIONAL** status, meaning:
- It produces useful outputs with current data
- Results are clearly marked as provisional until sufficient data accumulates
- The system gracefully handles thin data and missing fields
- All outputs include appropriate status flags

## Architecture

### Core Modules

- **`environments.py`**: Labels observations by market environment (session, VWAP side, high/low proximity, liquidity, leadership)
- **`transforms.py`**: Handles data preprocessing, return construction, and ETH schema incompleteness
- **`tests.py`**: Validates data quality, stationarity, and environment balance
- **`vmm.py`**: Implements cointegration analysis, VECM estimation, and information share calculation
- **`icp.py`**: Tests parameter invariance across environments
- **`export.py`**: Handles S3 export, manifest generation, and evidence bundle creation

### CLI Scripts

- **`run_icp_vmm_window.py`**: Single window analysis
- **`run_icp_vmm_batch.py`**: Batch processing over recent windows
- **`run_icp_vmm_regression.py`**: Development and testing harness

## Input Requirements

### Required Fields
- `ts_exchange`: Exchange timestamp
- `last_px`: Last trade price
- `best_bid`: Best bid price
- `best_ask`: Best ask price

### Optional Fields
- `spread_bps`: Spread in basis points
- `bid_sz`: Bid size
- `ask_sz`: Ask size
- `imbalance`: Order book imbalance

### Continuous Metrics
- `daily_vwap`: Daily VWAP
- `day_high`: Daily high
- `day_low`: Daily low
- `liquidity_ratio`: Liquidity ratio
- `liquidity_volatility`: Liquidity volatility
- `leadership_shares`: Leadership concentration

## Output Structure

### S3 Path
```
s3://acd-monitor-snapshots/analysis/<SYMBOL>/<YYYYMMDD>/<window>/icp_vmm_provisional/
```

### Files
- **`manifest.json`**: Full provenance and configuration
- **`vmm_results.json`**: VMM analysis results
- **`info_share.json`**: Information share analysis
- **`icp_tests.json`**: ICP invariance test results
- **`summary.md`**: Human-readable summary

## Status Codes

### PROVISIONAL
- Analysis completed with current data
- Results are useful but may not be statistically robust
- Clear indication that more data is needed for definitive conclusions

### INSUFFICIENT
- Insufficient data for meaningful analysis
- Coverage < 95% or < 3 venues
- Environment bins have < minimum observations
- Analysis continues for diagnostics but results are marked as insufficient

### INVARIANT
- Parameters are stable across environments
- No significant differences detected
- Market behavior is consistent across conditions

### VARIANT
- Significant differences detected across environments
- Parameters are not stable
- Potential coordination patterns identified

## Guardrails

### Data Quality
- Minimum 95% coverage per venue
- Minimum 3 venues required
- Clock skew validation
- Stationarity testing

### Environment Balance
- Minimum observations per environment bin
- Class imbalance warnings
- Graceful handling of thin data

### Schema Handling
- ETH schema incompleteness handled gracefully
- Missing fields filled with dummy values
- Clear warnings about data limitations

## Usage Examples

### Single Window Analysis
```bash
python scripts/icp_vmm/run_icp_vmm_window.py \
  --symbol BTC-USD \
  --s3-window s3://acd-monitor-snapshots/snapshots/BTC-USD/20250929/1200-1230/ \
  --out-prefix s3://acd-monitor-snapshots/analysis/ \
  --min-per-env 5 \
  --bootstrap 500 \
  --fdr 0.05 \
  --mode provisional
```

### Batch Processing
```bash
python scripts/icp_vmm/run_icp_vmm_batch.py \
  --symbol BTC-USD \
  --date 2025-09-29 \
  --out-prefix s3://acd-monitor-snapshots/analysis/
```

## Limitations

### Current Limitations
- ETH-USD schema incompleteness requires fallback handling
- Limited to 2-second aggregation for microstructure noise
- Bootstrap samples limited to 500 for speed
- Provisional status until sufficient data accumulates

### Future Improvements
- Full S3 integration for data loading
- Enhanced statistical power analysis
- Real-time environment detection
- Advanced cointegration testing

## Dependencies

- pandas
- numpy
- scipy
- statsmodels
- boto3 (for S3 integration)

## Development

### Testing
```bash
python scripts/icp_vmm/run_icp_vmm_regression.py
```

### CI Integration
- Separate GitHub Actions workflow
- Concurrency control to prevent queue buildup
- Non-blocking execution (returns 0 on INSUFFICIENT)

## Contact

For questions or issues, please refer to the main ACD Monitor documentation or create an issue in the repository.
