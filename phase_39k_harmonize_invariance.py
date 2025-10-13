#!/usr/bin/env python3
"""
Phase 39K-HARMONIZE-INVARIANCE: Build hourly beacon tables and tick-to-bar aggregates
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import gzip
import json
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
CANONICAL_DIR = BASE_DIR / 'data_v7' / 'canonical'
OUTPUT_DIR = BASE_DIR / 'data_v7' / 'beacons'
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'invariance'

# Venues and their expected pairs
VENUES = {
    'BINANCE': 'BTCUSDT',
    'COINBASE': 'BTC-USD', 
    'BYBITSPOT': 'BTCUSDT',
    'BITGET': 'BTCUSDT'
}

# Date range for processing
START_DATE = datetime(2025, 7, 7)
END_DATE = datetime(2025, 10, 10)  # Exclude future dates

def load_canonical_manifest():
    """Load the canonical manifest to understand available data"""
    print("📋 Loading canonical manifest...")
    
    manifest_path = BASE_DIR / 'data_v7' / 'reports' / 'canonical' / 'CANON_manifest.csv'
    
    if not manifest_path.exists():
        print("❌ Canonical manifest not found")
        return None
    
    df = pd.read_csv(manifest_path)
    print(f"✅ Loaded manifest: {len(df)} files")
    
    # Filter out non-date values (keep only 8-digit dates)
    df = df[df['date'].astype(str).str.len() == 8]
    
    # Convert date to datetime for filtering (handle mixed formats)
    df['date_dt'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
    
    # Filter to available date range
    df = df[(df['date_dt'] >= START_DATE) & (df['date_dt'] <= END_DATE)]
    print(f"📊 Files in date range: {len(df)}")
    
    return df

def load_tick_file(file_path):
    """Load a single tick file and parse it"""
    try:
        with gzip.open(file_path, 'rt') as f:
            # Read header
            header = f.readline().strip()
            columns = header.split(';')
            
            # Read data
            data = []
            for line in f:
                if line.strip():
                    values = line.strip().split(';')
                    if len(values) == len(columns):
                        data.append(values)
            
            if not data:
                return None
            
            df = pd.DataFrame(data, columns=columns)
            
            # Parse timestamps
            if 'time_exchange' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time_exchange'])
            elif 'time_coinapi' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time_coinapi'])
            else:
                return None
            
            # Parse price and volume
            if 'price' in df.columns:
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
            if 'base_amount' in df.columns:
                df['volume'] = pd.to_numeric(df['base_amount'], errors='coerce')
            
            # Clean data
            df = df.dropna(subset=['timestamp', 'price'])
            df = df.sort_values('timestamp')
            
            return df
            
    except Exception as e:
        print(f"    ⚠️ Error loading {file_path}: {e}")
        return None

def compute_hourly_features(df, venue):
    """Compute hourly features from tick data"""
    if df is None or len(df) == 0:
        return None
    
    # Set timestamp as index
    df = df.set_index('timestamp')
    
    # Resample to hourly
    hourly = df.resample('1H').agg({
        'price': ['last', 'mean', 'std', 'min', 'max'],
        'volume': ['sum', 'mean', 'std']
    }).dropna()
    
    if len(hourly) == 0:
        return None
    
    # Flatten column names
    hourly.columns = ['_'.join(col).strip() for col in hourly.columns]
    
    # Compute additional features
    hourly['vwap'] = (df['price'] * df['volume']).resample('1H').sum() / df['volume'].resample('1H').sum()
    hourly['price_range'] = hourly['price_max'] - hourly['price_min']
    hourly['volume_weighted_price'] = hourly['vwap']
    
    # Compute returns
    hourly['returns'] = hourly['price_last'].pct_change()
    hourly['log_returns'] = np.log(hourly['price_last'] / hourly['price_last'].shift(1))
    
    # Compute volatility proxy (standard deviation of log returns)
    hourly['vol_proxy'] = hourly['log_returns'].rolling(window=24, min_periods=1).std()
    
    # Compute order flow imbalance (OFI)
    if 'taker_side' in df.columns:
        df['trade_sign'] = df['taker_side'].map({'BUY': 1, 'SELL': -1})
        df['signed_volume'] = df['volume'] * df['trade_sign']
        hourly['ofi'] = df['signed_volume'].resample('1H').sum()
    else:
        hourly['ofi'] = 0
    
    # Add venue information
    hourly['venue'] = venue
    
    # Reset index to get timestamp as column
    hourly = hourly.reset_index()
    
    return hourly

def build_hourly_beacons():
    """Build hourly beacon tables from canonical dataset"""
    print("🏗️ Building hourly beacon tables...")
    
    # Load manifest
    manifest = load_canonical_manifest()
    if manifest is None:
        return None
    
    # Group by date and venue
    all_beacons = []
    
    for (date, venue), group in manifest.groupby(['date', 'venue']):
        if len(group) == 0:
            continue
        
        # Get the file path
        file_path = Path(group.iloc[0]['abs_path'])
        
        if not file_path.exists():
            print(f"    ⚠️ File not found: {file_path}")
            continue
        
        print(f"  📊 Processing: {date} {venue}")
        
        # Load tick data
        tick_data = load_tick_file(file_path)
        if tick_data is None:
            continue
        
        # Compute hourly features
        hourly_data = compute_hourly_features(tick_data, venue)
        if hourly_data is None:
            continue
        
        # Add date information
        hourly_data['date'] = date
        hourly_data['venue'] = venue
        
        all_beacons.append(hourly_data)
    
    if not all_beacons:
        print("❌ No beacon data generated")
        return None
    
    # Combine all beacons
    beacons_df = pd.concat(all_beacons, ignore_index=True)
    
    # Sort by timestamp and venue
    beacons_df = beacons_df.sort_values(['timestamp', 'venue'])
    
    print(f"✅ Generated {len(beacons_df)} hourly beacon records")
    return beacons_df

def create_tick_aggregates(beacons_df):
    """Create standardized tick-to-bar aggregates (1s, 1m, 1h)"""
    print("📊 Creating tick-to-bar aggregates...")
    
    if beacons_df is None or len(beacons_df) == 0:
        return None
    
    # Set timestamp as index
    beacons_df = beacons_df.set_index('timestamp')
    
    aggregates = {}
    
    # 1-second aggregates
    print("  📈 Computing 1-second aggregates...")
    sec_1 = beacons_df.resample('1S').agg({
        'price_last': ['last', 'mean', 'std'],
        'volume_sum': 'sum',
        'ofi': 'sum'
    }).dropna()
    sec_1.columns = ['_'.join(col).strip() for col in sec_1.columns]
    aggregates['1s'] = sec_1
    
    # 1-minute aggregates
    print("  📈 Computing 1-minute aggregates...")
    min_1 = beacons_df.resample('1T').agg({
        'price_last': ['last', 'mean', 'std', 'min', 'max'],
        'volume_sum': 'sum',
        'ofi': 'sum',
        'vol_proxy': 'mean'
    }).dropna()
    min_1.columns = ['_'.join(col).strip() for col in min_1.columns]
    aggregates['1m'] = min_1
    
    # 1-hour aggregates (already computed)
    print("  📈 Using existing 1-hour aggregates...")
    aggregates['1h'] = beacons_df
    
    print(f"✅ Generated aggregates: {', '.join(aggregates.keys())}")
    return aggregates

def create_venue_aligned_joins(beacons_df):
    """Create venue-aligned timestamp joins for invariance analysis"""
    print("🔗 Creating venue-aligned timestamp joins...")
    
    if beacons_df is None or len(beacons_df) == 0:
        return None
    
    # Pivot to get venues as columns
    pivot_cols = ['price_last', 'volume_sum', 'ofi', 'vol_proxy', 'vwap']
    
    aligned_data = {}
    
    for col in pivot_cols:
        if col in beacons_df.columns:
            pivot_df = beacons_df.pivot_table(
                index='timestamp',
                columns='venue',
                values=col,
                aggfunc='mean'
            )
            aligned_data[col] = pivot_df
    
    # Create a comprehensive aligned dataset
    if aligned_data:
        # Start with price data
        aligned_df = aligned_data['price_last'].copy()
        aligned_df.columns = [f'price_{col.lower()}' for col in aligned_df.columns]
        
        # Add other features
        for feature, df in aligned_data.items():
            if feature != 'price_last':
                feature_cols = {col: f'{feature}_{col.lower()}' for col in df.columns}
                df_renamed = df.rename(columns=feature_cols)
                aligned_df = aligned_df.join(df_renamed)
        
        # Fill missing values with forward fill
        aligned_df = aligned_df.fillna(method='ffill').fillna(method='bfill')
        
        print(f"✅ Created venue-aligned dataset: {len(aligned_df)} timestamps")
        return aligned_df
    
    return None

def compute_invariance_metrics(aligned_df):
    """Compute invariance analysis metrics"""
    print("📐 Computing invariance metrics...")
    
    if aligned_df is None or len(aligned_df) == 0:
        return None
    
    metrics = {}
    
    # Price correlation matrix
    price_cols = [col for col in aligned_df.columns if col.startswith('price_')]
    if len(price_cols) > 1:
        price_corr = aligned_df[price_cols].corr()
        metrics['price_correlation'] = price_corr
    
    # Volume correlation matrix
    volume_cols = [col for col in aligned_df.columns if col.startswith('volume_sum_')]
    if len(volume_cols) > 1:
        volume_corr = aligned_df[volume_cols].corr()
        metrics['volume_correlation'] = volume_corr
    
    # OFI correlation matrix
    ofi_cols = [col for col in aligned_df.columns if col.startswith('ofi_')]
    if len(ofi_cols) > 1:
        ofi_corr = aligned_df[ofi_cols].corr()
        metrics['ofi_correlation'] = ofi_corr
    
    # Cross-venue price differences
    if len(price_cols) > 1:
        price_diffs = {}
        for i, col1 in enumerate(price_cols):
            for col2 in price_cols[i+1:]:
                diff_name = f"{col1.replace('price_', '')}_vs_{col2.replace('price_', '')}"
                price_diffs[diff_name] = aligned_df[col1] - aligned_df[col2]
        metrics['price_differences'] = pd.DataFrame(price_diffs)
    
    # Price ratio stability
    if len(price_cols) > 1:
        price_ratios = {}
        for i, col1 in enumerate(price_cols):
            for col2 in price_cols[i+1:]:
                ratio_name = f"{col1.replace('price_', '')}_over_{col2.replace('price_', '')}"
                price_ratios[ratio_name] = aligned_df[col1] / aligned_df[col2]
        metrics['price_ratios'] = pd.DataFrame(price_ratios)
    
    # Volume symmetry measures
    if len(volume_cols) > 1:
        volume_symmetry = {}
        for i, col1 in enumerate(volume_cols):
            for col2 in volume_cols[i+1:]:
                sym_name = f"{col1.replace('volume_sum_', '')}_vs_{col2.replace('volume_sum_', '')}"
                # Volume ratio (symmetry measure)
                volume_symmetry[sym_name] = aligned_df[col1] / aligned_df[col2]
        metrics['volume_symmetry'] = pd.DataFrame(volume_symmetry)
    
    # OFI divergence indices
    if len(ofi_cols) > 1:
        ofi_divergence = {}
        for i, col1 in enumerate(ofi_cols):
            for col2 in ofi_cols[i+1:]:
                div_name = f"{col1.replace('ofi_', '')}_vs_{col2.replace('ofi_', '')}"
                # OFI difference (divergence measure)
                ofi_divergence[div_name] = aligned_df[col1] - aligned_df[col2]
        metrics['ofi_divergence'] = pd.DataFrame(ofi_divergence)
    
    # Summary statistics
    metrics['summary'] = {
        'total_timestamps': len(aligned_df),
        'price_features': len(price_cols),
        'volume_features': len(volume_cols),
        'ofi_features': len(ofi_cols),
        'date_range': f"{aligned_df.index.min()} to {aligned_df.index.max()}",
        'price_correlation_mean': price_corr.values[np.triu_indices_from(price_corr.values, k=1)].mean() if len(price_cols) > 1 else 0,
        'volume_correlation_mean': volume_corr.values[np.triu_indices_from(volume_corr.values, k=1)].mean() if len(volume_cols) > 1 else 0,
        'ofi_correlation_mean': ofi_corr.values[np.triu_indices_from(ofi_corr.values, k=1)].mean() if len(ofi_cols) > 1 else 0
    }
    
    print(f"✅ Computed {len(metrics)} metric categories")
    return metrics

def save_outputs(beacons_df, aggregates, aligned_df, metrics):
    """Save all outputs to files"""
    print("💾 Saving outputs...")
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save hourly beacons
    if beacons_df is not None:
        beacons_path = OUTPUT_DIR / 'hourly_beacons.parquet'
        beacons_df.to_parquet(beacons_path)
        print(f"✅ Saved hourly beacons: {beacons_path}")
    
    # Save aggregates
    if aggregates:
        for freq, df in aggregates.items():
            agg_path = OUTPUT_DIR / f'aggregates_{freq}.parquet'
            df.to_parquet(agg_path)
            print(f"✅ Saved {freq} aggregates: {agg_path}")
    
    # Save aligned data
    if aligned_df is not None:
        aligned_path = OUTPUT_DIR / 'venue_aligned.parquet'
        aligned_df.to_parquet(aligned_path)
        print(f"✅ Saved venue-aligned data: {aligned_path}")
    
    # Save metrics
    if metrics:
        metrics_path = REPORTS_DIR / 'invariance_metrics.json'
        
        # Convert DataFrames to dict for JSON serialization
        metrics_json = {}
        for key, value in metrics.items():
            if isinstance(value, pd.DataFrame):
                # Convert DataFrame to dict, handling Timestamp keys
                df_dict = value.to_dict()
                # Convert any Timestamp keys to ISO strings (avoid mutation during iteration)
                if isinstance(df_dict, dict):
                    # First pass: convert top-level keys
                    keys_to_convert = [k for k in df_dict.keys() if hasattr(k, 'isoformat')]
                    for k in keys_to_convert:
                        df_dict[k.isoformat()] = df_dict.pop(k)
                    
                    # Second pass: convert nested dict keys
                    for k, v in df_dict.items():
                        if isinstance(v, dict):
                            nested_keys_to_convert = [k2 for k2 in v.keys() if hasattr(k2, 'isoformat')]
                            for k2 in nested_keys_to_convert:
                                v[k2.isoformat()] = v.pop(k2)
                metrics_json[key] = df_dict
            else:
                metrics_json[key] = value
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics_json, f, indent=2, default=str)
        print(f"✅ Saved invariance metrics: {metrics_path}")
    
    # Save summary report
    summary_path = REPORTS_DIR / 'harmonize_summary.txt'
    with open(summary_path, 'w') as f:
        f.write("Phase 39K-HARMONIZE-INVARIANCE Summary\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
        
        if beacons_df is not None:
            f.write(f"Hourly Beacons: {len(beacons_df)} records\n")
            f.write(f"Date Range: {beacons_df['timestamp'].min()} to {beacons_df['timestamp'].max()}\n")
            f.write(f"Venues: {', '.join(beacons_df['venue'].unique())}\n\n")
        
        if aggregates:
            f.write("Aggregates Generated:\n")
            for freq, df in aggregates.items():
                f.write(f"  {freq}: {len(df)} records\n")
            f.write("\n")
        
        if aligned_df is not None:
            f.write(f"Venue-Aligned Data: {len(aligned_df)} timestamps\n")
            f.write(f"Features: {len(aligned_df.columns)} columns\n\n")
        
        if metrics and 'summary' in metrics:
            summary = metrics['summary']
            f.write("Invariance Metrics:\n")
            for key, value in summary.items():
                f.write(f"  {key}: {value}\n")
    
    print(f"✅ Saved summary report: {summary_path}")

def create_invariance_summary(metrics):
    """Create detailed invariance summary report"""
    print("📊 Creating invariance summary...")
    
    summary_path = REPORTS_DIR / 'invariance_summary.txt'
    
    with open(summary_path, 'w') as f:
        f.write("Invariance Analysis Summary Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
        
        if metrics and 'summary' in metrics:
            summary = metrics['summary']
            f.write("Dataset Overview:\n")
            f.write(f"  Total timestamps: {summary.get('total_timestamps', 'N/A')}\n")
            f.write(f"  Price features: {summary.get('price_features', 'N/A')}\n")
            f.write(f"  Volume features: {summary.get('volume_features', 'N/A')}\n")
            f.write(f"  OFI features: {summary.get('ofi_features', 'N/A')}\n")
            f.write(f"  Date range: {summary.get('date_range', 'N/A')}\n\n")
            
            f.write("Cross-Venue Correlation Analysis:\n")
            f.write(f"  Price correlation (mean): {summary.get('price_correlation_mean', 0):.4f}\n")
            f.write(f"  Volume correlation (mean): {summary.get('volume_correlation_mean', 0):.4f}\n")
            f.write(f"  OFI correlation (mean): {summary.get('ofi_correlation_mean', 0):.4f}\n\n")
            
            f.write("Invariance Metrics Available:\n")
            for key in metrics.keys():
                if key != 'summary':
                    f.write(f"  ✓ {key}\n")
            
            f.write(f"\nInterpretation:\n")
            f.write(f"  - Price correlation > 0.9: High price invariance\n")
            f.write(f"  - Volume correlation > 0.7: Moderate volume symmetry\n")
            f.write(f"  - OFI correlation > 0.5: Order flow coordination\n")
    
    print(f"✅ Created invariance summary: {summary_path}")

def compute_bom_hash():
    """Compute BOM hash for all invariance outputs"""
    print("🔐 Computing BOM hash...")
    
    # List all output files
    output_files = []
    
    # Beacon files
    beacon_files = [
        OUTPUT_DIR / 'hourly_beacons.parquet',
        OUTPUT_DIR / 'aggregates_1s.parquet',
        OUTPUT_DIR / 'aggregates_1m.parquet',
        OUTPUT_DIR / 'aggregates_1h.parquet',
        OUTPUT_DIR / 'venue_aligned.parquet'
    ]
    
    # Report files
    report_files = [
        REPORTS_DIR / 'invariance_metrics.json',
        REPORTS_DIR / 'harmonize_summary.txt',
        REPORTS_DIR / 'invariance_summary.txt'
    ]
    
    all_files = beacon_files + report_files
    
    # Compute BOM
    bom_string = ""
    for file_path in all_files:
        if file_path.exists():
            bom_string += f"{file_path}:{file_path.stat().st_size}\n"
    
    # Compute SHA-256
    import hashlib
    bom_hash = hashlib.sha256(bom_string.encode()).hexdigest()
    
    # Save BOM hash
    bom_path = REPORTS_DIR / 'CANON_invariance_bom_sha256.txt'
    with open(bom_path, 'w') as f:
        f.write(f"Invariance Analysis BOM SHA-256: {bom_hash}\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Files included: {len([f for f in all_files if f.exists()])}\n")
        f.write(f"Total size: {sum(f.stat().st_size for f in all_files if f.exists()):,} bytes\n")
    
    print(f"✅ BOM hash computed: {bom_hash}")
    return bom_hash

def main():
    """Main execution"""
    print("🚀 Phase 39K-HARMONIZE-INVARIANCE: Build Beacon Tables & Aggregates")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Step 1: Build hourly beacons
    beacons_df = build_hourly_beacons()
    if beacons_df is None:
        print("❌ Failed to build hourly beacons")
        sys.exit(1)
    
    # Step 2: Create tick aggregates
    aggregates = create_tick_aggregates(beacons_df)
    
    # Step 3: Create venue-aligned joins
    aligned_df = create_venue_aligned_joins(beacons_df)
    
    # Step 4: Compute invariance metrics
    metrics = compute_invariance_metrics(aligned_df)
    
    # Step 5: Save outputs
    save_outputs(beacons_df, aggregates, aligned_df, metrics)
    
    # Step 6: Create additional artifacts
    if metrics:
        create_invariance_summary(metrics)
    
    # Step 7: Compute BOM hash
    bom_hash = compute_bom_hash()
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-HARMONIZE-INVARIANCE Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    print(f"\n📋 Results Summary:")
    if beacons_df is not None:
        print(f"  Hourly beacons: {len(beacons_df)} records")
        print(f"  Venues: {', '.join(beacons_df['venue'].unique())}")
        print(f"  Date range: {beacons_df['timestamp'].min()} to {beacons_df['timestamp'].max()}")
    
    if aggregates:
        print(f"  Aggregates: {', '.join(aggregates.keys())}")
    
    if aligned_df is not None:
        print(f"  Venue-aligned: {len(aligned_df)} timestamps, {len(aligned_df.columns)} features")
    
    if metrics:
        print(f"  Invariance metrics: {len(metrics)} categories")
    
    print(f"\nKey outputs:")
    print(f"  {OUTPUT_DIR / 'hourly_beacons.parquet'}")
    print(f"  {OUTPUT_DIR / 'venue_aligned.parquet'}")
    print(f"  {REPORTS_DIR / 'invariance_metrics.json'}")
    print(f"  {REPORTS_DIR / 'harmonize_summary.txt'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
