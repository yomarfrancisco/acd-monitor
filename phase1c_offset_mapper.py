#!/usr/bin/env python3
"""
Phase 1.C - Offset Mapper (Read-Only, Ultra-Light)
Measure per-venue timing offsets vs BINANCE using tiny samples of 1s VWAP bars
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import psutil
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from collections import defaultdict
from scipy import signal

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 450:  # Increased threshold
        print(f"HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
        return True
    return False

def build_vwap_bars_window(venue, date, start_hour, end_hour):
    """Build 1-second VWAP bars for a specific time window using streaming"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Define time window
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} {start_hour:02d}:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} {end_hour:02d}:00:00", tz='UTC')
        
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Initialize VWAP aggregation
        sum_pxsz = defaultdict(float)
        sum_sz = defaultdict(float)
        
        # Process in smaller batches to reduce memory usage
        batch_size = 25000
        total_rows = 0
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during batch processing"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            total_rows += len(df_batch)
            
            # Filter to time window
            window_mask = (df_batch['ts'] >= day_start) & (df_batch['ts'] < day_end)
            df_window = df_batch[window_mask].copy()  # Use copy to avoid SettingWithCopyWarning
            
            if len(df_window) == 0:
                del df_batch, df_window
                gc.collect()
                continue
            
            # Build 1-second VWAP bars
            df_window['second'] = df_window['ts'].dt.floor('S')
            
            for _, row in df_window.iterrows():
                second = row['second']
                price = row['price']
                size = row['size']
                
                sum_pxsz[second] += price * size
                sum_sz[second] += size
            
            # Clean up batch aggressively
            del df_batch, df_window, window_mask
            gc.collect()
            
            # Check memory after each batch
            if get_memory_usage() >= 400:  # Early warning
                print(f"      ⚠️  Memory warning: {get_memory_usage():.1f} MB")
        
        # Create VWAP bars DataFrame
        bars_data = []
        for second in sorted(sum_pxsz.keys()):
            if sum_sz[second] > 0:
                vwap = sum_pxsz[second] / sum_sz[second]
                bars_data.append({'second': second, 'vwap': vwap})
        
        bars_df = pd.DataFrame(bars_data)
        
        # Clean up
        del sum_pxsz, sum_sz, bars_data
        gc.collect()
        
        if len(bars_df) < 120:  # Need at least 2 minutes of data
            return None, f"Insufficient data: {len(bars_df)} bars (need ≥120)"
        
        return bars_df, None
        
    except Exception as e:
        return None, f"Error processing {file_path}: {e}"

def compute_cross_correlation_lag(binance_bars, other_bars, venue_name):
    """Compute cross-correlation lag between BINANCE and another venue"""
    # Merge bars on second
    merged = pd.merge(binance_bars, other_bars, on='second', suffixes=('_bin', '_other'))
    
    if len(merged) < 120:
        return None, f"Insufficient overlapping data: {len(merged)} bars"
    
    # Sort by second
    merged = merged.sort_values('second').reset_index(drop=True)
    
    # Z-score the VWAP series within this window
    merged['vwap_bin_z'] = (merged['vwap_bin'] - merged['vwap_bin'].mean()) / merged['vwap_bin'].std()
    merged['vwap_other_z'] = (merged['vwap_other'] - merged['vwap_other'].mean()) / merged['vwap_other'].std()
    
    # Remove NaN values
    merged = merged.dropna(subset=['vwap_bin_z', 'vwap_other_z'])
    
    if len(merged) < 60:
        return None, f"Insufficient data after z-scoring: {len(merged)} bars"
    
    # Compute cross-correlation
    try:
        # Use scipy's correlate function
        correlation = signal.correlate(merged['vwap_bin_z'], merged['vwap_other_z'], mode='full')
        
        # Find the lag that maximizes correlation
        lags = np.arange(-len(merged['vwap_other_z']) + 1, len(merged['vwap_bin_z']))
        
        # Limit to ±5 seconds
        max_lag_idx = np.argmax(correlation)
        best_lag = lags[max_lag_idx]
        
        # Limit to ±5 seconds
        if abs(best_lag) > 5:
            # Find best lag within ±5 seconds
            valid_indices = np.where((lags >= -5) & (lags <= 5))[0]
            if len(valid_indices) > 0:
                best_idx = valid_indices[np.argmax(correlation[valid_indices])]
                best_lag = lags[best_idx]
            else:
                best_lag = 0
        
        # Compute Pearson correlation at the best lag
        if best_lag == 0:
            corr = merged['vwap_bin_z'].corr(merged['vwap_other_z'])
        elif best_lag > 0:
            # BINANCE leads
            if len(merged) > best_lag:
                corr = merged['vwap_bin_z'].iloc[:-best_lag].corr(merged['vwap_other_z'].iloc[best_lag:])
            else:
                corr = 0
        else:
            # Other venue leads
            if len(merged) > abs(best_lag):
                corr = merged['vwap_bin_z'].iloc[abs(best_lag):].corr(merged['vwap_other_z'].iloc[:-abs(best_lag)])
            else:
                corr = 0
        
        return {
            'lag': best_lag,
            'correlation': corr,
            'n_bars': len(merged)
        }, None
        
    except Exception as e:
        return None, f"Error computing cross-correlation: {e}"

