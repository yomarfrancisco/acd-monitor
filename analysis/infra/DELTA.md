# Zero-Copy Analytics Migration Delta

## Overview
This document maps the transition from local parquet processing to zero-copy Athena-based analytics.

## What Previously Downloaded → New Athena Step

### Wave-1: Panel Assembly
**Before (Local)**:
```python
# Downloaded parquet files locally
s3.download_file(bucket, key, local_path)
df = pd.read_parquet(local_path)
# Local processing...
```

**After (Athena)**:
```sql
-- scripts/analytics_athena/panel_1s.sql
CREATE TABLE acd_derived.panel_1s_20250929 AS
WITH venue_data AS (
    SELECT venue, ts_exchange, (best_bid + best_ask) / 2 as mid_px
    FROM acd_snapshots.btc_ticks
    WHERE date = '20250929'
)
-- Server-side resampling and alignment
```

### Wave-2: Environment Flags & Market Structure
**Before (Local)**:
```python
# Local computation of session labels, 2σ flags, VWAP deviations
df['session_label'] = df['timestamp'].apply(get_session)
df['is_return_2sigma'] = compute_2sigma_flags(df)
```

**After (Athena)**:
```sql
-- scripts/analytics_athena/env_flags.sql
CREATE TABLE acd_derived.env_flags_20250929 AS
WITH session_labels AS (
    SELECT *,
        CASE 
            WHEN EXTRACT(hour FROM timestamp) BETWEEN 0 AND 7 THEN 'Asia'
            -- Server-side session classification
        END as session_label
    FROM acd_derived.panel_1s_20250929
)
-- Server-side environment flag computation
```

### Wave-3: Advanced Features
**Before (Local)**:
```python
# Local computation of ICP design matrix, VMM moments, copula marginals
features = compute_icp_features(df)
moments = compute_vmm_moments(df)
marginals = compute_copula_marginals(df)
```

**After (Athena)**:
```sql
-- scripts/analytics_athena/wave3_features.sql
CREATE TABLE acd_derived.wave3_features_20250929 AS
WITH cross_venue_metrics AS (
    SELECT timestamp, AVG(mid_px) as mid_eq, STDDEV(mid_px) as dispersion
    FROM acd_derived.panel_1s_20250929
    GROUP BY timestamp
)
-- Server-side feature computation
```

## Infrastructure Changes

### New Components
1. **Glue Database**: `acd_snapshots` with partition projection
2. **Athena Workgroup**: `acd-analytics` with result location
3. **IAM Policy**: Least-privilege access for CI role
4. **SQL Scripts**: Server-side analytics in `scripts/analytics_athena/`
5. **Orchestrator**: `athena_orchestrate.py` for pipeline management

### Removed Components
1. **Local Downloads**: No more `boto3.get_object()` for parquet files
2. **Local Processing**: No more pandas DataFrames in CI
3. **Memory Constraints**: No more OOM issues with large datasets

## File Structure Changes

### Added
```
infra/zero_copy/
├── glue_ddl.sql                    # Glue database/table DDL
├── athena_workgroup.json          # Athena workgroup config
├── iam_policy.json                # Least-privilege IAM policy
├── RUNBOOK.md                     # Deployment instructions
└── sql/
    ├── counts_by_date.sql         # Basic aggregation test
    ├── venue_coverage.sql         # Data quality analysis
    └── mid_ohlc_5s.sql            # OHLC generation test

scripts/analytics_athena/
├── panel_1s.sql                   # Wave-1: 1-second aligned panel
├── env_flags.sql                  # Wave-2: Environment flags
├── market_structure_5s.sql        # Wave-2: Market structure
└── wave3_features.sql             # Wave-3: Advanced features

scripts/ops/
├── athena_orchestrate.py          # Pipeline orchestrator
└── ci_guard_zero_copy.py         # CI enforcement guard
```

### Modified
```
.github/workflows/ci.yml           # Added zero-copy guard
```

## Benefits

### Performance
- **No Memory Limits**: Server-side processing scales automatically
- **Faster Queries**: Athena optimizes query execution
- **Cost Effective**: Pay only for data scanned

### Security
- **Least Privilege**: CI role has minimal required permissions
- **No Local State**: No sensitive data in GitHub Actions
- **Audit Trail**: All queries logged in CloudWatch

### Maintainability
- **SQL-Based**: Easier to understand and modify
- **Version Controlled**: All analytics logic in Git
- **Reproducible**: Consistent results across environments

## Migration Checklist

### Infrastructure Deployment
- [ ] Create Glue database `acd_snapshots`
- [ ] Create external table `btc_ticks` with partition projection
- [ ] Create Athena workgroup `acd-analytics`
- [ ] Update IAM policy for CI role
- [ ] Test basic connectivity

### Analytics Pipeline
- [ ] Deploy Wave-1 SQL (panel assembly)
- [ ] Deploy Wave-2 SQL (environment flags, market structure)
- [ ] Deploy Wave-3 SQL (advanced features)
- [ ] Test complete pipeline with orchestrator

### CI Integration
- [ ] Enable zero-copy guard in CI
- [ ] Remove any remaining download patterns
- [ ] Update documentation

## Rollback Plan

If issues occur:
1. **Disable CI Guard**: Comment out zero-copy-guard job
2. **Revert to Local**: Use previous local processing scripts
3. **Clean Infrastructure**: Delete Glue/Athena resources
4. **Restore Secrets**: Re-enable AWS key-based access

## Success Criteria

### Technical
- [ ] All analytics run via Athena queries
- [ ] No direct S3 parquet downloads in CI
- [ ] Results written to `s3://acd-monitor-derived/`
- [ ] Pipeline completes within timeout limits

### Operational
- [ ] CI passes with zero-copy guard enabled
- [ ] Infrastructure costs within budget
- [ ] Query performance acceptable
- [ ] Documentation complete and accurate


