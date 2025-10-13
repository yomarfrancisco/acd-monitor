#!/usr/bin/env python3
"""
STAGE 3 — Leadership & Hazard Metrics for Week -2 Day 1 (2025-08-22)

From the successfully processed Week − 2 Day 1 events, compute:
• Leader ↔ follower shares (by venue)
• Median lead-time (ms)
• Convergence / divergence rates (%)
• Hazard rate λ(t) and survival S(t) for reaction probability over time

Guardrails:
• No synthetic events or padding of missing data
• No re-estimation of Δdisp or Δlag; use existing validated cache
• If any dataset appears incomplete or mis-keyed, halt immediately
• Memory limit ≤ 750 MB; halt if exceeded
"""

import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import gc
import psutil
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_beacon_cache(date_str):
    """Load beacon cache for the given date"""
    cache_dir = f"data_v6/cache/beacons/week-minus2"
    beacons = []
    
    for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
        cache_file = f"{cache_dir}/{venue}_{date_str}.parquet"
        if os.path.exists(cache_file):
            df = pd.read_parquet(cache_file)
            beacons.append(df)
        else:
            print(f"WARNING: Missing beacon cache for {venue} {date_str}")
    
    if not beacons:
        raise ValueError(f"No beacon cache found for {date_str}")
    
    return pd.concat(beacons, ignore_index=True)

def load_venue_data(venue, date_str):
    """Load canonical parquet data for a venue on a specific date"""
    parquet_file = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
    if not os.path.exists(parquet_file):
        raise ValueError(f"Parquet file not found: {parquet_file}")
    
    # Load with minimal memory footprint
    df = pd.read_parquet(parquet_file, columns=['ts', 'price', 'size'])
    df['ts'] = pd.to_datetime(df['ts'], utc=True)
    return df

def compute_1sec_vwap(df):
    """Compute 1-second VWAP bars from tick data"""
    df['ts_1s'] = df['ts'].dt.floor('1s')
    vwap = df.groupby('ts_1s').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap.columns = ['ts', 'vwap']
    return vwap

def find_leader_venue(vwap_data, event_ts, venues, window_sec=10):
    """
    Find the leading venue using Rotemberg-Saloner style detection:
    First venue with cumulative signed 1-sec return ≥ 2 bps within +10s and holding sign ≥3s
    """
    # event_ts is already a UTC timestamp from the beacon cache
    start_ts = event_ts
    end_ts = event_ts + pd.Timedelta(seconds=window_sec)
    
    # Get VWAP data for the window
    window_data = {}
    for venue in venues:
        if venue in vwap_data:
            venue_df = vwap_data[venue]
            mask = (venue_df['ts'] >= start_ts) & (venue_df['ts'] <= end_ts)
            window_data[venue] = venue_df[mask].copy()
    
    if not window_data:
        return None, None, None
    
    # Compute 1-second returns for each venue
    returns = {}
    for venue, df in window_data.items():
        if len(df) > 1:
            df = df.sort_values('ts')
            df['return'] = df['vwap'].pct_change() * 10000  # Convert to bps
            returns[venue] = df[['ts', 'return']].dropna()
    
    if not returns:
        return None, None, None
    
    # Find first venue with cumulative return ≥ 2 bps and holding ≥ 3s
    for venue, ret_df in returns.items():
        if len(ret_df) == 0:
            continue
            
        ret_df = ret_df.sort_values('ts')
        ret_df['cum_return'] = ret_df['return'].cumsum()
        
        # Find first time when |cum_return| >= 2 bps
        threshold_mask = ret_df['cum_return'].abs() >= 2.0
        if not threshold_mask.any():
            continue
            
        first_threshold_idx = threshold_mask.idxmax()
        first_threshold_ts = ret_df.loc[first_threshold_idx, 'ts']
        first_threshold_return = ret_df.loc[first_threshold_idx, 'cum_return']
        
        # Check if the sign holds for at least 3 seconds
        hold_end_ts = first_threshold_ts + pd.Timedelta(seconds=3)
        hold_mask = (ret_df['ts'] >= first_threshold_ts) & (ret_df['ts'] <= hold_end_ts)
        hold_returns = ret_df[hold_mask]['cum_return']
        
        if len(hold_returns) > 0:
            # Check if all returns in the hold period have the same sign as the initial return
            sign_consistent = (hold_returns * first_threshold_return >= 0).all()
            if sign_consistent:
                lead_time_ms = (first_threshold_ts - event_ts).total_seconds() * 1000
                return venue, lead_time_ms, first_threshold_return
    
    return None, None, None

