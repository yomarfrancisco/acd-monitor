# Glue Table Validation Instructions

## Overview
This document provides step-by-step instructions for validating the Glue table setup and testing the zero-copy analytics path.

## Prerequisites
- AWS Console access with Athena and Glue permissions
- S3 buckets: `acd-monitor-snapshots` (source) and `acd-monitor-derived` (output)

## Step 1: Manual Validation (AWS Console)

### 1.1 Check Glue Table
1. Open AWS Glue Console → Data Catalog → Databases
2. Click on `acd_snapshots` database
3. Click on `btc_ticks` table
4. Verify:
   - **Columns**: 32 data columns + 3 partition keys = 35 total
   - **Location**: `s3://acd-monitor-snapshots/snapshots/BTC-USD/`
   - **Partition Keys**: `date`, `window`, `venue`

### 1.2 Enable Partition Projection
1. Go to Athena Console → Query Editor
2. Select workgroup: `primary` (or `acd-analytics` if exists)
3. Run the following SQL:

```sql
ALTER TABLE acd_snapshots.btc_ticks SET TBLPROPERTIES (
  'projection.enabled'='true',
  'projection.date.type'='date',
  'projection.date.format'='yyyyMMdd',
  'projection.date.range'='20240901,20251231',
  'projection.window.type'='enum',
  'projection.window.values'='0000-0030,0030-0100,0100-0130,0130-0200,0200-0230,0230-0300,0300-0330,0330-0400,0400-0430,0430-0500,0500-0530,0530-0600,0600-0630,0630-0700,0700-0730,0730-0800,0800-0830,0830-0900,0900-0930,0930-1000,1000-1030,1030-1100,1100-1130,1130-1200,1200-1230,1230-1300,1300-1330,1330-1400,1400-1430,1430-1500,1500-1530,1530-1600,1600-1630,1630-1700,1700-1730,1730-1800,1800-1830,1830-1900,1900-1930,1930-2000,2000-2030,2030-2100,2100-2130,2130-2200,2200-2230,2230-2300,2300-2330,2330-0000',
  'projection.venue.type'='enum',
  'projection.venue.values'='binance,coinbase,kraken,okx,bybit',
  'storage.location.template'='s3://acd-monitor-snapshots/snapshots/BTC-USD/${date}/${window}/ticks/${venue}.parquet'
);
```

## Step 2: Smoke Tests (Athena Console)

### 2.1 Test A: Pointed Count
```sql
SELECT count(*) AS n
FROM acd_snapshots.btc_ticks
WHERE date='20250929' AND window='0200-0230' AND venue='binance';
```
**Expected**: Returns n > 0

### 2.2 Test B: Schema Preview
```sql
SELECT ts_exchange, best_bid, best_ask, last_px, mid_px
FROM acd_snapshots.btc_ticks
WHERE date='20250929' AND window='0200-0230' AND venue='binance'
ORDER BY ts_exchange
LIMIT 5;
```
**Expected**: Returns 5 rows with sensible timestamps and prices

### 2.3 Test C: Multi-Venue Coverage
```sql
SELECT venue, COUNT(1) AS rows
FROM acd_snapshots.btc_ticks
WHERE date='20250929'
GROUP BY venue
ORDER BY venue;
```
**Expected**: Returns rows for ≥3 venues

## Step 3: Configure Athena Output

### 3.1 Set Workgroup Output Location
1. Go to Athena Console → Workgroups
2. Select workgroup: `primary` (or create `acd-analytics`)
3. Click "Edit workgroup"
4. Set output location: `s3://acd-monitor-derived/athena-results/`
5. Save changes

## Step 4: Automated Validation (Optional)

### 4.1 Run Validation Script
```bash
# Requires proper AWS credentials with Athena/Glue permissions
python3 scripts/ops/validate_glue_table.py
```

This script will:
- Check Glue table exists and has correct schema
- Enable partition projection
- Run all smoke tests
- Report validation results

## Step 5: Proceed to Analytics

### 5.1 Wave-1 Analysis
```bash
# Run 1-second aligned panel assembly
python3 scripts/ops/athena_orchestrate.py --date 20250929 --dry-run
```

### 5.2 Check Results
```bash
# Verify outputs in S3
aws s3 ls s3://acd-monitor-derived/athena-results/ --recursive
aws s3 ls s3://acd-monitor-derived/panel_1s/ --recursive
```

## Success Criteria

### All Tests Must Pass:
- ✅ **Test A**: Returns n > 0
- ✅ **Test B**: Returns 5 rows with sensible timestamps and prices  
- ✅ **Test C**: Returns rows for ≥3 venues

### If Any Test Fails:
1. Check Glue table configuration
2. Verify partition projection settings
3. Ensure S3 data is accessible
4. Check IAM permissions
5. Re-run validation

## Troubleshooting

### Common Issues:
1. **Permission Denied**: Check IAM permissions for Athena/Glue
2. **Table Not Found**: Verify Glue table creation
3. **No Data**: Check partition projection configuration
4. **Query Timeout**: Increase timeout in Athena settings

### Debug Commands:
```bash
# Check Glue table
aws glue get-table --database-name acd_snapshots --name btc_ticks

# List Athena workgroups
aws athena list-work-groups

# Check S3 data
aws s3 ls s3://acd-monitor-snapshots/snapshots/BTC-USD/20250929/ --recursive
```

## Next Steps

Once validation passes:
1. **Wave-1**: Run panel assembly via Athena
2. **Wave-2**: Run environment flags and market structure
3. **Wave-3**: Run advanced features and marginals
4. **Analysis**: Proceed with coordination detection

All processing happens server-side via Athena queries - no local downloads.

