#!/usr/bin/env python3
"""
Download missing October 7-14 data to complete the October W1-W2 window.
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
from datetime import datetime, timedelta

def download_missing_october_data():
    """Download missing October 7-14 data"""
    print('🔍 Downloading Missing October 7-14 Data')
    print('=' * 60)
    
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Missing dates: October 7-14, 2025
    missing_dates = []
    start_date = datetime(2025, 10, 7)
    end_date = datetime(2025, 10, 14)
    
    current_date = start_date
    while current_date <= end_date:
        missing_dates.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    
    print(f'📊 Missing dates: {missing_dates}')
    print(f'📊 Venues: {venues}')
    print(f'📊 Total files to download: {len(missing_dates) * len(venues)}')
    
    # Create directory
    raw_dir = 'data_v6/raw/coinapi_oct'
    os.makedirs(raw_dir, exist_ok=True)
    
    download_results = []
    
    for date in missing_dates:
        for venue in venues:
            print(f'📊 Downloading {venue} {date}...')
            
            # List URL pattern
            list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
            
            retry_count = 0
            max_retries = 3
            
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
                                    
                                    download_results.append({
                                        'date': date,
                                        'venue': venue,
                                        'filename': filename,
                                        'size': size,
                                        'sha256': sha256_hash,
                                        'status': 'SUCCESS'
                                    })
                                    
                                    print(f'✅ {filename}: {size:,} bytes, SHA256: {sha256_hash[:8]}...')
                                    break  # Success, exit retry loop
                                else:
                                    print(f'❌ Size mismatch for {filename}: expected {size}, got {actual_size}')
                                    os.remove(filepath)
                            elif download_response.status_code == 404:
                                print(f'❌ Not Found (Provider Gap): {venue} {date}')
                                download_results.append({
                                    'date': date,
                                    'venue': venue,
                                    'filename': 'N/A',
                                    'size': 0,
                                    'sha256': 'N/A',
                                    'status': 'NOT_FOUND'
                                })
                                break  # Don't retry 404s
                            else:
                                print(f'❌ Download failed for {venue} {date}: {download_response.status_code}')
                        else:
                            print(f'❌ No BTC objects found for {venue} {date}')
                            download_results.append({
                                'date': date,
                                'venue': venue,
                                'filename': 'N/A',
                                'size': 0,
                                'sha256': 'N/A',
                                'status': 'NO_BTC_OBJECTS'
                            })
                    elif response.status_code == 404:
                        print(f'❌ Not Found (Provider Gap): {venue} {date}')
                        download_results.append({
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'size': 0,
                            'sha256': 'N/A',
                            'status': 'NOT_FOUND'
                        })
                        break  # Don't retry 404s
                    else:
                        print(f'❌ List failed for {venue} {date}: {response.status_code}')
                        
                except Exception as e:
                    print(f'❌ Error processing {venue} {date}: {str(e)}')
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f'⏳ Retrying {retry_count}/{max_retries}...')
                        time.sleep(60)
                    else:
                        download_results.append({
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'size': 0,
                            'sha256': 'N/A',
                            'status': 'FAILED'
                        })
                        break
    
    # Summary
    total_attempted = len(download_results)
    successful = sum(1 for r in download_results if r['status'] == 'SUCCESS')
    not_found = sum(1 for r in download_results if r['status'] == 'NOT_FOUND')
    failed = sum(1 for r in download_results if r['status'] == 'FAILED')
    
    print(f'\n📊 **Download Summary:**')
    print(f'📊 Total attempted: {total_attempted}')
    print(f'📊 Successful: {successful}')
    print(f'📊 Not Found: {not_found}')
    print(f'📊 Failed: {failed}')
    
    if successful == total_attempted:
        print(f'✅ All missing files downloaded successfully!')
        return True
    else:
        print(f'⚠️ Some files could not be downloaded')
        return False

if __name__ == '__main__':
    download_missing_october_data()
