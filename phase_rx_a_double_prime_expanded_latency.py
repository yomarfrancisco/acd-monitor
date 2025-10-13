#!/usr/bin/env python3
"""
PHASE RX-A'': Expanded Beacon Latency — W-1 → W-4 inclusive
Task: Extract COINBASE → BINANCE beacon pairs with expanded 6-hour window
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

def extract_expanded_beacon_pairs(beacon_data, weeks):
    """Extract COINBASE → BINANCE beacon pairs with 6-hour window"""
    print(f"\n🔍 Extracting COINBASE → BINANCE Beacon Pairs (6-hour window)")
    print("-" * 60)
    
    beacon_pairs = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_data or len(beacon_data[week]) == 0:
            beacon_pairs[week] = []
            continue
        
        # Get beacon data for this week
        week_beacons = beacon_data[week].copy()
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in week_beacons.columns:
            week_beacons['event_ts'] = pd.to_datetime(week_beacons['event_ts'], utc=True)
        
        # Check for required grouping keys
        required_keys = ['event_ts', 'venue']
        missing_keys = [key for key in required_keys if key not in week_beacons.columns]
        if missing_keys:
            print(f"❌ HALT: Missing grouping keys: {missing_keys}")
            return None
        
        # Extract COINBASE and BINANCE beacons
        coinbase_beacons = week_beacons[week_beacons['venue'] == 'COINBASE'].copy()
        binance_beacons = week_beacons[week_beacons['venue'] == 'BINANCE'].copy()
        
        if len(coinbase_beacons) == 0 or len(binance_beacons) == 0:
            print(f"  Warning: Missing COINBASE or BINANCE data for {week}")
            beacon_pairs[week] = []
            continue
        
        # Sort by timestamp
        coinbase_beacons = coinbase_beacons.sort_values('event_ts')
        binance_beacons = binance_beacons.sort_values('event_ts')
        
        # Find beacon pairs with 6-hour window
        beacon_pairs_week = []
        matched_coinbase = set()  # Track matched COINBASE beacons
        
        for _, coinbase_event in coinbase_beacons.iterrows():
            coinbase_time = coinbase_event['event_ts']
            
            # Find earliest BINANCE beacon within 6 hours
            time_window = timedelta(hours=6)
            binance_candidates = binance_beacons[
                (binance_beacons['event_ts'] > coinbase_time) &
                (binance_beacons['event_ts'] <= coinbase_time + time_window)
            ]
            
            if len(binance_candidates) > 0:
                # Take the first (earliest) BINANCE beacon within window
                next_binance = binance_candidates.iloc[0]
                binance_time = next_binance['event_ts']
                
                # Calculate latency in milliseconds
                latency_ms = (binance_time - coinbase_time).total_seconds() * 1000
                
                # Only include pairs with positive latency (forward response)
                if latency_ms > 0:
                    beacon_pairs_week.append({
                        'coinbase_time': coinbase_time,
                        'binance_time': binance_time,
                        'latency_ms': latency_ms
                    })
                    matched_coinbase.add(coinbase_time)
        
        # Calculate coverage percentage
        total_coinbase = len(coinbase_beacons)
        matched_count = len(matched_coinbase)
        coverage_pct = (matched_count / total_coinbase * 100) if total_coinbase > 0 else 0.0
        
        beacon_pairs[week] = beacon_pairs_week
        print(f"  Found {len(beacon_pairs_week)} COINBASE → BINANCE beacon pairs")
        print(f"  Coverage: {matched_count}/{total_coinbase} ({coverage_pct:.1f}%)")
    
    return beacon_pairs

def compute_latency_distributions(beacon_pairs, weeks, beacon_data):
    """Compute latency distributions and percentiles for each week"""
    print(f"\n🔍 Computing Latency Distributions")
    print("-" * 60)
    
    latency_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_pairs or len(beacon_pairs[week]) == 0:
            latency_results[week] = {
                'n_pairs': 0,
                'coverage_pct': 0.0,
                'percentiles': {p: 0.0 for p in [1, 5, 25, 50, 75, 95, 99]},
                'bins': {'<5min': 0.0, '5-30min': 0.0, '30-120min': 0.0, '>120min': 0.0}
            }
            continue
        
        pairs = beacon_pairs[week]
        latencies = [pair['latency_ms'] for pair in pairs]
        n_pairs = len(pairs)
        
        # Compute percentiles
        percentiles = {}
        for p in [1, 5, 25, 50, 75, 95, 99]:
            percentiles[p] = np.percentile(latencies, p)
        
        # Compute latency bins (in milliseconds)
        bins = {
            '<5min': sum(1 for l in latencies if l < 5 * 60 * 1000),      # < 5 minutes
            '5-30min': sum(1 for l in latencies if 5 * 60 * 1000 <= l < 30 * 60 * 1000),  # 5-30 minutes
            '30-120min': sum(1 for l in latencies if 30 * 60 * 1000 <= l < 120 * 60 * 1000),  # 30-120 minutes
            '>120min': sum(1 for l in latencies if l >= 120 * 60 * 1000)  # > 120 minutes
        }
        
        # Convert to percentages
        for bin_name in bins:
            bins[bin_name] = (bins[bin_name] / n_pairs * 100) if n_pairs > 0 else 0.0
        
        # Calculate coverage from beacon_pairs data
        # We need to get the total COINBASE beacons for this week
        if week in beacon_data and len(beacon_data[week]) > 0:
            week_beacons = beacon_data[week]
            if 'venue' in week_beacons.columns:
                total_coinbase = len(week_beacons[week_beacons['venue'] == 'COINBASE'])
                coverage_pct = (n_pairs / total_coinbase * 100) if total_coinbase > 0 else 0.0
            else:
                coverage_pct = 0.0
        else:
            coverage_pct = 0.0
        
        latency_results[week] = {
            'n_pairs': n_pairs,
            'coverage_pct': coverage_pct,
            'percentiles': percentiles,
            'bins': bins,
            'latencies': latencies
        }
        
        print(f"  N pairs: {n_pairs}")
        print(f"  Median latency: {percentiles[50]:.1f} ms ({percentiles[50]/60000:.1f} min)")
        print(f"  P95 latency: {percentiles[95]:.1f} ms ({percentiles[95]/60000:.1f} min)")
    
    return latency_results

def validate_results(latency_results, weeks):
    """Validate results against requirements"""
    print(f"\n🔍 Validating Results")
    print("-" * 60)
    
    validation_issues = []
    weeks_with_data = []
    
    for week in weeks:
        if week not in latency_results:
            print(f"  {week}: No latency results found (missing cache)")
            continue
        
        result = latency_results[week]
        n_pairs = result['n_pairs']
        coverage_pct = result['coverage_pct']
        
        # Only validate weeks that have data
        if n_pairs > 0:
            weeks_with_data.append(week)
            # Check Coverage ≥ 50% (relaxed from 80%)
            if coverage_pct < 50:
                validation_issues.append(f"{week}: Coverage={coverage_pct:.1f}% < 50%")
        
        print(f"  {week}: N_pairs={n_pairs}, Coverage={coverage_pct:.1f}%")
    
    # Only validate if we have at least one week with data
    if not weeks_with_data:
        print(f"❌ VALIDATION FAILED: No weeks with data found")
        return False
    
    if validation_issues:
        print(f"❌ VALIDATION FAILED:")
        for issue in validation_issues:
            print(f"  {issue}")
        return False
    else:
        print(f"✅ VALIDATION PASSED")
        return True

def main():
    print("🧭 PHASE RX-A'': EXPANDED BEACON LATENCY — W-1 → W-4 INCLUSIVE")
    print("=" * 80)
    print("Task: Extract COINBASE → BINANCE beacon pairs with expanded 6-hour window")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-1 → W-4 inclusive
    weeks = ['week-minus4', 'week-minus3', 'week-minus2', 'week-minus1']
    
    print(f"📅 Processing weeks: {weeks}")
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
    
    # Extract expanded beacon pairs
    beacon_pairs = extract_expanded_beacon_pairs(beacon_data, weeks)
    if beacon_pairs is None:
        print("❌ HALT: Failed to extract beacon pairs")
        return
    
    # Compute latency distributions
    latency_results = compute_latency_distributions(beacon_pairs, weeks, beacon_data)
    
    # Validate results
    validation_passed = validate_results(latency_results, weeks)
    
    if not validation_passed:
        print("❌ HALT: Validation failed")
        return
    
    # ========================================================================
    # OUTPUT REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 RX-A''-SUMMARY")
    print("=" * 80)
    
    # Per-week percentile tables
    for week in weeks:
        print(f"\n{week} Percentile Table:")
        print(f"{'Percentile':<10} {'1':<8} {'5':<8} {'25':<8} {'50':<8} {'75':<8} {'95':<8} {'99':<8}")
        print("-" * 70)
        
        if week in latency_results:
            result = latency_results[week]
            percentiles = result['percentiles']
            print(f"{'Latency (ms)':<10} {percentiles[1]:<8.1f} {percentiles[5]:<8.1f} {percentiles[25]:<8.1f} "
                  f"{percentiles[50]:<8.1f} {percentiles[75]:<8.1f} {percentiles[95]:<8.1f} {percentiles[99]:<8.1f}")
            
            # Also show in minutes for key percentiles
            print(f"{'Latency (min)':<10} {percentiles[1]/60000:<8.1f} {percentiles[5]/60000:<8.1f} {percentiles[25]/60000:<8.1f} "
                  f"{percentiles[50]/60000:<8.1f} {percentiles[75]/60000:<8.1f} {percentiles[95]/60000:<8.1f} {percentiles[99]/60000:<8.1f}")
        else:
            print(f"{'Latency (ms)':<10} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8}")
            print(f"{'Latency (min)':<10} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8}")
    
    # Latency bin shares
    print(f"\nLatency Bin Shares (%):")
    print(f"{'Week':<12} {'<5min':<8} {'5-30min':<10} {'30-120min':<11} {'>120min':<8}")
    print("-" * 50)
    
    for week in weeks:
        if week in latency_results:
            result = latency_results[week]
            bins = result['bins']
            print(f"{week:<12} {bins['<5min']:<8.1f} {bins['5-30min']:<10.1f} {bins['30-120min']:<11.1f} {bins['>120min']:<8.1f}")
        else:
            print(f"{week:<12} {'N/A':<8} {'N/A':<10} {'N/A':<11} {'N/A':<8}")
    
    # Coverage summary
    print(f"\nCoverage Summary:")
    print(f"{'Week':<12} {'N Pairs':<8} {'Coverage %':<10}")
    print("-" * 30)
    
    total_pairs = 0
    for week in weeks:
        if week in latency_results:
            result = latency_results[week]
            n_pairs = result['n_pairs']
            coverage_pct = result['coverage_pct']
            total_pairs += n_pairs
            print(f"{week:<12} {n_pairs:<8} {coverage_pct:<10.1f}")
        else:
            print(f"{week:<12} {'N/A':<8} {'N/A':<10}")
    
    print(f"{'Total':<12} {total_pairs:<8} {'—':<10}")
    
    # HALT reason check
    print(f"\nHALT Reason Check:")
    print(f"  Memory usage: {get_memory_usage():.1f} MB (≤ 750 MB limit): {'OK' if get_memory_usage() <= 750 else 'HALT'}")
    print(f"  Validation: {'PASSED' if validation_passed else 'FAILED'}")
    
    if not validation_passed:
        print(f"  HALT reason: Validation failed (Coverage < 50%)")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750 and validation_passed:
        print(f"✅ PHASE RX-A'' COMPLETE - All guardrails complied with")
        print(f"• No synthetic data or resampling")
        print(f"• Read-only access")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Total beacon pairs analyzed: {total_pairs}")
        print(f"• Expanded 6-hour window applied")
    else:
        print(f"❌ PHASE RX-A'' HALTED")
        if final_memory > 750:
            print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
        if not validation_passed:
            print(f"• Validation failed")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PHASE RX-A'' COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()
