#!/usr/bin/env python3
"""
October W1-W2 Retry and Coverage Report
Diagnose and recover missing CoinAPI Flat Files for the October W1–W2 extension.
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import pandas as pd
from datetime import datetime, timedelta
import glob

def check_memory_limit():
    """Check memory usage and halt if over 4.5GB"""
    import psutil
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 4500:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 4.5GB limit")
        return False
    return True

def get_expected_files():
    """Generate expected file list for October W1-W2"""
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    expected_files = []
    
    # Date range: 2025-09-22 to 2025-10-06 (15 days)
    start_date = datetime(2025, 9, 22)
    end_date = datetime(2025, 10, 6)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        for venue in venues:
            expected_files.append({
                'venue': venue,
                'date': date_str,
                'filename': f'{venue}_{date_str}_BTCUSDT.csv.gz'
            })
        current_date += timedelta(days=1)
    
    return expected_files

def get_downloaded_files():
    """Get list of actually downloaded files"""
    raw_dir = 'data_v6/raw/coinapi_oct'
    downloaded_files = []
    
    if os.path.exists(raw_dir):
        for file in os.listdir(raw_dir):
            if file.endswith('.csv.gz'):
                # Parse filename: VENUE_YYYYMMDD_BTCUSDT.csv.gz
                parts = file.replace('.csv.gz', '').split('_')
                if len(parts) >= 3:
                    venue = parts[0]
                    date = parts[1]
                    filepath = os.path.join(raw_dir, file)
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    
                    downloaded_files.append({
                        'venue': venue,
                        'date': date,
                        'filename': file,
                        'size_mb': size_mb,
                        'filepath': filepath
                    })
    
    return downloaded_files

def create_status_table():
    """Create status table comparing expected vs downloaded files"""
    print("🔍 **Task 1: Diff Expected vs Downloaded Files**")
    print("=" * 60)
    
    expected_files = get_expected_files()
    downloaded_files = get_downloaded_files()
    
    # Create lookup for downloaded files
    downloaded_lookup = {(f['venue'], f['date']): f for f in downloaded_files}
    
    status_table = []
    
    for expected in expected_files:
        venue = expected['venue']
        date = expected['date']
        filename = expected['filename']
        
        if (venue, date) in downloaded_lookup:
            downloaded = downloaded_lookup[(venue, date)]
            status_table.append({
                'Venue': venue,
                'Date': date,
                'Status': '✅ OK',
                'Local Size (MB)': f"{downloaded['size_mb']:.1f}",
                'Error Type': ''
            })
        else:
            status_table.append({
                'Venue': venue,
                'Date': date,
                'Status': '❌ Missing',
                'Local Size (MB)': '0.0',
                'Error Type': 'Not Downloaded'
            })
    
    # Convert to DataFrame and display
    df = pd.DataFrame(status_table)
    print(df.to_string(index=False))
    
    # Summary counts
    total_expected = len(expected_files)
    total_downloaded = len(downloaded_files)
    missing_count = total_expected - total_downloaded
    
    print(f"\n📊 **Summary:**")
    print(f"📊 Expected: {total_expected} files")
    print(f"📊 Downloaded: {total_downloaded} files")
    print(f"📊 Missing: {missing_count} files")
    print(f"📊 Coverage: {(total_downloaded/total_expected)*100:.1f}%")
    
    return status_table, expected_files, downloaded_files

def retry_missing_downloads(expected_files, downloaded_files):
    """Retry missing downloads with exponential backoff"""
    print(f"\n🔄 **Task 2: Retry Missing Downloads**")
    print("=" * 60)
    
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    raw_dir = 'data_v6/raw/coinapi_oct'
    os.makedirs(raw_dir, exist_ok=True)
    
    # Create lookup for downloaded files
    downloaded_lookup = {(f['venue'], f['date']): f for f in downloaded_files}
    
    # Find missing files
    missing_files = []
    for expected in expected_files:
        venue = expected['venue']
        date = expected['date']
        if (venue, date) not in downloaded_lookup:
            missing_files.append(expected)
    
    print(f"📊 Found {len(missing_files)} missing files to retry")
    
    recovered_count = 0
    permanent_missing = []
    
    for missing in missing_files:
        venue = missing['venue']
        date = missing['date']
        filename = missing['filename']
        
        print(f"🔄 Retrying {venue} {date}...")
        
        # Retry with exponential backoff
        for attempt in range(2):  # Max 2 attempts
            try:
                # List URL pattern
                list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
                
                headers = {
                    'X-CoinAPI-Key': coinapi_key,
                    'User-Agent': 'ACD-Monitor/1.0'
                }
                
                # List objects with longer timeout
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
                        
                        # Use the correct URL pattern
                        full_url = f'https://s3.flatfiles.coinapi.io/coinapi/{key}'
                        
                        # Download the file
                        download_response = requests.get(full_url, headers=headers, timeout=120)
                        
                        if download_response.status_code == 200:
                            # Create filepath
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
                                
                                print(f"✅ Recovered: {filename} ({size:,} bytes, SHA256: {sha256_hash[:8]}...)")
                                recovered_count += 1
                                break  # Success, exit retry loop
                            else:
                                print(f"❌ Size mismatch for {filename}: expected {size}, got {actual_size}")
                                os.remove(filepath)
                        elif download_response.status_code == 404:
                            print(f"❌ Not Found (Provider Gap): {filename}")
                            permanent_missing.append({
                                'venue': venue,
                                'date': date,
                                'filename': filename,
                                'error': 'HTTP 404 - Provider Gap'
                            })
                            break  # Don't retry 404s
                        else:
                            print(f"❌ Download failed for {filename}: {download_response.status_code}")
                    else:
                        print(f"❌ No BTC objects found for {venue} {date}")
                        permanent_missing.append({
                            'venue': venue,
                            'date': date,
                            'filename': filename,
                            'error': 'No BTC Objects'
                        })
                        break  # Don't retry if no objects found
                elif response.status_code == 404:
                    print(f"❌ Not Found (Provider Gap): {filename}")
                    permanent_missing.append({
                        'venue': venue,
                        'date': date,
                        'filename': filename,
                        'error': 'HTTP 404 - Provider Gap'
                    })
                    break  # Don't retry 404s
                else:
                    print(f"❌ List failed for {venue} {date}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error processing {venue} {date}: {str(e)}")
                
                if attempt == 0:  # First attempt failed
                    print(f"⏳ Retrying in 60 seconds...")
                    time.sleep(60)
                elif attempt == 1:  # Second attempt failed
                    print(f"⏳ Final retry in 120 seconds...")
                    time.sleep(120)
                else:
                    # All attempts failed
                    permanent_missing.append({
                        'venue': venue,
                        'date': date,
                        'filename': filename,
                        'error': str(e)
                    })
                    break
    
    print(f"\n📊 **Retry Summary:**")
    print(f"📊 Recovered: {recovered_count} files")
    print(f"📊 Permanent Missing: {len(permanent_missing)} files")
    
    return recovered_count, permanent_missing

def post_retry_coverage_summary():
    """Generate post-retry coverage summary"""
    print(f"\n📊 **Task 3: Post-Retry Coverage Summary**")
    print("=" * 60)
    
    expected_files = get_expected_files()
    downloaded_files = get_downloaded_files()
    
    # Count by venue
    venue_summary = []
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    for venue in venues:
        expected_count = len([f for f in expected_files if f['venue'] == venue])
        downloaded_count = len([f for f in downloaded_files if f['venue'] == venue])
        
        venue_summary.append({
            'Venue': venue,
            'Expected': expected_count,
            'Downloaded': downloaded_count,
            'Recovered': 0,  # We'll update this if we track recoveries
            'Permanent Missing': expected_count - downloaded_count
        })
    
    df = pd.DataFrame(venue_summary)
    print(df.to_string(index=False))
    
    total_expected = len(expected_files)
    total_downloaded = len(downloaded_files)
    coverage_pct = (total_downloaded / total_expected) * 100
    
    print(f"\n📊 **Overall Coverage:**")
    print(f"📊 Total Expected: {total_expected}")
    print(f"📊 Total Downloaded: {total_downloaded}")
    print(f"📊 Coverage: {coverage_pct:.1f}%")
    
    return venue_summary, coverage_pct

def gap_diagnostics():
    """Identify clustered vs isolated gaps"""
    print(f"\n🔍 **Task 4: Gap Diagnostics**")
    print("=" * 60)
    
    expected_files = get_expected_files()
    downloaded_files = get_downloaded_files()
    
    # Create lookup for downloaded files
    downloaded_lookup = {(f['venue'], f['date']): f for f in downloaded_files}
    
    # Find missing files by venue
    missing_by_venue = {}
    for expected in expected_files:
        venue = expected['venue']
        date = expected['date']
        if (venue, date) not in downloaded_lookup:
            if venue not in missing_by_venue:
                missing_by_venue[venue] = []
            missing_by_venue[venue].append(date)
    
    # Check for clustered gaps
    clustered_gaps = []
    isolated_gaps = []
    
    for venue, missing_dates in missing_by_venue.items():
        if len(missing_dates) >= 2:
            # Sort dates and check for adjacency
            missing_dates.sort()
            for i in range(len(missing_dates) - 1):
                date1 = datetime.strptime(missing_dates[i], '%Y%m%d')
                date2 = datetime.strptime(missing_dates[i + 1], '%Y%m%d')
                if (date2 - date1).days == 1:  # Adjacent days
                    clustered_gaps.append({
                        'venue': venue,
                        'start_date': missing_dates[i],
                        'end_date': missing_dates[i + 1]
                    })
        
        if len(missing_dates) == 1:
            isolated_gaps.append({
                'venue': venue,
                'date': missing_dates[0]
            })
    
    print(f"📊 **Gap Analysis:**")
    print(f"📊 Clustered Gaps: {len(clustered_gaps)}")
    print(f"📊 Isolated Gaps: {len(isolated_gaps)}")
    
    if clustered_gaps:
        print(f"⚠️ Clustered gap detected → potential RRI bias risk")
        for gap in clustered_gaps:
            print(f"   {gap['venue']}: {gap['start_date']} → {gap['end_date']}")
    else:
        print(f"✅ No clustered gaps detected")
    
    return clustered_gaps, isolated_gaps

def final_verification():
    """Compute final coverage and checksums"""
    print(f"\n✅ **Task 5: Final Verification**")
    print("=" * 60)
    
    expected_files = get_expected_files()
    downloaded_files = get_downloaded_files()
    
    # Compute total compressed size
    total_size_gb = sum(f['size_mb'] for f in downloaded_files) / 1024
    
    # Compute SHA-256 checksum of filenames + sizes
    checksum_data = []
    for f in downloaded_files:
        checksum_data.append(f"{f['filename']}:{f['size_mb']:.1f}")
    
    checksum_data.sort()
    checksum_string = "|".join(checksum_data)
    checksum_hash = hashlib.sha256(checksum_string.encode()).hexdigest()
    
    # Coverage calculation
    coverage_pct = (len(downloaded_files) / len(expected_files)) * 100
    
    print(f"📊 **Final Statistics:**")
    print(f"📊 Total Compressed Size: {total_size_gb:.2f} GB")
    print(f"📊 Files Checksum: {checksum_hash[:16]}...")
    print(f"📊 Coverage: {coverage_pct:.1f}% ({len(downloaded_files)}/{len(expected_files)} files)")
    
    # Final summary
    if coverage_pct >= 95:
        print(f"✅ Coverage: {coverage_pct:.1f}% ({len(downloaded_files)}/{len(expected_files)} files). Ready for beacon processing.")
    else:
        print(f"⚠️ Coverage: {coverage_pct:.1f}% ({len(downloaded_files)}/{len(expected_files)} files). Below 95% threshold.")
    
    return coverage_pct, total_size_gb, checksum_hash

def main():
    print('🔍 October W1-W2 Retry and Coverage Report')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Task 1: Diff expected vs downloaded files
    status_table, expected_files, downloaded_files = create_status_table()
    
    # Task 2: Retry missing downloads
    recovered_count, permanent_missing = retry_missing_downloads(expected_files, downloaded_files)
    
    # Refresh downloaded files list after retries
    downloaded_files = get_downloaded_files()
    
    # Task 3: Post-retry coverage summary
    venue_summary, coverage_pct = post_retry_coverage_summary()
    
    # Task 4: Gap diagnostics
    clustered_gaps, isolated_gaps = gap_diagnostics()
    
    # Task 5: Final verification
    final_coverage, total_size_gb, checksum_hash = final_verification()
    
    # Check guardrails
    if final_coverage < 95:
        print(f"\n❌ HALT: Coverage {final_coverage:.1f}% is below 95% threshold")
        print(f"❌ Permanent gaps remain > 5%. Cannot proceed with feature extraction.")
        return
    
    print(f"\n✅ All tasks completed successfully!")
    print(f"✅ Ready to proceed with beacon processing.")

if __name__ == '__main__':
    main()
