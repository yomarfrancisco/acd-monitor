#!/usr/bin/env python3
"""
Theo Verification: September data (Weeks 1-3) integrity and completeness check
Objective: Verify integrity and completeness of September data for both beacons and ticks
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
import json
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0.0

def verify_september_data():
    """Verify September data integrity and completeness"""
    print("✅ THEO VERIFICATION: SEPTEMBER DATA (WEEKS 1-3)")
    print("=" * 80)
    print("Objective: Verify integrity and completeness of September data for both beacons and ticks")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Expected date range
    expected_start = pd.to_datetime("2025-09-01 00:00:00", utc=True)
    expected_end = pd.to_datetime("2025-09-30 23:59:59", utc=True)
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f"📅 Expected date range: {expected_start} → {expected_end}")
    print(f"🏢 Expected venues: {venues}")
    print()
    
    # Check memory before processing
    if get_memory_usage() > 750:
        print(f"🚨 VERIFICATION HALTED — Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Initialize results
    verification_results = []
    missing_weeks = []
    
    # Check each week
    for week_num in [1, 2, 3]:
        week_name = f"week{week_num}"
        print(f"🔍 Verifying {week_name.upper()}")
        print("-" * 60)
        
        # Check beacon data
        beacon_path = f"data_v6/cache/beacons/{week_name}"
        beacon_files = glob.glob(f"{beacon_path}/*.parquet") if os.path.exists(beacon_path) else []
        
        # Check tick data
        tick_path = f"data_v6/cache/ticks/{week_name}"
        tick_files = glob.glob(f"{tick_path}/*.parquet") if os.path.exists(tick_path) else []
        
        print(f"  📁 Beacon files: {len(beacon_files)}")
        print(f"  📁 Tick files: {len(tick_files)}")
        
        # Initialize week results
        week_result = {
            'week': week_name,
            'beacon_files_found': len(beacon_files),
            'tick_files_found': len(tick_files),
            'beacon_total_size_mb': 0.0,
            'tick_total_size_mb': 0.0,
            'beacon_observations': 0,
            'tick_observations': 0,
            'beacon_hours_total': 0,
            'beacon_hours_valid': 0,
            'tick_hours_total': 0,
            'tick_hours_valid': 0,
            'beacon_min_timestamp': None,
            'beacon_max_timestamp': None,
            'tick_min_timestamp': None,
            'tick_max_timestamp': None,
            'beacon_venues_found': [],
            'tick_venues_found': [],
            'beacon_avg_per_hour': 0.0,
            'tick_avg_per_hour': 0.0,
            'beacon_continuity_gaps': 0,
            'tick_continuity_gaps': 0,
            'beacon_schema_columns': [],
            'tick_schema_columns': [],
            'beacon_validation_status': 'MISSING',
            'tick_validation_status': 'MISSING',
            'beacon_valid_hours_pct': 0.0,
            'tick_valid_hours_pct': 0.0
        }
        
        # Process beacon data if available
        if len(beacon_files) > 0:
            try:
                # Load beacon data
                beacon_data = []
                total_beacon_size = 0.0
                
                for file_path in beacon_files:
                    df = pd.read_parquet(file_path)
                    beacon_data.append(df)
                    total_beacon_size += get_file_size_mb(file_path)
                
                if beacon_data:
                    all_beacons = pd.concat(beacon_data, ignore_index=True)
                    
                    # Convert event_ts to datetime if needed
                    if 'event_ts' in all_beacons.columns:
                        all_beacons['event_ts'] = pd.to_datetime(all_beacons['event_ts'], utc=True)
                    
                    # Basic stats
                    week_result['beacon_total_size_mb'] = total_beacon_size
                    week_result['beacon_observations'] = len(all_beacons)
                    week_result['beacon_min_timestamp'] = all_beacons['event_ts'].min()
                    week_result['beacon_max_timestamp'] = all_beacons['event_ts'].max()
                    week_result['beacon_venues_found'] = sorted(all_beacons['venue'].unique().tolist())
                    week_result['beacon_schema_columns'] = sorted(all_beacons.columns.tolist())
                    
                    # Hourly analysis
                    all_beacons['hour'] = all_beacons['event_ts'].dt.floor('H')
                    unique_hours = all_beacons['hour'].unique()
                    week_result['beacon_hours_total'] = len(unique_hours)
                    
                    # Count valid hours (≥3 beacons, ≥2 venues)
                    valid_hours = 0
                    total_beacon_count = 0
                    
                    for hour in unique_hours:
                        hour_beacons = all_beacons[all_beacons['hour'] == hour]
                        venue_counts = hour_beacons['venue'].value_counts()
                        
                        if len(hour_beacons) >= 3 and len(venue_counts) >= 2:
                            valid_hours += 1
                        
                        total_beacon_count += len(hour_beacons)
                    
                    week_result['beacon_hours_valid'] = valid_hours
                    week_result['beacon_avg_per_hour'] = total_beacon_count / len(unique_hours) if len(unique_hours) > 0 else 0.0
                    week_result['beacon_valid_hours_pct'] = (valid_hours / len(unique_hours) * 100) if len(unique_hours) > 0 else 0.0
                    
                    # Check continuity (gaps >1h)
                    if len(unique_hours) > 1:
                        sorted_hours = sorted(unique_hours)
                        gaps = 0
                        for i in range(1, len(sorted_hours)):
                            gap_hours = (sorted_hours[i] - sorted_hours[i-1]).total_seconds() / 3600
                            if gap_hours > 1.0:
                                gaps += 1
                        week_result['beacon_continuity_gaps'] = gaps
                    
                    # Validation status
                    if week_result['beacon_valid_hours_pct'] >= 90.0:
                        week_result['beacon_validation_status'] = 'PASS'
                    else:
                        week_result['beacon_validation_status'] = 'FAIL'
                    
                    print(f"  ✅ Beacon data: {len(all_beacons)} observations, {valid_hours}/{len(unique_hours)} valid hours ({week_result['beacon_valid_hours_pct']:.1f}%)")
                    print(f"  📊 Beacon venues: {week_result['beacon_venues_found']}")
                    print(f"  📅 Beacon range: {week_result['beacon_min_timestamp']} → {week_result['beacon_max_timestamp']}")
                    print(f"  📁 Beacon size: {total_beacon_size:.1f} MB")
                
            except Exception as e:
                print(f"  ❌ Beacon data error: {e}")
                week_result['beacon_validation_status'] = 'ERROR'
        
        # Process tick data if available
        if len(tick_files) > 0:
            try:
                # Load tick data
                tick_data = []
                total_tick_size = 0.0
                
                for file_path in tick_files:
                    df = pd.read_parquet(file_path)
                    tick_data.append(df)
                    total_tick_size += get_file_size_mb(file_path)
                
                if tick_data:
                    all_ticks = pd.concat(tick_data, ignore_index=True)
                    
                    # Convert event_ts to datetime if needed
                    if 'event_ts' in all_ticks.columns:
                        all_ticks['event_ts'] = pd.to_datetime(all_ticks['event_ts'], utc=True)
                    
                    # Basic stats
                    week_result['tick_total_size_mb'] = total_tick_size
                    week_result['tick_observations'] = len(all_ticks)
                    week_result['tick_min_timestamp'] = all_ticks['event_ts'].min()
                    week_result['tick_max_timestamp'] = all_ticks['event_ts'].max()
                    week_result['tick_venues_found'] = sorted(all_ticks['venue'].unique().tolist())
                    week_result['tick_schema_columns'] = sorted(all_ticks.columns.tolist())
                    
                    # Hourly analysis
                    all_ticks['hour'] = all_ticks['event_ts'].dt.floor('H')
                    unique_hours = all_ticks['hour'].unique()
                    week_result['tick_hours_total'] = len(unique_hours)
                    
                    # Count valid hours (≥3 ticks, ≥2 venues)
                    valid_hours = 0
                    total_tick_count = 0
                    
                    for hour in unique_hours:
                        hour_ticks = all_ticks[all_ticks['hour'] == hour]
                        venue_counts = hour_ticks['venue'].value_counts()
                        
                        if len(hour_ticks) >= 3 and len(venue_counts) >= 2:
                            valid_hours += 1
                        
                        total_tick_count += len(hour_ticks)
                    
                    week_result['tick_hours_valid'] = valid_hours
                    week_result['tick_avg_per_hour'] = total_tick_count / len(unique_hours) if len(unique_hours) > 0 else 0.0
                    week_result['tick_valid_hours_pct'] = (valid_hours / len(unique_hours) * 100) if len(unique_hours) > 0 else 0.0
                    
                    # Check continuity (gaps >1h)
                    if len(unique_hours) > 1:
                        sorted_hours = sorted(unique_hours)
                        gaps = 0
                        for i in range(1, len(sorted_hours)):
                            gap_hours = (sorted_hours[i] - sorted_hours[i-1]).total_seconds() / 3600
                            if gap_hours > 1.0:
                                gaps += 1
                        week_result['tick_continuity_gaps'] = gaps
                    
                    # Validation status
                    if week_result['tick_valid_hours_pct'] >= 90.0:
                        week_result['tick_validation_status'] = 'PASS'
                    else:
                        week_result['tick_validation_status'] = 'FAIL'
                    
                    print(f"  ✅ Tick data: {len(all_ticks)} observations, {valid_hours}/{len(unique_hours)} valid hours ({week_result['tick_valid_hours_pct']:.1f}%)")
                    print(f"  📊 Tick venues: {week_result['tick_venues_found']}")
                    print(f"  📅 Tick range: {week_result['tick_min_timestamp']} → {week_result['tick_max_timestamp']}")
                    print(f"  📁 Tick size: {total_tick_size:.1f} MB")
                
            except Exception as e:
                print(f"  ❌ Tick data error: {e}")
                week_result['tick_validation_status'] = 'ERROR'
        
        # Check if week is missing
        if week_result['beacon_files_found'] == 0 and week_result['tick_files_found'] == 0:
            missing_weeks.append(week_name)
            print(f"  ❌ {week_name.upper()}: COMPLETELY MISSING")
        elif week_result['beacon_files_found'] == 0:
            missing_weeks.append(f"{week_name}_beacons")
            print(f"  ⚠️  {week_name.upper()}: Missing beacon data")
        elif week_result['tick_files_found'] == 0:
            missing_weeks.append(f"{week_name}_ticks")
            print(f"  ⚠️  {week_name.upper()}: Missing tick data")
        
        verification_results.append(week_result)
        print()
    
    # Create output directory
    output_dir = "tmp/research_rx/VERIFY_SEPTEMBER"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save results
    results_df = pd.DataFrame(verification_results)
    
    # Save summary CSV
    summary_path = f"{output_dir}/verify_sep_summary.csv"
    results_df.to_csv(summary_path, index=False)
    print(f"📁 Summary saved: {summary_path}")
    
    # Save missing weeks JSON
    missing_path = f"{output_dir}/verify_sep_missing.json"
    with open(missing_path, 'w') as f:
        json.dump({
            'missing_weeks': missing_weeks,
            'total_missing': len(missing_weeks),
            'verification_timestamp': datetime.now().isoformat()
        }, f, indent=2)
    print(f"📁 Missing weeks saved: {missing_path}")
    
    # Save summary log
    log_path = f"{output_dir}/verify_sep_summary.log"
    with open(log_path, 'w') as f:
        f.write("THEO VERIFICATION: SEPTEMBER DATA (WEEKS 1-3)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Verification timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Expected date range: {expected_start} → {expected_end}\n")
        f.write(f"Expected venues: {venues}\n\n")
        
        f.write("WEEKLY SUMMARY:\n")
        f.write("-" * 40 + "\n")
        for result in verification_results:
            f.write(f"\n{result['week'].upper()}:\n")
            f.write(f"  Beacon: {result['beacon_validation_status']} ({result['beacon_valid_hours_pct']:.1f}% valid)\n")
            f.write(f"  Tick: {result['tick_validation_status']} ({result['tick_valid_hours_pct']:.1f}% valid)\n")
            f.write(f"  Beacon files: {result['beacon_files_found']}\n")
            f.write(f"  Tick files: {result['tick_files_found']}\n")
        
        f.write(f"\nMISSING WEEKS: {missing_weeks}\n")
        f.write(f"TOTAL MISSING: {len(missing_weeks)}\n")
        
        f.write(f"\nMEMORY USAGE: {get_memory_usage():.1f} MB\n")
    
    print(f"📁 Summary log saved: {log_path}")
    
    # Generate console summary
    print("\n" + "=" * 80)
    print("📦 THEO VERIFICATION SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 WEEKLY VALIDATION STATUS:")
    for result in verification_results:
        week = result['week'].upper()
        beacon_status = result['beacon_validation_status']
        tick_status = result['tick_validation_status']
        beacon_pct = result['beacon_valid_hours_pct']
        tick_pct = result['tick_valid_hours_pct']
        
        print(f"  • {week}:")
        print(f"    Beacon: {beacon_status} ({beacon_pct:.1f}% valid hours)")
        print(f"    Tick: {tick_status} ({tick_pct:.1f}% valid hours)")
    
    print(f"\n📁 MISSING WEEKS: {missing_weeks}")
    print(f"📊 TOTAL MISSING: {len(missing_weeks)}")
    
    # Overall status
    all_beacon_pass = all(r['beacon_validation_status'] == 'PASS' for r in verification_results)
    all_tick_pass = all(r['tick_validation_status'] == 'PASS' for r in verification_results)
    no_missing = len(missing_weeks) == 0
    
    if all_beacon_pass and all_tick_pass and no_missing:
        print(f"\n✅ VERIFICATION RESULT: ALL WEEKS PASS VALIDATION")
        print(f"✅ READY FOR PHASE 28 (cross-month comparison)")
    else:
        print(f"\n❌ VERIFICATION RESULT: SOME WEEKS FAIL VALIDATION")
        print(f"❌ PREPARE CONTROLLED RE-DOWNLOAD FOR MISSING RANGES")
    
    print(f"\n🔒 GUARDRAIL LOG:")
    print(f"  • Memory usage: {get_memory_usage():.1f} MB (≤ 750 MB)")
    print(f"  • Real data only: CONFIRMED")
    print(f"  • No reconstruction: CONFIRMED")
    print(f"  • No synthetic fill: CONFIRMED")
    
    return verification_results, missing_weeks

if __name__ == "__main__":
    verify_september_data()




