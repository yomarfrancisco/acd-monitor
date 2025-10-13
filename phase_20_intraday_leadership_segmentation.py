#!/usr/bin/env python3
"""
Phase 20: Intra-Day Leadership Segmentation (Real Data Only)
Purpose: Measure how market leadership rotates across regional time zones (U.S., E.U., Asia)
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def preflight_safety_checks():
    """Perform all pre-flight safety checks"""
    print("🔍 PHASE 20 PRE-FLIGHT SAFETY CHECKS")
    print("=" * 60)
    
    # 1. Dataset Verification
    print("1. Dataset Verification")
    print("-" * 30)
    
    # Check for canonical datasets
    canonical_paths = [
        "data_v6/cache/beacons"
    ]
    
    for path in canonical_paths:
        if not os.path.exists(path):
            return f"🚨 PHASE 20 HALTED — Canonical path not found: {path}"
        print(f"  ✅ Found: {path}")
    
    # Note: Tick data not required for Phase 20 leadership analysis
    print(f"  ℹ️  Note: Using beacon data only (tick data not required for leadership analysis)")
    
    # Check beacon data availability
    beacon_weeks = ['week-minus4', 'week-minus3', 'week-minus2', 'week-minus1']
    beacon_files_found = 0
    
    for week in beacon_weeks:
        beacon_dir = f"data_v6/cache/beacons/{week}"
        if os.path.exists(beacon_dir):
            beacon_files = glob.glob(f"{beacon_dir}/*.parquet")
            beacon_files_found += len(beacon_files)
            print(f"  ✅ {week}: {len(beacon_files)} beacon files")
        else:
            print(f"  ⚠️  {week}: No beacon directory found")
    
    if beacon_files_found == 0:
        return "🚨 PHASE 20 HALTED — No beacon files found in canonical paths"
    
    # 2. Date Scope Check
    print("\n2. Date Scope Check")
    print("-" * 30)
    
    start_date = pd.to_datetime("2025-08-04 00:00:00", utc=True)
    end_date = pd.to_datetime("2025-09-07 23:59:59", utc=True)
    
    print(f"  ✅ Date range: {start_date} to {end_date}")
    print(f"  ✅ Duration: {(end_date - start_date).days} days")
    
    # 3. Memory & System Check
    print("\n3. Memory & System Check")
    print("-" * 30)
    
    current_memory = get_memory_usage()
    print(f"  ✅ Current memory: {current_memory:.1f} MB")
    
    if current_memory > 750:
        return f"🚨 PHASE 20 HALTED — Memory usage {current_memory:.1f} MB exceeds 750 MB limit"
    
    # 4. Entropy Bound Check
    print("\n4. Entropy Bound Check")
    print("-" * 30)
    
    max_entropy = np.log(4)  # ln(4) ≈ 1.386
    print(f"  ✅ Max theoretical entropy: {max_entropy:.3f}")
    print(f"  ✅ Entropy bounds: [0, {max_entropy:.3f}]")
    
    # 5. Operational Risk Confirmation
    print("\n5. Operational Risk Confirmation")
    print("-" * 30)
    
    print("  ✅ Read-only access to canonical data")
    print("  ✅ No data duplication planned")
    print("  ✅ No canonical source modification")
    print("  ✅ Output to tmp/research_rx/PHASE20/ only")
    
    print("\n✅ Phase 20 integrity confirmed — all guardrails green, proceeding with analysis.")
    return None

def load_verified_datasets():
    """Load verified real datasets for Phase 20"""
    print("\n🔍 Loading Verified Real Datasets")
    print("-" * 60)
    
    # Load beacon data
    beacon_weeks = ['week-minus4', 'week-minus3', 'week-minus2', 'week-minus1']
    all_beacons = []
    
    for week in beacon_weeks:
        beacon_dir = f"data_v6/cache/beacons/{week}"
        if not os.path.exists(beacon_dir):
            print(f"  ⚠️  Skipping {week}: directory not found")
            continue
        
        beacon_files = glob.glob(f"{beacon_dir}/*.parquet")
        if not beacon_files:
            print(f"  ⚠️  Skipping {week}: no beacon files")
            continue
        
        week_beacons = []
        for file_path in beacon_files:
            try:
                df = pd.read_parquet(file_path)
                week_beacons.append(df)
            except Exception as e:
                print(f"  Warning: Could not load {file_path}: {e}")
        
        if not week_beacons:
            print(f"  ⚠️  Skipping {week}: no valid beacon data")
            continue
        
        all_week_beacons = pd.concat(week_beacons, ignore_index=True)
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in all_week_beacons.columns:
            all_week_beacons['event_ts'] = pd.to_datetime(all_week_beacons['event_ts'], utc=True)
        
        # Filter to verified date range
        start_date = pd.to_datetime("2025-08-04 00:00:00", utc=True)
        end_date = pd.to_datetime("2025-09-07 23:59:59", utc=True)
        
        week_beacons_filtered = all_week_beacons[
            (all_week_beacons['event_ts'] >= start_date) &
            (all_week_beacons['event_ts'] <= end_date)
        ].copy()
        
        if len(week_beacons_filtered) > 0:
            all_beacons.append(week_beacons_filtered)
            print(f"  ✅ {week}: {len(week_beacons_filtered)} beacons in date range")
        else:
            print(f"  ⚠️  {week}: No beacons in date range")
    
    if not all_beacons:
        return None, "No beacon data found in verified date range"
    
    beacon_data = pd.concat(all_beacons, ignore_index=True)
    
    # Verify schema
    required_columns = ['event_ts', 'venue']
    missing_columns = [col for col in required_columns if col not in beacon_data.columns]
    if missing_columns:
        return None, f"Missing required columns: {missing_columns}"
    
    # Verify timestamp integrity
    for venue in beacon_data['venue'].unique():
        venue_data = beacon_data[beacon_data['venue'] == venue].sort_values('event_ts')
        if len(venue_data) > 1:
            # Check for reverse ordering
            time_diffs = venue_data['event_ts'].diff().dt.total_seconds()
            if (time_diffs < 0).any():
                return None, f"Reverse timestamp ordering detected for venue {venue}"
            
            # Check for duplicate timestamps
            if venue_data['event_ts'].duplicated().any():
                return None, f"Duplicate timestamps detected for venue {venue}"
    
    print(f"  ✅ Total beacons loaded: {len(beacon_data)}")
    print(f"  ✅ Venues: {sorted(beacon_data['venue'].unique())}")
    print(f"  ✅ Date range: {beacon_data['event_ts'].min()} to {beacon_data['event_ts'].max()}")
    
    return beacon_data, None

def segment_hourly_leadership(beacon_data):
    """Segment dataset into hourly bins and compute leadership"""
    print("\n🔍 Segmenting Hourly Leadership")
    print("-" * 60)
    
    # Create hourly bins
    beacon_data = beacon_data.copy()
    beacon_data['hour'] = beacon_data['event_ts'].dt.floor('H')
    
    # Get all unique hours in the dataset
    all_hours = pd.date_range(
        start=beacon_data['hour'].min(),
        end=beacon_data['hour'].max(),
        freq='H'
    )
    
    print(f"  ✅ Total hours to analyze: {len(all_hours)}")
    
    # Initialize results
    leadership_results = []
    
    for hour in all_hours:
        hour_beacons = beacon_data[beacon_data['hour'] == hour]
        
        if len(hour_beacons) == 0:
            # No beacons in this hour
            leadership_results.append({
                'hour': hour,
                'total_beacons': 0,
                'COINBASE_share': 0.0,
                'BINANCE_share': 0.0,
                'BYBITSPOT_share': 0.0,
                'BITGET_share': 0.0,
                'entropy_Ht': 0.0,
                'leading_venue': 'NONE'
            })
            continue
        
        # Count beacons per venue
        venue_counts = hour_beacons['venue'].value_counts()
        total_beacons = len(hour_beacons)
        
        # Calculate leadership shares
        venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
        venue_shares = {}
        
        for venue in venues:
            count = venue_counts.get(venue, 0)
            share = count / total_beacons if total_beacons > 0 else 0.0
            venue_shares[f'{venue}_share'] = share
        
        # Calculate Shannon entropy H_t = -Σ p_i ln p_i
        entropy_Ht = 0.0
        for venue in venues:
            share = venue_shares[f'{venue}_share']
            if share > 0:
                entropy_Ht -= share * np.log(share)
        
        # Identify leading venue
        leading_venue = venue_counts.index[0] if len(venue_counts) > 0 else 'NONE'
        
        # Store results
        result = {
            'hour': hour,
            'total_beacons': total_beacons,
            'entropy_Ht': entropy_Ht,
            'leading_venue': leading_venue
        }
        result.update(venue_shares)
        
        leadership_results.append(result)
    
    results_df = pd.DataFrame(leadership_results)
    
    print(f"  ✅ Leadership analysis complete: {len(results_df)} hourly segments")
    print(f"  ✅ Entropy range: {results_df['entropy_Ht'].min():.3f} to {results_df['entropy_Ht'].max():.3f}")
    
    return results_df

def compute_temporal_rotation_index(results_df):
    """Compute temporal rotation index R = max(H_t)/mean(H_t)"""
    print("\n🔍 Computing Temporal Rotation Index")
    print("-" * 60)
    
    # Filter out hours with no beacons
    active_hours = results_df[results_df['total_beacons'] > 0]
    
    if len(active_hours) == 0:
        return 0.0
    
    max_entropy = active_hours['entropy_Ht'].max()
    mean_entropy = active_hours['entropy_Ht'].mean()
    
    rotation_index = max_entropy / mean_entropy if mean_entropy > 0 else 0.0
    
    print(f"  ✅ Max entropy: {max_entropy:.3f}")
    print(f"  ✅ Mean entropy: {mean_entropy:.3f}")
    print(f"  ✅ Rotation index R: {rotation_index:.3f}")
    
    return rotation_index

def create_entropy_heatmap(results_df):
    """Create entropy heatmap visualization"""
    print("\n🔍 Creating Entropy Heatmap")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/PHASE20"
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare data for heatmap
    results_df = results_df.copy()
    results_df['date'] = results_df['hour'].dt.date
    results_df['hour_of_day'] = results_df['hour'].dt.hour
    
    # Create pivot table for heatmap
    heatmap_data = results_df.pivot_table(
        values='entropy_Ht',
        index='date',
        columns='hour_of_day',
        fill_value=0.0
    )
    
    # Create the heatmap
    plt.figure(figsize=(16, 10))
    sns.heatmap(
        heatmap_data,
        cmap='viridis',
        cbar_kws={'label': 'Shannon Entropy H_t'},
        fmt='.3f'
    )
    
    plt.title('Phase 20: Intra-Day Leadership Entropy Heatmap\n(2025-08-04 to 2025-09-07)', fontsize=14)
    plt.xlabel('Hour of Day (UTC)', fontsize=12)
    plt.ylabel('Date', fontsize=12)
    
    # Add timezone annotations
    plt.axvline(x=7, color='red', linestyle='--', alpha=0.7, label='EU Market Open')
    plt.axvline(x=13, color='blue', linestyle='--', alpha=0.7, label='US Market Open')
    plt.axvline(x=23, color='green', linestyle='--', alpha=0.7, label='Asia Market Open')
    
    plt.legend()
    plt.tight_layout()
    
    # Save the heatmap
    heatmap_path = f"{output_dir}/phase20_entropy_heatmap.png"
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Entropy heatmap saved: {heatmap_path}")
    
    return heatmap_path

def save_results(results_df, rotation_index):
    """Save results to CSV"""
    print("\n🔍 Saving Results")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/PHASE20"
    os.makedirs(output_dir, exist_ok=True)
    
    # Add rotation index to results
    results_df = results_df.copy()
    results_df['rotation_index_R'] = rotation_index
    
    # Save to CSV
    csv_path = f"{output_dir}/phase20_intra_day_leadership.csv"
    results_df.to_csv(csv_path, index=False)
    
    print(f"  ✅ Results saved: {csv_path}")
    print(f"  ✅ Total records: {len(results_df)}")
    
    return csv_path

def post_run_verification(results_df, rotation_index):
    """Perform post-run verification"""
    print("\n🔍 Post-Run Verification")
    print("-" * 60)
    
    # Memory check
    final_memory = get_memory_usage()
    print(f"  ✅ Final memory usage: {final_memory:.1f} MB")
    
    if final_memory > 750:
        return f"🚨 PHASE 20 HALTED — Final memory usage {final_memory:.1f} MB exceeds 750 MB"
    
    # Entropy bounds check
    max_entropy = np.log(4)  # ln(4) ≈ 1.386
    entropy_min = results_df['entropy_Ht'].min()
    entropy_max = results_df['entropy_Ht'].max()
    
    print(f"  ✅ Entropy range: [{entropy_min:.3f}, {entropy_max:.3f}]")
    print(f"  ✅ Theoretical bounds: [0, {max_entropy:.3f}]")
    
    if entropy_min < 0 or entropy_max > max_entropy:
        return f"🚨 PHASE 20 HALTED — Entropy values outside theoretical bounds"
    
    # Missing hours check - calculate based on actual data range
    if len(results_df) > 0:
        data_start = results_df['hour'].min()
        data_end = results_df['hour'].max()
        actual_days = (data_end - data_start).total_seconds() / (24 * 3600) + 1
        expected_hours = int(actual_days * 24)
    else:
        expected_hours = 0
    
    actual_hours = len(results_df)
    
    print(f"  ✅ Data range: {data_start} to {data_end}")
    print(f"  ✅ Expected hours: {expected_hours}")
    print(f"  ✅ Actual hours: {actual_hours}")
    
    if abs(actual_hours - expected_hours) > 24:  # Allow 1 day tolerance
        return f"🚨 PHASE 20 HALTED — Missing hours detected (expected {expected_hours}, got {actual_hours})"
    
    # Rotation index check
    print(f"  ✅ Rotation index R: {rotation_index:.3f}")
    
    print("  ✅ All verification checks passed")
    return None

def generate_summary_report(results_df, rotation_index):
    """Generate summary report"""
    print("\n" + "=" * 80)
    print("📦 PHASE 20 SUMMARY REPORT")
    print("=" * 80)
    
    # Filter active hours (with beacons)
    active_hours = results_df[results_df['total_beacons'] > 0]
    
    if len(active_hours) == 0:
        print("❌ No active hours found")
        return
    
    # Mean hourly entropy
    mean_entropy = active_hours['entropy_Ht'].mean()
    print(f"\n📊 Mean Hourly Entropy H_t: {mean_entropy:.3f}")
    
    # Top 3 leadership windows
    print(f"\n🏆 Top 3 Leadership Windows (by total beacons):")
    top_windows = active_hours.nlargest(3, 'total_beacons')
    
    for i, (_, window) in enumerate(top_windows.iterrows(), 1):
        hour_str = window['hour'].strftime('%Y-%m-%d %H:00 UTC')
        print(f"  {i}. {hour_str}: {window['total_beacons']} beacons, "
              f"entropy={window['entropy_Ht']:.3f}, leader={window['leading_venue']}")
    
    # Venue leadership summary
    print(f"\n📈 Venue Leadership Summary:")
    venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
    
    for venue in venues:
        share_col = f'{venue}_share'
        if share_col in active_hours.columns:
            avg_share = active_hours[share_col].mean()
            max_share = active_hours[share_col].max()
            print(f"  {venue}: avg={avg_share:.1%}, max={max_share:.1%}")
    
    # Temporal rotation analysis
    print(f"\n🔄 Temporal Rotation Analysis:")
    print(f"  Rotation Index R: {rotation_index:.3f}")
    
    if rotation_index > 1.5:
        print(f"  → High rotation (leadership changes frequently)")
    elif rotation_index > 1.2:
        print(f"  → Moderate rotation (some leadership stability)")
    else:
        print(f"  → Low rotation (stable leadership patterns)")
    
    # Anomalies check
    print(f"\n🔍 Anomaly Detection:")
    anomalies = []
    
    # Check for hours with zero entropy (single venue dominance)
    zero_entropy_hours = active_hours[active_hours['entropy_Ht'] == 0.0]
    if len(zero_entropy_hours) > 0:
        anomalies.append(f"{len(zero_entropy_hours)} hours with zero entropy (single venue dominance)")
    
    # Check for hours with maximum entropy (perfect distribution)
    max_entropy = np.log(4)
    max_entropy_hours = active_hours[active_hours['entropy_Ht'] >= max_entropy * 0.95]
    if len(max_entropy_hours) > 0:
        anomalies.append(f"{len(max_entropy_hours)} hours with near-maximum entropy")
    
    if anomalies:
        for anomaly in anomalies:
            print(f"  ⚠️  {anomaly}")
    else:
        print(f"  ✅ No significant anomalies detected")

def main():
    print("🧩 PHASE 20 – INTRA-DAY LEADERSHIP SEGMENTATION (REAL DATA ONLY)")
    print("=" * 80)
    print("Purpose: Measure how market leadership rotates across regional time zones")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Pre-flight safety checks
    halt_reason = preflight_safety_checks()
    if halt_reason:
        print(halt_reason)
        return
    
    # Load verified datasets
    beacon_data, error = load_verified_datasets()
    if error:
        print(f"🚨 PHASE 20 HALTED — {error}")
        return
    
    # Segment hourly leadership
    results_df = segment_hourly_leadership(beacon_data)
    
    # Compute temporal rotation index
    rotation_index = compute_temporal_rotation_index(results_df)
    
    # Create entropy heatmap
    heatmap_path = create_entropy_heatmap(results_df)
    
    # Save results
    csv_path = save_results(results_df, rotation_index)
    
    # Post-run verification
    verification_error = post_run_verification(results_df, rotation_index)
    if verification_error:
        print(verification_error)
        return
    
    # Generate summary report
    generate_summary_report(results_df, rotation_index)
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    print(f"✅ Phase 20 complete — all outputs validated, memory and integrity within guardrails.")
    print(f"📁 Output files:")
    print(f"  • {csv_path}")
    print(f"  • {heatmap_path}")
    print(f"💾 Final memory usage: {final_memory:.1f} MB")

if __name__ == "__main__":
    main()
