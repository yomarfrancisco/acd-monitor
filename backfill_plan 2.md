# 🚀 BACKFILL PLAN - BTC-USD WRITER FIX

## **📋 BACKFILL STEPS**

### **Step 1: Disable Canary Mode**
```bash
# Update GitHub Actions workflow environment
BTC_CANARY_ENABLED=false
```

### **Step 2: Re-emit Corrected Data**
```bash
# Trigger GitHub Actions workflow for affected windows
# Target windows: 20250928/0200-0230 (and any other affected windows)
# This will write to the normal ticks/ prefix instead of ticks_canary/
```

### **Step 3: Rebuild v5 Partitions**
```sql
-- Rebuild enriched_v5 table for affected partitions
DROP TABLE IF EXISTS acd_derived.btc_ticks_enriched_v5_repair;

CREATE TABLE acd_derived.btc_ticks_enriched_v5_repair
WITH (
  format='PARQUET',
  partitioned_by = ARRAY['vdate_ymd','vwindow','venue'],
  external_location='s3://acd-monitor-derived/enriched_v5_repair/'
) AS
SELECT
  ts_verified,
  best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
  (best_bid + best_ask)/2.0 AS mid_px,
  (best_ask - best_bid) / NULLIF((best_ask + best_bid)/2.0, 0) * 10000.0 AS spread_bps,
  _path,
  CASE
    WHEN ts_verified >= TIMESTAMP '2025-01-01 00:00:00 UTC' AND last_px < 80000 THEN 0
    ELSE 1
  END AS sanity_price_ok,
  vdate_ymd, vwindow, venue
FROM acd_snapshots.btc_ticks_files_v2_view_verified
WHERE date_format(ts_verified,'%Y%m%d') = '20250928'
  AND concat(
    date_format(ts_verified,'%H%i'),'-',
    date_format(ts_verified + interval '30' minute,'%H%i')
  ) = '0200-0230';
```

### **Step 4: Final Validation**
```sql
-- Re-run the same 5 gates on production data
-- Gate A: Median check
SELECT approx_percentile(last_px, 0.5) AS median_price
FROM acd_derived.btc_ticks_enriched_v5
WHERE vdate_ymd='20250928' AND vwindow='0200-0230';

-- Gate B: Range check
SELECT MIN(last_px) AS min_price, MAX(last_px) AS max_price
FROM acd_derived.btc_ticks_enriched_v5
WHERE vdate_ymd='20250928' AND vwindow='0200-0230';

-- Gate C: Coherence check
SELECT 
  COUNT(*) AS total,
  SUM(CASE WHEN best_bid <= last_px AND last_px <= best_ask THEN 1 ELSE 0 END) AS coherent
FROM acd_derived.btc_ticks_enriched_v5
WHERE vdate_ymd='20250928' AND vwindow='0200-0230';

-- Gate D: Sanity check
SELECT COUNT(*) AS sanity_ok
FROM acd_derived.btc_ticks_enriched_v5
WHERE vdate_ymd='20250928' AND vwindow='0200-0230' AND sanity_price_ok=1;

-- Gate E: OHLC check
SELECT *
FROM acd_derived.btc_ohlc_1m_v5
WHERE bucket_1m BETWEEN TIMESTAMP '2025-09-28 02:00:00 UTC' AND TIMESTAMP '2025-09-28 02:30:00 UTC'
ORDER BY bucket_1m DESC, venue
LIMIT 6;
```

## **🎯 EXPECTED RESULTS**

### **✅ Production Data Validation**
- **Median price**: ~110,000 USD (not ~50,000)
- **Price range**: 105,000 - 115,000 USD
- **Bid/ask coherence**: ≥90%
- **Sanity gates**: All pass
- **OHLC closes**: ~$110k

### **✅ Incident Resolution**
- **Root cause**: Fixed in writer code
- **Data quality**: Restored to expected levels
- **Monitoring**: v5 sanity gates prevent recurrence

## **📝 ROLLBACK PLAN**

If backfill validation fails:
1. **Revert to canary mode**: Set `BTC_CANARY_ENABLED=true`
2. **Quarantine bad data**: Move to quarantine prefix
3. **Investigate further**: Check writer logs and upstream sources
4. **Re-attempt**: After fixing any remaining issues

## **🔧 MONITORING**

### **Permanent Guards**
- **v5 sanity gates**: Always enabled
- **Freshness checks**: MAX(ts_verified) > now() - interval '5' minute
- **Price sanity**: last_px > 80,000 for 2025+ dates

### **Dashboard Queries**
```sql
-- All "latest" queries should include:
WHERE sanity_price_ok = 1 
  AND ts_verified > now() - interval '5' minute
  AND last_px > 80000  -- Additional sanity check
```
