#!/usr/bin/env python3
"""
Week -4 Analysis Step 0: Preflight (Read-Only, Metadata + Tiny Slices)
Scope: 2025-08-04 → 2025-08-10 (7 days × 4 venues = 28 combos)
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=600, hard_limit=750):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit warning: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

def validate_parquet_file(file_path, venue, date):
    """Validate Parquet file and get metadata"""
    try:
        # Read a small sample to check schema
        df_sample = pd.read_parquet(file_path)
        
        # Check if file exists and has data
        if df_sample.empty:
            return False, "Empty file", None, None
        
        # Check column names
        expected_cols = ['ts', 'price', 'size', 'venue']
        missing_cols = [col for col in expected_cols if col not in df_sample.columns]
        
        if missing_cols:
            return False, f"Missing columns: {missing_cols}", None, None
        
        # Get row count
        row_count = len(df_sample)
        
        # Check timestamp column
        ts_col = df_sample['ts']
        
        # Check timezone
        if not hasattr(ts_col.dtype, 'tz') or ts_col.dtype.tz is None:
            return False, "Timestamp column not timezone-aware", None, None
            
        if str(ts_col.dtype.tz) != 'UTC':
            return False, f"Timestamp not UTC: {ts_col.dtype.tz}", None, None
        
        # Check monotonicity in first 5k
        first_5k = ts_col.head(5000)
        if not first_5k.is_monotonic_increasing:
            return False, "First 5k timestamps not monotonic", None, None
            
        # Check monotonicity in last 5k
        last_5k = ts_col.tail(5000)
        if not last_5k.is_monotonic_increasing:
            return False, "Last 5k timestamps not monotonic", None, None
        
        # Get timestamp bounds
        ts_min = ts_col.min()
        ts_max = ts_col.max()
        
        # Price sanity check
        price_col = df_sample['price']
        price_min = price_col.min()
        price_max = price_col.max()
        
        # Check price range
        price_warning = ""
        if price_min < 20000 or price_max > 200000:
            price_warning = f" (WARNING: outside [20k, 200k])"
        
        # Get column types
        columns = {col: str(df_sample[col].dtype) for col in df_sample.columns}
        
        return True, f"Schema OK{price_warning}", {
            'row_count': row_count,
            'ts_min': ts_min,
            'ts_max': ts_max,
            'price_min': price_min,
            'price_max': price_max,
            'columns': columns
        }, df_sample
        
    except Exception as e:
        return False, f"Error reading file: {str(e)}", None, None

def compute_coverage_and_vwap(df, date_str):
    """Compute 1-second VWAP bars and coverage percentage"""
    try:
        # Ensure we have the required columns
        if not all(col in df.columns for col in ['ts', 'price', 'size']):
            return None, 0.0, "Missing required columns"
        
        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(df['ts']):
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
        
        # Create 1-second bins
        df['second'] = df['ts'].dt.floor('1S')
        
        # Compute VWAP for each second
        vwap_bars = df.groupby('second').apply(
            lambda x: np.average(x['price'], weights=x['size'])
        ).reset_index()
        vwap_bars.columns = ['second', 'vwap']
        
        # Calculate coverage
        day_start = pd.Timestamp(date_str, tz='UTC').replace(hour=0, minute=0, second=0)
        day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
        
        total_seconds = 86400  # 24 * 60 * 60
        covered_seconds = len(vwap_bars)
        coverage_pct = (covered_seconds / total_seconds) * 100
        
        return vwap_bars, coverage_pct, "OK"
        
    except Exception as e:
        return None, 0.0, f"Error computing VWAP: {str(e)}"

def compute_daily_correlations(vwap_data):
    """Compute pairwise correlations of 1-second VWAP series"""
    try:
        venues = list(vwap_data.keys())
        n_venues = len(venues)
        
        if n_venues < 2:
            return None, "Need at least 2 venues for correlations"
        
        # Create correlation matrix
        corr_matrix = np.full((n_venues, n_venues), np.nan)
        
        for i, venue1 in enumerate(venues):
            for j, venue2 in enumerate(venues):
                if i == j:
                    corr_matrix[i, j] = 1.0
                else:
                    vwap1 = vwap_data[venue1]
                    vwap2 = vwap_data[venue2]
                    
                    # Align timestamps
                    merged = pd.merge(vwap1, vwap2, on='second', how='inner', suffixes=('_1', '_2'))
                    
                    if len(merged) > 10:  # Need sufficient overlap
                        corr = merged['vwap_1'].corr(merged['vwap_2'])
                        corr_matrix[i, j] = corr if not np.isnan(corr) else np.nan
        
        # Remove diagonal for statistics
        mask = ~np.eye(n_venues, dtype=bool)
        valid_corrs = corr_matrix[mask]
        valid_corrs = valid_corrs[~np.isnan(valid_corrs)]
        
        if len(valid_corrs) > 0:
            return {
                'matrix': corr_matrix,
                'venues': venues,
                'min': np.min(valid_corrs),
                'median': np.median(valid_corrs),
                'max': np.max(valid_corrs),
                'count': len(valid_corrs)
            }, "OK"
        else:
            return None, "No valid correlations found"
            
    except Exception as e:
        return None, f"Error computing correlations: {str(e)}"

def main():
    print("🔍 Week -4 Analysis Step 0: Preflight (Read-Only)")
    print("=" * 80)
    print("Scope: 2025-08-04 → 2025-08-10 (7 days × 4 venues = 28 combos)")
    print("Memory limits: Soft 600MB, Hard 750MB")
    print()
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Results storage
    results = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        print(f"📅 Processing {date_display} ({date_str})")
        
        # Check memory before processing day
        mem_ok, mem_msg = check_memory_limit()
        if not mem_ok:
            print(f"❌ {mem_msg}")
            break
        print(f"💾 {mem_msg}")
        
        day_results = {
            'date': date_display,
            'date_str': date_str,
            'venues': {},
            'vwap_data': {},
            'correlations': None
        }
        
        # Process each venue for this day
        for venue in venues:
            file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
            
            print(f"  📊 {venue}: ", end="")
            
            # Validate file and get metadata
            schema_ok, schema_msg, metadata, df_sample = validate_parquet_file(file_path, venue, date_str)
            
            if not schema_ok:
                print(f"❌ {schema_msg}")
                day_results['venues'][venue] = {
                    'status': 'FAIL',
                    'error': schema_msg,
                    'row_count': 0,
                    'coverage': 0.0
                }
                continue
            
            print(f"✅ {schema_msg}")
            print(f"    📈 Rows: {metadata['row_count']:,}")
            print(f"    ⏰ Time: {metadata['ts_min']} → {metadata['ts_max']}")
            print(f"    💰 Price: ${metadata['price_min']:,.2f} → ${metadata['price_max']:,.2f}")
            
            # Compute coverage and VWAP
            vwap_bars, coverage_pct, vwap_msg = compute_coverage_and_vwap(df_sample, date_str)
            
            if vwap_bars is None:
                print(f"    ❌ VWAP: {vwap_msg}")
                day_results['venues'][venue] = {
                    'status': 'FAIL',
                    'error': vwap_msg,
                    'row_count': metadata['row_count'],
                    'coverage': 0.0
                }
                continue
            
            print(f"    📊 Coverage: {coverage_pct:.1f}%")
            
            # Store results
            day_results['venues'][venue] = {
                'status': 'OK',
                'row_count': metadata['row_count'],
                'coverage': coverage_pct,
                'price_min': metadata['price_min'],
                'price_max': metadata['price_max'],
                'ts_min': metadata['ts_min'],
                'ts_max': metadata['ts_max']
            }
            
            day_results['vwap_data'][venue] = vwap_bars
        
        # Compute daily correlations
        if len(day_results['vwap_data']) >= 2:
            corr_result, corr_msg = compute_daily_correlations(day_results['vwap_data'])
            if corr_result:
                day_results['correlations'] = corr_result
                print(f"  🔗 Correlations: min={corr_result['min']:.3f}, median={corr_result['median']:.3f}, max={corr_result['max']:.3f}")
            else:
                print(f"  ❌ Correlations: {corr_msg}")
        else:
            print(f"  ⚠️ Correlations: Need at least 2 venues")
        
        # Check memory after processing day
        mem_ok, mem_msg = check_memory_limit()
        print(f"  💾 {mem_msg}")
        
        results.append(day_results)
        current_date += timedelta(days=1)
        print()
    
    # Print Checkpoint 0 Summary
    print("=" * 80)
    print("✅ CHECKPOINT 0 SUMMARY")
    print("=" * 80)
    
    # Create summary table
    print("📊 Daily Summary Table:")
    print("Date       | BINANCE | COINBASE | BYBITSPOT | BITGET | Corr Min/Med/Max")
    print("-" * 80)
    
    schema_checks_passed = True
    total_venue_days = 0
    successful_venue_days = 0
    
    for day_result in results:
        date = day_result['date']
        venues_data = day_result['venues']
        
        # Count successful venues
        successful_venues = sum(1 for v in venues_data.values() if v['status'] == 'OK')
        total_venue_days += len(venues)
        successful_venue_days += successful_venues
        
        # Check for schema failures
        for venue, data in venues_data.items():
            if data['status'] != 'OK':
                schema_checks_passed = False
        
        # Format row counts and coverage
        row_counts = []
        for venue in venues:
            if venue in venues_data and venues_data[venue]['status'] == 'OK':
                row_count = venues_data[venue]['row_count']
                coverage = venues_data[venue]['coverage']
                row_counts.append(f"{row_count:,} ({coverage:.0f}%)")
            else:
                row_counts.append("FAIL")
        
        # Format correlations
        if day_result['correlations']:
            corr_str = f"{day_result['correlations']['min']:.3f}/{day_result['correlations']['median']:.3f}/{day_result['correlations']['max']:.3f}"
        else:
            corr_str = "N/A"
        
        print(f"{date} | {row_counts[0]:>8} | {row_counts[1]:>8} | {row_counts[2]:>9} | {row_counts[3]:>6} | {corr_str}")
    
    print()
    print(f"📈 Overall Statistics:")
    print(f"  • Total venue-days: {total_venue_days}")
    print(f"  • Successful venue-days: {successful_venue_days}")
    print(f"  • Success rate: {successful_venue_days/total_venue_days*100:.1f}%")
    
    # Schema and timezone check summary
    if schema_checks_passed:
        print("✅ All schema and tz checks passed")
    else:
        print("❌ Some schema/tz checks failed - see details above")
    
    # Memory summary
    final_mem = get_memory_usage()
    print(f"💾 Final memory usage: {final_mem:.1f} MB")
    
    print()
    print("🛑 CHECKPOINT 0 COMPLETE")
    print("Ready for Step 1 - Beacon Detection")
    print("=" * 80)

if __name__ == "__main__":
    main()




