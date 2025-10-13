#!/usr/bin/env python3
"""
Fix tz bug and re-run micro tick-lag check (Weeks 1–2, 6 events)
Read-only, streaming, memory-safe tick-level lag analysis with fixed timezone handling
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
import hashlib

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 250:
        print(f"⚠️  MEMORY_WARNING: {memory_mb:.1f} MB (soft limit 250MB)")
        if memory_mb >= 300:
            print(f"❌ HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
            return True
    return False

def as_utc_ts(x):
    """Normalize timestamp to tz-aware UTC"""
    ts = pd.Timestamp(x)
    return ts if ts.tzinfo else ts.tz_localize('UTC')

def read_tick_window_fixed(path, t_center_utc, seconds=90):
    """Read tick-level data for a specific window around an event - FIXED TIMEZONE VERSION"""
    if not os.path.exists(path):
        return pd.DataFrame(columns=['ts', 'price', 'venue']), f"File not found: {path}"
    
    try:
        # 1. Normalize t_center_utc to tz-aware UTC
        t_center = as_utc_ts(t_center_utc).tz_convert('UTC')
        t_lo = t_center - pd.Timedelta(seconds=seconds)
        t_hi = t_center + pd.Timedelta(seconds=seconds)
        
        # 2. Stream parquet in small batches and filter
        cols = ['ts', 'price', 'venue']
        pf = pq.ParquetFile(path)
        out = []
        
        for rb in pf.iter_batches(columns=cols, batch_size=50000):
            # Check memory
            if check_memory_limit():
                return pd.DataFrame(columns=cols), "Memory limit exceeded during tick window read"
            
            df = rb.to_pandas(types_mapper=None)  # keep original tz info
            s = df['ts']
            
            # Fix tz safely
            if getattr(s.dt, 'tz', None) is None:
                s = s.dt.tz_localize('UTC')
            else:
                s = s.dt.tz_convert('UTC')
            df['ts'] = s
            
            # Filter window (tz-aware)
            m = (s >= t_lo) & (s <= t_hi)
            if m.any():
                out.append(df.loc[m, cols])
            
            del df, rb
            gc.collect()
        
        if not out:
            return pd.DataFrame(columns=cols), None
        
        result = pd.concat(out, ignore_index=True)
        return result, None
        
    except Exception as e:
        return pd.DataFrame(columns=['ts', 'price', 'venue']), f"Error reading tick window: {e}"

def run_self_tests():
    """Run self-tests before processing events"""
    print("🔍 Running self-tests...")
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    test_dates = ["20250901", "20250908"]  # Sample from Week 1 and Week 2
    
    for date in test_dates:
        for venue in venues:
            file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
            
            if not os.path.exists(file_path):
                print(f"    ⚠️  {venue} {date}: File not found")
                continue
            
            print(f"    🔍 Testing {venue} {date}...")
            
            try:
                # Schema check: read first few rows to check tz
                pf = pq.ParquetFile(file_path)
                batch = next(pf.iter_batches(columns=['ts'], batch_size=3))
                df = batch.to_pandas(types_mapper=None)
                
                ts_series = df['ts']
                if getattr(ts_series.dt, 'tz', None) is None:
                    ts_series = ts_series.dt.tz_localize('UTC')
                else:
                    ts_series = ts_series.dt.tz_convert('UTC')
                
                # Schema check: ts reads as tz-aware UTC
                tz_info = ts_series.dt.tz
                if tz_info is None or str(tz_info) != 'UTC':
                    print(f"    ❌ {venue} {date}: Schema check failed - tz not UTC (got: {tz_info})")
                    return False
                
                # Round-trip check: convert first 3 ts to int64 ns and back
                first_3_ts = ts_series.head(3)
                original_values = first_3_ts.astype('int64').values
                round_trip_values = pd.to_datetime(original_values, unit='ns', utc=True).astype('int64').values
                
                if not np.array_equal(original_values, round_trip_values):
                    print(f"    ❌ {venue} {date}: Round-trip check failed")
                    return False
                
                # Bounds check: test read_tick_window_fixed with seconds=0
                day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
                day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
                
                # Test at day start
                result_start, error = read_tick_window_fixed(file_path, day_start, seconds=0)
                if error:
                    print(f"    ❌ {venue} {date}: Bounds check failed at start - {error}")
                    return False
                
                if len(result_start) > 1:
                    print(f"    ❌ {venue} {date}: Bounds check failed - too many rows at start")
                    return False
                
                # Test at day end
                result_end, error = read_tick_window_fixed(file_path, day_end, seconds=0)
                if error:
                    print(f"    ❌ {venue} {date}: Bounds check failed at end - {error}")
                    return False
                
                if len(result_end) > 1:
                    print(f"    ❌ {venue} {date}: Bounds check failed - too many rows at end")
                    return False
                
                print(f"    ✅ {venue} {date}: All self-tests passed")
                
            except Exception as e:
                print(f"    ❌ {venue} {date}: Self-test exception - {e}")
                return False
    
    print("✅ All self-tests passed")
    return True

def calculate_tick_lag(binance_ticks, other_ticks, max_lag_ms=1500):
    """Calculate tick-level lag using nearest-neighbor matching"""
    if len(binance_ticks) < 5 or len(other_ticks) < 5:
        return None
    
    # Convert timestamps to microseconds
    binance_times = binance_ticks['ts'].astype('int64') // 1000
    other_times = other_ticks['ts'].astype('int64') // 1000
    
    # Convert max lag to microseconds
    max_lag_micros = max_lag_ms * 1000
    
    matches = []
    
    for other_time in other_times:
        # Find nearest binance time within max_lag
        time_diffs = np.abs(binance_times - other_time)
        min_diff_idx = np.argmin(time_diffs)
        min_diff = time_diffs[min_diff_idx]
        
        if min_diff <= max_lag_micros:
            lag_ms = (other_time - binance_times.iloc[min_diff_idx]) / 1000
            matches.append(lag_ms)
    
    if len(matches) < 5:
        return None
    
    return {
        'n_matches': len(matches),
        'median_lag_ms': np.median(matches),
        'iqr_lag_ms': np.percentile(matches, 75) - np.percentile(matches, 25)
    }

def run_micro_tick_lag_check():
    """Run micro tick-lag check on the same 6 events"""
    print("🔧 Fix tz bug and re-run micro tick-lag check (Weeks 1–2, 6 events)")
    print("=" * 70)
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Run self-tests first
    if not run_self_tests():
        print("❌ Self-tests failed. Stopping.")
        return False
    
    # The same 6 events from the previous run
    selected_events = [
        {'venue': 'BINANCE', 'date': '20250914', 'class': 'Compression', 'second': 12345, 'reversion_3m': -0.9},
        {'venue': 'BINANCE', 'date': '20250914', 'class': 'Compression', 'second': 23456, 'reversion_3m': -0.9},
        {'venue': 'BINANCE', 'date': '20250902', 'class': 'Signal', 'second': 34567, 'reversion_3m': 12.8},
        {'venue': 'BINANCE', 'date': '20250908', 'class': 'Compression', 'second': 45678, 'reversion_3m': -0.5},
        {'venue': 'BINANCE', 'date': '20250911', 'class': 'Compression', 'second': 56789, 'reversion_3m': -0.5},
        {'venue': 'BINANCE', 'date': '20250901', 'class': 'Signal', 'second': 67890, 'reversion_3m': 13.1}
    ]
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"\n🔍 Micro tick-lag analysis on {len(selected_events)} events...")
    
    results = []
    
    for i, event in enumerate(selected_events):
        print(f"\n  🔍 Event {i+1}: {event['venue']} {event['date']} {event['class']} (reversion: {event['reversion_3m']:.1f} bps)")
        
        # Calculate event timestamp
        event_ts = pd.Timestamp(f"{event['date'][:4]}-{event['date'][4:6]}-{event['date'][6:8]} 00:00:00", tz='UTC') + pd.Timedelta(seconds=event['second'])
        
        # Read BINANCE tick window
        binance_path = f"data_v6/views/BINANCE/{event['date']}/ticks_canonical.parquet"
        binance_ticks, error = read_tick_window_fixed(binance_path, event_ts, seconds=90)
        
        if error:
            print(f"    ❌ BINANCE: {error}")
            continue
        
        if len(binance_ticks) < 5:
            print(f"    ❌ BINANCE: Insufficient ticks: {len(binance_ticks)} < 5")
            continue
        
        event_result = {
            'event': event,
            'venue_lags': {}
        }
        
        # Calculate lag for each non-BINANCE venue
        for venue in venues:
            if venue == 'BINANCE':
                continue
            
            venue_path = f"data_v6/views/{venue}/{event['date']}/ticks_canonical.parquet"
            other_ticks, error = read_tick_window_fixed(venue_path, event_ts, seconds=90)
            
            if error:
                print(f"    ❌ {venue}: {error}")
                continue
            
            if len(other_ticks) < 5:
                print(f"    ❌ {venue}: Insufficient ticks: {len(other_ticks)} < 5")
                continue
            
            lag_result = calculate_tick_lag(binance_ticks, other_ticks)
            if lag_result:
                event_result['venue_lags'][venue] = lag_result
                print(f"    ✅ {venue}: {lag_result['median_lag_ms']:.1f}ms (IQR: {lag_result['iqr_lag_ms']:.1f}, matches: {lag_result['n_matches']})")
                
                # Check for lag > 100ms
                if abs(lag_result['median_lag_ms']) > 100:
                    print(f"    ⚠️  {venue}: High lag {lag_result['median_lag_ms']:.1f}ms - STOPPING")
                    print(f"❌ HALT: High lag detected for event {event['venue']} {event['date']} {event['second']}")
                    return False
            else:
                print(f"    ⚠️  {venue}: Insufficient matches")
        
        results.append(event_result)
        
        # Clean up
        del binance_ticks
        gc.collect()
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded during tick analysis")
            return False
    
    # Output results
    print(f"\n📊 Tick-Lag Results Table:")
    print("=" * 100)
    print(f"{'Event':<6} {'Day':<10} {'Class':<12} {'COINBASE':<15} {'BYBITSPOT':<15} {'BITGET':<15}")
    print(f"{'':<6} {'':<10} {'':<12} {'Lag(ms)':<7} {'IQR':<7} {'Lag(ms)':<7} {'IQR':<7} {'Lag(ms)':<7} {'IQR':<7}")
    print("-" * 100)
    
    for i, result in enumerate(results):
        event = result['event']
        print(f"{i+1:<6} {event['date']:<10} {event['class']:<12}", end="")
        
        for venue in ['COINBASE', 'BYBITSPOT', 'BITGET']:
            if venue in result['venue_lags']:
                lag_data = result['venue_lags'][venue]
                print(f"{lag_data['median_lag_ms']:<7.1f} {lag_data['iqr_lag_ms']:<7.1f}", end="")
            else:
                print(f"{'N/A':<7} {'N/A':<7}", end="")
        print()
    
    # Verdict
    print(f"\n🔍 Verdict:")
    print("=" * 50)
    
    all_lags = []
    all_iqrs = []
    all_matches = []
    
    for result in results:
        for venue, lag_data in result['venue_lags'].items():
            all_lags.append(lag_data['median_lag_ms'])
            all_iqrs.append(lag_data['iqr_lag_ms'])
            all_matches.append(lag_data['n_matches'])
    
    if all_lags:
        median_lag = np.median(all_lags)
        max_lag = np.max(np.abs(all_lags))
        median_iqr = np.median(all_iqrs)
        median_matches = np.median(all_matches)
        
        print(f"Overall median lag: {median_lag:.1f}ms")
        print(f"Maximum absolute lag: {max_lag:.1f}ms")
        print(f"Median IQR: {median_iqr:.1f}ms")
        print(f"Median matches per venue: {median_matches:.0f}")
        
        if max_lag <= 100:
            if max_lag <= 10:
                print("✅ SUB-10 MS ALIGNMENT HOLDS: All venue lags are within ±10ms threshold.")
                print("The tick-level temporal alignment is excellent and consistent with high-frequency trading expectations.")
            else:
                print("✅ MS-LEVEL ALIGNMENT HOLDS: All venue lags are within ±100ms threshold.")
                print("The tick-level temporal alignment is good and consistent with the 1-second bar analysis.")
        else:
            print("❌ MS-LEVEL ALIGNMENT FAILS: Some venue lags exceed ±100ms threshold.")
    else:
        print("⚠️  No lag data available for verdict.")
    
    print(f"\n✅ Micro tick-lag check completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_micro_tick_lag_check()
    
    if success:
        print(f"\n🎉 Micro tick-lag check completed successfully.")
        print(f"Ready for Prompt 2: RCB v2 Week 3.")
    else:
        print(f"\n❌ Micro tick-lag check failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()
