#!/usr/bin/env python3
"""
Validate Week 1 Files
"""

import os
import gzip
import pandas as pd
import json
import hashlib
from datetime import datetime
from io import StringIO

def main():
    print('🔍 3. Validation')
    print('=' * 60)

    # Load existing v3 manifest
    manifest_path = 'analysis/flatfiles_1s/panel/_v3_manifest.json'

    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        print(f'📊 Loaded existing manifest with {len(manifest.get("included_slices", []))} slices')
    else:
        print(f'❌ Manifest not found')
        return

    # Validate downloaded files
    target_dir = 'analysis/flatfiles_ticks/week_20250801_20250807'
    downloaded_files = []

    if os.path.exists(target_dir):
        for file in os.listdir(target_dir):
            if file.endswith('.csv.gz'):
                downloaded_files.append(file)
        
        print(f'📊 Found {len(downloaded_files)} downloaded files')
    else:
        print(f'❌ Target directory not found')
        return

    # Validation results
    validation_results = []

    for filename in downloaded_files:
        print(f'📊 Validating {filename}...')
        
        filepath = os.path.join(target_dir, filename)
        
        try:
            # Read the compressed CSV file
            with gzip.open(filepath, 'rt') as f:
                lines = []
                for line in f:
                    lines.append(line.strip())
            
            if not lines:
                print(f'📊 Empty file: {filename}')
                continue
            
            # Parse CSV
            csv_content = '\n'.join(lines)
            df = pd.read_csv(StringIO(csv_content), sep=';')
            
            # Basic metrics
            tick_count = len(df)
            
            # Check required columns
            required_columns = ['time_exchange', 'price', 'base_amount', 'guid']
            missing_required = [col for col in required_columns if col not in df.columns]
            
            if missing_required:
                print(f'📊 Missing required columns: {missing_required}')
                validation_results.append({
                    'filename': filename,
                    'status': 'MISSING_COLUMNS',
                    'reason': f'Missing: {missing_required}',
                    'tick_count': 0,
                    'min_time': 'N/A',
                    'max_time': 'N/A',
                    'price_range': 'N/A',
                    'sha256': 'N/A'
                })
                continue
            
            # Timestamp analysis
            df['time_exchange'] = pd.to_datetime(df['time_exchange'])
            min_timestamp = df['time_exchange'].min()
            max_timestamp = df['time_exchange'].max()
            
            # Check for midnight pattern
            midnight_seconds = df['time_exchange'].dt.hour == 0
            midnight_count = midnight_seconds.sum()
            midnight_ratio = midnight_count / len(df) if len(df) > 0 else 0
            
            # Price analysis
            price_stats = df['price'].describe()
            price_p01 = df['price'].quantile(0.01)
            price_p99 = df['price'].quantile(0.99)
            
            # Size analysis
            nonpositive_size = (df['base_amount'] <= 0).sum()
            nonpositive_ratio = nonpositive_size / len(df) if len(df) > 0 else 0
            
            # QC checks
            if tick_count <= 10:
                verdict = 'STUB'
                reason = f'TICK_COUNT_TOO_LOW: {tick_count}'
            elif midnight_ratio == 1.0:
                verdict = 'STUB'
                reason = 'MIDNIGHT_SINGLETON'
            elif nonpositive_ratio > 0.1:
                verdict = 'STUB'
                reason = f'HIGH_NONPOSITIVE_SIZE: {nonpositive_ratio:.1%}'
            elif price_p01 < 80000 or price_p99 > 140000:
                verdict = 'STUB'
                reason = f'PRICE_OUT_OF_RANGE: {price_p01:.0f}-{price_p99:.0f}'
            else:
                verdict = 'VALID'
                reason = 'PASSED_QC'
            
            # Compute SHA256
            with open(filepath, 'rb') as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest()
            
            validation_results.append({
                'filename': filename,
                'status': verdict,
                'reason': reason,
                'tick_count': tick_count,
                'min_time': str(min_timestamp),
                'max_time': str(max_timestamp),
                'price_range': f'{price_p01:.0f}-{price_p99:.0f}',
                'sha256': sha256_hash
            })
            
            print(f'📊 {filename}: {tick_count} ticks, verdict: {verdict}')
            
        except Exception as e:
            print(f'📊 Error validating {filename}: {str(e)}')
            validation_results.append({
                'filename': filename,
                'status': 'PARSE_ERROR',
                'reason': f'Parse error: {str(e)}',
                'tick_count': 0,
                'min_time': 'N/A',
                'max_time': 'N/A',
                'price_range': 'N/A',
                'sha256': 'N/A'
            })

    # Generate validation table
    print(f'\n📊 **Validation Table:**')
    print(f'Date | Venue | Rows | Min Time | Max Time | Price Range | SHA256 | Verdict')
    print(f'-----|-------|------|----------|----------|-------------|--------|--------')

    valid_count = 0
    invalid_count = 0

    for result in validation_results:
        # Extract date and venue from filename
        filename = result['filename']
        if '_' in filename:
            parts = filename.split('_')
            venue = parts[0]
            date = parts[1]
        else:
            venue = 'UNKNOWN'
            date = 'UNKNOWN'
        
        time_span = f'{result["min_time"][:19]} to {result["max_time"][:19]}' if result['min_time'] != 'N/A' else 'N/A'
        sha256_str = result['sha256'][:8] + '...' if result['sha256'] != 'N/A' else 'N/A'
        
        print(f'{date} | {venue:6} | {result["tick_count"]:4} | {time_span:8} | {time_span:8} | {result["price_range"]:11} | {sha256_str:6} | {result["status"]:6}')
        
        if result['status'] == 'VALID':
            valid_count += 1
        else:
            invalid_count += 1

    print(f'\n📊 **Validation Summary:**')
    print(f'📊 Total files: {len(validation_results)}')
    print(f'📊 Valid: {valid_count}')
    print(f'📊 Invalid: {invalid_count}')

    # Update manifest with validated files
    if valid_count > 0:
        print(f'\n📊 **Updating manifest with validated files...**')
        
        for result in validation_results:
            if result['status'] == 'VALID':
                # Extract date and venue from filename
                filename = result['filename']
                if '_' in filename:
                    parts = filename.split('_')
                    venue = parts[0]
                    date = parts[1]
                    
                    # Add to manifest
                    manifest['included_slices'].append({
                        'date': date,
                        'venue': venue,
                        'filename': filename,
                        'size_bytes': os.path.getsize(os.path.join(target_dir, filename)),
                        'sha256': result['sha256'],
                        'tick_count': result['tick_count'],
                        'resampled_rows': 0,  # Will be filled during resampling
                        'time_span': f'{result["min_time"]} to {result["max_time"]}',
                        'verdict': 'REAL',
                        'verified': True
                    })
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f'📊 Manifest updated with {valid_count} validated files')

    if invalid_count > 0:
        print(f'\n❌ **STATUS: ❌** - {invalid_count} files failed validation')
        print(f'📊 Stopping - validation failures detected')
    else:
        print(f'\n✅ **STATUS: ✅** - All files passed validation')
        print(f'📊 Ready for resampling and append')

    print(f'\n✅ 3. completed')

if __name__ == '__main__':
    main()





