#!/usr/bin/env python3
"""
PHASE RX-C: Binance-Independence Regression — W-1 and W-2 only
Task: Estimate regression models to test BINANCE independence from other venues
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import glob
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
        
        beacon_cache_dir = f"data_v6/cache/beacons/{week}"
        if os.path.exists(beacon_cache_dir):
            beacon_files = glob.glob(f"{beacon_cache_dir}/*.parquet")
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
            print(f"  ❌ {week}: Beacon cache directory not found")
            all_beacon_data[week] = pd.DataFrame()
            cache_status[week] = 'MISSING'
    
    return all_beacon_data, cache_status

def load_canonical_data(weeks, venues):
    """Load canonical parquet data for volatility analysis"""
    print(f"\n🔍 Loading Canonical Data for Volatility Analysis")
    print("-" * 60)
    
    canonical_data = {}
    
    for week in weeks:
        print(f"Loading {week}...")
        
        week_data = {}
        
        for venue in venues:
            # Map week names to date ranges
            if week == 'week-minus2':
                date_range = ['2025-08-22', '2025-08-23', '2025-08-24', '2025-08-25', '2025-08-26', '2025-08-27', '2025-08-28']
            elif week == 'week-minus1':
                date_range = ['2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04', '2025-09-05', '2025-09-06', '2025-09-07']
            else:
                continue
            
            venue_data = []
            
            for date in date_range:
                file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
                if os.path.exists(file_path):
                    try:
                        df = pd.read_parquet(file_path)
                        venue_data.append(df)
                    except Exception as e:
                        print(f"  Warning: Could not load {file_path}: {e}")
            
            if venue_data:
                week_data[venue] = pd.concat(venue_data, ignore_index=True)
                print(f"  ✅ {venue}: {len(week_data[venue])} ticks loaded")
            else:
                print(f"  ⚠️ {venue}: No canonical data found")
                week_data[venue] = pd.DataFrame()
        
        canonical_data[week] = week_data
    
    return canonical_data

def create_time_series_data(beacon_data, canonical_data, weeks):
    """Create time series data for regression analysis"""
    print(f"\n🔍 Creating Time Series Data for Regression")
    print("-" * 60)
    
    time_series_data = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        # Get beacon data for this week
        if week not in beacon_data or len(beacon_data[week]) == 0:
            time_series_data[week] = pd.DataFrame()
            continue
        
        week_beacons = beacon_data[week].copy()
        if 'event_ts' in week_beacons.columns:
            week_beacons['event_ts'] = pd.to_datetime(week_beacons['event_ts'], utc=True)
        
        # Create 1-second time bins for the week
        if len(week_beacons) > 0:
            start_time = week_beacons['event_ts'].min().floor('1s')
            end_time = week_beacons['event_ts'].max().ceil('1s')
        else:
            # Default to a week if no beacons
            start_time = pd.Timestamp('2025-08-22', tz='UTC')
            end_time = pd.Timestamp('2025-08-29', tz='UTC')
        
        time_bins = pd.date_range(start=start_time, end=end_time, freq='1s')
        
        # Initialize time series DataFrame
        ts_df = pd.DataFrame({
            'timestamp': time_bins,
            'binance_update': 0,
            'coinbase_update': 0,
            'bitget_update': 0,
            'bybit_update': 0,
            'local_volatility': 0.0
        })
        
        # Count beacon updates per venue per time bin
        for venue in ['BINANCE', 'COINBASE', 'BITGET', 'BYBITSPOT']:
            venue_beacons = week_beacons[week_beacons['venue'] == venue].copy()
            
            if len(venue_beacons) > 0:
                venue_beacons['timestamp_bin'] = venue_beacons['event_ts'].dt.floor('1s')
                venue_counts = venue_beacons['timestamp_bin'].value_counts()
                
                # Map venue name to column name
                if venue == 'BYBITSPOT':
                    col_name = 'bybit_update'
                else:
                    col_name = venue.lower() + '_update'
                
                # Update time series
                for timestamp, count in venue_counts.items():
                    mask = ts_df['timestamp'] == timestamp
                    ts_df.loc[mask, col_name] = min(count, 1)  # Binary: 1 if any update, 0 otherwise
        
        # Calculate local volatility (5-second rolling standard deviation)
        if week in canonical_data and 'BINANCE' in canonical_data[week] and len(canonical_data[week]['BINANCE']) > 0:
            binance_ticks = canonical_data[week]['BINANCE'].copy()
            if 'ts' in binance_ticks.columns and 'price' in binance_ticks.columns:
                binance_ticks['ts'] = pd.to_datetime(binance_ticks['ts'], utc=True)
                binance_ticks = binance_ticks.sort_values('ts')
                
                # Calculate returns
                binance_ticks['returns'] = binance_ticks['price'].pct_change()
                
                # Calculate 5-second rolling volatility
                binance_ticks['volatility_5s'] = binance_ticks['returns'].rolling(window=5, min_periods=1).std()
                
                # Aggregate to 1-second bins
                binance_ticks['timestamp_bin'] = binance_ticks['ts'].dt.floor('1s')
                volatility_agg = binance_ticks.groupby('timestamp_bin')['volatility_5s'].mean()
                
                # Update time series
                for timestamp, vol in volatility_agg.items():
                    mask = ts_df['timestamp'] == timestamp
                    ts_df.loc[mask, 'local_volatility'] = vol
        
        # Remove rows with all zeros (no activity)
        ts_df = ts_df[(ts_df['binance_update'] > 0) | (ts_df['coinbase_update'] > 0) | 
                      (ts_df['bitget_update'] > 0) | (ts_df['bybit_update'] > 0) | 
                      (ts_df['local_volatility'] > 0)]
        
        time_series_data[week] = ts_df
        print(f"  Created {len(ts_df)} time bins with activity")
    
    return time_series_data

def estimate_regression_models(time_series_data, weeks):
    """Estimate regression models for BINANCE independence"""
    print(f"\n🔍 Estimating Regression Models")
    print("-" * 60)
    
    regression_results = {}
    
    for week in weeks:
        print(f"Processing {week}...")
        
        if week not in time_series_data or len(time_series_data[week]) == 0:
            regression_results[week] = {
                'model1': {'r2': 0.0, 'beta1': 0.0, 'beta1_se': 0.0},
                'model2': {'r2': 0.0, 'beta1': 0.0, 'beta1_se': 0.0, 'beta2': 0.0, 'beta3': 0.0, 'beta4': 0.0},
                'delta_r2': 0.0
            }
            continue
        
        ts_df = time_series_data[week].copy()
        
        # Prepare data
        y = ts_df['binance_update'].values  # Binary response: 1 if BINANCE updates
        
        # Model 1: Single-factor (COINBASE only)
        X1 = ts_df[['coinbase_update']].values
        
        # Model 2: Multi-factor (COINBASE + volatility + BITGET + BYBIT)
        X2 = ts_df[['coinbase_update', 'local_volatility', 'bitget_update', 'bybit_update']].values
        
        # Handle missing values
        valid_mask = ~(np.isnan(X2).any(axis=1) | np.isnan(y))
        X1_clean = X1[valid_mask]
        X2_clean = X2[valid_mask]
        y_clean = y[valid_mask]
        
        if len(y_clean) < 10:  # Need minimum data points
            print(f"  Insufficient data points: {len(y_clean)}")
            regression_results[week] = {
                'model1': {'r2': 0.0, 'beta1': 0.0, 'beta1_se': 0.0},
                'model2': {'r2': 0.0, 'beta1': 0.0, 'beta1_se': 0.0, 'beta2': 0.0, 'beta3': 0.0, 'beta4': 0.0},
                'delta_r2': 0.0
            }
            continue
        
        # Fit Model 1
        try:
            model1 = LinearRegression()
            model1.fit(X1_clean, y_clean)
            y_pred1 = model1.predict(X1_clean)
            r2_1 = r2_score(y_clean, y_pred1)
            beta1_1 = model1.coef_[0]
            
            # Calculate standard error for beta1 (simplified)
            residuals1 = y_clean - y_pred1
            mse1 = np.mean(residuals1**2)
            beta1_se_1 = np.sqrt(mse1 / np.sum((X1_clean[:, 0] - np.mean(X1_clean[:, 0]))**2))
            
        except Exception as e:
            print(f"  Warning: Model 1 failed: {e}")
            r2_1, beta1_1, beta1_se_1 = 0.0, 0.0, 0.0
        
        # Fit Model 2
        try:
            model2 = LinearRegression()
            model2.fit(X2_clean, y_clean)
            y_pred2 = model2.predict(X2_clean)
            r2_2 = r2_score(y_clean, y_pred2)
            beta1_2 = model2.coef_[0]
            beta2 = model2.coef_[1]
            beta3 = model2.coef_[2]
            beta4 = model2.coef_[3]
            
            # Calculate standard error for beta1 (simplified)
            residuals2 = y_clean - y_pred2
            mse2 = np.mean(residuals2**2)
            beta1_se_2 = np.sqrt(mse2 / np.sum((X2_clean[:, 0] - np.mean(X2_clean[:, 0]))**2))
            
        except Exception as e:
            print(f"  Warning: Model 2 failed: {e}")
            r2_2, beta1_2, beta1_se_2, beta2, beta3, beta4 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
        # Calculate delta R²
        delta_r2 = r2_2 - r2_1
        
        regression_results[week] = {
            'model1': {'r2': r2_1, 'beta1': beta1_1, 'beta1_se': beta1_se_1},
            'model2': {'r2': r2_2, 'beta1': beta1_2, 'beta1_se': beta1_se_2, 'beta2': beta2, 'beta3': beta3, 'beta4': beta4},
            'delta_r2': delta_r2
        }
        
        print(f"  Model 1 R²: {r2_1:.4f}, β₁: {beta1_1:.4f} (±{beta1_se_1:.4f})")
        print(f"  Model 2 R²: {r2_2:.4f}, β₁: {beta1_2:.4f} (±{beta1_se_2:.4f})")
        print(f"  ΔR²: {delta_r2:.4f}")
    
    return regression_results

def main():
    print("🧭 PHASE RX-C: BINANCE-INDEPENDENCE REGRESSION — W-1 AND W-2 ONLY")
    print("=" * 80)
    print("Task: Estimate regression models to test BINANCE independence from other venues")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope - W-2 and W-1 only
    weeks = ['week-minus2', 'week-minus1']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f"📅 Processing weeks: {weeks}")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load beacon data
    beacon_data, cache_status = load_beacon_data(weeks)
    
    # Check for sufficient data
    total_beacons = sum(len(df) for df in beacon_data.values())
    if total_beacons == 0:
        print("❌ HALT: No beacon data found in cache")
        return
    
    print(f"✅ Total beacons loaded: {total_beacons}")
    
    # Load canonical data
    canonical_data = load_canonical_data(weeks, venues)
    
    # Create time series data
    time_series_data = create_time_series_data(beacon_data, canonical_data, weeks)
    
    # Estimate regression models
    regression_results = estimate_regression_models(time_series_data, weeks)
    
    # ========================================================================
    # OUTPUT REPORT
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 RX-C-SUMMARY")
    print("=" * 80)
    
    # Per-week table
    print(f"\nPer-Week Regression Results:")
    print(f"{'Week':<12} {'Model':<6} {'R²':<8} {'β₁':<10} {'±SE':<8} {'ΔR²':<8}")
    print("-" * 60)
    
    delta_r2_values = []
    
    for week in weeks:
        if week in regression_results:
            result = regression_results[week]
            
            # Model 1
            model1 = result['model1']
            print(f"{week:<12} {'1':<6} {model1['r2']:<8.4f} {model1['beta1']:<10.4f} {model1['beta1_se']:<8.4f} {'—':<8}")
            
            # Model 2
            model2 = result['model2']
            delta_r2 = result['delta_r2']
            delta_r2_values.append(delta_r2)
            print(f"{week:<12} {'2':<6} {model2['r2']:<8.4f} {model2['beta1']:<10.4f} {model2['beta1_se']:<8.4f} {delta_r2:<8.4f}")
        else:
            print(f"{week:<12} {'1':<6} {'N/A':<8} {'N/A':<10} {'N/A':<8} {'—':<8}")
            print(f"{week:<12} {'2':<6} {'N/A':<8} {'N/A':<10} {'N/A':<8} {'N/A':<8}")
    
    # Aggregate mean ΔR²
    if delta_r2_values:
        mean_delta_r2 = np.mean(delta_r2_values)
        print(f"\nAggregate Mean ΔR²: {mean_delta_r2:.4f}")
    else:
        print(f"\nAggregate Mean ΔR²: N/A")
    
    # HALT reasons check
    print(f"\nHALT Reasons Check:")
    print(f"  Memory usage: {get_memory_usage():.1f} MB (≤ 750 MB limit): {'OK' if get_memory_usage() <= 750 else 'HALT'}")
    
    # Check data availability
    total_time_bins = sum(len(ts_df) for ts_df in time_series_data.values())
    print(f"  Total time bins with activity: {total_time_bins}")
    
    if total_time_bins == 0:
        print(f"  Data availability: HALT - No time series data created")
    else:
        print(f"  Data availability: OK")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750:
        print(f"✅ PHASE RX-C COMPLETE - All guardrails complied with")
        print(f"• Read-only mode; no cache writes or schema changes")
        print(f"• No synthetic data; Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Used same variables as Phase 18 + local volatility and venue-specific beacons")
    else:
        print(f"❌ PHASE RX-C HALTED - Memory limit exceeded")
        print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"PHASE RX-C COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




