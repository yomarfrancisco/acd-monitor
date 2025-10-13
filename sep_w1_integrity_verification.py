#!/usr/bin/env python3
"""
✅ Integrity & Completeness Verification Prompt (for Week 1)
TASK: Verify integrity, completeness, and schema conformity of September Week 1 BTC beacon + tick data
"""

import os
import pandas as pd
import numpy as np
import json
import hashlib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_file_hash(filepath):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_august_reference_schema():
    """Get reference schema from August data (Weeks -1 to -4)"""
    # Try to find August beacon data for reference
    august_beacon_paths = [
        'data_v6/cache/beacons/week-minus1',
        'data_v6/cache/beacons/week-minus2', 
        'data_v6/cache/beacons/week-minus3',
        'data_v6/cache/beacons/week-minus4'
    ]
    
    reference_schema = None
    for path in august_beacon_paths:
        if os.path.exists(path):
            # Look for parquet files
            for file in os.listdir(path):
                if file.endswith('.parquet'):
                    try:
                        df = pd.read_parquet(os.path.join(path, file))
                        reference_schema = {
                            'columns': df.columns.tolist(),
                            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                            'source_file': os.path.join(path, file)
                        }
                        break
                    except:
                        continue
            if reference_schema:
                break
    
    return reference_schema

