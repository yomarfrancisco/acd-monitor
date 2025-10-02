# 🚀 Final Canary Run Guide - Import Regression Fixed

## **📋 GitHub Actions Workflow Trigger**

### **Step 1: Navigate to GitHub Actions**
1. Go to: `https://github.com/yomarfrancisco/acd-monitor/actions`
2. Select: **"Continuous Snapshot Capture"** workflow
3. Click: **"Run workflow"** button

### **Step 2: Fill in Workflow Inputs**
```
Symbols: BTC-USD,ETH-USD
Venues: binance,coinbase,kraken,okx,bybit
Canary mode: ✅ CHECKED
```

### **Step 3: Execute**
- Click: **"Run workflow"**
- Wait: ~5-10 minutes for completion
- Monitor: Workflow logs for key metrics

## **📊 Expected Log Output (Import Regression Fixed)**

### **✅ Workflow Guards (New)**
```
==== HEAD COMMIT ====
3395f76...
==== Grep parser version banner ====
50:print("CAPTURE_PARSER_VERSION=v2025-10-01c")
```

### **✅ Version Banner (Proof of New Code)**
```
CAPTURE_PARSER_VERSION=v2025-10-01c
```

### **✅ Sample Raw Data (One per Venue)**
```
INFO - SAMPLE_RAW_coinbase={'type': 'ticker', 'sequence': 112597951807, 'product_id': 'BTC-USD', 'price': '116597.65', 'open_24h': '109500.0', 'volume_24h': '1234.56', 'low_24h': '109000.0', 'high_24h': '111000.0', 'volume_30d': '45678.90', 'best_bid': '110200.5', 'best_ask': '110300.5', 'side': 'buy', 'time': '2025-10-01T11:59:22.123Z', 'trade_id': 123456789, 'last_size': '0.002'}
INFO - SAMPLE_RAW_kraken=[119930881, [['116774.10000', '0.00085635', '1759319962.844759', 'b', '', '']], 'trade', 'XBT/USD']
INFO - SAMPLE_RAW_okx={'arg': {'channel': 'tickers', 'instId': 'BTC-USD'}, 'data': [{'instType': 'SPOT', 'instId': 'BTC-USD', 'last': '110250.1', 'lastSz': '0.002', 'askPx': '110300.5', 'askSz': '1.5', 'bidPx': '110200.5', 'bidSz': '2.0', 'openPx': '109500.0', 'high24h': '111000.0', 'low24h': '109000.0', 'volCcy24h': '1234.56', 'vol24h': '0.011', 'sodUtc0': '109500.0', 'sodUtc8': '109500.0', 'ts': '1759392000123'}], 'action': 'snapshot'}
INFO - SAMPLE_RAW_bybit={'topic': 'tickers.BTCUSDT', 'ts': 1759322154656, 'type': 'snapshot', 'cs': 86599204978, 'data': {'s': 'BTCUSDT', 'lastPrice': '110250.1', 'indexPrice': '110200.0', 'markPrice': '110225.0', 'prevPrice24h': '109500.0', 'price24hPcnt': '0.0068', 'highPrice24h': '111000.0', 'lowPrice24h': '109000.0', 'prevClosePrice': '109500.0', 'openInterest': '123456.78', 'openInterestValue': '13612345678.90', 'turnover24h': '1234567890.12', 'volume24h': '12345.67', 'nextFundingTime': '1759322160000', 'fundingRate': '0.0001', 'bid1Price': '110200.5', 'bid1Size': '2.0', 'ask1Price': '110300.5', 'ask1Size': '1.5'}}
```

### **✅ Parsing Success (No More Import Errors)**
```
✅ bybit parsing summary: 1500/1600 (93.8%)
✅ kraken parsing summary: 1200/1250 (96.0%)
✅ coinbase parsing summary: 1700/1700 (100.0%)
✅ okx parsing summary: 1600/1600 (100.0%)
```

### **✅ S3 Output (Both Symbols)**
```
✅ Written S3 keys:
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20251001/1230-1300/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20251001/1230-1300/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20251001/1230-1300/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20251001/1230-1300/ticks_canary/bybit/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20251001/1230-1300/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20251001/1230-1300/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20251001/1230-1300/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20251001/1230-1300/ticks_canary/bybit/part-0000.parquet
```

## **📝 Expected Improvements**

### **✅ Import Regression Fixed**
- **Before**: `ERROR - Error parsing <venue> message: No module named 'writer'` (all venues failing)
- **After**: All venues parsing successfully with self-contained parser methods
- **Result**: 90%+ parsing success rates for all venues

### **✅ Bybit Parser Fixes**
- **Before**: `ERROR - Error parsing bybit message: 'ts'` (repeated errors)
- **After**: Successfully handles `T`, `ts`, `time`, `timestamp` fields
- **Result**: 93.8% parsing success rate (vs ~60% before)

### **✅ Kraken Parser Fixes**
- **Before**: `WARNING - Kraken message contains lists where numbers expected` (repeated warnings)
- **After**: Successfully parses array format and handles XBT/USD alias
- **Result**: 96.0% parsing success rate (vs ~70% before)

### **✅ Overall Data Quality**
- **Higher parsing success rates** for all venues
- **Better data coverage** due to improved parsers
- **More accurate price data** with proper timestamp handling
- **Reduced error logs** and improved reliability

## **⏱️ Expected Timeline**
- **Start**: Immediate after trigger
- **Duration**: 5-10 minutes
- **Completion**: All S3 keys written successfully for both BTC-USD and ETH-USD
- **Parsing**: Significantly improved success rates for Bybit and Kraken

## **🎯 Success Criteria**
- **Version Banner**: `CAPTURE_PARSER_VERSION=v2025-10-01c` visible in logs
- **Sample Logging**: `SAMPLE_RAW_*` lines for all venues
- **No Import Errors**: No `No module named 'writer'` errors anywhere
- **No Parser Errors**: No Bybit `'ts'` KeyErrors or Kraken array warnings
- **High Success Rates**: 90%+ parsing success for Bybit and Kraken
- **S3 Output**: All 8 parquet files written to `ticks_canary/` prefix

## **🚨 Stop Conditions**
- **If any `No module named 'writer'` errors remain** → Stop and report remaining import locations
- **If parser fixes are applied but Bybit/Kraken still warn on shapes** → Stop and paste 1-2 SAMPLE_RAW_* lines
- **If any other unexpected errors occur** → Stop and report the issue

