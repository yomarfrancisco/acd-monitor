# Canonical Data Schema for Wave-1 Analysis

This document describes the effective schema used in canonical data validation for Wave-1 analysis.

## Overview

The canonical data is stored in S3 as Parquet files with the following structure:
- **Location**: `s3://acd-monitor-snapshots/canonical/20251001/`
- **Format**: Parquet (columnar storage)
- **Partitioning**: By symbol (`btc_ticks/`, `eth_ticks/`) and venue (`venue=coinbase`, `venue=kraken`, `venue=okx`)

## Schema Definition

### Core Fields

| Field Name | Type | Description | Notes |
|------------|------|-------------|-------|
| `symbol` | STRING | Trading pair symbol | Always "BTC-USD" or "ETH-USD" |
| `venue` | STRING | Exchange venue identifier | Values: "coinbase", "kraken", "okx" |
| `ts_exchange_ms` | BIGINT | Exchange timestamp in milliseconds | Unix epoch in milliseconds |
| `ts_exchange` | TIMESTAMP | Exchange timestamp (derived) | Computed from `ts_exchange_ms` |
| `last_px` | DOUBLE | Last traded price | Primary price field for analysis |
| `best_bid` | DOUBLE | Best bid price | Order book bid side |
| `best_ask` | DOUBLE | Best ask price | Order book ask side |
| `trade_sz` | DOUBLE | Trade size/volume | Transaction volume |
| `vdate_ymd` | STRING | Date in YYYYMMDD format | Extracted from timestamp |
| `vwindow` | STRING | Time window identifier | Format: "HHMM-HHMM" |
| `_path` | STRING | Source S3 object path | For lineage tracking |

### Derived Fields (Computed in Analysis)

| Field Name | Type | Description | Computation |
|------------|------|-------------|-------------|
| `mid_px` | DOUBLE | Mid price | `(best_bid + best_ask) / 2.0` |
| `spread_bps` | DOUBLE | Spread in basis points | `(best_ask - best_bid) / mid_px * 10000` |
| `sanity_price_ok` | INTEGER | Price sanity flag | `1` if price >= floor, `0` otherwise |

## Data Quality Constraints

### Price Sanity Rules
- **BTC-USD**: `last_px >= 80000` for dates >= 2025-01-01
- **ETH-USD**: `last_px >= 2000` for dates >= 2025-01-01

### Uniqueness Constraints
- Primary key: `(symbol, venue, ts_exchange_ms)`
- No duplicate records allowed
- Each venue-symbol-timestamp combination must be unique

### Venue Coverage (2025-10-01)
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

## Price Range Validation

### BTC-USD
- **Minimum**: >= $80,000
- **Maximum**: <= $118,500 (±0.5% slack)
- **Typical range**: $114,000 - $118,000

### ETH-USD
- **Minimum**: >= $2,000
- **Maximum**: <= $4,500
- **Typical range**: $4,290 - $4,340

## Timestamp Handling

### Epoch Conversion
```python
# Convert ts_exchange_ms to timestamp
ts_exchange = pd.to_datetime(ts_exchange_ms, unit='ms', utc=True)
```

### Time Window Derivation
```python
# Extract date and window from timestamp
vdate_ymd = ts_exchange.dt.strftime('%Y%m%d')
vwindow = ts_exchange.dt.strftime('%H%M') + '-' + (ts_exchange + pd.Timedelta(minutes=30)).dt.strftime('%H%M')
```

## Data Access Patterns

### Direct S3 Access
```python
import boto3
import pandas as pd

s3 = boto3.client('s3')
key = 'canonical/20251001/btc_ticks/venue=coinbase/part-0000.parquet'
file_obj = s3.get_object(Bucket='acd-monitor-snapshots', Key=key)
df = pd.read_parquet(io.BytesIO(file_obj['Body'].read()))
```

### Athena Queries (Planned)
```sql
-- Future Athena view (not yet deployed)
SELECT symbol, venue, ts_exchange_ms, last_px, best_bid, best_ask
FROM acd_canonical.btc_ticks_20251001_v1
WHERE ts_exchange >= TIMESTAMP '2025-10-01 00:00:00'
  AND ts_exchange < TIMESTAMP '2025-10-02 00:00:00'
```

## Validation Rules

### Row Count Validation
- Counts must match expected values exactly
- No missing or extra records allowed

### Range Validation
- All prices must be within sanity bounds
- No negative or zero prices allowed
- No extreme outliers (>3σ from mean)

### Uniqueness Validation
- No duplicate keys allowed
- Each record must be unique on primary key

### Venue Validation
- Only expected venues present
- No unexpected venues (e.g., bybit, binance)
- Venue coverage matches expectations

## Known Issues and Limitations

### Bybit Data Missing
- **Issue**: Epoch-0 timestamps in raw data
- **Impact**: No bybit data in canonical dataset
- **Status**: Tracked for parser hotfix and re-ingest

### Binance Data Missing
- **Issue**: WebSocket geofence restrictions
- **Impact**: No binance data in canonical dataset
- **Status**: Tracked for WS proxy or self-hosted runner solution

### Athena View Creation
- **Issue**: Permission/creation errors in Athena
- **Impact**: Views not yet deployed
- **Workaround**: Use direct S3 access via `reader_validate.py`

## Usage Examples

### Validation Script
```bash
python analytics/reader_checks/reader_validate.py --date 20251001
```

### Expected Output
- Row counts match expected values
- Price ranges within sanity bounds
- Uniqueness constraints satisfied
- Venue coverage as expected
- All validations pass for Wave-1 readiness

## Related Files

- `analytics/reader_checks/reader_validate.py` - Validation script
- `analytics/reader_checks/EXPECTED_COUNTS_20251001.json` - Expected counts
- `sql/athena/reader_views/` - Planned Athena DDL files
- `artifacts/_checks_reader/` - Validation artifacts
