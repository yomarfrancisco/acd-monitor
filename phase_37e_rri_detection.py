#!/usr/bin/env python3
"""
Phase 37E: Rolling Regime Invariance (RRI - Energy Distance + MMD)
Measure gradual structural change from July baseline using overlapping 36h windows
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
    print("🔍 **Phase 37E: Rolling Regime Invariance (RRI)**")
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
    """Build July baseline (July 22-31)"""
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
    nan_mask = np.isnan(X0).any(axis=1)
    if nan_mask.any():
        print(f"❌ HALT: Found NaN values in baseline features")
        nan_timestamps = july_data[nan_mask]['timestamp'].tolist()
        print(f"📊 NaN timestamps: {nan_timestamps[:10]}...")
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

def compute_energy_distance(X1, X2):
    """Compute Energy Distance between two feature matrices"""
    # E = 2 * E[||X1 - X2||] - E[||X1 - X1'||] - E[||X2 - X2'||]
    
    # Handle NaN values by filling with column means
    X1_clean = X1.copy()
    X2_clean = X2.copy()
    
    for i in range(X1_clean.shape[1]):
        if np.isnan(X1_clean[:, i]).any():
            X1_clean[:, i] = np.nan_to_num(X1_clean[:, i], nan=np.nanmean(X1_clean[:, i]))
        if np.isnan(X2_clean[:, i]).any():
            X2_clean[:, i] = np.nan_to_num(X2_clean[:, i], nan=np.nanmean(X2_clean[:, i]))
    
    # Pairwise distances within X1
    dist_X1_X1 = pairwise_distances(X1_clean, metric='euclidean')
    np.fill_diagonal(dist_X1_X1, 0)  # Remove diagonal
    E_X1_X1 = np.mean(dist_X1_X1)
    
    # Pairwise distances within X2
    dist_X2_X2 = pairwise_distances(X2_clean, metric='euclidean')
    np.fill_diagonal(dist_X2_X2, 0)  # Remove diagonal
    E_X2_X2 = np.mean(dist_X2_X2)
    
    # Cross distances between X1 and X2
    dist_X1_X2 = pairwise_distances(X1_clean, X2_clean, metric='euclidean')
    E_X1_X2 = np.mean(dist_X1_X2)
    
    # Energy distance
    energy_dist = 2 * E_X1_X2 - E_X1_X1 - E_X2_X2
    
    return energy_dist

def compute_mmd(X1, X2, sigma=None):
    """Compute Maximum Mean Discrepancy (MMD²) using Gaussian RBF kernel"""
    # Handle NaN values by filling with column means
    X1_clean = X1.copy()
    X2_clean = X2.copy()
    
    for i in range(X1_clean.shape[1]):
        if np.isnan(X1_clean[:, i]).any():
            X1_clean[:, i] = np.nan_to_num(X1_clean[:, i], nan=np.nanmean(X1_clean[:, i]))
        if np.isnan(X2_clean[:, i]).any():
            X2_clean[:, i] = np.nan_to_num(X2_clean[:, i], nan=np.nanmean(X2_clean[:, i]))
    
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

def generate_null_controls(df, window_size=36):
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

def rolling_rri_analysis(df, X0, window_size=36, stride=1):
    """Perform rolling RRI analysis"""
    print(f"\n📊 **Rolling RRI Analysis**")
    print("=" * 60)
    
    features = ['entropy', 'ofi', 'vol_proxy']
    
    # Generate null controls
    circular_shift, block_perm = generate_null_controls(df, window_size)
    
    # Rolling window analysis
    results = []
    total_windows = len(df) - window_size + 1
    
    print(f"📊 Processing {total_windows} windows (36h each, 1h stride)...")
    
    for i in range(0, total_windows, stride):
        if i % 1000 == 0:
            print(f"📊 Progress: {i}/{total_windows} windows")
        
        # Current window
        window_data = df.iloc[i:i+window_size]
        X_t = window_data[features].values
        
        # Check for NaN values - skip windows with NaN
        if np.isnan(X_t).any():
            print(f"⚠️ Skipping window {i} due to NaN values")
            continue
        
        # Compute Energy Distance
        E_t = compute_energy_distance(X_t, X0)
        
        # Compute MMD
        M_t, sigma = compute_mmd(X_t, X0)
        
        # Null controls for current window
        # Circular shift window
        circ_window = circular_shift.iloc[i:i+window_size]
        X_circ = circ_window[features].values
        if np.isnan(X_circ).any():
            print(f"⚠️ Skipping circular shift for window {i} due to NaN values")
            continue
        
        E_circ = compute_energy_distance(X_circ, X0)
        M_circ, _ = compute_mmd(X_circ, X0, sigma)
        
        # Block permutation window
        perm_window = block_perm.iloc[i:i+window_size]
        X_perm = perm_window[features].values
        if np.isnan(X_perm).any():
            print(f"⚠️ Skipping block permutation for window {i} due to NaN values")
            continue
        
        E_perm = compute_energy_distance(X_perm, X0)
        M_perm, _ = compute_mmd(X_perm, X0, sigma)
        
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
    
    return pd.DataFrame(results)

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
    
    print(f"📊 Energy Distance: mean={E_mean:.6f}, std={E_std:.6f}")
    print(f"📊 MMD: mean={M_mean:.6f}, std={M_std:.6f}")
    
    return results_df

def identify_drift_zones(results_df, threshold=1.8):
    """Identify drift zones based on decision rules"""
    print(f"\n📊 **Identifying Drift Zones**")
    print("=" * 60)
    
    # Decision rule: Z_E > +1.8 and Z_M > +1.8 and both real > null means + 1 SD
    divergent_mask = (
        (results_df['Z_E'] > threshold) & 
        (results_df['Z_M'] > threshold) &
        (results_df['E_t'] > results_df['E_circ'].mean() + results_df['E_circ'].std()) &
        (results_df['E_t'] > results_df['E_perm'].mean() + results_df['E_perm'].std()) &
        (results_df['M_t'] > results_df['M_circ'].mean() + results_df['M_circ'].std()) &
        (results_df['M_t'] > results_df['M_perm'].mean() + results_df['M_perm'].std())
    )
    
    divergent_windows = results_df[divergent_mask].copy()
    print(f"📊 Divergent windows: {len(divergent_windows)}")
    
    if len(divergent_windows) == 0:
        return []
    
    # Cluster consecutive divergent windows (gap ≤ 3h)
    timestamps = divergent_windows['timestamp'].values
    clustering = DBSCAN(eps=3, min_samples=1).fit(timestamps.reshape(-1, 1))
    
    # Group by cluster
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(divergent_windows.iloc[i])
    
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
        
        drift_zones.append({
            'start_utc': start_time,
            'end_utc': end_time,
            'duration_h': duration_h,
            'mean_ZE': mean_Z_E,
            'mean_ZM': mean_Z_M,
            'real_vs_null': {
                'energy_pass': energy_pass,
                'mmd_pass': mmd_pass
            }
        })
    
    # Sort by mean Z-score
    drift_zones.sort(key=lambda x: x['mean_ZE'] + x['mean_ZM'], reverse=True)
    
    print(f"📊 Drift zones identified: {len(drift_zones)}")
    return drift_zones

def create_rri_curve(results_df, drift_zones):
    """Create ASCII RRI curve"""
    print(f"\n📊 **ASCII RRI Curve**")
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
    print('🔍 Phase 37E: Rolling Regime Invariance (RRI)')
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
    results_df = rolling_rri_analysis(df, X0)
    if results_df is None:
        return
    
    # Compute Z-scores
    results_df = compute_z_scores(results_df)
    
    # Identify drift zones
    drift_zones = identify_drift_zones(results_df)
    
    # Create outputs
    print(f"\n📊 **Outputs**")
    print("=" * 60)
    
    # ASCII RRI curve
    timeline = create_rri_curve(results_df, drift_zones)
    print(timeline)
    
    # Top-5 drift zones table
    if drift_zones:
        print(f"\n📊 **Top-5 Drift Zones:**")
        top_zones = drift_zones[:5]
        for i, zone in enumerate(top_zones, 1):
            print(f"Zone {i}: {zone['start_utc']} → {zone['end_utc']} "
                  f"({zone['duration_h']:.1f}h, Z_E={zone['mean_ZE']:.2f}, "
                  f"Z_M={zone['mean_ZM']:.2f})")
    
    # JSON payload
    print(f"\n📊 **JSON Payload:**")
    json_payload = {
        "rri_zones": drift_zones,
        "scaling_summary": {
            "entropy": {"mean": float(X0[:, 0].mean()), "std": float(X0[:, 0].std())},
            "ofi": {"mean": float(X0[:, 1].mean()), "std": float(X0[:, 1].std())},
            "vol_proxy": {"mean": float(X0[:, 2].mean()), "std": float(X0[:, 2].std())}
        }
    }
    print(json.dumps(json_payload, indent=2, default=str))
    
    # Verdict
    if len(drift_zones) >= 1:
        print(f"\n✅ **ACCEPT – Gradual structural shift detected; hand off to Phase 38A (Recovery Typology).**")
        
        # Handoff to next phases
        print(f"\n📊 **Phase 37E → Phase 38A handoff:**")
        for i, zone in enumerate(drift_zones[:3], 1):
            print(f"   Zone {i}: {zone['start_utc']} → {zone['end_utc']} "
                  f"(Z_E={zone['mean_ZE']:.2f}, Z_M={zone['mean_ZM']:.2f})")
    else:
        print(f"\n❌ **REJECT – No distributional divergence; extend baseline or increase window to 48h.**")

if __name__ == '__main__':
    main()
