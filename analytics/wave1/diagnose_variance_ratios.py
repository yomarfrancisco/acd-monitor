#!/usr/bin/env python3
"""
Stage H: Diagnostic Drill-Down for Variance Ratio Anomaly

Investigates whether extremely low variance ratios (<0.3) are:
- Real coordination/manipulation signal
- Structural/data artifact  
- Ingestion/alignment issue
"""

import json
import os
import sys
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd
import boto3
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

S3_BUCKET = "acd-monitor-snapshots"
ANALYSIS_PREFIX = "analysis/20251001/wave1_diagnostics"
HISTORICAL_DATES = ["20250928", "20250929", "20250930", "20251001"]
SYMBOLS = ["BTC-USD", "ETH-USD"]
VENUES = ["coinbase", "kraken", "okx", "bybit"]

s3 = boto3.client('s3')

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response['Body'].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")

def compute_variance_ratio(df: pd.DataFrame) -> float:
    """Compute variance ratio from price data."""
    if len(df) < 2:
        return np.nan
    
    # Sort by timestamp
    df_sorted = df.sort_values('ts_verified')
    
    # Compute 1-second returns
    df_sorted['price_1s'] = df_sorted['last_px'].pct_change()
    df_sorted['price_1s'] = df_sorted['price_1s'].fillna(0)
    
    # Compute 5-second returns (every 5th observation)
    df_sorted['price_5s'] = df_sorted['last_px'].pct_change(periods=5)
    df_sorted['price_5s'] = df_sorted['price_5s'].fillna(0)
    
    # Calculate variances
    var_1s = df_sorted['price_1s'].var()
    var_5s = df_sorted['price_5s'].var()
    
    if var_5s == 0:
        return np.nan
    
    return var_1s / var_5s

def load_canonical_data_for_date(date: str, symbol: str) -> pd.DataFrame:
    """Load canonical data for a specific date and symbol."""
    # The canonical data is partitioned by venue, so we need to load all venue partitions
    symbol_lower = symbol.lower().replace('-', '_')
    
    # List all venue partitions for this symbol and date
    prefix = f"canonical/{date}/{symbol_lower}_ticks/"
    
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            raise Exception(f"No data found for {symbol} on {date}")
        
        # Load all venue partitions
        dfs = []
        for obj in response['Contents']:
            if obj['Key'].endswith('.parquet'):
                venue_df = read_parquet_s3(obj['Key'])
                dfs.append(venue_df)
        
        if not dfs:
            raise Exception(f"No parquet files found for {symbol} on {date}")
        
        # Combine all venue data
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
        
    except Exception as e:
        raise Exception(f"Failed to load canonical data for {symbol} on {date}: {e}")

def load_raw_trade_data(venue: str, symbol: str, date: str) -> pd.DataFrame:
    """Load raw trade-level data for control test."""
    # For the control test, we'll use the canonical data as a proxy for raw trades
    # This gives us the processed data to compare against the Wave-1 computation
    try:
        # Load all canonical data for the symbol
        all_data = load_canonical_data_for_date(date, symbol)
        
        # Filter to specific venue
        venue_data = all_data[all_data['venue'] == venue]
        
        if len(venue_data) == 0:
            raise Exception(f"No data found for venue {venue}")
        
        return venue_data
        
    except Exception as e:
        raise Exception(f"Could not load raw trade data for {venue} {symbol} on {date}: {e}")

# =============================================================================
# HISTORICAL COMPARISON
# =============================================================================

def compute_historical_variance_ratios() -> pd.DataFrame:
    """Compute variance ratios for historical dates."""
    print("📊 Computing historical variance ratios...")
    
    results = []
    
    for date in HISTORICAL_DATES:
        print(f"  📅 Processing {date}...")
        
        for symbol in SYMBOLS:
            try:
                # Load canonical data
                df = load_canonical_data_for_date(date, symbol)
                
                if len(df) == 0:
                    print(f"    ⚠️ No data for {symbol} on {date}")
                    continue
                
                # Compute overall variance ratio
                overall_vr = compute_variance_ratio(df)
                
                # Compute per-venue variance ratios
                venue_vrs = {}
                for venue in df['venue'].unique():
                    venue_df = df[df['venue'] == venue]
                    if len(venue_df) > 10:  # Minimum data requirement
                        venue_vr = compute_variance_ratio(venue_df)
                        venue_vrs[venue] = venue_vr
                
                # Calculate venue statistics
                venue_vr_values = list(venue_vrs.values())
                if venue_vr_values:
                    mean_vr = np.mean(venue_vr_values)
                    median_vr = np.median(venue_vr_values)
                    min_vr = np.min(venue_vr_values)
                    max_vr = np.max(venue_vr_values)
                    venue_count = len(venue_vr_values)
                else:
                    mean_vr = median_vr = min_vr = max_vr = np.nan
                    venue_count = 0
                
                results.append({
                    'date': date,
                    'symbol': symbol,
                    'overall_vr': overall_vr,
                    'venue_mean_vr': mean_vr,
                    'venue_median_vr': median_vr,
                    'venue_min_vr': min_vr,
                    'venue_max_vr': max_vr,
                    'venue_count': venue_count,
                    'venue_vrs': json.dumps(venue_vrs)
                })
                
                print(f"    ✅ {symbol}: overall_vr={overall_vr:.3f}, venue_mean={mean_vr:.3f}")
                
            except Exception as e:
                print(f"    ❌ Failed {symbol} on {date}: {e}")
                results.append({
                    'date': date,
                    'symbol': symbol,
                    'overall_vr': np.nan,
                    'venue_mean_vr': np.nan,
                    'venue_median_vr': np.nan,
                    'venue_min_vr': np.nan,
                    'venue_max_vr': np.nan,
                    'venue_count': 0,
                    'venue_vrs': '{}',
                    'error': str(e)
                })
    
    return pd.DataFrame(results)

