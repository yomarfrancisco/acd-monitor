#!/usr/bin/env python3
"""
Phase 42A-v7e: Week -6 (July 14-20) + July 21st Preflight + Download Attempt
Download missing raw flat files for Week -6 (July 14-20) plus July 21st if missing
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import pandas as pd
from datetime import datetime, timezone
import psutil

# Global start time for runtime tracking
START_TIME = time.time()

# API Configuration
API_KEY = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
BASE_URL = "https://s3.flatfiles.coinapi.io/"
MASKED_KEY = API_KEY[:-4] + "****"

# Guardrails
MAX_HTTP_REQUESTS = 80
MAX_RUNTIME_MINUTES = 45
GET_TIMEOUT = 120
RETRY_DELAY = 60

# Week -6 dates (UTC): 2025-07-14 → 2025-07-20 + July 21st
WEEK_6B_DATES = [
    '20250714', '20250715', '20250716', '20250717', 
    '20250718', '20250719', '20250720', '20250721'
]

VENUES = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

def check_guardrails():
    """Check runtime and API budget guardrails"""
    runtime_s = time.time() - START_TIME
    runtime_min = runtime_s / 60
    
    if runtime_min > MAX_RUNTIME_MINUTES:
        print(f"🚫 HALT: Runtime {runtime_min:.1f}m exceeds {MAX_RUNTIME_MINUTES}m limit")
        return False
    
    return True

def enumerate_expected_keys():
    """Enumerate expected keys for July 14-21 × 4 venues"""
    print("🔍 **Phase 42A-v7e: Week -6 (July 14-20) + July 21st Download**")
    print("=" * 60)
    print(f"📊 API Key: {MASKED_KEY}")
    print(f"📊 Week -6B dates: {WEEK_6B_DATES}")
    print(f"📊 Venues: {VENUES}")
    print(f"📊 Expected files: {len(WEEK_6B_DATES)} × {len(VENUES)} = {len(WEEK_6B_DATES) * len(VENUES)}")
    
    expected_keys = []
    
    for date in WEEK_6B_DATES:
        for venue in VENUES:
            # Expected key pattern: T-TRADES/D-YYYYMMDD/E-VENUE/...BTCUSDT.csv.gz
            expected_key = f"T-TRADES/D-{date}/E-{venue}/"
            expected_keys.append({
                'date': date,
                'venue': venue,
                'expected_key': expected_key,
                'filename': f"{venue}_{date}_BTCUSDT.csv.gz"
            })
    
    return expected_keys

def local_diff(expected_keys):
    """Compare against existing files to avoid re-downloads"""
    print(f"\n📊 **Local Diff: Checking Existing Files**")
    print("=" * 60)
    
    # Search paths for existing files
    search_paths = [
        'data_v6/raw/coinapi_jul/',
        'data_v7/raw/coinapi_jul_extension/',
        'data_v7/raw/coinapi_jul_w6/',
        'data_v7/raw/coinapi_jul_w6b/'
    ]
    
    existing_files = {}
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.endswith('.csv.gz'):
                        # Extract date and venue from filename
                        parts = file.split('_')
                        if len(parts) >= 3:
                            venue = parts[0]
                            date = parts[1]
                            key = f"{date}_{venue}"
                            existing_files[key] = {
                                'path': os.path.join(root, file),
                                'size': os.path.getsize(os.path.join(root, file))
                            }
    
    # Build diff table
    diff_data = []
    missing_keys = []
    
    for key_info in expected_keys:
        date = key_info['date']
        venue = key_info['venue']
        key = f"{date}_{venue}"
        
        exists_local = key in existing_files
        diff_data.append({
            'date': date,
            'venue': venue,
            'expected_key': key_info['expected_key'],
            'exists_local': exists_local,
            'local_size': existing_files[key]['size'] if exists_local else 0
        })
        
        if not exists_local:
            missing_keys.append(key_info)
    
    # Print preflight diff table
    print(f"📊 **Preflight Diff Table:**")
    print(f"   Date     | Venue    | Expected Key                    | Exists Local | Local Size")
    print(f"   ---------|----------|--------------------------------|--------------|----------")
    
    for row in diff_data:
        exists_str = "✅ Yes" if row['exists_local'] else "❌ No"
        size_str = f"{row['local_size']:,}" if row['exists_local'] else "0"
        print(f"   {row['date']} | {row['venue']:<8} | {row['expected_key']:<30} | {exists_str:<12} | {size_str}")
    
    existing_count = sum(1 for row in diff_data if row['exists_local'])
    missing_count = len(missing_keys)
    
    print(f"\n📊 Summary: {existing_count} exist locally, {missing_count} missing")
    
    return missing_keys, diff_data

def dry_run_list(missing_keys):
    """Perform LIST/HEAD for missing files only"""
    print(f"\n📊 **Dry Run: LIST/HEAD for Missing Files**")
    print("=" * 60)
    
    headers = {
        'X-CoinAPI-Key': API_KEY,
        'User-Agent': 'Mozilla/5.0 (compatible; DataDownloader/1.0)'
    }
    
    api_counters = {
        'list_calls': 0,
        'head_calls': 0,
        'get_calls': 0,
        'total_calls': 0
    }
    
    confirmed_files = []
    
    for key_info in missing_keys:
        if not check_guardrails():
            break
        
        if api_counters['total_calls'] >= MAX_HTTP_REQUESTS:
            print(f"🚫 API budget exceeded: {api_counters['total_calls']}/{MAX_HTTP_REQUESTS}")
            break
        
        date = key_info['date']
        venue = key_info['venue']
        expected_key = key_info['expected_key']
        
        print(f"📊 Checking {date} {venue}...")
        
        try:
            # LIST objects in bucket
            list_url = f"{BASE_URL}bucket/?prefix={expected_key}"
            response = requests.get(list_url, headers=headers, timeout=30)
            
            api_counters['list_calls'] += 1
            api_counters['total_calls'] += 1
            
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Find BTCUSDT file
                btcusdt_file = None
                for elem in root.iter():
                    if elem.tag.endswith('Key') and elem.text and 'BTCUSDT' in elem.text and elem.text.endswith('.gz'):
                        btcusdt_file = f"{BASE_URL}{elem.text}"
                        break
                
                if btcusdt_file:
                    print(f"   ✅ Found: {btcusdt_file}")
                    confirmed_files.append({
                        **key_info,
                        'file_url': btcusdt_file,
                        'status': 'confirmed'
                    })
                else:
                    print(f"   ❌ No BTCUSDT file found")
                    confirmed_files.append({
                        **key_info,
                        'file_url': None,
                        'status': 'no_btcusdt'
                    })
            else:
                print(f"   ❌ LIST failed: HTTP {response.status_code}")
                confirmed_files.append({
                    **key_info,
                    'file_url': None,
                    'status': f'list_error_{response.status_code}'
                })
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ LIST timeout")
            confirmed_files.append({
                **key_info,
                'file_url': None,
                'status': 'list_timeout'
            })
        except Exception as e:
            print(f"   ❌ LIST error: {e}")
            confirmed_files.append({
                **key_info,
                'file_url': None,
                'status': f'list_error_{str(e)}'
            })
    
    print(f"\n📊 Dry run complete: {len(confirmed_files)} files checked")
    print(f"📊 API calls used: {api_counters['total_calls']}/{MAX_HTTP_REQUESTS}")
    
    return confirmed_files, api_counters

def download_files(confirmed_files, api_counters):
    """Download confirmed files with retry policy"""
    print(f"\n📊 **Downloading Confirmed Files**")
    print("=" * 60)
    
    headers = {
        'X-CoinAPI-Key': API_KEY,
        'User-Agent': 'Mozilla/5.0 (compatible; DataDownloader/1.0)'
    }
    
    # Create output directory
    output_dir = 'data_v7/raw/coinapi_jul_w6b'
    os.makedirs(output_dir, exist_ok=True)
    
    download_results = []
    
    for file_info in confirmed_files:
        if not check_guardrails():
            break
        
        if api_counters['total_calls'] >= MAX_HTTP_REQUESTS:
            print(f"🚫 API budget exceeded: {api_counters['total_calls']}/{MAX_HTTP_REQUESTS}")
            break
        
        if file_info['status'] != 'confirmed':
            # Skip files that weren't confirmed
            download_results.append({
                **file_info,
                'download_status': 'skipped',
                'bytes': 0,
                'sha256': None,
                'elapsed_ms': 0
            })
            continue
        
        date = file_info['date']
        venue = file_info['venue']
        file_url = file_info['file_url']
        filename = file_info['filename']
        
        print(f"📊 Downloading {date} {venue}...")
        
        start_time = time.time()
        
        try:
            # Download file
            response = requests.get(file_url, headers=headers, timeout=GET_TIMEOUT)
            
            api_counters['get_calls'] += 1
            api_counters['total_calls'] += 1
            
            if response.status_code == 200:
                # Save file
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                
                # Compute SHA-256
                with open(output_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                print(f"   ✅ Success: {file_size:,} bytes, SHA256: {file_hash[:12]}...")
                
                download_results.append({
                    **file_info,
                    'download_status': 'OK',
                    'bytes': file_size,
                    'sha256': file_hash,
                    'elapsed_ms': elapsed_ms
                })
                
            elif response.status_code in [403, 408, 500, 502, 503, 504]:
                # Retry once
                print(f"   ⚠️ HTTP {response.status_code}, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                
                retry_response = requests.get(file_url, headers=headers, timeout=GET_TIMEOUT)
                api_counters['get_calls'] += 1
                api_counters['total_calls'] += 1
                
                if retry_response.status_code == 200:
                    # Save file
                    output_path = os.path.join(output_dir, filename)
                    
                    with open(output_path, 'wb') as f:
                        f.write(retry_response.content)
                    
                    file_size = len(retry_response.content)
                    
                    # Compute SHA-256
                    with open(output_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    print(f"   ✅ Retry success: {file_size:,} bytes, SHA256: {file_hash[:12]}...")
                    
                    download_results.append({
                        **file_info,
                        'download_status': 'OK',
                        'bytes': file_size,
                        'sha256': file_hash,
                        'elapsed_ms': elapsed_ms
                    })
                else:
                    print(f"   ❌ Retry failed: HTTP {retry_response.status_code}")
                    download_results.append({
                        **file_info,
                        'download_status': f'{response.status_code}_retry_{retry_response.status_code}',
                        'bytes': 0,
                        'sha256': None,
                        'elapsed_ms': (time.time() - start_time) * 1000
                    })
            else:
                print(f"   ❌ HTTP {response.status_code}")
                download_results.append({
                    **file_info,
                    'download_status': f'{response.status_code}',
                    'bytes': 0,
                    'sha256': None,
                    'elapsed_ms': (time.time() - start_time) * 1000
                })
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout")
            download_results.append({
                **file_info,
                'download_status': 'timeout',
                'bytes': 0,
                'sha256': None,
                'elapsed_ms': (time.time() - start_time) * 1000
            })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            download_results.append({
                **file_info,
                'download_status': f'error_{str(e)}',
                'bytes': 0,
                'sha256': None,
                'elapsed_ms': (time.time() - start_time) * 1000
            })
    
    return download_results, api_counters

def generate_reports(download_results, api_counters, diff_data):
    """Generate manifests and summary reports"""
    print(f"\n📊 **Generating Reports**")
    print("=" * 60)
    
    # Create output directories
    os.makedirs('data_v7/manifests', exist_ok=True)
    
    # Download log summary
    print(f"📊 **Download Log Summary:**")
    print(f"   Date     | Venue    | Status                    | Bytes      | SHA256 (first 12) | Elapsed (ms)")
    print(f"   ---------|----------|---------------------------|------------|-------------------|-------------")
    
    for result in download_results:
        status = result['download_status']
        bytes_str = f"{result['bytes']:,}" if result['bytes'] > 0 else "0"
        sha256_str = result['sha256'][:12] + "..." if result['sha256'] else "N/A"
        elapsed_str = f"{result['elapsed_ms']:.0f}"
        
        print(f"   {result['date']} | {result['venue']:<8} | {status:<25} | {bytes_str:<10} | {sha256_str:<17} | {elapsed_str}")
    
    # Coverage table
    print(f"\n📊 **Coverage Table (Post-Run):**")
    print(f"   Date     | Venue    | Expected | Downloaded | Missing")
    print(f"   ---------|----------|----------|------------|--------")
    
    coverage_data = []
    for date in WEEK_6B_DATES:
        for venue in VENUES:
            # Check if file exists locally (from diff) or was downloaded
            exists_local = any(row['date'] == date and row['venue'] == venue and row['exists_local'] 
                             for row in diff_data)
            downloaded = any(result['date'] == date and result['venue'] == venue and result['download_status'] == 'OK' 
                           for result in download_results)
            
            expected = 1
            found = 1 if (exists_local or downloaded) else 0
            missing = expected - found
            
            coverage_data.append({
                'date': date,
                'venue': venue,
                'expected': expected,
                'downloaded': found,
                'missing': missing
            })
            
            print(f"   {date} | {venue:<8} | {expected:<8} | {found:<10} | {missing}")
    
    # API usage counters
    print(f"\n📊 **API Usage Counters:**")
    print(f"   List calls: {api_counters['list_calls']}")
    print(f"   Head calls: {api_counters['head_calls']}")
    print(f"   Get calls: {api_counters['get_calls']}")
    print(f"   Total calls: {api_counters['total_calls']}/{MAX_HTTP_REQUESTS}")
    
    # Runtime
    runtime_s = time.time() - START_TIME
    runtime_min = runtime_s / 60
    print(f"\n📊 **Runtime:** {runtime_min:.1f}m ({runtime_s:.0f}s)")
    
    # Bytes downloaded
    total_bytes = sum(result['bytes'] for result in download_results)
    total_mb = total_bytes / (1024 * 1024)
    print(f"📊 **Bytes:** {total_mb:.1f} MB ({total_bytes:,} bytes)")
    
    # Generate manifest CSV
    manifest_data = []
    for result in download_results:
        if result['download_status'] == 'OK':
            manifest_data.append({
                'date': result['date'],
                'venue': result['venue'],
                'filename': result['filename'],
                'bytes': result['bytes'],
                'sha256': result['sha256'],
                'download_status': result['download_status'],
                'elapsed_ms': result['elapsed_ms']
            })
    
    if manifest_data:
        manifest_df = pd.DataFrame(manifest_data)
        manifest_path = 'data_v7/manifests/jul_w6b_flatfiles_manifest.csv'
        manifest_df.to_csv(manifest_path, index=False)
        print(f"📊 **Manifest path:** {manifest_path}")
    
    # Generate hash bundle
    hash_data = []
    for result in download_results:
        if result['download_status'] == 'OK':
            hash_data.append({
                'date': result['date'],
                'venue': result['venue'],
                'key': f"{result['date']}_{result['venue']}",
                'bytes': result['bytes'],
                'sha256': result['sha256']
            })
    
    if hash_data:
        hash_df = pd.DataFrame(hash_data)
        hash_path = 'data_v7/manifests/jul_w6b_hashes.csv'
        hash_df.to_csv(hash_path, index=False)
        print(f"📊 **Hash bundle:** {hash_path}")
    
    return coverage_data

def main():
    print('🔍 Phase 42A-v7e: Week -6 (July 14-20) + July 21st Download')
    print('=' * 60)
    
    try:
        # Step 1: Enumerate expected keys
        expected_keys = enumerate_expected_keys()
        
        # Step 2: Local diff
        missing_keys, diff_data = local_diff(expected_keys)
        
        if not missing_keys:
            print(f"📊 All files already exist locally - no downloads needed")
            return
        
        # Step 3: Dry run LIST/HEAD
        confirmed_files, api_counters = dry_run_list(missing_keys)
        
        # Step 4: Download files
        download_results, api_counters = download_files(confirmed_files, api_counters)
        
        # Step 5: Generate reports
        coverage_data = generate_reports(download_results, api_counters, diff_data)
        
        # Final summary
        successful_downloads = sum(1 for result in download_results if result['download_status'] == 'OK')
        total_expected = len(WEEK_6B_DATES) * len(VENUES)
        coverage_pct = (successful_downloads / total_expected * 100) if total_expected > 0 else 0
        
        print(f"\n📊 **Final Summary:**")
        print(f"   Successful downloads: {successful_downloads}")
        print(f"   Total expected: {total_expected}")
        print(f"   Coverage: {coverage_pct:.1f}%")
        print(f"   API calls used: {api_counters['total_calls']}/{MAX_HTTP_REQUESTS}")
        print(f"   Runtime: {(time.time() - START_TIME) / 60:.1f}m")
        
        # Success criteria check
        if coverage_pct >= 70 and api_counters['total_calls'] <= 80:
            print(f"✅ **Week -6B download succeeded - ready for Week -7 authorization**")
        else:
            print(f"❌ **Week -6B download failed - coverage {coverage_pct:.1f}% < 70% or API calls {api_counters['total_calls']} > 80**")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Final guardrail check
        if not check_guardrails():
            print(f"🚫 Runtime limit exceeded")

if __name__ == '__main__':
    main()
