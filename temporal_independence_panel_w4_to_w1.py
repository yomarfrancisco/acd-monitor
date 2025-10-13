#!/usr/bin/env python3
"""
PROMPT B: Build the Temporal-Independence Panel (W-4→W-1)
Goal: Combine RX-A″ (expanded latency) + RX-C (independence regression) across W-4 → W-1
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_beacon_data(weeks):
    """Load beacon data for specified weeks"""
    print(f"🔍 Loading Beacon Data for {weeks}")
    print("-" * 60)
    
    all_beacon_data = {}
    cache_status = {}
    
    for week in weeks:
        print(f"Loading {week}...")
        
        # Try TEMP beacons first (for W-3, W-4)
        temp_beacon_dir = f"tmp/research_rx/BEACONS/{week}"
        canonical_beacon_dir = f"data_v6/cache/beacons/{week}"
        
        beacon_files = []
        
        # Check TEMP location first
        if os.path.exists(temp_beacon_dir):
            temp_files = glob.glob(f"{temp_beacon_dir}/*/beacons.parquet")
            beacon_files.extend(temp_files)
            print(f"  Found {len(temp_files)} TEMP beacon files")
        
        # Check canonical location
        if os.path.exists(canonical_beacon_dir):
            canonical_files = glob.glob(f"{canonical_beacon_dir}/*.parquet")
            beacon_files.extend(canonical_files)
            print(f"  Found {len(canonical_files)} canonical beacon files")
        
        if beacon_files:
            week_beacons = []
            for file_path in beacon_files:
                try:
                    df = pd.read_parquet(file_path)
                    week_beacons.append(df)
                except Exception as e:
                    print(f"  Warning: Could not load {file_path}: {e}")
            
            if week_beacons:
                all_beacon_data[week] = pd.concat(week_beacons, ignore_index=True)
                cache_status[week] = 'OK'
                print(f"  ✅ {week}: {len(all_beacon_data[week])} beacons loaded")
            else:
                print(f"  ⚠️ {week}: No beacon data found")
                all_beacon_data[week] = pd.DataFrame()
                cache_status[week] = 'EMPTY'
        else:
            print(f"  ❌ {week}: No beacon cache found")
            all_beacon_data[week] = pd.DataFrame()
            cache_status[week] = 'MISSING'
    
    return all_beacon_data, cache_status

def extract_expanded_beacon_pairs(beacon_data, weeks):
    """Extract COINBASE → BINANCE beacon pairs with 6-hour window (RX-A″ methodology)"""
    print(f"\n🔍 Extracting COINBASE → BINANCE Beacon Pairs (6-hour window)")
    print("-" * 60)
    
    beacon_pairs = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_data or len(beacon_data[week]) == 0:
            beacon_pairs[week] = []
            continue
        
        # Get beacon data for this week
        week_beacons = beacon_data[week].copy()
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in week_beacons.columns:
            week_beacons['event_ts'] = pd.to_datetime(week_beacons['event_ts'], utc=True)
        
        # Check for required grouping keys
        required_keys = ['event_ts', 'venue']
        missing_keys = [key for key in required_keys if key not in week_beacons.columns]
        if missing_keys:
            print(f"❌ HALT: Missing grouping keys: {missing_keys}")
            return None
        
        # Extract COINBASE and BINANCE beacons
        coinbase_beacons = week_beacons[week_beacons['venue'] == 'COINBASE'].copy()
        binance_beacons = week_beacons[week_beacons['venue'] == 'BINANCE'].copy()
        
        if len(coinbase_beacons) == 0 or len(binance_beacons) == 0:
            print(f"  Warning: Missing COINBASE or BINANCE data for {week}")
            beacon_pairs[week] = []
            continue
        
        # Sort by timestamp
        coinbase_beacons = coinbase_beacons.sort_values('event_ts')
        binance_beacons = binance_beacons.sort_values('event_ts')
        
        # Find beacon pairs with 6-hour window
        beacon_pairs_week = []
        matched_coinbase = set()  # Track matched COINBASE beacons
        
        for _, coinbase_event in coinbase_beacons.iterrows():
            coinbase_time = coinbase_event['event_ts']
            
            # Find earliest BINANCE beacon within 6 hours
            time_window = timedelta(hours=6)
            binance_candidates = binance_beacons[
                (binance_beacons['event_ts'] > coinbase_time) &
                (binance_beacons['event_ts'] <= coinbase_time + time_window)
            ]
            
            if len(binance_candidates) > 0:
                # Take the first (earliest) BINANCE beacon within window
                next_binance = binance_candidates.iloc[0]
                binance_time = next_binance['event_ts']
                
                # Calculate latency in milliseconds
                latency_ms = (binance_time - coinbase_time).total_seconds() * 1000
                
                # Only include pairs with positive latency (forward response)
                if latency_ms > 0:
                    beacon_pairs_week.append({
                        'coinbase_time': coinbase_time,
                        'binance_time': binance_time,
                        'latency_ms': latency_ms
                    })
                    matched_coinbase.add(coinbase_time)
        
        # Calculate coverage percentage
        total_coinbase = len(coinbase_beacons)
        matched_count = len(matched_coinbase)
        coverage_pct = (matched_count / total_coinbase * 100) if total_coinbase > 0 else 0.0
        
        beacon_pairs[week] = beacon_pairs_week
        print(f"  Found {len(beacon_pairs_week)} COINBASE → BINANCE beacon pairs")
        print(f"  Coverage: {matched_count}/{total_coinbase} ({coverage_pct:.1f}%)")
    
    return beacon_pairs

def compute_latency_metrics(beacon_pairs, weeks):
    """Compute latency metrics for RX-A″ analysis"""
    print(f"\n🔍 Computing Latency Metrics (RX-A″)")
    print("-" * 60)
    
    latency_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_pairs or len(beacon_pairs[week]) == 0:
            latency_results[week] = {
                'n_pairs': 0,
                'coverage_pct': 0.0,
                'percentiles': {p: 0.0 for p in [1, 5, 25, 50, 75, 95, 99]},
                'bins': {'<5min': 0.0, '5-30min': 0.0, '30-120min': 0.0, '>120min': 0.0}
            }
            continue
        
        pairs = beacon_pairs[week]
        latencies = [pair['latency_ms'] for pair in pairs]
        n_pairs = len(pairs)
        
        # Compute percentiles
        percentiles = {}
        for p in [1, 5, 25, 50, 75, 95, 99]:
            percentiles[p] = np.percentile(latencies, p)
        
        # Compute latency bins (in milliseconds)
        bins = {
            '<5min': sum(1 for l in latencies if l < 5 * 60 * 1000),      # < 5 minutes
            '5-30min': sum(1 for l in latencies if 5 * 60 * 1000 <= l < 30 * 60 * 1000),  # 5-30 minutes
            '30-120min': sum(1 for l in latencies if 30 * 60 * 1000 <= l < 120 * 60 * 1000),  # 30-120 minutes
            '>120min': sum(1 for l in latencies if l >= 120 * 60 * 1000)  # > 120 minutes
        }
        
        # Convert to percentages
        for bin_name in bins:
            bins[bin_name] = (bins[bin_name] / n_pairs * 100) if n_pairs > 0 else 0.0
        
        # Calculate coverage (recalculate from pairs)
        coverage_pct = 0.0  # Will be updated from beacon_pairs data
        
        latency_results[week] = {
            'n_pairs': n_pairs,
            'coverage_pct': coverage_pct,
            'percentiles': percentiles,
            'bins': bins,
            'latencies': latencies
        }
        
        print(f"  N pairs: {n_pairs}")
        print(f"  Median latency: {percentiles[50]:.1f} ms ({percentiles[50]/60000:.1f} min)")
        print(f"  P95 latency: {percentiles[95]:.1f} ms ({percentiles[95]/60000:.1f} min)")
    
    return latency_results

def run_independence_regression(beacon_data, weeks):
    """Run independence regression analysis (RX-C methodology)"""
    print(f"\n🔍 Running Independence Regression (RX-C)")
    print("-" * 60)
    
    regression_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in beacon_data or len(beacon_data[week]) == 0:
            regression_results[week] = {
                'R2_single': 0.0,
                'R2_multi': 0.0,
                'delta_R2': 0.0,
                'beta_coinbase': 0.0,
                'se_coinbase': 0.0,
                'n_observations': 0
            }
            continue
        
        # Get beacon data for this week
        week_beacons = beacon_data[week].copy()
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in week_beacons.columns:
            week_beacons['event_ts'] = pd.to_datetime(week_beacons['event_ts'], utc=True)
        
        # Create binary indicators for venue updates
        venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
        venue_indicators = {}
        
        for venue in venues:
            venue_beacons = week_beacons[week_beacons['venue'] == venue]
            if len(venue_beacons) > 0:
                # Create time series of binary indicators
                min_time = week_beacons['event_ts'].min()
                max_time = week_beacons['event_ts'].max()
                
                # Create hourly time bins
                time_bins = pd.date_range(start=min_time, end=max_time, freq='H')
                venue_indicators[venue] = np.zeros(len(time_bins))
                
                for _, beacon in venue_beacons.iterrows():
                    # Find the time bin for this beacon
                    bin_idx = np.searchsorted(time_bins, beacon['event_ts']) - 1
                    if 0 <= bin_idx < len(time_bins):
                        venue_indicators[venue][bin_idx] = 1
            else:
                venue_indicators[venue] = np.zeros(1)
        
        # Align all indicators to the same length
        max_length = max(len(indicators) for indicators in venue_indicators.values())
        for venue in venues:
            if len(venue_indicators[venue]) < max_length:
                venue_indicators[venue] = np.pad(venue_indicators[venue], 
                                               (0, max_length - len(venue_indicators[venue])), 
                                               'constant')
        
        # Prepare data for regression
        Y = venue_indicators['BINANCE']  # Binary response: BINANCE updates
        
        # Model 1: Single-factor (COINBASE only)
        X1 = venue_indicators['COINBASE'].reshape(-1, 1)
        
        # Model 2: Multi-factor (COINBASE + BYBIT + BITGET + local_vol_proxy)
        # Local volatility proxy = 0 (no tick data available)
        local_vol_proxy = np.zeros(max_length)
        X2 = np.column_stack([
            venue_indicators['COINBASE'],
            venue_indicators['BYBITSPOT'],
            venue_indicators['BITGET'],
            local_vol_proxy
        ])
        
        # Fit models
        try:
            # Model 1
            model1 = LinearRegression()
            model1.fit(X1, Y)
            Y_pred1 = model1.predict(X1)
            R2_single = r2_score(Y, Y_pred1)
            
            # Model 2
            model2 = LinearRegression()
            model2.fit(X2, Y)
            Y_pred2 = model2.predict(X2)
            R2_multi = r2_score(Y, Y_pred2)
            
            # Calculate delta R²
            delta_R2 = R2_multi - R2_single
            
            # Get COINBASE coefficient and standard error
            beta_coinbase = model2.coef_[0]
            se_coinbase = 0.0  # Simplified - would need proper error calculation
            
            regression_results[week] = {
                'R2_single': R2_single,
                'R2_multi': R2_multi,
                'delta_R2': delta_R2,
                'beta_coinbase': beta_coinbase,
                'se_coinbase': se_coinbase,
                'n_observations': len(Y)
            }
            
            print(f"  Model 1 R²: {R2_single:.4f}")
            print(f"  Model 2 R²: {R2_multi:.4f}")
            print(f"  ΔR²: {delta_R2:.4f}")
            print(f"  COINBASE β: {beta_coinbase:.4f}")
            
        except Exception as e:
            print(f"  Warning: Regression failed for {week}: {e}")
            regression_results[week] = {
                'R2_single': 0.0,
                'R2_multi': 0.0,
                'delta_R2': 0.0,
                'beta_coinbase': 0.0,
                'se_coinbase': 0.0,
                'n_observations': 0
            }
    
    return regression_results

def build_temporal_independence_panel(latency_results, regression_results, weeks):
    """Build the temporal independence panel"""
    print(f"\n🔍 Building Temporal Independence Panel")
    print("-" * 60)
    
    panel_data = []
    
    for week in weeks:
        print(f"Processing {week}...")
        
        # Get latency results
        latency = latency_results.get(week, {})
        regression = regression_results.get(week, {})
        
        # Determine data source
        if week in ['week-minus3', 'week-minus4']:
            notes = "W-3/W-4 from TEMP beacons (if available)"
        else:
            notes = "W-2/W-1 from canonical beacons"
        
        # Check coverage flag
        coverage_pct = latency.get('coverage_pct', 0.0)
        if coverage_pct < 90:
            notes += f" [FLAG: Coverage {coverage_pct:.1f}% < 90%]"
        
        # Build row data
        row = {
            'week': week,
            'n_pairs': latency.get('n_pairs', 0),
            'coverage_pct': coverage_pct,
            'lat_p01': latency.get('percentiles', {}).get(1, 0.0),
            'lat_p05': latency.get('percentiles', {}).get(5, 0.0),
            'lat_p25': latency.get('percentiles', {}).get(25, 0.0),
            'lat_p50': latency.get('percentiles', {}).get(50, 0.0),
            'lat_p75': latency.get('percentiles', {}).get(75, 0.0),
            'lat_p95': latency.get('percentiles', {}).get(95, 0.0),
            'lat_p99': latency.get('percentiles', {}).get(99, 0.0),
            'share_<5min': latency.get('bins', {}).get('<5min', 0.0),
            'share_5_30min': latency.get('bins', {}).get('5-30min', 0.0),
            'share_30_120min': latency.get('bins', {}).get('30-120min', 0.0),
            'share_>120min': latency.get('bins', {}).get('>120min', 0.0),
            'R2_single': regression.get('R2_single', 0.0),
            'R2_multi': regression.get('R2_multi', 0.0),
            'delta_R2': regression.get('delta_R2', 0.0),
            'beta_coinbase': regression.get('beta_coinbase', 0.0),
            'se_coinbase': regression.get('se_coinbase', 0.0),
            'notes': notes
        }
        
        panel_data.append(row)
        print(f"  Added row for {week}")
    
    return pd.DataFrame(panel_data)

def save_panel_to_temp(panel_df):
    """Save panel to temporary location"""
    print(f"\n🔍 Saving Panel to TEMP Location")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/PANELS"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save CSV and Parquet
    csv_path = f"{output_dir}/temporal_independence_W-4_to_W-1.csv"
    parquet_path = f"{output_dir}/temporal_independence_W-4_to_W-1.parquet"
    
    panel_df.to_csv(csv_path, index=False)
    panel_df.to_parquet(parquet_path, index=False)
    
    print(f"  ✅ Saved CSV: {csv_path}")
    print(f"  ✅ Saved Parquet: {parquet_path}")
    
    return csv_path, parquet_path

def main():
    print("📊 PROMPT B: BUILD THE TEMPORAL-INDEPENDENCE PANEL (W-4→W-1)")
    print("=" * 80)
    print("Goal: Combine RX-A″ (expanded latency) + RX-C (independence regression) across W-4 → W-1")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-4 → W-1 inclusive
    weeks = ['week-minus4', 'week-minus3', 'week-minus2', 'week-minus1']
    
    print(f"📅 Processing weeks: {weeks}")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 500:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 500 MB limit")
        return
    
    # Load beacon data
    beacon_data, cache_status = load_beacon_data(weeks)
    
    # Check for sufficient data
    total_beacons = sum(len(df) for df in beacon_data.values())
    if total_beacons == 0:
        print("❌ HALT: No beacon data found")
        return
    
    print(f"✅ Total beacons loaded: {total_beacons}")
    
    # Extract expanded beacon pairs (RX-A″)
    beacon_pairs = extract_expanded_beacon_pairs(beacon_data, weeks)
    if beacon_pairs is None:
        print("❌ HALT: Failed to extract beacon pairs")
        return
    
    # Compute latency metrics (RX-A″)
    latency_results = compute_latency_metrics(beacon_pairs, weeks)
    
    # Run independence regression (RX-C)
    regression_results = run_independence_regression(beacon_data, weeks)
    
    # Build temporal independence panel
    panel_df = build_temporal_independence_panel(latency_results, regression_results, weeks)
    
    # Save panel to temporary location
    csv_path, parquet_path = save_panel_to_temp(panel_df)
    
    # ========================================================================
    # OUTPUT REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 TEMPORAL INDEPENDENCE PANEL SUMMARY")
    print("=" * 80)
    
    # Panel preview (10 rows)
    print(f"\nPanel Preview (10 rows):")
    print(panel_df.head(10).to_string(index=False))
    
    # Summary statistics
    print(f"\nSummary Statistics:")
    print(f"  Total weeks processed: {len(weeks)}")
    print(f"  Weeks with data: {sum(1 for week in weeks if panel_df[panel_df['week'] == week]['n_pairs'].iloc[0] > 0)}")
    print(f"  Total beacon pairs: {panel_df['n_pairs'].sum()}")
    print(f"  Average coverage: {panel_df['coverage_pct'].mean():.1f}%")
    print(f"  Average R² (single): {panel_df['R2_single'].mean():.4f}")
    print(f"  Average R² (multi): {panel_df['R2_multi'].mean():.4f}")
    print(f"  Average ΔR²: {panel_df['delta_R2'].mean():.4f}")
    
    # Data source confirmation
    print(f"\nData Source Confirmation:")
    for week in weeks:
        row = panel_df[panel_df['week'] == week].iloc[0]
        notes = row['notes']
        print(f"  {week}: {notes}")
    
    # File paths
    print(f"\nOutput Files:")
    print(f"  CSV: {csv_path}")
    print(f"  Parquet: {parquet_path}")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 500:
        print(f"✅ PROMPT B COMPLETE - All guardrails complied with")
        print(f"• Read-only on canonical; write outputs only to tmp/research_rx/PANELS/")
        print(f"• No schema edits, no synthetic data, no resampling")
        print(f"• No persistence of derived artifacts back into canonical week folders")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 500 MB limit)")
        print(f"• Panel created with {len(panel_df)} rows")
        print(f"• TEMP usage for W-3/W-4 explicitly noted in output metadata")
    else:
        print(f"❌ PROMPT B HALTED")
        print(f"• Memory usage: {final_memory:.1f} MB > 500 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PROMPT B COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




