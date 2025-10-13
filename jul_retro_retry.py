#!/usr/bin/env python3
"""
July W-5 & W-6 Retro Retry - Recover Aug 03-04 gaps
Target: 7 missing files to achieve ≥95% coverage (goal 100%)
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import random
import json
import pandas as pd
from datetime import datetime, timedelta

def check_memory_limit():
    """Check memory usage and halt if over 2.0GB"""
    import psutil
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 2000:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 2.0GB limit")
        return False
    print(f"📊 Memory usage: {current_mb:.1f} MB")
    return True

def build_expected_list():
    """Build expected list of 56 files (14 days × 4 venues)"""
    print("🔍 **Step 1: Build Expected List**")
    print("=" * 60)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    start_date = datetime(2025, 7, 22)
    end_date = datetime(2025, 8, 4)
    
    expected_files = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        for venue in venues:
            expected_files.append({
                'date': date_str,
                'venue': venue,
                'prefix': f'T-TRADES/D-{date_str}/E-{venue}/',
                'expected_path': f'data_v6/raw/coinapi_jul_aug/D-{date_str}/E-{venue}/'
            })
        current_date += timedelta(days=1)
    
    print(f"📊 Expected files: {len(expected_files)} (14 days × 4 venues)")
    
    # Save to logs
    os.makedirs('logs', exist_ok=True)
    with open('logs/coinapi_jul_aug_expected.jsonl', 'w') as f:
        for item in expected_files:
            f.write(json.dumps(item) + '\n')
    
    return expected_files

def diff_actual_vs_expected(expected_files):
    """Diff actual vs expected to find missing files"""
    print(f"\n🔍 **Step 2: Diff Actual vs Expected**")
    print("=" * 60)
    
    missing_files = []
    existing_files = []
    
    for expected in expected_files:
        # Check if file exists in the original location
        original_path = f"data_v6/raw/coinapi_jul/{expected['venue']}_{expected['date']}_BTCUSDT.csv.gz"
        
        if os.path.exists(original_path):
            existing_files.append(expected)
        else:
            missing_files.append(expected)
    
    print(f"📊 Existing files: {len(existing_files)}")
    print(f"📊 Missing files: {len(missing_files)}")
    
    # Save missing files to logs
    with open('logs/coinapi_jul_aug_missing_initial.jsonl', 'w') as f:
        for item in missing_files:
            f.write(json.dumps(item) + '\n')
    
    # Confirm we have exactly the 7 expected missing files
    expected_missing = [
        ('20250803', 'COINBASE'),
        ('20250803', 'BYBITSPOT'), 
        ('20250803', 'BITGET'),
        ('20250804', 'BINANCE'),
        ('20250804', 'COINBASE'),
        ('20250804', 'BYBITSPOT'),
        ('20250804', 'BITGET')
    ]
    
    actual_missing = [(item['date'], item['venue']) for item in missing_files]
    
    print(f"📊 Expected missing: {expected_missing}")
    print(f"📊 Actual missing: {actual_missing}")
    
    if set(actual_missing) == set(expected_missing):
        print(f"✅ Missing files match expected 7 files")
    else:
        print(f"⚠️ Missing files don't match expected - proceeding anyway")
    
    return missing_files

def download_with_advanced_retry(missing_file, coinapi_key, attempt_num):
    """Download with advanced retry logic and backoff"""
    date = missing_file['date']
    venue = missing_file['venue']
    prefix = missing_file['prefix']
    
    # Backoff schedule: 90, 150, 240, 360, 540, 780, 1080, 1440 seconds
    backoff_schedule = [90, 150, 240, 360, 540, 780, 1080, 1440]
    delay = backoff_schedule[min(attempt_num - 1, len(backoff_schedule) - 1)]
    
    # Add jitter (±15 seconds)
    jitter = random.uniform(-15, 15)
    actual_delay = max(0, delay + jitter)
    
    print(f"📊 Attempt {attempt_num} for {venue} {date} (delay: {actual_delay:.1f}s)")
    
    if attempt_num > 1:
        time.sleep(actual_delay)
    
    list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix={prefix}'
    
    try:
        headers = {
            'X-CoinAPI-Key': coinapi_key,
            'User-Agent': 'acd-monitor/39B-retro-retry',
            'Accept': 'application/octet-stream'
        }
        
        # List objects with 180s timeout
        response = requests.get(list_url, headers=headers, timeout=180)
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            # Find BTC-related objects
            btc_objects = []
            for content in root.findall('.//Contents'):
                key = content.find('Key').text
                size = int(content.find('Size').text)
                
                if 'BTC' in key.upper() and ('USDT' in key.upper() or 'USD' in key.upper()):
                    btc_objects.append((key, size))
            
            if btc_objects:
                # Get the largest BTC object
                largest_obj = max(btc_objects, key=lambda x: x[1])
                key, size = largest_obj
                
                # Use the correct URL pattern
                full_url = f'https://s3.flatfiles.coinapi.io/coinapi/{key}'
                
                # Download the file
                download_response = requests.get(full_url, headers=headers, timeout=180)
                
                if download_response.status_code == 200:
                    # Create directory structure
                    target_dir = f"data_v6/raw/coinapi_jul_aug/D-{date}/E-{venue}"
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Create filename
                    filename = f'{venue}_{date}_BTCUSDT.csv.gz'
                    filepath = os.path.join(target_dir, filename)
                    
                    # Also save to original location for consistency
                    original_path = f"data_v6/raw/coinapi_jul/{filename}"
                    
                    # Save to both locations
                    with open(filepath, 'wb') as f:
                        f.write(download_response.content)
                    with open(original_path, 'wb') as f:
                        f.write(download_response.content)
                    
                    # Verify file size
                    actual_size = os.path.getsize(original_path)
                    if actual_size == size:
                        # Compute SHA256
                        with open(original_path, 'rb') as f:
                            sha256_hash = hashlib.sha256(f.read()).hexdigest()
                        
                        # Log to SHA256 file
                        os.makedirs('logs', exist_ok=True)
                        with open('logs/sha256_jul_aug.csv', 'a') as f:
                            f.write(f"{original_path},{actual_size},{sha256_hash}\n")
                        
                        return {
                            'status': 'SUCCESS',
                            'filename': filename,
                            'size': size,
                            'sha256': sha256_hash,
                            'attempt': attempt_num
                        }
                    else:
                        print(f"❌ Size mismatch: expected {size}, got {actual_size}")
                        os.remove(filepath)
                        os.remove(original_path)
                        return {
                            'status': 'SIZE_MISMATCH',
                            'error': f'Size mismatch: expected {size}, got {actual_size}',
                            'attempt': attempt_num
                        }
                elif download_response.status_code == 404:
                    return {
                        'status': 'PERMANENT_MISSING',
                        'error': 'HTTP 404 - Provider Gap',
                        'attempt': attempt_num
                    }
                else:
                    return {
                        'status': 'DOWNLOAD_FAILED',
                        'error': f'HTTP {download_response.status_code}',
                        'attempt': attempt_num
                    }
            else:
                return {
                    'status': 'NO_BTC_OBJECTS',
                    'error': 'No BTC objects found',
                    'attempt': attempt_num
                }
        elif response.status_code == 404:
            return {
                'status': 'PERMANENT_MISSING',
                'error': 'HTTP 404 - Provider Gap',
                'attempt': attempt_num
            }
        elif response.status_code in [403, 429]:
            return {
                'status': 'RATE_LIMITED',
                'error': f'HTTP {response.status_code} - Rate Limited',
                'attempt': attempt_num
            }
        else:
            return {
                'status': 'LIST_FAILED',
                'error': f'HTTP {response.status_code}',
                'attempt': attempt_num
            }
            
    except Exception as e:
        return {
            'status': 'EXCEPTION',
            'error': str(e),
            'attempt': attempt_num
        }

def retry_missing_files(missing_files):
    """Retry loop for missing files"""
    print(f"\n🔍 **Step 3: Retry Loop**")
    print("=" * 60)
    
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    max_attempts = 8
    
    # Rotate order: [COINBASE, BYBITSPOT, BITGET, BINANCE]
    venue_order = ['COINBASE', 'BYBITSPOT', 'BITGET', 'BINANCE']
    
    retry_results = []
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n📊 **Attempt {attempt}/{max_attempts}**")
        
        # Rotate venue order
        rotated_missing = []
        for venue in venue_order:
            for missing in missing_files:
                if missing['venue'] == venue and missing not in [r['file'] for r in retry_results if r['status'] == 'SUCCESS']:
                    rotated_missing.append(missing)
        
        if not rotated_missing:
            print(f"✅ All files recovered!")
            break
        
        print(f"📊 Retrying {len(rotated_missing)} files...")
        
        for missing_file in rotated_missing:
            result = download_with_advanced_retry(missing_file, coinapi_key, attempt)
            result['file'] = missing_file
            retry_results.append(result)
            
            if result['status'] == 'SUCCESS':
                print(f"✅ {missing_file['venue']} {missing_file['date']}: {result['filename']} ({result['size']:,} bytes)")
            elif result['status'] == 'PERMANENT_MISSING':
                print(f"❌ {missing_file['venue']} {missing_file['date']}: PERMANENT MISSING")
            else:
                print(f"⏳ {missing_file['venue']} {missing_file['date']}: {result['status']} - {result.get('error', '')}")
    
    return retry_results

def coverage_check():
    """Post-retry coverage check"""
    print(f"\n🔍 **Step 4: Coverage Check**")
    print("=" * 60)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    start_date = datetime(2025, 7, 22)
    end_date = datetime(2025, 8, 4)
    
    coverage_data = []
    total_expected = 0
    total_downloaded = 0
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        for venue in venues:
            filename = f'{venue}_{date_str}_BTCUSDT.csv.gz'
            filepath = f"data_v6/raw/coinapi_jul/{filename}"
            
            exists = os.path.exists(filepath)
            status = "✅" if exists else "❌"
            
            coverage_data.append({
                'Date': date_display,
                'Venue': venue,
                'Status': status,
                'File': filename
            })
            
            total_expected += 1
            if exists:
                total_downloaded += 1
        
        current_date += timedelta(days=1)
    
    coverage_df = pd.DataFrame(coverage_data)
    coverage_pct = (total_downloaded / total_expected) * 100
    
    print(f"📊 **Coverage Table (Day × Venue):**")
    print(coverage_df.to_string(index=False))
    
    print(f"\n📊 **Coverage Summary:**")
    print(f"📊 Total expected: {total_expected}")
    print(f"📊 Total downloaded: {total_downloaded}")
    print(f"📊 Coverage: {coverage_pct:.1f}%")
    
    return coverage_df, coverage_pct, total_expected, total_downloaded

def main():
    print('🔍 July W-5 & W-6 Retro Retry - Recover Aug 03-04 gaps')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Step 1: Build expected list
    expected_files = build_expected_list()
    
    # Step 2: Diff actual vs expected
    missing_files = diff_actual_vs_expected(expected_files)
    
    if not missing_files:
        print(f"✅ No missing files - coverage already 100%")
        coverage_check()
        return
    
    # Step 3: Retry missing files
    retry_results = retry_missing_files(missing_files)
    
    # Step 4: Coverage check
    coverage_df, coverage_pct, total_expected, total_downloaded = coverage_check()
    
    # Final assessment
    if coverage_pct >= 95:
        print(f"\n✅ **39B-Retro-Retry COMPLETE — coverage {total_downloaded}/{total_expected} ({coverage_pct:.1f}%)**")
        
        # Show missing files (if any)
        missing_after_retry = coverage_df[coverage_df['Status'] == '❌']
        if len(missing_after_retry) > 0:
            print(f"\n📊 **Missing after retries ({len(missing_after_retry)}):**")
            for _, row in missing_after_retry.iterrows():
                print(f"   {row['Date']} {row['Venue']}")
    else:
        print(f"\n❌ **HALT: Coverage {coverage_pct:.1f}% below 95% threshold**")
        
        # Show missing files
        missing_after_retry = coverage_df[coverage_df['Status'] == '❌']
        print(f"\n📊 **Missing files ({len(missing_after_retry)}):**")
        for _, row in missing_after_retry.iterrows():
            print(f"   {row['Date']} {row['Venue']}")

if __name__ == '__main__':
    main()
