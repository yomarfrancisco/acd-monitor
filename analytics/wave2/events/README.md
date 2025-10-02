# Wave-2 Event Studies Engine

## Overview
Event studies engine for competitive behavior screening in cryptocurrency markets. Computes event study metrics around exogenous timing shocks to detect potential coordination patterns.

## Inputs
- **Canonical Data**: `s3://{bucket}/canonical/{DATE}/{symbol}/panel_1s_inner.parquet`
- **Environment Flags** (optional): `s3://{bucket}/data/derived/{symbol}/env_flags_1s.parquet`

## Event Types Detected
1. **NY Open**: 13:30-13:45 UTC (market open shock)
2. **VWAP Reset**: 00:00-00:05 UTC (daily reset shock)
3. **2-Sigma Return Shocks**: Per-venue return volatility spikes
4. **2-Sigma VWAP Deviations**: Per-venue VWAP deviation spikes

## Metrics Computed
- **CAR**: Cumulative Abnormal Returns (60s, 300s windows)
- **Spread Changes**: Pre vs post-event spread differences
- **Volume Changes**: Trading volume proxy changes
- **Hit Ratio**: Sign consistency of immediate returns

## Outputs
- **events.parquet**: Per-venue event metrics
- **manifest.json**: Metadata and QC statistics

## Usage
```bash
python3 analytics/wave2/events/runner.py \
  --date 20251001 \
  --bucket acd-monitor-snapshots \
  --symbol btc_usd \
  --no-overwrite
```

## Quality Controls
- Minimum 5 samples per event window
- No-overwrite protection for existing outputs
- Status tracking: success/insufficient_sample/no_data
- Read-only canonical inputs, write-only to analysis paths

## Guardrails
- BTC only (ETH remains soft-check)
- Single date per run
- No overwrite if target exists
- S3 read-only for canonical data