def verify_sep_w1_integrity():
    """Run comprehensive integrity and completeness verification for September Week 1"""
    print("✅ INTEGRITY & COMPLETENESS VERIFICATION - WEEK 1")
    print("=" * 80)
    print("TASK: Verify integrity, completeness, and schema conformity of September Week 1 BTC beacon + tick data")
    print()
    
    # Create output directory
    output_dir = 'tmp/research_rx/VERIFY_SEP_W1'
    os.makedirs(output_dir, exist_ok=True)
    
    # Input files
    tick_file = 'data_v6/cache/ticks/sep_w1/combined_sep_w1_ticks.parquet'
    beacon_file = 'data_v6/cache/beacons/sep_w1/combined_sep_w1_beacons.parquet'
    metadata_file = 'tmp/research_rx/INGEST_SEP_W1/ingest_sep_w1_metadata.json'
    
    print(f"📁 **Input Files:**")
    print(f"📁 Ticks: {tick_file}")
    print(f"📁 Beacons: {beacon_file}")
    print(f"📁 Metadata: {metadata_file}")
    print()
    
    # Initialize results
    integrity_report = {
        'verification_timestamp': datetime.now().isoformat(),
        'week': 'sep_w1',
        'date_range': '2025-09-01 to 2025-09-07',
        'checks': {}
    }
    
    completeness_summary = []
    schema_diffs = []
    
    # 1. File Integrity Check
    print("🔍 **1. File Integrity Check**")
    print("-" * 40)
    
    file_checks = {}
    for file_type, filepath in [('ticks', tick_file), ('beacons', beacon_file), ('metadata', metadata_file)]:
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            file_hash = get_file_hash(filepath)
            file_checks[file_type] = {
                'exists': True,
                'size_bytes': file_size,
                'size_mb': file_size / (1024 * 1024),
                'sha256': file_hash,
                'status': 'PASS' if file_size > 0 else 'FAIL'
            }
            print(f"✅ {file_type.upper()}: {file_size:,} bytes, SHA256: {file_hash[:8]}...")
        else:
            file_checks[file_type] = {
                'exists': False,
                'status': 'FAIL'
            }
            print(f"❌ {file_type.upper()}: FILE NOT FOUND")
    
    integrity_report['checks']['file_integrity'] = file_checks
    
    # 2. Load and examine data
    print(f"\n🔍 **2. Data Loading & Schema Analysis**")
    print("-" * 40)
    
    if not os.path.exists(tick_file) or not os.path.exists(beacon_file):
        print("❌ Cannot proceed - required files missing")
        return
    
    # Load data
    ticks_df = pd.read_parquet(tick_file)
    beacons_df = pd.read_parquet(beacon_file)
    
    print(f"📊 Ticks: {len(ticks_df):,} observations")
    print(f"📊 Beacons: {len(beacons_df):,} observations")
    print(f"📊 Tick columns: {ticks_df.columns.tolist()}")
    print(f"📊 Beacon columns: {beacons_df.columns.tolist()}")
    
    # 3. Schema Integrity Check
    print(f"\n🔍 **3. Schema Integrity Check**")
    print("-" * 40)
    
    reference_schema = get_august_reference_schema()
    if reference_schema:
        print(f"📊 Reference schema from: {reference_schema['source_file']}")
        
        # Compare tick schema
        tick_schema_diff = []
        for col in reference_schema['columns']:
            if col not in ticks_df.columns:
                tick_schema_diff.append(f"Missing column: {col}")
            elif str(ticks_df[col].dtype) != reference_schema['dtypes'][col]:
                tick_schema_diff.append(f"Type mismatch {col}: expected {reference_schema['dtypes'][col]}, got {ticks_df[col].dtype}")
        
        for col in ticks_df.columns:
            if col not in reference_schema['columns']:
                tick_schema_diff.append(f"Extra column: {col}")
        
        # Compare beacon schema
        beacon_schema_diff = []
        for col in reference_schema['columns']:
            if col not in beacons_df.columns:
                beacon_schema_diff.append(f"Missing column: {col}")
            elif str(beacons_df[col].dtype) != reference_schema['dtypes'][col]:
                beacon_schema_diff.append(f"Type mismatch {col}: expected {reference_schema['dtypes'][col]}, got {beacons_df[col].dtype}")
        
        for col in beacons_df.columns:
            if col not in reference_schema['columns']:
                beacon_schema_diff.append(f"Extra column: {col}")
        
        schema_diffs.extend(tick_schema_diff)
        schema_diffs.extend(beacon_schema_diff)
        
        if schema_diffs:
            print(f"❌ Schema differences found: {len(schema_diffs)}")
            for diff in schema_diffs:
                print(f"   • {diff}")
        else:
            print(f"✅ No schema differences found")
    else:
        print(f"⚠️ No August reference schema found - skipping schema comparison")
        schema_diffs.append("No reference schema available for comparison")
    
    integrity_report['checks']['schema_integrity'] = {
        'reference_available': reference_schema is not None,
        'tick_differences': len([d for d in schema_diffs if 'tick' in d.lower() or d.startswith('Missing') or d.startswith('Extra')]),
        'beacon_differences': len([d for d in schema_diffs if 'beacon' in d.lower() or d.startswith('Missing') or d.startswith('Extra')]),
        'total_differences': len(schema_diffs),
        'status': 'PASS' if len(schema_diffs) == 0 else 'FAIL'
    }
    
    # 4. Temporal Completeness Check
    print(f"\n🔍 **4. Temporal Completeness Check**")
    print("-" * 40)
    
    # Ensure timestamps are datetime
    ticks_df['event_ts'] = pd.to_datetime(ticks_df['event_ts'], utc=True)
    beacons_df['event_ts'] = pd.to_datetime(beacons_df['event_ts'], utc=True)
    
    # Expected time range
    expected_start = pd.to_datetime("2025-09-01 00:00:00", utc=True)
    expected_end = pd.to_datetime("2025-09-07 23:59:59", utc=True)
    expected_hours = 168  # 7 days * 24 hours
    
    # Check time range
    tick_min_ts = ticks_df['event_ts'].min()
    tick_max_ts = ticks_df['event_ts'].max()
    beacon_min_ts = beacons_df['event_ts'].min()
    beacon_max_ts = beacons_df['event_ts'].max()
    
    print(f"📊 Expected range: {expected_start} → {expected_end}")
    print(f"📊 Tick range: {tick_min_ts} → {tick_max_ts}")
    print(f"📊 Beacon range: {beacon_min_ts} → {beacon_max_ts}")
    
    # Check for gaps > 60 minutes
    tick_gaps = []
    beacon_gaps = []
    
    # Sort by timestamp
    ticks_sorted = ticks_df.sort_values('event_ts')
    beacons_sorted = beacons_df.sort_values('event_ts')
    
    # Check tick gaps
    for i in range(1, len(ticks_sorted)):
        gap_minutes = (ticks_sorted.iloc[i]['event_ts'] - ticks_sorted.iloc[i-1]['event_ts']).total_seconds() / 60
        if gap_minutes > 60:
            tick_gaps.append({
                'gap_minutes': gap_minutes,
                'start_ts': ticks_sorted.iloc[i-1]['event_ts'],
                'end_ts': ticks_sorted.iloc[i]['event_ts']
            })
    
    # Check beacon gaps
    for i in range(1, len(beacons_sorted)):
        gap_minutes = (beacons_sorted.iloc[i]['event_ts'] - beacons_sorted.iloc[i-1]['event_ts']).total_seconds() / 60
        if gap_minutes > 60:
            beacon_gaps.append({
                'gap_minutes': gap_minutes,
                'start_ts': beacons_sorted.iloc[i-1]['event_ts'],
                'end_ts': beacons_sorted.iloc[i]['event_ts']
            })
    
    print(f"📊 Tick gaps > 60 min: {len(tick_gaps)}")
    print(f"📊 Beacon gaps > 60 min: {len(beacon_gaps)}")
    
    integrity_report['checks']['temporal_completeness'] = {
        'expected_hours': expected_hours,
        'tick_gaps_count': len(tick_gaps),
        'beacon_gaps_count': len(beacon_gaps),
        'tick_gaps': tick_gaps,
        'beacon_gaps': beacon_gaps,
        'status': 'PASS' if len(tick_gaps) == 0 and len(beacon_gaps) == 0 else 'FAIL'
    }
    
    # 5. Venue Consistency Check
    print(f"\n🔍 **5. Venue Consistency Check**")
    print("-" * 40)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Create hourly bins
    ticks_df['hour'] = ticks_df['event_ts'].dt.floor('H')
    beacons_df['hour'] = beacons_df['event_ts'].dt.floor('H')
    
    # Get unique hours
    tick_hours = ticks_df['hour'].unique()
    beacon_hours = beacons_df['hour'].unique()
    
    print(f"📊 Unique tick hours: {len(tick_hours)}")
    print(f"📊 Unique beacon hours: {len(beacon_hours)}")
    
    # Check venue presence per hour
    venue_presence = {}
    for venue in venues:
        venue_ticks = ticks_df[ticks_df['venue'] == venue]
        venue_beacons = beacons_df[beacons_df['venue'] == venue]
        
        tick_hours_with_venue = len(venue_ticks['hour'].unique())
        beacon_hours_with_venue = len(venue_beacons['hour'].unique())
        
        tick_presence_pct = (tick_hours_with_venue / len(tick_hours) * 100) if len(tick_hours) > 0 else 0
        beacon_presence_pct = (beacon_hours_with_venue / len(beacon_hours) * 100) if len(beacon_hours) > 0 else 0
        
        venue_presence[venue] = {
            'tick_hours': tick_hours_with_venue,
            'beacon_hours': beacon_hours_with_venue,
            'tick_presence_pct': tick_presence_pct,
            'beacon_presence_pct': beacon_presence_pct,
            'tick_status': 'PASS' if tick_presence_pct >= 95.0 else 'FAIL',
            'beacon_status': 'PASS' if beacon_presence_pct >= 95.0 else 'FAIL'
        }
        
        print(f"📊 {venue}: {tick_hours_with_venue}/{len(tick_hours)} tick hours ({tick_presence_pct:.1f}%), {beacon_hours_with_venue}/{len(beacon_hours)} beacon hours ({beacon_presence_pct:.1f}%)")
    
    integrity_report['checks']['venue_consistency'] = venue_presence
    
    # 6. Statistical Sanity Check
    print(f"\n🔍 **6. Statistical Sanity Check**")
    print("-" * 40)
    
    # Tick counts per hour
    tick_counts_per_hour = ticks_df.groupby('hour').size()
    beacon_counts_per_hour = beacons_df.groupby('hour').size()
    
    tick_mean = tick_counts_per_hour.mean()
    tick_std = tick_counts_per_hour.std()
    tick_outliers = tick_counts_per_hour[tick_counts_per_hour > tick_mean + 3 * tick_std]
    
    beacon_mean = beacon_counts_per_hour.mean()
    beacon_std = beacon_counts_per_hour.std()
    beacon_outliers = beacon_counts_per_hour[beacon_counts_per_hour > beacon_mean + 3 * beacon_std]
    
    print(f"📊 Tick counts per hour: mean={tick_mean:.0f}, std={tick_std:.0f}")
    print(f"📊 Tick outliers > 3σ: {len(tick_outliers)}")
    print(f"📊 Beacon counts per hour: mean={beacon_mean:.0f}, std={beacon_std:.0f}")
    print(f"📊 Beacon outliers > 3σ: {len(beacon_outliers)}")
    
    # Create density plot
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    plt.hist(tick_counts_per_hour, bins=50, alpha=0.7, color='blue')
    plt.title('Tick Counts per Hour Distribution')
    plt.xlabel('Ticks per Hour')
    plt.ylabel('Frequency')
    
    plt.subplot(2, 2, 2)
    plt.hist(beacon_counts_per_hour, bins=50, alpha=0.7, color='green')
    plt.title('Beacon Counts per Hour Distribution')
    plt.xlabel('Beacons per Hour')
    plt.ylabel('Frequency')
    
    plt.subplot(2, 2, 3)
    tick_counts_per_hour.plot(kind='line', alpha=0.7, color='blue')
    plt.title('Tick Counts Over Time')
    plt.xlabel('Hour')
    plt.ylabel('Ticks per Hour')
    plt.xticks(rotation=45)
    
    plt.subplot(2, 2, 4)
    beacon_counts_per_hour.plot(kind='line', alpha=0.7, color='green')
    plt.title('Beacon Counts Over Time')
    plt.xlabel('Hour')
    plt.ylabel('Beacons per Hour')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/sep_w1_density.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Density plot saved: {output_dir}/sep_w1_density.png")
    
    integrity_report['checks']['statistical_sanity'] = {
        'tick_mean': tick_mean,
        'tick_std': tick_std,
        'tick_outliers_count': len(tick_outliers),
        'beacon_mean': beacon_mean,
        'beacon_std': beacon_std,
        'beacon_outliers_count': len(beacon_outliers),
        'status': 'PASS' if len(tick_outliers) == 0 and len(beacon_outliers) == 0 else 'FAIL'
    }
    
    # 7. Cross-file Sync Check
    print(f"\n🔍 **7. Cross-file Sync Check**")
    print("-" * 40)
    
    # Sample beacon timestamps and find nearest tick within ±1 second
    sample_beacons = beacons_df.sample(min(1000, len(beacons_df)))
    alignment_offsets = []
    
    for _, beacon in sample_beacons.iterrows():
        beacon_ts = beacon['event_ts']
        tolerance = pd.Timedelta(seconds=1)
        
        # Find ticks within ±1 second
        nearby_ticks = ticks_df[
            (ticks_df['event_ts'] >= beacon_ts - tolerance) & 
            (ticks_df['event_ts'] <= beacon_ts + tolerance)
        ]
        
        if len(nearby_ticks) > 0:
            # Find closest tick
            closest_tick = nearby_ticks.iloc[(nearby_ticks['event_ts'] - beacon_ts).abs().argsort()[:1]]
            offset_seconds = abs((closest_tick['event_ts'].iloc[0] - beacon_ts).total_seconds())
            alignment_offsets.append(offset_seconds)
    
    mean_alignment = np.mean(alignment_offsets) if alignment_offsets else float('inf')
    max_alignment = np.max(alignment_offsets) if alignment_offsets else float('inf')
    
    print(f"📊 Sampled {len(sample_beacons)} beacons")
    print(f"📊 Mean alignment offset: {mean_alignment:.3f} seconds")
    print(f"📊 Max alignment offset: {max_alignment:.3f} seconds")
    print(f"📊 Alignment status: {'PASS' if mean_alignment <= 1.0 else 'FAIL'}")
    
    integrity_report['checks']['cross_file_sync'] = {
        'samples_checked': len(sample_beacons),
        'mean_alignment_seconds': mean_alignment,
        'max_alignment_seconds': max_alignment,
        'status': 'PASS' if mean_alignment <= 1.0 else 'FAIL'
    }
    
    # Overall status
    all_checks = integrity_report['checks']
    overall_status = 'PASS' if all(
        check.get('status', 'FAIL') == 'PASS' 
        for check in all_checks.values()
    ) else 'FAIL'
    
    integrity_report['overall_status'] = overall_status
    
    # Save results
    with open(f'{output_dir}/sep_w1_integrity_report.json', 'w') as f:
        json.dump(integrity_report, f, indent=2, default=str)
    
    # Create completeness summary
    completeness_data = []
    for venue in venues:
        venue_data = venue_presence[venue]
        completeness_data.append({
            'venue': venue,
            'tick_hours': venue_data['tick_hours'],
            'beacon_hours': venue_data['beacon_hours'],
            'tick_presence_pct': venue_data['tick_presence_pct'],
            'beacon_presence_pct': venue_data['beacon_presence_pct'],
            'tick_status': venue_data['tick_status'],
            'beacon_status': venue_data['beacon_status']
        })
    
    completeness_df = pd.DataFrame(completeness_data)
    completeness_df.to_csv(f'{output_dir}/sep_w1_completeness_summary.csv', index=False)
    
    # Save schema differences
    with open(f'{output_dir}/sep_w1_schema_diff.log', 'w') as f:
        f.write("SEPTEMBER WEEK 1 SCHEMA DIFFERENCES\n")
        f.write("=" * 50 + "\n")
        f.write(f"Verification timestamp: {datetime.now().isoformat()}\n\n")
        if schema_diffs:
            for diff in schema_diffs:
                f.write(f"• {diff}\n")
        else:
            f.write("No schema differences found.\n")
    
    # Print summary
    print(f"\n" + "=" * 80)
    print(f"📦 **VERIFICATION SUMMARY**")
    print(f"=" * 80)
    
    print(f"\n📊 **Overall Status: {overall_status}**")
    print(f"\n📊 **Check Results:**")
    for check_name, check_data in all_checks.items():
        status = check_data.get('status', 'UNKNOWN')
        print(f"  • {check_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n📁 **Outputs Created:**")
    print(f"📁 {output_dir}/sep_w1_integrity_report.json")
    print(f"📁 {output_dir}/sep_w1_completeness_summary.csv")
    print(f"📁 {output_dir}/sep_w1_schema_diff.log")
    print(f"📁 {output_dir}/sep_w1_density.png")
    
    print(f"\n🔒 **Pass Criteria Status:**")
    print(f"  • Schema differences: {len(schema_diffs)} (target: 0)")
    print(f"  • Timestamp gaps > 60 min: {len(tick_gaps) + len(beacon_gaps)} (target: 0)")
    print(f"  • Venue presence ≥95%: {sum(1 for v in venue_presence.values() if v['tick_presence_pct'] >= 95.0)}/4 venues")
    print(f"  • Mean beacon alignment: {mean_alignment:.3f}s (target: ≤1.0s)")
    
    return integrity_report, completeness_df

if __name__ == '__main__':
    verify_sep_w1_integrity()




