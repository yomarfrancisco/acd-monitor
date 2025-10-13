#!/usr/bin/env python3
"""
October W1-W2 Download and Processing
Extends canonical beacon panel by two additional weeks (2025-09-22 → 2025-10-06 UTC)
using CoinAPI Flat Files trades.
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import gzip
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
from io import StringIO
import time
import psutil

def check_memory_limit():
    """Check memory usage and halt if over 4.5GB"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 4500:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 4.5GB limit")
        return False
    return True

def main():
    print('🔍 October W1-W2 Execution: Download, Process, Normalize')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Set API key
    coinapi_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    
    # October W1-W2 dates and venues
    oct_dates = []
    start_date = datetime(2025, 9, 22)
    end_date = datetime(2025, 10, 6)
    
    current_date = start_date
    while current_date <= end_date:
        oct_dates.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f'📊 **October W1-W2 Scope:**')
    print(f'📊 Dates: {len(oct_dates)} days from {oct_dates[0]} to {oct_dates[-1]}')
    print(f'📊 Venues: {venues}')
    print(f'📊 Expected hours: {len(oct_dates) * 24} = {len(oct_dates) * 24 * len(venues)} venue-hours')
    
    # Create directories
    raw_dir = 'data_v6/raw/coinapi_oct'
    os.makedirs(raw_dir, exist_ok=True)
    
    # Results tables
    download_results = []
    
    print(f'\n📊 **Download Phase:**')
    
    # Download all files for the date range
    for date in oct_dates:
        for venue in venues:
            print(f'📊 Downloading {date} {venue}...')
            
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
                    response = requests.get(list_url, headers=headers, timeout=10)
                    
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
                            download_response = requests.get(full_url, headers=headers, timeout=30)
                            
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
                                        'url': full_url,
                                        'http_status': download_response.status_code,
                                        'content_length': size,
                                        'sha256': sha256_hash,
                                        'status': 'SUCCESS'
                                    })
                                    
                                    print(f'📊 {filename}: {size:,} bytes, SHA256: {sha256_hash[:8]}...')
                                    break  # Success, exit retry loop
                                else:
                                    print(f'📊 Size mismatch for {filename}: expected {size}, got {actual_size}')
                                    os.remove(filepath)
                                    download_results.append({
                                        'date': date,
                                        'venue': venue,
                                        'filename': filename,
                                        'url': full_url,
                                        'http_status': download_response.status_code,
                                        'content_length': size,
                                        'sha256': 'N/A',
                                        'status': 'SIZE_MISMATCH'
                                    })
                            elif download_response.status_code in [403, 429]:
                                print(f'📊 Rate limited for {date} {venue}: {download_response.status_code}, sleeping 60s...')
                                time.sleep(60)
                                retry_count += 1
                                continue
                            else:
                                print(f'📊 Download failed for {date} {venue}: {download_response.status_code}')
                                download_results.append({
                                    'date': date,
                                    'venue': venue,
                                    'filename': 'N/A',
                                    'url': full_url,
                                    'http_status': download_response.status_code,
                                    'content_length': 0,
                                    'sha256': 'N/A',
                                    'status': f'DOWNLOAD_ERROR_{download_response.status_code}'
                                })
                        else:
                            print(f'📊 No BTC objects found for {date} {venue}')
                            download_results.append({
                                'date': date,
                                'venue': venue,
                                'filename': 'N/A',
                                'url': 'N/A',
                                'http_status': 200,
                                'content_length': 0,
                                'sha256': 'N/A',
                                'status': 'NO_BTC_OBJECTS'
                            })
                    elif response.status_code in [403, 429]:
                        print(f'📊 Rate limited for {date} {venue}: {response.status_code}, sleeping 60s...')
                        time.sleep(60)
                        retry_count += 1
                        continue
                    else:
                        print(f'📊 List failed for {date} {venue}: {response.status_code}')
                        download_results.append({
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'url': 'N/A',
                            'http_status': response.status_code,
                            'content_length': 0,
                            'sha256': 'N/A',
                            'status': f'LIST_ERROR_{response.status_code}'
                        })
                        break  # Exit retry loop for non-rate-limit errors
                        
                except Exception as e:
                    print(f'📊 Error processing {date} {venue}: {str(e)}')
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f'📊 Retrying {retry_count}/{max_retries}...')
                        time.sleep(10)
                    else:
                        download_results.append({
                            'date': date,
                            'venue': venue,
                            'filename': 'N/A',
                            'url': 'N/A',
                            'http_status': 0,
                            'content_length': 0,
                            'sha256': 'N/A',
                            'status': 'EXCEPTION',
                            'error': str(e)
                        })
                        break
    
    print(f'\n📊 **Download Summary:**')
    print(f'📊 Total attempted: {len(download_results)}')
    print(f'📊 Success: {sum(1 for r in download_results if r["status"] == "SUCCESS")}')
    print(f'📊 Error: {sum(1 for r in download_results if r["status"] != "SUCCESS")}')
    
    # Save download results
    download_df = pd.DataFrame(download_results)
    download_df.to_csv('oct_download_results.csv', index=False)
    
    print(f'\n✅ Download phase completed')
    print(f'📁 Raw data stored in: {raw_dir}')
    print(f'📊 Download results saved to: oct_download_results.csv')

if __name__ == '__main__':
    main()
