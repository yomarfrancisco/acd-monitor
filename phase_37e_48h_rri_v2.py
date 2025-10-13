#!/usr/bin/env python3
"""
Phase 37E-48h: RRI v2 - Energy + MMD with Robust/NaN-safe 48h windows
Quantify gradual structural drift from July baseline using robust distance metrics
"""

import os
import pandas as pd
import numpy as np
import hashlib
import psutil
from datetime import datetime, timedelta
from scipy import stats
from sklearn.metrics.pairwise import pairwise_distances
from sklearn.cluster import DBSCAN
from statsmodels.stats.multitest import multipletests
import json

def check_memory_limit():
    """Check memory usage and halt if over 4GB"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 4000:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 4GB limit")
        return False
    print(f"📊 Memory usage: {current_mb:.1f} MB")
    return True

def load_panel():
    """Load the 11-week normalized panel"""
    print("🔍 **Phase 37E-48h: RRI v2 - Robust/NaN-safe**")
    print("=" * 60)
    
    panel_path = 'data_v6/cache/beacons/beacons_jul_aug_sep_oct_11w_norm.v1.parquet'
    expected_sha256 = '5b8d2180af2b6aa2b03f8a3a8bbfee175a099b9898c6d048aa984b6fcfaff40b'
    
    if not os.path.exists(panel_path):
        print(f"❌ Panel not found: {panel_path}")
        return None
    
    # Verify SHA-256
    with open(panel_path, 'rb') as f:
        actual_sha256 = hashlib.sha256(f.read()).hexdigest()
    
    if actual_sha256 != expected_sha256:
        print(f"❌ SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}")
        return None
    
    df = pd.read_parquet(panel_path)
    print(f"📊 Loaded panel: {len(df)} rows")
    print(f"📊 Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"📊 Venues: {sorted(df['venue'].unique())}")
    
    # Check required columns
    required_cols = ['timestamp', 'venue', 'entropy', 'ofi', 'vol_proxy']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ HALT: Missing required columns: {missing_cols}")
        return None
    
    return df

def build_baseline(df):
    """Build July baseline (July 22-31) with NaN checks"""
    print(f"\n📊 **Building July Baseline**")
    print("=" * 60)
    
    # Filter to July 22-31
    july_start = pd.Timestamp('2025-07-22 00:00:00', tz='UTC')
    july_end = pd.Timestamp('2025-07-31 23:00:00', tz='UTC')
    
    july_data = df[
        (df['timestamp'] >= july_start) & 
        (df['timestamp'] <= july_end)
    ].copy()
    
    print(f"📊 July baseline: {len(july_data)} rows")
    print(f"📊 Date range: {july_data['timestamp'].min()} → {july_data['timestamp'].max()}")
    
    # Extract feature matrix X₀ = [entropy, ofi, vol_proxy]
    features = ['entropy', 'ofi', 'vol_proxy']
    X0 = july_data[features].values
    
    # Check for NaN values
    nan_counts = np.isnan(X0).sum(axis=0)
    nan_rates = nan_counts / len(X0) * 100
    
    print(f"📊 **NaN Diagnostics (Baseline):**")
    for i, feature in enumerate(features):
        print(f"   {feature}: {nan_counts[i]} NaNs ({nan_rates[i]:.2f}%)")
        if nan_rates[i] > 0.5:
            print(f"❌ HALT: {feature} has >0.5% NaNs in baseline")
            return None, None
    
    # Check for zero variance
    for i, feature in enumerate(features):
        variance = np.var(X0[:, i])
        if variance == 0 or np.isnan(variance):
            print(f"❌ HALT: Zero or NaN variance for {feature}")
            return None, None
        print(f"📊 {feature}: variance = {variance:.6f}")
    
    print(f"✅ Baseline X₀: {X0.shape[0]} samples × {X0.shape[1]} features")
    
    return df, X0

def huber_loss(x, delta):
    """Huber loss function"""
    abs_x = np.abs(x)
    return np.where(abs_x <= delta, 0.5 * x**2, delta * (abs_x - 0.5 * delta))

def compute_huberized_energy_distance(X1, X2, delta=None):
    """Compute Huberized Energy Distance between two feature matrices"""
    if delta is None:
        # Use median pairwise L2 distance in baseline
        all_data = np.vstack([X1, X2])
        pairwise_dist = pairwise_distances(all_data, metric='euclidean')
        delta = np.median(pairwise_dist[pairwise_dist > 0])
    
    # Remove NaN rows
    X1_clean = X1[~np.isnan(X1).any(axis=1)]
    X2_clean = X2[~np.isnan(X2).any(axis=1)]
    
    if len(X1_clean) == 0 or len(X2_clean) == 0:
        return 0.0, delta
    
    # Pairwise distances within X1
    dist_X1_X1 = pairwise_distances(X1_clean, metric='euclidean')
    np.fill_diagonal(dist_X1_X1, 0)  # Remove diagonal
    huber_X1_X1 = huber_loss(dist_X1_X1, delta)
    E_X1_X1 = np.mean(huber_X1_X1)
    
    # Pairwise distances within X2
    dist_X2_X2 = pairwise_distances(X2_clean, metric='euclidean')
    np.fill_diagonal(dist_X2_X2, 0)  # Remove diagonal
    huber_X2_X2 = huber_loss(dist_X2_X2, delta)
    E_X2_X2 = np.mean(huber_X2_X2)
    
    # Cross distances between X1 and X2
    dist_X1_X2 = pairwise_distances(X1_clean, X2_clean, metric='euclidean')
    huber_X1_X2 = huber_loss(dist_X1_X2, delta)
    E_X1_X2 = np.mean(huber_X1_X2)
    
    # Huberized Energy distance
    energy_dist = 2 * E_X1_X2 - E_X1_X1 - E_X2_X2
    
    return energy_dist, delta

def compute_mmd(X1, X2, sigma=None):
    """Compute Maximum Mean Discrepancy (MMD²) using Gaussian RBF kernel"""
    # Remove NaN rows
    X1_clean = X1[~np.isnan(X1).any(axis=1)]
    X2_clean = X2[~np.isnan(X2).any(axis=1)]
    
    if len(X1_clean) == 0 or len(X2_clean) == 0:
        return 0.0, sigma
    
    if sigma is None:
        # Use median pairwise distance as sigma
        all_data = np.vstack([X1_clean, X2_clean])
        pairwise_dist = pairwise_distances(all_data, metric='euclidean')
        sigma = np.median(pairwise_dist[pairwise_dist > 0])
    
    # Gaussian RBF kernel
    def rbf_kernel(X, Y, gamma):
        return np.exp(-gamma * pairwise_distances(X, Y, metric='euclidean')**2)
    
    gamma = 1.0 / (2 * sigma**2)
    
    # MMD² = E[k(X1, X1')] + E[k(X2, X2')] - 2*E[k(X1, X2)]
    n1, n2 = len(X1_clean), len(X2_clean)
    
    # K11: kernel matrix within X1
    K11 = rbf_kernel(X1_clean, X1_clean, gamma)
    np.fill_diagonal(K11, 0)  # Remove diagonal
    E_K11 = np.sum(K11) / (n1 * (n1 - 1))
    
    # K22: kernel matrix within X2
    K22 = rbf_kernel(X2_clean, X2_clean, gamma)
    np.fill_diagonal(K22, 0)  # Remove diagonal
    E_K22 = np.sum(K22) / (n2 * (n2 - 1))
    
    # K12: cross kernel matrix
    K12 = rbf_kernel(X1_clean, X2_clean, gamma)
    E_K12 = np.mean(K12)
    
    # MMD²
    mmd_squared = E_K11 + E_K22 - 2 * E_K12
    
    return mmd_squared, sigma

def generate_null_controls(df, window_size=48):
    """Generate null controls: circular shift and block permutation"""
    print(f"\n📊 **Generating Null Controls**")
    
    # Circular shift: rotate by +17 hours
    circular_shift = df.copy()
    circular_shift['timestamp'] = circular_shift['timestamp'] + pd.Timedelta(hours=17)
    
    # Block permutation: shuffle 6h blocks
    block_size = 6
    n_blocks = len(df) // block_size
    blocks = [df.iloc[i*block_size:(i+1)*block_size].copy() for i in range(n_blocks)]
    np.random.shuffle(blocks)
    
    block_perm = pd.concat(blocks, ignore_index=True)
    
    # Add remaining rows
    remaining = len(df) % block_size
    if remaining > 0:
        block_perm = pd.concat([block_perm, df.iloc[-remaining:]], ignore_index=True)
    
    return circular_shift, block_perm

def rolling_rri_analysis_48h(df, X0, window_size=48, stride=1):
    """Perform rolling RRI analysis with 48h windows"""
    print(f"\n📊 **Rolling RRI Analysis (48h windows)**")
    print("=" * 60)
    
    features = ['entropy', 'ofi', 'vol_proxy']
    
    # Generate null controls
    circular_shift, block_perm = generate_null_controls(df, window_size)
    
    # Rolling window analysis
    results = []
    skipped_windows = []
    total_windows = len(df) - window_size + 1
    
    print(f"📊 Processing {total_windows} windows (48h each, 1h stride)...")
    
    for i in range(0, total_windows, stride):
        if i % 1000 == 0:
            print(f"📊 Progress: {i}/{total_windows} windows")
        
        # Current window
        window_data = df.iloc[i:i+window_size]
        X_t = window_data[features].values
        
        # Check NaN policy: skip if >2% NaN rows
        nan_rows = np.isnan(X_t).any(axis=1)
        nan_rate = nan_rows.sum() / len(X_t)
        
        if nan_rate > 0.02:  # >2% NaN rows
            skipped_windows.append({
                'window_idx': i,
                'timestamp': window_data['timestamp'].iloc[0],
                'nan_rate': nan_rate
            })
            continue
        
        # Remove NaN rows for this window (no filling)
        X_t_clean = X_t[~nan_rows]
        
        if len(X_t_clean) < 10:  # Need minimum samples
            skipped_windows.append({
                'window_idx': i,
                'timestamp': window_data['timestamp'].iloc[0],
                'reason': 'insufficient_clean_samples'
            })
            continue
        
        # Compute Huberized Energy Distance
        E_t, delta = compute_huberized_energy_distance(X_t_clean, X0)
        
        # Compute MMD
        M_t, sigma = compute_mmd(X_t_clean, X0, sigma=None)
        
        # Null controls for current window
        # Circular shift window
        circ_window = circular_shift.iloc[i:i+window_size]
        X_circ = circ_window[features].values
        circ_nan_rows = np.isnan(X_circ).any(axis=1)
        X_circ_clean = X_circ[~circ_nan_rows]
        
        if len(X_circ_clean) >= 10:
            E_circ, _ = compute_huberized_energy_distance(X_circ_clean, X0, delta)
            M_circ, _ = compute_mmd(X_circ_clean, X0, sigma)
        else:
            E_circ, M_circ = 0.0, 0.0
        
        # Block permutation window
        perm_window = block_perm.iloc[i:i+window_size]
        X_perm = perm_window[features].values
        perm_nan_rows = np.isnan(X_perm).any(axis=1)
        X_perm_clean = X_perm[~perm_nan_rows]
        
        if len(X_perm_clean) >= 10:
            E_perm, _ = compute_huberized_energy_distance(X_perm_clean, X0, delta)
            M_perm, _ = compute_mmd(X_perm_clean, X0, sigma)
        else:
            E_perm, M_perm = 0.0, 0.0
        
        results.append({
            'window_idx': i,
            'timestamp': window_data['timestamp'].iloc[0],
            'E_t': E_t,
            'M_t': M_t,
            'E_circ': E_circ,
            'M_circ': M_circ,
            'E_perm': E_perm,
            'M_perm': M_perm
        })
    
    return pd.DataFrame(results), skipped_windows

def compute_z_scores(results_df):
    """Compute Z-scores using July baseline statistics"""
    print(f"\n📊 **Computing Z-Scores**")
    
    # Use first few windows (July) for baseline statistics
    july_windows = results_df.head(100)  # First 100 windows should be July
    
    E_mean = july_windows['E_t'].mean()
    E_std = july_windows['E_t'].std()
    M_mean = july_windows['M_t'].mean()
    M_std = july_windows['M_t'].std()
    
    # Compute Z-scores
    results_df['Z_E'] = (results_df['E_t'] - E_mean) / E_std
    results_df['Z_M'] = (results_df['M_t'] - M_mean) / M_std
    results_df['Z_avg'] = (results_df['Z_E'] + results_df['Z_M']) / 2
    
    print(f"📊 Energy Distance: mean={E_mean:.6f}, std={E_std:.6f}")
    print(f"📊 MMD: mean={M_mean:.6f}, std={M_std:.6f}")
    
    return results_df

def identify_drift_zones(results_df, threshold_e=1.5, threshold_m=1.5, threshold_avg=2.0):
    """Identify drift zones based on relaxed decision rules"""
    print(f"\n📊 **Identifying Drift Zones (Relaxed Criteria)**")
    print("=" * 60)
    
    # Decision rule A: Z_E > 1.5 and Z_M > 1.5, and each real ≥ (null mean + 0.5·null SD)
    rule_a = (
        (results_df['Z_E'] > threshold_e) & 
        (results_df['Z_M'] > threshold_m) &
        (results_df['E_t'] >= results_df['E_circ'].mean() + 0.5 * results_df['E_circ'].std()) &
        (results_df['E_t'] >= results_df['E_perm'].mean() + 0.5 * results_df['E_perm'].std()) &
        (results_df['M_t'] >= results_df['M_circ'].mean() + 0.5 * results_df['M_circ'].std()) &
        (results_df['M_t'] >= results_df['M_perm'].mean() + 0.5 * results_df['M_perm'].std())
    )
    
    # Decision rule B: Z_avg > 2.0 and real composite ≥ (null composite mean + 0.5·SD)
    null_composite_mean = (results_df['E_circ'] + results_df['M_circ']).mean()
    null_composite_std = (results_df['E_circ'] + results_df['M_circ']).std()
    real_composite = results_df['E_t'] + results_df['M_t']
    
    rule_b = (
        (results_df['Z_avg'] > threshold_avg) &
        (real_composite >= null_composite_mean + 0.5 * null_composite_std)
    )
    
    # Combine rules
    divergent_mask = rule_a | rule_b
    divergent_windows = results_df[divergent_mask].copy()
    
    print(f"📊 Divergent windows (Rule A): {rule_a.sum()}")
    print(f"📊 Divergent windows (Rule B): {rule_b.sum()}")
    print(f"📊 Total divergent windows: {len(divergent_windows)}")
    
    if len(divergent_windows) == 0:
        return []
    
    # Apply Holm-Bonferroni correction within each calendar day
    divergent_windows['date'] = divergent_windows['timestamp'].dt.date
    divergent_windows['holm_corrected'] = False
    
    for date, day_group in divergent_windows.groupby('date'):
        if len(day_group) > 1:
            # Apply Holm-Bonferroni correction
            p_values = 1 - stats.norm.cdf(day_group['Z_avg'].values)
            corrected = multipletests(p_values, method='holm')[0]
            divergent_windows.loc[day_group.index, 'holm_corrected'] = corrected
        else:
            divergent_windows.loc[day_group.index, 'holm_corrected'] = True
    
    # Filter to Holm-Bonferroni corrected significant windows
    significant_windows = divergent_windows[divergent_windows['holm_corrected']].copy()
    print(f"📊 Significant windows (Holm-Bonferroni): {len(significant_windows)}")
    
    if len(significant_windows) == 0:
        return []
    
    # Cluster consecutive divergent windows (gap ≤ 3h)
    timestamps = significant_windows['timestamp'].values
    clustering = DBSCAN(eps=3, min_samples=1).fit(timestamps.reshape(-1, 1))
    
    # Group by cluster
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(significant_windows.iloc[i])
    
    # Convert clusters to drift zones
    drift_zones = []
    
    for cluster_id, cluster_windows in clusters.items():
        if len(cluster_windows) < 2:  # Skip single-window clusters
            continue
        
        start_time = min([w['timestamp'] for w in cluster_windows])
        end_time = max([w['timestamp'] for w in cluster_windows])
        duration_h = (end_time - start_time).total_seconds() / 3600
        
        mean_Z_E = np.mean([w['Z_E'] for w in cluster_windows])
        mean_Z_M = np.mean([w['Z_M'] for w in cluster_windows])
        
        # Check if real > null for this cluster
        energy_pass = all(w['E_t'] > w['E_circ'] and w['E_t'] > w['E_perm'] for w in cluster_windows)
        mmd_pass = all(w['M_t'] > w['M_circ'] and w['M_t'] > w['M_perm'] for w in cluster_windows)
        zavg_pass = all(w['Z_avg'] > threshold_avg for w in cluster_windows)
        
        drift_zones.append({
            'start_utc': start_time,
            'end_utc': end_time,
            'duration_h': duration_h,
            'mean_ZE': mean_Z_E,
            'mean_ZM': mean_Z_M,
            'real_vs_null': {
                'E': energy_pass,
                'M': mmd_pass,
                'Zavg': zavg_pass
            },
            'holm_pass': True  # Already filtered
        })
    
    # Sort by mean Z-score
    drift_zones.sort(key=lambda x: x['mean_ZE'] + x['mean_ZM'], reverse=True)
    
    print(f"📊 Drift zones identified: {len(drift_zones)}")
    return drift_zones

def create_rri_timeline(results_df, drift_zones):
    """Create ASCII RRI timeline with two traces"""
    print(f"\n📊 **ASCII RRI Timeline**")
    print("=" * 60)
    
    # Create timeline representation
    timeline = ""
    
    for i, row in results_df.iterrows():
        timestamp = row['timestamp']
        z_e = row['Z_E']
        z_m = row['Z_M']
        
        # Check if this hour is in any drift zone
        in_zone = any(
            zone['start_utc'] <= timestamp <= zone['end_utc'] 
            for zone in drift_zones
        )
        
        # Energy Distance (solid line)
        if z_e > 2:
            e_char = "█"
        elif z_e > 1.5:
            e_char = "▇"
        elif z_e > 1:
            e_char = "▆"
        elif z_e > 0.5:
            e_char = "▅"
        elif z_e > 0:
            e_char = "▄"
        elif z_e > -0.5:
            e_char = "▃"
        elif z_e > -1:
            e_char = "▂"
        else:
            e_char = "▁"
        
        # MMD (dotted line)
        if z_m > 2:
            m_char = "▓"
        elif z_m > 1.5:
            m_char = "▒"
        elif z_m > 1:
            m_char = "░"
        elif z_m > 0.5:
            m_char = "·"
        elif z_m > 0:
            m_char = "."
        else:
            m_char = " "
        
        # Zone shading
        if in_zone:
            timeline += f"[{e_char}{m_char}]"
        else:
            timeline += f" {e_char}{m_char} "
        
        # Add newline every 24 hours
        if (i + 1) % 24 == 0:
            timeline += "\n"
    
    return timeline

def main():
    print('🔍 Phase 37E-48h: RRI v2 - Robust/NaN-safe')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Load panel
    df = load_panel()
    if df is None:
        return
    
    # Build baseline
    df, X0 = build_baseline(df)
    if df is None:
        return
    
    # Rolling RRI analysis
    results_df, skipped_windows = rolling_rri_analysis_48h(df, X0)
    if results_df is None or len(results_df) == 0:
        print("❌ HALT: No valid windows processed")
        return
    
    # Compute Z-scores
    results_df = compute_z_scores(results_df)
    
    # Identify drift zones
    drift_zones = identify_drift_zones(results_df)
    
    # Create outputs
    print(f"\n📊 **Outputs**")
    print("=" * 60)
    
    # ASCII RRI timeline
    timeline = create_rri_timeline(results_df, drift_zones)
    print(timeline)
    
    # Top-5 drift zones table
    if drift_zones:
        print(f"\n📊 **Top-5 Drift Zones:**")
        top_zones = drift_zones[:5]
        for i, zone in enumerate(top_zones, 1):
            print(f"Zone {i}: {zone['start_utc']} → {zone['end_utc']} "
                  f"({zone['duration_h']:.1f}h, Z_E={zone['mean_ZE']:.2f}, "
                  f"Z_M={zone['mean_ZM']:.2f})")
    
    # NaN diagnostics
    print(f"\n📊 **NaN Diagnostics:**")
    print(f"   Windows skipped: {len(skipped_windows)}")
    if skipped_windows:
        print(f"   First 5 examples:")
        for i, skip in enumerate(skipped_windows[:5]):
            print(f"     {i+1}. {skip['timestamp']} (nan_rate: {skip.get('nan_rate', 'N/A'):.3f})")
    
    # Per-feature NaN rates
    features = ['entropy', 'ofi', 'vol_proxy']
    print(f"   Per-feature NaN rates:")
    for feature in features:
        baseline_nan = np.isnan(X0[:, features.index(feature)]).mean() * 100
        full_nan = df[feature].isna().mean() * 100
        print(f"     {feature}: baseline={baseline_nan:.2f}%, full={full_nan:.2f}%")
    
    # JSON payload
    print(f"\n📊 **JSON Payload:**")
    
    # Create RRI series
    rri_series = []
    for _, row in results_df.iterrows():
        rri_series.append({
            "t": row['timestamp'].isoformat(),
            "ZE": float(row['Z_E']),
            "ZM": float(row['Z_M']),
            "Zavg": float(row['Z_avg'])
        })
    
    json_payload = {
        "rri_series": rri_series,
        "rri_zones": drift_zones,
        "nan_report": {
            "windows_skipped": len(skipped_windows),
            "examples": [skip['timestamp'].isoformat() for skip in skipped_windows[:5]],
            "feature_nan_rates": {
                feature: float(np.isnan(X0[:, features.index(feature)]).mean() * 100)
                for feature in features
            }
        }
    }
    print(json.dumps(json_payload, indent=2, default=str))
    
    # Verdict
    if len(drift_zones) >= 1:
        print(f"\n✅ **ACCEPT — gradual structural drift detected; hand off to 38A using these zone bounds.**")
        
        # Handoff to next phases
        print(f"\n📊 **Phase 37E-48h → Phase 38A handoff:**")
        for i, zone in enumerate(drift_zones[:3], 1):
            print(f"   Zone {i}: {zone['start_utc']} → {zone['end_utc']} "
                  f"(Z_E={zone['mean_ZE']:.2f}, Z_M={zone['mean_ZM']:.2f})")
    else:
        print(f"\n❌ **REJECT — no robust drift zones; emit rri_series for 42A (HMM) and 41 (synthetic control).**")
        print(f"📊 **RRI Series Available:** {len(rri_series)} data points for downstream analysis")

if __name__ == '__main__':
    main()
