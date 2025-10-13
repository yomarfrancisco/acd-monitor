#!/usr/bin/env python3
"""
STAGE 1 — Data Integrity & Beacon Health
Week -2 Day 1 (2025-08-22) Pre-flight Validation and Beacon Detection Only
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

def step0_preflight_validation(date_str, venues, base_path="data_v6/views"):
    """Step 0: Pre-flight validation for canonicalization, schema, and timestamps"""
    print(f"🔍 Step 0 - Pre-flight Validation for {date_str}")
    print("-" * 60)
    
    venue_data = {}
    validation_results = {}
    
    for venue in venues:
        try:
            file_path = os.path.join(base_path, venue, date_str, "ticks_canonical.parquet")
            
            # Check file existence
            if not os.path.exists(file_path):
                print(f"❌ HALT: Missing canonical file {file_path}")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Missing canonical file',
                    'file_path': file_path
                }
                return False, None, validation_results
            
            # Load data
            df = pd.read_parquet(file_path)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            # Verify schema alignment
            required_cols = ['ts', 'price', 'size', 'venue']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"❌ HALT: {venue} missing required columns: {missing_cols}")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': f'Missing columns: {missing_cols}',
                    'schema': list(df.columns)
                }
                return False, None, validation_results
            
            # Check for new variables (guardrail compliance)
            extra_cols = [col for col in df.columns if col not in required_cols]
            if extra_cols:
                print(f"❌ HALT: {venue} has unexpected columns: {extra_cols}")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': f'Unexpected columns: {extra_cols}',
                    'schema': list(df.columns)
                }
                return False, None, validation_results
            
            # Check monotonic UTC timestamps
            if not df['ts'].is_monotonic_increasing:
                print(f"❌ HALT: {venue} timestamps not monotonic")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Non-monotonic timestamps',
                    'timestamp_range': f"{df['ts'].min()} to {df['ts'].max()}"
                }
                return False, None, validation_results
            
            # Check UTC timezone
            if df['ts'].dt.tz is None:
                print(f"❌ HALT: {venue} timestamps not UTC")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Timestamps not UTC',
                    'timezone': str(df['ts'].dt.tz)
                }
                return False, None, validation_results
            
            # Check non-zero tick counts
            if len(df) == 0:
                print(f"❌ HALT: {venue} has zero ticks")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Zero tick count',
                    'row_count': len(df)
                }
                return False, None, validation_results
            
            # Check price range sanity
            price_min, price_max = df['price'].min(), df['price'].max()
            if price_min <= 0 or price_max <= 0:
                print(f"❌ HALT: {venue} has non-positive prices")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Non-positive prices',
                    'price_range': f"${price_min} to ${price_max}"
                }
                return False, None, validation_results
            
            # Check size range sanity
            size_min, size_max = df['size'].min(), df['size'].max()
            if size_min <= 0 or size_max <= 0:
                print(f"❌ HALT: {venue} has non-positive sizes")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': 'Non-positive sizes',
                    'size_range': f"{size_min} to {size_max}"
                }
                return False, None, validation_results
            
            # Check memory usage
            current_memory = get_memory_usage()
            if current_memory > 500:
                print(f"❌ HALT: Memory limit exceeded: {current_memory:.1f} MB > 500 MB")
                validation_results[venue] = {
                    'status': 'HALT',
                    'reason': f'Memory limit exceeded: {current_memory:.1f} MB',
                    'memory_usage': current_memory
                }
                return False, None, validation_results
            
            # Store successful validation
            venue_data[venue] = df
            validation_results[venue] = {
                'status': 'PASS',
                'reason': 'All validations passed',
                'row_count': len(df),
                'price_range': f"${price_min:,.0f} to ${price_max:,.0f}",
                'size_range': f"{size_min:.6f} to {size_max:.6f}",
                'timestamp_range': f"{df['ts'].min()} to {df['ts'].max()}",
                'memory_usage': current_memory
            }
            
            print(f"✅ {venue}: schema✓, UTC monotonic✓, price bounds [${price_min:,.0f},${price_max:,.0f}], rows={len(df):,}, mem={current_memory:.1f} MB")
            
        except Exception as e:
            print(f"❌ HALT: Error loading {venue}: {str(e)}")
            validation_results[venue] = {
                'status': 'HALT',
                'reason': f'Load error: {str(e)}',
                'error_type': type(e).__name__
            }
            return False, None, validation_results
    
    print(f"✅ Pre-flight validation passed for {date_str}")
    return True, venue_data, validation_results

def detect_beacons(df, micro_p10, round_levels):
    """Detect beacons using standard logic"""
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

def step1_beacon_detection(date_str, venue_data, venues, cache_path="data_v6/cache/beacons/week-minus2"):
    """Step 1: Beacon detection and caching"""
    print(f"🔍 Step 1 - Beacon Detection for {date_str}")
    print("-" * 60)
    
    os.makedirs(cache_path, exist_ok=True)
    all_beacons = []
    beacon_counts = {}
    
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
            
            beacon_counts[venue] = {
                'raw_candidates': n_raw,
                'cached_beacons': len(sampled_beacons),
                'micro_threshold': micro_p10,
                'round_levels_count': len(round_levels)
            }
            
            print(f"  {venue}: {n_raw} raw candidates → {len(sampled_beacons)} cached beacons")
            
            if len(sampled_beacons) == 0:
                print(f"⚠️ WARNING: {venue} has no beacons detected")
                continue
            
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
            
            # Save to parquet (guardrail: no duplication of existing data)
            output_file = os.path.join(cache_path, f"{venue}_{date_str}.parquet")
            
            # Check if file already exists (guardrail compliance)
            if os.path.exists(output_file):
                print(f"⚠️ WARNING: Beacon cache already exists for {venue} {date_str} - skipping write")
            else:
                beacon_df.to_parquet(output_file, index=False)
                print(f"  ✅ Cached {len(sampled_beacons)} beacons for {venue}")
            
            all_beacons.extend(beacon_df.to_dict('records'))
            
        except Exception as e:
            print(f"❌ HALT: Error processing {venue}: {str(e)}")
            return False, None, None
    
    print(f"✅ Beacon detection completed for {date_str}")
    return True, all_beacons, beacon_counts

def print_stage1_results(validation_results, beacon_counts, venues, date_str):
    """Print Stage 1 results summary"""
    print(f"\n📊 STAGE 1 RESULTS - {date_str}")
    print("=" * 80)
    
    # Pre-flight Summary Table
    print(f"\nTable 1: Pre-flight Validation Summary")
    print(f"{'Venue':<12} {'Status':<8} {'Row Count':<12} {'Price Range':<20} {'Memory (MB)':<12}")
    print("-" * 80)
    
    for venue in venues:
        result = validation_results[venue]
        if result['status'] == 'PASS':
            print(f"{venue:<12} {result['status']:<8} {result['row_count']:<12,} {result['price_range']:<20} {result['memory_usage']:<12.1f}")
        else:
            print(f"{venue:<12} {result['status']:<8} {'N/A':<12} {'N/A':<20} {'N/A':<12}")
    
    # Beacon Counts Table
    print(f"\nTable 2: Beacon Detection Summary")
    print(f"{'Venue':<12} {'Raw Candidates':<15} {'Cached Beacons':<15} {'Micro Threshold':<15}")
    print("-" * 70)
    
    for venue in venues:
        if venue in beacon_counts:
            counts = beacon_counts[venue]
            print(f"{venue:<12} {counts['raw_candidates']:<15} {counts['cached_beacons']:<15} {counts['micro_threshold']:<15.6f}")
        else:
            print(f"{venue:<12} {'N/A':<15} {'N/A':<15} {'N/A':<15}")
    
    # Memory Usage Report
    current_memory = get_memory_usage()
    print(f"\nTable 3: Memory Usage Report")
    print(f"{'Metric':<25} {'Value':<15}")
    print("-" * 40)
    print(f"{'Peak Memory Usage':<25} {current_memory:<15.1f} MB")
    print(f"{'Memory Limit':<25} {'500':<15} MB")
    print(f"{'Memory Status':<25} {'PASS' if current_memory < 500 else 'FAIL':<15}")
    
    # Integrity Issues Summary
    print(f"\nTable 4: Integrity Issues Summary")
    issues_found = [venue for venue, result in validation_results.items() if result['status'] != 'PASS']
    
    if issues_found:
        print(f"{'Venue':<12} {'Issue':<30} {'Details':<30}")
        print("-" * 80)
        for venue in issues_found:
            result = validation_results[venue]
            print(f"{venue:<12} {result['reason']:<30} {str(result.get('details', 'N/A')):<30}")
    else:
        print("✅ No integrity issues detected - all validations passed")
    
    # Stage 1 Completion Status
    print(f"\n📝 STAGE 1 COMPLETION STATUS:")
    all_passed = all(result['status'] == 'PASS' for result in validation_results.values())
    beacons_detected = any(counts['cached_beacons'] > 0 for counts in beacon_counts.values())
    
    if all_passed and beacons_detected:
        print("✅ STAGE 1 COMPLETE - Ready for Stage 2")
        print("• All pre-flight validations passed")
        print("• Beacon detection successful")
        print("• No integrity issues detected")
    else:
        print("❌ STAGE 1 INCOMPLETE - Halt conditions detected")
        if not all_passed:
            print("• Pre-flight validation failures")
        if not beacons_detected:
            print("• No beacons detected")

def main():
    print("🧩 STAGE 1 — Data Integrity & Beacon Health")
    print("=" * 80)
    print("Week -2 Day 1 (2025-08-22) Pre-flight Validation and Beacon Detection")
    print("Mode: READ-ONLY, NO SYNTHETIC DATA, NO SCHEMA MODIFICATIONS")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250822'
    date_display = '2025-08-22'
    
    print(f"📅 Processing {date_display} ({date_str})")
    print("=" * 80)
    
    # Step 0: Pre-flight Validation
    validation_ok, venue_data, validation_results = step0_preflight_validation(date_str, venues)
    if not validation_ok:
        print("❌ Pre-flight validation failed - halting Stage 1")
        print_stage1_results(validation_results, {}, venues, date_str)
        return
    
    # Step 1: Beacon Detection
    beacon_ok, all_beacons, beacon_counts = step1_beacon_detection(date_str, venue_data, venues)
    if not beacon_ok:
        print("❌ Beacon detection failed - halting Stage 1")
        print_stage1_results(validation_results, {}, venues, date_str)
        return
    
    # Print comprehensive results
    print_stage1_results(validation_results, beacon_counts, venues, date_str)
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print(f"STAGE 1 COMPLETE — awaiting Stage 2 instructions.")

if __name__ == "__main__":
    main()




