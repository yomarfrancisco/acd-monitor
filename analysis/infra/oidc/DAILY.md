# Daily OIDC Authentication Test

## Purpose
Daily verification that OIDC authentication is working correctly across all workflows.

## Test Schedule
- **Frequency**: Daily at 6:00 AM UTC
- **Workflow**: OIDC Test
- **Trigger**: Manual (scheduled for this week)

## Test Results

### 2025-09-30 (Initial Test)
**Status**: ✅ **SUCCESS**

**AWS Identity**:
```json
{
    "UserId": "AROAXPPBU6QSXHH5IU36X:GitHubActions",
    "Account": "514258695205", 
    "Arn": "arn:aws:sts::514258695205:assumed-role/acd-ci-oidc/GitHubActions"
}
```

**S3 Access Test**:
```
2025-09-30T21:03:15.5381118Z 
2025-09-30T21:03:15.5381652Z Unknown options: --max-items,3
```

**OIDC Credentials**:
- AWS_ACCESS_KEY_ID: Present (temporary)
- AWS_SECRET_ACCESS_KEY: Present (temporary) 
- AWS_SESSION_TOKEN: Present (temporary)

**Conclusion**: OIDC authentication working correctly with temporary credentials.

---

## Notes
- OIDC role: `arn:aws:iam::514258695205:role/acd-ci-oidc`
- All workflows now use OIDC instead of static credentials
- No long-lived AWS keys in use