def process_day_offsets(date, venues):
    """Process offset mapping for a single day"""
    print(f"\n📊 Processing {date}...")
    
    # Define sampling windows: [00-02], [06-08], [12-14], [18-20] UTC
    windows = [(0, 2), (6, 8), (12, 14), (18, 20)]
    
    day_results = {}
    
    # Build VWAP bars for BINANCE (reference)
    print(f"  🔍 Building BINANCE reference bars...")
    binance_bars_all = {}
    
    for start_hour, end_hour in windows:
        window_name = f"{start_hour:02d}-{end_hour:02d}"
        print(f"    Window {window_name}...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded at BINANCE {date} window {window_name}")
            return None
        
        bars, error = build_vwap_bars_window('BINANCE', date, start_hour, end_hour)
        if error:
            print(f"      ⚠️  Skipped: {error}")
            continue
        
        binance_bars_all[window_name] = bars
        print(f"      ✅ {len(bars):,} bars")
        
        gc.collect()
    
    if len(binance_bars_all) == 0:
        print(f"    ❌ No valid BINANCE windows for {date}")
        return None
    
    # Process other venues
    for venue in venues[1:]:  # Skip BINANCE
        print(f"  🔍 Processing {venue}...")
        
        venue_results = []
        
        for start_hour, end_hour in windows:
            window_name = f"{start_hour:02d}-{end_hour:02d}"
            
            if window_name not in binance_bars_all:
                continue
            
            print(f"    Window {window_name}...")
            
            if check_memory_limit():
                print(f"❌ HALT: Memory limit exceeded at {venue} {date} window {window_name}")
                return None
            
            # Build VWAP bars for this venue
            bars, error = build_vwap_bars_window(venue, date, start_hour, end_hour)
            if error:
                print(f"      ⚠️  Skipped: {error}")
                continue
            
            # Compute cross-correlation lag
            result, error = compute_cross_correlation_lag(binance_bars_all[window_name], bars, venue)
            if error:
                print(f"      ⚠️  Skipped: {error}")
                continue
            
            venue_results.append({
                'window': window_name,
                'lag': result['lag'],
                'correlation': result['correlation'],
                'n_bars': result['n_bars']
            })
            
            print(f"      ✅ lag={result['lag']:+.1f}s, ρ={result['correlation']:.3f}")
            
            # Clean up
            del bars
            gc.collect()
        
        if len(venue_results) > 0:
            # Aggregate results for this venue
            lags = [r['lag'] for r in venue_results]
            correlations = [r['correlation'] for r in venue_results]
            
            median_lag = np.median(lags)
            iqr_lag = np.percentile(lags, 75) - np.percentile(lags, 25)
            median_corr = np.median(correlations)
            n_windows = len(venue_results)
            
            # Determine verdict
            if iqr_lag <= 1.0 and abs(median_lag) >= 1.0:
                verdict = "Stable offset"
            elif abs(median_lag) < 1.0 and iqr_lag <= 1.0:
                verdict = "No offset"
            else:
                verdict = "Unstable"
            
            day_results[venue] = {
                'n_windows': n_windows,
                'median_lag_s': median_lag,
                'iqr_lag_s': iqr_lag,
                'median_r': median_corr,
                'verdict': verdict
            }
            
            print(f"    ✅ {venue}: {n_windows} windows, median_lag={median_lag:+.1f}s, IQR={iqr_lag:.1f}s, verdict={verdict}")
        else:
            print(f"    ❌ No valid windows for {venue}")
    
    # Clean up BINANCE bars
    del binance_bars_all
    gc.collect()
    
    return day_results

def run_week2_offset_mapping():
    """Run offset mapping for Week 2 (2025-09-08 to 2025-09-14)"""
    print("🔍 Phase 1.C - Offset Mapper (Week 2)")
    print("=" * 60)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    # Week 2 dates
    start_date = datetime(2025, 9, 8)
    end_date = datetime(2025, 9, 14)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Processing {len(dates)} days: {dates[0]} to {dates[-1]}")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    all_results = {}
    
    for date in dates:
        day_results = process_day_offsets(date, venues)
        if day_results is None:
            print(f"❌ Failed to process {date}")
            return False
        
        all_results[date] = day_results
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
    
    # Print results table
    print(f"\n📊 Week 2 Offset Mapping Results:")
    print("Day | Venue | n_win | median_lag_s | IQR_lag_s | median_r | verdict")
    print("-" * 80)
    
    for date in dates:
        if date in all_results:
            for venue in venues[1:]:  # Skip BINANCE
                if venue in all_results[date]:
                    result = all_results[date][venue]
                    print(f"{date} | {venue} | {result['n_windows']} | {result['median_lag_s']:+.1f} | {result['iqr_lag_s']:.1f} | {result['median_r']:.3f} | {result['verdict']}")
    
    print(f"\n✅ Week 2 offset mapping completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_week2_offset_mapping()
    
    if success:
        print(f"\n🎉 Week 2 offset mapping completed successfully.")
        print(f"Please confirm: ✅ Proceed to Week 3")
    else:
        print(f"\n❌ Week 2 offset mapping failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()
