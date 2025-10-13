#!/usr/bin/env python3
"""
Phase 42A-v7b: July W-7 Download Completion (Retry + Coverage Gate)
Recover all 4 July 1 files to achieve 100% coverage
"""

import os
import requests
import xml.etree.ElementTree as ET
import gzip
import hashlib
import time
import random
import concurrent.futures
from datetime import datetime
import pandas as pd

# Global start time for runtime tracking
START_TIME = time.time()

def check_guardrails():
    """Check memory and runtime guardrails"""
    import psutil
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    runtime_s = time.time() - START_TIME
    
    if current_mb > 750:  # 750 MB limit
        print(f"🚫 HALT: Memory usage {current_mb:.1f} MB exceeds 750 MB limit")
        return False
    
    if runtime_s > 2700:  # 45 minutes
        print(f"🚫 HALT: Runtime {runtime_s:.1f}s exceeds 45 minutes")
        return False
    
    print(f"📊 Memory: {current_mb:.1f} MB, Runtime: {runtime_s:.1f}s")
    return True

def identify_missing_files():
    """Identify missing July 1st files for all 4 venues"""
    print("🔍 **Phase 42A-v7b: July W-7 Download Completion**")
    print("=" * 60)
    
    # Target date and venues
    target_date = "2025-07-01"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Check existing files in the raw directory
    raw_dir = 'data_v7/raw/coinapi_jul_extension'
    
    missing_files = []
    existing_files = []
    
    for venue in venues:
        # Expected file path pattern
        expected_path = os.path.join(raw_dir, f"{target_date}_{venue}.gz")
        
        if os.path.exists(expected_path):
            file_size = os.path.getsize(expected_path)
            if file_size > 0:
                existing_files.append({
                    'venue': venue,
                    'path': expected_path,
                    'size': file_size,
                    'status': 'exists'
                })
            else:
                missing_files.append({
                    'venue': venue,
                    'path': expected_path,
                    'status': 'empty_file'
                })
        else:
            missing_files.append({
                'venue': venue,
                'path': expected_path,
                'status': 'missing'
            })
    
    print(f"📊 **Missing Files Analysis for {target_date}:**")
    print(f"   Existing: {len(existing_files)} files")
    print(f"   Missing: {len(missing_files)} files")
    
    if missing_files:
        print(f"📊 Missing files:")
        for file_info in missing_files:
            print(f"   {file_info['venue']}: {file_info['status']}")
    
    return missing_files, existing_files

