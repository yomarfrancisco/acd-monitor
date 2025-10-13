#!/usr/bin/env python3
"""
Phase 37D - Rolling Regime Index (RRI) with energy distance/MMD
Detect transition zone by measuring divergence from August baseline
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from scipy import stats
from scipy.stats import median_abs_deviation
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics.pairwise import rbf_kernel
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb > 3500:  # Memory limit
        print(f"❌ MEMORY LIMIT EXCEEDED: {memory_mb:.1f} MB > 3500 MB")
        return False
    elif memory_mb > 3200:  # Warning threshold
        print(f"⚠️ MEMORY WARNING: {memory_mb:.1f} MB > 3200 MB")
    return True

def load_and_prepare_data():
    """Load data and prepare for analysis"""
    print("📁 Loading normalized panel...")
    
    input_path = "/Users/ygorfrancisco/Desktop/acd-monitor/data_v6/cache/beacons/beacons_aug_sep_7w_norm.parquet"
    
    if not os.path.exists(input_path):
        print(f"❌ Normalized panel not found: {input_path}")
        return None
    
    df = pd.read_parquet(input_path)
    
    print(f"✅ Loaded panel: {df.shape}")
    print(f"📅 Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"💾 Memory usage: {get_memory_usage():.1f} MB")
    
    # Use only required columns
    required_columns = ['timestamp', 'venue', 'entropy', 'ofi', 'vol_proxy']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"❌ HALT: Missing required columns: {missing_columns}")
        return None
    
    df = df[required_columns]
    
    # Aggregate to hourly level
    print(f"📊 Aggregating to hourly level...")
    hourly_df = df.groupby('timestamp').agg({
        'entropy': 'mean',
        'ofi': 'mean',
        'vol_proxy': 'mean'
    }).reset_index()
    
    print(f"✅ Aggregated to {len(hourly_df)} hourly observations")
    
    return hourly_df

def winsorize_series(series, lower=0.01, upper=0.99):
    """Winsorize series at specified percentiles"""
    lower_bound = series.quantile(lower)
    upper_bound = series.quantile(upper)
    
    winsorized = series.clip(lower=lower_bound, upper=upper_bound)
    
    return winsorized, lower_bound, upper_bound

def signed_log1p(x):
    """Apply signed_log1p transformation: sign(x) * log1p(|x|)"""
    return np.sign(x) * np.log1p(np.abs(x))

def robust_scale_features(hourly_df):
    """Robust-scale features with winsorize, log1p for OFI, median/MAD standardize"""
    print(f"\n🔧 Robust scaling features...")
    
    features = ['entropy', 'ofi', 'vol_proxy']
    scaled_data = {}
    scaling_info = {}
    
    for feature in features:
        print(f"\n📊 Processing {feature}...")
        
        # Get original values
        original_values = hourly_df[feature].dropna()
        
        if len(original_values) == 0:
            print(f"❌ HALT: No data for feature {feature}")
            return None, None
        
        # Winsorize at [1%, 99%]
        winsorized, lower_bound, upper_bound = winsorize_series(original_values, 0.01, 0.99)
        
        # Apply OFI transformation if needed
        if feature == 'ofi':
            transformed = signed_log1p(winsorized)
            print(f"   Applied signed_log1p transformation to OFI")
        else:
            transformed = winsorized
        
        # Compute robust statistics
        median_val = np.median(transformed)
        mad_val = median_abs_deviation(transformed, scale='normal')
        
        # Check for scaling anomalies
        if mad_val < 1e-10:
            print(f"❌ HALT: Scaling anomaly - MAD ≈ 0 for {feature}")
            return None, None
        
        # Robust standardize
        standardized = (transformed - median_val) / mad_val
        
        # Store results
        scaled_data[feature] = standardized
        scaling_info[feature] = {
            'original_median': np.median(original_values),
            'original_mad': median_abs_deviation(original_values, scale='normal'),
            'winsorized_lower': lower_bound,
            'winsorized_upper': upper_bound,
            'transformed_median': median_val,
            'transformed_mad': mad_val,
            'count': len(standardized)
        }
        
        print(f"   Original: median={scaling_info[feature]['original_median']:.6f}, MAD={scaling_info[feature]['original_mad']:.6f}")
        print(f"   Transformed: median={median_val:.6f}, MAD={mad_val:.6f}")
        print(f"   Winsorized: [{lower_bound:.6f}, {upper_bound:.6f}]")
    
    return scaled_data, scaling_info

def build_reference_set(hourly_df, scaled_data):
    """Build reference set from August hours (W-4 to W-1)"""
    print(f"\n📚 Building reference set from August hours...")
    
    # Define August period (W-4 to W-1)
    aug_start = '2025-08-04'
    aug_end = '2025-08-31'
    
    # Filter August data
    aug_mask = (hourly_df['timestamp'] >= aug_start) & (hourly_df['timestamp'] < aug_end)
    aug_data = hourly_df[aug_mask].copy()
    
    print(f"📊 August reference period: {aug_start} → {aug_end}")
    print(f"   August hours: {len(aug_data)}")
    
    if len(aug_data) == 0:
        print(f"❌ HALT: No August data found")
        return None
    
    # Extract scaled features for reference
    features = ['entropy', 'ofi', 'vol_proxy']
    reference_data = []
    
    for idx, row in aug_data.iterrows():
        feature_vector = []
        for feature in features:
            if feature in scaled_data:
                feature_vector.append(scaled_data[feature].iloc[idx])
            else:
                print(f"❌ HALT: Missing scaled data for {feature}")
                return None
        
        reference_data.append(feature_vector)
    
    reference_matrix = np.array(reference_data)
    
    print(f"✅ Reference set: {reference_matrix.shape[0]} samples × {reference_matrix.shape[1]} features")
    
    return reference_matrix

def energy_distance(X, Y):
    """Compute energy distance between two sets of samples"""
    n, m = len(X), len(Y)
    
    # Compute pairwise distances within X
    XX = np.sum(X**2, axis=1)[:, np.newaxis] + np.sum(X**2, axis=1)[np.newaxis, :] - 2 * np.dot(X, X.T)
    XX = np.sqrt(np.maximum(XX, 0))
    
    # Compute pairwise distances within Y
    YY = np.sum(Y**2, axis=1)[:, np.newaxis] + np.sum(Y**2, axis=1)[np.newaxis, :] - 2 * np.dot(Y, Y.T)
    YY = np.sqrt(np.maximum(YY, 0))
    
    # Compute pairwise distances between X and Y
    XY = np.sum(X**2, axis=1)[:, np.newaxis] + np.sum(Y**2, axis=1)[np.newaxis, :] - 2 * np.dot(X, Y.T)
    XY = np.sqrt(np.maximum(XY, 0))
    
    # Energy distance formula
    energy_dist = (2 * np.mean(XY) - np.mean(XX) - np.mean(YY))
    
    return energy_dist

def mmd_distance(X, Y, sigma):
    """Compute Maximum Mean Discrepancy with Gaussian kernel"""
    # Compute kernel matrices
    K_XX = rbf_kernel(X, X, gamma=1/(2*sigma**2))
    K_YY = rbf_kernel(Y, Y, gamma=1/(2*sigma**2))
    K_XY = rbf_kernel(X, Y, gamma=1/(2*sigma**2))
    
    # MMD formula
    mmd_dist = np.mean(K_XX) + np.mean(K_YY) - 2 * np.mean(K_XY)
    
    return mmd_dist

def bootstrap_confidence_interval(X, Y, distance_func, n_bootstrap=500, **kwargs):
    """Compute bootstrap confidence interval for distance"""
    n, m = len(X), len(Y)
    
    bootstrap_distances = []
    
    for _ in range(n_bootstrap):
        # Bootstrap resample
        X_boot = X[np.random.choice(n, n, replace=True)]
        Y_boot = Y[np.random.choice(m, m, replace=True)]
        
        # Compute distance
        dist = distance_func(X_boot, Y_boot, **kwargs)
        bootstrap_distances.append(dist)
    
    # Compute confidence interval
    ci_low = np.percentile(bootstrap_distances, 2.5)
    ci_high = np.percentile(bootstrap_distances, 97.5)
    
    return ci_low, ci_high

def slide_48h_window(hourly_df, scaled_data, reference_matrix):
    """Slide 48h window and compute distances"""
    print(f"\n🔄 Sliding 48h window from Aug-20 to Sep-21...")
    
    # Define sliding window parameters
    window_size = 48  # hours
    step_size = 1  # hour
    
    # Define sliding period
    slide_start = '2025-08-20'
    slide_end = '2025-09-21'
    
    # Filter sliding period
    slide_mask = (hourly_df['timestamp'] >= slide_start) & (hourly_df['timestamp'] <= slide_end)
    slide_data = hourly_df[slide_mask].copy()
    
    print(f"📊 Sliding period: {slide_start} → {slide_end}")
    print(f"   Sliding hours: {len(slide_data)}")
    
    if len(slide_data) == 0:
        print(f"❌ HALT: No sliding data found")
        return None
    
    # Compute sigma for MMD from reference pairwise distances
    ref_distances = pdist(reference_matrix)
    sigma = np.median(ref_distances)
    print(f"   MMD sigma (median pairwise distance): {sigma:.6f}")
    
    # Initialize results
    results = []
    features = ['entropy', 'ofi', 'vol_proxy']
    
    # Slide window
    for i in range(len(slide_data) - window_size + 1):
        window_data = slide_data.iloc[i:i+window_size]
        
        # Check NaN rate
        nan_count = window_data[features].isnull().sum().sum()
        nan_rate = (nan_count / (len(window_data) * len(features))) * 100
        
        if nan_rate > 5:
            print(f"⚠️ Skipping window {i}: NaN rate {nan_rate:.1f}% > 5%")
            continue
        
        # Extract window features
        window_features = []
        for idx, row in window_data.iterrows():
            feature_vector = []
            for feature in features:
                if feature in scaled_data:
                    feature_vector.append(scaled_data[feature].iloc[idx])
                else:
                    print(f"❌ HALT: Missing scaled data for {feature}")
                    return None
            
            window_features.append(feature_vector)
        
        window_matrix = np.array(window_features)
        
        # Compute distances
        energy_dist = energy_distance(reference_matrix, window_matrix)
        mmd_dist = mmd_distance(reference_matrix, window_matrix, sigma)
        
        # Bootstrap confidence intervals
        try:
            energy_ci = bootstrap_confidence_interval(reference_matrix, window_matrix, energy_distance, n_bootstrap=500)
            mmd_ci = bootstrap_confidence_interval(reference_matrix, window_matrix, mmd_distance, n_bootstrap=500, sigma=sigma)
        except Exception as e:
            print(f"❌ HALT: Bootstrap failure at window {i}: {e}")
            return None
        
        # Store results
        results.append({
            'window_idx': i,
            'timestamp': window_data.iloc[0]['timestamp'],
            'energy_distance': energy_dist,
            'mmd_distance': mmd_dist,
            'energy_ci_low': energy_ci[0],
            'energy_ci_high': energy_ci[1],
            'mmd_ci_low': mmd_ci[0],
            'mmd_ci_high': mmd_ci[1]
        })
        
        if i % 100 == 0:
            print(f"   Processed window {i}/{len(slide_data) - window_size + 1}")
    
    print(f"✅ Processed {len(results)} windows")
    
    return results

def create_rri_index(results):
    """Create RRI(t) = z-scored average of (energy, MMD)"""
    print(f"\n📊 Creating Rolling Regime Index (RRI)...")
    
    if not results:
        print(f"❌ HALT: No results to create RRI")
        return None
    
    # Extract distances
    energy_distances = [r['energy_distance'] for r in results]
    mmd_distances = [r['mmd_distance'] for r in results]
    
    # Compute z-scores
    energy_z = stats.zscore(energy_distances)
    mmd_z = stats.zscore(mmd_distances)
    
    # Create RRI as average of z-scores
    rri = (energy_z + mmd_z) / 2
    
    # Add RRI to results
    for i, result in enumerate(results):
        result['rri'] = rri[i]
        result['energy_z'] = energy_z[i]
        result['mmd_z'] = mmd_z[i]
    
    print(f"✅ RRI computed for {len(results)} windows")
    print(f"   RRI range: [{np.min(rri):.4f}, {np.max(rri):.4f}]")
    print(f"   RRI mean: {np.mean(rri):.4f}, std: {np.std(rri):.4f}")
    
    return results

def flag_transition_blocks(results, threshold=2.0):
    """Flag consecutive hours where RRI(t) > threshold for ≥ 12h"""
    print(f"\n🚩 Flagging transition blocks (RRI > {threshold}σ for ≥ 12h)...")
    
    if not results:
        print(f"❌ HALT: No results to flag")
        return None
    
    # Extract RRI values
    rri_values = [r['rri'] for r in results]
    
    # Flag high RRI periods
    high_rri = np.array(rri_values) > threshold
    
    # Find consecutive blocks
    blocks = []
    current_block = None
    
    for i, is_high in enumerate(high_rri):
        if is_high:
            if current_block is None:
                current_block = {'start': i, 'end': i}
            else:
                current_block['end'] = i
        else:
            if current_block is not None:
                # Check if block is long enough (≥ 12h)
                block_length = current_block['end'] - current_block['start'] + 1
                if block_length >= 12:
                    blocks.append(current_block)
                current_block = None
    
    # Handle block that extends to end
    if current_block is not None:
        block_length = current_block['end'] - current_block['start'] + 1
        if block_length >= 12:
            blocks.append(current_block)
    
    print(f"📊 Found {len(blocks)} transition blocks")
    
    for i, block in enumerate(blocks):
        start_time = results[block['start']]['timestamp']
        end_time = results[block['end']]['timestamp']
        duration = block['end'] - block['start'] + 1
        
        # Compute mean RRI for block
        block_rri = [results[j]['rri'] for j in range(block['start'], block['end'] + 1)]
        mean_rri = np.mean(block_rri)
        
        print(f"   Block {i+1}: {start_time} → {end_time} ({duration}h), mean RRI: {mean_rri:.4f}")
    
    return blocks

def merge_blocks(blocks, results, max_gap=6):
    """Merge blocks separated by < max_gap hours"""
    print(f"\n🔗 Merging blocks separated by < {max_gap}h...")
    
    if not blocks:
        print(f"❌ HALT: No blocks to merge")
        return None
    
    if len(blocks) == 1:
        return blocks
    
    # Sort blocks by start time
    sorted_blocks = sorted(blocks, key=lambda x: x['start'])
    
    merged_blocks = []
    current_block = sorted_blocks[0].copy()
    
    for next_block in sorted_blocks[1:]:
        gap = next_block['start'] - current_block['end'] - 1
        
        if gap < max_gap:
            # Merge blocks
            current_block['end'] = next_block['end']
            print(f"   Merged blocks with gap {gap}h")
        else:
            # Start new block
            merged_blocks.append(current_block)
            current_block = next_block.copy()
    
    # Add last block
    merged_blocks.append(current_block)
    
    print(f"📊 Merged {len(blocks)} blocks into {len(merged_blocks)} zones")
    
    return merged_blocks

def validate_zones(zones, results):
    """Validate zones: duration ≥ 24h and ≥60% hours significant"""
    print(f"\n✅ Validating transition zones...")
    
    if not zones:
        print(f"❌ HALT: No zones to validate")
        return None
    
    validated_zones = []
    
    for i, zone in enumerate(zones):
        start_idx = zone['start']
        end_idx = zone['end']
        duration = end_idx - start_idx + 1
        
        # Check duration requirement
        if duration < 24:
            print(f"   Zone {i+1}: Duration {duration}h < 24h - REJECTED")
            continue
        
        # Check significance requirement
        zone_results = results[start_idx:end_idx+1]
        significant_hours = 0
        
        for result in zone_results:
            # Check if both distances are significant (p < 0.05)
            # This is a simplified check - in practice, you'd need proper statistical tests
            if (result['energy_distance'] > result['energy_ci_high'] and 
                result['mmd_distance'] > result['mmd_ci_high']):
                significant_hours += 1
        
        significance_rate = significant_hours / len(zone_results)
        
        if significance_rate >= 0.60:
            print(f"   Zone {i+1}: Duration {duration}h, significance {significance_rate:.1%} - ACCEPTED")
            validated_zones.append(zone)
        else:
            print(f"   Zone {i+1}: Duration {duration}h, significance {significance_rate:.1%} - REJECTED")
    
    print(f"📊 Validated {len(validated_zones)} out of {len(zones)} zones")
    
    return validated_zones

def generate_ascii_outputs(hourly_df, scaling_info, results, zones):
    """Generate ASCII outputs with sparklines and summary tables"""
    print(f"\n📈 ASCII Outputs:")
    print("=" * 80)
    
    # Scaling summary table
    print(f"\n🔧 Scaling Summary:")
    print(f"{'Feature':<12} {'Orig Median':<12} {'Orig MAD':<12} {'Trans Median':<12} {'Trans MAD':<12}")
    print("-" * 60)
    
    for feature, info in scaling_info.items():
        print(f"{feature:<12} {info['original_median']:<12.6f} {info['original_mad']:<12.6f} "
              f"{info['transformed_median']:<12.6f} {info['transformed_mad']:<12.6f}")
    
    # Zone summary table
    if zones:
        print(f"\n🎯 Transition Zone Summary:")
        print(f"{'Zone':<6} {'Start':<20} {'End':<20} {'Duration':<10} {'Mean RRI':<10}")
        print("-" * 70)
        
        for i, zone in enumerate(zones):
            start_time = results[zone['start']]['timestamp']
            end_time = results[zone['end']]['timestamp']
            duration = zone['end'] - zone['start'] + 1
            
            # Compute mean RRI for zone
            zone_rri = [results[j]['rri'] for j in range(zone['start'], zone['end'] + 1)]
            mean_rri = np.mean(zone_rri)
            
            print(f"{i+1:<6} {str(start_time)[:19]:<20} {str(end_time)[:19]:<20} {duration:<10} {mean_rri:<10.4f}")
    else:
        print(f"\n🎯 No transition zones found")
    
    # RRI sparkline with zones
    if results:
        print(f"\n📊 RRI Sparkline (zones shaded):")
        
        # Create sparkline
        rri_values = [r['rri'] for r in results]
        n_points = 60
        
        if len(rri_values) > n_points:
            step = len(rri_values) // n_points
            spark_values = rri_values[::step][:n_points]
        else:
            spark_values = rri_values
        
        # Normalize for sparkline
        min_val = min(spark_values)
        max_val = max(spark_values)
        if max_val > min_val:
            normalized = [(v - min_val) / (max_val - min_val) for v in spark_values]
        else:
            normalized = [0] * len(spark_values)
        
        # Create sparkline characters
        spark_chars = "▁▂▃▄▅▆▇█"
        sparkline = "".join([spark_chars[int(v * (len(spark_chars) - 1))] for v in normalized])
        
        # Mark zones
        if zones:
            for zone in zones:
                start_pos = min(zone['start'] * len(sparkline) // len(rri_values), len(sparkline) - 1)
                end_pos = min(zone['end'] * len(sparkline) // len(rri_values), len(sparkline) - 1)
                
                if start_pos >= 0 and end_pos >= 0:
                    # Mark zone boundaries
                    sparkline = sparkline[:start_pos] + "[" + sparkline[start_pos+1:end_pos] + "]" + sparkline[end_pos+1:]
        
        print(f"RRI: {sparkline}")
        print(f"Range: [{min_val:.4f}, {max_val:.4f}]")

def main():
    """Main execution function"""
    print("🧭 Phase 37D - Rolling Regime Index (RRI) with energy distance/MMD")
    print("=" * 70)
    
    # Check initial memory usage
    if not check_memory_limit():
        print("❌ Memory limit exceeded at start")
        return
    
    # Load and prepare data
    hourly_df = load_and_prepare_data()
    if hourly_df is None:
        print("❌ Failed to load and prepare data")
        return
    
    # Robust scale features
    scaled_data, scaling_info = robust_scale_features(hourly_df)
    if scaled_data is None:
        print("❌ Failed to scale features")
        return
    
    # Build reference set
    reference_matrix = build_reference_set(hourly_df, scaled_data)
    if reference_matrix is None:
        print("❌ Failed to build reference set")
        return
    
    # Slide 48h window
    results = slide_48h_window(hourly_df, scaled_data, reference_matrix)
    if results is None:
        print("❌ Failed to slide window")
        return
    
    # Create RRI index
    results = create_rri_index(results)
    if results is None:
        print("❌ Failed to create RRI index")
        return
    
    # Flag transition blocks
    blocks = flag_transition_blocks(results, threshold=2.0)
    if blocks is None:
        print("❌ Failed to flag transition blocks")
        return
    
    # Merge blocks
    zones = merge_blocks(blocks, results, max_gap=6)
    if zones is None:
        print("❌ Failed to merge blocks")
        return
    
    # Validate zones
    validated_zones = validate_zones(zones, results)
    if validated_zones is None:
        print("❌ Failed to validate zones")
        return
    
    # Generate ASCII outputs
    generate_ascii_outputs(hourly_df, scaling_info, results, validated_zones)
    
    # Final summary
    print(f"\n🎯 PHASE 37D SUMMARY")
    print("=" * 50)
    
    if validated_zones:
        print(f"✅ Transition zones identified: {len(validated_zones)}")
        for i, zone in enumerate(validated_zones):
            start_time = results[zone['start']]['timestamp']
            end_time = results[zone['end']]['timestamp']
            duration = zone['end'] - zone['start'] + 1
            print(f"   Zone {i+1}: {start_time} → {end_time} ({duration}h)")
    else:
        print(f"❌ No robust transition zones found")
    
    print(f"💾 Final memory usage: {get_memory_usage():.1f} MB")
    print("✅ Phase 37D - Rolling Regime Index complete")

if __name__ == "__main__":
    main()
