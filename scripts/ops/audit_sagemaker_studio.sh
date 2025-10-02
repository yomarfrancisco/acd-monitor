#!/bin/bash
set -euo pipefail

echo "=== SageMaker Studio Audit ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "=== List SageMaker Domains ==="
aws sagemaker list-domains --query "Domains[].{Id:DomainId,Name:DomainName}" --output json 2>/dev/null || echo "No SageMaker domains found or no access"

echo
echo "=== Check if we're in SageMaker environment ==="
echo "SAGEMAKER_PROGRAM: ${SAGEMAKER_PROGRAM:-not_set}"
echo "SAGEMAKER_SUBMIT_DIRECTORY: ${SAGEMAKER_SUBMIT_DIRECTORY:-not_set}"
echo "SAGEMAKER_CONTAINER_LOG_LEVEL: ${SAGEMAKER_CONTAINER_LOG_LEVEL:-not_set}"

echo
echo "=== Current execution context ==="
echo "AWS_REGION: ${AWS_REGION:-not_set}"
echo "AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-not_set}"
