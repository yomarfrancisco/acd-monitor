#!/usr/bin/env python3
"""
Week-4 Day-4 Latency-Sensitivity Analysis (2025-08-07)
Compute cumulative venue reactions within 1s, 3s, 6s, 9s, 12s, 15s after each beacon
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

def compute_price_reaction_timing(event_ts, venue_data, venues, reaction_threshold_bps=0.5):
    """Compute when each venue reacts to a beacon event"""
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

def analyze_latency_sensitivity(all_beacons, venue_data, venues):
    """Analyze latency sensitivity across all beacon events"""
    print(f"🔍 Latency-Sensitivity Analysis")
    print("-" * 50)
    
    # Define time horizons
    horizons = [1, 3, 6, 9, 12, 15]  # seconds
    
    # Initialize results
    horizon_results = {h: [] for h in horizons}
    venue_reaction_times = {venue: [] for venue in venues}
    outlier_events = []
    
    print(f"Processing {len(all_beacons)} beacon events...")
    
    for i, beacon in enumerate(all_beacons):
        if i % 20 == 0:
            print(f"  Processing event {i+1}/{len(all_beacons)}...")
        
        event_ts = beacon['event_ts']
        
        # Compute reaction times for each venue
        reaction_times = compute_price_reaction_timing(event_ts, venue_data, venues)
        
        # Count venues that reacted within each horizon
        for horizon in horizons:
            reacted_venues = 0
            for venue, reaction_time in reaction_times.items():
                if reaction_time is not None and reaction_time <= horizon:
                    reacted_venues += 1
                    venue_reaction_times[venue].append(reaction_time)
            
            horizon_results[horizon].append(reacted_venues)
        
        # Identify outlier venues (reacting after 9s)
        late_reactors = []
        for venue, reaction_time in reaction_times.items():
            if reaction_time is not None and reaction_time > 9:
                late_reactors.append((venue, reaction_time))
        
        if late_reactors:
            outlier_events.append({
                'event_ts': event_ts,
                'venue': beacon['venue'],
                'late_reactors': late_reactors
            })
    
    return horizon_results, venue_reaction_times, outlier_events

def compute_summary_statistics(horizon_results, venue_reaction_times, venues):
    """Compute summary statistics for latency analysis"""
    print(f"📊 Computing Summary Statistics")
    print("-" * 50)
    
    # Horizon-based statistics
    horizon_stats = {}
    for horizon, reactions in horizon_results.items():
        if reactions:
            horizon_stats[horizon] = {
                'mean_venues_reacted': np.mean(reactions),
                'median_venues_reacted': np.median(reactions),
                'std_venues_reacted': np.std(reactions),
                'pct_venues_reacted': (np.mean(reactions) / len(venues)) * 100,
                'total_events': len(reactions)
            }
    
    # Venue-based statistics
    venue_stats = {}
    for venue, reaction_times in venue_reaction_times.items():
        if reaction_times:
            venue_stats[venue] = {
                'mean_reaction_time': np.mean(reaction_times),
                'median_reaction_time': np.median(reaction_times),
                'std_reaction_time': np.std(reaction_times),
                'min_reaction_time': np.min(reaction_times),
                'max_reaction_time': np.max(reaction_times),
                'total_reactions': len(reaction_times)
            }
        else:
            venue_stats[venue] = {
                'mean_reaction_time': None,
                'median_reaction_time': None,
                'std_reaction_time': None,
                'min_reaction_time': None,
                'max_reaction_time': None,
                'total_reactions': 0
            }
    
    return horizon_stats, venue_stats

def print_results(horizon_stats, venue_stats, outlier_events, venues):
    """Print comprehensive results"""
    print(f"\n📊 LATENCY-SENSITIVITY ANALYSIS RESULTS")
    print("=" * 80)
    
    # Table 1: Cumulative Venue Reactions by Horizon
    print(f"\nTable 1: Cumulative Venue Reactions by Time Horizon")
    print(f"{'Horizon (s)':<12} {'Mean Venues':<12} {'Median Venues':<14} {'% of Venues':<12} {'Std Dev':<10}")
    print("-" * 70)
    
    for horizon in sorted(horizon_stats.keys()):
        stats = horizon_stats[horizon]
        print(f"{horizon:<12} {stats['mean_venues_reacted']:<12.2f} {stats['median_venues_reacted']:<14.1f} {stats['pct_venues_reacted']:<12.1f} {stats['std_venues_reacted']:<10.2f}")
    
    # Table 2: Venue-Specific Reaction Times
    print(f"\nTable 2: Venue-Specific Reaction Time Statistics")
    print(f"{'Venue':<12} {'Mean (s)':<10} {'Median (s)':<12} {'Min (s)':<10} {'Max (s)':<10} {'Reactions':<10}")
    print("-" * 70)
    
    for venue in venues:
        stats = venue_stats[venue]
        if stats['total_reactions'] > 0:
            print(f"{venue:<12} {stats['mean_reaction_time']:<10.2f} {stats['median_reaction_time']:<12.2f} {stats['min_reaction_time']:<10.2f} {stats['max_reaction_time']:<10.2f} {stats['total_reactions']:<10}")
        else:
            print(f"{venue:<12} {'N/A':<10} {'N/A':<12} {'N/A':<10} {'N/A':<10} {'0':<10}")
    
    # Table 3: Outlier Events (Late Reactors)
    print(f"\nTable 3: Outlier Events (Venues Reacting After 9s)")
    print(f"{'Event Time':<20} {'Source Venue':<12} {'Late Reactors':<30}")
    print("-" * 70)
    
    if outlier_events:
        for event in outlier_events[:10]:  # Show first 10 outliers
            late_reactors_str = ", ".join([f"{venue}({time:.1f}s)" for venue, time in event['late_reactors']])
            print(f"{event['event_ts'].strftime('%H:%M:%S'):<20} {event['venue']:<12} {late_reactors_str:<30}")
        
        if len(outlier_events) > 10:
            print(f"... and {len(outlier_events) - 10} more outlier events")
    else:
        print("No outlier events found (no venues reacting after 9s)")
    
    # Summary Insights
    print(f"\n📝 Key Insights:")
    
    # Find fastest and slowest venues
    venue_means = {venue: stats['mean_reaction_time'] for venue, stats in venue_stats.items() 
                   if stats['mean_reaction_time'] is not None}
    
    if venue_means:
        fastest_venue = min(venue_means.keys(), key=lambda x: venue_means[x])
        slowest_venue = max(venue_means.keys(), key=lambda x: venue_means[x])
        
        print(f"• Fastest venue: {fastest_venue} (mean: {venue_means[fastest_venue]:.2f}s)")
        print(f"• Slowest venue: {slowest_venue} (mean: {venue_means[slowest_venue]:.2f}s)")
    
    # Reaction coverage analysis
    if 1 in horizon_stats and 15 in horizon_stats:
        coverage_1s = horizon_stats[1]['pct_venues_reacted']
        coverage_15s = horizon_stats[15]['pct_venues_reacted']
        print(f"• 1s coverage: {coverage_1s:.1f}% of venues react within 1 second")
        print(f"• 15s coverage: {coverage_15s:.1f}% of venues react within 15 seconds")
        print(f"• Coverage improvement: {coverage_15s - coverage_1s:.1f} percentage points from 1s to 15s")
    
    # Outlier analysis
    print(f"• Outlier events: {len(outlier_events)} events with venues reacting after 9s")
    if outlier_events:
        outlier_venues = set()
        for event in outlier_events:
            for venue, _ in event['late_reactors']:
                outlier_venues.add(venue)
        print(f"• Outlier venues: {', '.join(sorted(outlier_venues))}")

def main():
    print("🔍 Week-4 Day-4 Latency-Sensitivity Analysis (2025-08-07)")
    print("=" * 80)
    print("Mode: READ-ONLY, REACTION TIMING ANALYSIS")
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
    
    # Run latency sensitivity analysis
    horizon_results, venue_reaction_times, outlier_events = analyze_latency_sensitivity(
        all_beacons, venue_data, venues
    )
    
    # Compute summary statistics
    horizon_stats, venue_stats = compute_summary_statistics(
        horizon_results, venue_reaction_times, venues
    )
    
    # Print comprehensive results
    print_results(horizon_stats, venue_stats, outlier_events, venues)
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print(f"LATENCY-SENSITIVITY ANALYSIS COMPLETE — awaiting next instructions.")

if __name__ == "__main__":
    main()




