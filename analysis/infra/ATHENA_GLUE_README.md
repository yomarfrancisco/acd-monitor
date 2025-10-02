# Zero-Copy Analytics Infrastructure

## Overview
This infrastructure enables server-side analytics processing using AWS Glue and Athena, eliminating the need to download parquet files locally.

## Architecture

```
S3 Snapshots (Source)
    ↓
Glue Catalog (Metadata)
    ↓
Athena Queries (Processing)
    ↓
S3 Derived (Results)
```

## Components

### 1. Glue Database & Table
- **Database**: `acd_snapshots`
- **Table**: `btc_ticks` with partition projection
- **Location**: `s3://acd-monitor-snapshots/snapshots/BTC-USD/`
- **Partitions**: `date`, `window`, `venue`

### 2. Athena Workgroup
- **Name**: `acd-analytics`
- **Output**: `s3://acd-monitor-derived/athena-results/`
- **Encryption**: SSE-S3

### 3. IAM Permissions
- **Role**: `acd-ci-oidc`
- **Policy**: Least-privilege access to Glue/Athena/S3
- **Scope**: Read snapshots, write derived results

## Deployment

### Quick Start
1. **Apply Infrastructure**:
   ```bash
   # Create Glue database and table
   aws glue create-database --database-input file://infra/zero_copy/glue_ddl.sql
   
   # Create Athena workgroup
   aws athena create-work-group --cli-input-json file://infra/zero_copy/athena_workgroup.json
   
   # Update IAM policy
   aws iam put-role-policy --role-name acd-ci-oidc --policy-name ACD-Analytics-ZeroCopy --policy-document file://infra/zero_copy/iam_policy.json
   ```

2. **Test Connectivity**:
   ```sql
   SELECT COUNT(*) FROM acd_snapshots.btc_ticks WHERE date = '20250929';
   ```

3. **Run Analytics Pipeline**:
   ```bash
   python3 scripts/ops/athena_orchestrate.py --date 20250929 --dry-run
   ```

### Manual Deployment
See `infra/zero_copy/RUNBOOK.md` for step-by-step Console instructions.

## Implementation Status

### ✅ Fully Implemented (Athena SQL)
- **OHLC Bars**: 5-second aggregation with open/high/low/close
- **Median Mid**: Cross-venue median price calculation
- **ATR14**: 14-period Average True Range
- **Basic Aggregations**: COUNT, AVG, STDDEV, MIN, MAX
- **Window Functions**: LAG, LEAD, ROW_NUMBER, RANK
- **Session Classification**: UTC hour-based session labels
- **Rolling Statistics**: 30-minute windows with 1800 observations

### ⚠️ Simplified/Stubbed (Athena SQL Limitations)
- **Fractal Swings**: Basic k=2 pattern detection (simplified logic)
- **BOS/CHoCH**: Simplified break-of-structure detection
- **Complex Patterns**: Multi-period pattern recognition limited by SQL
- **Advanced Statistics**: Some econometric tests require Python libraries

### ❌ Not Implemented (Requires Python)
- **Machine Learning**: Clustering, classification algorithms
- **Advanced Econometrics**: GARCH, VAR, cointegration tests
- **Statistical Tests**: Hypothesis testing, p-values
- **Visualization**: Plotting and chart generation

## Usage

### Basic Queries
```sql
-- Count records by venue
SELECT venue, COUNT(*) as records
FROM acd_snapshots.btc_ticks
WHERE date = '20250929'
GROUP BY venue;
```

### Analytics Pipeline
```bash
# Run complete pipeline
python3 scripts/ops/athena_orchestrate.py --date 20250929

# Dry run mode
python3 scripts/ops/athena_orchestrate.py --date 20250929 --dry-run
```

### CI Integration
The zero-copy guard automatically enforces server-side processing:
```yaml
# .github/workflows/ci.yml
zero-copy-guard:
  name: Zero-Copy Analytics Guard
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Enforce Zero-Copy Analytics
      run: python3 scripts/ops/ci_guard_zero_copy.py
```

## File Structure

```
infra/zero_copy/
├── glue_ddl.sql                    # Glue database/table DDL
├── athena_workgroup.json          # Athena workgroup configuration
├── iam_policy.json                # IAM permissions policy
├── RUNBOOK.md                     # Manual deployment guide
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

## Monitoring

### CloudWatch Metrics
- Query execution time
- Data scanned (bytes)
- Query success/failure rates
- Cost per query

### S3 Outputs
- Results location: `s3://acd-monitor-derived/athena-results/`
- Analytics outputs: `s3://acd-monitor-derived/panel_1s/`, `env_flags/`, etc.

## Troubleshooting

### Common Issues
1. **Permission Denied**: Check IAM policy attachment
2. **Table Not Found**: Verify Glue table creation
3. **No Data**: Check partition projection configuration
4. **Query Timeout**: Increase timeout in Athena settings

### Debug Commands
```bash
# Check Glue table
aws glue get-table --database-name acd_snapshots --name btc_ticks

# List Athena workgroups
aws athena list-work-groups

# Check query execution
aws athena get-query-execution --query-execution-id <execution-id>
```

## Cost Optimization

### Query Optimization
- Use partition filters (`WHERE date = '20250929'`)
- Limit data scanned with `LIMIT` clauses
- Use appropriate data types

### Storage Optimization
- Results in Parquet format (compressed)
- Partitioned outputs by date
- Lifecycle policies for old results

## Security

### IAM Permissions
- **Read**: `s3:GetObject` on `acd-monitor-snapshots`
- **Write**: `s3:PutObject` on `acd-monitor-derived`
- **Query**: `athena:StartQueryExecution` on `acd-analytics` workgroup
- **Metadata**: `glue:GetTable` on `btc_ticks`

### Data Protection
- All data encrypted in transit and at rest
- No local storage of sensitive data
- Audit trail in CloudWatch logs

## Support

### Documentation
- `infra/zero_copy/RUNBOOK.md`: Manual deployment guide
- `analysis/infra/DELTA.md`: Migration documentation
- `scripts/analytics_athena/`: SQL analytics scripts

### Contact
- Issues: GitHub Issues
- Infrastructure: AWS Console
- Analytics: Athena Query Editor
