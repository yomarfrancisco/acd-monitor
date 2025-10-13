#!/usr/bin/env python3
"""
Prompt 1 — Tick-Lag Hot-Fix & Micro Check (Weeks 1–2, tiny subset)
Read-only, streaming, memory-safe tick-level lag analysis
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

def build_vwap_and_micro_trades(venue, date):
    """Build 1-second VWAP and micro-trade counts using streaming"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Define full day range
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
        
        # Convert to datetime64[ns, UTC] for comparison
        day_start_dt = day_start.to_datetime64()
        day_end_dt = day_end.to_datetime64()
        
        # Ensure both are timezone-aware for comparison
        day_start_dt = pd.Timestamp(day_start_dt, tz='UTC')
        day_end_dt = pd.Timestamp(day_end_dt, tz='UTC')
        
        # Initialize full-day arrays (86,400 seconds)
        sum_pxsz = np.zeros(86400, dtype=np.float64)
        sum_sz = np.zeros(86400, dtype=np.float64)
        trade_counts = np.zeros(86400, dtype=np.int32)
        micro_trade_counts = np.zeros(86400, dtype=np.int32)
        
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Process in small batches
        batch_size = 10000
        total_rows = 0
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during batch processing"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            total_rows += len(df_batch)
            
            # Filter to day range
            # Ensure both sides are timezone-aware
            if df_batch['ts'].dt.tz is None:
                df_batch['ts'] = df_batch['ts'].dt.tz_localize('UTC')
            
            day_mask = (df_batch['ts'] >= day_start_dt) & (df_batch['ts'] <= day_end_dt)
            df_day = df_batch[day_mask].copy()
            
            if len(df_day) == 0:
                del df_batch, df_day
                gc.collect()
                continue
            
            # Convert timestamps to second indices (0-86399)
            day_start_tz = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
            df_day['second_idx'] = ((df_day['ts'] - day_start_tz).dt.total_seconds()).astype(int)
            
            # Aggregate into arrays
            for _, row in df_day.iterrows():
                second_idx = int(row['second_idx'])
                if 0 <= second_idx < 86400:
                    price = row['price']
                    size = row['size']
                    sum_pxsz[second_idx] += price * size
                    sum_sz[second_idx] += size
                    trade_counts[second_idx] += 1
                    
                    # Count micro-trades (size <= 0.001 BTC)
                    if size <= 0.001:
                        micro_trade_counts[second_idx] += 1
            
            # Clean up batch
            del df_batch, df_day
            gc.collect()
        
        # Compute VWAP for each second
        vwap_array = np.zeros(86400, dtype=np.float64)
        valid_seconds = sum_sz > 0
        vwap_array[valid_seconds] = sum_pxsz[valid_seconds] / sum_sz[valid_seconds]
        
        # Calculate coverage
        coverage_pct = np.sum(valid_seconds) / 86400 * 100
        
        # Check coverage threshold
        if coverage_pct < 50:
            return None, f"Coverage too low: {coverage_pct:.1f}% (minimum 50%)"
        
        result = {
            'vwap_array': vwap_array,
            'trade_counts': trade_counts,
            'micro_trade_counts': micro_trade_counts,
            'valid_seconds': valid_seconds,
            'coverage_pct': coverage_pct,
            'total_rows': total_rows
        }
        
        # Clean up
        del sum_pxsz, sum_sz
        gc.collect()
        
        return result, None
        
    except Exception as e:
        return None, f"Error processing {file_path}: {e}"

