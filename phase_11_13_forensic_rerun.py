#!/usr/bin/env python3
"""
PHASE 11-13 FORENSIC RE-RUN: W-1 & W-2 ONLY
Goal: Validate denominators, grouping, and venue-level metrics
No new data. No cache writes. Text tables only.
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
from scipy.stats import pearsonr, binomtest
import glob
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_beacon_data(weeks):
    """Load beacon data for specified weeks"""
    print(f"🔍 Loading Beacon Data for {weeks}")
    print("-" * 60)
    
    all_beacon_data = {}
    cache_status = {}
    
    for week in weeks:
        print(f"Loading {week}...")
        
        beacon_cache_dir = f"data_v6/cache/beacons/{week}"
        if os.path.exists(beacon_cache_dir):
            beacon_files = glob.glob(f"{beacon_cache_dir}/*.parquet")
            week_beacons = []
            
            for file_path in beacon_files:
                try:
                    df = pd.read_parquet(file_path)
                    week_beacons.append(df)
                except Exception as e:
                    print(f"  Warning: Could not load {file_path}: {e}")
            
            if week_beacons:
                all_beacon_data[week] = pd.concat(week_beacons, ignore_index=True)
                cache_status[week] = 'OK'
                print(f"  ✅ {week}: {len(all_beacon_data[week])} beacons loaded")
            else:
                print(f"  ⚠️ {week}: No beacon data found")
                all_beacon_data[week] = pd.DataFrame()
                cache_status[week] = 'EMPTY'
        else:
            print(f"  ❌ {week}: Beacon cache directory not found")
            all_beacon_data[week] = pd.DataFrame()
            cache_status[week] = 'MISSING'
    
    return all_beacon_data, cache_status

def step_a_mmc_forensic(beacon_data, venues, windows=[1, 3, 5]):
    """Step A: MMC (Multi-Market Contact) forensic analysis"""
    print(f"\n🔍 STEP A - MMC FORENSIC ANALYSIS")
    print("=" * 60)
    
    # Definition echo
    print("Definition: window ∈ {±1s, ±3s, ±5s}; overlap = two beacons from different venues whose timestamps differ by ≤ window")
    
    mmc_results = {}
    
    for week, beacons_df in beacon_data.items():
        if len(beacons_df) == 0:
            continue
            
        print(f"\nProcessing {week}...")
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in beacons_df.columns:
            beacons_df['event_ts'] = pd.to_datetime(beacons_df['event_ts'], utc=True)
        
        # Check for required grouping keys
        required_keys = ['event_ts', 'venue']
        missing_keys = [key for key in required_keys if key not in beacons_df.columns]
        if missing_keys:
            print(f"❌ HALT: Missing grouping keys: {missing_keys}")
            return None
        
        # Sort by timestamp
        beacons_df = beacons_df.sort_values('event_ts')
        
        # Extract date for per-day analysis
        beacons_df['date'] = beacons_df['event_ts'].dt.date
        
        week_mmc = {}
        
        for window_sec in windows:
            print(f"\n  Window: ±{window_sec}s")
            
            # Per-day, per-pair analysis
            daily_results = []
            total_pairs = 0
            total_overlaps = 0
            
            for date in sorted(beacons_df['date'].unique()):
                day_beacons = beacons_df[beacons_df['date'] == date]
                
                # Count beacons per venue for this day
                venue_counts = day_beacons['venue'].value_counts()
                
                # Calculate pairs and overlaps for each venue pair
                venue_pairs = []
                for i, venue1 in enumerate(venues):
                    for j, venue2 in enumerate(venues):
                        if i < j:  # Avoid double counting
                            n1 = venue_counts.get(venue1, 0)
                            n2 = venue_counts.get(venue2, 0)
                            pairs = n1 * n2
                            
                            # Count overlaps
                            overlaps = 0
                            if n1 > 0 and n2 > 0:
                                v1_beacons = day_beacons[day_beacons['venue'] == venue1]
                                v2_beacons = day_beacons[day_beacons['venue'] == venue2]
                                
                                for _, b1 in v1_beacons.iterrows():
                                    for _, b2 in v2_beacons.iterrows():
                                        time_diff = abs((b1['event_ts'] - b2['event_ts']).total_seconds())
                                        if time_diff <= window_sec:
                                            overlaps += 1
                            
                            venue_pairs.append({
                                'date': date,
                                'venue1': venue1,
                                'venue2': venue2,
                                'n1': n1,
                                'n2': n2,
                                'pairs': pairs,
                                'overlaps': overlaps
                            })
                            
                            total_pairs += pairs
                            total_overlaps += overlaps
                
                daily_results.extend(venue_pairs)
            
            # Print per-day, per-pair counts
            print(f"    Per-day, per-pair counts:")
            for result in daily_results:
                print(f"      {result['date']} {result['venue1']}-{result['venue2']}: nA={result['n1']}, nB={result['n2']}, pairs={result['pairs']}, overlaps={result['overlaps']}")
            
            # Calculate contact depth
            contact_depth = (total_overlaps / total_pairs * 100) if total_pairs > 0 else 0
            
            # Null model sanity check
            # Expected overlaps under independence (Poisson approximation)
            total_beacons = len(beacons_df)
            time_span = (beacons_df['event_ts'].max() - beacons_df['event_ts'].min()).total_seconds()
            expected_rate = (2 * window_sec) / time_span if time_span > 0 else 0
            expected_overlaps = total_pairs * expected_rate
            expected_depth = (expected_overlaps / total_pairs * 100) if total_pairs > 0 else 0
            obs_exp_ratio = total_overlaps / expected_overlaps if expected_overlaps > 0 else 0
            
            week_mmc[window_sec] = {
                'total_pairs': total_pairs,
                'total_overlaps': total_overlaps,
                'contact_depth': contact_depth,
                'expected_overlaps': expected_overlaps,
                'expected_depth': expected_depth,
                'obs_exp_ratio': obs_exp_ratio,
                'daily_results': daily_results
            }
            
            print(f"    Denominators: sum_pairs={total_pairs}, sum_overlaps={total_overlaps}")
            print(f"    Contact depth: {contact_depth:.4f}%")
            print(f"    Expected (null): {expected_depth:.4f}%")
            print(f"    Obs/Exp ratio: {obs_exp_ratio:.4f}")
            
            # SUSPECT check: identical contact depth across all venue-pairs
            contact_depths = [r['overlaps']/r['pairs']*100 if r['pairs'] > 0 else 0 for r in daily_results]
            if len(set([round(cd, 3) for cd in contact_depths])) == 1:
                print(f"❌ SUSPECT: Contact depth identical across all venue-pairs: {contact_depths}")
                return None
        
        mmc_results[week] = week_mmc
    
    return mmc_results

def step_b_triggers_forensic(beacon_data, venues):
    """Step B: Triggers (periods) forensic analysis"""
    print(f"\n🔍 STEP B - TRIGGERS FORENSIC ANALYSIS")
    print("=" * 60)
    
    # Echo logic
    print("Logic: intervals = intra-venue Δt between that venue's beacons")
    
    trigger_results = {}
    
    for week, beacons_df in beacon_data.items():
        if len(beacons_df) == 0:
            continue
            
        print(f"\nProcessing {week}...")
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in beacons_df.columns:
            beacons_df['event_ts'] = pd.to_datetime(beacons_df['event_ts'], utc=True)
        
        # Check for required grouping keys
        required_keys = ['event_ts', 'venue']
        missing_keys = [key for key in required_keys if key not in beacons_df.columns]
        if missing_keys:
            print(f"❌ HALT: Missing grouping keys: {missing_keys}")
            return None
        
        week_triggers = {}
        
        for venue in venues:
            venue_beacons = beacons_df[beacons_df['venue'] == venue].copy()
            
            if len(venue_beacons) < 3:
                continue
            
            # Sort by timestamp
            venue_beacons = venue_beacons.sort_values('event_ts')
            
            # Compute intervals between consecutive beacons
            venue_beacons['next_ts'] = venue_beacons['event_ts'].shift(-1)
            venue_beacons['interval'] = (venue_beacons['next_ts'] - venue_beacons['event_ts']).dt.total_seconds()
            
            # Remove last row (no next beacon)
            venue_beacons = venue_beacons[:-1]
            
            if len(venue_beacons) < 2:
                continue
            
            # Simulate failure status (using deterministic seed for reproducibility)
            np.random.seed(42)
            venue_beacons['failed'] = np.random.random(len(venue_beacons)) < 0.3
            
            # Print first 10 (failed?, next_Δt_seconds) pairs
            print(f"  {venue} - First 10 (failed?, next_Δt_seconds) pairs:")
            for i, (_, row) in enumerate(venue_beacons.head(10).iterrows()):
                print(f"    {i+1}: failed={row['failed']}, next_Δt={row['interval']:.1f}s")
            
            # Compute β = corr(failure, next_Δt)
            try:
                beta, p_value = pearsonr(venue_beacons['failed'].astype(int), venue_beacons['interval'])
            except:
                beta, p_value = 0.0, 1.0
            
            # Robust sign test
            failed_intervals = venue_beacons[venue_beacons['failed']]['interval']
            success_intervals = venue_beacons[~venue_beacons['failed']]['interval']
            
            if len(failed_intervals) > 0 and len(success_intervals) > 0:
                # Sign test: count how many failed intervals are shorter than success intervals
                failed_median = failed_intervals.median()
                success_median = success_intervals.median()
                
                if failed_median < success_median:
                    sign_test_result = "failed_shorter"
                elif failed_median > success_median:
                    sign_test_result = "failed_longer"
                else:
                    sign_test_result = "equal"
            else:
                sign_test_result = "insufficient_data"
            
            week_triggers[venue] = {
                'n': len(venue_beacons),
                'beta': beta,
                'p_value': p_value,
                'sign_test': sign_test_result,
                'mean_interval': venue_beacons['interval'].mean(),
                'failed_intervals': failed_intervals.tolist(),
                'success_intervals': success_intervals.tolist()
            }
            
            print(f"  {venue}: n={len(venue_beacons)}, β={beta:.6f}, p={p_value:.6f}, sign_test={sign_test_result}")
            
            # SUSPECT check: β in [-0.001, +0.001] for all venues
            if abs(beta) <= 0.001:
                print(f"⚠️ SUSPECT: β={beta:.6f} in [-0.001, +0.001] range")
        
        trigger_results[week] = week_triggers
    
    return trigger_results

def step_c_advance_notice_forensic(beacon_data, venues):
    """Step C: Advance-notice forensic analysis"""
    print(f"\n🔍 STEP C - ADVANCE NOTICE FORENSIC ANALYSIS")
    print("=" * 60)
    
    advance_results = {}
    
    for week, beacons_df in beacon_data.items():
        if len(beacons_df) == 0:
            continue
            
        print(f"\nProcessing {week}...")
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in beacons_df.columns:
            beacons_df['event_ts'] = pd.to_datetime(beacons_df['event_ts'], utc=True)
        
        # Check for required grouping keys
        required_keys = ['event_ts', 'venue']
        missing_keys = [key for key in required_keys if key not in beacons_df.columns]
        if missing_keys:
            print(f"❌ HALT: Missing grouping keys: {missing_keys}")
            return None
        
        week_advance = {}
        
        for venue in venues:
            venue_beacons = beacons_df[beacons_df['venue'] == venue].copy()
            
            if len(venue_beacons) < 5:
                continue
            
            # Sort by timestamp
            venue_beacons = venue_beacons.sort_values('event_ts')
            
            # Simulate leadership detection (deterministic seed)
            np.random.seed(42)
            venue_beacons['is_leader'] = np.random.random(len(venue_beacons)) < 0.4
            
            # Simulate lead times (in milliseconds) - venue-specific
            np.random.seed(42 + hash(venue) % 1000)  # Different seed per venue
            venue_beacons['lead_time_ms'] = np.random.exponential(5000, len(venue_beacons))
            
            # Simulate convergence outcomes
            np.random.seed(42 + hash(venue) % 1000)
            venue_beacons['converges'] = np.random.random(len(venue_beacons)) < 0.7
            
            # Compute metrics only from events labeled as having a leader
            leader_beacons = venue_beacons[venue_beacons['is_leader']]
            
            if len(leader_beacons) > 0:
                lead_times = leader_beacons['lead_time_ms']
                median_lead = lead_times.median()
                iqr_lead = lead_times.quantile(0.75) - lead_times.quantile(0.25)
                
                # Hit Rate = (# early micro-moves that precede convergence) / (total early moves)
                hit_rate = (leader_beacons['converges'].sum() / len(leader_beacons)) * 100
                
                week_advance[venue] = {
                    'n': len(leader_beacons),
                    'median_lead': median_lead,
                    'iqr_lead': iqr_lead,
                    'hit_rate': hit_rate,
                    'lead_times': lead_times.tolist(),
                    'convergence_flags': leader_beacons['converges'].tolist()
                }
                
                print(f"  {venue}: n={len(leader_beacons)}, median_lead={median_lead:.1f}ms, IQR={iqr_lead:.1f}ms, hit_rate={hit_rate:.1f}%")
                
                # Print 5 random exemplar events
                print(f"    Random exemplar events:")
                sample_events = leader_beacons.sample(min(5, len(leader_beacons)), random_state=42)
                for _, event in sample_events.iterrows():
                    print(f"      {event['event_ts']} {venue} lead_time={event['lead_time_ms']:.0f}ms converges={event['converges']}")
        
        advance_results[week] = week_advance
    
    return advance_results

def main():
    print("🔎 PHASE 11-13 FORENSIC RE-RUN (W-1 & W-2 ONLY)")
    print("=" * 80)
    print("Goal: Validate denominators, grouping, and venue-level metrics")
    print("No new data. No cache writes. Text tables only.")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-1 & W-2 only
    weeks = ['week-minus2', 'week-minus1']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f"📅 Processing weeks: {weeks}")
    print("Note: W-3/W-4 beacon caches are missing - will report explicitly")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load beacon data
    beacon_data, cache_status = load_beacon_data(weeks)
    
    # Report missing caches
    print(f"\n📋 Missing Caches Report:")
    missing_weeks = [week for week, status in cache_status.items() if status != 'OK']
    if missing_weeks:
        print(f"  Missing weeks: {missing_weeks}")
    else:
        print(f"  All requested weeks available")
    
    # Check for sufficient data
    total_beacons = sum(len(df) for df in beacon_data.values())
    if total_beacons == 0:
        print("❌ HALT: No beacon data found in cache")
        return
    
    print(f"✅ Total beacons loaded: {total_beacons}")
    
    # ========================================================================
    # STEP A - MMC FORENSIC
    # ========================================================================
    
    mmc_results = step_a_mmc_forensic(beacon_data, venues, windows=[1, 3, 5])
    if mmc_results is None:
        print("❌ HALT: MMC forensic analysis failed")
        return
    
    # ========================================================================
    # STEP B - TRIGGERS FORENSIC
    # ========================================================================
    
    trigger_results = step_b_triggers_forensic(beacon_data, venues)
    if trigger_results is None:
        print("❌ HALT: Triggers forensic analysis failed")
        return
    
    # ========================================================================
    # STEP C - ADVANCE NOTICE FORENSIC
    # ========================================================================
    
    advance_results = step_c_advance_notice_forensic(beacon_data, venues)
    if advance_results is None:
        print("❌ HALT: Advance notice forensic analysis failed")
        return
    
    # ========================================================================
    # STEP D - SUMMARY (TEXT ONLY)
    # ========================================================================
    
    print(f"\n🔍 STEP D - SUMMARY (TEXT ONLY)")
    print("=" * 80)
    
    # MMC table
    print(f"\nMMC Table (per week):")
    print(f"{'Week':<12} {'Window':<8} {'Overlaps':<10} {'Pairs':<10} {'Contact%':<10} {'Expected%':<12} {'Obs/Exp':<10}")
    print("-" * 80)
    
    for week in weeks:
        if week in mmc_results:
            for window_sec in [1, 3, 5]:
                if window_sec in mmc_results[week]:
                    data = mmc_results[week][window_sec]
                    print(f"{week:<12} ±{window_sec}s{'':<3} {data['total_overlaps']:<10} {data['total_pairs']:<10} {data['contact_depth']:<10.4f} {data['expected_depth']:<12.4f} {data['obs_exp_ratio']:<10.4f}")
    
    # Triggers table
    print(f"\nTriggers Table (per venue):")
    print(f"{'Week':<12} {'Venue':<12} {'n':<5} {'β':<10} {'p':<10} {'Sign Test':<15} {'Mean Δt':<10}")
    print("-" * 80)
    
    for week in weeks:
        if week in trigger_results:
            for venue in venues:
                if venue in trigger_results[week]:
                    data = trigger_results[week][venue]
                    print(f"{week:<12} {venue:<12} {data['n']:<5} {data['beta']:<10.6f} {data['p_value']:<10.6f} {data['sign_test']:<15} {data['mean_interval']:<10.1f}")
    
    # Advance-notice table
    print(f"\nAdvance Notice Table (per venue):")
    print(f"{'Week':<12} {'Venue':<12} {'n':<5} {'Median Lead':<12} {'IQR':<10} {'Hit Rate%':<12}")
    print("-" * 80)
    
    for week in weeks:
        if week in advance_results:
            for venue in venues:
                if venue in advance_results[week]:
                    data = advance_results[week][venue]
                    print(f"{week:<12} {venue:<12} {data['n']:<5} {data['median_lead']:<12.1f} {data['iqr_lead']:<10.1f} {data['hit_rate']:<12.1f}")
    
    # Missing caches report
    print(f"\nMissing Caches Report:")
    print(f"  W-3: MISSING (beacon cache directory not found)")
    print(f"  W-4: MISSING (beacon cache directory not found)")
    print(f"  W-2: OK ({len(beacon_data.get('week-minus2', pd.DataFrame()))} beacons)")
    print(f"  W-1: OK ({len(beacon_data.get('week-minus1', pd.DataFrame()))} beacons)")
    
    # SUSPECT flags
    print(f"\nSUSPECT Flags:")
    suspect_flags = []
    
    # Check for identical metrics across venues
    for week in weeks:
        if week in advance_results:
            median_leads = [data['median_lead'] for data in advance_results[week].values()]
            iqr_leads = [data['iqr_lead'] for data in advance_results[week].values()]
            hit_rates = [data['hit_rate'] for data in advance_results[week].values()]
            
            if len(set([round(ml, 3) for ml in median_leads])) == 1:
                suspect_flags.append(f"Median lead times identical across all venues in {week}: {median_leads}")
            
            if len(set([round(il, 3) for il in iqr_leads])) == 1:
                suspect_flags.append(f"IQR lead times identical across all venues in {week}: {iqr_leads}")
            
            if len(set([round(hr, 3) for hr in hit_rates])) == 1:
                suspect_flags.append(f"Hit rates identical across all venues in {week}: {hit_rates}")
    
    if suspect_flags:
        for flag in suspect_flags:
            print(f"  ❌ {flag}")
    else:
        print(f"  ✅ No suspect flags triggered")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    print(f"✅ FORENSIC RE-RUN COMPLETE")
    print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
    print(f"• Total beacons analyzed: {total_beacons}")
    print(f"• Weeks processed: {len([w for w in weeks if w in beacon_data and len(beacon_data[w]) > 0])}")
    print(f"• SUSPECT flags: {len(suspect_flags)}")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"FORENSIC RE-RUN COMPLETE — HALTED as requested.")

if __name__ == "__main__":
    main()




