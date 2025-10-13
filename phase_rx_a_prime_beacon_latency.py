#!/usr/bin/env python3
"""
PHASE RX-A': Beacon-Level Latency Estimation — W-1 and W-2 only
Task: Extract COINBASE → BINANCE causal-lead pairs and compute latency distributions
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

def extract_causal_lead_pairs(beacon_data, weeks):
    """Extract COINBASE → BINANCE causal-lead pairs from beacon data"""
    print(f"\n🔍 Extracting COINBASE → BINANCE Causal-Lead Pairs")
    print("-" * 60)
    
    causal_pairs = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_data or len(beacon_data[week]) == 0:
            causal_pairs[week] = []
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
            causal_pairs[week] = []
            continue
        
        # Sort by timestamp
        coinbase_beacons = coinbase_beacons.sort_values('event_ts')
        binance_beacons = binance_beacons.sort_values('event_ts')
        
        # Find causal-lead pairs (COINBASE events that precede BINANCE events)
        causal_pairs_week = []
        
        for _, coinbase_event in coinbase_beacons.iterrows():
            coinbase_time = coinbase_event['event_ts']
            
            # Find next BINANCE beacon after COINBASE timestamp
            binance_candidates = binance_beacons[binance_beacons['event_ts'] > coinbase_time]
            
            if len(binance_candidates) > 0:
                # Take the first (earliest) BINANCE beacon after COINBASE
                next_binance = binance_candidates.iloc[0]
                binance_time = next_binance['event_ts']
                
                # Calculate latency in milliseconds
                latency_ms = (binance_time - coinbase_time).total_seconds() * 1000
                
                # Only include pairs with positive latency (forward response)
                if latency_ms > 0:
                    causal_pairs_week.append({
                        'coinbase_time': coinbase_time,
                        'binance_time': binance_time,
                        'latency_ms': latency_ms
                    })
        
        causal_pairs[week] = causal_pairs_week
        print(f"  Found {len(causal_pairs_week)} COINBASE → BINANCE causal-lead pairs")
    
    return causal_pairs

def compute_latency_distributions(causal_pairs, weeks):
    """Compute latency distributions and percentiles for each week"""
    print(f"\n🔍 Computing Latency Distributions")
    print("-" * 60)
    
    latency_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in causal_pairs or len(causal_pairs[week]) == 0:
            latency_results[week] = {
                'n_pairs': 0,
                'coverage_pct': 0.0,
                'percentiles': {p: 0.0 for p in [1, 5, 25, 50, 75, 95, 99]},
                'bins': {'<100': 0.0, '100-300': 0.0, '300-1000': 0.0, '>1000': 0.0}
            }
            continue
        
        pairs = causal_pairs[week]
        latencies = [pair['latency_ms'] for pair in pairs]
        n_pairs = len(pairs)
        
        # Calculate coverage percentage (assuming expected ~272 total pairs from Phase 18)
        expected_pairs = 272  # From Phase 18 analysis
        coverage_pct = (n_pairs / expected_pairs * 100) if expected_pairs > 0 else 0.0
        
        # Compute percentiles
        percentiles = {}
        for p in [1, 5, 25, 50, 75, 95, 99]:
            percentiles[p] = np.percentile(latencies, p)
        
        # Compute latency bins
        bins = {
            '<100': sum(1 for l in latencies if l < 100),
            '100-300': sum(1 for l in latencies if 100 <= l < 300),
            '300-1000': sum(1 for l in latencies if 300 <= l < 1000),
            '>1000': sum(1 for l in latencies if l >= 1000)
        }
        
        # Convert to percentages
        for bin_name in bins:
            bins[bin_name] = (bins[bin_name] / n_pairs * 100) if n_pairs > 0 else 0.0
        
        latency_results[week] = {
            'n_pairs': n_pairs,
            'coverage_pct': coverage_pct,
            'percentiles': percentiles,
            'bins': bins,
            'latencies': latencies
        }
        
        print(f"  N pairs: {n_pairs}, Coverage: {coverage_pct:.1f}%")
        print(f"  Median latency: {percentiles[50]:.1f} ms")
        print(f"  P95 latency: {percentiles[95]:.1f} ms")
    
    return latency_results

def validate_results(latency_results, weeks):
    """Validate results against requirements"""
    print(f"\n🔍 Validating Results")
    print("-" * 60)
    
    validation_issues = []
    
    for week in weeks:
        if week not in latency_results:
            validation_issues.append(f"{week}: No latency results found")
            continue
        
        result = latency_results[week]
        n_pairs = result['n_pairs']
        coverage_pct = result['coverage_pct']
        
        # Check N_pairs ≥ 100 per week
        if n_pairs < 100:
            validation_issues.append(f"{week}: N_pairs={n_pairs} < 100")
        
        # Check Coverage ≥ 80% of causal-lead pairs
        if coverage_pct < 80:
            validation_issues.append(f"{week}: Coverage={coverage_pct:.1f}% < 80%")
        
        print(f"  {week}: N_pairs={n_pairs}, Coverage={coverage_pct:.1f}%")
    
    if validation_issues:
        print(f"❌ VALIDATION FAILED:")
        for issue in validation_issues:
            print(f"  {issue}")
        return False
    else:
        print(f"✅ VALIDATION PASSED")
        return True

def main():
    print("🧭 PHASE RX-A': BEACON-LEVEL LATENCY ESTIMATION — W-1 AND W-2 ONLY")
    print("=" * 80)
    print("Task: Extract COINBASE → BINANCE causal-lead pairs and compute latency distributions")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-2 and W-1 only
    weeks = ['week-minus2', 'week-minus1']
    
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
    
    # Extract causal-lead pairs
    causal_pairs = extract_causal_lead_pairs(beacon_data, weeks)
    if causal_pairs is None:
        print("❌ HALT: Failed to extract causal-lead pairs")
        return
    
    # Compute latency distributions
    latency_results = compute_latency_distributions(causal_pairs, weeks)
    
    # Validate results
    validation_passed = validate_results(latency_results, weeks)
    
    if not validation_passed:
        print("❌ HALT: Validation failed")
        return
    
    # ========================================================================
    # OUTPUT REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 RX-A′-SUMMARY")
    print("=" * 80)
    
    # Week W-2 percentile table
    print(f"\nWeek W-2 Percentile Table:")
    print(f"{'Percentile':<10} {'1':<8} {'5':<8} {'25':<8} {'50':<8} {'75':<8} {'95':<8} {'99':<8}")
    print("-" * 70)
    
    if 'week-minus2' in latency_results:
        w2_result = latency_results['week-minus2']
        percentiles = w2_result['percentiles']
        print(f"{'Latency (ms)':<10} {percentiles[1]:<8.1f} {percentiles[5]:<8.1f} {percentiles[25]:<8.1f} "
              f"{percentiles[50]:<8.1f} {percentiles[75]:<8.1f} {percentiles[95]:<8.1f} {percentiles[99]:<8.1f}")
    else:
        print(f"{'Latency (ms)':<10} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8}")
    
    # Week W-1 percentile table
    print(f"\nWeek W-1 Percentile Table:")
    print(f"{'Percentile':<10} {'1':<8} {'5':<8} {'25':<8} {'50':<8} {'75':<8} {'95':<8} {'99':<8}")
    print("-" * 70)
    
    if 'week-minus1' in latency_results:
        w1_result = latency_results['week-minus1']
        percentiles = w1_result['percentiles']
        print(f"{'Latency (ms)':<10} {percentiles[1]:<8.1f} {percentiles[5]:<8.1f} {percentiles[25]:<8.1f} "
              f"{percentiles[50]:<8.1f} {percentiles[75]:<8.1f} {percentiles[95]:<8.1f} {percentiles[99]:<8.1f}")
    else:
        print(f"{'Latency (ms)':<10} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8} {'N/A':<8}")
    
    # Latency bin shares
    print(f"\nLatency Bin Shares (%):")
    print(f"{'Week':<12} {'<100ms':<8} {'100-300ms':<10} {'300-1000ms':<11} {'>1000ms':<8}")
    print("-" * 50)
    
    for week in weeks:
        if week in latency_results:
            result = latency_results[week]
            bins = result['bins']
            print(f"{week:<12} {bins['<100']:<8.1f} {bins['100-300']:<10.1f} {bins['300-1000']:<11.1f} {bins['>1000']:<8.1f}")
        else:
            print(f"{week:<12} {'N/A':<8} {'N/A':<10} {'N/A':<11} {'N/A':<8}")
    
    # N pairs analyzed / coverage %
    print(f"\nN Pairs Analyzed / Coverage %:")
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
        print(f"  HALT reason: Validation failed (N_pairs < 100 or Coverage < 80%)")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750 and validation_passed:
        print(f"✅ PHASE RX-A' COMPLETE - All guardrails complied with")
        print(f"• No synthetic data, smoothing, or resampling")
        print(f"• No schema changes or cache writes")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Used beacon caches only (no canonical tick dependency)")
        print(f"• Total causal-lead pairs analyzed: {total_pairs}")
    else:
        print(f"❌ PHASE RX-A' HALTED")
        if final_memory > 750:
            print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
        if not validation_passed:
            print(f"• Validation failed")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PHASE RX-A' COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




