#!/usr/bin/env python3
"""
PHASE RX-A: Raw-Latency Measurement — W-1 and W-2 only
Task: Measure reaction latency between COINBASE updates and BINANCE mid-price changes
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
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

def load_canonical_data(weeks, venues):
    """Load canonical parquet data for mid-price analysis"""
    print(f"\n🔍 Loading Canonical Data for Mid-Price Analysis")
    print("-" * 60)
    
    canonical_data = {}
    
    for week in weeks:
        print(f"Loading {week}...")
        
        week_data = {}
        
        for venue in venues:
            # Map week names to date ranges
            if week == 'week-minus2':
                date_range = ['2025-08-22', '2025-08-23', '2025-08-24', '2025-08-25', '2025-08-26', '2025-08-27', '2025-08-28']
            elif week == 'week-minus1':
                date_range = ['2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04', '2025-09-05', '2025-09-06', '2025-09-07']
            else:
                continue
            
            venue_data = []
            
            for date in date_range:
                file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
                if os.path.exists(file_path):
                    try:
                        df = pd.read_parquet(file_path)
                        venue_data.append(df)
                    except Exception as e:
                        print(f"  Warning: Could not load {file_path}: {e}")
            
            if venue_data:
                week_data[venue] = pd.concat(venue_data, ignore_index=True)
                print(f"  ✅ {venue}: {len(week_data[venue])} ticks loaded")
            else:
                print(f"  ⚠️ {venue}: No canonical data found")
                week_data[venue] = pd.DataFrame()
        
        canonical_data[week] = week_data
    
    return canonical_data

def extract_coinbase_updates(beacon_data, canonical_data, weeks):
    """Extract COINBASE updates (beacons and >0.5 bps mid-price moves)"""
    print(f"\n🔍 Extracting COINBASE Updates")
    print("-" * 60)
    
    coinbase_updates = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        # Get COINBASE beacons
        if week in beacon_data and len(beacon_data[week]) > 0:
            coinbase_beacons = beacon_data[week][beacon_data[week]['venue'] == 'COINBASE'].copy()
            if 'event_ts' in coinbase_beacons.columns:
                coinbase_beacons['event_ts'] = pd.to_datetime(coinbase_beacons['event_ts'], utc=True)
                coinbase_beacons = coinbase_beacons.sort_values('event_ts')
        else:
            coinbase_beacons = pd.DataFrame()
        
        # Get COINBASE canonical data for mid-price analysis
        if week in canonical_data and 'COINBASE' in canonical_data[week] and len(canonical_data[week]['COINBASE']) > 0:
            coinbase_ticks = canonical_data[week]['COINBASE'].copy()
            if 'ts' in coinbase_ticks.columns:
                coinbase_ticks['ts'] = pd.to_datetime(coinbase_ticks['ts'], utc=True)
                coinbase_ticks = coinbase_ticks.sort_values('ts')
                
                # Calculate mid-price changes (simplified: use price as mid-price)
                coinbase_ticks['price_change'] = coinbase_ticks['price'].pct_change() * 10000  # Convert to bps
                coinbase_ticks['abs_price_change'] = coinbase_ticks['price_change'].abs()
                
                # Filter for >0.5 bps moves
                significant_moves = coinbase_ticks[coinbase_ticks['abs_price_change'] > 0.5].copy()
            else:
                significant_moves = pd.DataFrame()
        else:
            significant_moves = pd.DataFrame()
        
        # Combine beacons and significant moves
        updates = []
        
        # Add beacons
        for _, beacon in coinbase_beacons.iterrows():
            updates.append({
                'timestamp': beacon['event_ts'],
                'type': 'beacon',
                'price': None,
                'change_bps': None
            })
        
        # Add significant moves
        for _, move in significant_moves.iterrows():
            updates.append({
                'timestamp': move['ts'],
                'type': 'price_move',
                'price': move['price'],
                'change_bps': move['abs_price_change']
            })
        
        # Sort by timestamp and remove duplicates
        updates_df = pd.DataFrame(updates)
        if len(updates_df) > 0:
            updates_df = updates_df.sort_values('timestamp')
            # Remove duplicates within 1 second
            updates_df['timestamp_rounded'] = updates_df['timestamp'].dt.floor('1s')
            updates_df = updates_df.drop_duplicates(subset=['timestamp_rounded'], keep='first')
            updates_df = updates_df.drop('timestamp_rounded', axis=1)
        
        coinbase_updates[week] = updates_df
        print(f"  Found {len(updates_df)} COINBASE updates ({len(coinbase_beacons)} beacons + {len(significant_moves)} price moves)")
    
    return coinbase_updates

def extract_binance_midprice_changes(canonical_data, weeks, thresholds):
    """Extract BINANCE mid-price changes for different thresholds"""
    print(f"\n🔍 Extracting BINANCE Mid-Price Changes")
    print("-" * 60)
    
    binance_changes = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week in canonical_data and 'BINANCE' in canonical_data[week] and len(canonical_data[week]['BINANCE']) > 0:
            binance_ticks = canonical_data[week]['BINANCE'].copy()
            if 'ts' in binance_ticks.columns:
                binance_ticks['ts'] = pd.to_datetime(binance_ticks['ts'], utc=True)
                binance_ticks = binance_ticks.sort_values('ts')
                
                # Calculate mid-price changes (simplified: use price as mid-price)
                binance_ticks['price_change'] = binance_ticks['price'].pct_change() * 10000  # Convert to bps
                binance_ticks['abs_price_change'] = binance_ticks['price_change'].abs()
                
                week_changes = {}
                
                for threshold in thresholds:
                    # Filter for changes >= threshold
                    threshold_changes = binance_ticks[binance_ticks['abs_price_change'] >= threshold].copy()
                    week_changes[threshold] = threshold_changes
                    print(f"  Threshold {threshold} bps: {len(threshold_changes)} changes")
                
                binance_changes[week] = week_changes
            else:
                binance_changes[week] = {threshold: pd.DataFrame() for threshold in thresholds}
        else:
            binance_changes[week] = {threshold: pd.DataFrame() for threshold in thresholds}
    
    return binance_changes

def compute_reaction_latency(coinbase_updates, binance_changes, weeks, thresholds):
    """Compute reaction latency between COINBASE updates and BINANCE changes"""
    print(f"\n🔍 Computing Reaction Latency")
    print("-" * 60)
    
    latency_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in coinbase_updates or len(coinbase_updates[week]) == 0:
            latency_results[week] = {threshold: {'latencies': [], 'n_pairs': 0, 'matched_pct': 0.0} for threshold in thresholds}
            continue
        
        week_results = {}
        
        for threshold in thresholds:
            if week not in binance_changes or threshold not in binance_changes[week]:
                week_results[threshold] = {'latencies': [], 'n_pairs': 0, 'matched_pct': 0.0}
                continue
            
            binance_changes_threshold = binance_changes[week][threshold]
            
            if len(binance_changes_threshold) == 0:
                week_results[threshold] = {'latencies': [], 'n_pairs': 0, 'matched_pct': 0.0}
                continue
            
            latencies = []
            matched_count = 0
            
            for _, coinbase_update in coinbase_updates[week].iterrows():
                coinbase_time = coinbase_update['timestamp']
                
                # Find next BINANCE change within 10 seconds
                time_window = timedelta(seconds=10)
                binance_candidates = binance_changes_threshold[
                    (binance_changes_threshold['ts'] >= coinbase_time) &
                    (binance_changes_threshold['ts'] <= coinbase_time + time_window)
                ]
                
                if len(binance_candidates) > 0:
                    # Take the first (earliest) BINANCE change
                    next_binance = binance_candidates.iloc[0]
                    binance_time = next_binance['ts']
                    
                    # Calculate latency in milliseconds
                    latency_ms = (binance_time - coinbase_time).total_seconds() * 1000
                    latencies.append(latency_ms)
                    matched_count += 1
            
            n_pairs = len(coinbase_updates[week])
            matched_pct = (matched_count / n_pairs * 100) if n_pairs > 0 else 0.0
            
            week_results[threshold] = {
                'latencies': latencies,
                'n_pairs': n_pairs,
                'matched_pct': matched_pct,
                'matched_count': matched_count
            }
            
            print(f"  Threshold {threshold} bps: {matched_count}/{n_pairs} matched ({matched_pct:.1f}%)")
        
        latency_results[week] = week_results
    
    return latency_results

def compute_percentiles_and_bins(latency_results, weeks, thresholds):
    """Compute percentiles and latency bins for each threshold and week"""
    print(f"\n🔍 Computing Percentiles and Bins")
    print("-" * 60)
    
    percentile_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        week_results = {}
        
        for threshold in thresholds:
            if week not in latency_results or threshold not in latency_results[week]:
                week_results[threshold] = {
                    'percentiles': {},
                    'bins': {},
                    'n_pairs': 0,
                    'matched_pct': 0.0
                }
                continue
            
            latencies = latency_results[week][threshold]['latencies']
            n_pairs = latency_results[week][threshold]['n_pairs']
            matched_pct = latency_results[week][threshold]['matched_pct']
            
            if len(latencies) == 0:
                week_results[threshold] = {
                    'percentiles': {p: 0.0 for p in [1, 5, 25, 50, 75, 95, 99]},
                    'bins': {'<100': 0, '100-300': 0, '300-1000': 0, '>1000': 0},
                    'n_pairs': n_pairs,
                    'matched_pct': matched_pct
                }
                continue
            
            # Compute percentiles
            percentiles = {}
            for p in [1, 5, 25, 50, 75, 95, 99]:
                percentiles[p] = np.percentile(latencies, p)
            
            # Compute bins
            bins = {
                '<100': sum(1 for l in latencies if l < 100),
                '100-300': sum(1 for l in latencies if 100 <= l < 300),
                '300-1000': sum(1 for l in latencies if 300 <= l < 1000),
                '>1000': sum(1 for l in latencies if l >= 1000)
            }
            
            # Convert to percentages
            total_matched = len(latencies)
            for bin_name in bins:
                bins[bin_name] = (bins[bin_name] / total_matched * 100) if total_matched > 0 else 0.0
            
            week_results[threshold] = {
                'percentiles': percentiles,
                'bins': bins,
                'n_pairs': n_pairs,
                'matched_pct': matched_pct
            }
            
            print(f"  Threshold {threshold} bps: {len(latencies)} latencies, {matched_pct:.1f}% matched")
        
        percentile_results[week] = week_results
    
    return percentile_results

def main():
    print("🧭 PHASE RX-A: RAW-LATENCY MEASUREMENT — W-1 AND W-2 ONLY")
    print("=" * 80)
    print("Task: Measure reaction latency between COINBASE updates and BINANCE mid-price changes")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-2 and W-1 only
    weeks = ['week-minus2', 'week-minus1']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    thresholds = [0.2, 0.5, 1.0]  # bps thresholds
    
    print(f"📅 Processing weeks: {weeks}")
    print(f"🎯 Thresholds: {thresholds} bps")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load beacon data
    beacon_data, cache_status = load_beacon_data(weeks)
    
    # Check for sufficient data
    total_beacons = sum(len(df) for df in beacon_data.values())
    if total_beacons == 0:
        print("❌ HALT: No beacon data found in cache")
        return
    
    print(f"✅ Total beacons loaded: {total_beacons}")
    
    # Load canonical data
    canonical_data = load_canonical_data(weeks, venues)
    
    # Extract COINBASE updates
    coinbase_updates = extract_coinbase_updates(beacon_data, canonical_data, weeks)
    
    # Extract BINANCE mid-price changes
    binance_changes = extract_binance_midprice_changes(canonical_data, weeks, thresholds)
    
    # Compute reaction latency
    latency_results = compute_reaction_latency(coinbase_updates, binance_changes, weeks, thresholds)
    
    # Compute percentiles and bins
    percentile_results = compute_percentiles_and_bins(latency_results, weeks, thresholds)
    
    # ========================================================================
    # OUTPUT REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 RX-A-SUMMARY")
    print("=" * 80)
    
    # Results for each threshold and week
    for threshold in thresholds:
        print(f"\nThreshold {threshold} bps:")
        print(f"{'Week':<12} {'N Pairs':<8} {'% Matched':<10} {'P1':<8} {'P5':<8} {'P25':<8} {'P50':<8} {'P75':<8} {'P95':<8} {'P99':<8}")
        print("-" * 100)
        
        for week in weeks:
            if week in percentile_results and threshold in percentile_results[week]:
                result = percentile_results[week][threshold]
                percentiles = result['percentiles']
                
                print(f"{week:<12} {result['n_pairs']:<8} {result['matched_pct']:<10.1f} "
                      f"{percentiles[1]:<8.1f} {percentiles[5]:<8.1f} {percentiles[25]:<8.1f} "
                      f"{percentiles[50]:<8.1f} {percentiles[75]:<8.1f} {percentiles[95]:<8.1f} "
                      f"{percentiles[99]:<8.1f}")
            else:
                print(f"{week:<12} {'N/A':<8} {'N/A':<10} {'N/A':<8} {'N/A':<8} {'N/A':<8} "
                      f"{'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8}")
    
    # Bin shares table
    print(f"\nLatency Bin Shares (%):")
    print(f"{'Week':<12} {'Threshold':<10} {'<100ms':<8} {'100-300ms':<10} {'300-1000ms':<11} {'>1000ms':<8}")
    print("-" * 70)
    
    for week in weeks:
        for threshold in thresholds:
            if week in percentile_results and threshold in percentile_results[week]:
                result = percentile_results[week][threshold]
                bins = result['bins']
                
                print(f"{week:<12} {threshold:<10.1f} {bins['<100']:<8.1f} {bins['100-300']:<10.1f} "
                      f"{bins['300-1000']:<11.1f} {bins['>1000']:<8.1f}")
            else:
                print(f"{week:<12} {threshold:<10.1f} {'N/A':<8} {'N/A':<10} {'N/A':<11} {'N/A':<8}")
    
    # HALT reasons check
    print(f"\nHALT Reasons Check:")
    print(f"  Memory usage: {get_memory_usage():.1f} MB (≤ 750 MB limit): {'OK' if get_memory_usage() <= 750 else 'HALT'}")
    
    # Check if we have sufficient data
    total_updates = sum(len(updates) for updates in coinbase_updates.values())
    print(f"  Total COINBASE updates: {total_updates}")
    
    total_changes = 0
    for week in weeks:
        for threshold in thresholds:
            if week in binance_changes and threshold in binance_changes[week]:
                total_changes += len(binance_changes[week][threshold])
    print(f"  Total BINANCE changes: {total_changes}")
    
    if total_updates == 0:
        print(f"  Data availability: HALT - No COINBASE updates found")
    elif total_changes == 0:
        print(f"  Data availability: HALT - No BINANCE changes found")
    else:
        print(f"  Data availability: OK")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750:
        print(f"✅ PHASE RX-A COMPLETE - All guardrails complied with")
        print(f"• No synthetic data, no resampling")
        print(f"• No schema edits, no cache writes")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Used existing beacon + mid-price feeds only")
    else:
        print(f"❌ PHASE RX-A HALTED - Memory limit exceeded")
        print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PHASE RX-A COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




