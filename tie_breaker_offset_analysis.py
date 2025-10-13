#!/usr/bin/env python3
"""
Tie-Breaker: Full-Day vs Windowed Offsets (Read-Only, Ultra-Light)
Resolve discrepancy between ~2-3s lags and Phase 1.C "No offset" result
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
    if memory_mb >= 250:
        print(f"HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
        return True
    return False

def build_full_day_vwap_bars(venue, date):
    """Build full-day 1-second VWAP bars using streaming aggregation"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Define full day range
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
        
        # Initialize full-day VWAP aggregation (86,400 seconds)
        sum_pxsz = np.zeros(86400, dtype=np.float64)
        sum_sz = np.zeros(86400, dtype=np.float64)
        
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Process in small batches
        batch_size = 25000
        total_rows = 0
        
        print(f"    📊 Building full-day VWAP bars for {venue}...")
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during batch processing"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            total_rows += len(df_batch)
            
            # Filter to day range
            day_mask = (df_batch['ts'] >= day_start) & (df_batch['ts'] <= day_end)
            df_day = df_batch[day_mask].copy()
            
            if len(df_day) == 0:
                del df_batch, df_day
                gc.collect()
                continue
            
            # Convert timestamps to second indices (0-86399)
            df_day['second_idx'] = ((df_day['ts'] - day_start).dt.total_seconds()).astype(int)
            
            # Aggregate into VWAP arrays
            for _, row in df_day.iterrows():
                second_idx = int(row['second_idx'])
                if 0 <= second_idx < 86400:
                    price = row['price']
                    size = row['size']
                    sum_pxsz[second_idx] += price * size
                    sum_sz[second_idx] += size
            
            # Clean up batch
            del df_batch, df_day
            gc.collect()
        
        # Compute VWAP for each second
        vwap_array = np.zeros(86400, dtype=np.float64)
        valid_seconds = sum_sz > 0
        vwap_array[valid_seconds] = sum_pxsz[valid_seconds] / sum_sz[valid_seconds]
        
        # Create results
        first_second = np.where(valid_seconds)[0][0] if np.any(valid_seconds) else None
        last_second = np.where(valid_seconds)[0][-1] if np.any(valid_seconds) else None
        coverage_pct = np.sum(valid_seconds) / 86400 * 100
        
        result = {
            'vwap_array': vwap_array,
            'valid_seconds': valid_seconds,
            'first_second': first_second,
            'last_second': last_second,
            'coverage_pct': coverage_pct,
            'total_rows': total_rows
        }
        
        # Clean up
        del sum_pxsz, sum_sz
        gc.collect()
        
        return result, None
        
    except Exception as e:
        return None, f"Error processing {file_path}: {e}"

def method_a_cross_correlation(binance_vwap, other_vwap, venue_name):
    """Method A: Cross-correlation of z-scored series"""
    # Find overlapping valid seconds
    valid_mask = binance_vwap['valid_seconds'] & other_vwap['valid_seconds']
    
    if np.sum(valid_mask) < 1000:  # Need sufficient overlap
        return None, f"Insufficient overlapping data: {np.sum(valid_mask)} seconds"
    
    # Extract overlapping VWAP values
    binance_overlap = binance_vwap['vwap_array'][valid_mask]
    other_overlap = other_vwap['vwap_array'][valid_mask]
    
    # Z-score the series
    binance_z = (binance_overlap - np.mean(binance_overlap)) / np.std(binance_overlap)
    other_z = (other_overlap - np.mean(other_overlap)) / np.std(other_overlap)
    
    # Compute cross-correlation
    try:
        correlation = signal.correlate(binance_z, other_z, mode='full')
        lags = np.arange(-len(other_z) + 1, len(binance_z))
        
        # Find the lag that maximizes correlation
        max_lag_idx = np.argmax(correlation)
        best_lag = lags[max_lag_idx]
        
        # Limit to ±5 seconds
        if abs(best_lag) > 5:
            valid_indices = np.where((lags >= -5) & (lags <= 5))[0]
            if len(valid_indices) > 0:
                best_idx = valid_indices[np.argmax(correlation[valid_indices])]
                best_lag = lags[best_idx]
            else:
                best_lag = 0
        
        # Compute Pearson correlation at the best lag
        if best_lag == 0:
            corr = np.corrcoef(binance_z, other_z)[0, 1]
        elif best_lag > 0:
            # BINANCE leads
            if len(binance_z) > best_lag:
                corr = np.corrcoef(binance_z[:-best_lag], other_z[best_lag:])[0, 1]
            else:
                corr = 0
        else:
            # Other venue leads
            if len(binance_z) > abs(best_lag):
                corr = np.corrcoef(binance_z[abs(best_lag):], other_z[:-abs(best_lag)])[0, 1]
            else:
                corr = 0
        
        return {
            'lag': best_lag,
            'correlation': corr,
            'n_overlap': np.sum(valid_mask)
        }, None
        
    except Exception as e:
        return None, f"Error computing cross-correlation: {e}"

