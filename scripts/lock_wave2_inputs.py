#!/usr/bin/env python3
"""
Lock inputs for Stage I1 - Event Studies
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
    """Lock inputs for Stage I1."""
    print("🔒 Locking inputs for Stage I1 - Event Studies...")
    
    # Hash canonical data
    print("📊 Hashing canonical data...")
    canonical_btc = get_s3_prefix_hashes(f"canonical/{DATE}/btc_ticks/")
    canonical_eth = get_s3_prefix_hashes(f"canonical/{DATE}/eth_ticks/")
    
    # Hash H2 environment flags
    print("📊 Hashing H2 environment flags...")
    env_flags_btc = get_s3_object_hash(f"data/derived/btc_usd/env_flags_1s.parquet")
    env_flags_eth = get_s3_object_hash(f"data/derived/eth_usd/env_flags_1s.parquet")
    
    # Hash Wave-1 outputs for cross-checks
    print("📊 Hashing Wave-1 outputs...")
    wave1_btc = get_s3_prefix_hashes(f"analysis/{DATE}/wave1/btc_usd/")
    wave1_eth = get_s3_prefix_hashes(f"analysis/{DATE}/wave1/eth_usd/")
    
    # Event study parameters
    parameters = {
        "events": {
            "ny_open": {
                "window_center": "13:30",
                "window_range": "13:30-13:45",
                "description": "NY open window center at 13:30 UTC"
            },
            "session_transition": {
                "boundaries": ["00:00", "08:00", "13:00", "20:00"],
                "tolerance": "±5m",
                "description": "Session transition boundaries"
            },
            "vwap_reset": {
                "time": "00:00",
                "tolerance": "±5m",
                "description": "Midnight VWAP reset jump"
            },
            "return_2sigma_v": {
                "source": "H2_flags",
                "description": "Per-venue 2-sigma return shocks"
            }
        },
        "windows": {
            "estimation_window": "15 minutes pre-event",
            "event_window": "15 minutes post-event"
        },
        "metrics": [
            "mid-return CAR",
            "spread change",
            "volatility change (pre vs post)",
            "hit ratio (sign of first 60s return)",
            "missing data percentage"
        ],
        "min_sample_rule": {
            "n_events_required": 5,
            "status_if_insufficient": "insufficient_sample"
        }
    }
    
    # Create lock data
    lock_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "I1",
        "date": DATE,
        "canonical_btc": canonical_btc,
        "canonical_eth": canonical_eth,
        "env_flags_btc": env_flags_btc,
        "env_flags_eth": env_flags_eth,
        "wave1_btc": wave1_btc,
        "wave1_eth": wave1_eth,
        "parameters": parameters,
        "lock_checksum": hashlib.sha256(
            json.dumps({
                "canonical_btc": canonical_btc,
                "canonical_eth": canonical_eth,
                "env_flags_btc": env_flags_btc,
                "env_flags_eth": env_flags_eth,
                "wave1_btc": wave1_btc,
                "wave1_eth": wave1_eth
            }, sort_keys=True).encode()
        ).hexdigest()
    }
    
    # Write S3 lock file
    s3_key = f"analysis/{DATE}/wave2/events/_checks/_lock.json"
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
    print(f"  H2 env flags BTC: {env_flags_btc[:16]}...")
    print(f"  H2 env flags ETH: {env_flags_eth[:16]}...")
    print(f"  Wave-1 BTC files: {len(wave1_btc)}")
    print(f"  Wave-1 ETH files: {len(wave1_eth)}")
    print(f"  Lock checksum: {lock_data['lock_checksum']}")
    
    print(f"\n📋 Event Study Parameters:")
    print(f"  Events: {list(parameters['events'].keys())}")
    print(f"  Windows: {parameters['windows']}")
    print(f"  Min sample: {parameters['min_sample_rule']['n_events_required']} events per venue")

if __name__ == "__main__":
    main()

