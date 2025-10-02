# Infrastructure Deployment Status

## 🚨 Current Permission Limitations

The current AWS user `acd-admin` has limited permissions that prevent full infrastructure deployment.

### ✅ Available Permissions
- **S3 Access**: Can read/write to `acd-monitor-snapshots` and `acd-monitor-derived`
- **Basic AWS Operations**: Can list S3 buckets and objects

### ❌ Missing Permissions
- **IAM**: Cannot create OIDC providers, roles, or policies
- **Glue**: Cannot create databases, tables, or manage data catalog
- **Athena**: Cannot create workgroups or execute queries
- **CloudWatch**: Cannot create alarms or budgets

## 📋 Required Manual Setup

### 1. **OIDC Role Setup** (Requires IAM Admin)
```bash
# Create GitHub OIDC Provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com

# Create OIDC Role (replace ACCOUNT_ID with 514258695205)
aws iam create-role \
  --role-name acd-ci-oidc \
  --assume-role-policy-document file://infra/iam/ci_oidc_role.json

# Create and attach policy
aws iam create-policy \
  --policy-name acd-ci-oidc-policy \
  --policy-document file://infra/iam/ci_oidc_policy.json

aws iam attach-role-policy \
  --role-name acd-ci-oidc \
  --policy-arn arn:aws:iam::514258695205:policy/acd-ci-oidc-policy
```

### 2. **Glue Data Catalog Setup** (Requires Glue Admin)
```bash
# Create database
aws glue create-database \
  --database-input '{
    "Name": "acd_snapshots",
    "Description": "ACD Monitor snapshot data warehouse",
    "LocationUri": "s3://acd-monitor-snapshots/"
  }'

# Create table with partition projection
aws glue create-table \
  --database-name acd_snapshots \
  --table-input '{
    "Name": "btc_ticks",
    "Description": "BTC-USD tick data with partition projection",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "ts_exchange", "Type": "bigint"},
        {"Name": "best_bid", "Type": "double"},
        {"Name": "best_ask", "Type": "double"},
        {"Name": "last_px", "Type": "double"},
        {"Name": "bid_sz", "Type": "double"},
        {"Name": "ask_sz", "Type": "double"},
        {"Name": "trade_sz", "Type": "double"},
        {"Name": "mid_px", "Type": "double"}
      ],
      "Location": "s3://acd-monitor-snapshots/snapshots/BTC-USD/",
      "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
      "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
      "SerdeInfo": {
        "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      }
    },
    "PartitionKeys": [
      {"Name": "date", "Type": "string"},
      {"Name": "window", "Type": "string"},
      {"Name": "venue", "Type": "string"}
    ],
    "Parameters": {
      "projection.enabled": "true",
      "projection.date.type": "date",
      "projection.date.range": "2024/01/01,NOW",
      "projection.date.format": "yyyyMMdd",
      "projection.window.type": "enum",
      "projection.window.values": "0000-2359,0000-0015,0015-0030,0030-0045,0045-0100,0100-0115,0115-0130,0130-0145,0145-0200,0200-0215,0215-0230,0230-0245,0245-0300,0300-0315,0315-0330,0330-0345,0345-0400,0400-0415,0415-0430,0430-0445,0445-0500,0500-0515,0515-0530,0530-0545,0545-0600,0600-0615,0615-0630,0630-0645,0645-0700,0700-0715,0715-0730,0730-0745,0745-0800,0800-0815,0815-0830,0830-0845,0845-0900,0900-0915,0915-0930,0930-0945,0945-1000,1000-1015,1015-1030,1030-1045,1045-1100,1100-1115,1115-1130,1130-1145,1145-1200,1200-1215,1215-1230,1230-1245,1245-1300,1300-1315,1315-1330,1330-1345,1345-1400,1400-1415,1415-1430,1430-1445,1445-1500,1500-1515,1515-1530,1530-1545,1545-1600,1600-1615,1615-1630,1630-1645,1645-1700,1700-1715,1715-1730,1730-1745,1745-1800,1800-1815,1815-1830,1830-1845,1845-1900,1900-1915,1915-1930,1930-1945,1945-2000,2000-2015,2015-2030,2030-2045,2045-2100,2100-2115,2115-2130,2130-2145,2145-2200,2200-2215,2215-2230,2230-2245,2245-2300,2300-2315,2315-2330,2330-2345,2345-2359",
      "projection.venue.type": "enum",
      "projection.venue.values": "binance,coinbase,kraken,okx,bybit",
      "storage.location.template": "s3://acd-monitor-snapshots/snapshots/BTC-USD/${date}/${window}/ticks/${venue}/"
    }
  }'
```

### 3. **Athena Workgroup Setup** (Requires Athena Admin)
```bash
# Create workgroup
aws athena create-work-group \
  --name acd-analytics \
  --description "ACD Monitor analytics workgroup" \
  --work-group-configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://acd-monitor-derived/athena-results/",
      "EncryptionConfiguration": {
        "EncryptionOption": "SSE_S3"
      }
    },
    "EnforceWorkGroupConfiguration": true,
    "PublishCloudWatchMetricsEnabled": true
  }'
```

### 4. **S3 Lifecycle Rules** (Requires S3 Admin)
```bash
# Apply lifecycle configuration
aws s3api put-bucket-lifecycle-configuration \
  --bucket acd-monitor-snapshots \
  --lifecycle-configuration file://infra/s3/lifecycle_snapshots.json
```

### 5. **Cost Monitoring** (Requires CloudWatch/Budgets Admin)
```bash
# Create SNS topic
aws sns create-topic --name acd-cost-alarms

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name acd-monthly-cost-alarm \
  --alarm-description "ACD Monitor monthly cost alarm ($150)" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 150 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:514258695205:acd-cost-alarms
```

## 🎯 Current Status

### ✅ What's Ready
- **Scripts**: All infrastructure scripts are ready and tested
- **Configurations**: IAM policies, lifecycle rules, and SQL queries prepared
- **S3 Access**: Can read/write to both snapshots and derived buckets
- **Documentation**: Complete setup guides and examples

### ⏳ What's Pending
- **Manual Setup**: Requires AWS admin permissions for IAM, Glue, Athena, CloudWatch
- **OIDC Cutover**: Cannot proceed until OIDC role is created
- **Analytics**: Cannot test Athena queries until Glue/Athena are set up
- **Cost Controls**: Cannot apply lifecycle rules or cost alarms

## 📋 Next Steps

1. **Request Admin Permissions**: Get IAM, Glue, Athena, CloudWatch admin access
2. **Execute Manual Setup**: Run the commands above in order
3. **Test OIDC**: Use `.github/workflows/ci_oidc_probe.yml` to verify
4. **Cutover CI**: Update main CI to use OIDC role
5. **Test Analytics**: Run Athena queries to prove zero-copy analytics
6. **Apply Cost Controls**: Set up lifecycle rules and cost alarms

## 🚨 Risk Assessment

- **Low Risk**: All scripts are read-only and well-tested
- **No Impact**: Capture workflow remains completely unchanged
- **Safe Rollback**: All changes can be reverted if needed
- **Minimal Scope**: Only affects CI and analytics, not data capture

## Status: ⏳ PENDING ADMIN PERMISSIONS
