#!/usr/bin/env python3
import json, os, re, sys
import boto3

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
SYMBOLS = os.getenv("SYMBOLS", "BTC-USD,ETH-USD").split(",")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

s3 = boto3.client("s3")


def list_keys(prefix):
    """Yield all keys under prefix (handles pagination)."""
    token = None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for o in resp.get("Contents", []):
            yield o["Key"]
        token = resp.get("NextContinuationToken")
        if not token:
            break


def windows_for_symbol(sym):
    # match both 2025-09-29/HHMM-HHMM and 20250929/HHMM-HHMM
    pat = re.compile(
        rf"{re.escape(PREFIX)}/{re.escape(sym)}/(\d{{4}}-\d{{2}}-\d{{2}}|\d{{8}})/\d{{4}}-\d{{4}}"
    )
    for k in list_keys(f"{PREFIX}/{sym}/"):
        if k.endswith("OVERLAP.json"):
            base = k.rsplit("/", 1)[0]
            yield base


def compute_coverage(base_key):
    """Coverage = fraction(venues with at least one parquet) and per-venue flags."""
    # discover venues from OVERLAP.json
    ol_key = f"{base_key}/OVERLAP.json"
    ol = json.loads(s3.get_object(Bucket=BUCKET, Key=ol_key)["Body"].read())
    venues = ol.get("venues", [])
    per_venue = {}
    for v in venues:
        # find one parquet under ticks/{venue}/
        found = False
        for k in list_keys(f"{base_key}/ticks/{v}/"):
            if k.endswith(".parquet"):
                found = True
                break
        per_venue[v] = 1.0 if found else 0.0
    # overall coverage: mean of venue coverages (simple heuristic)
    overall = sum(per_venue.values()) / max(1, len(venues))
    return {
        "coverage_percentage": overall,
        **{v: {"coverage_percentage": per_venue[v]} for v in per_venue},
    }


def has_coverage(base_key):
    try:
        s3.head_object(Bucket=BUCKET, Key=f"{base_key}/meta/coverage.json")
        return True
    except Exception:
        return False


def write_coverage(base_key, cov):
    body = (json.dumps(cov, indent=2)).encode()
    s3.put_object(
        Bucket=BUCKET,
        Key=f"{base_key}/meta/coverage.json",
        Body=body,
        ContentType="application/json",
    )


def main():
    missing = []
    for sym in SYMBOLS:
        for base in windows_for_symbol(sym):
            if not has_coverage(base):
                missing.append(base)
    print(f"Found {len(missing)} windows missing coverage.json")
    if DRY_RUN:
        for b in missing[:10]:
            print("DRY-RUN would fill:", f"s3://{BUCKET}/{b}/meta/coverage.json")
        return
    for b in missing:
        cov = compute_coverage(b)
        write_coverage(b, cov)
        print("Wrote coverage:", f"s3://{BUCKET}/{b}/meta/coverage.json")


if __name__ == "__main__":
    main()
