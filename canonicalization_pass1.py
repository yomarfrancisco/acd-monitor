#!/usr/bin/env python3
"""
🧠 Canonicalization & Integrity Verification (Pass 1)
Weeks -4 → 4 (2025-08-04 → 2025-09-28)
"""

import os
import pandas as pd
import gzip
import hashlib
import gc
import psutil
from datetime import datetime, timedelta
import json

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=400):
    """Check if memory usage exceeds limit"""
    current_mb = get_memory_usage()
    if current_mb > soft_limit:
        print(f"⚠️ Memory usage: {current_mb:.1f} MB (limit: {soft_limit} MB)")
        return False
    return True

def calculate_sha256(file_path):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def validate_and_canonicalize_file(raw_file_path, venue, date):
    """Validate and canonicalize a single raw file"""
    print(f"  📊 Processing {venue} {date}...")
    
    # Check memory before processing
    if not check_memory_limit():
        return None, "Memory limit exceeded"
    
    try:
        # Read the gzipped CSV file
        with gzip.open(raw_file_path, 'rt') as f:
            df = pd.read_csv(f, sep=';')
        
        print(f"    📈 Raw rows: {len(df):,}")
        
        # Validate required columns
        required_cols = ['time_exchange', 'price', 'base_amount']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Missing columns: {missing_cols}"
        
        # Rename base_amount to size for consistency
        df = df.rename(columns={'base_amount': 'size'})
        
        # Convert timestamp to datetime
        df['ts'] = pd.to_datetime(df['time_exchange'])
        
        # Drop original time_exchange column
        df = df.drop('time_exchange', axis=1)
        
        # Reorder columns: ts, price, size, venue
        df = df[['ts', 'price', 'size']].copy()
        df['venue'] = venue
        
        # Data quality checks
        initial_rows = len(df)
        
        # Remove rows with null values
        df = df.dropna()
        print(f"    🧹 After removing nulls: {len(df):,} rows")
        
        # Remove rows with zero or negative prices/sizes
        df = df[(df['price'] > 0) & (df['size'] > 0)]
        print(f"    🧹 After removing zeros/negatives: {len(df):,} rows")
        
        # Check row count threshold
        if len(df) < 50000:
            return None, f"Row count too low: {len(df):,} (minimum: 50,000)"
        
        # Sort by timestamp
        df = df.sort_values('ts')
        
        # Check for duplicates
        duplicates = df.duplicated(subset=['ts', 'price', 'size']).sum()
        if duplicates > 0:
            print(f"    🔍 Found {duplicates:,} duplicate rows, removing...")
            df = df.drop_duplicates(subset=['ts', 'price', 'size'])
        
        # Check monotonic timestamps
        if not df['ts'].is_monotonic_increasing:
            print(f"    ⚠️ Timestamps not monotonic, sorting...")
            df = df.sort_values('ts')
        
        final_rows = len(df)
        print(f"    ✅ Final rows: {final_rows:,}")
        
        # Calculate statistics
        price_min = df['price'].min()
        price_max = df['price'].max()
        size_min = df['size'].min()
        size_max = df['size'].max()
        ts_min = df['ts'].min()
        ts_max = df['ts'].max()
        
        print(f"    📊 Price range: ${price_min:,.2f} - ${price_max:,.2f}")
        print(f"    📊 Size range: {size_min:.6f} - {size_max:.6f}")
        print(f"    📊 Time range: {ts_min} - {ts_max}")
        
        # Create output directory
        output_dir = f"data_v6/views/{venue}/{date}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Backup existing file if it exists
        output_path = f"{output_dir}/ticks_canonical.parquet"
        if os.path.exists(output_path):
            backup_path = f"data_v6/backup/{venue}/{date}/ticks_canonical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            os.rename(output_path, backup_path)
            print(f"    💾 Backed up existing file to: {backup_path}")
        
        # Save canonical file
        df.to_parquet(output_path, index=False)
        
        # Calculate SHA256 of canonical file
        canonical_sha256 = calculate_sha256(output_path)
        
        # Clean up memory
        del df
        gc.collect()
        
        # Check memory after processing
        if not check_memory_limit():
            return None, "Memory limit exceeded after processing"
        
        return {
            'venue': venue,
            'date': date,
            'raw_rows': initial_rows,
            'final_rows': final_rows,
            'price_min': price_min,
            'price_max': price_max,
            'size_min': size_min,
            'size_max': size_max,
            'ts_min': ts_min,
            'ts_max': ts_max,
            'canonical_sha256': canonical_sha256,
            'status': 'SUCCESS'
        }, None
        
    except Exception as e:
        return None, f"Processing error: {e}"

