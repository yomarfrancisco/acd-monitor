#!/usr/bin/env python3
"""
Week -4 Analysis Step 1: Beacon Detection (Read-Only)
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

def validate_venue_day(df, venue, date_str):
    """Validate venue-day data meets requirements"""
    try:
        # Check required columns
        required_cols = ['ts', 'price', 'size']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}", None
        
        # Check timestamp monotonicity
        if not df['ts'].is_monotonic_increasing:
            return False, "Timestamps not monotonic", None
        
        # Check price range
        price_min, price_max = df['price'].min(), df['price'].max()
        if price_min < 80000 or price_max > 180000:
            return False, f"Price out of range: ${price_min:,.0f}-${price_max:,.0f}", None
        
        # Compute 1-second VWAP coverage
        df['second'] = df['ts'].dt.floor('1S')
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
        
        if coverage_pct < 35:
            return False, f"Coverage too low: {coverage_pct:.1f}% < 35%", None
        
        return True, "OK", {
            'coverage_pct': coverage_pct,
            'price_min': price_min,
            'price_max': price_max,
            'vwap_bars': vwap_bars
        }
        
    except Exception as e:
        return False, f"Validation error: {str(e)}", None

def compute_micro_threshold(df):
    """Compute 10th percentile of trade sizes"""
    return df['size'].quantile(0.10)

def find_round_levels(vwap_bars, band_pct=0.001):
    """Find integer price levels within ±0.10% band"""
    round_levels = set()
    
    for _, row in vwap_bars.iterrows():
        vwap = row['vwap']
        
        # Check nearby integer levels
        for level in range(int(vwap * 0.999), int(vwap * 1.001) + 2):
            if level > 0:  # Ensure positive
                distance = abs(vwap - level) / level
                if distance <= band_pct:
                    round_levels.add(level)
    
    return sorted(round_levels)

def detect_beacons(df, vwap_bars, micro_p10, round_levels, band_pct=0.001):
    """Detect beacons using fixed rules"""
    beacons = []
    lockout_until = None
    
    # Create round-eligible seconds
    round_eligible = set()
    for _, row in vwap_bars.iterrows():
        vwap = row['vwap']
        second = row['second']
        
        for level in round_levels:
            distance = abs(vwap - level) / level
            if distance <= band_pct:
                round_eligible.add(second)
                break
    
    # Sort by timestamp
    df_sorted = df.sort_values('ts').reset_index(drop=True)
    
    # Slide 10-second window
    window_size = timedelta(seconds=10)
    
    for i in range(len(df_sorted)):
        current_time = df_sorted.iloc[i]['ts']
        
        # Check lockout
        if lockout_until and current_time < lockout_until:
            continue
        
        # Define window
        window_start = current_time
        window_end = current_time + window_size
        
        # Get trades in window
        window_trades = df_sorted[
            (df_sorted['ts'] >= window_start) & 
            (df_sorted['ts'] < window_end)
        ]
        
        if len(window_trades) == 0:
            continue
        
        # Count micro trades
        micro_trades = window_trades[window_trades['size'] <= micro_p10]
        n_micro = len(micro_trades)
        
        # Check if window has round-eligible seconds
        window_seconds = pd.date_range(
            start=window_start.floor('1S'),
            end=window_end.floor('1S'),
            freq='1S'
        )
        
        has_round_eligible = any(sec in round_eligible for sec in window_seconds)
        
        # Beacon condition: ≥3 micro trades AND round-eligible
        if n_micro >= 3 and has_round_eligible:
            # Find the closest round level
            window_vwap = np.average(window_trades['price'], weights=window_trades['size'])
            closest_level = min(round_levels, key=lambda x: abs(x - window_vwap))
            
            beacon = {
                't_event': current_time,
                'level': closest_level,
                'n_trades_10s': len(window_trades),
                'n_micro_10s': n_micro,
                'micro_p10': micro_p10,
                'band': f"±{band_pct*100:.1f}%"
            }
            beacons.append(beacon)
            
            # Apply 60s lockout
            lockout_until = current_time + timedelta(seconds=60)
    
    return beacons

def sample_beacons(beacons, max_beacons=24, seed=1337):
    """Sample beacons if >120, down to 24 with deterministic seed"""
    if len(beacons) <= max_beacons:
        return beacons, len(beacons)
    
    # Deterministic sampling
    np.random.seed(seed)
    indices = np.random.choice(len(beacons), size=max_beacons, replace=False)
    sampled = [beacons[i] for i in sorted(indices)]
    
    return sampled, len(beacons)

def process_venue_day(venue, date_str, date_display):
    """Process a single venue-day for beacon detection"""
    file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
    
    try:
        # Load data
        df = pd.read_parquet(file_path)
        
        # Validate venue-day
        valid, msg, validation_data = validate_venue_day(df, venue, date_str)
        if not valid:
            return {
                'status': 'FAIL',
                'error': msg,
                'beacons': [],
                'candidates_found': 0,
                'sampled_kept': 0,
                'micro_p10': 0,
                'median_price': 0,
                'vwap_coverage': 0,
                'round_levels': [],
                'qa_counters': {}
            }
        
        # Compute micro threshold
        micro_p10 = compute_micro_threshold(df)
        
        # Find round levels
        round_levels = find_round_levels(validation_data['vwap_bars'])
        
        # Detect beacons
        beacons = detect_beacons(df, validation_data['vwap_bars'], micro_p10, round_levels)
        
        # Sample if needed
        sampled_beacons, original_count = sample_beacons(beacons)
        
        # QA counters
        qa_counters = {
            'seconds_evaluated': len(validation_data['vwap_bars']),
            'windows_evaluated': len(df),
            'lockouts_applied': len(beacons),  # Each beacon triggers a lockout
            'events_dropped_by_sampling': max(0, original_count - len(sampled_beacons)),
            'events_dropped_by_safeguards': 0  # Would be set if we had safeguard drops
        }
        
        return {
            'status': 'OK',
            'beacons': sampled_beacons,
            'candidates_found': original_count,
            'sampled_kept': len(sampled_beacons),
            'micro_p10': micro_p10,
            'median_price': df['price'].median(),
            'vwap_coverage': validation_data['coverage_pct'],
            'round_levels': round_levels,
            'qa_counters': qa_counters
        }
        
    except Exception as e:
        return {
            'status': 'FAIL',
            'error': f"Processing error: {str(e)}",
            'beacons': [],
            'candidates_found': 0,
            'sampled_kept': 0,
            'micro_p10': 0,
            'median_price': 0,
            'vwap_coverage': 0,
            'round_levels': [],
            'qa_counters': {}
        }

def main():
    print("🔍 Week -4 Analysis Step 1: Beacon Detection (Read-Only)")
    print("=" * 80)
    print("Scope: 2025-08-04 → 2025-08-10 (7 days × 4 venues = 28 combos)")
    print("Memory limits: Soft 600MB, Hard 750MB")
    print("Detection rules: 10s window, ±0.10% band, ≥3 micros, 60s lockout, cap=24")
    print()
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Results storage
    all_results = []
    anomalies = []
    peak_memory = 0
    
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
            'venues': {}
        }
        
        # Process each venue for this day
        for venue in venues:
            print(f"  📊 {venue}: ", end="")
            
            result = process_venue_day(venue, date_str, date_display)
            day_results['venues'][venue] = result
            
            if result['status'] == 'OK':
                print(f"✅ {result['candidates_found']} candidates → {result['sampled_kept']} kept")
                print(f"    📈 Micro p10: {result['micro_p10']:.6f}, Coverage: {result['vwap_coverage']:.1f}%")
            else:
                print(f"❌ {result['error']}")
                anomalies.append((venue, date_display, result['error']))
        
        # Check memory after processing day
        mem_ok, mem_msg = check_memory_limit()
        current_memory = get_memory_usage()
        peak_memory = max(peak_memory, current_memory)
        print(f"  💾 {mem_msg}")
        
        all_results.append(day_results)
        current_date += timedelta(days=1)
        print()
    
    # Print Step 1 Outputs
    print("=" * 80)
    print("✅ STEP 1 OUTPUTS - BEACON DETECTION")
    print("=" * 80)
    
    # A. Summary table (per day)
    print("A. Summary Table (per day):")
    print("Date       | Venue     | Candidates | Kept | Micro p10 | Median Price | Coverage%")
    print("-" * 80)
    
    for day_result in all_results:
        date = day_result['date']
        for venue in venues:
            if venue in day_result['venues']:
                result = day_result['venues'][venue]
                if result['status'] == 'OK':
                    print(f"{date} | {venue:>9} | {result['candidates_found']:>10} | {result['sampled_kept']:>4} | {result['micro_p10']:>8.6f} | ${result['median_price']:>11,.0f} | {result['vwap_coverage']:>8.1f}")
                else:
                    print(f"{date} | {venue:>9} | {'FAIL':>10} | {'N/A':>4} | {'N/A':>8} | {'N/A':>11} | {'N/A':>8}")
    
    print()
    
    # B. Round-level histogram (per day)
    print("B. Round-Level Histogram (per day):")
    for day_result in all_results:
        date = day_result['date']
        print(f"\n{date}:")
        print("Level    | Beacons | Share%")
        print("-" * 25)
        
        # Collect all beacons for this day
        day_beacons = []
        for venue in venues:
            if venue in day_result['venues'] and day_result['venues'][venue]['status'] == 'OK':
                day_beacons.extend(day_result['venues'][venue]['beacons'])
        
        if day_beacons:
            # Count beacons by level
            level_counts = {}
            for beacon in day_beacons:
                level = beacon['level']
                level_counts[level] = level_counts.get(level, 0) + 1
            
            total_beacons = len(day_beacons)
            for level in sorted(level_counts.keys()):
                count = level_counts[level]
                share = (count / total_beacons) * 100
                print(f"${level:>7,} | {count:>7} | {share:>6.1f}")
        else:
            print("No beacons detected")
    
    print()
    
    # C. QA counters (per day)
    print("C. QA Counters (per day):")
    for day_result in all_results:
        date = day_result['date']
        print(f"\n{date}:")
        print("Venue     | Seconds | Windows | Lockouts | Dropped (Sampling) | Dropped (Safeguards)")
        print("-" * 80)
        
        for venue in venues:
            if venue in day_result['venues'] and day_result['venues'][venue]['status'] == 'OK':
                qa = day_result['venues'][venue]['qa_counters']
                print(f"{venue:>9} | {qa['seconds_evaluated']:>7} | {qa['windows_evaluated']:>7} | {qa['lockouts_applied']:>8} | {qa['events_dropped_by_sampling']:>18} | {qa['events_dropped_by_safeguards']:>19}")
            else:
                print(f"{venue:>9} | {'N/A':>7} | {'N/A':>7} | {'N/A':>8} | {'N/A':>18} | {'N/A':>19}")
    
    print()
    
    # D. Anomaly log
    print("D. Anomaly Log:")
    if anomalies:
        print("Venue     | Date       | Issue")
        print("-" * 50)
        for venue, date, issue in anomalies:
            print(f"{venue:>9} | {date} | {issue}")
    else:
        print("No anomalies detected")
    
    print()
    
    # E. Checkpoint footer
    print("E. Checkpoint Footer:")
    
    # Total beacons by venue
    venue_totals = {venue: {'pre': 0, 'post': 0} for venue in venues}
    
    for day_result in all_results:
        for venue in venues:
            if venue in day_result['venues'] and day_result['venues'][venue]['status'] == 'OK':
                result = day_result['venues'][venue]
                venue_totals[venue]['pre'] += result['candidates_found']
                venue_totals[venue]['post'] += result['sampled_kept']
    
    print("Venue     | Pre-Sampling | Post-Sampling")
    print("-" * 40)
    for venue in venues:
        print(f"{venue:>9} | {venue_totals[venue]['pre']:>12} | {venue_totals[venue]['post']:>13}")
    
    print(f"\nPeak memory observed: {peak_memory:.1f} MB")
    
    print()
    print("🛑 STEP 1 COMPLETE - BEACON DETECTION")
    print("Ready for Step 2 - Typology & Core Effects")
    print("=" * 80)

if __name__ == "__main__":
    main()




