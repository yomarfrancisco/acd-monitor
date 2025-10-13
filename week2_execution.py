#!/usr/bin/env python3
"""
Week-2 Execution (2025-08-08 → 2025-08-14)
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import gzip
import pandas as pd
import time
from datetime import datetime
from io import StringIO

def main():
    print('🔍 Week-2 Execution (2025-08-08 → 2025-08-14)')
    print('=' * 60)

    # Check environment variables
    coinapi_key = os.getenv('COINAPI_KEY')

    if not coinapi_key:
        print('❌ COINAPI_KEY not found in environment')
        return

    # Week-2 dates and venues
    week2_dates = ['20250808', '20250809', '20250810', '20250811', '20250812', '20250813', '20250814']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

    print(f'📊 **Week-2 Scope:**')
    print(f'📊 Dates: {week2_dates}')
    print(f'📊 Venues: {venues}')
    print(f'📊 Total candidates: {len(week2_dates) * len(venues)}')

    # Results tables
    head_results = []
    download_results = []
    validation_results = []

    print(f'\n📊 **1) Pre-flight HEAD (no downloads):**')

    for date in week2_dates:
        for venue in venues:
            print(f'📊 HEAD {date} {venue}...')
            
            # List URL pattern
            list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
            
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
                        
                        # Make HEAD request
                        head_response = requests.head(full_url, headers=headers, timeout=10)
                        
                        if head_response.status_code == 200:
                            content_length = int(head_response.headers.get('Content-Length', 0))
                            if content_length > 500000:  # > 500KB
                                status = 'VALID'
                            else:
                                status = 'INDETERMINATE'
                        else:
                            status = f'ERROR_{head_response.status_code}'
                            content_length = 0
                        
                        head_results.append({
                            'date': date,
                            'venue': venue,
                            'url': full_url[:50] + '...' if len(full_url) > 50 else full_url,
                            'status': status,
                            'content_length': content_length,
                            'http_status': head_response.status_code
                        })
                    else:
                        head_results.append({
                            'date': date,
                            'venue': venue,
                            'url': 'N/A',
                            'status': 'NO_BTC_OBJECTS',
                            'content_length': 0,
                            'http_status': 200
                        })
                else:
                    head_results.append({
                        'date': date,
                        'venue': venue,
                        'url': 'N/A',
                        'status': f'LIST_ERROR_{response.status_code}',
                        'content_length': 0,
                        'http_status': response.status_code
                    })
            except Exception as e:
                head_results.append({
                    'date': date,
                    'venue': venue,
                    'url': 'N/A',
                    'status': 'EXCEPTION',
                    'content_length': 0,
                    'http_status': 0,
                    'error': str(e)
                })

    # Print HEAD results table
    print(f'\n📊 **HEAD Results Table:**')
    print(f'Date | Venue | Status | Content-Length | HTTP Status')
    print(f'-----|-------|--------|----------------|-------------')

    valid_count = 0
    for result in head_results:
        content_length_str = f'{result["content_length"]:,}' if result['content_length'] > 0 else 'N/A'
        print(f'{result["date"]} | {result["venue"]:6} | {result["status"]:8} | {content_length_str:14} | {result["http_status"]:11}')
        
        if result['status'] == 'VALID':
            valid_count += 1

    print(f'\n📊 **HEAD Summary:**')
    print(f'📊 Total tested: {len(head_results)}')
    print(f'📊 VALID: {valid_count}')
    print(f'📊 INDETERMINATE: {len(head_results) - valid_count}')

    if valid_count > 0:
        print(f'\n✅ **STATUS: ✅** - {valid_count} files ready for download')
        print(f'📊 Proceeding to download')
    else:
        print(f'\n❌ **STATUS: ❌** - No files ready for download')
        print(f'📊 Stopping - no data to download')
        return

    print(f'\n📊 **2) Download REAL only (concurrency ≤ 2):**')

    # Download only VALID files from HEAD pass
    valid_files = []
    for result in head_results:
        if result['status'] == 'VALID':
            valid_files.append((result['date'], result['venue']))

    print(f'📊 Downloading {len(valid_files)} VALID files...')

    # Process files with concurrency ≤ 2
    for i, (date, venue) in enumerate(valid_files):
        if i >= 2:  # Concurrency limit
            print(f'📊 Concurrency limit reached, waiting...')
            time.sleep(1)
            i = 0  # Reset counter
        
        print(f'📊 Downloading {date} {venue}...')
        
        # List URL pattern
        list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
        
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
                        filepath = f'analysis/flatfiles_ticks_v4/raw/{filename}'
                        
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
        except Exception as e:
            print(f'📊 Error processing {date} {venue}: {str(e)}')
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

    print(f'\n📊 **Download Summary:**')
    print(f'📊 Total attempted: {len(download_results)}')
    print(f'📊 Success: {sum(1 for r in download_results if r["status"] == "SUCCESS")}')
    print(f'📊 Error: {sum(1 for r in download_results if r["status"] != "SUCCESS")}')

    print(f'\n✅ 2) completed')

if __name__ == '__main__':
    main()





