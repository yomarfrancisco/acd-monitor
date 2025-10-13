#!/usr/bin/env python3
"""
Phase 4: Causal Drift & Regime Test (Weeks 1–3)
Read-only, streaming, memory-safe causal drift analysis
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
from sklearn.linear_model import LinearRegression

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 300:
        print(f"⚠️  MEMORY_WARNING: {memory_mb:.1f} MB (soft limit 300MB)")
        if memory_mb >= 350:
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

def bootstrap_drift_test(week1_2_data, week3_data, n_bootstrap=2000):
    """Bootstrap test for regime drift"""
    if len(week1_2_data) == 0 or len(week3_data) == 0:
        return None, None, None, None
    
    # Combine weeks 1-2 data
    combined_week1_2 = np.array(week1_2_data)
    week3_array = np.array(week3_data)
    
    # Bootstrap samples
    bootstrap_diffs = []
    
    for _ in range(n_bootstrap):
        # Sample with replacement
        sample_week1_2 = np.random.choice(combined_week1_2, size=len(combined_week1_2), replace=True)
        sample_week3 = np.random.choice(week3_array, size=len(week3_array), replace=True)
        
        # Calculate difference in means
        diff = np.mean(sample_week3) - np.mean(sample_week1_2)
        bootstrap_diffs.append(diff)
    
    bootstrap_diffs = np.array(bootstrap_diffs)
    
    # Calculate statistics
    mean_delta_disp = np.mean(bootstrap_diffs)
    ci_lower = np.percentile(bootstrap_diffs, 2.5)
    ci_upper = np.percentile(bootstrap_diffs, 97.5)
    
    # Two-sided p-value
    p_value = 2 * min(
        np.mean(bootstrap_diffs <= 0),
        np.mean(bootstrap_diffs >= 0)
    )
    
    return mean_delta_disp, ci_lower, ci_upper, p_value

def calculate_cross_venue_residual_variance(week_vwap_data, venues):
    """Calculate cross-venue residual variance for a week"""
    weekly_residual_vars = []
    
    for date, day_vwap_data in week_vwap_data.items():
        if len(day_vwap_data) < 4:  # Need all 4 venues
            continue
        
        # Get BINANCE as reference
        if 'BINANCE' not in day_vwap_data:
            continue
        
        binance_vwap = day_vwap_data['BINANCE']['vwap_array']
        valid_binance = day_vwap_data['BINANCE']['valid_seconds']
        
        if np.sum(valid_binance) < 1000:  # Need sufficient data
            continue
        
        day_residual_vars = []
        
        for venue in venues:
            if venue == 'BINANCE' or venue not in day_vwap_data:
                continue
            
            venue_vwap = day_vwap_data[venue]['vwap_array']
            valid_venue = day_vwap_data[venue]['valid_seconds']
            
            # Find common valid seconds
            common_valid = valid_binance & valid_venue
            if np.sum(common_valid) < 100:  # Need sufficient overlap
                continue
            
            # Get valid data
            binance_valid = binance_vwap[common_valid]
            venue_valid = venue_vwap[common_valid]
            
            # Remove zeros
            non_zero_mask = (binance_valid > 0) & (venue_valid > 0)
            if np.sum(non_zero_mask) < 50:
                continue
            
            binance_clean = binance_valid[non_zero_mask]
            venue_clean = venue_valid[non_zero_mask]
            
            # Fit linear model: venue = alpha + beta * binance + epsilon
            try:
                X = binance_clean.reshape(-1, 1)
                y = venue_clean
                
                model = LinearRegression()
                model.fit(X, y)
                
                # Calculate residuals
                y_pred = model.predict(X)
                residuals = y - y_pred
                
                # Calculate residual variance
                residual_var = np.var(residuals)
                day_residual_vars.append(residual_var)
                
            except Exception as e:
                continue
        
        if len(day_residual_vars) > 0:
            weekly_residual_vars.extend(day_residual_vars)
    
    if len(weekly_residual_vars) == 0:
        return None
    
    return np.median(weekly_residual_vars)

def run_phase4_causal_drift_test():
    """Run Phase 4: Causal Drift & Regime Test"""
    print("🔍 Phase 4: Causal Drift & Regime Test (Weeks 1–3)")
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
    all_dispersion_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    all_vwap_data = {}
    
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
        
        # Determine week
        if day_idx < 7:
            week = 1
        elif day_idx < 14:
            week = 2
        else:
            week = 3
        
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
            
            # Calculate cross-venue effects
            if len(config_events) > 0:
                dispersion_changes = calculate_cross_venue_effects(config_events, all_vwap_data, venues)
                
                # Store by week, config, and class
                for event in config_events:
                    event_class = event['class']
                    all_dispersion_data[week][config_name][event_class].extend(dispersion_changes)
        
        # Clean up day data
        del day_vwap_data
        gc.collect()
        
        # Check memory after each day
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {date}")
            return False
    
    print(f"\n🔍 Data Preparation Complete")
    print(f"🧠 Memory usage: {get_memory_usage():.1f} MB")
    
    # 2️⃣ Bootstrapped Regime Drift Test
    print(f"\n🔍 Bootstrapped Regime Drift Test")
    print("=" * 50)
    
    drift_results = []
    
    for config_name in configs.keys():
        for event_class in ['Signal', 'Compression', 'Unclassified']:
            # Get data for weeks 1-2 and week 3
            week1_2_data = []
            week3_data = []
            
            # Combine weeks 1 and 2
            for week in [1, 2]:
                if week in all_dispersion_data and config_name in all_dispersion_data[week]:
                    week1_2_data.extend(all_dispersion_data[week][config_name][event_class])
            
            # Week 3
            if 3 in all_dispersion_data and config_name in all_dispersion_data[3]:
                week3_data = all_dispersion_data[3][config_name][event_class]
            
            if len(week1_2_data) == 0 or len(week3_data) == 0:
                continue
            
            print(f"  🔍 {config_name} {event_class}: Week 1-2: {len(week1_2_data)}, Week 3: {len(week3_data)}")
            
            # Run bootstrap test
            mean_delta_disp, ci_lower, ci_upper, p_value = bootstrap_drift_test(week1_2_data, week3_data)
            
            if mean_delta_disp is not None:
                # Calculate means
                week1_2_mean = np.mean(week1_2_data)
                week3_mean = np.mean(week3_data)
                
                # Determine verdict
                if abs(mean_delta_disp) > 0.25 and p_value < 0.05:
                    verdict = "significant drift"
                else:
                    verdict = "no significant drift"
                
                drift_results.append({
                    'config': config_name,
                    'class': event_class,
                    'week1_2_mean': week1_2_mean,
                    'week3_mean': week3_mean,
                    'delta_delta_disp': mean_delta_disp,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'p_value': p_value,
                    'verdict': verdict
                })
                
                print(f"    📊 ΔΔdisp: {mean_delta_disp:.6f}, 95% CI: [{ci_lower:.6f}, {ci_upper:.6f}], p: {p_value:.4f}")
    
    # 3️⃣ Cross-Venue Residual Variance
    print(f"\n🔍 Cross-Venue Residual Variance")
    print("=" * 50)
    
    # Group data by week
    week_vwap_data = {1: {}, 2: {}, 3: {}}
    
    for day_idx, date in enumerate(dates):
        if date in all_vwap_data:
            if day_idx < 7:
                week = 1
            elif day_idx < 14:
                week = 2
            else:
                week = 3
            
            week_vwap_data[week][date] = all_vwap_data[date]
    
    residual_vars = {}
    for week in [1, 2, 3]:
        if week in week_vwap_data:
            residual_var = calculate_cross_venue_residual_variance(week_vwap_data[week], venues)
            if residual_var is not None:
                residual_vars[week] = residual_var
                print(f"  Week {week} median residual variance: {residual_var:.6f}")
    
    # Calculate percentage changes
    residual_var_changes = {}
    for week in [2, 3]:
        if week in residual_vars and (week - 1) in residual_vars:
            prev_var = residual_vars[week - 1]
            curr_var = residual_vars[week]
            pct_change = ((curr_var - prev_var) / prev_var) * 100
            residual_var_changes[week] = pct_change
            print(f"  Week {week} vs Week {week-1} ΔVar: {pct_change:.1f}%")
    
    # 4️⃣ Outputs
    print(f"\n📊 Drift Test Results Table:")
    print("=" * 100)
    print(f"{'Config':<12} {'Class':<12} {'Week 1-2 mean':<12} {'Week 3 mean':<12} {'ΔΔdisp':<10} {'95% CI':<20} {'p':<8} {'Verdict':<20}")
    print("-" * 100)
    
    for result in drift_results:
        ci_str = f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]"
        print(f"{result['config']:<12} {result['class']:<12} {result['week1_2_mean']:<12.6f} {result['week3_mean']:<12.6f} {result['delta_delta_disp']:<10.6f} {ci_str:<20} {result['p_value']:<8.4f} {result['verdict']:<20}")
    
    # Summary paragraph
    print(f"\n🔍 Summary:")
    print("=" * 50)
    
    significant_drifts = [r for r in drift_results if r['verdict'] == 'significant drift']
    
    if len(significant_drifts) > 0:
        print(f"✅ CONVERGENCE MATERIALLY WEAKENED: {len(significant_drifts)} config×class combinations show significant drift.")
        print(f"The transition from convergence (Weeks 1-2) to divergence (Week 3) is statistically significant and persistent.")
        
        for drift in significant_drifts:
            print(f"  - {drift['config']} {drift['class']}: ΔΔdisp = {drift['delta_delta_disp']:.6f} (p = {drift['p_value']:.4f})")
    else:
        print(f"⚠️  CONVERGENCE WEAKENING UNCLEAR: No significant drift detected in any config×class combination.")
        print(f"The transition may be sampling noise rather than a persistent regime change.")
    
    # Residual variance analysis
    if len(residual_var_changes) > 0:
        median_var_change = np.median(list(residual_var_changes.values()))
        print(f"\nCross-venue residual variance analysis:")
        print(f"  Median ΔVar across weeks: {median_var_change:.1f}%")
        
        if median_var_change > 10:
            print(f"  → Increased residual variance suggests weakening cross-venue coordination")
        elif median_var_change < -10:
            print(f"  → Decreased residual variance suggests strengthening cross-venue coordination")
        else:
            print(f"  → Stable residual variance suggests consistent cross-venue coordination")
    
    print(f"\n✅ Phase 4: Causal Drift & Regime Test completed")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_phase4_causal_drift_test()
    
    if success:
        print(f"\n🎉 Phase 4: Causal Drift & Regime Test completed successfully.")
        print(f"Ready for downstream analysis and regime characterization.")
    else:
        print(f"\n❌ Phase 4: Causal Drift & Regime Test failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




