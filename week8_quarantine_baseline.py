#!/usr/bin/env python3
"""
Week-8 Quarantine & Baseline Finalization Plan
Safely isolate corrupted Week-8 data and finalize a verified baseline through Week-7
"""

import os
import pandas as pd
import json
import hashlib
import subprocess
import shutil
from datetime import datetime, timedelta
import glob
import numpy as np

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file."""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def quarantine_week8_data():
    """Quarantine Week-8 artifacts to quarantine directory."""
    print('🔍 **Week-8 Quarantine & Baseline Finalization**')
    print('=' * 60)
    
    # Create quarantine directory
    quarantine_dir = 'analysis/flatfiles_1s_v4/quarantine/week_20250919'
    os.makedirs(quarantine_dir, exist_ok=True)
    
    # Week-8 dates
    week8_dates = ['20250919', '20250920', '20250921', '20250922', '20250923', '20250924', '20250925']
    
    print(f'📊 **Quarantining Week-8 data:**')
    print(f'📊 Dates: {week8_dates}')
    
    # Move Week-8 partitioned data to quarantine
    partitioned_dir = 'analysis/flatfiles_1s_v4/partitioned'
    quarantined_slices = []
    
    for date in week8_dates:
        date_dir = f'{partitioned_dir}/dt={date[:4]}-{date[4:6]}-{date[6:8]}'
        if os.path.exists(date_dir):
            # Move entire date directory to quarantine
            quarantine_date_dir = f'{quarantine_dir}/dt={date[:4]}-{date[4:6]}-{date[6:8]}'
            shutil.move(date_dir, quarantine_date_dir)
            quarantined_slices.append(date)
            print(f'📊 Quarantined: {date}')
    
    print(f'📊 Quarantined {len(quarantined_slices)} date directories')
    
    return quarantined_slices

def clean_manifest():
    """Remove Week-8 entries from live manifest and create clean manifest."""
    print(f'\n📊 **Cleaning manifest:**')
    
    manifest_path = 'analysis/flatfiles_1s_v4/partitioned/manifest.jsonl'
    clean_manifest_path = 'analysis/flatfiles_1s_v4/panel/_v4_manifest_final.jsonl'
    
    # Week-8 dates to exclude
    week8_dates = ['20250919', '20250920', '20250921', '20250922', '20250923', '20250924', '20250925']
    
    clean_entries = []
    excluded_entries = []
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('date') in week8_dates:
                        excluded_entries.append(entry)
                    else:
                        clean_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    
    # Write clean manifest
    os.makedirs('analysis/flatfiles_1s_v4/panel', exist_ok=True)
    with open(clean_manifest_path, 'w') as f:
        for entry in clean_entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f'📊 Clean manifest: {len(clean_entries)} entries')
    print(f'📊 Excluded: {len(excluded_entries)} Week-8 entries')
    
    return clean_entries, excluded_entries

def create_baseline_panel(clean_entries):
    """Create consolidated baseline panel from Weeks 1-7."""
    print(f'\n📊 **Creating baseline panel:**')
    
    # Load all clean partitions
    all_data = []
    
    for entry in clean_entries:
        if os.path.exists(entry['path']):
            try:
                df = pd.read_parquet(entry['path'])
                df['date'] = entry['date']
                df['venue'] = entry['venue']
                all_data.append(df)
                print(f'📊 Loaded: {entry["date"]} {entry["venue"]} ({len(df)} rows)')
            except Exception as e:
                print(f'❌ Failed to load {entry["path"]}: {e}')
    
    if not all_data:
        print(f'❌ No data loaded for baseline panel')
        return None
    
    # Combine all data
    baseline_panel = pd.concat(all_data, ignore_index=True)
    
    # Sort by date, venue, timestamp
    baseline_panel = baseline_panel.sort_values(['date', 'venue', 't1s'])
    
    # Save baseline panel
    baseline_path = 'analysis/flatfiles_1s_v4/panel/candles_1s_panel_v4_baseline.parquet'
    baseline_panel.to_parquet(baseline_path, compression='zstd')
    
    # Compute hash
    baseline_hash = compute_file_hash(baseline_path)
    
    print(f'📊 Baseline panel: {len(baseline_panel)} rows, {len(baseline_panel.columns)} columns')
    print(f'📊 Baseline hash: {baseline_hash}')
    
    return baseline_panel, baseline_hash

def validate_cross_venue_alignment(baseline_panel):
    """Validate cross-venue alignment for random days."""
    print(f'\n📊 **Validating cross-venue alignment:**')
    
    # Get unique dates
    unique_dates = baseline_panel['date'].unique()
    
    # Sample random days (one per week)
    sample_dates = []
    for week in range(1, 8):  # Weeks 1-7
        week_dates = [d for d in unique_dates if d.startswith('202508') and int(d[6:8]) >= (week-1)*7 + 1 and int(d[6:8]) <= week*7]
        if week_dates:
            sample_dates.append(week_dates[0])  # Take first date of each week
    
    print(f'📊 Sample dates: {sample_dates}')
    
    correlations_summary = {}
    
    for sample_date in sample_dates:
        print(f'\n📊 **Cross-venue alignment check for {sample_date}:**')
        
        # Filter data for this date
        date_data = baseline_panel[baseline_panel['date'] == sample_date].copy()
        
        if len(date_data) == 0:
            print(f'❌ No data for {sample_date}')
            continue
        
        # Pivot to get venue columns
        date_data['t1s'] = pd.to_datetime(date_data['t1s'])
        date_data = date_data.set_index(['t1s', 'venue'])['close'].unstack()
        
        # Remove any venues with all NaN
        date_data = date_data.dropna(axis=1, how='all')
        
        if len(date_data.columns) < 2:
            print(f'❌ Insufficient venues for {sample_date}')
            continue
        
        # Compute correlations
        correlations = date_data.corr()
        
        # Check if all correlations >= 0.995
        all_good = True
        for i, venue1 in enumerate(correlations.columns):
            for j, venue2 in enumerate(correlations.columns):
                if i < j:  # Only upper triangle
                    corr = correlations.loc[venue1, venue2]
                    print(f'📊 {venue1} ↔ {venue2}: {corr:.6f}')
                    if corr < 0.995:
                        print(f'⚠️  LOW CORRELATION: {venue1} ↔ {venue2} = {corr:.6f} < 0.995')
                        all_good = False
        
        correlations_summary[sample_date] = {
            'correlations': correlations.to_dict(),
            'all_good': all_good
        }
    
    return correlations_summary

def validate_price_ranges(baseline_panel):
    """Validate price ranges are within [100K, 130K]."""
    print(f'\n📊 **Validating price ranges:**')
    
    # Get price statistics
    price_stats = baseline_panel['close'].describe()
    min_price = price_stats['min']
    max_price = price_stats['max']
    
    print(f'📊 Price range: ${min_price:,.0f} - ${max_price:,.0f}')
    
    # Check if within bounds
    within_bounds = 100000 <= min_price <= max_price <= 130000
    
    if within_bounds:
        print(f'✅ Price range within bounds [100K, 130K]')
    else:
        print(f'❌ Price range outside bounds [100K, 130K]')
    
    return within_bounds, min_price, max_price

def process_quarantine_baseline():
    """Main process for quarantine and baseline finalization."""
    print('🔍 **Week-8 Quarantine & Baseline Finalization**')
    print('=' * 60)
    
    # Step 1: Quarantine Week-8 data
    quarantined_slices = quarantine_week8_data()
    
    # Step 2: Clean manifest
    clean_entries, excluded_entries = clean_manifest()
    
    # Step 3: Create baseline panel
    baseline_panel, baseline_hash = create_baseline_panel(clean_entries)
    
    if baseline_panel is None:
        print(f'❌ Failed to create baseline panel')
        return
    
    # Step 4: Validate cross-venue alignment
    correlations_summary = validate_cross_venue_alignment(baseline_panel)
    
    # Step 5: Validate price ranges
    within_bounds, min_price, max_price = validate_price_ranges(baseline_panel)
    
    # Step 6: Create QC results
    qc_results = {
        'timestamp': datetime.now().isoformat(),
        'baseline_weeks': 'Weeks 1-7 (2025-08-01 → 2025-09-18)',
        'quarantined_weeks': 'Week 8 (2025-09-19 → 2025-09-25)',
        'total_rows': len(baseline_panel),
        'total_columns': len(baseline_panel.columns),
        'baseline_hash': baseline_hash,
        'quarantined_slices': quarantined_slices,
        'clean_entries': len(clean_entries),
        'excluded_entries': len(excluded_entries),
        'correlations_summary': correlations_summary,
        'price_range_valid': within_bounds,
        'min_price': float(min_price),
        'max_price': float(max_price),
        'status': 'SUCCESS' if within_bounds else 'FAILED'
    }
    
    # Save QC results
    with open('analysis/outputs_v4/qc_baseline_final.json', 'w') as f:
        json.dump(qc_results, f, indent=2, default=str)
    
    print(f'\n📊 QC results saved to: analysis/outputs_v4/qc_baseline_final.json')
    
    # Update progress log
    progress_log_path = 'analysis/outputs_v4/README_v4_progress.md'
    with open(progress_log_path, 'a') as f:
        f.write(f'- Baseline Finalization: Weeks 1-7 (2025-08-01 → 2025-09-18) - {len(baseline_panel)} rows, {len(baseline_panel.columns)} columns\n')
        f.write(f'- Week-8 Quarantine: {len(quarantined_slices)} slices quarantined due to data corruption\n')
    
    # Git commit if all validations pass
    if within_bounds:
        try:
            # Add files
            subprocess.run(['git', 'add', 'week8_quarantine_baseline.py'], check=True)
            
            # Commit
            commit_result = subprocess.run(['git', 'commit', '-m', 'panel_v4: finalized baseline through Week-7; quarantined Week-8 due to source data corruption'], 
                                         capture_output=True, text=True, check=True)
            
            commit_hash = commit_result.stdout.split()[-1]
            print(f'\n📊 **Git commit successful:** {commit_hash}')
            
        except subprocess.CalledProcessError as e:
            print(f'\n❌ **Git commit failed:** {e.stderr}')
            print(f'📊 Manual intervention required')
    
    # Print final summary
    print(f'\n📊 **Baseline Finalization Summary:**')
    print(f'📊 Weeks included: 1-7 (2025-08-01 → 2025-09-18)')
    print(f'📊 Total rows: {len(baseline_panel):,}')
    print(f'📊 Total columns: {len(baseline_panel.columns)}')
    print(f'📊 Baseline hash: {baseline_hash}')
    print(f'📊 Price range: ${min_price:,.0f} - ${max_price:,.0f}')
    print(f'📊 Cross-venue correlations: {"✅ All ≥ 0.995" if all(corr["all_good"] for corr in correlations_summary.values()) else "❌ Some < 0.995"}')
    print(f'📊 Quarantined Week-8 slices: {len(quarantined_slices)}')
    
    print(f'\n🛑 **STOP — Baseline finalization complete, awaiting review**')

if __name__ == '__main__':
    process_quarantine_baseline()





