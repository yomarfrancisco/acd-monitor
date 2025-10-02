#!/bin/bash
set -euo pipefail

BUCKET=acd-monitor-snapshots
PREFIX=snapshots/BTC-USD

echo "=== S3 Access Audit ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Bucket: $BUCKET"
echo "Prefix: $PREFIX"
echo

echo "=== List Objects (first 5) ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" --max-keys 5 \
  --query '{KeyCount:KeyCount,Sample:Contents[].Key}' \
  --output json

echo
echo "=== Find Parquet Files ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" \
  --query 'Contents[?ends_with(Key, `part-0000.parquet`)].Key' --output text | head -n 1 | \
while read -r KEY; do
  if [ -n "$KEY" ]; then
    echo "HEAD $KEY"
    aws s3api head-object --bucket "$BUCKET" --key "$KEY" \
      --query '{Size:ContentLength,ETag:ETag,SSE:ServerSideEncryption,KMSKeyId:SSEKMSKeyId}' \
      --output json
  else
    echo "No parquet files found"
  fi
done

echo
echo "=== Bucket Location ==="
aws s3api get-bucket-location --bucket "$BUCKET" --output json
