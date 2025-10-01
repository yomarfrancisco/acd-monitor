#!/usr/bin/env python3
"""
Lock inputs for Stage H2 - Environment Flags + Lagged/Nonlinear Screens
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
import boto3

S3_BUCKET = "acd-monitor-snapshots"
DATE = "20251001"

s3 = boto3.client('s3')

def get_s3_object_hash(key: str) -> str:
    """Get SHA256 hash of S3 object."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        content = response['Body'].read()
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        print(f"Warning: Could not hash {key}: {e}")
        return "MISSING"

def get_s3_prefix_hashes(prefix: str) -> dict:
    """Get hashes for all objects in S3 prefix."""
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            return {}
        
        hashes = {}
        for obj in response['Contents']:
            if obj['Key'].endswith('.parquet') or obj['Key'].endswith('.json'):
                hashes[obj['Key']] = get_s3_object_hash(obj['Key'])
        
        return hashes
    except Exception as e:
        print(f"Warning: Could not list {prefix}: {e}")
        return {}

def main():
    """Lock inputs for Stage H2."""
    print("🔒 Locking inputs for Stage H2...")
    
    # Hash canonical data
    print("📊 Hashing canonical data...")
    canonical_btc = get_s3_prefix_hashes(f"canonical/{DATE}/btc_ticks/")
    canonical_eth = get_s3_prefix_hashes(f"canonical/{DATE}/eth_ticks/")
    
    # Hash Wave-1 outputs
    print("📊 Hashing Wave-1 outputs...")
    wave1_btc = get_s3_prefix_hashes(f"analysis/{DATE}/wave1/btc_usd/")
    wave1_eth = get_s3_prefix_hashes(f"analysis/{DATE}/wave1/eth_usd/")
    
    # Create lock data
    lock_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "H2",
        "date": DATE,
        "canonical_btc": canonical_btc,
        "canonical_eth": canonical_eth,
        "wave1_btc": wave1_btc,
        "wave1_eth": wave1_eth,
        "lock_checksum": hashlib.sha256(
            json.dumps({
                "canonical_btc": canonical_btc,
                "canonical_eth": canonical_eth,
                "wave1_btc": wave1_btc,
                "wave1_eth": wave1_eth
            }, sort_keys=True).encode()
        ).hexdigest()
    }
    
    # Write local lock file
    os.makedirs("analysis/_locks", exist_ok=True)
    with open("analysis/_locks/wave1_20251001.sha256", "w") as f:
        json.dump(lock_data, f, indent=2)
    
    print(f"✅ Local lock written: analysis/_locks/wave1_20251001.sha256")
    
    # Write S3 lock file
    s3_key = f"analysis/{DATE}/wave1_h2/_checks/_lock.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(lock_data, indent=2)
    )
    
    print(f"✅ S3 lock written: s3://{S3_BUCKET}/{s3_key}")
    
    # Print summary
    print(f"\n📊 Lock Summary:")
    print(f"  Canonical BTC files: {len(canonical_btc)}")
    print(f"  Canonical ETH files: {len(canonical_eth)}")
    print(f"  Wave-1 BTC files: {len(wave1_btc)}")
    print(f"  Wave-1 ETH files: {len(wave1_eth)}")
    print(f"  Lock checksum: {lock_data['lock_checksum']}")

if __name__ == "__main__":
    main()