def detect_beacons_config(vwap_array, trade_counts, micro_trade_counts, valid_seconds, venue, date, config):
    """Detect beacon events with specific configuration"""
    beacons = []
    
    # Configuration parameters
    price_band = config['price_band']
    min_trades_10s = config['min_trades_10s']
    min_micro_trades_10s = config['min_micro_trades_10s']
    signal_threshold = config['signal_threshold']
    
    # Debounce window
    debounce_window = 30  # ±30 seconds
    
    # Find valid price range for percentage calculations
    valid_prices = vwap_array[valid_seconds]
    if len(valid_prices) == 0:
        return beacons
    
    # Scan for beacon candidates
    for second in range(10, 86400 - 180):  # Need 3 minutes after for reversion
        if not valid_seconds[second]:
            continue
        
        current_price = vwap_array[second]
        if current_price == 0:
            continue
        
        # Check if price is within price band of nearest $100 round level
        nearest_100 = round(current_price / 100) * 100
        price_diff_pct = abs(current_price - nearest_100) / nearest_100
        
        if price_diff_pct > price_band:
            continue
        
        # Check 10-second window trade counts
        window_start = second
        window_end = min(86400, second + 10)
        
        trades_in_10s = np.sum(trade_counts[window_start:window_end])
        micro_trades_in_10s = np.sum(micro_trade_counts[window_start:window_end])
        
        if trades_in_10s < min_trades_10s or micro_trades_in_10s < min_micro_trades_10s:
            continue
        
        # Calculate 3-minute reversion
        reversion_3m = calculate_3m_reversion(vwap_array, valid_seconds, second)
        
        # Classify event
        if reversion_3m >= signal_threshold:
            event_class = 'Signal'
        elif reversion_3m < 5:  # 5 bps
            event_class = 'Compression'
        else:
            event_class = 'Unclassified'
        
        # Create event key for deterministic sampling
        event_key = f"{date}|{venue}|{second}"
        
        beacon = {
            'venue': venue,
            'date': date,
            'second': second,
            'price': current_price,
            'nearest_100': nearest_100,
            'price_diff_pct': price_diff_pct,
            'trades_in_10s': trades_in_10s,
            'micro_trades_in_10s': micro_trades_in_10s,
            'reversion_3m': reversion_3m,
            'class': event_class,
            'event_key': event_key
        }
        
        beacons.append(beacon)
    
    # Apply debouncing (keep highest trades_in_10s within ±30s)
    beacons = apply_debouncing(beacons, debounce_window)
    
    return beacons

def apply_debouncing(beacons, debounce_window):
    """Apply debouncing to remove nearby beacons"""
    if len(beacons) == 0:
        return beacons
    
    # Sort by second
    beacons.sort(key=lambda x: x['second'])
    
    debounced = []
    i = 0
    
    while i < len(beacons):
        current = beacons[i]
        window_start = current['second'] - debounce_window
        window_end = current['second'] + debounce_window
        
        # Find all beacons in the debounce window
        window_beacons = [current]
        j = i + 1
        
        while j < len(beacons) and beacons[j]['second'] <= window_end:
            window_beacons.append(beacons[j])
            j += 1
        
        # Keep the one with highest trades_in_10s
        best_beacon = max(window_beacons, key=lambda x: x['trades_in_10s'])
        debounced.append(best_beacon)
        
        i = j
    
    return debounced

def calculate_3m_reversion(vwap_array, valid_seconds, event_second):
    """Calculate 3-minute reversion in basis points"""
    # Look 3 minutes (180 seconds) after the event
    post_start = event_second + 1
    post_end = min(86400, event_second + 181)
    
    if post_end - post_start < 60:  # Need at least 1 minute of data
        return 0
    
    # Get event price
    event_price = vwap_array[event_second]
    
    # Get post-event prices
    post_prices = vwap_array[post_start:post_end]
    post_valid = valid_seconds[post_start:post_end]
    
    if np.sum(post_valid) == 0 or event_price == 0:
        return 0
    
    post_mean = np.mean(post_prices[post_valid])
    
    # Calculate reversion in basis points
    reversion_bps = ((post_mean - event_price) / event_price) * 10000
    return reversion_bps

