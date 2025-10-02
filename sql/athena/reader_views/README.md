# Athena Reader Views for Wave-1 Analysis

This directory contains DDL files for creating Athena views that provide read-only access to canonical data for Wave-1 analysis.

## Status: Not Yet Deployed

⚠️ **Important**: These views are not yet deployed due to current permission/creation errors in Athena. Use `analytics/reader_checks/reader_validate.py` as the authoritative reader for Wave-1 analysis.

## Files

### `btc_ticks_20251001_v1.sql`
- **Purpose**: Read-only access to BTC-USD tick data for 2025-10-01
- **Location**: `s3://acd-monitor-snapshots/canonical/20251001/btc_ticks/`
- **Venues**: coinbase, kraken, okx
- **Expected Records**: 27,974 total

### `eth_ticks_20251001_v1.sql`
- **Purpose**: Read-only access to ETH-USD tick data for 2025-10-01
- **Location**: `s3://acd-monitor-snapshots/canonical/20251001/eth_ticks/`
- **Venues**: coinbase, kraken
- **Expected Records**: 5,368 total

## Schema

Both views expose the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | STRING | Trading pair symbol |
| `venue` | STRING | Exchange venue identifier |
| `ts_exchange_ms` | BIGINT | Exchange timestamp in milliseconds |
| `ts_exchange` | TIMESTAMP | Exchange timestamp (derived) |
| `last_px` | DOUBLE | Last traded price |
| `best_bid` | DOUBLE | Best bid price |
| `best_ask` | DOUBLE | Best ask price |
| `trade_sz` | DOUBLE | Trade size/volume |
| `vdate_ymd` | STRING | Date in YYYYMMDD format |
| `vwindow` | STRING | Time window identifier |
| `_path` | STRING | Source S3 object path |

## Data Quality Filters

### Price Sanity Checks
- **BTC-USD**: `last_px >= 80000` for 2025+ dates
- **ETH-USD**: `last_px >= 2000` for 2025+ dates

### Venue Filters
- **BTC-USD**: Only coinbase, kraken, okx (excludes bybit, binance)
- **ETH-USD**: Only coinbase, kraken (excludes bybit, binance, okx)

### Data Completeness
- `ts_exchange_ms IS NOT NULL`
- `last_px IS NOT NULL`
- `symbol` matches expected value

## Deployment Notes

### Current Issues
1. **Permission Errors**: Athena table/view creation failing
2. **Schema Mismatches**: Column order/type issues
3. **Path Resolution**: S3 path resolution problems

### Workaround
Use direct S3 access via `analytics/reader_checks/reader_validate.py`:
```bash
python analytics/reader_checks/reader_validate.py --date 20251001
```

### Future Deployment
Once Athena issues are resolved:
1. Create database: `acd_canonical`
2. Execute DDL files in order
3. Validate views return expected data
4. Update Wave-1 analysis to use views

## Usage Examples

### Query BTC Data
```sql
SELECT venue, COUNT(*) as record_count, AVG(last_px) as avg_price
FROM acd_canonical.btc_ticks_20251001_v1
WHERE ts_exchange >= TIMESTAMP '2025-10-01 00:00:00'
  AND ts_exchange < TIMESTAMP '2025-10-02 00:00:00'
GROUP BY venue
ORDER BY venue;
```

### Query ETH Data
```sql
SELECT venue, COUNT(*) as record_count, AVG(last_px) as avg_price
FROM acd_canonical.eth_ticks_20251001_v1
WHERE ts_exchange >= TIMESTAMP '2025-10-01 00:00:00'
  AND ts_exchange < TIMESTAMP '2025-10-02 00:00:00'
GROUP BY venue
ORDER BY venue;
```

## Validation

### Expected Counts
- **BTC-USD**: 27,974 records (coinbase: 9,737, kraken: 3,753, okx: 14,484)
- **ETH-USD**: 5,368 records (coinbase: 4,170, kraken: 1,198)

### Price Ranges
- **BTC-USD**: $80,000 - $118,500
- **ETH-USD**: $2,000 - $4,500

### Uniqueness
- Primary key: `(symbol, venue, ts_exchange_ms)`
- No duplicate records allowed

## Related Files

- `analytics/reader_checks/reader_validate.py` - Validation script
- `analytics/reader_checks/SCHEMA.md` - Schema documentation
- `analytics/reader_checks/EXPECTED_COUNTS_20251001.json` - Expected counts
- `artifacts/_checks_reader/` - Validation artifacts

