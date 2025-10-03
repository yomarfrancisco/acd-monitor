# 🚀 Canary Run Guide - BTC & ETH (Fixed Parsers)

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

## **📊 Expected Log Output (Fixed Parsers)**

### **✅ Version Banner (Proof of New Code)**
```
CAPTURE_PARSER_VERSION=v2025-10-01b
```

### **✅ Sample Raw Data (One per Venue)**
```
SAMPLE_RAW_binance={"e":"trade","E":1759392000123,"s":"BTCUSDT","t":123456789,"p":"110250.1","q":"0.002","b":123456788,"a":123456790,"T":1759392000123,"m":true,"M":true}
SAMPLE_RAW_coinbase={"type":"ticker","sequence":123456789,"product_id":"BTC-USD","price":"110250.1","open_24h":"109500.0","volume_24h":"1234.56","low_24h":"109000.0","high_24h":"111000.0","volume_30d":"45678.90","best_bid":"110200.5","best_ask":"110300.5","side":"buy","time":"2025-10-01T11:59:22.123Z","trade_id":123456789,"last_size":"0.002"}
SAMPLE_RAW_kraken=[119930881, [["116774.10000", "0.00085635", "1759319962.844759", "b", "", ""]], "trade", "XBT/USD"]
SAMPLE_RAW_okx={"arg":{"channel":"tickers","instId":"BTC-USD"},"data":[{"instType":"SPOT","instId":"BTC-USD","last":"110250.1","lastSz":"0.002","askPx":"110300.5","askSz":"1.5","bidPx":"110200.5","bidSz":"2.0","openPx":"109500.0","high24h":"111000.0","low24h":"109000.0","volCcy24h":"1234.56","vol24h":"0.011","sodUtc0":"109500.0","sodUtc8":"109500.0","ts":"1759392000123"}],"action":"snapshot"}
SAMPLE_RAW_bybit={"topic":"publicTrade.btcusdt","data":[{"T":1759392000123,"p":"110250.1","v":"0.002","s":"BTCUSDT","i":"123456789","S":"Buy","BT":false}]}
```

### **✅ Parsing Summary (New)**
```
bybit parsing summary: 1500/1600 (93.8%)
kraken parsing summary: 1200/1250 (96.0%)
binance parsing summary: 1800/1800 (100.0%)
coinbase parsing summary: 1700/1700 (100.0%)
okx parsing summary: 1600/1600 (100.0%)
```

### **✅ S3 Output (Both Symbols)**
```
✅ Written S3 keys:
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/binance/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/bybit/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20250928/0200-0230/ticks_canary/binance/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20250928/0200-0230/ticks_canary/coinbase/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20250928/0200-0230/ticks_canary/kraken/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20250928/0200-0230/ticks_canary/okx/part-0000.parquet
  - s3://acd-monitor-snapshots/snapshots/ETH-USD/20250928/0200-0230/ticks_canary/bybit/part-0000.parquet
```

## **📝 Expected Improvements**

### **✅ Bybit Parser Fixes**
- **Before**: `ERROR - Error parsing bybit message: 'ts'` (repeated errors)
- **After**: Successfully handles both `T` and `ts` timestamp fields
- **Result**: 93.8% parsing success rate (vs ~60% before)

### **✅ Kraken Parser Fixes**
- **Before**: `WARNING - Kraken message contains lists where numbers expected` (repeated warnings)
- **After**: Successfully parses array format and handles XBT/USD alias
- **Result**: 96.0% parsing success rate (vs ~70% before)

## **⏱️ Expected Timeline**
- **Start**: Immediate after trigger
- **Duration**: 5-10 minutes
- **Completion**: All S3 keys written successfully for both BTC-USD and ETH-USD
- **Parsing**: Significantly improved success rates for Bybit and Kraken
