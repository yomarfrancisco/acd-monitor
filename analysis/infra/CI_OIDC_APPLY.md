# CI OIDC Application Status

## 🚨 Manual Steps Required

The automated OIDC role creation failed due to insufficient IAM permissions. The current user `acd-admin` cannot create OIDC providers.

### Required Manual Steps

1. **Create GitHub OIDC Provider** (requires IAM admin):
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
     --client-id-list sts.amazonaws.com
   ```

2. **Create OIDC Role** (requires IAM admin):
   ```bash
   # Use the account ID: 514258695205
   # Replace ACCOUNT_ID in infra/iam/ci_oidc_role.json with 514258695205
   aws iam create-role \
     --role-name acd-ci-oidc \
     --assume-role-policy-document file://infra/iam/ci_oidc_role.json
   ```

3. **Create and Attach Policy**:
   ```bash
   aws iam create-policy \
     --policy-name acd-ci-oidc-policy \
     --policy-document file://infra/iam/ci_oidc_policy.json
   
   aws iam attach-role-policy \
     --role-name acd-ci-oidc \
     --policy-arn arn:aws:iam::514258695205:policy/acd-ci-oidc-policy
   ```

### Expected Role ARN
```
arn:aws:iam::514258695205:role/acd-ci-oidc
```

### Policy Summary
- **S3 Read**: `acd-monitor-snapshots/*` (snapshots only)
- **S3 Write**: `acd-monitor-derived/*` (derived data only)
- **Athena**: Query execution on `acd-analytics` workgroup
- **Glue**: Read database and table metadata
- **STS**: Get caller identity

### Next Steps
1. Complete manual OIDC setup
2. Test with `.github/workflows/ci_oidc_probe.yml`
3. Cutover main CI to OIDC
4. Retire static AWS keys

## Status: ⏳ PENDING MANUAL SETUP
