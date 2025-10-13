#!/usr/bin/env python3
"""
October W1-W2 Beacon Processing & Normalization
Convert CoinAPI Flat Files into hourly beacons and create unified 9-week panel.
"""

import os
import pandas as pd
import numpy as np
import gzip
import hashlib
import psutil
from datetime import datetime, timedelta
from scipy import stats
import glob

def check_memory_limit():
    """Check memory usage and halt if over 3GB"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 3000:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 3GB limit")
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
    
    # Create hourly bins
    df['hour'] = df['timestamp'].dt.floor('H')
    
    # Group by hour and compute features
    hourly_data = []
    
    for hour, group in df.groupby('hour'):
        if len(group) < 10:  # Skip hours with too few trades
            continue
            
        # Sort by timestamp
        group = group.sort_values('timestamp')
        
        # Compute price (VWAP)
        vwap = (group['price'] * group['volume']).sum() / group['volume'].sum()
        
        # Compute vol_proxy (z-scored hourly trade volume)
        total_volume = group['volume'].sum()
        
        # Compute OFI (Order Flow Imbalance)
        price_changes = group['price'].diff().fillna(0)
        price_signs = np.sign(price_changes)
        ofi = (price_signs * group['volume']).sum()
        
        # Compute entropy (Shannon entropy of price-change signs)
        sign_counts = price_signs.value_counts()
        if len(sign_counts) > 1:
            probabilities = sign_counts / len(price_signs)
            entropy = -np.sum(probabilities * np.log(probabilities))
        else:
            entropy = 0.0
        
        hourly_data.append({
            'timestamp': hour,
            'venue': venue,
            'price': vwap,
            'vol_proxy': total_volume,  # Will be z-scored later
            'ofi': ofi,
            'entropy': entropy
        })
    
    return pd.DataFrame(hourly_data)

def process_october_data():
    """Process all October raw files into hourly beacons"""
    print("🔍 **Task 1: Parse Raw Trades → Hourly Beacons**")
    print("=" * 60)
    
    raw_dir = 'data_v6/raw/coinapi_oct'
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    all_beacons = []
    
    # Get all files
    files = glob.glob(os.path.join(raw_dir, '*.csv.gz'))
    files.sort()
    
    print(f"📊 Processing {len(files)} files...")
    
    for filepath in files:
        filename = os.path.basename(filepath)
        # Parse filename: VENUE_YYYYMMDD_BTCUSDT.csv.gz
        parts = filename.replace('.csv.gz', '').split('_')
        if len(parts) >= 3:
            venue = parts[0]
            date = parts[1]
            
            print(f"📊 Processing {venue} {date}...")
            
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
    
    if all_beacons:
        # Combine all beacons
        oct_beacons = pd.concat(all_beacons, ignore_index=True)
        
        # Z-score vol_proxy across all venues
        oct_beacons['vol_proxy'] = (oct_beacons['vol_proxy'] - oct_beacons['vol_proxy'].mean()) / oct_beacons['vol_proxy'].std()
        
        print(f"✅ October beacons created: {len(oct_beacons)} rows")
        return oct_beacons
    else:
        print("❌ No beacons created")
        return pd.DataFrame()

def compute_leader_per_hour(beacons_df):
    """Compute leader (venue with highest OFI) per hour"""
    if len(beacons_df) == 0:
        return beacons_df
    
    # Group by timestamp and find venue with highest OFI
    leader_data = []
    
    for timestamp, group in beacons_df.groupby('timestamp'):
        if len(group) > 0:
            # Find venue with highest OFI
            leader_venue = group.loc[group['ofi'].idxmax(), 'venue']
            
            # Add leader to all rows for this hour
            group = group.copy()
            group['leader'] = leader_venue
            leader_data.append(group)
    
    if leader_data:
        return pd.concat(leader_data, ignore_index=True)
    else:
        return beacons_df

def validate_coverage(beacons_df):
    """Validate coverage against expected rows"""
    print(f"\n🔍 **Task 2: Validate Coverage**")
    print("=" * 60)
    
    # Expected: 2 weeks × 7 days × 24 hours × 4 venues = 1,344 rows
    expected_oct = 2 * 7 * 24 * 4
    actual_oct = len(beacons_df)
    
    print(f"📊 Expected October rows: {expected_oct}")
    print(f"📊 Actual October rows: {actual_oct}")
    print(f"📊 Coverage: {(actual_oct/expected_oct)*100:.1f}%")
    
    # Coverage by venue
    venue_coverage = []
    for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
        venue_data = beacons_df[beacons_df['venue'] == venue]
        venue_hours = len(venue_data)
        expected_hours = 2 * 7 * 24  # 2 weeks × 7 days × 24 hours
        missing_hours = expected_hours - venue_hours
        coverage_pct = (venue_hours / expected_hours) * 100
        
        venue_coverage.append({
            'Venue': venue,
            'Hours Present': venue_hours,
            'Missing Hours': missing_hours,
            '% Coverage': f"{coverage_pct:.1f}%"
        })
    
    coverage_df = pd.DataFrame(venue_coverage)
    print(f"\n📊 **Coverage by Venue:**")
    print(coverage_df.to_string(index=False))
    
    return coverage_df

def merge_and_normalize(oct_beacons):
    """Merge with existing Aug-Sep data and apply global normalization"""
    print(f"\n🔍 **Task 3: Merge & Global Scale**")
    print("=" * 60)
    
    # Load existing Aug-Sep data
    existing_path = 'data_v6/cache/beacons/beacons_aug_sep_7w_norm.parquet'
    if not os.path.exists(existing_path):
        print(f"❌ Existing data not found: {existing_path}")
        return None
    
    print("📊 Loading existing Aug-Sep data...")
    existing_df = pd.read_parquet(existing_path)
    print(f"📊 Existing data: {len(existing_df)} rows")
    
    # Add leader to October data
    oct_beacons = compute_leader_per_hour(oct_beacons)
    
    # Combine datasets
    print("📊 Combining datasets...")
    combined_df = pd.concat([existing_df, oct_beacons], ignore_index=True)
    print(f"📊 Combined data: {len(combined_df)} rows")
    
    # Apply global normalization
    print("📊 Applying global normalization...")
    
    # Winsorize 1-99 percentile
    for col in ['price', 'entropy', 'ofi', 'vol_proxy']:
        lower = combined_df[col].quantile(0.01)
        upper = combined_df[col].quantile(0.99)
        combined_df[col] = combined_df[col].clip(lower, upper)
    
    # Apply log1p to OFI only
    combined_df['ofi'] = np.sign(combined_df['ofi']) * np.log1p(np.abs(combined_df['ofi']))
    
    # Median/MAD standardization
    for col in ['price', 'entropy', 'ofi', 'vol_proxy']:
        median = combined_df[col].median()
        mad = np.median(np.abs(combined_df[col] - median))
        if mad > 0:
            combined_df[col] = (combined_df[col] - median) / mad
    
    print("✅ Global normalization applied")
    return combined_df

def distribution_consistency_checks(combined_df):
    """Run KS tests for distribution consistency"""
    print(f"\n🔍 **Task 4: Distribution Consistency Checks**")
    print("=" * 60)
    
    # Split data by month
    combined_df['month'] = combined_df['timestamp'].dt.to_period('M')
    
    aug_data = combined_df[combined_df['month'] == '2025-08']
    sep_data = combined_df[combined_df['month'] == '2025-09']
    oct_data = combined_df[combined_df['month'] == '2025-10']
    
    print(f"📊 August data: {len(aug_data)} rows")
    print(f"📊 September data: {len(sep_data)} rows")
    print(f"📊 October data: {len(oct_data)} rows")
    
    # KS tests
    features = ['entropy', 'ofi', 'vol_proxy']
    ks_results = []
    
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
            'KS p-value (Sep vs Oct)': f"{p_value_sep_oct:.4f}" if not np.isnan(p_value_sep_oct) else "N/A",
            'Pass (> 0.05 = OK)': '✅' if (p_value_aug_sep > 0.05 and p_value_sep_oct > 0.05) else '❌'
        })
    
    ks_df = pd.DataFrame(ks_results)
    print(f"\n📊 **KS Distribution Tests:**")
    print(ks_df.to_string(index=False))
    
    return ks_df

def quality_assurance_outputs(combined_df):
    """Generate quality assurance outputs"""
    print(f"\n🔍 **Task 5: Quality Assurance Outputs**")
    print("=" * 60)
    
    # Coverage table by venue and month
    coverage_data = []
    for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
        venue_data = combined_df[combined_df['venue'] == venue]
        for month in ['2025-08', '2025-09', '2025-10']:
            month_data = venue_data[venue_data['timestamp'].dt.to_period('M').astype(str) == month]
            coverage_data.append({
                'Venue': venue,
                'Month': month,
                'Hours': len(month_data)
            })
    
    coverage_df = pd.DataFrame(coverage_data)
    print(f"\n📊 **Coverage Table (Venue × Month):**")
    print(coverage_df.to_string(index=False))
    
    # Global feature summary
    features = ['price', 'entropy', 'ofi', 'vol_proxy']
    summary_data = []
    
    for feature in features:
        data = combined_df[feature].dropna()
        summary_data.append({
            'Feature': feature,
            'Mean': f"{data.mean():.4f}",
            'Std': f"{data.std():.4f}",
            'MAD': f"{np.median(np.abs(data - data.median())):.4f}",
            'Min': f"{data.min():.4f}",
            'Max': f"{data.max():.4f}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    print(f"\n📊 **Global Feature Summary:**")
    print(summary_df.to_string(index=False))
    
    # Save final file
    output_path = 'data_v6/cache/beacons/beacons_aug_sep_oct_9w_norm.parquet'
    print(f"\n📊 Saving final file: {output_path}")
    combined_df.to_parquet(output_path, index=False)
    
    # Compute SHA-256 checksum
    with open(output_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    print(f"📊 Final file SHA-256: {file_hash}")
    print(f"📊 Final row count: {len(combined_df)}")
    
    # Memory diagnostics
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"📊 Final memory usage: {current_mb:.1f} MB")
    
    return coverage_df, summary_df, file_hash

def main():
    print('🔍 October W1-W2 Beacon Processing & Normalization')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Task 1: Parse raw trades → hourly beacons
    oct_beacons = process_october_data()
    if len(oct_beacons) == 0:
        print("❌ HALT: No October beacons created")
        return
    
    # Task 2: Validate coverage
    coverage_df = validate_coverage(oct_beacons)
    
    # Task 3: Merge and normalize
    combined_df = merge_and_normalize(oct_beacons)
    if combined_df is None:
        print("❌ HALT: Failed to merge and normalize data")
        return
    
    # Task 4: Distribution consistency checks
    ks_df = distribution_consistency_checks(combined_df)
    
    # Task 5: Quality assurance outputs
    coverage_final, summary_df, file_hash = quality_assurance_outputs(combined_df)
    
    print(f"\n✅ All tasks completed successfully!")
    print(f"✅ Final 9-week panel created with {len(combined_df)} rows")
    print(f"✅ File saved: data_v6/cache/beacons/beacons_aug_sep_oct_9w_norm.parquet")

if __name__ == '__main__':
    main()