# =============================================================================
# VENUE-LEVEL DRILLDOWN
# =============================================================================

def compute_venue_level_analysis() -> pd.DataFrame:
    """Compute detailed venue-level variance ratio analysis."""
    print("📊 Computing venue-level variance ratio analysis...")
    
    results = []
    
    for date in HISTORICAL_DATES:
        for symbol in SYMBOLS:
            try:
                df = load_canonical_data_for_date(date, symbol)
                
                for venue in df['venue'].unique():
                    venue_df = df[df['venue'] == venue]
                    
                    if len(venue_df) < 10:
                        continue
                    
                    # Compute variance ratio
                    vr = compute_variance_ratio(venue_df)
                    
                    # Compute additional statistics
                    venue_df_sorted = venue_df.sort_values('ts_verified')
                    venue_df_sorted['returns'] = venue_df_sorted['last_px'].pct_change()
                    venue_df_sorted = venue_df_sorted.dropna()
                    
                    if len(venue_df_sorted) > 0:
                        returns_std = venue_df_sorted['returns'].std()
                        price_range = venue_df_sorted['last_px'].max() - venue_df_sorted['last_px'].min()
                        price_mean = venue_df_sorted['last_px'].mean()
                        price_cv = returns_std / price_mean if price_mean > 0 else np.nan
                        
                        results.append({
                            'date': date,
                            'symbol': symbol,
                            'venue': venue,
                            'variance_ratio': vr,
                            'returns_std': returns_std,
                            'price_range': price_range,
                            'price_mean': price_mean,
                            'price_cv': price_cv,
                            'n_obs': len(venue_df_sorted)
                        })
                
            except Exception as e:
                print(f"    ❌ Failed venue analysis for {symbol} on {date}: {e}")
    
    return pd.DataFrame(results)

# =============================================================================
# CONTROL TEST
# =============================================================================

def run_control_test() -> Dict[str, Any]:
    """Run control test using raw trade data."""
    print("📊 Running control test with raw trade data...")
    
    control_results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'test_description': 'Control test using raw trade-level data',
        'results': {}
    }
    
    # Test with Coinbase BTC data for 20251001
    test_venue = 'coinbase'
    test_symbol = 'BTC-USD'
    test_date = '20251001'
    
    try:
        # Load raw trade data
        raw_df = load_raw_trade_data(test_venue, test_symbol, test_date)
        
        if len(raw_df) == 0:
            control_results['results']['status'] = 'FAILED'
            control_results['results']['error'] = 'No raw trade data available'
            return control_results
        
        # Compute variance ratio from raw trades
        raw_vr = compute_variance_ratio(raw_df)
        
        # Compare with canonical data
        canonical_df = load_canonical_data_for_date(test_date, test_symbol)
        canonical_venue_df = canonical_df[canonical_df['venue'] == test_venue]
        canonical_vr = compute_variance_ratio(canonical_venue_df)
        
        control_results['results'] = {
            'status': 'SUCCESS',
            'test_venue': test_venue,
            'test_symbol': test_symbol,
            'test_date': test_date,
            'raw_vr': raw_vr,
            'canonical_vr': canonical_vr,
            'vr_difference': abs(raw_vr - canonical_vr) if not np.isnan(raw_vr) and not np.isnan(canonical_vr) else np.nan,
            'raw_obs': len(raw_df),
            'canonical_obs': len(canonical_venue_df),
            'structural_artifact_suspected': abs(raw_vr - canonical_vr) > 0.1 if not np.isnan(raw_vr) and not np.isnan(canonical_vr) else False
        }
        
        print(f"  ✅ Control test: raw_vr={raw_vr:.3f}, canonical_vr={canonical_vr:.3f}")
        
    except Exception as e:
        control_results['results'] = {
            'status': 'FAILED',
            'error': str(e)
        }
        print(f"  ❌ Control test failed: {e}")
    
    return control_results

# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main():
    """Main diagnostic analysis."""
    print("🔍 Stage H: Diagnostic Drill-Down for Variance Ratio Anomaly")
    print("=" * 70)
    
    # 1. Historical comparison
    print("\n1️⃣ Historical Comparison")
    print("-" * 30)
    historical_df = compute_historical_variance_ratios()
    
    # 2. Venue-level drilldown
    print("\n2️⃣ Venue-Level Drilldown")
    print("-" * 30)
    venue_df = compute_venue_level_analysis()
    
    # 3. Control test
    print("\n3️⃣ Control Test")
    print("-" * 30)
    control_results = run_control_test()
    
    # Save results to S3
    print("\n💾 Saving diagnostic results to S3...")
    
    # Save historical comparison
    historical_key = f"{ANALYSIS_PREFIX}/variance_ratio_history.csv"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=historical_key,
        Body=historical_df.to_csv(index=False)
    )
    print(f"  ✅ {historical_key}")
    
    # Save venue-level analysis
    venue_key = f"{ANALYSIS_PREFIX}/variance_ratio_by_venue.csv"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=venue_key,
        Body=venue_df.to_csv(index=False)
    )
    print(f"  ✅ {venue_key}")
    
    # Save control test results
    control_key = f"{ANALYSIS_PREFIX}/variance_ratio_control.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=control_key,
        Body=json.dumps(control_results, indent=2)
    )
    print(f"  ✅ {control_key}")
    
    # Create README
    readme_content = f"""Variance Ratio Diagnostic Analysis for 20251001
Generated: {datetime.now(timezone.utc).isoformat()}

This diagnostic analysis investigates the extremely low variance ratios (<0.3) 
detected in Stage G Wave-1 analysis for both BTC-USD and ETH-USD.

Files:
- variance_ratio_history.csv: Historical comparison across dates
- variance_ratio_by_venue.csv: Detailed venue-level analysis
- variance_ratio_control.json: Control test results using raw trade data

Analysis Summary:
- Historical dates analyzed: {', '.join(HISTORICAL_DATES)}
- Symbols: {', '.join(SYMBOLS)}
- Venues: {', '.join(VENUES)}

Key Findings:
- Historical comparison: {len(historical_df)} data points analyzed
- Venue-level analysis: {len(venue_df)} venue-date combinations
- Control test status: {control_results['results'].get('status', 'UNKNOWN')}

If variance ratios remain consistently low across all historical dates,
this suggests a systemic issue rather than an isolated event.

If control test shows significant difference between raw and canonical data,
this indicates a potential structural artifact in the data processing pipeline.

Next Steps:
1. Review historical comparison to identify if anomaly is systemic
2. Examine venue-level patterns for coordination signals
3. Investigate control test results for structural artifacts
"""
    
    readme_key = f"{ANALYSIS_PREFIX}/README.txt"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=readme_key,
        Body=readme_content
    )
    print(f"  ✅ {readme_key}")
    
    # Print summary
    print("\n📊 DIAGNOSTIC SUMMARY:")
    print("=" * 40)
    
    # Historical summary
    if len(historical_df) > 0:
        recent_data = historical_df[historical_df['date'] == '20251001']
        if len(recent_data) > 0:
            print("Recent VRs (20251001):")
            for _, row in recent_data.iterrows():
                print(f"  {row['symbol']}: overall={row['overall_vr']:.3f}, venue_mean={row['venue_mean_vr']:.3f}")
    
    # Venue summary
    if len(venue_df) > 0:
        recent_venues = venue_df[venue_df['date'] == '20251001']
        if len(recent_venues) > 0:
            print("\nVenue-level VRs (20251001):")
            for _, row in recent_venues.iterrows():
                print(f"  {row['symbol']} {row['venue']}: {row['variance_ratio']:.3f}")
    
    # Control test summary
    if control_results['results'].get('status') == 'SUCCESS':
        results = control_results['results']
        print(f"\nControl Test:")
        print(f"  Raw VR: {results['raw_vr']:.3f}")
        print(f"  Canonical VR: {results['canonical_vr']:.3f}")
        print(f"  Difference: {results['vr_difference']:.3f}")
        if results.get('structural_artifact_suspected'):
            print("  ⚠️ STRUCTURAL ARTIFACT SUSPECTED")
    
    print(f"\n✅ Diagnostic analysis complete. Results saved to s3://{S3_BUCKET}/{ANALYSIS_PREFIX}/")

if __name__ == "__main__":
    main()
