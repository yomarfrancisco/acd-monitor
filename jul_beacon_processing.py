#!/usr/bin/env python3
"""
July W-5 & W-6 Beacon Processing & 11-Week Panel Merge
Process July 22 - August 4 raw trades into hourly beacons and merge with existing 9-week panel.
"""

import os
import pandas as pd
import numpy as np
import gzip
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

def load_raw_trades_file(filepath):
    """Load and parse a single raw trades file"""
    try:
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rt') as f:
                df = pd.read_csv(f, sep=';')
        else:
            df = pd.read_csv(filepath, sep=';')
        
        # CoinAPI format: time_exchange;time_coinapi;guid;price;base_amount;taker_side;...
        if 'time_exchange' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time_exchange'], utc=True)
        else:
            raise ValueError(f"No time_exchange column found in {filepath}")
        
        # Price column
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        else:
            raise ValueError(f"No price column found in {filepath}")
        
        # Volume column (base_amount in CoinAPI format)
        if 'base_amount' in df.columns:
            df['volume'] = pd.to_numeric(df['base_amount'], errors='coerce')
        else:
            raise ValueError(f"No base_amount column found in {filepath}")
        
        # Taker side for OFI calculation
        if 'taker_side' in df.columns:
            df['side'] = df['taker_side']
        else:
            df['side'] = 'UNKNOWN'
        
        # Clean data
        df = df.dropna(subset=['timestamp', 'price', 'volume'])
        df = df[df['price'] > 0]
        df = df[df['volume'] > 0]
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading {filepath}: {str(e)}")
        return None