def process_day(date):
    """Process a single day for all venues"""
    print(f"\n📅 Day Summary ({date[:4]}-{date[4:6]}-{date[6:8]}):")
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    results = []
    successful_venues = 0
    
    for venue in venues:
        # Determine filename
        if venue == 'COINBASE':
            filename = f"{venue}_{date}_BTCUSD.csv.gz"
        else:
            filename = f"{venue}_{date}_BTCUSDT.csv.gz"
        
        raw_file_path = f"analysis/flatfiles_ticks_v4/raw/{filename}"
        
        if not os.path.exists(raw_file_path):
            print(f"  ❌ {venue}: Raw file not found: {raw_file_path}")
            results.append({
                'venue': venue,
                'date': date,
                'status': 'FAIL',
                'error': 'Raw file not found'
            })
            continue
        
        result, error = validate_and_canonicalize_file(raw_file_path, venue, date)
        if result:
            print(f"  ✅ {venue}: {result['final_rows']:,} rows, ${result['price_min']:,.2f}-${result['price_max']:,.2f}")
            results.append(result)
            successful_venues += 1
        else:
            print(f"  ❌ {venue}: {error}")
            results.append({
                'venue': venue,
                'date': date,
                'status': 'FAIL',
                'error': error
            })
    
    # Determine day status
    if successful_venues == 4:
        day_status = "FULL"
    elif successful_venues > 0:
        day_status = "PARTIAL"
    else:
        day_status = "FAIL"
    
    print(f"Day status: {day_status} ({successful_venues}/4 venues)")
    
    return results, day_status

def main():
    """Main function"""
    print("🧠 Canonicalization & Integrity Verification (Pass 1)")
    print("=" * 80)
    print("Weeks -4 → 4 (2025-08-04 → 2025-09-28)")
    
    # Create output directories
    os.makedirs('data_v6/views', exist_ok=True)
    os.makedirs('data_v6/backup', exist_ok=True)
    
    # Generate all dates from 2025-08-04 to 2025-09-28
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 9, 28)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Total dates to process: {len(dates)}")
    print(f"🎯 Memory limit: 400 MB")
    print(f"📊 Row count floor: 50,000 per venue-day")
    
    # Process each day
    all_results = []
    week_summary = []
    current_week = None
    week_results = []
    
    for i, date in enumerate(dates):
        # Check if we're starting a new week
        date_obj = datetime.strptime(date, "%Y%m%d")
        week_start = date_obj - timedelta(days=date_obj.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        if current_week != week_key:
            if current_week is not None:
                # Process previous week
                week_summary.append({
                    'week': current_week,
                    'results': week_results
                })
            current_week = week_key
            week_results = []
        
        print(f"\n{'='*60}")
        print(f"Processing day {i+1}/{len(dates)}: {date}")
        
        day_results, day_status = process_day(date)
        all_results.extend(day_results)
        week_results.extend(day_results)
        
        # Count successful venues
        ok_venues = [r['venue'] for r in day_results if r.get('status') == 'SUCCESS']
        fail_venues = [r['venue'] for r in day_results if r.get('status') == 'FAIL']
        
        # Check memory usage
        memory_mb = get_memory_usage()
        print(f"💾 Memory usage: {memory_mb:.1f} MB")
        
        if memory_mb > 400:
            print(f"❌ HALT: Memory limit exceeded ({memory_mb:.1f} MB > 400 MB)")
            break
    
    # Process final week
    if current_week is not None:
        week_summary.append({
            'week': current_week,
            'results': week_results
        })
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"📊 CANONICALIZATION SUMMARY")
    print(f"{'='*80}")
    
    total_venue_days = len(all_results)
    successful_venue_days = len([r for r in all_results if r.get('status') == 'SUCCESS'])
    
    print(f"Total venue-days processed: {total_venue_days}")
    print(f"Successful canonicalizations: {successful_venue_days}")
    print(f"Success rate: {successful_venue_days/total_venue_days*100:.1f}%")
    
    # Print week-by-week summary
    print(f"\n📅 Week-by-Week Summary:")
    print(f"{'Week':<15} {'Days':<6} {'Success':<8} {'Rate':<8}")
    print("-" * 40)
    
    for week_data in week_summary:
        week_results = week_data['results']
        week_success = len([r for r in week_results if r.get('status') == 'SUCCESS'])
        week_total = len(week_results)
        week_rate = week_success/week_total*100 if week_total > 0 else 0
        
        print(f"{week_data['week']:<15} {week_total:<6} {week_success:<8} {week_rate:<8.1f}%")
    
    print(f"\n✅ Canonicalization pass 1 completed!")

if __name__ == "__main__":
    main()




