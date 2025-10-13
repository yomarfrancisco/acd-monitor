#!/usr/bin/env python3
"""
Week-3 Real-Beacon Analysis - Day 7 Only (2025-08-17)
Exact same validated pipeline and guardrails as Day 6
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

def step0_preflight(date_str, venues, base_path="data_v6/views"):
    """Step 0: Preflight validation for a single day"""
    print(f"🔍 Step 0 - Preflight for {date_str}")
    print("-" * 40)
    
    venue_data = {}
    
    for venue in venues:
        try:
            file_path = os.path.join(base_path, venue, date_str, "ticks_canonical.parquet")
            
            if not os.path.exists(file_path):
                print(f"❌ HALT: Missing file {file_path}")
                return False, None
            
            # Load data
            df = pd.read_parquet(file_path)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            # Verify schema
            required_cols = ['ts', 'price', 'size', 'venue']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"❌ HALT: {venue} missing columns: {missing_cols}")
                return False, None
            
            # Check monotonic timestamps
            if not df['ts'].is_monotonic_increasing:
                print(f"❌ HALT: {venue} timestamps not monotonic")
                return False, None
            
            # Check non-zero tick counts
            if len(df) == 0:
                print(f"❌ HALT: {venue} has zero ticks")
                return False, None
            
            # Check price range
            price_min, price_max = df['price'].min(), df['price'].max()
            if price_min < 90000 or price_max > 130000:
                print(f"❌ HALT: {venue} price range ${price_min:,.0f} - ${price_max:,.0f} outside [$90K, $130K]")
                return False, None
            
            # Check memory
            current_memory = get_memory_usage()
            if current_memory > 500:
                print(f"❌ HALT: Memory limit exceeded: {current_memory:.1f} MB > 500 MB")
                return False, None
            
            venue_data[venue] = df
            print(f"✅ {venue}: schema✓, UTC monotonic✓, price bounds [${price_min:,.0f},${price_max:,.0f}], mem={current_memory:.1f} MB")
            
        except Exception as e:
            print(f"❌ HALT: Error loading {venue}: {str(e)}")
            return False, None
    
    print(f"✅ Preflight passed for {date_str}")
    return True, venue_data

def detect_beacons(df, micro_p10, round_levels):
    """Detect beacons using Week-4 logic"""
    beacons = []
    
    for level in round_levels:
        # Define price band around round level
        band_low = level * 0.999  # -0.10%
        band_high = level * 1.001  # +0.10%
        
        # Find trades within price band
        band_trades = df[(df['price'] >= band_low) & (df['price'] <= band_high)]
        
        if len(band_trades) < 3:
            continue
        
        # Group by 10-second windows
        band_trades = band_trades.copy()
        band_trades['window'] = (band_trades['ts'] - band_trades['ts'].min()).dt.total_seconds() // 10
        
        for window in band_trades['window'].unique():
            window_trades = band_trades[band_trades['window'] == window]
            
            # Count micro trades
            micro_trades = window_trades[window_trades['size'] <= micro_p10]
            
            if len(micro_trades) >= 3:
                # Use median timestamp of micro trades as event time
                event_ts = micro_trades['ts'].median()
                beacons.append({
                    't_event': event_ts,
                    'level': level,
                    'n_micro_10s': len(micro_trades)
                })
    
    return beacons

def sample_beacons(beacons, target_count=24, seed=1337):
    """Sample beacons deterministically"""
    if len(beacons) <= target_count:
        return beacons, len(beacons)
    
    # Sort by timestamp for deterministic sampling
    beacons_sorted = sorted(beacons, key=lambda x: x['t_event'])
    
    # Apply 60-second lockout
    sampled = []
    last_event_time = None
    
    for beacon in beacons_sorted:
        if last_event_time is None or (beacon['t_event'] - last_event_time).total_seconds() >= 60:
            sampled.append(beacon)
            last_event_time = beacon['t_event']
            
            if len(sampled) >= target_count:
                break
    
    return sampled, len(beacons)

def step1_beacon_detection(date_str, venue_data, venues, cache_path="data_v6/cache/beacons/week-3"):
    """Step 1: Beacon detection for a single day"""
    print(f"🔍 Step 1 - Beacon Detection for {date_str}")
    print("-" * 40)
    
    os.makedirs(cache_path, exist_ok=True)
    all_beacons = []
    raw_candidates = {}
    
    for venue in venues:
        try:
            df = venue_data[venue]
            
            # Compute micro threshold (10th percentile by size)
            micro_p10 = df['size'].quantile(0.10)
            
            # Define round levels ($100/$250 increments)
            min_price = df['price'].min()
            max_price = df['price'].max()
            round_levels = np.arange(
                np.floor(min_price / 100) * 100,
                np.ceil(max_price / 100) * 100 + 1,
                250
            )
            
            # Detect beacons
            raw_beacons = detect_beacons(df, micro_p10, round_levels)
            sampled_beacons, n_raw = sample_beacons(raw_beacons)
            
            raw_candidates[venue] = n_raw
            print(f"  {venue}: {n_raw} raw candidates → 24 cached ✓")
            
            if len(sampled_beacons) != 24:
                print(f"❌ HALT: {venue} has {len(sampled_beacons)} beacons, expected 24")
                return False, None, None
            
            # Convert to DataFrame
            beacon_df = pd.DataFrame(sampled_beacons)
            beacon_df['date'] = date_str
            beacon_df['venue'] = venue
            beacon_df = beacon_df.rename(columns={
                't_event': 'event_ts',
                'level': 'round_level',
                'n_micro_10s': 'n_micro'
            })
            beacon_df = beacon_df[['date', 'venue', 'event_ts', 'round_level', 'n_micro']]
            
            # Ensure event_ts is UTC
            beacon_df['event_ts'] = pd.to_datetime(beacon_df['event_ts'], utc=True)
            
            # Save to parquet
            output_file = os.path.join(cache_path, f"{venue}_{date_str}.parquet")
            beacon_df.to_parquet(output_file, index=False)
            
            all_beacons.extend(beacon_df.to_dict('records'))
            
        except Exception as e:
            print(f"❌ HALT: Error processing {venue}: {str(e)}")
            return False, None, None
    
    print(f"✅ Beacon detection completed for {date_str}")
    return True, all_beacons, raw_candidates

def compute_effects(event, venue_data, venues, min_coverage_pct=60):
    """Compute effects for a single event"""
    event_ts = event['event_ts']
    
    # Define analysis windows
    pre_start_3m = event_ts - pd.Timedelta(minutes=3)
    post_end_3m = event_ts + pd.Timedelta(minutes=3)
    post_end_6m = event_ts + pd.Timedelta(minutes=6)
    post_end_9m = event_ts + pd.Timedelta(minutes=9)
    
    # Build 1-sec VWAP bars for each venue
    venue_vwap = {}
    coverage_ok = True
    
    for venue in venues:
        df = venue_data[venue]
        
        # Get data for all windows
        all_data = df[
            (df['ts'] >= pre_start_3m) & 
            (df['ts'] <= post_end_9m)
        ].copy()
        
        if len(all_data) == 0:
            return {'status': 'FAIL_COVERAGE', 'reason': 'No data in window'}
        
        # Build 1-sec VWAP
        vwap_bars = all_data.set_index('ts').resample('1S').apply(
            lambda x: np.average(x['price'], weights=x['size']) if len(x) > 0 else np.nan
        ).dropna()
        
        # Check coverage
        expected_bars = (post_end_9m - pre_start_3m).total_seconds() + 1
        coverage_pct = (len(vwap_bars) / expected_bars) * 100
        
        if coverage_pct < min_coverage_pct:
            coverage_ok = False
        
        venue_vwap[venue] = vwap_bars
    
    if not coverage_ok:
        return {'status': 'FAIL_COVERAGE', 'reason': 'Low coverage'}
    
    # Compute ΔDispersion
    delta_dispersions = []
    
    for window_minutes in [3, 6, 9]:
        pre_end = event_ts
        post_start = event_ts
        post_end = event_ts + pd.Timedelta(minutes=window_minutes)
        
        pre_dispersions = []
        post_dispersions = []
        
        for venue in venues:
            vwap = venue_vwap[venue]
            
            pre_bars = vwap[(vwap.index >= pre_start_3m) & (vwap.index < pre_end)]
            post_bars = vwap[(vwap.index >= post_start) & (vwap.index <= post_end)]
            
            if len(pre_bars) > 1 and len(post_bars) > 1:
                pre_disp = np.mean(np.abs(pre_bars.diff().dropna()))
                post_disp = np.mean(np.abs(post_bars.diff().dropna()))
                
                pre_dispersions.append(pre_disp)
                post_dispersions.append(post_disp)
        
        if len(pre_dispersions) > 0 and len(post_dispersions) > 0:
            delta_disp = np.mean(post_dispersions) - np.mean(pre_dispersions)
            delta_dispersions.append(delta_disp)
    
    # Compute ΔLag (cross-correlation)
    delta_lags = []
    
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue
            
            vwap1 = venue_vwap[venue1]
            vwap2 = venue_vwap[venue2]
            
            # Align time series
            common_index = vwap1.index.intersection(vwap2.index)
            if len(common_index) < 10:
                continue
            
            vwap1_aligned = vwap1.loc[common_index]
            vwap2_aligned = vwap2.loc[common_index]
            
            # Compute cross-correlation
            correlation = np.corrcoef(vwap1_aligned, vwap2_aligned)[0, 1]
            if not np.isnan(correlation):
                delta_lags.append(correlation)
    
    # Typology
    median_delta_disp_3m = np.median(delta_dispersions) if len(delta_dispersions) > 0 else 0
    
    if median_delta_disp_3m >= 0.001:  # 10 bps
        typology = 'Signal-10'
    elif median_delta_disp_3m >= 0.0007:  # 7 bps
        typology = 'Signal-7'
    elif abs(median_delta_disp_3m) < 0.0005:  # 5 bps
        typology = 'Compression'
    else:
        typology = 'Unclassified'
    
    return {
        'status': 'OK',
        'delta_dispersion_3m': median_delta_disp_3m,
        'delta_dispersion_6m': np.median(delta_dispersions[1:]) if len(delta_dispersions) > 1 else 0,
        'delta_dispersion_9m': np.median(delta_dispersions[2:]) if len(delta_dispersions) > 2 else 0,
        'delta_lag_ms': np.median(delta_lags) if len(delta_lags) > 0 else 0,
        'typology': typology
    }

def step2_effects_computation(date_str, all_beacons, venue_data, venues):
    """Step 2: Effects computation for a single day"""
    print(f"🔍 Step 2 - Effects Computation for {date_str}")
    print("-" * 40)
    
    results = []
    
    for beacon in all_beacons:
        effects = compute_effects(beacon, venue_data, venues)
        effects['date'] = date_str
        effects['venue'] = beacon['venue']
        effects['event_ts'] = beacon['event_ts']
        results.append(effects)
    
    # Aggregate results
    ok_results = [r for r in results if r['status'] == 'OK']
    
    if len(ok_results) == 0:
        print(f"❌ HALT: No successful event processing")
        return False, None
    
    # Compute summary statistics
    delta_disp_3m = [r['delta_dispersion_3m'] for r in ok_results]
    delta_disp_6m = [r['delta_dispersion_6m'] for r in ok_results]
    delta_disp_9m = [r['delta_dispersion_9m'] for r in ok_results]
    delta_lag_ms = [r['delta_lag_ms'] for r in ok_results]
    
    # Typology counts
    typology_counts = {}
    for r in ok_results:
        typology = r['typology']
        typology_counts[typology] = typology_counts.get(typology, 0) + 1
    
    # Validation hooks
    s10_count = typology_counts.get('Signal-10', 0)
    s7_count = typology_counts.get('Signal-7', 0)
    comp_count = typology_counts.get('Compression', 0)
    n_processed = len(ok_results)
    
    print(f"Typology S10={s10_count}, S7={s7_count}, Comp={comp_count}, n_proc={n_processed}")
    
    # Validation hook 1: Typology reporting mismatch
    if (s10_count == 0 and s7_count == 0 and comp_count == 0) and n_processed > 0:
        print("❌ WARNING: typology reporting mismatch")
        return False, None
    
    # Validation hook 2: Dispersion collapse
    if len(delta_disp_3m) > 0:
        median_disp = np.median(delta_disp_3m)
        iqr_disp = np.percentile(delta_disp_3m, 75) - np.percentile(delta_disp_3m, 25)
        if median_disp == 0.00 and iqr_disp == 0.00:
            print("❌ WARNING: dispersion collapse — recheck window coverage")
            return False, None
    
    summary = {
        'date': date_str,
        'total_beacons': len(all_beacons),
        'processed_ok': len(ok_results),
        'median_delta_disp_3m': np.median(delta_disp_3m),
        'median_delta_disp_6m': np.median(delta_disp_6m),
        'median_delta_disp_9m': np.median(delta_disp_9m),
        'median_delta_lag_ms': np.median(delta_lag_ms),
        'typology_counts': typology_counts
    }
    
    print(f"✅ Effects computation completed for {date_str}")
    return True, summary

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

def step3_leadership_dynamics(date_str, all_beacons, venue_data, venues):
    """Step 3: Leadership dynamics analysis for a single day"""
    print(f"🔍 Step 3 - Leadership Dynamics for {date_str}")
    print("-" * 40)
    
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
    
    print(f"  Successful leadership analyses: {len(successful_results)}/{len(leadership_results)}")
    
    if len(successful_results) == 0:
        print("❌ No successful leadership analyses found")
        return False, None
    
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
    
    summary = {
        'date': date_str,
        'total_events': len(leadership_results),
        'successful_analyses': len(successful_results),
        'median_lead_time_ms': np.median(lead_times) if lead_times else 0,
        'median_persistence_s': np.median(persistence_times) if persistence_times else 0,
        'median_follow_through_bps': np.median(follow_through_rates) * 10000 if follow_through_rates else 0,
        'leader_counts': leader_counts,
        'outcome_counts': outcome_counts
    }
    
    print(f"✅ Leadership dynamics completed for {date_str}")
    return True, summary

def main():
    print("🧾 Week-3 Real-Beacon Analysis - Day 7 Only (2025-08-17)")
    print("=" * 60)
    print("Mode: STRICT READ-ONLY, STREAMING, PERSISTENT CACHE")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250817'
    date_display = '2025-08-17'
    
    print(f"📅 Processing {date_display} ({date_str})")
    print("=" * 60)
    
    # Step 0: Preflight
    preflight_ok, venue_data = step0_preflight(date_str, venues)
    if not preflight_ok:
        print("❌ Preflight failed - halting")
        return
    
    # Step 1: Beacon Detection
    beacon_ok, all_beacons, raw_candidates = step1_beacon_detection(date_str, venue_data, venues)
    if not beacon_ok:
        print("❌ Beacon detection failed - halting")
        return
    
    # Step 2: Effects Computation
    effects_ok, effects_summary = step2_effects_computation(date_str, all_beacons, venue_data, venues)
    if not effects_ok:
        print("❌ Effects computation failed - halting")
        return
    
    # Step 3: Leadership Dynamics
    leadership_ok, leadership_summary = step3_leadership_dynamics(date_str, all_beacons, venue_data, venues)
    if not leadership_ok:
        print("❌ Leadership dynamics failed - halting")
        return
    
    # Checkpoint Output
    print(f"\n📊 DAY {date_display} - SUMMARY TABLES")
    print("=" * 60)
    
    # Table A: Beacons
    print("Table A (Beacons):")
    print(f"{'Venue':<10} {'Raw Candidates':<15} {'Cached':<10}")
    print("-" * 35)
    for venue in venues:
        print(f"{venue:<10} {raw_candidates[venue]:<15} 24")
    
    # Table B: Effects
    print(f"\nTable B (Effects, processed only):")
    print(f"{'Metric':<25} {'Value':<15}")
    print("-" * 40)
    print(f"{'med Δdisp3 (bps)':<25} {effects_summary['median_delta_disp_3m']:.2f}")
    print(f"{'med Δdisp6 (bps)':<25} {effects_summary['median_delta_disp_6m']:.2f}")
    print(f"{'med Δdisp9 (bps)':<25} {effects_summary['median_delta_disp_9m']:.2f}")
    print(f"{'med Δlag (ms)':<25} {effects_summary['median_delta_lag_ms']:.2f}")
    
    # Typology counts
    typology_counts = effects_summary['typology_counts']
    s10_count = typology_counts.get('Signal-10', 0)
    s7_count = typology_counts.get('Signal-7', 0)
    comp_count = typology_counts.get('Compression', 0)
    print(f"{'Typology (S10/S7/Comp)':<25} {s10_count}/{s7_count}/{comp_count}")
    print(f"{'n_processed':<25} {effects_summary['processed_ok']}")
    
    # Table C: Leadership
    print(f"\nTable C (Leadership, processed only):")
    print(f"{'Metric':<25} {'Value':<15}")
    print("-" * 40)
    
    # Leader share by venue
    leader_counts = leadership_summary['leader_counts']
    total_successful = leadership_summary['successful_analyses']
    for venue in venues:
        count = leader_counts.get(venue, 0)
        pct = (count / total_successful) * 100 if total_successful > 0 else 0
        print(f"{'Leader share ' + venue:<25} {pct:.1f}%")
    
    print(f"{'median lead_time_ms':<25} {leadership_summary['median_lead_time_ms']:.1f}")
    print(f"{'median persistence_s':<25} {leadership_summary['median_persistence_s']:.1f}")
    print(f"{'median followthrough_bps':<25} {leadership_summary['median_follow_through_bps']:.1f}")
    
    # Convergence/divergence
    outcome_counts = leadership_summary['outcome_counts']
    convergence_count = outcome_counts.get('CONVERGENCE', 0)
    divergence_count = outcome_counts.get('DIVERGENCE', 0)
    total_events = leadership_summary['total_events']
    convergence_pct = (convergence_count / total_events) * 100 if total_events > 0 else 0
    divergence_pct = (divergence_count / total_events) * 100 if total_events > 0 else 0
    print(f"{'convergence% / divergence%':<25} {convergence_pct:.1f}% / {divergence_pct:.1f}%")
    
    # Key Insights
    print(f"\nKey Insights:")
    success_rate = (effects_summary['processed_ok'] / effects_summary['total_beacons']) * 100
    leadership_success_rate = (leadership_summary['successful_analyses'] / leadership_summary['total_events']) * 100
    
    dominant_leader = max(leader_counts.keys(), key=lambda x: leader_counts[x]) if leader_counts else 'NONE'
    dominant_pct = (leader_counts[dominant_leader] / total_successful) * 100 if leader_counts and total_successful > 0 else 0
    
    print(f"• {success_rate:.1f}% beacon processing success rate")
    print(f"• {leadership_success_rate:.1f}% leadership detection success rate")
    print(f"• {dominant_leader} dominant leader ({dominant_pct:.1f}% share)")
    print(f"• {effects_summary['median_delta_disp_3m']:.2f} bps median dispersion change")
    print(f"• {convergence_pct:.1f}% convergence vs {divergence_pct:.1f}% divergence")
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print(f"DAY {date_display} COMPLETE — awaiting next instructions.")

if __name__ == "__main__":
    main()




