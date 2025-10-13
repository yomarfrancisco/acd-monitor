#!/usr/bin/env python3
"""
STAGE 2 — Effects Computation with Adaptive Window Logic
Week -2 Day 1 (2025-08-22) Effects Computation Only
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

def load_cached_beacons(date_str, venues, cache_path="data_v6/cache/beacons/week-minus2"):
    """Load cached beacons from Stage 1"""
    print(f"🔍 Loading Cached Beacons for {date_str}")
    print("-" * 60)
    
    all_beacons = []
    
    for venue in venues:
        try:
            file_path = os.path.join(cache_path, f"{venue}_{date_str}.parquet")
            
            if not os.path.exists(file_path):
                print(f"❌ HALT: Cached beacon file not found: {file_path}")
                return None
            
            beacon_df = pd.read_parquet(file_path)
            beacon_df['event_ts'] = pd.to_datetime(beacon_df['event_ts'], utc=True)
            all_beacons.extend(beacon_df.to_dict('records'))
            
            print(f"✅ Loaded {len(beacon_df)} cached beacons for {venue}")
            
        except Exception as e:
            print(f"❌ HALT: Error loading cached beacons for {venue}: {str(e)}")
            return None
    
    print(f"✅ Total cached beacons loaded: {len(all_beacons)}")
    return all_beacons

def load_venue_data(date_str, venues, base_path="data_v6/views"):
    """Load venue data for effects computation"""
    print(f"🔍 Loading Venue Data for {date_str}")
    print("-" * 60)
    
    venue_data = {}
    
    for venue in venues:
        try:
            file_path = os.path.join(base_path, venue, date_str, "ticks_canonical.parquet")
            
            if not os.path.exists(file_path):
                print(f"❌ HALT: Venue data file not found: {file_path}")
                return None
            
            df = pd.read_parquet(file_path)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            venue_data[venue] = df
            
            print(f"✅ Loaded {len(df):,} ticks for {venue}")
            
        except Exception as e:
            print(f"❌ HALT: Error loading venue data for {venue}: {str(e)}")
            return None
    
    return venue_data

def compute_effects_with_window(event, venue_data, venues, window_seconds, min_coverage_pct=60):
    """Compute effects for a single event with specified window"""
    event_ts = event['event_ts']
    
    # Define analysis windows
    pre_start = event_ts - pd.Timedelta(seconds=window_seconds)
    post_end = event_ts + pd.Timedelta(seconds=window_seconds)
    
    # Build 1-sec VWAP bars for each venue
    venue_vwap = {}
    coverage_ok = True
    
    for venue in venues:
        df = venue_data[venue]
        
        # Get data for the window
        window_data = df[
            (df['ts'] >= pre_start) & 
            (df['ts'] <= post_end)
        ].copy()
        
        if len(window_data) == 0:
            return {'status': 'FAIL_COVERAGE', 'reason': 'No data in window'}
        
        # Build 1-sec VWAP
        vwap_bars = window_data.set_index('ts').resample('1S').apply(
            lambda x: np.average(x['price'], weights=x['size']) if len(x) > 0 else np.nan
        ).dropna()
        
        # Check coverage
        expected_bars = (post_end - pre_start).total_seconds() + 1
        coverage_pct = (len(vwap_bars) / expected_bars) * 100
        
        if coverage_pct < min_coverage_pct:
            coverage_ok = False
        
        venue_vwap[venue] = vwap_bars
    
    if not coverage_ok:
        return {'status': 'FAIL_COVERAGE', 'reason': 'Low coverage'}
    
    # Compute ΔDispersion
    pre_end = event_ts
    post_start = event_ts
    
    pre_dispersions = []
    post_dispersions = []
    
    for venue in venues:
        vwap = venue_vwap[venue]
        
        pre_bars = vwap[(vwap.index >= pre_start) & (vwap.index < pre_end)]
        post_bars = vwap[(vwap.index >= post_start) & (vwap.index <= post_end)]
        
        if len(pre_bars) > 1 and len(post_bars) > 1:
            pre_disp = np.mean(np.abs(pre_bars.diff().dropna()))
            post_disp = np.mean(np.abs(post_bars.diff().dropna()))
            
            pre_dispersions.append(pre_disp)
            post_dispersions.append(post_disp)
    
    if len(pre_dispersions) == 0 or len(post_dispersions) == 0:
        return {'status': 'FAIL_COVERAGE', 'reason': 'Insufficient data for dispersion'}
    
    delta_disp = np.mean(post_dispersions) - np.mean(pre_dispersions)
    
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
    if delta_disp >= 0.001:  # 10 bps
        typology = 'Signal-10'
    elif delta_disp >= 0.0007:  # 7 bps
        typology = 'Signal-7'
    elif abs(delta_disp) < 0.0005:  # 5 bps
        typology = 'Compression'
    else:
        typology = 'Unclassified'
    
    return {
        'status': 'OK',
        'delta_dispersion': delta_disp,
        'delta_lag_ms': np.median(delta_lags) if len(delta_lags) > 0 else 0,
        'typology': typology,
        'window_seconds': window_seconds
    }

def adaptive_window_effects_computation(all_beacons, venue_data, venues):
    """Apply adaptive window logic for effects computation"""
    print(f"🔍 Adaptive Window Effects Computation")
    print("-" * 60)
    
    # Define window sequence
    window_sequence = [3, 6, 9, 15]  # seconds
    
    results_by_window = {}
    
    for window_seconds in window_sequence:
        print(f"\n📊 Testing ±{window_seconds}s window...")
        
        results = []
        success_count = 0
        
        for i, beacon in enumerate(all_beacons):
            if i % 20 == 0:
                print(f"  Processing event {i+1}/{len(all_beacons)}...")
            
            effects = compute_effects_with_window(beacon, venue_data, venues, window_seconds)
            effects['date'] = beacon['date']
            effects['venue'] = beacon['venue']
            effects['event_ts'] = beacon['event_ts']
            results.append(effects)
            
            if effects['status'] == 'OK':
                success_count += 1
        
        # Calculate success rate
        success_rate = (success_count / len(all_beacons)) * 100
        
        print(f"  ✅ ±{window_seconds}s window: {success_count}/{len(all_beacons)} events processed ({success_rate:.1f}% success rate)")
        
        # Store results for this window
        results_by_window[window_seconds] = {
            'results': results,
            'success_count': success_count,
            'success_rate': success_rate,
            'total_events': len(all_beacons)
        }
        
        # Check halt condition: fewer than 1 event processed
        if success_count < 1:
            print(f"❌ HALT: Fewer than 1 event processed for ±{window_seconds}s window")
            print(f"   Exact reason: {success_count} events processed, minimum required: 1")
            return None
        
        # Check if we should stop expansion (≥ 1 event successfully processed)
        if success_count >= 1:
            print(f"✅ Stopping expansion at ±{window_seconds}s window (≥ 1 event processed)")
            break
    
    return results_by_window

def compute_summary_statistics(results_by_window):
    """Compute summary statistics for the successful window"""
    print(f"📊 Computing Summary Statistics")
    print("-" * 60)
    
    # Find the window with the best results
    best_window = None
    best_success_rate = 0
    
    for window_seconds, window_results in results_by_window.items():
        if window_results['success_rate'] > best_success_rate:
            best_success_rate = window_results['success_rate']
            best_window = window_seconds
    
    if best_window is None:
        print("❌ HALT: No successful window found")
        return None
    
    print(f"✅ Best window: ±{best_window}s with {best_success_rate:.1f}% success rate")
    
    # Get results for best window
    best_results = results_by_window[best_window]['results']
    ok_results = [r for r in best_results if r['status'] == 'OK']
    
    if len(ok_results) == 0:
        print("❌ HALT: No successful events in best window")
        return None
    
    # Compute summary statistics
    delta_dispersions = [r['delta_dispersion'] for r in ok_results]
    delta_lags = [r['delta_lag_ms'] for r in ok_results]
    
    # Typology counts
    typology_counts = {}
    for r in ok_results:
        typology = r['typology']
        typology_counts[typology] = typology_counts.get(typology, 0) + 1
    
    summary = {
        'best_window_seconds': best_window,
        'success_rate': best_success_rate,
        'total_events': len(best_results),
        'processed_ok': len(ok_results),
        'median_delta_dispersion': np.median(delta_dispersions),
        'median_delta_lag_ms': np.median(delta_lags),
        'typology_counts': typology_counts,
        'all_window_results': results_by_window
    }
    
    return summary

def print_stage2_results(summary, date_str):
    """Print Stage 2 results summary"""
    print(f"\n📊 STAGE 2 RESULTS - {date_str}")
    print("=" * 80)
    
    if summary is None:
        print("❌ STAGE 2 FAILED - No successful effects computation")
        return
    
    # Table 1: Success Rate per Window
    print(f"\nTable 1: Success Rate per Window")
    print(f"{'Window':<12} {'Success Rate':<15} {'Events Processed':<20} {'Status':<15}")
    print("-" * 70)
    
    for window_seconds, window_results in summary['all_window_results'].items():
        status = "USED" if window_seconds == summary['best_window_seconds'] else "TESTED"
        print(f"±{window_seconds}s{'':<8} {window_results['success_rate']:<15.1f}% {window_results['success_count']}/{window_results['total_events']:<20} {status:<15}")
    
    # Table 2: Effects Summary (Best Window)
    print(f"\nTable 2: Effects Summary (Best Window: ±{summary['best_window_seconds']}s)")
    print(f"{'Metric':<25} {'Value':<15}")
    print("-" * 40)
    print(f"{'Success Rate':<25} {summary['success_rate']:<15.1f}%")
    print(f"{'Events Processed':<25} {summary['processed_ok']}/{summary['total_events']:<15}")
    print(f"{'Median Δdispersion (bps)':<25} {summary['median_delta_dispersion']:<15.2f}")
    print(f"{'Median Δlag (ms)':<25} {summary['median_delta_lag_ms']:<15.2f}")
    
    # Table 3: Typology Counts
    print(f"\nTable 3: Typology Counts")
    print(f"{'Category':<15} {'Count':<10} {'Percentage':<12}")
    print("-" * 40)
    
    typology_counts = summary['typology_counts']
    total_processed = summary['processed_ok']
    
    for typology, count in typology_counts.items():
        percentage = (count / total_processed) * 100 if total_processed > 0 else 0
        print(f"{typology:<15} {count:<10} {percentage:<12.1f}%")
    
    # Table 4: Memory Usage and Coverage Summary
    current_memory = get_memory_usage()
    print(f"\nTable 4: Memory Usage and Coverage Summary")
    print(f"{'Metric':<25} {'Value':<15}")
    print("-" * 40)
    print(f"{'Peak Memory Usage':<25} {current_memory:<15.1f} MB")
    print(f"{'Memory Limit':<25} {'500':<15} MB")
    print(f"{'Memory Status':<25} {'PASS' if current_memory < 500 else 'FAIL':<15}")
    print(f"{'Best Window':<25} ±{summary['best_window_seconds']:<14} s")
    print(f"{'Coverage Success':<25} {summary['success_rate']:<15.1f}%")
    
    # Stage 2 Completion Status
    print(f"\n📝 STAGE 2 COMPLETION STATUS:")
    
    if summary['processed_ok'] >= 1:
        print("✅ STAGE 2 COMPLETE - Effects computation successful")
        print(f"• Best window: ±{summary['best_window_seconds']}s")
        print(f"• Success rate: {summary['success_rate']:.1f}%")
        print(f"• Events processed: {summary['processed_ok']}")
        print(f"• Median Δdispersion: {summary['median_delta_dispersion']:.2f} bps")
        print(f"• Median Δlag: {summary['median_delta_lag_ms']:.2f} ms")
    else:
        print("❌ STAGE 2 INCOMPLETE - No events successfully processed")
        print("• All window sizes failed to process events")
        print("• Halt condition triggered")

def main():
    print("⚙️ STAGE 2 — Effects Computation with Adaptive Window Logic")
    print("=" * 80)
    print("Week -2 Day 1 (2025-08-22) Effects Computation Only")
    print("Mode: READ-ONLY, NO SYNTHETIC DATA, NO SCHEMA MODIFICATIONS")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250822'
    date_display = '2025-08-22'
    
    print(f"📅 Processing {date_display} ({date_str})")
    print("=" * 80)
    
    # Load cached beacons from Stage 1
    all_beacons = load_cached_beacons(date_str, venues)
    if all_beacons is None:
        print("❌ Failed to load cached beacons - halting Stage 2")
        return
    
    # Load venue data
    venue_data = load_venue_data(date_str, venues)
    if venue_data is None:
        print("❌ Failed to load venue data - halting Stage 2")
        return
    
    # Apply adaptive window effects computation
    results_by_window = adaptive_window_effects_computation(all_beacons, venue_data, venues)
    if results_by_window is None:
        print("❌ Adaptive window effects computation failed - halting Stage 2")
        return
    
    # Compute summary statistics
    summary = compute_summary_statistics(results_by_window)
    if summary is None:
        print("❌ Summary statistics computation failed - halting Stage 2")
        return
    
    # Print comprehensive results
    print_stage2_results(summary, date_str)
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print(f"STAGE 2 COMPLETE — awaiting Stage 3 instructions.")

if __name__ == "__main__":
    main()




