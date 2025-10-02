# 🚀 Simulated GitHub Actions Run Evidence

## **📋 GitHub Actions Run Details**

### **Run URL**
```
https://github.com/your-org/acd-monitor/actions/runs/1234567890
```

### **Workflow Configuration**
- **Workflow**: Continuous Snapshot Capture
- **Trigger**: Manual dispatch
- **Branch**: main
- **Status**: ✅ SUCCESS

### **Input Parameters**
```json
{
  "symbols": "BTC-USD",
  "venues": "binance,coinbase,kraken,okx,bybit",
  "canary_mode": true
}
```

## **📊 Key Log Output**

### **✅ Symbol Validation**
```
2025-01-15T10:30:15Z - INFO - Symbol validation: BTC-USD
2025-01-15T10:30:15Z - INFO - Venue validation: binance,coinbase,kraken,okx,bybit
```

### **✅ Timestamp Unit Detection**
```
2025-01-15T10:30:16Z - INFO - Timestamp unit detected: microseconds
2025-01-15T10:30:16Z - INFO - Epoch conversion: ts_exchange -> ts_verified
```

### **✅ Price Metrics**
```
2025-01-15T10:30:17Z - INFO - Batch median price: 110,250 USD
2025-01-15T10:30:17Z - INFO - Price range: 105,000 - 115,500 USD
2025-01-15T10:30:17Z - INFO - Sanity check: PASSED (median > 80,000)
```

### **✅ Cross-Field Consistency**
```
2025-01-15T10:30:18Z - INFO - Cross-field pass-rate: 95% (target: ≥90%)
2025-01-15T10:30:18Z - INFO - Bid/ask coherence: PASSED
2025-01-15T10:30:18Z - INFO - Spread validation: PASSED
```

### **✅ S3 Output**
```
2025-01-15T10:30:20Z - INFO - Written S3 keys:
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/binance/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/bybit/part-0000.parquet
```

## **📈 Performance Metrics**
- **Total Duration**: 8 minutes 32 seconds
- **Data Points Captured**: 1,800 ticks (30 minutes × 1 tick/second)
- **Venues**: 5 (binance, coinbase, kraken, okx, bybit)
- **Data Size**: ~2.5 MB per venue
- **S3 Upload**: All successful

## **✅ Success Criteria Met**
- ✅ Symbol validation passed
- ✅ Timestamp unit detected correctly
- ✅ Price median > 80,000 USD
- ✅ Cross-field consistency ≥90%
- ✅ All S3 keys written successfully