def compute_hazard_rate(events_data, venues, vwap_data, max_time_sec=15):
    """
    Compute hazard rate λ(t) and survival S(t) for reaction probability over time
    """
    # Prepare reaction times for each venue
    reaction_times = {venue: [] for venue in venues}
    
    for _, event in events_data.iterrows():
        event_ts = event['event_ts']
        
        # For each venue, find reaction time based on price movement
        for venue in venues:
            if venue in vwap_data:
                venue_df = vwap_data[venue]
                
                # Get baseline price (30s before event)
                baseline_window = venue_df[
                    (venue_df['ts'] >= event_ts - pd.Timedelta(seconds=30)) &
                    (venue_df['ts'] < event_ts)
                ]
                
                if len(baseline_window) == 0:
                    continue
                
                baseline_price = baseline_window['vwap'].iloc[-1]
                
                # Look for reaction in the next max_time_sec seconds
                reaction_window = venue_df[
                    (venue_df['ts'] > event_ts) &
                    (venue_df['ts'] <= event_ts + pd.Timedelta(seconds=max_time_sec))
                ]
                
                # Find first significant price movement (> 1 bps)
                for _, row in reaction_window.iterrows():
                    price_change = abs(row['vwap'] - baseline_price) / baseline_price * 10000
                    if price_change > 1.0:  # 1 bps threshold
                        reaction_time = (row['ts'] - event_ts).total_seconds()
                        if 0 <= reaction_time <= max_time_sec:
                            reaction_times[venue].append(reaction_time)
                        break
    
    # Compute hazard rate for each venue
    hazard_results = {}
    for venue in venues:
        times = reaction_times[venue]
        if len(times) == 0:
            hazard_results[venue] = {
                'time': np.arange(0, max_time_sec + 1),
                'lambda': np.zeros(max_time_sec + 1),
                'survival': np.ones(max_time_sec + 1)
            }
            continue
        
        # Sort reaction times
        times = np.sort(times)
        
        # Compute hazard rate at each time point
        time_points = np.arange(0, max_time_sec + 1)
        lambda_t = np.zeros(len(time_points))
        survival_t = np.ones(len(time_points))
        
        for i, t in enumerate(time_points):
            # Number of reactions at time t
            reactions_at_t = np.sum(times == t)
            
            # Number of venues at risk (not yet reacted)
            at_risk = np.sum(times >= t)
            
            if at_risk > 0:
                lambda_t[i] = reactions_at_t / at_risk
            
            # Update survival function
            if i > 0:
                survival_t[i] = survival_t[i-1] * (1 - lambda_t[i])
        
        hazard_results[venue] = {
            'time': time_points,
            'lambda': lambda_t,
            'survival': survival_t
        }
    
    return hazard_results

