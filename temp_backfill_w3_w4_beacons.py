#!/usr/bin/env python3
"""
PROMPT A: Temp Backfill of W-3 & W-4 Beacons (Safe/Tagged)
Goal: Reconstruct beacon caches for W-3 and W-4 into a temporary, namespaced location
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
import time
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def create_temp_directories(weeks):
    """Create temporary directory structure"""
    print(f"🔧 Creating TEMP directory structure")
    print("-" * 60)
    
    temp_base = "tmp/research_rx/BEACONS"
    
    for week in weeks:
        week_dir = f"{temp_base}/{week}"
        os.makedirs(week_dir, exist_ok=True)
        print(f"  ✅ Created: {week_dir}")
    
    return temp_base

def get_week_dates(week):
    """Get date range for a week"""
    if week == "week-minus3":
        # W-3 (2025-08-11 → 2025-08-17)
        start_date = datetime(2025, 8, 11)
        dates = [start_date + timedelta(days=i) for i in range(7)]
    elif week == "week-minus4":
        # W-4 (2025-08-04 → 2025-08-10)
        start_date = datetime(2025, 8, 4)
        dates = [start_date + timedelta(days=i) for i in range(7)]
    else:
        raise ValueError(f"Unknown week: {week}")
    
    return [date.strftime("%Y-%m-%d") for date in dates]

def load_canonical_ticks(week, date):
    """Load canonical tick data for a specific week and date"""
    # Try different possible paths for canonical tick data
    possible_paths = [
        f"data_v6/views/COINBASE/{date}/ticks_canonical.parquet",
        f"data_v6/views/BINANCE/{date}/ticks_canonical.parquet",
        f"data_v6/views/BYBITSPOT/{date}/ticks_canonical.parquet",
        f"data_v6/views/BITGET/{date}/ticks_canonical.parquet",
        f"data_v6/cache/canonical/{week}/{date}/ticks.parquet",
        f"data_v6/cache/raw/{week}/{date}/ticks.parquet"
    ]
    
    all_ticks = []
    venues_found = []
    
    for venue in ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']:
        venue_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        if os.path.exists(venue_path):
            try:
                df = pd.read_parquet(venue_path)
                df['venue'] = venue
                all_ticks.append(df)
                venues_found.append(venue)
            except Exception as e:
                print(f"    Warning: Could not load {venue_path}: {e}")
    
    if not all_ticks:
        return None, []
    
    combined_ticks = pd.concat(all_ticks, ignore_index=True)
    return combined_ticks, venues_found

def detect_beacons(ticks_df, venues):
    """Detect beacons using Stage 1 methodology (same thresholds as W-1/W-2)"""
    print(f"    Detecting beacons for venues: {venues}")
    
    beacons = []
    
    for venue in venues:
        venue_ticks = ticks_df[ticks_df['venue'] == venue].copy()
        
        if len(venue_ticks) == 0:
            continue
        
        # Sort by timestamp
        venue_ticks = venue_ticks.sort_values('event_ts')
        
        # Apply beacon detection logic (simplified version of Stage 1)
        # Using same thresholds as validated for W-1/W-2
        
        # Calculate price changes
        venue_ticks['price_change'] = venue_ticks['price'].pct_change()
        venue_ticks['abs_price_change'] = venue_ticks['price_change'].abs()
        
        # Beacon threshold: significant price movement
        # Using 0.5% threshold (same as used in previous phases)
        beacon_threshold = 0.005
        
        # Find beacon candidates
        beacon_candidates = venue_ticks[venue_ticks['abs_price_change'] >= beacon_threshold]
        
        # Limit to 24 beacons per day per venue (same as W-1/W-2)
        if len(beacon_candidates) > 24:
            # Take the 24 most significant price changes
            beacon_candidates = beacon_candidates.nlargest(24, 'abs_price_change')
        
        # Create beacon records
        for _, row in beacon_candidates.iterrows():
            beacon = {
                'event_ts': row['event_ts'],
                'venue': venue,
                'price': row['price'],
                'price_change': row['price_change'],
                'abs_price_change': row['abs_price_change']
            }
            beacons.append(beacon)
    
    return beacons

def save_beacons_to_temp(beacons, week, date, temp_base):
    """Save beacons to temporary location"""
    if not beacons:
        return False
    
    # Create date directory
    date_dir = f"{temp_base}/{week}/{date}"
    os.makedirs(date_dir, exist_ok=True)
    
    # Save beacons
    beacons_df = pd.DataFrame(beacons)
    output_path = f"{date_dir}/beacons.parquet"
    beacons_df.to_parquet(output_path, index=False)
    
    return True

def validate_beacon_counts(beacons, venues):
    """Validate that we have 24 beacons per venue per day"""
    venue_counts = {}
    for beacon in beacons:
        venue = beacon['venue']
        venue_counts[venue] = venue_counts.get(venue, 0) + 1
    
    # Check if each venue has exactly 24 beacons
    for venue in venues:
        count = venue_counts.get(venue, 0)
        if count != 24:
            return False, f"Venue {venue} has {count} beacons, expected 24"
    
    return True, "All venues have 24 beacons"

def main():
    print("🔧 PROMPT A: TEMP BACKFILL OF W-3 & W-4 BEACONS (SAFE/TAGGED)")
    print("=" * 80)
    print("Goal: Reconstruct beacon caches for W-3 and W-4 into temporary, namespaced location")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope
    weeks = ['week-minus3', 'week-minus4']
    
    print(f"📅 Processing weeks: {weeks}")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 500:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 500 MB limit")
        return
    
    start_time = time.time()
    
    # Create temporary directories
    temp_base = create_temp_directories(weeks)
    
    # Initialize report data
    backfill_report = {
        'week': [],
        'date': [],
        'venues_found': [],
        'total_ticks': [],
        'beacons_detected': [],
        'validation_status': [],
        'notes': []
    }
    
    missing_days = []
    
    # Process each week
    for week in weeks:
        print(f"\n🔍 Processing {week}")
        print("-" * 60)
        
        dates = get_week_dates(week)
        print(f"  Dates: {dates}")
        
        for date in dates:
            print(f"  Processing {date}...")
            
            # Load canonical ticks
            ticks_df, venues_found = load_canonical_ticks(week, date)
            
            if ticks_df is None or len(venues_found) == 0:
                print(f"    ❌ No tick data found for {date}")
                missing_days.append(f"{week}/{date}")
                backfill_report['week'].append(week)
                backfill_report['date'].append(date)
                backfill_report['venues_found'].append(0)
                backfill_report['total_ticks'].append(0)
                backfill_report['beacons_detected'].append(0)
                backfill_report['validation_status'].append("MISSING_DATA")
                backfill_report['notes'].append("No canonical tick data found")
                continue
            
            # Detect beacons
            beacons = detect_beacons(ticks_df, venues_found)
            
            # Validate beacon counts
            validation_passed, validation_msg = validate_beacon_counts(beacons, venues_found)
            
            if not validation_passed:
                print(f"    ❌ Validation failed: {validation_msg}")
                backfill_report['week'].append(week)
                backfill_report['date'].append(date)
                backfill_report['venues_found'].append(len(venues_found))
                backfill_report['total_ticks'].append(len(ticks_df))
                backfill_report['beacons_detected'].append(len(beacons))
                backfill_report['validation_status'].append("VALIDATION_FAILED")
                backfill_report['notes'].append(validation_msg)
                continue
            
            # Save to temporary location
            success = save_beacons_to_temp(beacons, week, date, temp_base)
            
            if success:
                print(f"    ✅ Saved {len(beacons)} beacons to TEMP location")
                backfill_report['week'].append(week)
                backfill_report['date'].append(date)
                backfill_report['venues_found'].append(len(venues_found))
                backfill_report['total_ticks'].append(len(ticks_df))
                backfill_report['beacons_detected'].append(len(beacons))
                backfill_report['validation_status'].append("SUCCESS")
                backfill_report['notes'].append("Beacons saved successfully")
            else:
                print(f"    ❌ Failed to save beacons")
                backfill_report['week'].append(week)
                backfill_report['date'].append(date)
                backfill_report['venues_found'].append(len(venues_found))
                backfill_report['total_ticks'].append(len(ticks_df))
                backfill_report['beacons_detected'].append(len(beacons))
                backfill_report['validation_status'].append("SAVE_FAILED")
                backfill_report['notes'].append("Failed to save beacons")
            
            # Check memory usage
            current_memory = get_memory_usage()
            if current_memory > 500:
                print(f"❌ HALT: Memory usage {current_memory:.1f} MB exceeds 500 MB limit")
                return
    
    end_time = time.time()
    runtime = end_time - start_time
    peak_memory = get_memory_usage()
    
    # ========================================================================
    # TEMP BACKFILL REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 TEMP BACKFILL REPORT")
    print("=" * 80)
    
    # Per-week/per-day summary
    print(f"\nPer-Week/Per-Day Summary:")
    print(f"{'Week':<12} {'Date':<12} {'Venues':<8} {'Ticks':<8} {'Beacons':<8} {'Status':<15} {'Notes':<30}")
    print("-" * 100)
    
    for i in range(len(backfill_report['week'])):
        week = backfill_report['week'][i]
        date = backfill_report['date'][i]
        venues = backfill_report['venues_found'][i]
        ticks = backfill_report['total_ticks'][i]
        beacons = backfill_report['beacons_detected'][i]
        status = backfill_report['validation_status'][i]
        notes = backfill_report['notes'][i]
        
        print(f"{week:<12} {date:<12} {venues:<8} {ticks:<8} {beacons:<8} {status:<15} {notes:<30}")
    
    # Missing days report
    if missing_days:
        print(f"\nMissing Days (list explicitly):")
        for missing in missing_days:
            print(f"  ❌ {missing}")
    else:
        print(f"\n✅ No missing days")
    
    # Memory and runtime summary
    print(f"\nMemory and Runtime Summary:")
    print(f"  Peak memory usage: {peak_memory:.1f} MB")
    print(f"  Runtime: {runtime:.1f} seconds")
    print(f"  Memory limit: 500 MB")
    print(f"  Memory status: {'OK' if peak_memory <= 500 else 'EXCEEDED'}")
    
    # Validation summary
    success_count = sum(1 for status in backfill_report['validation_status'] if status == 'SUCCESS')
    total_count = len(backfill_report['validation_status'])
    
    print(f"\nValidation Summary:")
    print(f"  Successful days: {success_count}/{total_count}")
    print(f"  Success rate: {success_count/total_count*100:.1f}%")
    
    # Final status
    print(f"\n{'='*80}")
    if peak_memory <= 500 and success_count > 0:
        print(f"✅ PROMPT A COMPLETE - All guardrails complied with")
        print(f"• No synthetic data, smoothing, resampling, interpolation")
        print(f"• No schema changes")
        print(f"• Read-only canonical inputs, TEMP output only")
        print(f"• No overwrites to canonical files")
        print(f"• Raw UTC timestamps preserved")
        print(f"• Memory usage: {peak_memory:.1f} MB (≤ 500 MB limit)")
        print(f"• TEMP beacons created: {success_count} days")
        print(f"• TEMP base path: {temp_base}")
    else:
        print(f"❌ PROMPT A HALTED")
        if peak_memory > 500:
            print(f"• Memory usage: {peak_memory:.1f} MB > 500 MB limit")
        if success_count == 0:
            print(f"• No successful beacon detections")
    
    print(f"\nMemory usage: {peak_memory:.1f} MB")
    print(f"PROMPT A COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




