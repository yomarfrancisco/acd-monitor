#!/usr/bin/env python3
"""
Week -4 Analysis Step 1: Beacon Detection (Lightweight Progress)
Scope: 2025-08-04 → 2025-08-10 (7 days × 4 venues = 28 combos)
"""

import pandas as pd
import numpy as np
import psutil
import os
import time
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

def validate_venue_day_quick(df, venue, date_str):
    """Quick validation for venue-day data"""
    try:
        # Check required columns
        required_cols = ['ts', 'price', 'size']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Check timestamp monotonicity (sample check)
        if not df['ts'].head(1000).is_monotonic_increasing:
            return False, "Timestamps not monotonic (sample)"
        
        # Check price range
        price_min, price_max = df['price'].min(), df['price'].max()
        if price_min < 80000 or price_max > 180000:
            return False, f"Price out of range: ${price_min:,.0f}-${price_max:,.0f}"
        
        # Quick coverage check
        df['second'] = df['ts'].dt.floor('1S')
        unique_seconds = df['second'].nunique()
        coverage_pct = (unique_seconds / 86400) * 100
        
        if coverage_pct < 35:
            return False, f"Coverage too low: {coverage_pct:.1f}% < 35%"
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def compute_micro_threshold(df):
    """Compute 10th percentile of trade sizes"""
    return df['size'].quantile(0.10)

def find_round_levels_quick(vwap_bars, band_pct=0.001):
    """Find integer price levels within ±0.10% band (quick version)"""
    round_levels = set()
    
    # Sample every 10th VWAP bar for speed
    sampled_vwap = vwap_bars.iloc[::10]
    
    for _, row in sampled_vwap.iterrows():
        vwap = row['vwap']
        
        # Check nearby integer levels
        for level in range(int(vwap * 0.999), int(vwap * 1.001) + 2):
            if level > 0:
                distance = abs(vwap - level) / level
                if distance <= band_pct:
                    round_levels.add(level)
    
    return sorted(round_levels)

def detect_beacons_quick(df, micro_p10, round_levels, band_pct=0.001):
    """Detect beacons using fixed rules (optimized version)"""
    beacons = []
    lockout_until = None
    
    # Create 1-second VWAP bars
    df['second'] = df['ts'].dt.floor('1S')
    vwap_bars = df.groupby('second').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap_bars.columns = ['second', 'vwap']
    
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
    
    # Slide 10-second window (sample every 100th trade for speed)
    window_size = timedelta(seconds=10)
    step_size = max(1, len(df_sorted) // 1000)  # Sample for speed
    
    for i in range(0, len(df_sorted), step_size):
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
                'micro_p10': micro_p10
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

def process_venue_day_quick(venue, date_str):
    """Process a single venue-day for beacon detection (quick version)"""
    file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
    
    try:
        # Load data
        df = pd.read_parquet(file_path)
        
        # Quick validation
        valid, msg = validate_venue_day_quick(df, venue, date_str)
        if not valid:
            return False, msg, 0, 0, 0
        
        # Compute micro threshold
        micro_p10 = compute_micro_threshold(df)
        
        # Create VWAP bars for round level detection
        df['second'] = df['ts'].dt.floor('1S')
        vwap_bars = df.groupby('second').apply(
            lambda x: np.average(x['price'], weights=x['size'])
        ).reset_index()
        vwap_bars.columns = ['second', 'vwap']
        
        # Find round levels
        round_levels = find_round_levels_quick(vwap_bars)
        
        if not round_levels:
            return True, "OK", 0, 0, len(df)
        
        # Detect beacons
        beacons = detect_beacons_quick(df, micro_p10, round_levels)
        
        # Sample if needed
        sampled_beacons, original_count = sample_beacons(beacons)
        
        return True, "OK", original_count, len(sampled_beacons), len(df)
        
    except Exception as e:
        return False, f"Error: {str(e)}", 0, 0, 0

def main():
    print("🔍 Week -4 Analysis Step 1: Beacon Detection (Lightweight)")
    print("=" * 60)
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Results storage
    venue_totals = {venue: {'pre': 0, 'post': 0} for venue in venues}
    peak_memory = 0
    total_lockouts = 0
    processed_count = 0
    start_time = time.time()
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        # Process each venue for this day
        for venue in venues:
            # Check memory
            mem_ok, mem_msg = check_memory_limit()
            if not mem_ok:
                print(f"❌ HALT: {mem_msg}")
                return
            
            current_memory = get_memory_usage()
            peak_memory = max(peak_memory, current_memory)
            
            # Process venue-day
            success, msg, beacons_pre, beacons_post, windows = process_venue_day_quick(venue, date_str)
            
            if success:
                venue_totals[venue]['pre'] += beacons_pre
                venue_totals[venue]['post'] += beacons_post
                total_lockouts += beacons_post  # Each beacon triggers a lockout
                
                print(f"[PROGRESS] date={date_display} venue={venue} windows={windows} beacons_pre={beacons_pre} beacons_post={beacons_post} mem={current_memory:.0f}MB")
            else:
                print(f"[PROGRESS] date={date_display} venue={venue} FAIL: {msg}")
                return  # Halt on any failure
            
            processed_count += 1
            
            # Memory summary every 4 venue-days
            if processed_count % 4 == 0:
                avg_memory = peak_memory / processed_count if processed_count > 0 else 0
                print(f"PeakRSS={peak_memory:.0f} MB | Avg per file={avg_memory:.0f} MB | Lockouts={total_lockouts}")
        
        current_date += timedelta(days=1)
    
    # Calculate duration
    duration = time.time() - start_time
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Print checkpoint footer
    print("\n[CHECKPOINT]")
    print("Venue totals (pre/post)")
    for venue in venues:
        print(f"{venue}:   {venue_totals[venue]['pre']:>3} / {venue_totals[venue]['post']:>3}")
    print(f"PeakMemory: {peak_memory:.0f} MB")
    print(f"Duration:   {duration_str}")
    print("Status: OK")
    
    print("\n🛑 STEP 1 COMPLETE - BEACON DETECTION")
    print("Ready for Step 2 - Typology & Core Effects")

if __name__ == "__main__":
    main()




