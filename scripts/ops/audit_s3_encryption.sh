#!/bin/bash
set -euo pipefail

BUCKET=acd-monitor-snapshots

echo "=== S3 Bucket Encryption Audit ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Bucket: $BUCKET"
echo

echo "=== Bucket Policy ==="
aws s3api get-bucket-policy --bucket "$BUCKET" --query Policy --output text 2>/dev/null || echo "No explicit bucket policy"

echo
echo "=== Bucket Encryption ==="
aws s3api get-bucket-encryption --bucket "$BUCKET" \
  --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault' \
  --output json 2>/dev/null || echo "No default encryption"

echo
echo "=== Bucket Versioning ==="
aws s3api get-bucket-versioning --bucket "$BUCKET" --output json

echo
echo "=== Bucket Public Access Block ==="
aws s3api get-public-access-block --bucket "$BUCKET" --output json