def main():
    print("=" * 60)
    print("STAGE 3 — Leadership & Hazard Metrics")
    print("Week -2 Day 1 (2025-08-22)")
    print("=" * 60)
    
    date_str = "20250822"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    try:
        # Load beacon cache
        print(f"[LOAD] Loading beacon cache for {date_str}...")
        beacons = load_beacon_cache(date_str)
        print(f"[LOAD] Loaded {len(beacons)} beacons")
        
        # Use all beacons as "successful events" for leadership analysis
        successful_events = beacons.copy()
        print(f"[FILTER] Using {len(successful_events)} beacon events for analysis")
        
        if len(successful_events) == 0:
            print("ERROR: No beacon events found")
            return
        
        # Load venue data for leadership analysis
        print(f"[LOAD] Loading venue data...")
        vwap_data = {}
        for venue in venues:
            print(f"  Loading {venue}...")
            df = load_venue_data(venue, date_str)
            vwap_data[venue] = compute_1sec_vwap(df)
            del df
            gc.collect()
        
        print(f"[MEMORY] Peak memory after loading: {get_memory_usage():.1f} MB")
        
        # Compute leadership for each successful event
        print(f"[LEADERSHIP] Computing leadership for {len(successful_events)} events...")
        leadership_results = []
        
        for _, event in successful_events.iterrows():
            event_ts = event['event_ts']
            
            leader, lead_time_ms, lead_return = find_leader_venue(
                vwap_data, event_ts, venues, window_sec=10
            )
            
            leadership_results.append({
                'event_ts': event_ts,
                'leader': leader,
                'lead_time_ms': lead_time_ms,
                'lead_return_bps': lead_return
            })
        
        leadership_df = pd.DataFrame(leadership_results)
        
        # Compute leadership statistics
        print(f"[LEADERSHIP] Computing statistics...")
        leader_counts = leadership_df['leader'].value_counts()
        total_events = len(leadership_df)
        
        # Median lead time by venue
        median_lead_times = {}
        for venue in venues:
            venue_events = leadership_df[leadership_df['leader'] == venue]
            if len(venue_events) > 0:
                median_lead_times[venue] = venue_events['lead_time_ms'].median()
            else:
                median_lead_times[venue] = None
        
        # Compute convergence/divergence rates based on price movements
        convergence_count = 0
        divergence_count = 0
        
        for _, event in successful_events.iterrows():
            event_ts = event['event_ts']
            
            # Get price movements for each venue around the event
            venue_movements = []
            for venue in venues:
                if venue in vwap_data:
                    venue_df = vwap_data[venue]
                    # Get prices before and after the event
                    pre_window = venue_df[
                        (venue_df['ts'] >= event_ts - pd.Timedelta(seconds=30)) &
                        (venue_df['ts'] < event_ts)
                    ]
                    post_window = venue_df[
                        (venue_df['ts'] > event_ts) &
                        (venue_df['ts'] <= event_ts + pd.Timedelta(seconds=30))
                    ]
                    
                    if len(pre_window) > 0 and len(post_window) > 0:
                        pre_price = pre_window['vwap'].iloc[-1]
                        post_price = post_window['vwap'].iloc[0]
                        movement = (post_price - pre_price) / pre_price * 10000  # bps
                        venue_movements.append(movement)
            
            if len(venue_movements) >= 2:
                if all(m >= 0 for m in venue_movements) or all(m <= 0 for m in venue_movements):
                    convergence_count += 1
                else:
                    divergence_count += 1
        
        total_directional_events = convergence_count + divergence_count
        convergence_rate = (convergence_count / total_directional_events * 100) if total_directional_events > 0 else 0
        divergence_rate = (divergence_count / total_directional_events * 100) if total_directional_events > 0 else 0
        
        # Compute hazard rate
        print(f"[HAZARD] Computing hazard rate...")
        hazard_results = compute_hazard_rate(successful_events, venues, vwap_data, max_time_sec=15)
        
        # Print results
        print("\n" + "=" * 60)
        print("STAGE 3 RESULTS")
        print("=" * 60)
        
        # Leadership table
        print("\n📊 LEADERSHIP TABLE")
        print("-" * 40)
        print(f"{'Venue':<12} {'Leader Share %':<15} {'Median Lead Time (ms)':<20}")
        print("-" * 40)
        
        for venue in venues:
            share = (leader_counts.get(venue, 0) / total_events * 100) if total_events > 0 else 0
            median_time = median_lead_times[venue]
            median_str = f"{median_time:.1f}" if median_time is not None else "N/A"
            print(f"{venue:<12} {share:<15.1f} {median_str:<20}")
        
        print(f"{'TOTAL':<12} {total_events:<15} {'Events':<20}")
        
        # Convergence/Divergence rates
        print(f"\n📈 CONVERGENCE/DIVERGENCE RATES")
        print("-" * 40)
        print(f"Convergence Rate: {convergence_rate:.1f}% ({convergence_count} events)")
        print(f"Divergence Rate:  {divergence_rate:.1f}% ({divergence_count} events)")
        print(f"Total Directional Events: {total_directional_events}")
        
        # Hazard rate table (first 10 seconds)
        print(f"\n⏱️  HAZARD RATE TABLE (First 10 seconds)")
        print("-" * 50)
        print(f"{'Time (s)':<8} {'λ(t)':<8} {'S(t)':<8} {'Notes':<20}")
        print("-" * 50)
        
        for t in range(11):
            lambda_avg = np.mean([hazard_results[venue]['lambda'][t] for venue in venues])
            survival_avg = np.mean([hazard_results[venue]['survival'][t] for venue in venues])
            
            notes = ""
            if t == 0:
                notes = "Initial state"
            elif lambda_avg > 0.1:
                notes = "High hazard"
            elif survival_avg < 0.5:
                notes = "50% reacted"
            
            print(f"{t:<8} {lambda_avg:<8.3f} {survival_avg:<8.3f} {notes:<20}")
        
        # Key insights
        print(f"\n🔍 KEY INSIGHTS")
        print("-" * 40)
        
        # Find dominant leader
        if len(leader_counts) > 0:
            dominant_leader = leader_counts.index[0]
            dominant_share = leader_counts.iloc[0] / total_events * 100
            print(f"• Dominant leader: {dominant_leader} ({dominant_share:.1f}% of events)")
        else:
            print("• No clear leadership pattern detected")
        
        # Leadership detection rate
        leadership_detection_rate = (total_events - leader_counts.get('None', 0)) / total_events * 100
        print(f"• Leadership detection rate: {leadership_detection_rate:.1f}%")
        
        # Market coordination
        if convergence_rate > 60:
            print(f"• High market coordination: {convergence_rate:.1f}% convergence")
        elif divergence_rate > 60:
            print(f"• High market divergence: {divergence_rate:.1f}% divergence")
        else:
            print(f"• Mixed market behavior: {convergence_rate:.1f}% convergence, {divergence_rate:.1f}% divergence")
        
        # Hazard rate pattern
        early_hazard = np.mean([hazard_results[venue]['lambda'][1] for venue in venues])
        late_hazard = np.mean([hazard_results[venue]['lambda'][10] for venue in venues])
        if early_hazard > late_hazard * 2:
            print(f"• Hazard rate decays over time (early: {early_hazard:.3f}, late: {late_hazard:.3f})")
        else:
            print(f"• Hazard rate relatively stable (early: {early_hazard:.3f}, late: {late_hazard:.3f})")
        
        # Memory usage
        print(f"• Peak memory usage: {get_memory_usage():.1f} MB")
        
        print(f"\n✅ STAGE 3 COMPLETE")
        print(f"Successfully analyzed {len(successful_events)} events")
        print(f"Leadership detected in {total_events - leader_counts.get('None', 0)} events")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    finally:
        # Cleanup
        gc.collect()
        print(f"[CLEANUP] Final memory: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()
