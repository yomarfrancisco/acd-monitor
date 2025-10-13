#!/usr/bin/env python3
"""
RCB v2 (Fix & Verify) - Read-only analysis on 2025-09-01 and 2025-09-02
Stricter beacon detection with full cross-venue metrics
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
    if memory_mb >= 350:
        print(f"⚠️  MEMORY_WARNING: {memory_mb:.1f} MB (soft limit 350MB)")
        if memory_mb >= 400:
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
        
        # Initialize full-day arrays (86,400 seconds)
        sum_pxsz = np.zeros(86400, dtype=np.float64)
        sum_sz = np.zeros(86400, dtype=np.float64)
        trade_counts = np.zeros(86400, dtype=np.int32)
        micro_trade_counts = np.zeros(86400, dtype=np.int32)
        
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Process in small batches
        batch_size = 20000
        total_rows = 0
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during batch processing"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            total_rows += len(df_batch)
            
            # Filter to day range
            day_mask = (df_batch['ts'] >= day_start_dt) & (df_batch['ts'] <= day_end_dt)
            df_day = df_batch[day_mask].copy()
            
            if len(df_day) == 0:
                del df_batch, df_day
                gc.collect()
                continue
            
            # Ensure timestamps are timezone-aware
            if df_day['ts'].dt.tz is None:
                df_day['ts'] = df_day['ts'].dt.tz_localize('UTC')
            
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

def detect_beacons_strict(vwap_array, trade_counts, micro_trade_counts, valid_seconds, venue, date):
    """Detect beacon events using stricter criteria"""
    beacons = []
    
    # Price bands
    price_band_10 = 0.001  # ±0.10%
    price_band_25 = 0.0025  # ±0.25%
    
    # Trade thresholds
    min_trades_10s = 12
    min_micro_trades_10s = 6
    
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
        
        # Check if price is within ±0.10% of nearest $100 round level
        nearest_100 = round(current_price / 100) * 100
        price_diff_pct = abs(current_price - nearest_100) / nearest_100
        
        if price_diff_pct > price_band_10:
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
        if reversion_3m >= 10:  # 10 bps
            event_class = 'Signal'
        elif reversion_3m < 5:  # 5 bps
            event_class = 'Compression'
        else:
            event_class = 'Unclassified'
        
        # Check if within ±0.25% band
        within_25_band = price_diff_pct <= price_band_25
        
        # Create event key for deterministic sampling
        event_key = f"{date}_{venue}_{second}_{reversion_3m:.1f}"
        
        beacon = {
            'venue': venue,
            'date': date,
            'second': second,
            'price': current_price,
            'nearest_100': nearest_100,
            'price_diff_pct': price_diff_pct,
            'within_25_band': within_25_band,
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

def calculate_cross_venue_metrics(event, all_vwap_data, venues):
    """Calculate cross-venue metrics for an event"""
    event_second = event['second']
    event_venue = event['venue']
    event_date = event['date']
    
    # Get ±5-minute windows (300 seconds)
    window_start = max(0, event_second - 300)
    window_end = min(86400, event_second + 301)
    
    # Collect VWAP data for all venues
    venue_vwaps = {}
    for venue in venues:
        if venue in all_vwap_data[event_date]:
            vwap_data = all_vwap_data[event_date][venue]
            window_vwap = vwap_data['vwap_array'][window_start:window_end]
            window_valid = vwap_data['valid_seconds'][window_start:window_end]
            venue_vwaps[venue] = {
                'vwap': window_vwap,
                'valid': window_valid
            }
    
    if len(venue_vwaps) < 2:
        return None
    
    # Calculate lag using cross-correlation
    lag_result = calculate_cross_correlation_lag(venue_vwaps, event_venue)
    
    # Calculate dispersion change
    dispersion_result = calculate_dispersion_change(venue_vwaps, event_second - window_start)
    
    # Calculate leadership
    leadership_result = calculate_leadership(venue_vwaps, event_venue, event['reversion_3m'], event_second - window_start)
    
    return {
        'lag_ms': lag_result['lag_ms'],
        'correlation': lag_result['correlation'],
        'dispersion_change': dispersion_result,
        'leader': leadership_result['leader'],
        'lead_time_ms': leadership_result['lead_time_ms']
    }

def calculate_cross_correlation_lag(venue_vwaps, reference_venue):
    """Calculate cross-correlation lag between reference venue and others"""
    if reference_venue not in venue_vwaps:
        return {'lag_ms': 0, 'correlation': 0}
    
    ref_vwap = venue_vwaps[reference_venue]['vwap']
    ref_valid = venue_vwaps[reference_venue]['valid']
    
    # Find overlapping valid seconds
    valid_mask = ref_valid
    for venue, data in venue_vwaps.items():
        if venue != reference_venue:
            valid_mask = valid_mask & data['valid']
    
    if np.sum(valid_mask) < 10:
        return {'lag_ms': 0, 'correlation': 0}
    
    # Get overlapping data
    ref_overlap = ref_vwap[valid_mask]
    
    # Calculate correlation with other venues
    best_lag = 0
    best_corr = 0
    
    for venue, data in venue_vwaps.items():
        if venue == reference_venue:
            continue
        
        other_overlap = data['vwap'][valid_mask]
        
        # Search lags within ±3 seconds
        for lag in range(-3, 4):
            if lag == 0:
                corr = np.corrcoef(ref_overlap, other_overlap)[0, 1]
            elif lag > 0:
                if len(ref_overlap) > lag:
                    corr = np.corrcoef(ref_overlap[:-lag], other_overlap[lag:])[0, 1]
                else:
                    continue
            else:
                if len(ref_overlap) > abs(lag):
                    corr = np.corrcoef(ref_overlap[abs(lag):], other_overlap[:-abs(lag)])[0, 1]
                else:
                    continue
            
            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag
    
    return {'lag_ms': best_lag * 1000, 'correlation': best_corr}

def calculate_dispersion_change(venue_vwaps, event_offset):
    """Calculate dispersion change pre→post 3 minutes"""
    # Pre-event: 3 minutes before
    pre_start = max(0, event_offset - 180)
    pre_end = event_offset
    
    # Post-event: 3 minutes after
    post_start = event_offset + 1
    post_end = min(len(list(venue_vwaps.values())[0]['vwap']), event_offset + 181)
    
    if pre_end - pre_start < 60 or post_end - post_start < 60:
        return 0
    
    # Calculate pre-event dispersion
    pre_dispersion = calculate_dispersion_window(venue_vwaps, pre_start, pre_end)
    
    # Calculate post-event dispersion
    post_dispersion = calculate_dispersion_window(venue_vwaps, post_start, post_end)
    
    return post_dispersion - pre_dispersion

def calculate_dispersion_window(venue_vwaps, start, end):
    """Calculate price dispersion across venues for a time window"""
    venue_means = []
    
    for venue, data in venue_vwaps.items():
        window_vwap = data['vwap'][start:end]
        window_valid = data['valid'][start:end]
        
        if np.sum(window_valid) > 0:
            valid_prices = window_vwap[window_valid]
            venue_means.append(np.mean(valid_prices))
    
    if len(venue_means) < 2:
        return 0
    
    # Calculate dispersion as standard deviation of venue means
    dispersion = np.std(venue_means)
    return dispersion

def calculate_leadership(venue_vwaps, reference_venue, reversion_3m, event_offset):
    """Calculate leadership (first venue to move in direction of reversion)"""
    if reference_venue not in venue_vwaps:
        return {'leader': 'unknown', 'lead_time_ms': 0}
    
    ref_vwap = venue_vwaps[reference_venue]['vwap']
    ref_valid = venue_vwaps[reference_venue]['valid']
    
    if not ref_valid[event_offset] or event_offset >= len(ref_vwap):
        return {'leader': 'unknown', 'lead_time_ms': 0}
    
    event_price = ref_vwap[event_offset]
    direction = 1 if reversion_3m > 0 else -1
    threshold = 0.5 / 10000  # 0.5 bps
    
    # Look for first venue to cross threshold
    for venue, data in venue_vwaps.items():
        if venue == reference_venue:
            continue
        
        venue_vwap = data['vwap']
        venue_valid = data['valid']
        
        # Check next 60 seconds
        for i in range(1, min(61, len(venue_vwap) - event_offset)):
            check_idx = event_offset + i
            if check_idx >= len(venue_vwap) or not venue_valid[check_idx]:
                continue
            
            price_change = (venue_vwap[check_idx] - event_price) / event_price
            if direction * price_change >= threshold:
                return {'leader': venue, 'lead_time_ms': i * 1000}
    
    return {'leader': 'none', 'lead_time_ms': 0}

def run_rcb_v2_fix_verify():
    """Run RCB v2 fix and verify on test days"""
    print("🔍 RCB v2 (Fix & Verify) - Test Days: 2025-09-01 & 2025-09-02")
    print("=" * 70)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    test_dates = ["20250901", "20250902"]
    
    print(f"📅 Processing {len(test_dates)} test days: {test_dates}")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    all_beacons = []
    all_vwap_data = {}
    warnings = []
    
    # Process each test day
    for date in test_dates:
        print(f"\n📊 Processing {date}...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded before processing {date}")
            return False
        
        day_vwap_data = {}
        day_beacons = []
        
        # Build VWAP and micro-trade counts for all venues
        for venue in venues:
            print(f"  🔍 Processing {venue}...")
            
            vwap_data, error = build_vwap_and_micro_trades(venue, date)
            if error:
                print(f"    ❌ {error}")
                if "Coverage too low" in error:
                    warnings.append(f"{venue} {date}: {error}")
                    return False
                return False
            
            day_vwap_data[venue] = vwap_data
            
            print(f"    ✅ {vwap_data['total_rows']:,} rows, {vwap_data['coverage_pct']:.1f}% coverage")
            
            # Detect beacons with stricter criteria
            beacons = detect_beacons_strict(
                vwap_data['vwap_array'],
                vwap_data['trade_counts'],
                vwap_data['micro_trade_counts'],
                vwap_data['valid_seconds'],
                venue,
                date
            )
            
            day_beacons.extend(beacons)
            print(f"    📊 Detected {len(beacons)} beacons")
        
        # Check event count limit
        if len(day_beacons) > 120:
            print(f"    ⚠️  Event count > 120, sampling to 24...")
            # Deterministic sampling preserving class mix
            class_counts = defaultdict(int)
            for beacon in day_beacons:
                class_counts[beacon['class']] += 1
            
            sampled_beacons = []
            for event_class in ['Signal', 'Compression', 'Unclassified']:
                class_beacons = [b for b in day_beacons if b['class'] == event_class]
                if len(class_beacons) > 0:
                    # Sample proportionally
                    target_count = max(1, int(24 * len(class_beacons) / len(day_beacons)))
                    for beacon in class_beacons:
                        event_key = beacon['event_key']
                        hash_val = int(hashlib.md5(event_key.encode()).hexdigest(), 16)
                        if hash_val % (len(class_beacons) // target_count + 1) == 0:
                            sampled_beacons.append(beacon)
                            if len(sampled_beacons) >= 24:
                                break
                    if len(sampled_beacons) >= 24:
                        break
            
            day_beacons = sampled_beacons[:24]
            print(f"    📊 Sampled to {len(day_beacons)} beacons")
        
        all_beacons.extend(day_beacons)
        all_vwap_data[date] = day_vwap_data
        
        print(f"  ✅ {date}: {len(day_beacons)} total beacons")
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
    
    # Calculate cross-venue metrics for all beacons
    print(f"\n🔍 Calculating cross-venue metrics for {len(all_beacons)} beacons...")
    
    for beacon in all_beacons:
        metrics = calculate_cross_venue_metrics(beacon, all_vwap_data, venues)
        if metrics:
            beacon.update(metrics)
        else:
            beacon.update({
                'lag_ms': 0,
                'correlation': 0,
                'dispersion_change': 0,
                'leader': 'unknown',
                'lead_time_ms': 0
            })
    
    # Generate outputs
    print(f"\n📊 A) Beacon Counts by Class:")
    beacon_counts = defaultdict(lambda: defaultdict(int))
    
    for beacon in all_beacons:
        key = f"{beacon['venue']}_{beacon['date']}"
        beacon_counts[key][beacon['class']] += 1
    
    for key in sorted(beacon_counts.keys()):
        venue, date = key.split('_')
        counts = beacon_counts[key]
        total = sum(counts.values())
        print(f"  {venue} {date}: {total} total ({counts.get('Signal', 0)} Signal, {counts.get('Compression', 0)} Compression, {counts.get('Unclassified', 0)} Unclassified)")
    
    # B) Medians per class
    print(f"\n📊 B) Event Metrics by Class:")
    class_metrics = defaultdict(list)
    
    for beacon in all_beacons:
        class_metrics[beacon['class']].append({
            'reversion_3m': beacon['reversion_3m'],
            'trades_in_10s': beacon['trades_in_10s'],
            'micro_trades_in_10s': beacon['micro_trades_in_10s'],
            'within_25_band': beacon['within_25_band']
        })
    
    for event_class in ['Signal', 'Compression', 'Unclassified']:
        if event_class in class_metrics:
            metrics = class_metrics[event_class]
            reversions = [m['reversion_3m'] for m in metrics]
            trades = [m['trades_in_10s'] for m in metrics]
            micro_trades = [m['micro_trades_in_10s'] for m in metrics]
            within_25 = [m['within_25_band'] for m in metrics]
            
            print(f"  {event_class.upper()}:")
            print(f"    Reversion: {np.median(reversions):.1f} bps (IQR: {np.percentile(reversions, 75) - np.percentile(reversions, 25):.1f})")
            print(f"    Trades in 10s: {np.median(trades):.1f} (IQR: {np.percentile(trades, 75) - np.percentile(trades, 25):.1f})")
            print(f"    Micro trades: {np.median(micro_trades):.1f} (IQR: {np.percentile(micro_trades, 75) - np.percentile(micro_trades, 25):.1f})")
            print(f"    Within ±0.25% band: {np.mean(within_25)*100:.1f}%")
    
    # C) Cross-venue metrics
    print(f"\n📊 C) Cross-Venue Metrics:")
    lags = [b['lag_ms'] for b in all_beacons]
    correlations = [b['correlation'] for b in all_beacons]
    dispersion_changes = [b['dispersion_change'] for b in all_beacons]
    
    print(f"  Lag: {np.median(lags):.1f} ms (IQR: {np.percentile(lags, 75) - np.percentile(lags, 25):.1f})")
    print(f"  Correlation: {np.median(correlations):.3f} (IQR: {np.percentile(correlations, 75) - np.percentile(correlations, 25):.3f})")
    print(f"  Dispersion change: {np.median(dispersion_changes):.6f} (IQR: {np.percentile(dispersion_changes, 75) - np.percentile(dispersion_changes, 25):.6f})")
    
    # D) Leadership analysis
    print(f"\n📊 D) Leadership Analysis (Signal events only):")
    signal_events = [b for b in all_beacons if b['class'] == 'Signal']
    leadership_counts = defaultdict(int)
    lead_times = defaultdict(list)
    
    for event in signal_events:
        leader = event['leader']
        if leader != 'unknown' and leader != 'none':
            leadership_counts[leader] += 1
            lead_times[leader].append(event['lead_time_ms'])
    
    for venue in venues:
        count = leadership_counts[venue]
        if count > 0:
            mean_time = np.mean(lead_times[venue])
            print(f"  {venue}: {count} leads, mean lead time: {mean_time:.1f} ms")
        else:
            print(f"  {venue}: 0 leads")
    
    # E) Top/Bottom events
    print(f"\n📊 E) Top/Bottom Events by Reversion:")
    sorted_beacons = sorted(all_beacons, key=lambda x: x['reversion_3m'], reverse=True)
    
    print(f"  Top 3 by reversion:")
    for i, beacon in enumerate(sorted_beacons[:3]):
        print(f"    {i+1}. {beacon['date']} {beacon['venue']} {beacon['second']}s: {beacon['reversion_3m']:.1f} bps ({beacon['trades_in_10s']}/{beacon['micro_trades_in_10s']} trades, {beacon['lag_ms']:.0f}ms lag, {beacon['class']})")
    
    print(f"  Bottom 3 by reversion:")
    for i, beacon in enumerate(sorted_beacons[-3:]):
        print(f"    {i+1}. {beacon['date']} {beacon['venue']} {beacon['second']}s: {beacon['reversion_3m']:.1f} bps ({beacon['trades_in_10s']}/{beacon['micro_trades_in_10s']} trades, {beacon['lag_ms']:.0f}ms lag, {beacon['class']})")
    
    # F) Warnings
    print(f"\n📊 F) Warnings:")
    if warnings:
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    else:
        print(f"  ✅ No warnings or STOP conditions encountered")
    
    print(f"\n✅ RCB v2 fix and verify completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_rcb_v2_fix_verify()
    
    if success:
        print(f"\n🎉 RCB v2 fix and verify completed successfully.")
        print(f"Please review results and provide approval for full Week 1.")
    else:
        print(f"\n❌ RCB v2 fix and verify failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




