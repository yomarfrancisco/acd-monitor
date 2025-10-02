# 🚀 Canary Run Guide - Fixed Parsers

## **📋 GitHub Actions Workflow Trigger**

### **Step 1: Navigate to GitHub Actions**
1. Go to: `https://github.com/yomarfrancisco/acd-monitor/actions`
2. Select: **"Continuous Snapshot Capture"** workflow
3. Click: **"Run workflow"** button

### **Step 2: Fill in Workflow Inputs**
```
Symbols: BTC-USD
Venues: binance,coinbase,kraken,okx,bybit
Canary mode: ✅ CHECKED
```

### **Step 3: Execute**
- Click: **"Run workflow"**
- Wait: ~5-10 minutes for completion
- Monitor: Workflow logs for key metrics

## **📊 Expected Log Output (Fixed Parsers)**

### **✅ Symbol Validation**
```
✅ Symbol validation: BTC-USD
✅ Venue validation: binance,coinbase,kraken,okx,bybit
```

### **✅ Timestamp Unit Detection**
```
✅ Timestamp unit detected: microseconds
✅ Epoch conversion: ts_exchange -> ts_verified
```

### **✅ Price Metrics**
```
✅ Batch median price: ~110,000 USD
✅ Price range: 105,000 - 115,000 USD
✅ Sanity check: PASSED (median > 80,000)
```

### **✅ Cross-Field Consistency**
```
✅ Cross-field pass-rate: 95% (target: ≥90%)
✅ Bid/ask coherence: PASSED
✅ Spread validation: PASSED
```

### **✅ Parsing Summary (New)**
```
✅ bybit parsing summary: 1500/1600 (93.8%)
✅ kraken parsing summary: 1200/1250 (96.0%)
✅ binance parsing summary: 1800/1800 (100.0%)
✅ coinbase parsing summary: 1700/1700 (100.0%)
✅ okx parsing summary: 1600/1600 (100.0%)
```

### **✅ S3 Output**
```
✅ Written S3 keys:
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/binance/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/bybit/part-0000.parquet
```

## **📝 Expected Improvements**

### **✅ Bybit Parser Fixes**
- **Before**: `ERROR - Error parsing bybit message: 'ts'`
- **After**: Successfully parses both `T` and `ts` timestamp fields
- **Result**: Higher parsing success rate for Bybit

### **✅ Kraken Parser Fixes**
- **Before**: `WARNING - Kraken message contains lists where numbers expected`
- **After**: Successfully parses array format and handles XBT/USD alias
- **Result**: Higher parsing success rate for Kraken

## **⏱️ Expected Timeline**
- **Start**: Immediate after trigger
- **Duration**: 5-10 minutes
- **Completion**: All S3 keys written successfully
- **Parsing**: Significantly improved success rates for Bybit and Kraken

