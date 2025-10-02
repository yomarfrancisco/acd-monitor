#!/usr/bin/env python3
"""
Investigate S3 Parquet Files Structure
Check the actual format and content of S3 parquet files.
"""

import boto3
import pandas as pd
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class S3FileInvestigator:
    """Investigate S3 parquet files to understand their structure."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'acd-monitor-snapshots'
        self.btc_prefix = 'snapshots/BTC-USD/'
    
    def investigate_files(self):
        """Investigate a few sample parquet files."""
        print("🔍 Investigating S3 Parquet Files")
        print("=" * 50)
        
        # Get a few sample files
        sample_files = self._get_sample_files()
        
        if not sample_files:
            print("❌ No sample files found")
            return
        
        print(f"📊 Found {len(sample_files)} sample files")
        
        # Investigate each file
        for i, file_info in enumerate(sample_files[:3]):  # Check first 3 files
            print(f"\n🔍 Investigating file {i+1}: {file_info['key']}")
            self._investigate_single_file(file_info)
    
    def _get_sample_files(self):
        """Get sample parquet files."""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('.parquet'):
                            objects.append({
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': obj['LastModified']
                            })
                            if len(objects) >= 5:  # Limit to 5 files
                                break
                    if len(objects) >= 5:
                        break
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return []
        
        return objects
    
    def _investigate_single_file(self, file_info):
        """Investigate a single parquet file."""
        try:
            print(f"  📥 Downloading {file_info['key']} ({file_info['size']} bytes)...")
            
            # Download file to local temp
            temp_file = f"/tmp/temp_{file_info['key'].split('/')[-1]}"
            
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=file_info['key'],
                Filename=temp_file
            )
            
            print(f"  📊 File downloaded to {temp_file}")
            
            # Try to read with pandas
            try:
                df = pd.read_parquet(temp_file)
                print(f"  ✅ Successfully read parquet file")
                print(f"    Shape: {df.shape}")
                print(f"    Columns: {list(df.columns)}")
                print(f"    Index: {df.index.name if df.index.name else 'RangeIndex'}")
                print(f"    Dtypes: {df.dtypes.to_dict()}")
                
                if len(df) > 0:
                    print(f"    Sample data:")
                    print(f"    {df.head(2).to_string()}")
                
            except Exception as e:
                print(f"  ❌ Error reading parquet: {e}")
                
                # Try to read as raw bytes
                with open(temp_file, 'rb') as f:
                    raw_data = f.read(100)  # First 100 bytes
                    print(f"  📄 Raw data (first 100 bytes): {raw_data}")
            
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
        except Exception as e:
            print(f"  ❌ Error investigating file: {e}")

if __name__ == "__main__":
    investigator = S3FileInvestigator()
    investigator.investigate_files()
