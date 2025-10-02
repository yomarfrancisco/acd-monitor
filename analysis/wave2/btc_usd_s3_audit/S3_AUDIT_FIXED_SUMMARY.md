# Fixed S3 BTC-USD Data Availability Audit

**Audit Date**: 2025-09-30T16:58:05.915911
**S3 Bucket**: acd-monitor-snapshots
**Prefix**: snapshots/BTC-USD/

## Summary

- **Total Objects**: 194
- **Parquet Files**: 101
- **Distinct Dates**: 4
- **Distinct Time Windows**: 24
- **Earliest Date**: 2025-09-28
- **Latest Date**: 20250930
- **Total Size**: 27,949,470 bytes

## Venue Coverage

- **binance**: 16 files, 5,453,758 bytes, 1 dates
- **coinbase**: 22 files, 5,274,310 bytes, 2 dates
- **kraken**: 16 files, 5,453,690 bytes, 1 dates
- **okx**: 22 files, 5,233,544 bytes, 2 dates
- **bybit**: 16 files, 5,453,601 bytes, 1 dates

## Date Analysis

### 20250928
- **Parquet Files**: 9
- **Venues Present**: 5 (kraken.parquet, coinbase.parquet, okx.parquet, bybit.parquet, binance.parquet)
- **Time Windows**: ['0200-0230', '1015-1045', '1000-1030']
- **Total Size**: 1,080,567 bytes

### 20250929
- **Parquet Files**: 82
- **Venues Present**: 5 (bybit, coinbase, okx, binance, kraken)
- **Time Windows**: ['0745-0815', '1300-1330', '0945-1015', '0730-0800', '0830-0900', '0930-1000', '1030-1100', '1100-1130', '1000-1030', '1330-1400', '1230-1300', '0800-0830', '1045-1115', '1200-1500', '0845-0915', '0900-0930', '1200-1230']
- **Total Size**: 26,711,456 bytes

### 20250930
- **Parquet Files**: 10
- **Venues Present**: 2 (coinbase, okx)
- **Time Windows**: ['1145-1215', '1345-1415', '1300-1330', '1215-1245', '1400-1430']
- **Total Size**: 157,447 bytes

## Recommendations

- ✅ Sufficient data available for multi-day analysis
- 💡 Proceed with real data alignment and extended analysis
- ✅ Good venue coverage for analysis

## Next Steps

✅ **Proceed with real data alignment**
- Assemble multi-day panel from real S3 data
- Run extended Wave-2 analysis on authentic data
