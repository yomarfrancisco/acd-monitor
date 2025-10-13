#!/usr/bin/env python3
"""
Week-3 Leadership Dynamics Analysis for 2025-08-11
Step-3: Identify leader venues and analyze dynamics
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

def find_leader_venue(event_ts, venue_data, venues, lead_threshold_bps=2.0, hold_duration_s=3.0, window_s=10.0):
    """Find the leader venue for a given event using Rotemberg-Saloner style detection"""
    
    # Define analysis window
    window_start = event_ts
    window_end = event_ts + pd.Timedelta(seconds=window_s)
    
    venue_returns = {}
    venue_lead_times = {}
    venue_persistence = {}
    
    for venue in venues:
        df = venue_data[venue]
        
        # Get data in the window
        window_data = df[(df['ts'] >= window_start) & (df['ts'] <= window_end)]
        
        if len(window_data) < 10:  # Need sufficient data
            continue
        
        # Build 1-second VWAP bars
        vwap_bars = window_data.set_index('ts').resample('1S').apply(
            lambda x: np.average(x['price'], weights=x['size']) if len(x) > 0 else np.nan
        ).dropna()
        
        if len(vwap_bars) < 3:
            continue
        
        # Compute 1-second returns
        returns = vwap_bars.pct_change().dropna()
        
        # Find first sustained move
        cumulative_returns = returns.cumsum()
        
        # Look for first move >= threshold
        lead_time_ms = None
        persistence_s = 0
        
        for i, (timestamp, cum_ret) in enumerate(cumulative_returns.items()):
            if abs(cum_ret) >= (lead_threshold_bps / 10000):  # Convert bps to decimal
                # Check if the move is sustained
                remaining_data = cumulative_returns.iloc[i:]
                if len(remaining_data) >= hold_duration_s:
                    # Check if sign is maintained for hold_duration
                    sign = np.sign(cum_ret)
                    sustained = all(np.sign(remaining_data.iloc[:int(hold_duration_s)]) == sign)
                    
                    if sustained:
                        lead_time_ms = (timestamp - event_ts).total_seconds() * 1000
                        persistence_s = hold_duration_s
                        break
        
        venue_returns[venue] = returns
        venue_lead_times[venue] = lead_time_ms
        venue_persistence[venue] = persistence_s
    
    # Find the venue with earliest lead time
    valid_leaders = {venue: lead_time for venue, lead_time in venue_lead_times.items() 
                    if lead_time is not None}
    
    if not valid_leaders:
        return 'NONE', None, None, None
    
    leader_venue = min(valid_leaders.keys(), key=lambda x: valid_leaders[x])
    lead_time_ms = valid_leaders[leader_venue]
    persistence_s = venue_persistence[leader_venue]
    
    # Compute follow-through rate (simplified)
    leader_returns = venue_returns[leader_venue]
    if len(leader_returns) > 0:
        follow_through_rate = np.mean(np.abs(leader_returns))
    else:
        follow_through_rate = 0
    
    return leader_venue, lead_time_ms, persistence_s, follow_through_rate

def analyze_convergence_divergence(event_ts, venue_data, venues, window_minutes=3):
    """Analyze convergence vs divergence outcomes"""
    
    # Define pre and post windows
    pre_start = event_ts - pd.Timedelta(minutes=window_minutes)
    pre_end = event_ts
    post_start = event_ts
    post_end = event_ts + pd.Timedelta(minutes=window_minutes)
    
    pre_prices = {}
    post_prices = {}
    
    for venue in venues:
        df = venue_data[venue]
        
        # Get pre-event data
        pre_data = df[(df['ts'] >= pre_start) & (df['ts'] < pre_end)]
        if len(pre_data) > 0:
            pre_prices[venue] = np.mean(pre_data['price'])
        
        # Get post-event data
        post_data = df[(df['ts'] >= post_start) & (df['ts'] <= post_end)]
        if len(post_data) > 0:
            post_prices[venue] = np.mean(post_data['price'])
    
    if len(pre_prices) < 2 or len(post_prices) < 2:
        return 'INSUFFICIENT_DATA', 0, 0
    
    # Compute price dispersion
    pre_dispersion = np.std(list(pre_prices.values()))
    post_dispersion = np.std(list(post_prices.values()))
    
    # Determine outcome
    if post_dispersion < pre_dispersion * 0.95:  # 5% threshold
        outcome = 'CONVERGENCE'
    elif post_dispersion > pre_dispersion * 1.05:
        outcome = 'DIVERGENCE'
    else:
        outcome = 'NEUTRAL'
    
    return outcome, pre_dispersion, post_dispersion

def main():
    print("🔍 Step-3 Leadership Dynamics Analysis for 2025-08-11")
    print("=" * 60)
    print("Mode: STRICT READ-ONLY, no synthetic data")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250811'
    
    # Load venue data
    print("Loading venue data...")
    venue_data = {}
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
        df = pd.read_parquet(file_path)
        df['ts'] = pd.to_datetime(df['ts'], utc=True)
        venue_data[venue] = df
        print(f"  {venue}: {len(df):,} ticks")
    
    # Load beacon data
    print("\nLoading beacon data...")
    beacon_cache_path = "data_v6/cache/beacons/week-3"
    all_beacons = []
    
    for venue in venues:
        beacon_file = os.path.join(beacon_cache_path, f"{venue}_{date_str}.parquet")
        if os.path.exists(beacon_file):
            beacons_df = pd.read_parquet(beacon_file)
            beacons_df['event_ts'] = pd.to_datetime(beacons_df['event_ts'], utc=True)
            all_beacons.extend(beacons_df.to_dict('records'))
            print(f"  {venue}: {len(beacons_df)} beacons")
    
    print(f"\nTotal beacons: {len(all_beacons)}")
    
    # Analyze leadership dynamics
    print("\nAnalyzing leadership dynamics...")
    leadership_results = []
    
    for i, beacon in enumerate(all_beacons):
        if i % 20 == 0:
            print(f"  Processing beacon {i+1}/{len(all_beacons)}...")
        
        event_ts = beacon['event_ts']
        venue = beacon['venue']
        
        # Find leader
        leader_venue, lead_time_ms, persistence_s, follow_through_rate = find_leader_venue(
            event_ts, venue_data, venues
        )
        
        # Analyze convergence/divergence
        outcome, pre_disp, post_disp = analyze_convergence_divergence(
            event_ts, venue_data, venues
        )
        
        leadership_results.append({
            'event_ts': event_ts,
            'venue': venue,
            'leader_venue': leader_venue,
            'lead_time_ms': lead_time_ms,
            'persistence_s': persistence_s,
            'follow_through_rate': follow_through_rate,
            'outcome': outcome,
            'pre_dispersion': pre_disp,
            'post_dispersion': post_disp
        })
    
    # Filter successful analyses
    successful_results = [r for r in leadership_results if r['leader_venue'] != 'NONE']
    
    print(f"\nSuccessful leadership analyses: {len(successful_results)}/{len(leadership_results)}")
    
    if len(successful_results) == 0:
        print("❌ No successful leadership analyses found")
        return
    
    # Compute summary statistics
    lead_times = [r['lead_time_ms'] for r in successful_results if r['lead_time_ms'] is not None]
    persistence_times = [r['persistence_s'] for r in successful_results if r['persistence_s'] is not None]
    follow_through_rates = [r['follow_through_rate'] for r in successful_results]
    
    # Leader venue distribution
    leader_counts = {}
    for r in successful_results:
        leader = r['leader_venue']
        leader_counts[leader] = leader_counts.get(leader, 0) + 1
    
    # Outcome distribution
    outcome_counts = {}
    for r in leadership_results:
        outcome = r['outcome']
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    
    # Print results table
    print(f"\n📊 LEADERSHIP DYNAMICS SUMMARY - 2025-08-11")
    print("=" * 60)
    print(f"{'Metric':<25} {'Value':<15} {'Details':<20}")
    print("-" * 60)
    print(f"{'Total Events':<25} {len(leadership_results):<15} {'All beacon events':<20}")
    print(f"{'Successful Analyses':<25} {len(successful_results):<15} {'With clear leaders':<20}")
    print(f"{'Median Lead Time':<25} {np.median(lead_times):.1f} ms{'':<10} {'First mover detection':<20}")
    print(f"{'Median Persistence':<25} {np.median(persistence_times):.1f} s{'':<10} {'Sustained movement':<20}")
    print(f"{'Median Follow-through':<25} {np.median(follow_through_rates)*10000:.1f} bps{'':<10} {'Return magnitude':<20}")
    print()
    
    # Leader venue distribution
    print(f"{'Leader Venue Distribution':<25}")
    print("-" * 40)
    for venue, count in sorted(leader_counts.items()):
        pct = (count / len(successful_results)) * 100
        print(f"  {venue:<15} {count:>3} events ({pct:>5.1f}%)")
    print()
    
    # Outcome distribution
    print(f"{'Convergence/Divergence Outcomes':<25}")
    print("-" * 40)
    for outcome, count in sorted(outcome_counts.items()):
        pct = (count / len(leadership_results)) * 100
        print(f"  {outcome:<15} {count:>3} events ({pct:>5.1f}%)")
    
    # Narrative interpretation
    print(f"\n📝 NARRATIVE INTERPRETATION")
    print("=" * 60)
    
    success_rate = (len(successful_results) / len(leadership_results)) * 100
    median_lead_time = np.median(lead_times)
    median_persistence = np.median(persistence_times)
    median_follow_through = np.median(follow_through_rates) * 10000
    
    print(f"Leadership Detection: {success_rate:.1f}% of events showed clear leadership patterns.")
    print(f"Market Responsiveness: Median lead time of {median_lead_time:.1f} ms indicates rapid price discovery.")
    print(f"Movement Persistence: {median_persistence:.1f} s median persistence suggests sustained directional moves.")
    print(f"Follow-through Strength: {median_follow_through:.1f} bps median follow-through indicates meaningful price impact.")
    
    # Dominant leader analysis
    dominant_leader = max(leader_counts.keys(), key=lambda x: leader_counts[x])
    dominant_pct = (leader_counts[dominant_leader] / len(successful_results)) * 100
    print(f"Market Leadership: {dominant_leader} emerged as the dominant leader ({dominant_pct:.1f}% of events).")
    
    # Outcome analysis
    convergence_pct = (outcome_counts.get('CONVERGENCE', 0) / len(leadership_results)) * 100
    divergence_pct = (outcome_counts.get('DIVERGENCE', 0) / len(leadership_results)) * 100
    
    if convergence_pct > divergence_pct:
        print(f"Market Dynamics: Convergence dominant ({convergence_pct:.1f}% vs {divergence_pct:.1f}% divergence) suggests coordinated price discovery.")
    else:
        print(f"Market Dynamics: Divergence dominant ({divergence_pct:.1f}% vs {convergence_pct:.1f}% convergence) suggests fragmented price discovery.")
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print("✅ Step-3 Leadership Dynamics Analysis completed for 2025-08-11")

if __name__ == "__main__":
    main()




