#!/usr/bin/env python3
"""
ICP-VMM Backfill Script

Runs provisional analysis on the last 4 valid BTC windows.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import boto3
from datetime import datetime, timezone

def get_latest_btc_windows(bucket: str, count: int = 4) -> List[str]:
    """Get the latest BTC-USD windows from S3."""
    s3 = boto3.client('s3')
    
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix='snapshots/BTC-USD/')
        
        windows = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('/OVERLAP.json'):
                # Extract window path
                window_path = key.replace('/OVERLAP.json', '')
                windows.append(f"s3://{bucket}/{window_path}")
        
        # Sort by timestamp and return latest
        windows.sort(reverse=True)
        return windows[:count]
        
    except Exception as e:
        print(f"❌ Error listing BTC windows: {e}")
        return []

def run_analysis_on_window(window_path: str) -> Dict[str, Any]:
    """Run ICP-VMM analysis on a single window."""
    print(f"📊 Analyzing window: {window_path}")
    
    try:
        # Extract window ID from path
        window_id = window_path.split('/')[-1]
        
        # Run the analysis
        result = subprocess.run([
            'python', 'scripts/icp_vmm/test_refined_icp_vmm.py'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        if result.returncode != 0:
            return {
                'window_id': window_id,
                'status': 'ERROR',
                'error': result.stderr
            }
        
        # Find output directory
        output_dirs = list(Path('/tmp').glob('icp_vmm_output_*'))
        if not output_dirs:
            return {
                'window_id': window_id,
                'status': 'ERROR',
                'error': 'No output directory found'
            }
        
        output_dir = output_dirs[0]
        
        # Read manifest to get results
        manifest_path = output_dir / 'MANIFEST.json'
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            return {
                'window_id': window_id,
                'status': 'SUCCESS',
                'manifest_hash': manifest.get('integrity', {}).get('manifestHash', ''),
                'run_status': manifest.get('run', {}).get('runStatus', 'UNKNOWN'),
                'output_dir': str(output_dir)
            }
        else:
            return {
                'window_id': window_id,
                'status': 'ERROR',
                'error': 'MANIFEST.json not found'
            }
            
    except Exception as e:
        return {
            'window_id': window_id,
            'status': 'ERROR',
            'error': str(e)
        }

def create_index(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create _index.json for all runs."""
    return {
        'indexVersion': '1.0.0',
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'totalRuns': len(results),
        'runs': results,
        'summary': {
            'statusCounts': {
                'SUCCESS': len([r for r in results if r['status'] == 'SUCCESS']),
                'ERROR': len([r for r in results if r['status'] == 'ERROR'])
            },
            'latestRun': results[0] if results else None
        }
    }

def upload_index(bucket: str, prefix: str, index_content: Dict[str, Any]) -> bool:
    """Upload index.json to S3."""
    s3 = boto3.client('s3')
    
    try:
        index_key = f"{prefix}/_index.json"
        s3.put_object(
            Bucket=bucket,
            Key=index_key,
            Body=json.dumps(index_content, indent=2),
            ContentType='application/json'
        )
        print(f"✅ Index uploaded to s3://{bucket}/{index_key}")
        return True
    except Exception as e:
        print(f"❌ Error uploading index: {e}")
        return False

def main():
    """Main backfill function."""
    bucket = "acd-monitor-snapshots"
    prefix = "analysis/BTC-USD/icp_vmm/provisional"
    
    print("🚀 Starting ICP-VMM backfill...")
    
    # Get latest BTC windows
    windows = get_latest_btc_windows(bucket, 4)
    if not windows:
        print("❌ No BTC windows found")
        sys.exit(1)
    
    print(f"✅ Found {len(windows)} BTC windows")
    
    # Run analysis on each window
    results = []
    for window in windows:
        result = run_analysis_on_window(window)
        results.append(result)
        
        if result['status'] == 'SUCCESS':
            print(f"✅ {result['window_id']}: {result['run_status']}")
        else:
            print(f"❌ {result['window_id']}: {result.get('error', 'Unknown error')}")
    
    # Create and upload index
    index_content = create_index(results)
    if upload_index(bucket, prefix, index_content):
        print("🎉 Backfill completed successfully!")
        print(f"📊 Results: {len([r for r in results if r['status'] == 'SUCCESS'])}/{len(results)} successful")
        sys.exit(0)
    else:
        print("❌ Backfill failed to upload index")
        sys.exit(1)

if __name__ == '__main__':
    main()
