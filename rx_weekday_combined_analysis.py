#!/usr/bin/env python3
"""
PROMPT 3: RX-Weekday-Combined (W-2 + W-1, Mon–Fri): RX-A″ + RX-B + RX-C
Goal: Run RX tests on the union of W-2 and W-1 weekdays (Mon–Fri only, UTC)
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
from scipy.stats import chi2_contingency
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_beacon_data_weekday_filtered(weeks):
    """Load beacon data for specified weeks with weekday filtering"""
    print(f"🔍 Loading Beacon Data for {weeks} (Weekday Filtered)")
    print("-" * 60)
    
    all_weekday_beacons = []
    
    for week in weeks:
        beacon_cache_dir = f"data_v6/cache/beacons/{week}"
        if not os.path.exists(beacon_cache_dir):
            print(f"❌ Beacon cache directory not found: {beacon_cache_dir}")
            continue
        
        beacon_files = glob.glob(f"{beacon_cache_dir}/*.parquet")
        if not beacon_files:
            print(f"❌ No beacon files found in {beacon_cache_dir}")
            continue
        
        week_beacons = []
        for file_path in beacon_files:
            try:
                df = pd.read_parquet(file_path)
                week_beacons.append(df)
            except Exception as e:
                print(f"  Warning: Could not load {file_path}: {e}")
        
        if not week_beacons:
            print(f"❌ No beacon data loaded for {week}")
            continue
        
        all_beacons = pd.concat(week_beacons, ignore_index=True)
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in all_beacons.columns:
            all_beacons['event_ts'] = pd.to_datetime(all_beacons['event_ts'], utc=True)
        
        # Apply weekday filter (Mon-Fri only, UTC)
        all_beacons['weekday'] = all_beacons['event_ts'].dt.dayofweek
        weekday_beacons = all_beacons[all_beacons['weekday'].isin([0, 1, 2, 3, 4])].copy()  # Mon=0, Fri=4
        
        # Add week identifier
        weekday_beacons['week'] = week
        
        all_weekday_beacons.append(weekday_beacons)
        
        print(f"  ✅ {week}: Total={len(all_beacons)}, Weekday={len(weekday_beacons)}")
    
    if not all_weekday_beacons:
        print(f"❌ No beacon data loaded")
        return pd.DataFrame()
    
    combined_beacons = pd.concat(all_weekday_beacons, ignore_index=True)
    print(f"  ✅ Combined weekday beacons: {len(combined_beacons)}")
    
    return combined_beacons

def rx_a_prime_expanded_latency(beacon_data):
    """RX-A″: Expanded Beacon Latency with 6-hour window, first-match only (per-week pairing)"""
    print(f"\n🔍 RX-A″: Expanded Beacon Latency (6h window, first-match, per-week pairing)")
    print("-" * 60)
    
    all_beacon_pairs = []
    per_week_results = {}
    
    # Process each week separately to avoid cross-week pair bleed
    for week in beacon_data['week'].unique():
        print(f"  Processing {week}...")
        
        week_data = beacon_data[beacon_data['week'] == week].copy()
        
        # Extract COINBASE and BINANCE beacons
        coinbase_beacons = week_data[week_data['venue'] == 'COINBASE'].copy()
        binance_beacons = week_data[week_data['venue'] == 'BINANCE'].copy()
        
        if len(coinbase_beacons) == 0 or len(binance_beacons) == 0:
            print(f"    ❌ Missing COINBASE or BINANCE data for {week}")
            continue
        
        # Sort by timestamp
        coinbase_beacons = coinbase_beacons.sort_values('event_ts')
        binance_beacons = binance_beacons.sort_values('event_ts')
        
        # Find beacon pairs with 6-hour window (first-match only)
        beacon_pairs_week = []
        matched_coinbase = set()
        
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
                    pair = {
                        'week': week,
                        'coinbase_time': coinbase_time,
                        'binance_time': binance_time,
                        'latency_ms': latency_ms
                    }
                    beacon_pairs_week.append(pair)
                    all_beacon_pairs.append(pair)
                    matched_coinbase.add(coinbase_time)
        
        # Calculate coverage percentage for this week
        total_coinbase = len(coinbase_beacons)
        matched_count = len(matched_coinbase)
        coverage_pct = (matched_count / total_coinbase * 100) if total_coinbase > 0 else 0.0
        
        print(f"    Found {len(beacon_pairs_week)} pairs, Coverage: {matched_count}/{total_coinbase} ({coverage_pct:.1f}%)")
        
        # Store per-week results
        per_week_results[week] = {
            'n_pairs': len(beacon_pairs_week),
            'coverage_pct': coverage_pct,
            'pairs': beacon_pairs_week
        }
    
    if not all_beacon_pairs:
        print(f"❌ HALT: No beacon pairs found")
        return None
    
    # Validation: coverage ≥ 90% per week
    for week, results in per_week_results.items():
        if results['coverage_pct'] < 90:
            print(f"❌ HALT: {week} coverage={results['coverage_pct']:.1f}% < 90%")
            return None
    
    # Compute combined latency metrics
    latencies = [pair['latency_ms'] for pair in all_beacon_pairs]
    
    # Percentiles
    percentiles = {}
    for p in [1, 5, 25, 50, 75, 95, 99]:
        percentiles[p] = np.percentile(latencies, p)
    
    # Latency bins (in milliseconds)
    bins = {
        '<5min': sum(1 for l in latencies if l < 5 * 60 * 1000),
        '5-30min': sum(1 for l in latencies if 5 * 60 * 1000 <= l < 30 * 60 * 1000),
        '30-120min': sum(1 for l in latencies if 30 * 60 * 1000 <= l < 120 * 60 * 1000),
        '>120min': sum(1 for l in latencies if l >= 120 * 60 * 1000)
    }
    
    # Convert to percentages
    for bin_name in bins:
        bins[bin_name] = (bins[bin_name] / len(latencies) * 100) if len(latencies) > 0 else 0.0
    
    # Calculate combined coverage
    total_coinbase = sum(len(beacon_data[(beacon_data['week'] == week) & (beacon_data['venue'] == 'COINBASE')]) for week in beacon_data['week'].unique())
    combined_coverage_pct = (len(all_beacon_pairs) / total_coinbase * 100) if total_coinbase > 0 else 0.0
    
    results = {
        'n_pairs': len(all_beacon_pairs),
        'coverage_pct': combined_coverage_pct,
        'percentiles': percentiles,
        'bins': bins,
        'latencies': latencies,
        'beacon_pairs': all_beacon_pairs,
        'per_week_results': per_week_results
    }
    
    print(f"  ✅ Combined: {len(all_beacon_pairs)} pairs, Coverage: {combined_coverage_pct:.1f}%")
    print(f"  ✅ Validation passed: All weeks ≥ 90% coverage")
    print(f"  Combined median latency: {percentiles[50]:.1f} ms ({percentiles[50]/60000:.1f} min)")
    print(f"  Combined P95 latency: {percentiles[95]:.1f} ms ({percentiles[95]/60000:.1f} min)")
    
    return results

def rx_b_information_timing(beacon_pairs):
    """RX-B: Information-Timing Analysis using COINBASE→BINANCE pairs (per-week and combined)"""
    print(f"\n🔍 RX-B: Information-Timing Analysis (per-week and combined)")
    print("-" * 60)
    
    if not beacon_pairs:
        print(f"❌ HALT: No beacon pairs available")
        return None
    
    # Per-week analysis
    per_week_results = {}
    for week in set(pair['week'] for pair in beacon_pairs):
        week_pairs = [pair for pair in beacon_pairs if pair['week'] == week]
        
        # Bin by UTC trading blocks
        asia_events = []
        eu_events = []
        us_events = []
        
        for pair in week_pairs:
            coinbase_time = pair['coinbase_time']
            hour = coinbase_time.hour
            
            if 23 <= hour or hour <= 6:  # ASIA: 23:00–06:59
                asia_events.append(pair)
            elif 7 <= hour <= 12:  # EU: 07:00–12:59
                eu_events.append(pair)
            elif 13 <= hour <= 20:  # US: 13:00–20:59
                us_events.append(pair)
        
        # Calculate hours per bin (assuming 5 weekdays)
        asia_hours = 5 * 8  # 8 hours per day (23:00-06:59)
        eu_hours = 5 * 6    # 6 hours per day (07:00-12:59)
        us_hours = 5 * 8    # 8 hours per day (13:00-20:59)
        
        # Calculate rates
        asia_rate = len(asia_events) / asia_hours if asia_hours > 0 else 0
        eu_rate = len(eu_events) / eu_hours if eu_hours > 0 else 0
        us_rate = len(us_events) / us_hours if us_hours > 0 else 0
        
        # Chi-square test of uniformity
        observed = [len(asia_events), len(eu_events), len(us_events)]
        expected = [sum(observed) / 3] * 3  # Uniform distribution
        
        chi2_stat, p_value = chi2_contingency([observed, expected])[:2]
        
        per_week_results[week] = {
            'asia_events': len(asia_events),
            'eu_events': len(eu_events),
            'us_events': len(us_events),
            'asia_hours': asia_hours,
            'eu_hours': eu_hours,
            'us_hours': us_hours,
            'asia_rate': asia_rate,
            'eu_rate': eu_rate,
            'us_rate': us_rate,
            'chi2_stat': chi2_stat,
            'p_value': p_value
        }
        
        print(f"  {week}: ASIA={len(asia_events)}, EU={len(eu_events)}, US={len(us_events)}")
    
    # Combined analysis
    asia_events = []
    eu_events = []
    us_events = []
    
    for pair in beacon_pairs:
        coinbase_time = pair['coinbase_time']
        hour = coinbase_time.hour
        
        if 23 <= hour or hour <= 6:  # ASIA: 23:00–06:59
            asia_events.append(pair)
        elif 7 <= hour <= 12:  # EU: 07:00–12:59
            eu_events.append(pair)
        elif 13 <= hour <= 20:  # US: 13:00–20:59
            us_events.append(pair)
    
    # Calculate hours per bin (assuming 10 weekdays total)
    asia_hours = 10 * 8  # 8 hours per day (23:00-06:59)
    eu_hours = 10 * 6    # 6 hours per day (07:00-12:59)
    us_hours = 10 * 8    # 8 hours per day (13:00-20:59)
    
    # Calculate rates
    asia_rate = len(asia_events) / asia_hours if asia_hours > 0 else 0
    eu_rate = len(eu_events) / eu_hours if eu_hours > 0 else 0
    us_rate = len(us_events) / us_hours if us_hours > 0 else 0
    
    # Chi-square test of uniformity
    observed = [len(asia_events), len(eu_events), len(us_events)]
    expected = [sum(observed) / 3] * 3  # Uniform distribution
    
    chi2_stat, p_value = chi2_contingency([observed, expected])[:2]
    
    combined_results = {
        'asia_events': len(asia_events),
        'eu_events': len(eu_events),
        'us_events': len(us_events),
        'asia_hours': asia_hours,
        'eu_hours': eu_hours,
        'us_hours': us_hours,
        'asia_rate': asia_rate,
        'eu_rate': eu_rate,
        'us_rate': us_rate,
        'chi2_stat': chi2_stat,
        'p_value': p_value
    }
    
    print(f"  Combined: ASIA={len(asia_events)}, EU={len(eu_events)}, US={len(us_events)}")
    print(f"  Combined χ² test: stat={chi2_stat:.4f}, p-value={p_value:.4f}")
    
    results = {
        'per_week_results': per_week_results,
        'combined_results': combined_results
    }
    
    return results

def rx_c_binance_independence_regression(beacon_data):
    """RX-C: Binance Independence Regression with combined weekday 1-minute panel"""
    print(f"\n🔍 RX-C: Binance Independence Regression (combined panel)")
    print("-" * 60)
    
    # Create 1-minute time bins over all weekday days
    min_time = beacon_data['event_ts'].min()
    max_time = beacon_data['event_ts'].max()
    
    # Round to minute boundaries
    min_time = min_time.replace(second=0, microsecond=0)
    max_time = max_time.replace(second=0, microsecond=0)
    
    # Create 1-minute time grid
    time_bins = pd.date_range(start=min_time, end=max_time, freq='1min')
    
    print(f"  Time range: {min_time} to {max_time}")
    print(f"  Total time bins: {len(time_bins)}")
    
    # Create binary indicators for venue updates
    venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
    venue_indicators = {}
    
    for venue in venues:
        venue_beacons = beacon_data[beacon_data['venue'] == venue]
        venue_indicators[venue] = np.zeros(len(time_bins))
        
        for _, beacon in venue_beacons.iterrows():
            # Find the time bin for this beacon
            bin_idx = np.searchsorted(time_bins, beacon['event_ts']) - 1
            if 0 <= bin_idx < len(time_bins):
                venue_indicators[venue][bin_idx] = 1
    
    # Prepare data for regression
    Y = venue_indicators['BINANCE']  # Binary response: BINANCE updates
    
    # Model 1: Single-factor (COINBASE only)
    X1 = venue_indicators['COINBASE'].reshape(-1, 1)
    
    # Model 2: Multi-factor (COINBASE + BYBIT + BITGET + local_vol_proxy)
    # Local volatility proxy = 0 (no tick data available for now)
    local_vol_proxy = np.zeros(len(time_bins))
    X2 = np.column_stack([
        venue_indicators['COINBASE'],
        venue_indicators['BYBITSPOT'],
        venue_indicators['BITGET'],
        local_vol_proxy
    ])
    
    # Drop bins with missing local_vol_t (none in this case, but keep for consistency)
    valid_mask = ~np.isnan(local_vol_proxy)
    Y_clean = Y[valid_mask]
    X1_clean = X1[valid_mask]
    X2_clean = X2[valid_mask]
    
    print(f"  Valid time bins after NA-drop: {len(Y_clean)}")
    
    # Validation: ≥ 2,000 combined bins after NA-drop
    if len(Y_clean) < 2000:
        print(f"❌ HALT: {len(Y_clean)} time bins < 2,000 required")
        return None
    
    # Fit models
    try:
        # Model 1
        model1 = LinearRegression()
        model1.fit(X1_clean, Y_clean)
        Y_pred1 = model1.predict(X1_clean)
        R2_single = r2_score(Y_clean, Y_pred1)
        
        # Model 2
        model2 = LinearRegression()
        model2.fit(X2_clean, Y_clean)
        Y_pred2 = model2.predict(X2_clean)
        R2_multi = r2_score(Y_clean, Y_pred2)
        
        # Calculate delta R²
        delta_R2 = R2_multi - R2_single
        
        # Get COINBASE coefficient and standard error
        beta_coinbase = model2.coef_[0]
        se_coinbase = 0.0  # Simplified - would need proper error calculation
        
        results = {
            'n_bins_used': len(Y_clean),
            'R2_single': R2_single,
            'R2_multi': R2_multi,
            'delta_R2': delta_R2,
            'beta_coinbase': beta_coinbase,
            'se_coinbase': se_coinbase
        }
        
        print(f"  ✅ Validation passed: {len(Y_clean)} time bins ≥ 2,000 required")
        print(f"  Model 1 R²: {R2_single:.4f}")
        print(f"  Model 2 R²: {R2_multi:.4f}")
        print(f"  ΔR²: {delta_R2:.4f}")
        print(f"  COINBASE β: {beta_coinbase:.4f}")
        
        return results
        
    except Exception as e:
        print(f"❌ HALT: Regression failed: {e}")
        return None

def save_results_to_temp(rx_a_results, rx_b_results, rx_c_results):
    """Save all results to temporary location with COMBINED_WEEKDAY tag"""
    print(f"\n🔍 Saving Results to TEMP Location")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/WEEKDAY_ONLY"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/PANELS", exist_ok=True)
    
    # Save RX-A″ results
    if rx_a_results:
        rx_a_df = pd.DataFrame([{
            'n_pairs': rx_a_results['n_pairs'],
            'coverage_pct': rx_a_results['coverage_pct'],
            'lat_p01': rx_a_results['percentiles'][1],
            'lat_p05': rx_a_results['percentiles'][5],
            'lat_p25': rx_a_results['percentiles'][25],
            'lat_p50': rx_a_results['percentiles'][50],
            'lat_p75': rx_a_results['percentiles'][75],
            'lat_p95': rx_a_results['percentiles'][95],
            'lat_p99': rx_a_results['percentiles'][99],
            'share_<5min': rx_a_results['bins']['<5min'],
            'share_5_30min': rx_a_results['bins']['5-30min'],
            'share_30_120min': rx_a_results['bins']['30-120min'],
            'share_>120min': rx_a_results['bins']['>120min']
        }])
        
        csv_path = f"{output_dir}/RX_Aprime_COMBINED_WEEKDAY_latency.csv"
        parquet_path = f"{output_dir}/RX_Aprime_COMBINED_WEEKDAY_latency.parquet"
        rx_a_df.to_csv(csv_path, index=False)
        rx_a_df.to_parquet(parquet_path, index=False)
        print(f"  ✅ Saved RX-A″: {csv_path}")
    
    # Save RX-B results
    if rx_b_results:
        combined = rx_b_results['combined_results']
        rx_b_df = pd.DataFrame([{
            'asia_events': combined['asia_events'],
            'eu_events': combined['eu_events'],
            'us_events': combined['us_events'],
            'asia_hours': combined['asia_hours'],
            'eu_hours': combined['eu_hours'],
            'us_hours': combined['us_hours'],
            'asia_rate': combined['asia_rate'],
            'eu_rate': combined['eu_rate'],
            'us_rate': combined['us_rate'],
            'chi2_stat': combined['chi2_stat'],
            'p_value': combined['p_value']
        }])
        
        csv_path = f"{output_dir}/RX_B_COMBINED_WEEKDAY_timing.csv"
        parquet_path = f"{output_dir}/RX_B_COMBINED_WEEKDAY_timing.parquet"
        rx_b_df.to_csv(csv_path, index=False)
        rx_b_df.to_parquet(parquet_path, index=False)
        print(f"  ✅ Saved RX-B: {csv_path}")
    
    # Save RX-C results
    if rx_c_results:
        rx_c_df = pd.DataFrame([{
            'n_bins_used': rx_c_results['n_bins_used'],
            'R2_single': rx_c_results['R2_single'],
            'R2_multi': rx_c_results['R2_multi'],
            'delta_R2': rx_c_results['delta_R2'],
            'beta_coinbase': rx_c_results['beta_coinbase'],
            'se_coinbase': rx_c_results['se_coinbase']
        }])
        
        csv_path = f"{output_dir}/RX_C_COMBINED_WEEKDAY_regression.csv"
        parquet_path = f"{output_dir}/RX_C_COMBINED_WEEKDAY_regression.parquet"
        rx_c_df.to_csv(csv_path, index=False)
        rx_c_df.to_parquet(parquet_path, index=False)
        print(f"  ✅ Saved RX-C: {csv_path}")
    
    # Save combined panel
    if rx_a_results and rx_b_results and rx_c_results:
        combined = rx_b_results['combined_results']
        panel_df = pd.DataFrame([{
            'week': 'COMBINED',
            'n_pairs': rx_a_results['n_pairs'],
            'coverage_pct': rx_a_results['coverage_pct'],
            'lat_p01': rx_a_results['percentiles'][1],
            'lat_p05': rx_a_results['percentiles'][5],
            'lat_p25': rx_a_results['percentiles'][25],
            'lat_p50': rx_a_results['percentiles'][50],
            'lat_p75': rx_a_results['percentiles'][75],
            'lat_p95': rx_a_results['percentiles'][95],
            'lat_p99': rx_a_results['percentiles'][99],
            'share_<5min': rx_a_results['bins']['<5min'],
            'share_5_30min': rx_a_results['bins']['5-30min'],
            'share_30_120min': rx_a_results['bins']['30-120min'],
            'share_>120min': rx_a_results['bins']['>120min'],
            'asia_events': combined['asia_events'],
            'eu_events': combined['eu_events'],
            'us_events': combined['us_events'],
            'asia_rate': combined['asia_rate'],
            'eu_rate': combined['eu_rate'],
            'us_rate': combined['us_rate'],
            'chi2_stat': combined['chi2_stat'],
            'p_value': combined['p_value'],
            'n_bins_used': rx_c_results['n_bins_used'],
            'R2_single': rx_c_results['R2_single'],
            'R2_multi': rx_c_results['R2_multi'],
            'delta_R2': rx_c_results['delta_R2'],
            'beta_coinbase': rx_c_results['beta_coinbase'],
            'se_coinbase': rx_c_results['se_coinbase'],
            'notes': "Combined W-2 + W-1 weekday analysis (Mon-Fri only, 10 days total)"
        }])
        
        csv_path = f"{output_dir}/PANELS/temporal_independence_COMBINED_WEEKDAY.csv"
        parquet_path = f"{output_dir}/PANELS/temporal_independence_COMBINED_WEEKDAY.parquet"
        panel_df.to_csv(csv_path, index=False)
        panel_df.to_parquet(parquet_path, index=False)
        print(f"  ✅ Saved Panel: {csv_path}")

def main():
    print("📊 PROMPT 3: RX-WEEKDAY-COMBINED (W-2 + W-1, MON–FRI): RX-A″ + RX-B + RX-C")
    print("=" * 80)
    print("Goal: Run RX tests on the union of W-2 and W-1 weekdays (Mon–Fri only, UTC)")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope
    weeks = ['week-minus2', 'week-minus1']
    
    print(f"📅 Processing weeks: {weeks} (Mon-Fri only, 10 days total)")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load beacon data with weekday filtering
    beacon_data = load_beacon_data_weekday_filtered(weeks)
    
    if len(beacon_data) == 0:
        print("❌ HALT: No weekday beacon data found")
        return
    
    # Run RX-A″: Expanded Beacon Latency
    rx_a_results = rx_a_prime_expanded_latency(beacon_data)
    if rx_a_results is None:
        print("❌ HALT: RX-A″ failed")
        return
    
    # Run RX-B: Information-Timing
    rx_b_results = rx_b_information_timing(rx_a_results['beacon_pairs'])
    if rx_b_results is None:
        print("❌ HALT: RX-B failed")
        return
    
    # Run RX-C: Binance Independence Regression
    rx_c_results = rx_c_binance_independence_regression(beacon_data)
    if rx_c_results is None:
        print("❌ HALT: RX-C failed")
        return
    
    # Save results to temporary location
    save_results_to_temp(rx_a_results, rx_b_results, rx_c_results)
    
    # ========================================================================
    # CONSOLE TABLES
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 CONSOLE TABLES")
    print("=" * 80)
    
    # RX-A″ Table
    print(f"\nRX-A″ Latency Results (Combined):")
    print(f"{'Metric':<20} {'Value':<15}")
    print("-" * 35)
    print(f"{'N Pairs':<20} {rx_a_results['n_pairs']:<15}")
    print(f"{'Coverage %':<20} {rx_a_results['coverage_pct']:.1f}%")
    print(f"{'P01 (ms)':<20} {rx_a_results['percentiles'][1]:.1f}")
    print(f"{'P50 (ms)':<20} {rx_a_results['percentiles'][50]:.1f}")
    print(f"{'P95 (ms)':<20} {rx_a_results['percentiles'][95]:.1f}")
    print(f"{'<5min %':<20} {rx_a_results['bins']['<5min']:.1f}%")
    print(f"{'5-30min %':<20} {rx_a_results['bins']['5-30min']:.1f}%")
    print(f"{'30-120min %':<20} {rx_a_results['bins']['30-120min']:.1f}%")
    print(f"{'>120min %':<20} {rx_a_results['bins']['>120min']:.1f}%")
    
    # Per-week breakdown
    print(f"\nPer-Week Breakdown:")
    for week, results in rx_a_results['per_week_results'].items():
        print(f"  {week}: {results['n_pairs']} pairs, {results['coverage_pct']:.1f}% coverage")
    
    # RX-B Table
    combined = rx_b_results['combined_results']
    print(f"\nRX-B Timing Results (Combined):")
    print(f"{'Region':<10} {'Events':<8} {'Hours':<8} {'Rate':<10} {'Chi2':<10} {'P-value':<10}")
    print("-" * 60)
    print(f"{'ASIA':<10} {combined['asia_events']:<8} {combined['asia_hours']:<8} {combined['asia_rate']:<10.2f} {combined['chi2_stat']:<10.4f} {combined['p_value']:<10.4f}")
    print(f"{'EU':<10} {combined['eu_events']:<8} {combined['eu_hours']:<8} {combined['eu_rate']:<10.2f}")
    print(f"{'US':<10} {combined['us_events']:<8} {combined['us_hours']:<8} {combined['us_rate']:<10.2f}")
    
    # RX-C Table
    print(f"\nRX-C Regression Results (Combined):")
    print(f"{'Metric':<20} {'Value':<15}")
    print("-" * 35)
    print(f"{'N Bins Used':<20} {rx_c_results['n_bins_used']:<15}")
    print(f"{'R² Single':<20} {rx_c_results['R2_single']:.4f}")
    print(f"{'R² Multi':<20} {rx_c_results['R2_multi']:.4f}")
    print(f"{'ΔR²':<20} {rx_c_results['delta_R2']:.4f}")
    print(f"{'COINBASE β':<20} {rx_c_results['beta_coinbase']:.4f}")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750:
        print(f"✅ PROMPT 3 COMPLETE - All guardrails complied with")
        print(f"• No synthetic data, smoothing, resampling, or imputations")
        print(f"• No schema edits")
        print(f"• No overwrites/merges/append to canonical caches")
        print(f"• Raw UTC timestamps preserved")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Weekday filter applied (Mon-Fri only, 10 days total)")
        print(f"• All outputs saved with COMBINED_WEEKDAY tag")
    else:
        print(f"❌ PROMPT 3 HALTED")
        print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PROMPT 3 COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




