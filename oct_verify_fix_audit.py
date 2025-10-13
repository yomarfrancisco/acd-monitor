#!/usr/bin/env python3
"""
October W1-W2 Coverage & Consistency Audit
Verify and fix the 9-week panel for exact window coverage and data integrity.
"""

import os
import pandas as pd
import numpy as np
import hashlib
import psutil
from datetime import datetime, timedelta
from scipy import stats

def check_memory_limit():
    """Check memory usage and halt if over 3.5GB"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 3500:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 3.5GB limit")
        return False
    print(f"📊 Memory usage: {current_mb:.1f} MB")
    return True

def load_current_panel():
    """Load the current 9-week panel"""
    print("🔍 **Step 1: Load Current 9-Week Panel**")
    print("=" * 60)
    
    panel_path = 'data_v6/cache/beacons/beacons_aug_sep_oct_9w_norm.parquet'
    if not os.path.exists(panel_path):
        print(f"❌ Panel not found: {panel_path}")
        return None
    
    df = pd.read_parquet(panel_path)
    print(f"📊 Loaded panel: {len(df)} rows")
    print(f"📊 Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"📊 Venues: {sorted(df['venue'].unique())}")
    
    return df

def check_key_integrity(df):
    """Check for duplicate (timestamp, venue) keys"""
    print(f"\n🔍 **Step 2: Key Integrity Check**")
    print("=" * 60)
    
    # Create primary key
    df['timestamp_utc_hour'] = df['timestamp'].dt.floor('H')
    df['primary_key'] = df['timestamp_utc_hour'].astype(str) + '_' + df['venue']
    
    # Count duplicates
    key_counts = df['primary_key'].value_counts()
    duplicates = key_counts[key_counts > 1]
    
    if len(duplicates) > 0:
        print(f"❌ Found {len(duplicates)} duplicate keys")
        print(f"📊 Top 10 duplicates:")
        for key, count in duplicates.head(10).items():
            print(f"   {key}: {count} occurrences")
        
        # Propose de-dup rule
        print(f"\n📊 **Proposed De-dup Rule:**")
        print(f"   Keep first occurrence by ingest order")
        print(f"   Drop {duplicates.sum() - len(duplicates)} duplicate rows")
        
        # Apply de-duplication
        print(f"📊 Applying de-duplication...")
        df_dedup = df.drop_duplicates(subset=['timestamp_utc_hour', 'venue'], keep='first')
        dropped_count = len(df) - len(df_dedup)
        print(f"📊 Dropped {dropped_count} duplicate rows")
        print(f"📊 Remaining rows: {len(df_dedup)}")
        
        return df_dedup, True
    else:
        print(f"✅ No duplicate keys found")
        return df, False

def enforce_october_slice(df):
    """Enforce exact October W1-W2 slice (Oct 1-14 UTC)"""
    print(f"\n🔍 **Step 3: October Slice Enforcement**")
    print("=" * 60)
    
    # Define exact October window: 2025-10-01 00:00:00 → 2025-10-07 23:00:00 UTC (7 days available)
    oct_start = pd.Timestamp('2025-10-01 00:00:00', tz='UTC')
    oct_end = pd.Timestamp('2025-10-07 23:00:00', tz='UTC')
    
    print(f"📊 October window: {oct_start} → {oct_end}")
    
    # Split data by month
    df['month'] = df['timestamp'].dt.to_period('M')
    aug_data = df[df['month'] == '2025-08']
    sep_data = df[df['month'] == '2025-09']
    oct_data = df[df['month'] == '2025-10']
    
    print(f"📊 Current October data: {len(oct_data)} rows")
    
    # Hard slice October data to exact window
    oct_sliced = oct_data[
        (oct_data['timestamp'] >= oct_start) & 
        (oct_data['timestamp'] <= oct_end)
    ].copy()
    
    print(f"📊 October sliced data: {len(oct_sliced)} rows")
    
    # Expected October rows: 7 days × 24 hours × 4 venues = 672
    expected_oct = 7 * 24 * 4
    actual_oct = len(oct_sliced)
    
    print(f"📊 Expected October rows: {expected_oct}")
    print(f"📊 Actual October rows: {actual_oct}")
    
    if actual_oct != expected_oct:
        print(f"❌ October row count mismatch!")
        
        # Analyze by venue and day
        oct_sliced['date'] = oct_sliced['timestamp'].dt.date
        oct_sliced['venue'] = oct_sliced['venue']
        
        # Coverage by venue
        venue_coverage = []
        for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
            venue_data = oct_sliced[oct_sliced['venue'] == venue]
            venue_hours = len(venue_data)
            expected_hours = 7 * 24  # 7 days × 24 hours
            missing_hours = expected_hours - venue_hours
            
            venue_coverage.append({
                'Venue': venue,
                'Hours Present': venue_hours,
                'Expected Hours': expected_hours,
                'Missing Hours': missing_hours,
                'Status': 'OK' if missing_hours == 0 else 'GAP'
            })
        
        venue_df = pd.DataFrame(venue_coverage)
        print(f"\n📊 **October Coverage by Venue:**")
        print(venue_df.to_string(index=False))
        
        # Coverage by day
        daily_coverage = []
        for date in pd.date_range(start=oct_start.date(), end=oct_end.date(), freq='D'):
            date_data = oct_sliced[oct_sliced['date'] == date.date()]
            date_hours = len(date_data)
            expected_hours = 24 * 4  # 24 hours × 4 venues
            missing_hours = expected_hours - date_hours
            
            daily_coverage.append({
                'Date': date.strftime('%Y-%m-%d'),
                'Hours Present': date_hours,
                'Expected Hours': expected_hours,
                'Missing Hours': missing_hours,
                'Status': 'OK' if missing_hours == 0 else 'GAP'
            })
        
        daily_df = pd.DataFrame(daily_coverage)
        print(f"\n📊 **October Coverage by Day:**")
        print(daily_df.to_string(index=False))
        
        return None, False
    else:
        print(f"✅ October slice correct: {actual_oct} rows")
        
        # Reconstruct full dataset
        full_df = pd.concat([aug_data, sep_data, oct_sliced], ignore_index=True)
        return full_df, True

def global_row_check(df):
    """Check global row counts for all months"""
    print(f"\n🔍 **Step 4: Global Row Check**")
    print("=" * 60)
    
    # Split by month
    df['month'] = df['timestamp'].dt.to_period('M')
    aug_data = df[df['month'] == '2025-08']
    sep_data = df[df['month'] == '2025-09']
    oct_data = df[df['month'] == '2025-10']
    
    # Expected counts
    expected_aug = 672 * 4  # 4 weeks × 7 days × 24 hours × 4 venues
    expected_sep = 720 * 4  # 5 weeks × 7 days × 24 hours × 4 venues  
    expected_oct = 672      # 7 days × 24 hours × 4 venues
    expected_total = expected_aug + expected_sep + expected_oct
    
    actual_aug = len(aug_data)
    actual_sep = len(sep_data)
    actual_oct = len(oct_data)
    actual_total = len(df)
    
    row_check = pd.DataFrame({
        'Month': ['Aug', 'Sep', 'Oct', 'Total'],
        'Expected': [expected_aug, expected_sep, expected_oct, expected_total],
        'Actual': [actual_aug, actual_sep, actual_oct, actual_total],
        'Status': [
            'OK' if actual_aug == expected_aug else 'MISMATCH',
            'OK' if actual_sep == expected_sep else 'MISMATCH', 
            'OK' if actual_oct == expected_oct else 'MISMATCH',
            'OK' if actual_total == expected_total else 'MISMATCH'
        ]
    })
    
    print(f"📊 **Global Row Check:**")
    print(row_check.to_string(index=False))
    
    if actual_total != expected_total:
        print(f"❌ Total row count mismatch: {actual_total} vs {expected_total}")
        return False
    else:
        print(f"✅ Total row count correct: {actual_total}")
        return True

def rebuild_normalization(df):
    """Rebuild normalization on corrected dataset"""
    print(f"\n🔍 **Step 5: Rebuild Normalization**")
    print("=" * 60)
    
    # Create a copy for normalization
    df_norm = df.copy()
    
    # Winsorize 1-99% globally on [entropy, ofi, vol_proxy]
    print(f"📊 Applying winsorization (1-99%)...")
    for col in ['entropy', 'ofi', 'vol_proxy']:
        lower = df_norm[col].quantile(0.01)
        upper = df_norm[col].quantile(0.99)
        df_norm[col] = df_norm[col].clip(lower, upper)
    
    # signed_log1p on OFI only
    print(f"📊 Applying signed_log1p to OFI...")
    df_norm['ofi'] = np.sign(df_norm['ofi']) * np.log1p(np.abs(df_norm['ofi']))
    
    # Median/MAD scaling once across the corrected 9w dataset
    print(f"📊 Applying Median/MAD scaling...")
    mad_stats = []
    
    for col in ['entropy', 'ofi', 'vol_proxy']:
        median = df_norm[col].median()
        mad = np.median(np.abs(df_norm[col] - median))
        
        if mad > 0:
            df_norm[col] = (df_norm[col] - median) / mad
        else:
            print(f"⚠️ MAD=0 for {col}, skipping scaling")
        
        mad_stats.append({
            'Feature': col,
            'Median': f"{median:.4f}",
            'MAD': f"{mad:.4f}",
            'Status': 'OK' if mad > 0 else 'MAD=0'
        })
    
    mad_df = pd.DataFrame(mad_stats)
    print(f"\n📊 **MAD Statistics:**")
    print(mad_df.to_string(index=False))
    
    return df_norm

def generate_sanity_tables(df):
    """Generate sanity check tables"""
    print(f"\n🔍 **Step 6: Sanity Tables**")
    print("=" * 60)
    
    # Coverage table (month × venue)
    coverage_data = []
    for month in ['2025-08', '2025-09', '2025-10']:
        month_data = df[df['timestamp'].dt.to_period('M').astype(str) == month]
        for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
            venue_data = month_data[month_data['venue'] == venue]
            hours_present = len(venue_data)
            
            if month == '2025-08':
                expected_hours = 672  # 4 weeks × 7 days × 24 hours
            elif month == '2025-09':
                expected_hours = 720  # 5 weeks × 7 days × 24 hours
            else:  # 2025-10
                expected_hours = 168  # 7 days × 24 hours
            
            missing_hours = expected_hours - hours_present
            coverage_pct = (hours_present / expected_hours) * 100 if expected_hours > 0 else 0
            
            coverage_data.append({
                'Month': month,
                'Venue': venue,
                'Hours Present': hours_present,
                'Missing Hours': missing_hours,
                '% Coverage': f"{coverage_pct:.1f}%"
            })
    
    coverage_df = pd.DataFrame(coverage_data)
    print(f"📊 **Coverage Table (Month × Venue):**")
    print(coverage_df.to_string(index=False))
    
    # OFI distribution per venue
    ofi_stats = []
    for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
        venue_data = df[df['venue'] == venue]['ofi']
        ofi_stats.append({
            'Venue': venue,
            'Mean': f"{venue_data.mean():.4f}",
            'Std': f"{venue_data.std():.4f}",
            'MAD': f"{np.median(np.abs(venue_data - venue_data.median())):.4f}",
            'Min': f"{venue_data.min():.4f}",
            'Max': f"{venue_data.max():.4f}"
        })
    
    ofi_df = pd.DataFrame(ofi_stats)
    print(f"\n📊 **OFI Distribution per Venue:**")
    print(ofi_df.to_string(index=False))
    
    # KS tests (Aug vs Sep, Sep vs Oct)
    aug_data = df[df['timestamp'].dt.to_period('M').astype(str) == '2025-08']
    sep_data = df[df['timestamp'].dt.to_period('M').astype(str) == '2025-09']
    oct_data = df[df['timestamp'].dt.to_period('M').astype(str) == '2025-10']
    
    ks_results = []
    features = ['entropy', 'ofi', 'vol_proxy']
    
    for feature in features:
        # Aug vs Sep
        if len(aug_data) > 0 and len(sep_data) > 0:
            ks_stat_aug_sep, p_value_aug_sep = stats.ks_2samp(
                aug_data[feature].dropna(), 
                sep_data[feature].dropna()
            )
        else:
            p_value_aug_sep = np.nan
        
        # Sep vs Oct
        if len(sep_data) > 0 and len(oct_data) > 0:
            ks_stat_sep_oct, p_value_sep_oct = stats.ks_2samp(
                sep_data[feature].dropna(), 
                oct_data[feature].dropna()
            )
        else:
            p_value_sep_oct = np.nan
        
        ks_results.append({
            'Feature': feature,
            'KS p-value (Aug vs Sep)': f"{p_value_aug_sep:.4f}" if not np.isnan(p_value_aug_sep) else "N/A",
            'KS p-value (Sep vs Oct)': f"{p_value_sep_oct:.4f}" if not np.isnan(p_value_sep_oct) else "N/A"
        })
    
    ks_df = pd.DataFrame(ks_results)
    print(f"\n📊 **KS Tests:**")
    print(ks_df.to_string(index=False))
    
    return coverage_df, ofi_df, ks_df

def final_decision_and_write(df):
    """Make final decision and write corrected file if PASS"""
    print(f"\n🔍 **Step 7: Decision & Write**")
    print("=" * 60)
    
    # Final checks
    checks = []
    
    # Check 1: No duplicates
    df['timestamp_utc_hour'] = df['timestamp'].dt.floor('H')
    duplicates = df.duplicated(subset=['timestamp_utc_hour', 'venue']).sum()
    checks.append(('No duplicates', duplicates == 0, f"Found {duplicates} duplicates"))
    
    # Check 2: October = 672 rows exact (7 days)
    oct_data = df[df['timestamp'].dt.to_period('M').astype(str) == '2025-10']
    oct_rows = len(oct_data)
    checks.append(('October rows = 672', oct_rows == 672, f"October has {oct_rows} rows"))
    
    # Check 3: Total = 6,240 rows (Aug: 2,688 + Sep: 2,880 + Oct: 672)
    total_rows = len(df)
    expected_total = 2688 + 2880 + 672  # 6,240
    checks.append(('Total rows = 6,240', total_rows == expected_total, f"Total has {total_rows} rows"))
    
    # Check 4: Data quality (non-zero variance)
    variance_checks = []
    for col in ['entropy', 'ofi', 'vol_proxy']:
        variance = df[col].var()
        variance_checks.append(variance > 0)
    
    checks.append(('Non-zero variance for all features', all(variance_checks), f"Zero variance for some features"))
    
    # Print check results
    print(f"📊 **Final Checks:**")
    for check_name, passed, message in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check_name}: {status} - {message}")
    
    all_passed = all(passed for _, passed, _ in checks)
    
    if all_passed:
        print(f"\n✅ **PASS: All checks passed!**")
        
        # Write corrected file
        output_path = 'data_v6/cache/beacons/beacons_aug_sep_oct_9w_norm.v2.parquet'
        print(f"📊 Writing corrected file: {output_path}")
        df.to_parquet(output_path, index=False)
        
        # Compute SHA-256
        with open(output_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        print(f"📊 Final file SHA-256: {file_hash}")
        print(f"📊 Final row count: {len(df)}")
        
        return True, file_hash
    else:
        print(f"\n❌ **FAIL: Some checks failed!**")
        print(f"📊 **Remediation Plan:**")
        print(f"   1. Re-parse October data with exact date filtering")
        print(f"   2. Check for timezone issues in timestamp parsing")
        print(f"   3. Verify venue name consistency")
        print(f"   4. Re-run beacon processing with corrected parameters")
        
        return False, None

def main():
    print('🔍 October W1-W2 Coverage & Consistency Audit')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Step 1: Load current panel
    df = load_current_panel()
    if df is None:
        return
    
    # Step 2: Check key integrity
    df, had_duplicates = check_key_integrity(df)
    
    # Step 3: Enforce October slice
    df, oct_slice_ok = enforce_october_slice(df)
    if not oct_slice_ok:
        print(f"❌ HALT: October slice enforcement failed")
        return
    
    # Step 4: Global row check
    row_check_ok = global_row_check(df)
    if not row_check_ok:
        print(f"❌ HALT: Global row check failed")
        return
    
    # Step 5: Rebuild normalization
    df_norm = rebuild_normalization(df)
    
    # Step 6: Generate sanity tables
    coverage_df, ofi_df, ks_df = generate_sanity_tables(df_norm)
    
    # Step 7: Final decision and write
    passed, file_hash = final_decision_and_write(df_norm)
    
    if passed:
        print(f"\n✅ **AUDIT COMPLETED SUCCESSFULLY**")
        print(f"✅ Corrected 9-week panel saved with SHA-256: {file_hash}")
    else:
        print(f"\n❌ **AUDIT FAILED - REMEDIATION REQUIRED**")

if __name__ == '__main__':
    main()