def read_tick_window_fixed(venue, date, event_second, window_seconds=90):
    """Read tick-level data for a specific window around an event - HOT-FIXED VERSION"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Define window range with proper timezone handling
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        window_start = day_start + timedelta(seconds=event_second - window_seconds)
        window_end = day_start + timedelta(seconds=event_second + window_seconds)
        
        # Ensure both are timezone-aware
        window_start = pd.Timestamp(window_start, tz='UTC')
        window_end = pd.Timestamp(window_end, tz='UTC')
        
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Collect ticks in window
        ticks = []
        
        for batch in parquet_file.iter_batches(batch_size=6000, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during tick window read"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            
            # HOT-FIX: Ensure timestamps are timezone-aware UTC
            df_batch['ts'] = pd.to_datetime(df_batch['ts'], utc=True)
            
            # Filter to window with proper timezone comparison
            window_mask = (df_batch['ts'] >= window_start) & (df_batch['ts'] <= window_end)
            df_window = df_batch[window_mask].copy()
            
            if len(df_window) == 0:
                del df_batch, df_window
                gc.collect()
                continue
            
            # Convert to microseconds for precise matching
            df_window['ts_micros'] = df_window['ts'].astype('int64') // 1000
            
            # Calculate midprice (simplified as price for now)
            df_window['midprice'] = df_window['price']
            
            # Downsample identical successive prices
            df_window = df_window[df_window['midprice'] != df_window['midprice'].shift(1)]
            
            ticks.extend(df_window[['ts_micros', 'midprice']].values.tolist())
            
            # Clean up
            del df_batch, df_window
            gc.collect()
        
        if len(ticks) < 5:
            return None, f"Insufficient ticks: {len(ticks)} < 5"
        
        return np.array(ticks), None
        
    except Exception as e:
        return None, f"Error reading tick window: {e}"

def calculate_tick_lag(binance_ticks, other_ticks, max_lag_ms=1500):
    """Calculate tick-level lag using nearest-neighbor matching"""
    if len(binance_ticks) < 5 or len(other_ticks) < 5:
        return None
    
    binance_times = binance_ticks[:, 0]  # microseconds
    other_times = other_ticks[:, 0]
    
    # Convert max lag to microseconds
    max_lag_micros = max_lag_ms * 1000
    
    matches = []
    
    for other_time in other_times:
        # Find nearest binance time within max_lag
        time_diffs = np.abs(binance_times - other_time)
        min_diff_idx = np.argmin(time_diffs)
        min_diff = time_diffs[min_diff_idx]
        
        if min_diff <= max_lag_micros:
            lag_ms = (other_time - binance_times[min_diff_idx]) / 1000
            matches.append(lag_ms)
    
    if len(matches) < 5:
        return None
    
    return {
        'n_matches': len(matches),
        'median_lag_ms': np.median(matches),
        'iqr_lag_ms': np.percentile(matches, 75) - np.percentile(matches, 25)
    }

def run_prompt1_tick_lag_hotfix():
    """Run Prompt 1: Tick-Lag Hot-Fix & Micro Check"""
    print("🔧 Prompt 1 — Tick-Lag Hot-Fix & Micro Check (Weeks 1–2)")
    print("=" * 70)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    # Weeks 1-2 dates
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2025, 9, 14)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Processing {len(dates)} days: {dates[0]} to {dates[-1]}")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Configuration definitions
    configs = {
        'Tighter': {
            'price_band': 0.0005,  # ±0.05%
            'min_trades_10s': 60,
            'min_micro_trades_10s': 24,
            'signal_threshold': 10  # 10 bps
        },
        'Lower-Signal': {
            'price_band': 0.001,  # ±0.10%
            'min_trades_10s': 12,
            'min_micro_trades_10s': 6,
            'signal_threshold': 7  # 7 bps
        }
    }
    
    # Storage for results
    all_events = []
    
    # Process each day
    for day_idx, date in enumerate(dates):
        print(f"\n📊 Processing {date} (Day {day_idx + 1}/14)...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded before processing {date}")
            return False
        
        day_vwap_data = {}
        
        # Build VWAP data for all venues
        for venue in venues:
            print(f"  🔍 Processing {venue}...")
            
            vwap_data, error = build_vwap_and_micro_trades(venue, date)
            if error:
                print(f"    ❌ {error}")
                if "Coverage too low" in error:
                    print(f"    ⚠️  Skipping {date} due to coverage issue")
                    break
                return False
            
            day_vwap_data[venue] = vwap_data
            print(f"    ✅ {vwap_data['total_rows']:,} rows, {vwap_data['coverage_pct']:.1f}% coverage")
        
        if len(day_vwap_data) < 4:
            print(f"    ⚠️  Skipping {date} - insufficient venues")
            continue
        
        # Run both configs
        for config_name, config in configs.items():
            print(f"  🔍 Config: {config_name}")
            
            config_events = []
            
            # Detect beacons for all venues
            for venue in venues:
                if venue in day_vwap_data:
                    vwap_data = day_vwap_data[venue]
                    
                    beacons = detect_beacons_config(
                        vwap_data['vwap_array'],
                        vwap_data['trade_counts'],
                        vwap_data['micro_trade_counts'],
                        vwap_data['valid_seconds'],
                        venue,
                        date,
                        config
                    )
                    
                    config_events.extend(beacons)
            
            # Check if sampling needed
            original_count = len(config_events)
            if len(config_events) > 120:
                # Deterministic sampling
                sampled_events = []
                for event in config_events:
                    event_key = event['event_key']
                    hash_val = int(hashlib.md5(event_key.encode()).hexdigest(), 16)
                    if hash_val % (original_count // 24 + 1) == 0:
                        sampled_events.append(event)
                        if len(sampled_events) >= 24:
                            break
                config_events = sampled_events[:24]
                print(f"    📊 Sampled to {len(config_events)} events (from {original_count})")
            
            # Add config name to events
            for event in config_events:
                event['config'] = config_name
            
            all_events.extend(config_events)
        
        # Clean up day data
        del day_vwap_data
        gc.collect()
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
    
    print(f"\n🔍 Total events collected: {len(all_events)}")
    
    # Task B: Select exactly 6 events total (3 per config)
    print(f"\n🔍 Task B: Selecting 6 events for micro tick-lag check...")
    
    selected_events = []
    
    for config_name in ['Tighter', 'Lower-Signal']:
        config_events = [e for e in all_events if e['config'] == config_name]
        
        if len(config_events) == 0:
            continue
        
        # Calculate median reversion for each class
        compression_events = [e for e in config_events if e['class'] == 'Compression']
        signal_events = [e for e in config_events if e['class'] == 'Signal']
        unclassified_events = [e for e in config_events if e['class'] == 'Unclassified']
        
        if len(compression_events) > 0:
            compression_median = np.median([e['reversion_3m'] for e in compression_events])
        else:
            compression_median = 0
        
        # Select 2 Compression events (closest to median)
        if len(compression_events) >= 2:
            compression_events.sort(key=lambda x: abs(x['reversion_3m'] - compression_median))
            selected_events.extend(compression_events[:2])
        elif len(compression_events) == 1:
            selected_events.extend(compression_events)
        
        # Select 1 Signal event (if none, take top Unclassified by reversion)
        if len(signal_events) > 0:
            signal_events.sort(key=lambda x: x['reversion_3m'], reverse=True)
            selected_events.append(signal_events[0])
        elif len(unclassified_events) > 0:
            unclassified_events.sort(key=lambda x: x['reversion_3m'], reverse=True)
            selected_events.append(unclassified_events[0])
    
    # Limit to exactly 6 events
    selected_events = selected_events[:6]
    
    print(f"📊 Selected {len(selected_events)} events for tick-lag analysis")
    
    # Analyze tick-level lag for selected events
    print(f"\n🔍 Tick-level lag analysis...")
    
    results = []
    
    for i, event in enumerate(selected_events):
        print(f"  🔍 Event {i+1}: {event['venue']} {event['date']} {event['class']} (reversion: {event['reversion_3m']:.1f} bps)")
        
        # Read BINANCE tick window
        binance_ticks, error = read_tick_window_fixed('BINANCE', event['date'], event['second'])
        if error:
            print(f"    ❌ BINANCE: {error}")
            continue
        
        event_result = {
            'event': event,
            'venue_lags': {}
        }
        
        # Calculate lag for each non-BINANCE venue
        for venue in venues:
            if venue == 'BINANCE':
                continue
            
            other_ticks, error = read_tick_window_fixed(venue, event['date'], event['second'])
            if error:
                print(f"    ❌ {venue}: {error}")
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
    print("=" * 80)
    print(f"{'Event':<8} {'Class':<12} {'Venue':<10} {'Median Lag (ms)':<15} {'IQR (ms)':<10} {'Matches':<8}")
    print("-" * 80)
    
    for i, result in enumerate(results):
        event = result['event']
        for venue, lag_data in result['venue_lags'].items():
            print(f"{i+1:<8} {event['class']:<12} {venue:<10} {lag_data['median_lag_ms']:<15.1f} {lag_data['iqr_lag_ms']:<10.1f} {lag_data['n_matches']:<8}")
    
    # Verdict
    print(f"\n🔍 Verdict:")
    print("=" * 50)
    
    all_lags = []
    for result in results:
        for venue, lag_data in result['venue_lags'].items():
            all_lags.append(lag_data['median_lag_ms'])
    
    if all_lags:
        median_lag = np.median(all_lags)
        max_lag = np.max(np.abs(all_lags))
        
        print(f"Overall median lag: {median_lag:.1f}ms")
        print(f"Maximum absolute lag: {max_lag:.1f}ms")
        
        if max_lag <= 100:
            print("✅ MS-level alignment HOLDS: All venue lags are within ±100ms threshold.")
            print("The tick-level temporal alignment is consistent with the 1-second bar analysis.")
        else:
            print("❌ MS-level alignment FAILS: Some venue lags exceed ±100ms threshold.")
    else:
        print("⚠️  No lag data available for verdict.")
    
    print(f"\n✅ Prompt 1: Tick-Lag Hot-Fix completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_prompt1_tick_lag_hotfix()
    
    if success:
        print(f"\n🎉 Prompt 1: Tick-Lag Hot-Fix completed successfully.")
        print(f"Ready for Prompt 2: RCB v2 Week 3.")
    else:
        print(f"\n❌ Prompt 1: Tick-Lag Hot-Fix failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




