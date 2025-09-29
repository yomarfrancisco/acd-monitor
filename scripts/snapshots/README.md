# S3 Snapshot Tools

Tools for writing and verifying snapshots in S3 following the agreed schema.

## Schema

```
s3://acd-monitor-snapshots/snapshots/{symbol}/{yyyymmdd}/{HHMM}-{HHMM}/
  OVERLAP.json
  ticks/{venue}.parquet
  meta/provenance.json
```

## Environment Variables

- `ACD_S3_BUCKET`: S3 bucket name (default: `acd-monitor-snapshots`)
- `ACD_S3_PREFIX`: S3 prefix (default: `snapshots`)
- `AWS_DEFAULT_REGION`: AWS region (default: `us-east-1`)

## Tools

### `write_snapshot.py`

Write a complete snapshot to S3 with synthetic tick data.

```bash
python scripts/snapshots/write_snapshot.py \
  --date 2025-09-28 \
  --start-time 0200 \
  --end-time 0230 \
  --venues "binance,coinbase" \
  --verbose
```

### `verify_snapshot.py`

Verify snapshot integrity, coverage, and clock skew.

```bash
python scripts/snapshots/verify_snapshot.py \
  --overlap "s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/OVERLAP.json" \
  --verbose
```

## Smoke Test

```bash
# Set environment
export ACD_S3_BUCKET=acd-monitor-snapshots
export ACD_S3_PREFIX=snapshots
export AWS_DEFAULT_REGION=us-east-1

# Create test snapshot
python scripts/snapshots/write_snapshot.py \
  --date 2025-09-28 \
  --start-time 0200 \
  --end-time 0230 \
  --venues "binance,coinbase" \
  --verbose

# Verify snapshot
python scripts/snapshots/verify_snapshot.py \
  --overlap "s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/OVERLAP.json" \
  --verbose
```