def method_b_mse_alignment(binance_vwap, other_vwap, venue_name):
    """Method B: Brute-force MSE minimization"""
    # Find overlapping valid seconds
    valid_mask = binance_vwap['valid_seconds'] & other_vwap['valid_seconds']
    
    if np.sum(valid_mask) < 1000:  # Need sufficient overlap
        return None, f"Insufficient overlapping data: {np.sum(valid_mask)} seconds"
    
    # Extract overlapping VWAP values
    binance_overlap = binance_vwap['vwap_array'][valid_mask]
    other_overlap = other_vwap['vwap_array'][valid_mask]
    
    # Z-score the series
    binance_z = (binance_overlap - np.mean(binance_overlap)) / np.std(binance_overlap)
    other_z = (other_overlap - np.mean(other_overlap)) / np.std(other_overlap)
    
    # Brute-force search over ±5 second lags
    best_lag = 0
    best_mse = float('inf')
    
    for lag in range(-5, 6):
        if lag == 0:
            mse = np.mean((binance_z - other_z) ** 2)
        elif lag > 0:
            # BINANCE leads
            if len(binance_z) > lag:
                mse = np.mean((binance_z[:-lag] - other_z[lag:]) ** 2)
            else:
                continue
        else:
            # Other venue leads
            if len(binance_z) > abs(lag):
                mse = np.mean((binance_z[abs(lag):] - other_z[:-abs(lag)]) ** 2)
            else:
                continue
        
        if mse < best_mse:
            best_mse = mse
            best_lag = lag
    
    return {
        'lag': best_lag,
        'mse': best_mse,
        'n_overlap': np.sum(valid_mask)
    }, None

def run_tie_breaker_analysis():
    """Run tie-breaker analysis for 2025-09-08"""
    print("🔍 Tie-Breaker: Full-Day vs Windowed Offsets")
    print("=" * 60)
    
    date = "20250908"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"📅 Analyzing {date} across {len(venues)} venues")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Build full-day VWAP bars for all venues
    all_vwap_data = {}
    
    for venue in venues:
        print(f"\n🔍 Processing {venue}...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded before processing {venue}")
            return False
        
        vwap_data, error = build_full_day_vwap_bars(venue, date)
        if error:
            print(f"    ❌ {error}")
            return False
        
        all_vwap_data[venue] = vwap_data
        
        print(f"    ✅ {vwap_data['total_rows']:,} rows, {vwap_data['coverage_pct']:.1f}% coverage")
        print(f"    📊 First: {vwap_data['first_second']}, Last: {vwap_data['last_second']}")
        
        # Check memory after each venue
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after processing {venue}")
            return False
    
    # Run both methods for each non-BINANCE venue
    print(f"\n🔍 Running Method A (Cross-Correlation) and Method B (MSE)...")
    
    results = {}
    binance_vwap = all_vwap_data['BINANCE']
    
    for venue in venues[1:]:  # Skip BINANCE
        print(f"\n  🔍 Analyzing {venue}...")
        
        other_vwap = all_vwap_data[venue]
        
        # Method A: Cross-correlation
        print(f"    Method A (Cross-correlation)...")
        method_a_result, error = method_a_cross_correlation(binance_vwap, other_vwap, venue)
        if error:
            print(f"      ❌ {error}")
            return False
        
        # Method B: MSE alignment
        print(f"    Method B (MSE alignment)...")
        method_b_result, error = method_b_mse_alignment(binance_vwap, other_vwap, venue)
        if error:
            print(f"      ❌ {error}")
            return False
        
        # Determine verdict
        lag_a = method_a_result['lag']
        lag_b = method_b_result['lag']
        
        if (abs(lag_a) <= 1 and abs(lag_b) <= 1):
            verdict = "No offset (consistent)"
        elif (abs(lag_a) >= 2 and abs(lag_b) >= 2 and abs(lag_a - lag_b) <= 1):
            verdict = "Offset present (consistent)"
        elif abs(lag_a - lag_b) >= 2:
            verdict = "Method discrepancy — investigate"
        else:
            verdict = "Unclear"
        
        results[venue] = {
            'coverage_pct': other_vwap['coverage_pct'],
            'first_second': other_vwap['first_second'],
            'last_second': other_vwap['last_second'],
            'lag_xcorr': lag_a,
            'rho_at_lag': method_a_result['correlation'],
            'lag_mse': lag_b,
            'mse_at_lag': method_b_result['mse'],
            'verdict': verdict
        }
        
        print(f"      ✅ Method A: lag={lag_a:+.1f}s, ρ={method_a_result['correlation']:.3f}")
        print(f"      ✅ Method B: lag={lag_b:+.1f}s, MSE={method_b_result['mse']:.6f}")
        print(f"      🎯 Verdict: {verdict}")
    
    # Print results table
    print(f"\n📊 Tie-Breaker Results:")
    print("Venue | Cov% | FirstSec→LastSec | Lag_XCorr(s) | ρ_at_lag | Lag_MSE(s) | MSE_at_lag | Verdict")
    print("-" * 100)
    
    for venue in venues[1:]:  # Skip BINANCE
        result = results[venue]
        first_last = f"{result['first_second']}→{result['last_second']}"
        
        print(f"{venue} | {result['coverage_pct']:.1f} | {first_last} | {result['lag_xcorr']:+.1f} | {result['rho_at_lag']:.3f} | {result['lag_mse']:+.1f} | {result['mse_at_lag']:.6f} | {result['verdict']}")
    
    # Sanity checks
    print(f"\n🔍 Sanity Checks:")
    binance_first = binance_vwap['first_second']
    binance_last = binance_vwap['last_second']
    
    for venue in venues[1:]:
        result = results[venue]
        first_diff = result['first_second'] - binance_first
        last_diff = result['last_second'] - binance_last
        
        print(f"  {venue}: First diff = {first_diff:+d}s, Last diff = {last_diff:+d}s")
        
        if last_diff < -1:
            print(f"    ⚠️  {venue} ends >1s earlier than BINANCE")
    
    print(f"\n✅ Tie-breaker analysis completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_tie_breaker_analysis()
    
    if success:
        print(f"\n🎉 Tie-breaker analysis completed successfully.")
        print(f"Please review results and provide approval for next steps.")
    else:
        print(f"\n❌ Tie-breaker analysis failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




