#!/usr/bin/env python3
"""
Week 1 Download and Validation
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import gzip
import pandas as pd
import json
from datetime import datetime
from io import StringIO

def main():
    print('🔍 Week 1 Execution: Download, Validate, Resample')
    print('=' * 60)

    # Check environment variables
    coinapi_key = os.getenv('COINAPI_KEY')

    if not coinapi_key:
        print('❌ COINAPI_KEY not found in environment')
        return

    # Week 1 dates and venues
    week1_dates = ['20250801', '20250802', '20250803', '20250804', '20250805', '20250806', '20250807']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

    print(f'📊 **Week 1 Scope:**')
    print(f'📊 Dates: {week1_dates}')
    print(f'📊 Venues: {venues}')

    # Create v4 directories
    os.makedirs('analysis/flatfiles_ticks_v4/raw', exist_ok=True)
    os.makedirs('analysis/flatfiles_1s_v4/panel', exist_ok=True)

    # Results tables
    download_results = []
    validation_results = []

    print(f'\n📊 **5.1.2 Selective Download (GET):**')

    # Download only REAL files from HEAD pass
    real_files = [
        ('20250801', 'COINBASE'),
        ('20250801', 'BYBITSPOT'),
        ('20250801', 'BITGET'),
        ('20250802', 'BINANCE'),
        ('20250802', 'COINBASE'),
        ('20250802', 'BYBITSPOT'),
        ('20250802', 'BITGET'),
        ('20250803', 'BINANCE'),
        ('20250803', 'COINBASE'),
        ('20250803', 'BYBITSPOT'),
        ('20250803', 'BITGET'),
        ('20250804', 'COINBASE'),
        ('20250804', 'BYBITSPOT'),
        ('20250804', 'BITGET'),
        ('20250805', 'COINBASE'),
        ('20250805', 'BYBITSPOT'),
        ('20250805', 'BITGET'),
        ('20250806', 'BINANCE'),
        ('20250806', 'COINBASE'),
        ('20250806', 'BYBITSPOT'),
        ('20250806', 'BITGET'),
        ('20250807', 'BINANCE'),
        ('20250807', 'COINBASE'),
        ('20250807', 'BYBITSPOT'),
        ('20250807', 'BITGET')
    ]

    print(f'📊 Downloading {len(real_files)} verified REAL files...')

    for date, venue in real_files:
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

    print(f'\n✅ 5.1.2 completed')

if __name__ == '__main__':
    main()





