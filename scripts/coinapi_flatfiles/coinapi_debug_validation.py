#!/usr/bin/env python3
"""
Debug validation issues in the 7-day backfill.
"""

import json
import boto3
import tempfile
from pathlib import Path
import pandas as pd

def debug_validation_issues():
    """Debug why validation is failing."""
    s3_client = boto3.client('s3')
    bucket = "acd-monitor-snapshots"
    
    print("🔍 DEBUGGING VALIDATION ISSUES")
    print("="*80)
    
    # Check what's actually in S3
    print("📊 Checking S3 contents...")
    
    # List backfill directory
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix="backfill/coinapi_1s/", Delimiter='/')
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                print(f"   📁 {prefix['Prefix']}")
        else:
            print("   ❌ No backfill data found")
    except Exception as e:
        print(f"   ❌ Error listing S3: {e}")
    
    # Check run log
    try:
        response = s3_client.get_object(Bucket=bucket, Key="analysis/coinapi_1s/run_log.json")
        run_log = json.loads(response['Body'].read().decode('utf-8'))
        
        print(f"\n📊 RUN LOG SUMMARY:")
        print(f"   Successes: {run_log['successes']}")
        print(f"   Failures: {run_log['failures']}")
        
        for venue, venue_data in run_log['venues'].items():
            print(f"\n📊 {venue}:")
            for date, day_data in venue_data['days'].items():
                if day_data['status'] == 'failed':
                    print(f"   ❌ {date}: {day_data.get('issues', day_data.get('error', 'Unknown error'))}")
                else:
                    print(f"   ✅ {date}: {day_data.get('n_candles', 'Unknown')} candles")
                    
    except Exception as e:
        print(f"   ❌ Error reading run log: {e}")

if __name__ == "__main__":
    debug_validation_issues()
