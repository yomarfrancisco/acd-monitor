#!/usr/bin/env python3
"""
Find Raw BTC-USD Data Files in S3
"""

import boto3
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import json
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class RawDataFinder:
    """Find raw BTC-USD data files in S3."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'acd-monitor-snapshots'
        
    def find_raw_data(self):
        """Find raw BTC-USD data files."""
        print("🔍 Finding Raw BTC-USD Data Files")
        print("=" * 50)
        
        # Look for snapshots directory
        print("📥 Looking for snapshots directory...")
        snapshots_objects = self._list_objects_with_prefix('snapshots/')
        
        print(f"📊 Found {len(snapshots_objects)} objects in snapshots/")
        
        # Look for BTC-USD specifically
        btc_objects = [obj for obj in snapshots_objects if 'BTC-USD' in obj['Key']]
        print(f"📊 Found {len(btc_objects)} BTC-USD objects")
        
        if btc_objects:
            print("\n🔍 BTC-USD Raw Data Files:")
            for obj in btc_objects:
                print(f"  📄 {obj['Key']} ({obj['Size']} bytes)")
        
        # Look for venue-specific data
        venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        venue_data = {}
        for venue in venues:
            venue_objects = [obj for obj in btc_objects if venue in obj['Key'].lower()]
            venue_data[venue] = len(venue_objects)
            print(f"\n  {venue}: {len(venue_objects)} files")
            if venue_objects:
                for obj in venue_objects[:3]:  # Show first 3
                    print(f"    📄 {obj['Key']} ({obj['Size']} bytes)")
        
        # Look for parquet files specifically
        parquet_objects = [obj for obj in btc_objects if obj['Key'].endswith('.parquet')]
        print(f"\n📊 Parquet files: {len(parquet_objects)}")
        
        if parquet_objects:
            print("🔍 Sample parquet files:")
            for obj in parquet_objects[:5]:
                print(f"  📄 {obj['Key']} ({obj['Size']} bytes)")
        
        # Generate report
        report = {
            'audit_date': datetime.now().isoformat(),
            'bucket': self.bucket_name,
            'snapshots_objects': len(snapshots_objects),
            'btc_objects': len(btc_objects),
            'parquet_objects': len(parquet_objects),
            'venue_data': venue_data,
            'sample_objects': btc_objects[:10] if btc_objects else []
        }
        
        # Save report
        os.makedirs('analysis/wave2/btc_usd_s3_audit', exist_ok=True)
        with open('analysis/wave2/btc_usd_s3_audit/raw_data_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n✅ Raw data search completed")
        print(f"📁 Report saved to analysis/wave2/btc_usd_s3_audit/raw_data_report.json")
        
        return report
    
    def _list_objects_with_prefix(self, prefix):
        """List objects with specific prefix."""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    objects.extend(page['Contents'])
        except Exception as e:
            print(f"❌ Error listing objects: {e}")
            return []
        
        return objects

if __name__ == "__main__":
    finder = RawDataFinder()
    finder.find_raw_data()
