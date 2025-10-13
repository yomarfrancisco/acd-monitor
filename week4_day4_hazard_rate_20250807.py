#!/usr/bin/env python3
"""
Week-4 Day-4 Hazard Rate Analysis (2025-08-07)
Compute hazard rate (reaction probability per second conditional on non-reaction)
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

def load_beacon_cache(date_str, venues, cache_path="data_v6/cache/beacons/week-4"):
    """Load beacon cache for the specified date"""
    all_beacons = []
    
    for venue in venues:
        try:
            file_path = os.path.join(cache_path, f"{venue}_{date_str}.parquet")
            if os.path.exists(file_path):
                beacon_df = pd.read_parquet(file_path)
                beacon_df['event_ts'] = pd.to_datetime(beacon_df['event_ts'], utc=True)
                all_beacons.extend(beacon_df.to_dict('records'))
            else:
                print(f"⚠️ Warning: Beacon cache not found for {venue} {date_str}")
        except Exception as e:
            print(f"❌ Error loading beacon cache for {venue}: {str(e)}")
    
    return all_beacons

def load_venue_data(date_str, venues, base_path="data_v6/views"):
    """Load venue data for the specified date"""
    venue_data = {}
    
    for venue in venues:
        try:
            file_path = os.path.join(base_path, venue, date_str, "ticks_canonical.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                venue_data[venue] = df
            else:
                print(f"❌ Error: Data file not found for {venue} {date_str}")
                return None
        except Exception as e:
            print(f"❌ Error loading data for {venue}: {str(e)}")
            return None
    
    return venue_data

def compute_reaction_times(event_ts, venue_data, venues, reaction_threshold_bps=0.5):
    """Compute reaction times for all venues to a beacon event"""
    reaction_times = {}
    
    for venue in venues:
        df = venue_data[venue]
        
        # Define analysis window: 15 seconds after event
        window_start = event_ts
        window_end = event_ts + pd.Timedelta(seconds=15)
        
        # Get data in the window
        window_data = df[(df['ts'] >= window_start) & (df['ts'] <= window_end)]
        
        if len(window_data) < 2:
            reaction_times[venue] = None
            continue
        
        # Get baseline price (last price before event)
        baseline_data = df[df['ts'] < event_ts]
        if len(baseline_data) == 0:
            reaction_times[venue] = None
            continue
        
        baseline_price = baseline_data['price'].iloc[-1]
        
        # Find first significant price movement
        reaction_time = None
        
        for i, row in window_data.iterrows():
            price_change_bps = abs((row['price'] - baseline_price) / baseline_price) * 10000
            
            if price_change_bps >= reaction_threshold_bps:
                reaction_time = (row['ts'] - event_ts).total_seconds()
                break
        
        reaction_times[venue] = reaction_time
    
    return reaction_times

def compute_hazard_rate(all_beacons, venue_data, venues, max_time=15.0, time_step=0.1):
    """Compute hazard rate for venue reactions"""
    print(f"🔍 Computing Hazard Rate")
    print("-" * 50)
    
    # Create time grid
    time_grid = np.arange(0, max_time + time_step, time_step)
    
    # Initialize arrays to track survivors and events
    n_events = len(all_beacons)
    n_venues = len(venues)
    total_observations = n_events * n_venues
    
    # Track reactions at each time point
    reactions_by_time = np.zeros(len(time_grid))
    survivors_by_time = np.zeros(len(time_grid))
    
    print(f"Processing {n_events} events across {n_venues} venues...")
    
    for i, beacon in enumerate(all_beacons):
        if i % 20 == 0:
            print(f"  Processing event {i+1}/{n_events}...")
        
        event_ts = beacon['event_ts']
        reaction_times = compute_reaction_times(event_ts, venue_data, venues)
        
        # For each venue, track when it reacts (or doesn't)
        for venue in venues:
            reaction_time = reaction_times[venue]
            
            # Find the time grid index for this reaction
            if reaction_time is not None:
                # Venue reacted - find the time bin
                time_idx = int(reaction_time / time_step)
                if time_idx < len(time_grid):
                    reactions_by_time[time_idx] += 1
            
            # Count survivors at each time point
            for t_idx, t in enumerate(time_grid):
                if reaction_time is None or reaction_time > t:
                    survivors_by_time[t_idx] += 1
    
    # Compute hazard rate: h(t) = events(t) / survivors(t)
    hazard_rate = np.zeros(len(time_grid))
    for i in range(len(time_grid)):
        if survivors_by_time[i] > 0:
            hazard_rate[i] = reactions_by_time[i] / survivors_by_time[i]
        else:
            hazard_rate[i] = 0
    
    return time_grid, hazard_rate, reactions_by_time, survivors_by_time

def compute_venue_specific_hazard_rates(all_beacons, venue_data, venues, max_time=15.0, time_step=0.1):
    """Compute hazard rate for each venue separately"""
    print(f"🔍 Computing Venue-Specific Hazard Rates")
    print("-" * 50)
    
    time_grid = np.arange(0, max_time + time_step, time_step)
    venue_hazard_rates = {}
    
    for venue in venues:
        print(f"  Processing {venue}...")
        
        n_events = len(all_beacons)
        reactions_by_time = np.zeros(len(time_grid))
        survivors_by_time = np.zeros(len(time_grid))
        
        for i, beacon in enumerate(all_beacons):
            event_ts = beacon['event_ts']
            reaction_times = compute_reaction_times(event_ts, venue_data, venues)
            reaction_time = reaction_times[venue]
            
            # Find the time grid index for this reaction
            if reaction_time is not None:
                time_idx = int(reaction_time / time_step)
                if time_idx < len(time_grid):
                    reactions_by_time[time_idx] += 1
            
            # Count survivors at each time point
            for t_idx, t in enumerate(time_grid):
                if reaction_time is None or reaction_time > t:
                    survivors_by_time[t_idx] += 1
        
        # Compute hazard rate for this venue
        hazard_rate = np.zeros(len(time_grid))
        for i in range(len(time_grid)):
            if survivors_by_time[i] > 0:
                hazard_rate[i] = reactions_by_time[i] / survivors_by_time[i]
            else:
                hazard_rate[i] = 0
        
        venue_hazard_rates[venue] = hazard_rate
    
    return time_grid, venue_hazard_rates

def analyze_hazard_rate_curve(time_grid, hazard_rate):
    """Analyze the hazard rate curve to determine if it decays or rises"""
    print(f"📊 Analyzing Hazard Rate Curve")
    print("-" * 50)
    
    # Smooth the hazard rate for analysis (moving average)
    window_size = 10  # 1 second window
    smoothed_hazard = np.convolve(hazard_rate, np.ones(window_size)/window_size, mode='valid')
    smoothed_time = time_grid[window_size-1:]
    
    # Compute trend analysis
    if len(smoothed_hazard) > 1:
        # Linear trend
        coeffs = np.polyfit(smoothed_time, smoothed_hazard, 1)
        slope = coeffs[0]
        
        # Early vs late comparison (first 5s vs last 5s)
        early_mask = smoothed_time <= 5.0
        late_mask = smoothed_time >= 10.0
        
        if np.any(early_mask) and np.any(late_mask):
            early_mean = np.mean(smoothed_hazard[early_mask])
            late_mean = np.mean(smoothed_hazard[late_mask])
            change_ratio = late_mean / early_mean if early_mean > 0 else 0
        else:
            early_mean = late_mean = change_ratio = 0
        
        # Peak analysis
        peak_idx = np.argmax(smoothed_hazard)
        peak_time = smoothed_time[peak_idx]
        peak_value = smoothed_hazard[peak_idx]
        
        return {
            'slope': slope,
            'early_mean': early_mean,
            'late_mean': late_mean,
            'change_ratio': change_ratio,
            'peak_time': peak_time,
            'peak_value': peak_value,
            'smoothed_time': smoothed_time,
            'smoothed_hazard': smoothed_hazard
        }
    
    return None

def print_hazard_rate_results(time_grid, hazard_rate, venue_hazard_rates, venues, trend_analysis):
    """Print comprehensive hazard rate results"""
    print(f"\n📊 HAZARD RATE ANALYSIS RESULTS")
    print("=" * 80)
    
    # Table 1: Overall Hazard Rate by Time
    print(f"\nTable 1: Overall Hazard Rate by Time")
    print(f"{'Time (s)':<10} {'Hazard Rate':<15} {'Cumulative Events':<20} {'Survivors':<15}")
    print("-" * 70)
    
    # Sample every 0.5 seconds for readability
    sample_indices = np.arange(0, len(time_grid), 5)  # Every 0.5s
    for i in sample_indices:
        if i < len(time_grid):
            t = time_grid[i]
            h = hazard_rate[i]
            events = np.sum(hazard_rate[:i+1] * np.diff(np.concatenate([[0], time_grid[:i+1]])))
            survivors = 384 - events  # 96 events * 4 venues
            print(f"{t:<10.1f} {h:<15.6f} {events:<20.1f} {survivors:<15.1f}")
    
    # Table 2: Venue-Specific Hazard Rates (at key time points)
    print(f"\nTable 2: Venue-Specific Hazard Rates at Key Time Points")
    print(f"{'Time (s)':<10} {'BINANCE':<12} {'COINBASE':<12} {'BYBITSPOT':<12} {'BITGET':<12}")
    print("-" * 70)
    
    key_times = [1.0, 3.0, 6.0, 9.0, 12.0, 15.0]
    for t in key_times:
        idx = int(t / 0.1)
        if idx < len(time_grid):
            rates = [venue_hazard_rates[venue][idx] for venue in venues]
            print(f"{t:<10.1f} {rates[0]:<12.6f} {rates[1]:<12.6f} {rates[2]:<12.6f} {rates[3]:<12.6f}")
    
    # Table 3: Trend Analysis
    if trend_analysis:
        print(f"\nTable 3: Hazard Rate Trend Analysis")
        print(f"{'Metric':<25} {'Value':<15}")
        print("-" * 40)
        print(f"{'Linear slope (per s)':<25} {trend_analysis['slope']:<15.6f}")
        print(f"{'Early mean (0-5s)':<25} {trend_analysis['early_mean']:<15.6f}")
        print(f"{'Late mean (10-15s)':<25} {trend_analysis['late_mean']:<15.6f}")
        print(f"{'Change ratio (late/early)':<25} {trend_analysis['change_ratio']:<15.3f}")
        print(f"{'Peak time (s)':<25} {trend_analysis['peak_time']:<15.1f}")
        print(f"{'Peak value':<25} {trend_analysis['peak_value']:<15.6f}")
    
    # Summary Insights
    print(f"\n📝 Key Insights:")
    
    if trend_analysis:
        slope = trend_analysis['slope']
        change_ratio = trend_analysis['change_ratio']
        
        if slope > 0.001:
            print(f"• Hazard rate RISES over time (slope: {slope:.6f} per second)")
        elif slope < -0.001:
            print(f"• Hazard rate DECAYS over time (slope: {slope:.6f} per second)")
        else:
            print(f"• Hazard rate is RELATIVELY CONSTANT (slope: {slope:.6f} per second)")
        
        if change_ratio > 1.2:
            print(f"• Late period (10-15s) shows {change_ratio:.1f}x higher hazard than early period")
        elif change_ratio < 0.8:
            print(f"• Late period (10-15s) shows {change_ratio:.1f}x lower hazard than early period")
        else:
            print(f"• Hazard rate remains relatively stable between early and late periods")
        
        print(f"• Peak hazard occurs at {trend_analysis['peak_time']:.1f} seconds")
        print(f"• Peak hazard value: {trend_analysis['peak_value']:.6f}")
    
    # Venue comparison
    print(f"\nVenue-Specific Patterns:")
    for venue in venues:
        venue_rates = venue_hazard_rates[venue]
        early_avg = np.mean(venue_rates[:50])  # First 5 seconds
        late_avg = np.mean(venue_rates[-50:])  # Last 5 seconds
        print(f"• {venue}: Early={early_avg:.6f}, Late={late_avg:.6f}, Ratio={late_avg/early_avg:.2f}")

def main():
    print("🔍 Week-4 Day-4 Hazard Rate Analysis (2025-08-07)")
    print("=" * 80)
    print("Mode: READ-ONLY, HAZARD RATE COMPUTATION")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250807'
    date_display = '2025-08-07'
    
    print(f"📅 Analyzing {date_display} ({date_str})")
    print("=" * 80)
    
    # Load beacon cache
    print("Loading beacon cache...")
    all_beacons = load_beacon_cache(date_str, venues)
    if not all_beacons:
        print("❌ No beacon data found - halting")
        return
    
    print(f"✅ Loaded {len(all_beacons)} beacon events")
    
    # Load venue data
    print("Loading venue data...")
    venue_data = load_venue_data(date_str, venues)
    if not venue_data:
        print("❌ Failed to load venue data - halting")
        return
    
    print(f"✅ Loaded data for {len(venue_data)} venues")
    
    # Compute overall hazard rate
    time_grid, hazard_rate, reactions_by_time, survivors_by_time = compute_hazard_rate(
        all_beacons, venue_data, venues, max_time=15.0, time_step=0.1
    )
    
    # Compute venue-specific hazard rates
    time_grid_venue, venue_hazard_rates = compute_venue_specific_hazard_rates(
        all_beacons, venue_data, venues, max_time=15.0, time_step=0.1
    )
    
    # Analyze hazard rate curve
    trend_analysis = analyze_hazard_rate_curve(time_grid, hazard_rate)
    
    # Print comprehensive results
    print_hazard_rate_results(time_grid, hazard_rate, venue_hazard_rates, venues, trend_analysis)
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print(f"HAZARD RATE ANALYSIS COMPLETE — awaiting next instructions.")

if __name__ == "__main__":
    main()




