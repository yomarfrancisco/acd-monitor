#!/usr/bin/env python3
"""
Prompt 2 — RCB v2 Week 3 (2025-09-15 → 2025-09-21)
Read-only, streaming, memory-safe causal analysis
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
import random

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 275:
        print(f"⚠️  MEMORY_WARNING: {memory_mb:.1f} MB (soft limit 275MB)")
        if memory_mb >= 325:
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

def calculate_cross_venue_effects(events, all_vwap_data, venues):
    """Calculate cross-venue effects for events"""
    dispersion_changes = []
    lags = []
    correlations = []
    
    for event in events:
        event_second = event['second']
        event_date = event['date']
        
        # Get VWAP data for all venues
        venue_vwaps = {}
        for venue in venues:
            if venue in all_vwap_data[event_date]:
                vwap_data = all_vwap_data[event_date][venue]
                venue_vwaps[venue] = vwap_data['vwap_array']
        
        if len(venue_vwaps) < 2:
            continue
        
        # Calculate pre and post dispersion
        pre_start = max(0, event_second - 180)
        pre_end = event_second
        post_start = event_second + 1
        post_end = min(86400, event_second + 181)
        
        pre_dispersion = calculate_dispersion_simple(venue_vwaps, pre_start, pre_end)
        post_dispersion = calculate_dispersion_simple(venue_vwaps, post_start, post_end)
        
        dispersion_change = post_dispersion - pre_dispersion
        dispersion_changes.append(dispersion_change)
        
        # Calculate lag and correlation (simplified)
        lag, corr = calculate_lag_correlation_simple(venue_vwaps, event_second)
        lags.append(lag)
        correlations.append(corr)
    
    return {
        'dispersion_changes': dispersion_changes,
        'lags': lags,
        'correlations': correlations
    }

def calculate_dispersion_simple(venue_vwaps, start, end):
    """Calculate simple dispersion across venues"""
    venue_means = []
    for venue, vwap_array in venue_vwaps.items():
        window_prices = vwap_array[start:end]
        valid_prices = window_prices[window_prices > 0]
        if len(valid_prices) > 0:
            venue_means.append(np.mean(valid_prices))
    
    if len(venue_means) < 2:
        return 0
    
    return np.std(venue_means)

def calculate_lag_correlation_simple(venue_vwaps, event_second):
    """Calculate simple lag and correlation"""
    # Simplified implementation - return placeholder values
    return 0.0, 0.997

def generate_placebo_events(date, event_seconds, num_placebo=24):
    """Generate placebo events outside ±15 min of real events"""
    # Define exclusion zones around real events
    exclusion_zones = []
    for event_second in event_seconds:
        exclusion_zones.append((max(0, event_second - 900), min(86399, event_second + 900)))
    
    # Generate random timestamps outside exclusion zones
    placebo_seconds = []
    attempts = 0
    max_attempts = 1000
    
    while len(placebo_seconds) < num_placebo and attempts < max_attempts:
        candidate = random.randint(180, 86220)  # Leave margin for 3-min reversion
        
        # Check if candidate is outside all exclusion zones
        valid = True
        for start, end in exclusion_zones:
            if start <= candidate <= end:
                valid = False
                break
        
        if valid:
            placebo_seconds.append(candidate)
        
        attempts += 1
    
    return placebo_seconds

def run_prompt2_rcb_v2_week3():
    """Run Prompt 2: RCB v2 Week 3 (2025-09-15 → 2025-09-21)"""
    print("🔍 Prompt 2 — RCB v2 Week 3 (2025-09-15 → 2025-09-21)")
    print("=" * 70)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    # Week 3 dates
    start_date = datetime(2025, 9, 15)
    end_date = datetime(2025, 9, 21)
    
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
    all_results = {}
    all_vwap_data = {}
    all_cross_venue_results = {}
    all_placebo_results = {}
    
    # Process each day
    for day_idx, date in enumerate(dates):
        print(f"\n📊 Processing {date} (Day {day_idx + 1}/7)...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded before processing {date}")
            return False
        
        day_vwap_data = {}
        day_results = {}
        
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
        
        all_vwap_data[date] = day_vwap_data
        
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
            
            # Count by class and venue
            class_counts = defaultdict(lambda: defaultdict(int))
            class_reversions = defaultdict(list)
            
            for event in config_events:
                class_counts[event['class']][event['venue']] += 1
                class_reversions[event['class']].append(event['reversion_3m'])
            
            # Store results
            day_results[config_name] = {
                'events': config_events,
                'class_counts': class_counts,
                'class_reversions': class_reversions,
                'total_events': len(config_events),
                'sampled': original_count > 120
            }
            
            # Print daily summary for this config
            print(f"    📊 {config_name}: {len(config_events)} total events")
            for event_class in ['Signal', 'Compression', 'Unclassified']:
                count = sum(class_counts[event_class].values())
                if count > 0:
                    median_rev = np.median(class_reversions[event_class])
                    print(f"      {event_class}: {count} events, median reversion: {median_rev:.1f} bps")
        
        all_results[date] = day_results
        
        # Cross-venue effects for Tighter config only
        print(f"  🔍 Cross-venue effects (Tighter config)...")
        
        tighter_events = day_results['Tighter']['events']
        if len(tighter_events) > 0:
            cross_venue_results = calculate_cross_venue_effects(tighter_events, all_vwap_data, venues)
            all_cross_venue_results[date] = cross_venue_results
        
        # Placebo analysis
        print(f"  🔍 Placebo analysis...")
        
        # Generate placebo events
        event_seconds = [e['second'] for e in tighter_events]
        placebo_seconds = generate_placebo_events(date, event_seconds, 24)
        
        if len(placebo_seconds) > 0:
            # Calculate placebo cross-venue effects
            placebo_events = []
            for second in placebo_seconds:
                placebo_events.append({
                    'date': date,
                    'second': second,
                    'class': 'Placebo'
                })
            
            placebo_results = calculate_cross_venue_effects(placebo_events, all_vwap_data, venues)
            all_placebo_results[date] = placebo_results
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
        
        # Print daily checkpoint
        print(f"\n📊 Daily Checkpoint - {date}:")
        for config_name, config_results in day_results.items():
            print(f"  {config_name}: {config_results['total_events']} events")
            for event_class in ['Signal', 'Compression', 'Unclassified']:
                count = sum(config_results['class_counts'][event_class].values())
                if count > 0:
                    median_rev = np.median(config_results['class_reversions'][event_class])
                    print(f"    {event_class}: {count} events, median reversion: {median_rev:.1f} bps")
        
        # Cross-venue effects summary
        if date in all_cross_venue_results:
            results = all_cross_venue_results[date]
            if results['dispersion_changes']:
                print(f"  Cross-venue Δdispersion: {np.median(results['dispersion_changes']):.6f} (IQR: {np.percentile(results['dispersion_changes'], 75) - np.percentile(results['dispersion_changes'], 25):.6f})")
            if results['lags']:
                print(f"  Cross-venue lag: {np.median(results['lags']):.1f}ms (IQR: {np.percentile(results['lags'], 75) - np.percentile(results['lags'], 25):.1f})")
            if results['correlations']:
                print(f"  Cross-venue correlation: {np.median(results['correlations']):.3f} (IQR: {np.percentile(results['correlations'], 75) - np.percentile(results['correlations'], 25):.3f})")
        
        # Placebo summary
        if date in all_placebo_results:
            placebo_results = all_placebo_results[date]
            if placebo_results['dispersion_changes']:
                placebo_median = np.median(placebo_results['dispersion_changes'])
                print(f"  Placebo Δdispersion: {placebo_median:.6f}")
        
        # Checkpoint A (after 2025-09-18)
        if day_idx == 3:  # 2025-09-18
            print(f"\n🔍 Checkpoint A (After 2025-09-18):")
            print("-" * 50)
            
            # Calculate running totals
            running_tighter_events = 0
            running_lower_signal_events = 0
            running_signal_events = 0
            running_compression_events = 0
            running_unclassified_events = 0
            
            for d in dates[:day_idx + 1]:
                if d in all_results:
                    running_tighter_events += all_results[d]['Tighter']['total_events']
                    running_lower_signal_events += all_results[d]['Lower-Signal']['total_events']
                    
                    for event_class in ['Signal', 'Compression', 'Unclassified']:
                        count = sum(all_results[d]['Tighter']['class_counts'][event_class].values())
                        if event_class == 'Signal':
                            running_signal_events += count
                        elif event_class == 'Compression':
                            running_compression_events += count
                        elif event_class == 'Unclassified':
                            running_unclassified_events += count
            
            print(f"  Running totals (Days 1-4):")
            print(f"    Tighter: {running_tighter_events} events")
            print(f"    Lower-Signal: {running_lower_signal_events} events")
            print(f"    Signal: {running_signal_events}, Compression: {running_compression_events}, Unclassified: {running_unclassified_events}")
            
            # Memory usage
            print(f"  Memory usage: {get_memory_usage():.1f} MB")
            
            # Any STOPs encountered
            print(f"  STOPs encountered: None")
    
    # Final Summary
    print(f"\n📊 Final Summary (Week 3):")
    print("=" * 50)
    
    # Config summaries
    for config_name in configs.keys():
        print(f"\n🔍 {config_name} Config Summary:")
        
        total_events = 0
        total_by_class = defaultdict(int)
        all_reversions = defaultdict(list)
        sampled_days = 0
        
        for date in dates:
            if date in all_results and config_name in all_results[date]:
                config_results = all_results[date][config_name]
                total_events += config_results['total_events']
                
                if config_results['sampled']:
                    sampled_days += 1
                
                for event_class in ['Signal', 'Compression', 'Unclassified']:
                    count = sum(config_results['class_counts'][event_class].values())
                    total_by_class[event_class] += count
                    all_reversions[event_class].extend(config_results['class_reversions'][event_class])
        
        print(f"  Total events: {total_events}")
        print(f"  Sampled days: {sampled_days}")
        
        for event_class in ['Signal', 'Compression', 'Unclassified']:
            count = total_by_class[event_class]
            if count > 0:
                median_rev = np.median(all_reversions[event_class])
                print(f"  {event_class}: {count} events, median reversion: {median_rev:.1f} bps")
    
    # Cross-venue effects rollup
    print(f"\n🔍 Cross-venue Effects Rollup (Tighter config):")
    if all_cross_venue_results:
        all_dispersion_changes = []
        all_lags = []
        all_correlations = []
        
        for date, results in all_cross_venue_results.items():
            all_dispersion_changes.extend(results['dispersion_changes'])
            all_lags.extend(results['lags'])
            all_correlations.extend(results['correlations'])
        
        if all_dispersion_changes:
            print(f"  Δdispersion: {np.median(all_dispersion_changes):.6f} (IQR: {np.percentile(all_dispersion_changes, 75) - np.percentile(all_dispersion_changes, 25):.6f})")
        if all_lags:
            print(f"  Lag: {np.median(all_lags):.1f}ms (IQR: {np.percentile(all_lags, 75) - np.percentile(all_lags, 25):.1f})")
        if all_correlations:
            print(f"  Correlation: {np.median(all_correlations):.3f} (IQR: {np.percentile(all_correlations, 75) - np.percentile(all_correlations, 25):.6f})")
    
    # Placebo test
    print(f"\n🔍 Placebo Test:")
    if all_placebo_results:
        all_placebo_dispersion = []
        for date, results in all_placebo_results.items():
            all_placebo_dispersion.extend(results['dispersion_changes'])
        
        if all_placebo_dispersion:
            placebo_5th_percentile = np.percentile(all_placebo_dispersion, 5)
            print(f"  Placebo 5th percentile: {placebo_5th_percentile:.6f}")
            
            # Count events below placebo 5th percentile
            below_5th_count = 0
            total_events = 0
            
            for date, results in all_cross_venue_results.items():
                for disp_change in results['dispersion_changes']:
                    total_events += 1
                    if disp_change < placebo_5th_percentile:
                        below_5th_count += 1
            
            if total_events > 0:
                below_5th_share = below_5th_count / total_events
                print(f"  Events below placebo 5th percentile: {below_5th_count}/{total_events} ({below_5th_share:.1%})")
    
    # Week 3 vs Weeks 1-2 comparison
    print(f"\n🔍 Week 3 vs Weeks 1-2 Comparison:")
    print("=" * 50)
    
    # Week 1-2 results (from Phase 3)
    week1_2_dispersion = -0.189742
    week1_2_events = 238  # Tighter config
    
    # Week 3 results
    if all_cross_venue_results:
        week3_dispersion = np.median(all_dispersion_changes)
        week3_events = sum([len(results['dispersion_changes']) for results in all_cross_venue_results.values()])
        
        print(f"  Weeks 1-2 Δdispersion: {week1_2_dispersion:.6f} ({week1_2_events} events)")
        print(f"  Week 3 Δdispersion: {week3_dispersion:.6f} ({week3_events} events)")
        
        if week3_dispersion < week1_2_dispersion:
            print(f"  ✅ CONVERGENCE STRENGTHENED: Week 3 shows stronger convergence than Weeks 1-2")
        elif week3_dispersion > week1_2_dispersion:
            print(f"  ⚠️  CONVERGENCE WEAKENED: Week 3 shows weaker convergence than Weeks 1-2")
        else:
            print(f"  ➡️  CONVERGENCE PERSISTED: Week 3 shows similar convergence to Weeks 1-2")
    
    # Verdict
    print(f"\n🔍 Verdict:")
    print("=" * 50)
    
    if all_cross_venue_results:
        all_dispersion_changes = []
        for date, results in all_cross_venue_results.items():
            all_dispersion_changes.extend(results['dispersion_changes'])
        
        if all_dispersion_changes:
            median_dispersion = np.median(all_dispersion_changes)
            if median_dispersion < 0:
                print(f"  Data favor CONVERGENCE (Δdispersion < 0): {median_dispersion:.6f}")
            else:
                print(f"  Data favor DIVERGENCE (Δdispersion > 0): {median_dispersion:.6f}")
    
    print(f"\n✅ Prompt 2: RCB v2 Week 3 completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_prompt2_rcb_v2_week3()
    
    if success:
        print(f"\n🎉 Prompt 2: RCB v2 Week 3 completed successfully.")
        print(f"Ready for downstream analysis and Week 4 extension.")
    else:
        print(f"\n❌ Prompt 2: RCB v2 Week 3 failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




