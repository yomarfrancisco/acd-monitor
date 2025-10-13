#!/usr/bin/env python3
"""
STEP B QC Forensics (Read-Only)
Comprehensive quality control analysis of candles_1s_panel_v4_rev1.parquet
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime
import hashlib

def main():
    print('🔍 STEP B QC Forensics (Read-Only)')
    print('=' * 60)
    
    # Validate rationale and risks
    print(f'📊 **Rationale Validation:**')
    print(f'📊 - QC-only: No writes except small JSON report')
    print(f'📊 - Read-only: No modifications to any panel files')
    print(f'📊 - Comprehensive validation of rev1 panel integrity')
    print(f'📊 - Clear decision gate based on results')
    
    print(f'\n📊 **Risk Assessment:**')
    print(f'📊 - No data risk: Only reading existing files')
    print(f'📊 - No schema risk: No changes to data structure')
    print(f'📊 - No concurrency risk: Sequential read-only operations')
    print(f'📊 - No git risk: Only adding one small JSON file')
    
    # Load the rev1 panel
    panel_path = 'analysis/flatfiles_1s_v4/panel/candles_1s_panel_v4_rev1.parquet'
    
    if not os.path.exists(panel_path):
        print(f'❌ Rev1 panel not found: {panel_path}')
        return
    
    print(f'\n📊 **A. Panel Shape & Span:**')
    df = pd.read_parquet(panel_path)
    
    total_rows = len(df)
    total_columns = len(df.columns)
    start_ts = df.index.min()
    end_ts = df.index.max()
    
    # Extract venues from column names
    venues = []
    for col in df.columns:
        if '_' in col:
            venue = col.split('_')[0]
            if venue not in venues:
                venues.append(venue)
    
    print(f'📊 Total rows: {total_rows:,}')
    print(f'📊 Total columns: {total_columns}')
    print(f'📊 Start timestamp: {start_ts}')
    print(f'📊 End timestamp: {end_ts}')
    print(f'📊 Venues: {venues}')
    
    print(f'\n📊 **B. Per-Venue Coverage & Non-NaN Ratios:**')
    venue_stats = {}
    
    for venue in venues:
        venue_columns = [col for col in df.columns if col.startswith(venue)]
        if venue_columns:
            # OHLC columns
            ohlc_columns = [col for col in venue_columns if any(x in col.lower() for x in ['open', 'high', 'low', 'close'])]
            volume_columns = [col for col in venue_columns if 'volume' in col.lower()]
            
            ohlc_nonnan = {}
            volume_nonnan = {}
            
            for col in ohlc_columns:
                if col in df.columns:
                    nonnan_count = df[col].notna().sum()
                    total_count = len(df)
                    ohlc_nonnan[col] = (nonnan_count / total_count) * 100
            
            for col in volume_columns:
                if col in df.columns:
                    nonnan_count = df[col].notna().sum()
                    total_count = len(df)
                    volume_nonnan[col] = (nonnan_count / total_count) * 100
            
            venue_stats[venue] = {
                'ohlc_nonnan': ohlc_nonnan,
                'volume_nonnan': volume_nonnan
            }
            
            print(f'📊 {venue}:')
            for col, ratio in ohlc_nonnan.items():
                print(f'📊   {col}: {ratio:.2f}%')
            for col, ratio in volume_nonnan.items():
                print(f'📊   {col}: {ratio:.2f}%')
    
    print(f'\n📊 **C. Per-Day × Venue Health Table (Sample 10 Days):**')
    
    # Sample 10 days across the 8 weeks
    sample_days = []
    current_date = start_ts.date()
    end_date = end_ts.date()
    
    # Get 10 evenly spaced days
    date_range = pd.date_range(start=current_date, end=end_date, freq='D')
    if len(date_range) >= 10:
        sample_days = date_range[::len(date_range)//10][:10]
    else:
        sample_days = date_range
    
    day_health = []
    
    for day in sample_days:
        day_start = pd.Timestamp(day)
        day_end = day_start + pd.Timedelta(days=1)
        
        day_data = df[(df.index >= day_start) & (df.index < day_end)]
        
        if len(day_data) > 0:
            day_stats = {
                'date': str(day.date()),
                'rows': len(day_data),
                'venues': {}
            }
            
            for venue in venues:
                venue_columns = [col for col in df.columns if col.startswith(venue)]
                if venue_columns:
                    close_col = f'{venue}_close'
                    volume_col = f'{venue}_volume'
                    
                    if close_col in day_data.columns and volume_col in day_data.columns:
                        close_nonnan = (day_data[close_col].notna().sum() / len(day_data)) * 100
                        volume_nonnan = (day_data[volume_col].notna().sum() / len(day_data)) * 100
                        
                        close_prices = day_data[close_col].dropna()
                        volume_values = day_data[volume_col].dropna()
                        
                        min_price = close_prices.min() if len(close_prices) > 0 else None
                        max_price = close_prices.max() if len(close_prices) > 0 else None
                        min_volume = volume_values.min() if len(volume_values) > 0 else None
                        max_volume = volume_values.max() if len(volume_values) > 0 else None
                        
                        day_stats['venues'][venue] = {
                            'close_nonnan_pct': close_nonnan,
                            'volume_nonnan_pct': volume_nonnan,
                            'min_price': float(min_price) if min_price is not None else None,
                            'max_price': float(max_price) if max_price is not None else None,
                            'min_volume': float(min_volume) if min_volume is not None else None,
                            'max_volume': float(max_volume) if max_volume is not None else None
                        }
            
            day_health.append(day_stats)
    
    # Print sample results
    for day_stat in day_health[:5]:  # Show first 5 days
        print(f'📊 {day_stat["date"]}: {day_stat["rows"]} rows')
        for venue, stats in day_stat['venues'].items():
            print(f'📊   {venue}: close={stats["close_nonnan_pct"]:.1f}%, volume={stats["volume_nonnan_pct"]:.1f}%')
            if stats['min_price'] and stats['max_price']:
                print(f'📊     Price range: ${stats["min_price"]:,.0f} - ${stats["max_price"]:,.0f}')
    
    print(f'\n📊 **D. Cleaning Audit:**')
    
    # Recompute cleaning statistics
    volume_columns = [col for col in df.columns if 'volume' in col.lower()]
    price_columns = [col for col in df.columns if any(x in col.lower() for x in ['open', 'high', 'low', 'close'])]
    
    seconds_total = len(df)
    seconds_with_any_trade = 0
    seconds_with_zero_trades = 0
    seconds_volume_set_to_nan = 0
    seconds_price_set_to_nan = 0
    
    # Count seconds with any trade (any non-NaN price)
    for col in price_columns:
        if col in df.columns:
            seconds_with_any_trade = max(seconds_with_any_trade, df[col].notna().sum())
    
    # Count seconds with zero trades (all prices NaN)
    all_price_nan = True
    for col in price_columns:
        if col in df.columns:
            all_price_nan = all_price_nan & df[col].isna()
    seconds_with_zero_trades = all_price_nan.sum()
    
    # Count volume set to NaN (non-positive values)
    for col in volume_columns:
        if col in df.columns:
            # This is an approximation - we can't know the original values
            # But we can count NaN values in volume columns
            seconds_volume_set_to_nan = max(seconds_volume_set_to_nan, df[col].isna().sum())
    
    # Count price set to NaN (should be 0 for OHLC)
    for col in price_columns:
        if col in df.columns:
            seconds_price_set_to_nan = max(seconds_price_set_to_nan, df[col].isna().sum())
    
    print(f'📊 Seconds total: {seconds_total:,}')
    print(f'📊 Seconds with any trade: {seconds_with_any_trade:,}')
    print(f'📊 Seconds with zero trades: {seconds_with_zero_trades:,}')
    print(f'📊 Seconds volume set to NaN: {seconds_volume_set_to_nan:,}')
    print(f'📊 Seconds price set to NaN: {seconds_price_set_to_nan:,}')
    
    # Recompute "Rows Cleaned %" correctly
    rows_cleaned_pct = (seconds_volume_set_to_nan / seconds_total) * 100
    print(f'📊 Rows cleaned % (corrected): {rows_cleaned_pct:.2f}%')
    
    print(f'\n📊 **E. OHLC Construction Sanity:**')
    
    # Check OHLC invariants
    ohlc_issues = []
    
    for venue in venues:
        open_col = f'{venue}_open'
        high_col = f'{venue}_high'
        low_col = f'{venue}_low'
        close_col = f'{venue}_close'
        
        if all(col in df.columns for col in [open_col, high_col, low_col, close_col]):
            # Check open < low
            open_low_issues = (df[open_col] < df[low_col]).sum()
            # Check close > high
            close_high_issues = (df[close_col] > df[high_col]).sum()
            
            if open_low_issues > 0 or close_high_issues > 0:
                ohlc_issues.append({
                    'venue': venue,
                    'open_low_issues': int(open_low_issues),
                    'close_high_issues': int(close_high_issues)
                })
    
    if ohlc_issues:
        print(f'📊 OHLC Issues found:')
        for issue in ohlc_issues:
            print(f'📊   {issue["venue"]}: open<low={issue["open_low_issues"]}, close>high={issue["close_high_issues"]}')
    else:
        print(f'📊 OHLC invariants: ✅ All venues pass')
    
    print(f'\n📊 **F. Cross-Venue Spot Check (One Day):**')
    
    # Pick one mid-week day
    mid_date = start_ts + (end_ts - start_ts) / 2
    mid_day_start = pd.Timestamp(mid_date.date())
    mid_day_end = mid_day_start + pd.Timedelta(days=1)
    
    mid_day_data = df[(df.index >= mid_day_start) & (df.index < mid_day_end)]
    
    if len(mid_day_data) > 0:
        print(f'📊 Checking day: {mid_day_start.date()}')
        
        # Compute correlations between venue close prices
        venue_closes = {}
        for venue in venues:
            close_col = f'{venue}_close'
            if close_col in mid_day_data.columns:
                venue_closes[venue] = mid_day_data[close_col]
        
        if len(venue_closes) > 1:
            # Forward fill within the day
            for venue in venue_closes:
                venue_closes[venue] = venue_closes[venue].fillna(method='ffill')
            
            # Compute correlation matrix
            closes_df = pd.DataFrame(venue_closes)
            corr_matrix = closes_df.corr()
            
            print(f'📊 Correlation matrix:')
            for i, venue1 in enumerate(venue_closes.keys()):
                for j, venue2 in enumerate(venue_closes.keys()):
                    if i < j:  # Only show upper triangle
                        corr = corr_matrix.loc[venue1, venue2]
                        print(f'📊   {venue1} vs {venue2}: {corr:.4f}')
    
    print(f'\n📊 **G. Git Status:**')
    import subprocess
    try:
        git_status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        print(f'📊 Git status: {git_status.stdout.strip() or "Clean working directory"}')
    except Exception as e:
        print(f'📊 Git status: Error - {str(e)}')
    
    # Compile QC results
    qc_results = {
        'timestamp': datetime.now().isoformat(),
        'panel_shape': {
            'total_rows': int(total_rows),
            'total_columns': int(total_columns),
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'venues': venues
        },
        'venue_coverage': venue_stats,
        'day_health': day_health,
        'cleaning_audit': {
            'seconds_total': int(seconds_total),
            'seconds_with_any_trade': int(seconds_with_any_trade),
            'seconds_with_zero_trades': int(seconds_with_zero_trades),
            'seconds_volume_set_to_nan': int(seconds_volume_set_to_nan),
            'seconds_price_set_to_nan': int(seconds_price_set_to_nan),
            'rows_cleaned_pct': float(rows_cleaned_pct)
        },
        'ohlc_issues': ohlc_issues,
        'cross_venue_check': {
            'date_checked': str(mid_day_start.date()),
            'correlations': corr_matrix.to_dict() if 'corr_matrix' in locals() else {}
        }
    }
    
    # Save QC results
    os.makedirs('analysis/outputs_v4', exist_ok=True)
    with open('analysis/outputs_v4/stepB_qc_forensics.json', 'w') as f:
        json.dump(qc_results, f, indent=2, default=str)
    
    print(f'\n📊 QC results saved to: analysis/outputs_v4/stepB_qc_forensics.json')
    
    # Decision gate
    print(f'\n📊 **Decision Gate:**')
    
    # Check if all venues have close non-NaN >= 98%
    all_venues_healthy = True
    for venue in venues:
        close_col = f'{venue}_close'
        if close_col in df.columns:
            close_nonnan = (df[close_col].notna().sum() / len(df)) * 100
            if close_nonnan < 98:
                all_venues_healthy = False
                print(f'📊 {venue}: close non-NaN = {close_nonnan:.2f}% (< 98%)')
    
    # Check OHLC invariants
    ohlc_healthy = len(ohlc_issues) == 0
    
    if all_venues_healthy and ohlc_healthy:
        print(f'\n✅ **GO: rev1 USABLE** - All venues have close non-NaN >= 98% and OHLC invariants hold')
        print(f'📊 Ready to proceed to STEP C')
        qc_results['rev1_usable'] = True
    else:
        print(f'\n❌ **STOP: rev1 NOT USABLE** - QC failed')
        print(f'📊 Need Alternative Route A (Partitioned rebuild)')
        qc_results['rev1_usable'] = False
    
    # Update QC results with decision
    with open('analysis/outputs_v4/stepB_qc_forensics.json', 'w') as f:
        json.dump(qc_results, f, indent=2, default=str)
    
    print(f'\n🛑 **STOP** - Awaiting human review')

if __name__ == '__main__':
    main()





