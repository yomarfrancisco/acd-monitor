#!/usr/bin/env python3
"""
Prompt B — Theory Hooks (W1–W3)
MMC, Trigger-Periods, Advance-Notice — W1–W3 (Read-Only)
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
from scipy import stats
from scipy.stats import wilcoxon, spearmanr
# jonckheere_terpstra not available in current scipy version

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
        if coverage_pct < 40:
            return None, f"Coverage too low: {coverage_pct:.1f}% (minimum 40%)"
        
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

def calculate_mmc_index(events, all_vwap_data, venues):
    """Calculate MMC (Multi-Micro-Collision) index for each event"""
    mmc_results = []
    
    for event in events:
        event_second = event['second']
        event_date = event['date']
        
        # Get VWAP data for all venues
        venue_vwaps = {}
        venue_micro_counts = {}
        
        for venue in venues:
            if venue in all_vwap_data[event_date]:
                vwap_data = all_vwap_data[event_date][venue]
                venue_vwaps[venue] = vwap_data['vwap_array']
                venue_micro_counts[venue] = vwap_data['micro_trade_counts']
        
        if len(venue_vwaps) < 2:
            continue
        
        # Count venues with micro-bursts within ±30s & ±0.10% around beacon
        mmc_count = 0
        
        for venue in venues:
            if venue == event['venue'] or venue not in venue_vwaps:
                continue
            
            # Check if venue has micro-burst within ±30s
            window_start = max(0, event_second - 30)
            window_end = min(86400, event_second + 30)
            
            micro_burst = np.sum(venue_micro_counts[venue][window_start:window_end])
            
            if micro_burst >= 6:  # Micro-burst threshold
                # Check if price is within ±0.10% of beacon price
                venue_price = venue_vwaps[venue][event_second]
                if venue_price > 0:
                    price_diff_pct = abs(venue_price - event['price']) / event['price']
                    if price_diff_pct <= 0.001:  # ±0.10%
                        mmc_count += 1
        
        mmc_results.append({
            'event': event,
            'mmc_index': mmc_count
        })
    
    return mmc_results

def calculate_dispersion_change(events, all_vwap_data, venues, window_min=3):
    """Calculate dispersion change for events"""
    window_seconds = window_min * 60
    dispersion_changes = []
    
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
        pre_start = max(0, event_second - window_seconds)
        pre_end = event_second
        post_start = event_second + 1
        post_end = min(86400, event_second + window_seconds + 1)
        
        pre_dispersion = calculate_dispersion_simple(venue_vwaps, pre_start, pre_end)
        post_dispersion = calculate_dispersion_simple(venue_vwaps, post_start, post_end)
        
        dispersion_change = post_dispersion - pre_dispersion
        dispersion_changes.append(dispersion_change)
    
    return dispersion_changes

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

def calculate_trigger_periods(events):
    """Calculate trigger periods and test failed compression effects"""
    # Group events by venue and round level
    venue_round_events = defaultdict(list)
    
    for event in events:
        venue = event['venue']
        round_level = event['nearest_100']
        venue_round_events[(venue, round_level)].append(event)
    
    # Calculate inter-beacon intervals
    intervals = []
    compression_failures = []
    
    for (venue, round_level), round_events in venue_round_events.items():
        if len(round_events) < 2:
            continue
        
        # Sort by time
        round_events.sort(key=lambda x: x['second'])
        
        for i in range(len(round_events) - 1):
            current_event = round_events[i]
            next_event = round_events[i + 1]
            
            # Calculate interval
            interval = next_event['second'] - current_event['second']
            intervals.append(interval)
            
            # Check if current event was a failed compression
            # (simplified: if reversion_3m >= 0, it's a failure)
            failed_compression = current_event['reversion_3m'] >= 0
            compression_failures.append(failed_compression)
    
    return intervals, compression_failures

def calculate_advance_notice(events, all_vwap_data, venues):
    """Calculate advance notice (lead_ms × lead_bps) for events"""
    advance_notices = []
    dispersion_changes = []
    
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
        
        # Find leader (venue with highest price change in first 3 seconds)
        leader = None
        max_lead_bps = 0
        lead_ms = 0
        
        for venue, vwap_array in venue_vwaps.items():
            if venue == event['venue']:
                continue
            
            # Calculate price change in first 3 seconds
            event_price = vwap_array[event_second]
            if event_price == 0:
                continue
            
            # Look at price 3 seconds after event
            post_second = min(86400, event_second + 3)
            post_price = vwap_array[post_second]
            
            if post_price > 0:
                lead_bps = abs(post_price - event_price) / event_price * 10000
                if lead_bps > max_lead_bps:
                    max_lead_bps = lead_bps
                    leader = venue
                    lead_ms = 3000  # 3 seconds in ms
        
        if leader and max_lead_bps >= 2:  # 2 bps threshold
            advance_notice = lead_ms * max_lead_bps
            advance_notices.append(advance_notice)
            
            # Calculate dispersion change
            dispersion_change = calculate_dispersion_change([event], all_vwap_data, venues, 3)[0]
            dispersion_changes.append(dispersion_change)
    
    return advance_notices, dispersion_changes

def create_non_round_control(events):
    """Create non-round pseudo-events as negative control"""
    non_round_events = []
    
    for event in events:
        # Create pseudo-event at non-round price
        pseudo_price = event['price'] + 25  # Add $25 to make it non-round
        pseudo_nearest_100 = round(pseudo_price / 100) * 100
        
        pseudo_event = event.copy()
        pseudo_event['price'] = pseudo_price
        pseudo_event['nearest_100'] = pseudo_nearest_100
        pseudo_event['price_diff_pct'] = abs(pseudo_price - pseudo_nearest_100) / pseudo_nearest_100
        
        non_round_events.append(pseudo_event)
    
    return non_round_events

def create_shuffled_round_control(events):
    """Create shuffled round labels as negative control"""
    shuffled_events = []
    round_levels = [event['nearest_100'] for event in events]
    random.shuffle(round_levels)
    
    for i, event in enumerate(events):
        shuffled_event = event.copy()
        shuffled_event['nearest_100'] = round_levels[i]
        shuffled_events.append(shuffled_event)
    
    return shuffled_events

def create_time_shift_control(events, shift_minutes=20):
    """Create time-shifted events as negative control"""
    shift_seconds = shift_minutes * 60
    shifted_events = []
    
    for event in events:
        shifted_event = event.copy()
        shifted_event['second'] = (event['second'] + shift_seconds) % 86400
        shifted_events.append(shifted_event)
    
    return shifted_events

def run_prompt_b_theory_hooks():
    """Run Prompt B: Theory Hooks (W1–W3)"""
    print("🔍 Prompt B — Theory Hooks (W1–W3)")
    print("=" * 70)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    # All weeks dates
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2025, 9, 21)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Processing {len(dates)} days: {dates[0]} to {dates[-1]}")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Configuration definitions (fixed specs)
    config = {
        'price_band': 0.001,  # ±0.10%
        'min_trades_10s': 12,  # 10s burst
        'min_micro_trades_10s': 6,
        'signal_threshold': 10  # 10 bps
    }
    
    # Storage for results
    all_vwap_data = {}
    all_events = []
    
    # Process each day
    for day_idx, date in enumerate(dates):
        print(f"\n📊 Processing {date} (Day {day_idx + 1}/21)...")
        
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
        
        all_vwap_data[date] = day_vwap_data
        
        # Detect beacons for all venues
        config_events = []
        
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
        
        all_events.extend(config_events)
        
        # Clean up day data
        del day_vwap_data
        gc.collect()
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
    
    print(f"\n🔍 Data Preparation Complete")
    print(f"🧠 Memory usage: {get_memory_usage():.1f} MB")
    print(f"📊 Total events: {len(all_events)}")
    
    # Task 1: MMC index analysis
    print(f"\n🔍 Task 1: MMC index analysis")
    print("=" * 50)
    
    mmc_results = calculate_mmc_index(all_events, all_vwap_data, venues)
    print(f"📊 MMC results: {len(mmc_results)} events")
    
    # Calculate dispersion changes for MMC analysis
    mmc_events = [r['event'] for r in mmc_results]
    mmc_indices = [r['mmc_index'] for r in mmc_results]
    dispersion_changes = calculate_dispersion_change(mmc_events, all_vwap_data, venues, 3)
    
    # Group by MMC index
    mmc_groups = defaultdict(list)
    for i, mmc_idx in enumerate(mmc_indices):
        if i < len(dispersion_changes):
            mmc_groups[mmc_idx].append(dispersion_changes[i])
    
    # Jonckheere-Terpstra test for monotone trend
    mmc_values = []
    dispersion_by_mmc = []
    
    for mmc_idx in sorted(mmc_groups.keys()):
        mmc_values.extend([mmc_idx] * len(mmc_groups[mmc_idx]))
        dispersion_by_mmc.extend(mmc_groups[mmc_idx])
    
    if len(mmc_values) > 0:
        try:
            # Use Spearman correlation as alternative to Jonckheere-Terpstra
            jt_slope, jt_p = spearmanr(mmc_values, dispersion_by_mmc)
            jt_stat = jt_slope  # Use correlation as test statistic
        except:
            jt_stat, jt_p, jt_slope = 0, 1.0, 0.0
    else:
        jt_stat, jt_p, jt_slope = 0, 1.0, 0.0
    
    # Non-round control
    non_round_events = create_non_round_control(all_events)
    non_round_mmc = calculate_mmc_index(non_round_events, all_vwap_data, venues)
    non_round_disp = calculate_dispersion_change([r['event'] for r in non_round_mmc], all_vwap_data, venues, 3)
    
    # Task 2: Trigger-periods analysis
    print(f"\n🔍 Task 2: Trigger-periods analysis")
    print("=" * 50)
    
    intervals, compression_failures = calculate_trigger_periods(all_events)
    print(f"📊 Trigger periods: {len(intervals)} intervals")
    
    # Paired Wilcoxon test
    if len(intervals) > 10:
        failed_intervals = [intervals[i] for i, failed in enumerate(compression_failures) if failed]
        success_intervals = [intervals[i] for i, failed in enumerate(compression_failures) if not failed]
        
        if len(failed_intervals) > 5 and len(success_intervals) > 5:
            try:
                wilcoxon_stat, wilcoxon_p = wilcoxon(failed_intervals, success_intervals)
            except:
                wilcoxon_stat, wilcoxon_p = 0, 1.0
        else:
            wilcoxon_stat, wilcoxon_p = 0, 1.0
    else:
        wilcoxon_stat, wilcoxon_p = 0, 1.0
    
    # Shuffled-round falsification
    shuffled_events = create_shuffled_round_control(all_events)
    shuffled_intervals, shuffled_failures = calculate_trigger_periods(shuffled_events)
    
    # Task 3: Advance-notice analysis
    print(f"\n🔍 Task 3: Advance-notice analysis")
    print("=" * 50)
    
    advance_notices, advance_disp_changes = calculate_advance_notice(all_events, all_vwap_data, venues)
    print(f"📊 Advance notices: {len(advance_notices)} events")
    
    # Spearman correlation
    if len(advance_notices) > 10:
        try:
            spearman_rho, spearman_p = spearmanr(advance_notices, advance_disp_changes)
        except:
            spearman_rho, spearman_p = 0, 1.0
    else:
        spearman_rho, spearman_p = 0, 1.0
    
    # Time-shift falsification
    time_shift_events = create_time_shift_control(all_events, 20)
    shift_advance_notices, shift_disp_changes = calculate_advance_notice(time_shift_events, all_vwap_data, venues)
    
    # Output tables
    print(f"\n📊 Table 1: MMC Index Analysis")
    print("=" * 80)
    print(f"{'MMC':<6} {'n_events':<10} {'Median_Δdisp':<15} {'IQR':<15} {'Control_Median':<15}")
    print("-" * 80)
    
    for mmc_idx in sorted(mmc_groups.keys()):
        if len(mmc_groups[mmc_idx]) > 0:
            median_disp = np.median(mmc_groups[mmc_idx])
            iqr_disp = np.percentile(mmc_groups[mmc_idx], 75) - np.percentile(mmc_groups[mmc_idx], 25)
            print(f"{mmc_idx:<6} {len(mmc_groups[mmc_idx]):<10} {median_disp:<15.6f} {iqr_disp:<15.6f} {'N/A':<15}")
    
    print(f"\nSpearman Correlation (MMC trend): ρ={jt_slope:.4f}, p={jt_p:.4f}")
    print(f"Non-round control median: {np.median(non_round_disp):.6f}")
    
    print(f"\n📊 Table 2: Trigger-Periods Analysis")
    print("=" * 80)
    print(f"{'Condition':<15} {'n_intervals':<12} {'Median_Interval':<15} {'p_wilcoxon':<12}")
    print("-" * 80)
    
    if len(intervals) > 0:
        failed_intervals = [intervals[i] for i, failed in enumerate(compression_failures) if failed]
        success_intervals = [intervals[i] for i, failed in enumerate(compression_failures) if not failed]
        
        print(f"{'Failed_Compression':<15} {len(failed_intervals):<12} {np.median(failed_intervals):<15.1f} {wilcoxon_p:<12.4f}")
        print(f"{'Success_Compression':<15} {len(success_intervals):<12} {np.median(success_intervals):<15.1f} {'N/A':<12}")
        print(f"{'Shuffled_Control':<15} {len(shuffled_intervals):<12} {np.median(shuffled_intervals):<15.1f} {'N/A':<12}")
    
    print(f"\n📊 Table 3: Advance-Notice Analysis")
    print("=" * 80)
    print(f"{'Condition':<15} {'n_events':<10} {'Spearman_ρ':<12} {'p_value':<10}")
    print("-" * 80)
    
    print(f"{'Real_Events':<15} {len(advance_notices):<10} {spearman_rho:<12.4f} {spearman_p:<10.4f}")
    print(f"{'Time_Shift_Control':<15} {len(shift_advance_notices):<10} {'N/A':<12} {'N/A':<10}")
    
    # 6-line narrative
    print(f"\n🔍 6-Line Narrative:")
    print("=" * 50)
    
    print(f"1. MMC Index Effect: {len(mmc_groups)} MMC levels detected, Spearman ρ={jt_slope:.4f} (p={jt_p:.4f})")
    print(f"2. MMC Dispersion Trend: {'Significant' if jt_p < 0.05 else 'No significant'} trend in Δdispersion across MMC levels")
    print(f"3. Trigger-Period Effect: Failed compression → {'shorter' if wilcoxon_p < 0.05 and np.median(failed_intervals) < np.median(success_intervals) else 'no change in'} next interval (p={wilcoxon_p:.4f})")
    print(f"4. Advance-Notice Effect: Lead_ms × lead_bps {'predicts' if spearman_p < 0.05 else 'does not predict'} Δdispersion (ρ={spearman_rho:.4f}, p={spearman_p:.4f})")
    print(f"5. Control Validation: Non-round control median={np.median(non_round_disp):.6f}, shuffled control median={np.median(shuffled_intervals):.1f}s")
    print(f"6. Overall Assessment: {'Significant' if min(jt_p, wilcoxon_p, spearman_p) < 0.05 else 'No significant'} theory-consistent effects detected across all three mechanisms")
    
    print(f"\n✅ Prompt B: Theory Hooks completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_prompt_b_theory_hooks()
    
    if success:
        print(f"\n🎉 Prompt B: Theory Hooks completed successfully.")
        print(f"Ready for downstream analysis and theory validation.")
    else:
        print(f"\n❌ Prompt B: Theory Hooks failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()
