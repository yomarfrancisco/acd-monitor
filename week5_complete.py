#!/usr/bin/env python3
"""
Week-5 Complete Execution (2025-08-29 → 2025-09-04)
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import gzip
import pandas as pd
import time
import json
from datetime import datetime
from io import StringIO

def main():
    print('🔍 Week-5 Complete Execution (2025-08-29 → 2025-09-04)')
    print('=' * 60)

    # Check environment variables
    coinapi_key = os.getenv('COINAPI_KEY')

    if not coinapi_key:
        print('❌ COINAPI_KEY not found in environment')
        return

    # Week-5 dates and venues
    week5_dates = ['20250829', '20250830', '20250831', '20250901', '20250902', '20250903', '20250904']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

    print(f'📊 **Week-5 Scope:**')
    print(f'📊 Dates: {week5_dates}')
    print(f'📊 Venues: {venues}')
    print(f'📊 Total candidates: {len(week5_dates) * len(venues)}')

    # Results tables
    head_results = []
    download_results = []
    validation_results = []

    print(f'\n📊 **1) Pre-flight HEAD (no downloads):**')

    for date in week5_dates:
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

    print(f'\n📊 **3) Validate ticks (in-memory):**')

    # Validate each downloaded file
    for result in download_results:
        if result['status'] == 'SUCCESS':
            print(f'📊 Validating {result["filename"]}...')
            
            filepath = f'analysis/flatfiles_ticks_v4/raw/{result["filename"]}'
            
            try:
                # Read and parse the file
                with gzip.open(filepath, 'rt') as f:
                    lines = []
                    for line in f:
                        lines.append(line.strip())
                
                if lines:
                    csv_content = '\n'.join(lines)
                    df = pd.read_csv(StringIO(csv_content), sep=';')
                    
                    # Check required columns
                    required_columns = ['time_exchange', 'price', 'base_amount', 'guid']
                    missing_required = [col for col in required_columns if col not in df.columns]
                    
                    if not missing_required and len(df) > 10:
                        # Quality gates
                        non_positive_base_amount = (df['base_amount'] <= 0).sum() / len(df) * 100
                        midnight_ratio = df['time_exchange'].str.contains('00:00:00').sum() / len(df) * 100
                        
                        # Price sanity check
                        price_p01 = df['price'].quantile(0.01)
                        price_p99 = df['price'].quantile(0.99)
                        
                        # Check if quality gates pass
                        quality_pass = (
                            non_positive_base_amount == 0 and
                            midnight_ratio < 15 and
                            price_p01 > 1000 and price_p99 < 1000000  # Reasonable BTC price range
                        )
                        
                        validation_results.append({
                            'date': result['date'],
                            'venue': result['venue'],
                            'filename': result['filename'],
                            'ticks': len(df),
                            'price_p01': price_p01,
                            'price_p99': price_p99,
                            'midnight_pct': midnight_ratio,
                            'nonpos_pct': non_positive_base_amount,
                            'quality_pass': quality_pass,
                            'status': 'VALID' if quality_pass else 'INDETERMINATE'
                        })
                        
                        print(f'📊 {result["filename"]}: {len(df)} ticks, p01={price_p01:.2f}, p99={price_p99:.2f}, midnight={midnight_ratio:.1f}%, nonpos={non_positive_base_amount:.1f}%')
                    else:
                        print(f'📊 {result["filename"]}: Schema validation failed')
                        validation_results.append({
                            'date': result['date'],
                            'venue': result['venue'],
                            'filename': result['filename'],
                            'ticks': len(df) if not missing_required else 0,
                            'price_p01': 0,
                            'price_p99': 0,
                            'midnight_pct': 0,
                            'nonpos_pct': 0,
                            'quality_pass': False,
                            'status': 'SCHEMA_FAILED'
                        })
                else:
                    print(f'📊 {result["filename"]}: Empty file')
                    validation_results.append({
                        'date': result['date'],
                        'venue': result['venue'],
                        'filename': result['filename'],
                        'ticks': 0,
                        'price_p01': 0,
                        'price_p99': 0,
                        'midnight_pct': 0,
                        'nonpos_pct': 0,
                        'quality_pass': False,
                        'status': 'EMPTY_FILE'
                    })
            except Exception as e:
                print(f'📊 {result["filename"]}: Validation error: {str(e)}')
                validation_results.append({
                    'date': result['date'],
                    'venue': result['venue'],
                    'filename': result['filename'],
                    'ticks': 0,
                    'price_p01': 0,
                    'price_p99': 0,
                    'midnight_pct': 0,
                    'nonpos_pct': 0,
                    'quality_pass': False,
                    'status': 'VALIDATION_ERROR'
                })

    print(f'\n📊 **Validation Summary:**')
    print(f'📊 Total validated: {len(validation_results)}')
    print(f'📊 VALID: {sum(1 for r in validation_results if r["status"] == "VALID")}')
    print(f'📊 INDETERMINATE: {sum(1 for r in validation_results if r["status"] == "INDETERMINATE")}')

    print(f'\n📊 **4) Resample to 1-second OHLCV (per venue/day):**')

    # Resample valid files
    resampled_data = []
    for result in validation_results:
        if result['status'] == 'VALID':
            print(f'📊 Resampling {result["filename"]}...')
            
            filepath = f'analysis/flatfiles_ticks_v4/raw/{result["filename"]}'
            
            try:
                # Read the file
                with gzip.open(filepath, 'rt') as f:
                    lines = []
                    for line in f:
                        lines.append(line.strip())
                
                if lines:
                    csv_content = '\n'.join(lines)
                    df = pd.read_csv(StringIO(csv_content), sep=';')
                    
                    # Convert time_exchange to datetime and set as index
                    df['time_exchange'] = pd.to_datetime(df['time_exchange'])
                    df = df.set_index('time_exchange')
                    
                    # Resample to 1-second bars
                    df_resampled = df.resample('1S').agg({
                        'price': ['first', 'max', 'min', 'last'],  # OHLC
                        'base_amount': 'sum'  # Volume
                    })
                    
                    # Flatten column names
                    df_resampled.columns = ['open', 'high', 'low', 'close', 'volume']
                    
                    # Add venue and date columns
                    df_resampled['venue'] = result['venue']
                    df_resampled['date'] = result['date']
                    
                    # Store resampled data
                    key = f'{result["date"]}_{result["venue"]}'
                    resampled_data.append((key, df_resampled))
                    
                    print(f'📊 {result["filename"]}: {len(df)} ticks → {len(df_resampled)} 1s bars')
                    
            except Exception as e:
                print(f'📊 Error resampling {result["filename"]}: {str(e)}')

    print(f'\n📊 **5) Append to panel_v4 (atomic):**')

    if resampled_data:
        # Load existing panel if it exists
        existing_panel = None
        panel_path = 'analysis/flatfiles_1s_v4/panel/candles_1s_panel_v4.parquet'
        
        if os.path.exists(panel_path):
            print(f'📊 Loading existing panel from {panel_path}...')
            existing_panel = pd.read_parquet(panel_path)
            print(f'📊 Existing panel shape: {existing_panel.shape}')
        
        # Create new week's data
        new_week_data = []
        
        for key, df_resampled in resampled_data:
            # Add venue prefix to OHLCV columns
            df_venue = df_resampled.copy()
            venue = df_venue['venue'].iloc[0]
            df_venue.columns = [f'{venue}_{col}' if col in ['open', 'high', 'low', 'close', 'volume'] else col for col in df_venue.columns]
            
            # Keep only the OHLCV columns
            df_venue = df_venue[[col for col in df_venue.columns if col.startswith(venue)]]
            
            new_week_data.append(df_venue)
        
        # Combine new week's data
        new_week_panel = pd.concat(new_week_data, axis=0)
        new_week_panel = new_week_panel.sort_index()
        
        print(f'📊 New week panel shape: {new_week_panel.shape}')
        print(f'📊 New week time span: {new_week_panel.index.min()} to {new_week_panel.index.max()}')
        
        # Combine with existing panel
        if existing_panel is not None:
            combined_panel = pd.concat([existing_panel, new_week_panel], axis=0)
            combined_panel = combined_panel.sort_index()
        else:
            combined_panel = new_week_panel
        
        # Save atomically
        temp_path = 'analysis/flatfiles_1s_v4/panel/candles_1s_panel_v4_temp.parquet'
        combined_panel.to_parquet(temp_path)
        
        # Atomic rename
        os.rename(temp_path, panel_path)
        
        print(f'📊 Combined panel shape: {combined_panel.shape}')
        print(f'📊 Combined time span: {combined_panel.index.min()} to {combined_panel.index.max()}')
        
        # Update manifest
        manifest_path = 'analysis/flatfiles_1s_v4/panel/_v4_manifest.json'
        
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        else:
            manifest = {
                'version': 'v4',
                'created_at': datetime.now().isoformat(),
                'description': 'Week-5 rebuild from CoinAPI Flat Files',
                'date_range': '2025-08-29 to 2025-09-04',
                'venues': ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET'],
                'instruments': ['BTCUSDT', 'BTC-USD'],
                'week5_files': [],
                'panel_info': {
                    'total_rows': 0,
                    'time_span': '',
                    'columns': [],
                    'venues': [],
                    'file_path': panel_path
                }
            }
        
        # Update manifest
        manifest['week5_files'] = [r['filename'] for r in download_results if r['status'] == 'SUCCESS']
        manifest['panel_info']['total_rows'] = len(combined_panel)
        manifest['panel_info']['time_span'] = f'{combined_panel.index.min()} to {combined_panel.index.max()}'
        manifest['panel_info']['columns'] = list(combined_panel.columns)
        manifest['panel_info']['venues'] = list(set([col.split('_')[0] for col in combined_panel.columns if '_' in col]))
        
        # Save manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f'📊 Manifest updated: {manifest_path}')
        
    else:
        print(f'❌ No resampled data to append')

    print(f'\n✅ Week-5 execution completed')

if __name__ == '__main__':
    main()