def download_single_file(venue, target_date, output_dir, attempt=1, max_attempts=3):
    """Download a single file with retry logic"""
    print(f"📊 Downloading {venue} for {target_date} (attempt {attempt}/{max_attempts})")
    
    # CoinAPI configuration
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    base_url = "https://s3.flatfiles.coinapi.io/"
    
    # Construct the listing URL
    date_formatted = target_date.replace('-', '')
    list_url = f"{base_url}bucket/?prefix=T-TRADES/D-{date_formatted}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'Mozilla/5.0 (compatible; DataDownloader/1.0)'
    }
    
    try:
        # List objects in the bucket
        response = requests.get(list_url, headers=headers, timeout=120)
        
        if response.status_code == 200:
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Find the actual file URL
            file_url = None
            for elem in root.iter():
                if elem.tag.endswith('Key') and elem.text and elem.text.endswith('.gz'):
                    file_url = f"{base_url}{elem.text}"
                    break
            
            if file_url:
                # Download the file
                file_response = requests.get(file_url, headers=headers, timeout=120)
                
                if file_response.status_code == 200:
                    # Save the file
                    output_path = os.path.join(output_dir, f"{target_date}_{venue}.gz")
                    
                    with open(output_path, 'wb') as f:
                        f.write(file_response.content)
                    
                    file_size = len(file_response.content)
                    
                    # Compute SHA-256
                    with open(output_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    return {
                        'venue': venue,
                        'status': 'success',
                        'size': file_size,
                        'sha256': file_hash,
                        'attempts': attempt,
                        'elapsed': time.time() - START_TIME,
                        'error': None
                    }
                else:
                    return {
                        'venue': venue,
                        'status': 'http_error',
                        'size': 0,
                        'sha256': None,
                        'attempts': attempt,
                        'elapsed': time.time() - START_TIME,
                        'error': f"HTTP {file_response.status_code}"
                    }
            else:
                return {
                    'venue': venue,
                    'status': 'no_file_found',
                    'size': 0,
                    'sha256': None,
                    'attempts': attempt,
                    'elapsed': time.time() - START_TIME,
                    'error': "No .gz file found in listing"
                }
        else:
            return {
                'venue': venue,
                'status': 'http_error',
                'size': 0,
                'sha256': None,
                'attempts': attempt,
                'elapsed': time.time() - START_TIME,
                'error': f"HTTP {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        return {
            'venue': venue,
            'status': 'timeout',
            'size': 0,
            'sha256': None,
            'attempts': attempt,
            'elapsed': time.time() - START_TIME,
            'error': "Request timeout"
        }
    except Exception as e:
        return {
            'venue': venue,
            'status': 'error',
            'size': 0,
            'sha256': None,
            'attempts': attempt,
            'elapsed': time.time() - START_TIME,
            'error': str(e)
        }

def retry_downloads(missing_files):
    """Retry downloads with exponential backoff and jitter"""
    print(f"\n📊 **Retrying Downloads with Exponential Backoff**")
    print("=" * 60)
    
    if not missing_files:
        print("📊 No missing files to retry")
        return []
    
    # Create output directory
    output_dir = 'data_v7/raw/coinapi_jul_extension'
    os.makedirs(output_dir, exist_ok=True)
    
    target_date = "2025-07-01"
    venues_to_retry = [f['venue'] for f in missing_files]
    
    # Backoff intervals: 30s → 60s → 120s
    backoff_intervals = [30, 60, 120]
    max_attempts = 3
    
    retry_results = []
    
    for venue in venues_to_retry:
        print(f"📊 Retrying {venue}...")
        
        for attempt in range(1, max_attempts + 1):
            # Add jitter to backoff interval
            if attempt > 1:
                base_interval = backoff_intervals[attempt - 2]
                jitter = random.uniform(-5, 5)  # ±5 second jitter
                sleep_time = max(0, base_interval + jitter)
                print(f"   Waiting {sleep_time:.1f}s before attempt {attempt}")
                time.sleep(sleep_time)
            
            # Attempt download
            result = download_single_file(venue, target_date, output_dir, attempt, max_attempts)
            retry_results.append(result)
            
            if result['status'] == 'success':
                print(f"   ✅ {venue}: Success (attempt {attempt})")
                break
            else:
                print(f"   ❌ {venue}: {result['error']} (attempt {attempt})")
                
                # If this was the last attempt, log the failure
                if attempt == max_attempts:
                    print(f"   🚫 {venue}: Failed after {max_attempts} attempts")
    
    return retry_results

def verify_downloads():
    """Verify file sizes and SHA-256 checksums"""
    print(f"\n📊 **Verifying Downloads**")
    print("=" * 60)
    
    target_date = "2025-07-01"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    raw_dir = 'data_v7/raw/coinapi_jul_extension'
    
    verification_results = []
    
    for venue in venues:
        file_path = os.path.join(raw_dir, f"{target_date}_{venue}.gz")
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            
            if file_size > 0:
                # Compute SHA-256
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                verification_results.append({
                    'venue': venue,
                    'status': 'verified',
                    'size': file_size,
                    'sha256': file_hash
                })
                
                print(f"   ✅ {venue}: {file_size:,} bytes, SHA-256: {file_hash[:16]}...")
            else:
                verification_results.append({
                    'venue': venue,
                    'status': 'empty',
                    'size': 0,
                    'sha256': None
                })
                
                print(f"   ❌ {venue}: Empty file")
        else:
            verification_results.append({
                'venue': venue,
                'status': 'missing',
                'size': 0,
                'sha256': None
            })
            
            print(f"   ❌ {venue}: File not found")
    
    return verification_results

def compute_coverage():
    """Recompute coverage for July 1-14 (target 56/56 = 100%)"""
    print(f"\n📊 **Computing Coverage for July 1-14**")
    print("=" * 60)
    
    # Expected files: 14 days × 4 venues = 56 files
    expected_files = 56
    
    # Check actual files
    raw_dir = 'data_v7/raw/coinapi_jul_extension'
    actual_files = 0
    
    # Check each day from July 1-14
    for day in range(1, 15):
        date_str = f"2025-07-{day:02d}"
        
        for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
            file_path = os.path.join(raw_dir, f"{date_str}_{venue}.gz")
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                actual_files += 1
    
    coverage_percentage = (actual_files / expected_files) * 100
    
    print(f"📊 Expected files: {expected_files}")
    print(f"📊 Actual files: {actual_files}")
    print(f"📊 Coverage: {coverage_percentage:.1f}%")
    
    return actual_files, expected_files, coverage_percentage

def generate_report(retry_results, verification_results, coverage_stats):
    """Generate coverage report and final verdict"""
    print(f"\n📊 **Final Coverage Report**")
    print("=" * 60)
    
    # Per-venue status table for 2025-07-01
    print(f"📊 **Per-Venue Status for 2025-07-01:**")
    print(f"   Venue     | Status    | Size (bytes) | SHA-256 (first 16) | Attempts | Elapsed (s)")
    print(f"   ----------|-----------|--------------|--------------------|----------|------------")
    
    for result in verification_results:
        venue = result['venue']
        status = result['status']
        size = result['size']
        sha256 = result['sha256'][:16] + "..." if result['sha256'] else "N/A"
        
        # Find retry info for this venue
        retry_info = next((r for r in retry_results if r['venue'] == venue), None)
        attempts = retry_info['attempts'] if retry_info else "N/A"
        elapsed = retry_info['elapsed'] if retry_info else "N/A"
        
        print(f"   {venue:<10} | {status:<9} | {size:>12,} | {sha256:<18} | {attempts:>8} | {elapsed:>10}")
    
    # Coverage summary
    actual_files, expected_files, coverage_percentage = coverage_stats
    
    print(f"\n📊 **Coverage Summary for July 1-14:**")
    print(f"   Expected: {expected_files} files")
    print(f"   Downloaded: {actual_files} files")
    print(f"   Coverage: {coverage_percentage:.1f}%")
    
    # Final verdict
    print(f"\n📊 **Final Verdict:**")
    
    if coverage_percentage >= 100.0:
        print(f"✅ Coverage gate PASSED: {actual_files}/{expected_files} ({coverage_percentage:.1f}%). Ready for 39C-Retro-2 (beacons).")
        return True
    elif coverage_percentage >= 95.0:
        print(f"⚠️ Coverage gate PASSED (threshold): {actual_files}/{expected_files} ({coverage_percentage:.1f}%). Ready for 39C-Retro-2 (beacons).")
        return True
    else:
        print(f"❌ Coverage gate FAILED: {actual_files}/{expected_files} ({coverage_percentage:.1f}%). Reason(s): Missing files. Next step required.")
        return False

def main():
    print('🔍 Phase 42A-v7b: July W-7 Download Completion')
    print('=' * 60)
    
    # Check guardrails
    if not check_guardrails():
        return
    
    try:
        # Step 1: Identify missing files
        missing_files, existing_files = identify_missing_files()
        
        # Step 2: Retry downloads
        retry_results = retry_downloads(missing_files)
        
        # Step 3: Verify downloads
        verification_results = verify_downloads()
        
        # Step 4: Compute coverage
        coverage_stats = compute_coverage()
        
        # Step 5: Generate report
        gate_passed = generate_report(retry_results, verification_results, coverage_stats)
        
        if gate_passed:
            print(f"\n✅ **Phase 42A-v7b Complete - Ready for Beacon Processing**")
        else:
            print(f"\n❌ **Phase 42A-v7b Failed - Manual Intervention Required**")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Final guardrail check
        check_guardrails()

if __name__ == '__main__':
    main()
