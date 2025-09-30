#!/usr/bin/env bash
set -euo pipefail

echo "=== AWS STS Identity Audit ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "=== STS Get Caller Identity ==="
aws sts get-caller-identity \
  --query '{Account:Account,Arn:Arn,UserId:UserId}' \
  --output json

echo
echo "=== AWS Configure List ==="
aws configure list

echo
echo "=== AWS Configure List (with values) ==="
aws configure list --debug 2>&1 | grep -E "(access_key|secret_key|session_token|region)" || echo "No credential details in debug output"
