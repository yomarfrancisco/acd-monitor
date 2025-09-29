#!/bin/bash
set -euo pipefail

BUCKET="acd-monitor-snapshots"
SYMBOLS="${SYMBOLS:-BTC-USD ETH-USD}"
YMD="${YMD:-$(date -u +%Y%m%d)}"

echo "::group::S3 Consistency Check"
# small backoff for S3 eventual consistency
for i in 1 2 3; do
  aws s3 ls "s3://${BUCKET}/snapshots/" && break || sleep 5
done
echo "::endgroup::"

ec=0
for SYM in $SYMBOLS; do
  echo "::group::Discover windows for ${SYM}/${YMD}"
  WINDOWS=$(aws s3 ls "s3://${BUCKET}/snapshots/${SYM}/${YMD}/" --recursive \
    | awk '/OVERLAP.json/ {print $4}' \
    | sed -E 's#.*'"${SYM}"'/'"${YMD}"'/([^/]+)/OVERLAP.json#\1#' \
    | sort -u)
  echo "Found windows:" $WINDOWS || true
  echo "::endgroup::"

  if [ -z "$WINDOWS" ]; then
    echo "::notice ::No windows found for ${SYM}/${YMD}; skipping."
    continue
  fi

  for WIN in $WINDOWS; do
    echo "::group::Verifying ${SYM}/${WIN}"
    
    # Check quality gates first
    echo "Checking coverage requirements..."
    ok=$(aws s3 cp "s3://${BUCKET}/snapshots/${SYM}/${YMD}/${WIN}/meta/coverage.json" - \
      | jq '[to_entries[] | select(.value.coverage_percentage >= 95)] | length >= 3')
    
    if [ "$ok" != "true" ]; then
      echo "::notice ::Skipping (venues_ok=false) ${SYM}/${WIN}"
      echo "::endgroup::"
      continue
    fi
    
    echo "Running verification..."
    if ! python scripts/snapshots/verify_snapshot.py \
        --overlap "s3://${BUCKET}/snapshots/${SYM}/${YMD}/${WIN}/OVERLAP.json" \
        --fail-under-coverage 0.95 --report clocks,coverage ; then
      echo "::warning ::Verification failed for ${SYM}/${WIN}"
      ec=1
    else
      echo "✅ Verified ${SYM}/${WIN}"
    fi
    echo "::endgroup::"
  done
done

if [ $ec -eq 0 ]; then
  echo "✅ All verifications passed"
else
  echo "⚠️ Some verifications failed (non-blocking)"
fi

exit $ec