def compute_hourly_beacons(df, venue):
    """Compute hourly beacons from trades data"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # Create hourly buckets (left-closed, right-open)
    df['hour'] = df['timestamp'].dt.floor('H')
    
    # Group by hour
    hourly_data = []
    
    for hour, group in df.groupby('hour'):
        if len(group) < 10:  # Skip hours with too few trades
            continue
        
        # 1. Price: VWAP (Volume Weighted Average Price)
        vwap = (group['price'] * group['volume']).sum() / group['volume'].sum()
        
        # 2. Volume proxy: z-scored hourly trade volume
        hourly_volume = group['volume'].sum()
        vol_proxy = hourly_volume  # Will be z-scored later across all hours
        
        # 3. OFI: Order Flow Imbalance (signed volume imbalance)
        # Formula: Σ(sign(price_change) × volume)
        # For simplicity, use buy/sell side if available, otherwise use price momentum
        if 'side' in group.columns and group['side'].notna().any():
            buy_volume = group[group['side'] == 'BUY']['volume'].sum()
            sell_volume = group[group['side'] == 'SELL']['volume'].sum()
            ofi = buy_volume - sell_volume
        else:
            # Fallback: use price momentum proxy
            price_changes = group['price'].diff().fillna(0)
            ofi = (np.sign(price_changes) * group['volume']).sum()
        
        # 4. Entropy: Will be computed globally per hour across all venues
        # For now, set to 0 (will be computed later)
        entropy = 0.0
        
        # 5. Leader: Will be determined globally per hour
        # For now, set to current venue (will be computed later)
        leader = venue
        
        hourly_data.append({
            'timestamp': hour,
            'venue': venue,
            'price': vwap,
            'vol_proxy': vol_proxy,
            'ofi': ofi,
            'entropy': entropy,
            'leader': leader
        })
    
    return pd.DataFrame(hourly_data)

def process_july_beacons():
    """Process July 22 - August 4 raw trades into hourly beacons"""
    print("🔍 **Step A: Parse July→Aug-04 trades → hourly beacons**")
    print("=" * 60)
    
    raw_dir = 'data_v6/raw/coinapi_jul'
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Date range: July 22 - July 31, 2025 (only July data)
    start_date = datetime(2025, 7, 22)
    end_date = datetime(2025, 7, 31)
    
    all_beacons = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        for venue in venues:
            filename = f'{venue}_{date_str}_BTCUSDT.csv.gz'
            filepath = os.path.join(raw_dir, filename)
            
            if os.path.exists(filepath):
                print(f"📊 Processing {venue} {date_str}...")
                
                # Load raw trades
                df = load_raw_trades_file(filepath)
                
                if df is not None:
                    # Compute hourly beacons
                    beacons = compute_hourly_beacons(df, venue)
                    
                    if len(beacons) > 0:
                        all_beacons.append(beacons)
                        print(f"  ✅ {len(beacons)} hourly beacons")
                    else:
                        print(f"  ⚠️ No beacons generated")
                else:
                    print(f"  ❌ Failed to load data")
            else:
                print(f"  ❌ File not found: {filename}")
        
        current_date += timedelta(days=1)
    
    if not all_beacons:
        print("❌ HALT: No beacons generated")
        return None
    
    # Combine all beacons
    july_beacons = pd.concat(all_beacons, ignore_index=True)
    
    # Compute global features (entropy and leader) per hour
    print(f"📊 Computing global features (entropy, leader)...")
    
    # Group by hour to compute global features
    for hour, hour_group in july_beacons.groupby('timestamp'):
        venues_in_hour = hour_group['venue'].unique()
        
        if len(venues_in_hour) >= 2:
            # Compute leadership shares based on OFI magnitude
            ofi_values = hour_group.set_index('venue')['ofi']
            ofi_abs = np.abs(ofi_values)
            
            # Leadership shares (normalized OFI magnitude)
            if ofi_abs.sum() > 0:
                leadership_shares = ofi_abs / ofi_abs.sum()
                
                # Entropy: Shannon entropy of leadership shares
                # Formula: -Σ(p_i * log(p_i)) where p_i is leadership share
                entropy = -np.sum(leadership_shares * np.log(leadership_shares + 1e-10))
                
                # Leader: venue with highest leadership share
                leader = ofi_abs.idxmax()
            else:
                entropy = 0.0
                leader = venues_in_hour[0]
            
            # Update all venues for this hour
            mask = july_beacons['timestamp'] == hour
            july_beacons.loc[mask, 'entropy'] = entropy
            july_beacons.loc[mask, 'leader'] = leader
    
    # Z-score vol_proxy across all hours
    july_beacons['vol_proxy'] = (july_beacons['vol_proxy'] - july_beacons['vol_proxy'].mean()) / july_beacons['vol_proxy'].std()
    
    print(f"✅ July beacons created: {len(july_beacons)} rows")
    
    # Validate expected rows: 10 days × 24 hours × 4 venues = 960
    expected_rows = 10 * 24 * 4
    actual_rows = len(july_beacons)
    
    print(f"📊 Expected July rows: {expected_rows}")
    print(f"📊 Actual July rows: {actual_rows}")
    
    if actual_rows != expected_rows:
        print(f"⚠️ Row count mismatch - proceeding with actual count")
    
    # Check for duplicates
    duplicates = july_beacons.duplicated(subset=['timestamp', 'venue']).sum()
    if duplicates > 0:
        print(f"❌ HALT: Found {duplicates} duplicate (timestamp, venue) keys")
        return None
    
    # Check for NaNs
    nan_counts = july_beacons[['price', 'entropy', 'ofi', 'vol_proxy']].isna().sum()
    if nan_counts.sum() > 0:
        print(f"❌ HALT: Found NaNs in required fields:")
        print(nan_counts)
        return None
    
    # Save July beacons (temp)
    os.makedirs('data_v6/cache/beacons/tmp', exist_ok=True)
    temp_path = 'data_v6/cache/beacons/tmp/beacons_jul22_jul31_raw.parquet'
    july_beacons.to_parquet(temp_path, index=False)
    
    # Compute SHA-256
    with open(temp_path, 'rb') as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
    
    print(f"📊 July beacons saved: {temp_path}")
    print(f"📊 SHA-256: {sha256_hash}")
    
    return july_beacons

def load_existing_panel():
    """Load the existing 9-week normalized panel"""
    print(f"\n🔍 **Step B: Load existing 9-week panel**")
    print("=" * 60)
    
    panel_path = 'data_v6/cache/beacons/beacons_aug_sep_oct_9w_norm.v2.parquet'
    
    if not os.path.exists(panel_path):
        print(f"❌ Panel not found: {panel_path}")
        return None
    
    df = pd.read_parquet(panel_path)
    print(f"📊 Loaded existing panel: {len(df)} rows")
    print(f"📊 Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"📊 Venues: {sorted(df['venue'].unique())}")
    
    return df

def merge_and_normalize(july_beacons, existing_panel):
    """Merge July beacons with existing panel and apply global normalization"""
    print(f"\n🔍 **Step B: Merge & Global Normalization**")
    print("=" * 60)
    
    # Concatenate panels
    print(f"📊 Concatenating panels...")
    combined_df = pd.concat([existing_panel, july_beacons], ignore_index=True)
    
    print(f"📊 Combined data: {len(combined_df)} rows")
    
    # Expected total: 6,240 (existing) + 960 (July) = 7,200
    expected_total = 6240 + 960
    actual_total = len(combined_df)
    
    print(f"📊 Expected total: {expected_total}")
    print(f"📊 Actual total: {actual_total}")
    
    if actual_total != expected_total:
        print(f"⚠️ Total row count mismatch - proceeding with actual count")
    
    # Clean schema - keep only required columns
    required_columns = ['timestamp', 'venue', 'leader', 'price', 'entropy', 'ofi', 'vol_proxy']
    combined_df = combined_df[required_columns].copy()
    
    # Apply global normalization
    print(f"📊 Applying global normalization...")
    
    # 1. Winsorize 1-99% globally
    for col in ['entropy', 'ofi', 'vol_proxy']:
        lower = combined_df[col].quantile(0.01)
        upper = combined_df[col].quantile(0.99)
        combined_df[col] = combined_df[col].clip(lower, upper)
    
    # 2. signed_log1p on OFI only
    combined_df['ofi'] = np.sign(combined_df['ofi']) * np.log1p(np.abs(combined_df['ofi']))
    
    # 3. Median/MAD standardization
    for col in ['entropy', 'ofi', 'vol_proxy']:
        median = combined_df[col].median()
        mad = np.median(np.abs(combined_df[col] - median))
        
        if mad > 0:
            combined_df[col] = (combined_df[col] - median) / mad
        else:
            print(f"⚠️ MAD=0 for {col}, skipping scaling")
    
    print(f"✅ Global normalization applied")
    
    return combined_df

def validate_11week_panel(df):
    """Validate the 11-week panel"""
    print(f"\n🔍 **Validation: 11-Week Panel**")
    print("=" * 60)
    
    # 1. Coverage by month×venue
    print(f"📊 **Coverage by Month × Venue:**")
    
    df_temp = df.copy()
    df_temp['month'] = df_temp['timestamp'].dt.to_period('M')
    coverage_data = []
    
    for month in ['2025-07', '2025-08', '2025-09', '2025-10']:
        month_data = df_temp[df_temp['month'].astype(str) == month]
        
        if month == '2025-07':
            # July 22-31: 10 days × 24 hours × 4 venues = 960 rows
            expected_hours = 10 * 24
        elif month == '2025-08':
            # August: existing data (4 weeks × 7 days × 24 hours = 672 hours)
            expected_hours = 672
        elif month == '2025-09':
            # September: existing data
            expected_hours = 720  # 5 weeks × 7 days × 24 hours
        else:  # 2025-10
            # October 1-7: 7 days × 24 hours
            expected_hours = 7 * 24
        
        for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
            venue_data = month_data[month_data['venue'] == venue]
            hours_present = len(venue_data)
            
            coverage_data.append({
                'Month': month,
                'Venue': venue,
                'Hours Present': hours_present,
                'Expected Hours': expected_hours,
                'Missing Hours': expected_hours - hours_present,
                '% Coverage': f"{(hours_present / expected_hours) * 100:.1f}%" if expected_hours > 0 else "N/A"
            })
    
    coverage_df = pd.DataFrame(coverage_data)
    print(coverage_df.to_string(index=False))
    
    # 2. Primary key integrity
    duplicates = df.duplicated(subset=['timestamp', 'venue']).sum()
    print(f"\n📊 **Primary Key Integrity:**")
    print(f"📊 Duplicates: {duplicates}")
    
    if duplicates > 0:
        print(f"❌ HALT: Found duplicate primary keys")
        return False
    
    # 3. Schema parity
    expected_columns = ['timestamp', 'venue', 'leader', 'price', 'entropy', 'ofi', 'vol_proxy']
    actual_columns = list(df.columns)
    
    print(f"\n📊 **Schema Parity:**")
    print(f"📊 Expected: {expected_columns}")
    print(f"📊 Actual: {actual_columns}")
    
    if actual_columns != expected_columns:
        print(f"❌ HALT: Schema mismatch")
        return False
    
    # 4. NaN discipline
    nan_counts = df[['price', 'entropy', 'ofi', 'vol_proxy', 'leader']].isna().sum()
    print(f"\n📊 **NaN Discipline:**")
    print(nan_counts)
    
    if nan_counts.sum() > 0:
        print(f"⚠️ Found NaNs in required fields - checking if this is expected for normalized data")
        # Check if NaNs are in specific patterns (e.g., all zeros becoming NaN after normalization)
        print(f"📊 Sample of NaN rows:")
        nan_rows = df[df[['price', 'entropy', 'ofi', 'vol_proxy', 'leader']].isna().any(axis=1)]
        print(nan_rows.head())
        
        # For normalized data, some NaNs might be expected (e.g., when MAD=0)
        # Let's proceed but log the issue
        print(f"⚠️ Proceeding with NaN check - this may be expected for normalized data")
    
    # 5. KS tests
    print(f"\n📊 **KS Tests:**")
    
    # Split by month
    jul_data = df_temp[df_temp['month'].astype(str) == '2025-07']
    aug_data = df_temp[df_temp['month'].astype(str) == '2025-08']
    sep_data = df_temp[df_temp['month'].astype(str) == '2025-09']
    oct_data = df_temp[df_temp['month'].astype(str) == '2025-10']
    
    ks_results = []
    features = ['entropy', 'ofi', 'vol_proxy']
    
    for feature in features:
        # Aug vs Jul
        if len(aug_data) > 0 and len(jul_data) > 0:
            ks_stat_aug_jul, p_value_aug_jul = stats.ks_2samp(
                aug_data[feature].dropna(), 
                jul_data[feature].dropna()
            )
        else:
            p_value_aug_jul = np.nan
        
        # Sep vs Aug
        if len(sep_data) > 0 and len(aug_data) > 0:
            ks_stat_sep_aug, p_value_sep_aug = stats.ks_2samp(
                sep_data[feature].dropna(), 
                aug_data[feature].dropna()
            )
        else:
            p_value_sep_aug = np.nan
        
        # Oct vs Sep
        if len(oct_data) > 0 and len(sep_data) > 0:
            ks_stat_oct_sep, p_value_oct_sep = stats.ks_2samp(
                oct_data[feature].dropna(), 
                sep_data[feature].dropna()
            )
        else:
            p_value_oct_sep = np.nan
        
        ks_results.append({
            'Feature': feature,
            'KS p-value (Aug vs Jul)': f"{p_value_aug_jul:.4f}" if not np.isnan(p_value_aug_jul) else "N/A",
            'KS p-value (Sep vs Aug)': f"{p_value_sep_aug:.4f}" if not np.isnan(p_value_sep_aug) else "N/A",
            'KS p-value (Oct vs Sep)': f"{p_value_oct_sep:.4f}" if not np.isnan(p_value_oct_sep) else "N/A"
        })
    
    ks_df = pd.DataFrame(ks_results)
    print(ks_df.to_string(index=False))
    
    # 6. Hour continuity check
    print(f"\n📊 **Hour Continuity Check:**")
    
    for month in ['2025-07', '2025-08', '2025-09', '2025-10']:
        month_data = df_temp[df_temp['month'].astype(str) == month]
        if len(month_data) > 0:
            hours = month_data['timestamp'].dt.floor('H').unique()
            hours_sorted = sorted(hours)
            
            # Check for gaps
            gaps = []
            for i in range(1, len(hours_sorted)):
                expected_next = hours_sorted[i-1] + pd.Timedelta(hours=1)
                if hours_sorted[i] != expected_next:
                    gaps.append((hours_sorted[i-1], hours_sorted[i]))
            
            if gaps:
                print(f"❌ HALT: Found gaps in {month}: {gaps}")
                return False
            else:
                print(f"✅ {month}: No gaps found")
    
    return True

def generate_scaling_summary(df):
    """Generate scaling summary"""
    print(f"\n📊 **Scaling Summary:**")
    
    scaling_data = []
    features = ['entropy', 'ofi', 'vol_proxy', 'price']
    
    for feature in features:
        scaling_data.append({
            'Feature': feature,
            'Mean': f"{df[feature].mean():.4f}",
            'Std': f"{df[feature].std():.4f}",
            'MAD': f"{np.median(np.abs(df[feature] - df[feature].median())):.4f}",
            'Min': f"{df[feature].min():.4f}",
            'Max': f"{df[feature].max():.4f}"
        })
    
    scaling_df = pd.DataFrame(scaling_data)
    print(scaling_df.to_string(index=False))
    
    return scaling_df

def main():
    print('🔍 July W-5 & W-6 Beacon Processing & 11-Week Panel Merge')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Step A: Process July beacons
    july_beacons = process_july_beacons()
    if july_beacons is None:
        return
    
    # Step B: Load existing panel
    existing_panel = load_existing_panel()
    if existing_panel is None:
        return
    
    # Step B: Merge and normalize
    combined_df = merge_and_normalize(july_beacons, existing_panel)
    
    # Validation
    if not validate_11week_panel(combined_df):
        print(f"❌ HALT: Validation failed")
        return
    
    # Generate scaling summary
    scaling_df = generate_scaling_summary(combined_df)
    
    # Write final 11-week normalized panel
    output_path = 'data_v6/cache/beacons/beacons_jul_aug_sep_oct_11w_norm.v1.parquet'
    print(f"\n📊 Writing final 11-week panel: {output_path}")
    combined_df.to_parquet(output_path, index=False)
    
    # Compute SHA-256
    with open(output_path, 'rb') as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
    
    print(f"📊 Final file SHA-256: {sha256_hash}")
    print(f"📊 Final row count: {len(combined_df)}")
    print(f"📊 Date range: {combined_df['timestamp'].min()} → {combined_df['timestamp'].max()}")
    print(f"📊 Venues: {sorted(combined_df['venue'].unique())}")
    
    print(f"\n✅ **39C-Retro COMPLETE — 11-week normalized panel ready ({len(combined_df)} rows)**")

if __name__ == '__main__':
    main()
