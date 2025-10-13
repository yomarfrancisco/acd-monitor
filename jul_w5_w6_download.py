#!/usr/bin/env python3
"""
July W-5 & W-6 Download (July 22 - August 4, 2025)
Download and checksum all raw trade files from CoinAPI Flat-File S3.
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import pandas as pd
from datetime import datetime, timedelta

def check_memory_limit():
    """Check memory usage and halt if over 3.5GB"""
    import psutil
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 3500:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 3.5GB limit")
        return False
    print(f"📊 Memory usage: {current_mb:.1f} MB")
    return True

def build_daily_prefixes():
    """Build daily prefixes for July 22 - August 4, 2025"""
    print("🔍 **Step 1: Build Daily Prefixes**")
    print("=" * 60)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Date range: July 22 - August 4, 2025 (inclusive)
    start_date = datetime(2025, 7, 22)
    end_date = datetime(2025, 8, 4)
    
    prefixes = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        for venue in venues:
            prefixes.append({
                'date': date_str,
                'venue': venue,
                'prefix': f'T-TRADES/D-{date_str}/E-{venue}/'
            })
        current_date += timedelta(days=1)
    
    print(f"📊 Date range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Total prefixes: {len(prefixes)} (14 days × 4 venues)")
    
    return prefixes

def download_with_retry(prefix_info, coinapi_key, raw_dir):
    """Download file with exponential backoff retry"""
    date = prefix_info['date']
    venue = prefix_info['venue']
    prefix = prefix_info['prefix']
    
    list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix={prefix}'
    
    retry_count = 0
    max_retries = 3
    retry_delays = [60, 120]  # 60s, then 120s
    
    while retry_count < max_retries:
        try:
            headers = {
                'X-CoinAPI-Key': coinapi_key,
                'User-Agent': 'ACD-Monitor/1.0'
            }
            
            # List objects
            response = requests.get(list_url, headers=headers, timeout=120)
            
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
                    
                    # Check if file is large enough (> 1 MB)
                    if size < 1024 * 1024:  # Less than 1 MB
                        return {
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'size': size,
                            'sha256': 'N/A',
                            'status': 'FILE_TOO_SMALL',
                            'error': f'File size {size} < 1MB'
                        }
                    
                    # Use the correct URL pattern
                    full_url = f'https://s3.flatfiles.coinapi.io/coinapi/{key}'
                    
                    # Download the file
                    download_response = requests.get(full_url, headers=headers, timeout=120)
                    
                    if download_response.status_code == 200:
                        # Create filename
                        filename = f'{venue}_{date}_BTCUSDT.csv.gz'
                        filepath = os.path.join(raw_dir, filename)
                        
                        # Save to file
                        with open(filepath, 'wb') as f:
                            f.write(download_response.content)
                        
                        # Verify file size
                        actual_size = os.path.getsize(filepath)
                        if actual_size == size:
                            # Compute SHA256
                            with open(filepath, 'rb') as f:
                                sha256_hash = hashlib.sha256(f.read()).hexdigest()
                            
                            return {
                                'date': date,
                                'venue': venue,
                                'filename': filename,
                                'size': size,
                                'sha256': sha256_hash,
                                'status': 'SUCCESS'
                            }
                        else:
                            print(f"❌ Size mismatch for {filename}: expected {size}, got {actual_size}")
                            os.remove(filepath)
                            return {
                                'date': date,
                                'venue': venue,
                                'filename': filename,
                                'size': size,
                                'sha256': 'N/A',
                                'status': 'SIZE_MISMATCH',
                                'error': f'Size mismatch: expected {size}, got {actual_size}'
                            }
                    elif download_response.status_code == 404:
                        return {
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'size': 0,
                            'sha256': 'N/A',
                            'status': 'NOT_FOUND',
                            'error': 'HTTP 404 - Provider Gap'
                        }
                    else:
                        print(f"❌ Download failed for {venue} {date}: {download_response.status_code}")
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            delay = retry_delays[min(retry_count - 1, len(retry_delays) - 1)]
                            print(f"⏳ Retrying in {delay}s...")
                            time.sleep(delay)
                            continue
                        else:
                            return {
                                'date': date,
                                'venue': venue,
                                'filename': 'N/A',
                                'size': 0,
                                'sha256': 'N/A',
                                'status': 'DOWNLOAD_FAILED',
                                'error': f'HTTP {download_response.status_code}'
                            }
                else:
                    return {
                        'date': date,
                        'venue': venue,
                        'filename': 'N/A',
                        'size': 0,
                        'sha256': 'N/A',
                        'status': 'NO_BTC_OBJECTS',
                        'error': 'No BTC objects found'
                    }
            elif response.status_code == 404:
                return {
                    'date': date,
                    'venue': venue,
                    'filename': 'N/A',
                    'size': 0,
                    'sha256': 'N/A',
                    'status': 'NOT_FOUND',
                    'error': 'HTTP 404 - Provider Gap'
                }
            else:
                print(f"❌ List failed for {venue} {date}: {response.status_code}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    delay = retry_delays[min(retry_count - 1, len(retry_delays) - 1)]
                    print(f"⏳ Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        'date': date,
                        'venue': venue,
                        'filename': 'N/A',
                        'size': 0,
                        'sha256': 'N/A',
                        'status': 'LIST_FAILED',
                        'error': f'HTTP {response.status_code}'
                    }
                    
        except Exception as e:
            print(f"❌ Error processing {venue} {date}: {str(e)}")
            if retry_count < max_retries - 1:
                retry_count += 1
                delay = retry_delays[min(retry_count - 1, len(retry_delays) - 1)]
                print(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)
                continue
            else:
                return {
                    'date': date,
                    'venue': venue,
                    'filename': 'N/A',
                    'size': 0,
                    'sha256': 'N/A',
                    'status': 'EXCEPTION',
                    'error': str(e)
                }
    
    return {
        'date': date,
        'venue': venue,
        'filename': 'N/A',
        'size': 0,
        'sha256': 'N/A',
        'status': 'MAX_RETRIES_EXCEEDED',
        'error': 'Max retries exceeded'
    }

def download_all_files():
    """Download all files for July W-5 & W-6"""
    print("🔍 **Step 2: Download All Files**")
    print("=" * 60)
    
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    
    # Create directory
    raw_dir = 'data_v6/raw/coinapi_jul'
    os.makedirs(raw_dir, exist_ok=True)
    
    # Get all prefixes
    prefixes = build_daily_prefixes()
    
    download_results = []
    
    for i, prefix_info in enumerate(prefixes, 1):
        print(f"📊 [{i}/{len(prefixes)}] Downloading {prefix_info['venue']} {prefix_info['date']}...")
        
        result = download_with_retry(prefix_info, coinapi_key, raw_dir)
        download_results.append(result)
        
        if result['status'] == 'SUCCESS':
            print(f"✅ {result['filename']}: {result['size']:,} bytes, SHA256: {result['sha256'][:8]}...")
        else:
            print(f"❌ {result['status']}: {result.get('error', 'Unknown error')}")
    
    return download_results

def validate_coverage(download_results):
    """Validate coverage and report results"""
    print(f"\n🔍 **Step 3: Validate Coverage**")
    print("=" * 60)
    
    # Expected: 14 days × 4 venues = 56 files
    expected_files = 14 * 4
    actual_files = len(download_results)
    successful_files = sum(1 for r in download_results if r['status'] == 'SUCCESS')
    
    print(f"📊 Expected files: {expected_files}")
    print(f"📊 Actual files: {actual_files}")
    print(f"📊 Successful downloads: {successful_files}")
    
    coverage_pct = (successful_files / expected_files) * 100
    print(f"📊 Coverage: {coverage_pct:.1f}%")
    
    if coverage_pct < 95:
        print(f"❌ HALT: Coverage {coverage_pct:.1f}% is below 95% threshold")
        return False, download_results
    
    print(f"✅ Coverage {coverage_pct:.1f}% meets 95% threshold")
    return True, download_results

def generate_summary_report(download_results):
    """Generate summary report"""
    print(f"\n🔍 **Step 4: Summary Report**")
    print("=" * 60)
    
    # Coverage table
    coverage_data = []
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    for venue in venues:
        venue_results = [r for r in download_results if r['venue'] == venue]
        successful = sum(1 for r in venue_results if r['status'] == 'SUCCESS')
        total = len(venue_results)
        coverage_pct = (successful / total) * 100 if total > 0 else 0
        
        coverage_data.append({
            'Venue': venue,
            'Successful': successful,
            'Total': total,
            'Coverage %': f"{coverage_pct:.1f}%"
        })
    
    coverage_df = pd.DataFrame(coverage_data)
    print(f"📊 **Coverage by Venue:**")
    print(coverage_df.to_string(index=False))
    
    # Failed downloads
    failed_results = [r for r in download_results if r['status'] != 'SUCCESS']
    if failed_results:
        print(f"\n📊 **Failed Downloads ({len(failed_results)}):**")
        for result in failed_results:
            print(f"   {result['venue']} {result['date']}: {result['status']} - {result.get('error', '')}")
    
    # Total size and SHA-256 summary
    successful_results = [r for r in download_results if r['status'] == 'SUCCESS']
    total_size_gb = sum(r['size'] for r in successful_results) / (1024**3)
    
    print(f"\n📊 **Download Summary:**")
    print(f"📊 Total files downloaded: {len(successful_results)}")
    print(f"📊 Total size: {total_size_gb:.2f} GB")
    
    # SHA-256 hashes
    print(f"\n📊 **SHA-256 Hashes:**")
    for result in successful_results[:10]:  # Show first 10
        print(f"   {result['filename']}: {result['sha256']}")
    if len(successful_results) > 10:
        print(f"   ... and {len(successful_results) - 10} more files")
    
    return coverage_df, total_size_gb

def main():
    print('🔍 July W-5 & W-6 Download (July 22 - August 4, 2025)')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Download all files
    download_results = download_all_files()
    
    # Validate coverage
    coverage_ok, download_results = validate_coverage(download_results)
    if not coverage_ok:
        return
    
    # Generate summary report
    coverage_df, total_size_gb = generate_summary_report(download_results)
    
    print(f"\n✅ **Download completed successfully!**")
    print(f"✅ Coverage: {len([r for r in download_results if r['status'] == 'SUCCESS'])}/{len(download_results)} files")
    print(f"✅ Total size: {total_size_gb:.2f} GB")
    print(f"✅ Files saved to: data_v6/raw/coinapi_jul/")

if __name__ == '__main__':
    main()
