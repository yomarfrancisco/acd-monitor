# Zero-Copy Analytics Infrastructure Runbook

## Overview
This runbook provides step-by-step instructions for deploying the zero-copy analytics infrastructure using AWS Glue and Athena. All processing happens server-side with results written to `s3://acd-monitor-derived/`.

## Prerequisites
- AWS Console access with Glue/Athena permissions
- S3 buckets: `acd-monitor-snapshots` (source) and `acd-monitor-derived` (output)

## Step 1: Create Glue Database and Table

### 1.1 Create Database
1. Open AWS Glue Console → Data Catalog → Databases
2. Click "Add database"
3. Name: `acd_snapshots`
4. Description: `ACD Monitor snapshot data warehouse`
5. Location: `s3://acd-monitor-snapshots/`
6. Click "Create database"

### 1.2 Create External Table
1. Go to Data Catalog → Tables → "Add table"
2. Database: `acd_snapshots`
3. Table name: `btc_ticks`
4. Copy and paste the DDL from `glue_ddl.sql`
5. Click "Create table"

**Verification**: Run `DESCRIBE acd_snapshots.btc_ticks;` in Athena

## Step 2: Create Athena Workgroup

### 2.1 Create Workgroup
1. Open Athena Console → Workgroups
2. Click "Create workgroup"
3. Name: `acd-analytics`
4. Description: `ACD Monitor analytics workgroup`
5. Use configuration from `athena_workgroup.json`
6. Output location: `s3://acd-monitor-derived/athena-results/`
7. Click "Create workgroup"

### 2.2 Switch to New Workgroup
1. In Athena Query Editor, click workgroup dropdown
2. Select `acd-analytics`
3. Confirm output location shows `s3://acd-monitor-derived/athena-results/`

## Step 3: Update IAM Permissions

### 3.1 Attach Policy to CI Role
1. Open IAM Console → Roles → `acd-ci-oidc`
2. Click "Add permissions" → "Attach policies"
3. Create new policy from `iam_policy.json`
4. Name: `ACD-Analytics-ZeroCopy`
5. Attach to role

## Step 4: Test Infrastructure

### 4.1 Basic Connectivity Test
```sql
-- Run in Athena (acd-analytics workgroup)
SELECT COUNT(*) as total_records 
FROM acd_snapshots.btc_ticks 
WHERE date = '20250929';
```

**Expected**: Returns record count for September 29, 2025

### 4.2 Venue Coverage Test
```sql
-- Run venue coverage query
-- File: sql/venue_coverage.sql
```

**Expected**: Shows data availability per venue with quality metrics

### 4.3 OHLC Generation Test
```sql
-- Run OHLC 5s generation
-- File: sql/mid_ohlc_5s.sql
```

**Expected**: Creates parquet files in `s3://acd-monitor-derived/ohlc_5s/date=20250929/`

## Step 5: Verification Queries

### 5.1 Check Output Location
```bash
aws s3 ls s3://acd-monitor-derived/athena-results/ --recursive
```

### 5.2 Verify OHLC Output
```bash
aws s3 ls s3://acd-monitor-derived/ohlc_5s/date=20250929/ --recursive
```

## Rollback Instructions

### If Issues Occur:
1. **Delete Athena Workgroup**: Athena Console → Workgroups → `acd-analytics` → Delete
2. **Delete Glue Table**: Glue Console → Tables → `btc_ticks` → Delete
3. **Delete Glue Database**: Glue Console → Databases → `acd_snapshots` → Delete
4. **Clean S3**: Remove any test outputs from `acd-monitor-derived/`

### ⚠️ NEVER DELETE:
- `s3://acd-monitor-snapshots/` (source data)
- Any files in the snapshots bucket

## Expected Results

### After Successful Deployment:
- Glue database `acd_snapshots` exists
- Table `btc_ticks` with partition projection active
- Athena workgroup `acd-analytics` configured
- Test queries return data without errors
- OHLC files created in derived bucket

### Performance Expectations:
- Initial table scan: ~30-60 seconds
- OHLC generation: ~2-5 minutes per day
- Query costs: ~$0.01-0.05 per query (based on data scanned)

## Troubleshooting

### Common Issues:
1. **Permission Denied**: Check IAM policy attachment
2. **Table Not Found**: Verify Glue table creation
3. **No Data**: Check partition projection configuration
4. **Query Timeout**: Increase timeout in Athena settings

### Support:
- Check CloudWatch logs for Athena queries
- Verify S3 bucket permissions
- Confirm Glue table schema matches source data


