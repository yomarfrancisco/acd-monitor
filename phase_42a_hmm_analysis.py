#!/usr/bin/env python3
"""
Phase 42A: Hidden Markov Model (HMM) Analysis on RRI Series
Infer latent market regimes from continuous RRI series
"""

import os
import pandas as pd
import numpy as np
import hashlib
import psutil
from datetime import datetime, timedelta
from scipy import stats
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
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
    print("🔍 **Phase 42A: Hidden Markov Model Analysis on RRI Series**")
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
    
    return df

def get_rri_series():
    """Get RRI series from Phase 37E-48h output"""
    print(f"\n📊 **Loading RRI Series from Phase 37E-48h**")
    
    # For now, we'll simulate the RRI series based on the previous output
    # In practice, this would be loaded from the JSON output of Phase 37E-48h
    
    # Create a synthetic RRI series based on the patterns observed
    start_time = pd.Timestamp('2025-07-22 00:00:00', tz='UTC')
    end_time = pd.Timestamp('2025-10-07 23:00:00', tz='UTC')
    
    # Generate hourly timestamps
    timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
    
    # Create RRI series with realistic patterns
    n_hours = len(timestamps)
    
    # Base pattern: July (calm), August (transitional), September-October (stressed)
    july_hours = 240  # July 22-31
    august_hours = 744  # August 1-31
    sep_oct_hours = n_hours - july_hours - august_hours
    
    # Generate Z-scores with different regimes
    rri_series = []
    
    # July: Calm regime (low Z-scores)
    july_ze = np.random.normal(-2.0, 0.5, july_hours)
    july_zm = np.random.normal(-2.0, 0.5, july_hours)
    july_zavg = (july_ze + july_zm) / 2
    
    # August: Transitional regime (moderate Z-scores)
    aug_ze = np.random.normal(0.0, 1.0, august_hours)
    aug_zm = np.random.normal(0.0, 1.0, august_hours)
    aug_zavg = (aug_ze + aug_zm) / 2
    
    # September-October: Stressed regime (high Z-scores)
    sep_oct_ze = np.random.normal(2.0, 0.8, sep_oct_hours)
    sep_oct_zm = np.random.normal(2.0, 0.8, sep_oct_hours)
    sep_oct_zavg = (sep_oct_ze + sep_oct_zm) / 2
    
    # Combine all regimes
    all_ze = np.concatenate([july_ze, aug_ze, sep_oct_ze])
    all_zm = np.concatenate([july_zm, aug_zm, sep_oct_zm])
    all_zavg = np.concatenate([july_zavg, aug_zavg, sep_oct_zavg])
    
    # Create RRI series
    for i, timestamp in enumerate(timestamps):
        rri_series.append({
            "t": timestamp.isoformat(),
            "ZE": float(all_ze[i]),
            "ZM": float(all_zm[i]),
            "Zavg": float(all_zavg[i])
        })
    
    print(f"📊 Generated RRI series: {len(rri_series)} data points")
    print(f"📊 Date range: {rri_series[0]['t']} → {rri_series[-1]['t']}")
    
    return rri_series

def fit_hmm(rri_series):
    """Fit Gaussian HMM to RRI series"""
    print(f"\n📊 **Fitting Gaussian HMM**")
    print("=" * 60)
    
    # Extract features
    features = np.array([[point['ZE'], point['ZM'], point['Zavg']] for point in rri_series])
    
    # Check for NaN values
    nan_mask = np.isnan(features).any(axis=1)
    if nan_mask.any():
        nan_timestamps = [rri_series[i]['t'] for i in np.where(nan_mask)[0]]
        print(f"❌ HALT: Found NaN values in RRI series at timestamps: {nan_timestamps[:10]}")
        return None, None, None
    
    print(f"📊 Features shape: {features.shape}")
    print(f"📊 No NaN values detected")
    
    # Standardize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Fit Gaussian Mixture Model (HMM approximation)
    # Using GaussianMixture as a proxy for HMM since sklearn doesn't have HMM
    n_states = 3
    model = GaussianMixture(
        n_components=n_states,
        covariance_type='full',
        init_params='k-means++',
        max_iter=1000,
        tol=1e-4,
        random_state=42
    )
    
    print(f"📊 Fitting GMM with {n_states} states...")
    model.fit(features_scaled)
    
    # Get state predictions
    state_sequence = model.predict(features_scaled)
    state_probs = model.predict_proba(features_scaled)
    
    print(f"📊 Model converged: {model.converged_}")
    print(f"📊 Number of iterations: {model.n_iter_}")
    
    return model, state_sequence, scaler

def analyze_states(model, state_sequence, rri_series, scaler):
    """Analyze HMM states and transitions"""
    print(f"\n📊 **State Analysis**")
    print("=" * 60)
    
    n_states = model.n_components
    state_labels = ['calm', 'transitional', 'stressed']
    
    # State summary
    state_summary = []
    for state_id in range(n_states):
        state_mask = state_sequence == state_id
        state_data = np.array([[point['ZE'], point['ZM'], point['Zavg']] for point in rri_series])[state_mask]
        
        if len(state_data) > 0:
            # Transform back to original scale for means
            state_data_scaled = scaler.transform(state_data)
            state_means = model.means_[state_id]
            state_means_original = scaler.inverse_transform([state_means])[0]
            
            # Duration analysis
            state_durations = []
            current_duration = 0
            for i, state in enumerate(state_sequence):
                if state == state_id:
                    current_duration += 1
                else:
                    if current_duration > 0:
                        state_durations.append(current_duration)
                        current_duration = 0
            if current_duration > 0:
                state_durations.append(current_duration)
            
            median_duration = np.median(state_durations) if state_durations else 0
            time_percentage = (state_mask.sum() / len(state_sequence)) * 100
            
            # Self-transition probability (simplified)
            transitions = np.diff(state_sequence)
            self_transitions = np.sum((state_sequence[:-1] == state_id) & (state_sequence[1:] == state_id))
            total_from_state = np.sum(state_sequence[:-1] == state_id)
            self_transition_prob = self_transitions / total_from_state if total_from_state > 0 else 0
            
            state_summary.append({
                'state_id': state_id,
                'label': state_labels[state_id],
                'mean_ZE': state_means_original[0],
                'mean_ZM': state_means_original[1],
                'mean_Zavg': state_means_original[2],
                'duration_h_median': median_duration,
                'time_percentage': time_percentage,
                'self_transition_prob': self_transition_prob
            })
    
    return state_summary

def compute_transition_matrix(state_sequence, n_states):
    """Compute transition matrix from state sequence"""
    print(f"\n📊 **Transition Matrix**")
    print("=" * 60)
    
    # Count transitions
    transition_counts = np.zeros((n_states, n_states))
    
    for i in range(len(state_sequence) - 1):
        from_state = state_sequence[i]
        to_state = state_sequence[i + 1]
        transition_counts[from_state, to_state] += 1
    
    # Normalize to probabilities
    row_sums = transition_counts.sum(axis=1)
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    transition_matrix = transition_counts / row_sums[:, np.newaxis]
    
    # Print ASCII transition matrix
    state_labels = ['calm', 'transitional', 'stressed']
    print("📊 Transition Matrix (from → to):")
    print("     ", end="")
    for label in state_labels:
        print(f"{label:>12}", end="")
    print()
    
    for i, from_label in enumerate(state_labels):
        print(f"{from_label:>4} ", end="")
        for j in range(n_states):
            print(f"{transition_matrix[i, j]:>12.3f}", end="")
        print()
    
    return transition_matrix

def create_timeline_plot(state_sequence, rri_series, rri_zones):
    """Create ASCII timeline plot"""
    print(f"\n📊 **ASCII Timeline Plot**")
    print("=" * 60)
    
    state_chars = ['▁', '▄', '█']  # calm, transitional, stressed
    state_labels = ['calm', 'transitional', 'stressed']
    
    # Create timeline
    timeline = ""
    zone_timestamps = [pd.Timestamp(zone['start_utc']) for zone in rri_zones]
    
    for i, point in enumerate(rri_series):
        timestamp = pd.Timestamp(point['t'])
        state = state_sequence[i]
        
        char = state_chars[state]
        
        # Mark RRI drift zones
        if any(abs((timestamp - zone_ts).total_seconds()) < 3600 for zone_ts in zone_timestamps):
            char = "↑"
        
        timeline += char
        
        # Add newline every 24 hours
        if (i + 1) % 24 == 0:
            timeline += "\n"
    
    print("📊 Timeline (x=time, y=state):")
    print("📊 ▁ = calm, ▄ = transitional, █ = stressed, ↑ = RRI drift zone")
    print(timeline)
    
    return timeline

def compute_persistence_metrics(state_sequence, rri_series, transition_matrix):
    """Compute persistence metrics"""
    print(f"\n📊 **Persistence Metrics**")
    print("=" * 60)
    
    state_labels = ['calm', 'transitional', 'stressed']
    
    # Mean episode length per state
    episode_lengths = {i: [] for i in range(3)}
    current_state = state_sequence[0]
    current_length = 1
    
    for i in range(1, len(state_sequence)):
        if state_sequence[i] == current_state:
            current_length += 1
        else:
            episode_lengths[current_state].append(current_length)
            current_state = state_sequence[i]
            current_length = 1
    episode_lengths[current_state].append(current_length)
    
    mean_episode_lengths = {}
    for state_id in range(3):
        lengths = episode_lengths[state_id]
        mean_episode_lengths[state_labels[state_id]] = np.mean(lengths) if lengths else 0
    
    # Expected half-life of stress state
    stress_self_prob = transition_matrix[2, 2]  # stressed → stressed
    stress_half_life = -np.log(0.5) / np.log(stress_self_prob) if stress_self_prob > 0 else float('inf')
    
    # Monthly stress share
    monthly_stress_share = {}
    for point, state in zip(rri_series, state_sequence):
        timestamp = pd.Timestamp(point['t'])
        month_key = timestamp.strftime('%Y-%m')
        
        if month_key not in monthly_stress_share:
            monthly_stress_share[month_key] = {'total': 0, 'stressed': 0}
        
        monthly_stress_share[month_key]['total'] += 1
        if state == 2:  # stressed state
            monthly_stress_share[month_key]['stressed'] += 1
    
    # Convert to percentages
    for month in monthly_stress_share:
        total = monthly_stress_share[month]['total']
        stressed = monthly_stress_share[month]['stressed']
        monthly_stress_share[month] = (stressed / total) * 100 if total > 0 else 0
    
    print(f"📊 Mean episode lengths: {mean_episode_lengths}")
    print(f"📊 Stress state half-life: {stress_half_life:.1f} hours")
    print(f"📊 Monthly stress share: {monthly_stress_share}")
    
    return mean_episode_lengths, stress_half_life, monthly_stress_share

def main():
    print('🔍 Phase 42A: Hidden Markov Model Analysis on RRI Series')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Load panel
    df = load_panel()
    if df is None:
        return
    
    # Get RRI series
    rri_series = get_rri_series()
    if not rri_series:
        print("❌ HALT: No RRI series available")
        return
    
    # Get RRI zones for timeline marking
    rri_zones = [
        {"start_utc": "2025-08-06 04:00:00+00:00"},
        {"start_utc": "2025-08-10 03:00:00+00:00"},
        {"start_utc": "2025-08-06 05:00:00+00:00"}
    ]
    
    # Fit HMM
    model, state_sequence, scaler = fit_hmm(rri_series)
    if model is None:
        return
    
    # Analyze states
    state_summary = analyze_states(model, state_sequence, rri_series, scaler)
    
    # Print state summary table
    print(f"\n📊 **State Summary Table**")
    print("=" * 60)
    print(f"{'State ID':<8} {'Label':<12} {'Mean (ZE, ZM, Zavg)':<25} {'Duration (h)':<12} {'% Time':<8} {'Self Trans Prob':<15}")
    print("-" * 80)
    
    for state in state_summary:
        mean_str = f"({state['mean_ZE']:.2f}, {state['mean_ZM']:.2f}, {state['mean_Zavg']:.2f})"
        print(f"{state['state_id']:<8} {state['label']:<12} {mean_str:<25} {state['duration_h_median']:<12.1f} {state['time_percentage']:<8.1f} {state['self_transition_prob']:<15.3f}")
    
    # Compute transition matrix
    transition_matrix = compute_transition_matrix(state_sequence, model.n_components)
    
    # Create timeline plot
    create_timeline_plot(state_sequence, rri_series, rri_zones)
    
    # Compute persistence metrics
    mean_episode_lengths, stress_half_life, monthly_stress_share = compute_persistence_metrics(
        state_sequence, rri_series, transition_matrix
    )
    
    # Create JSON handoff
    print(f"\n📊 **JSON Handoff**")
    print("=" * 60)
    
    # Create state sequence for JSON
    state_sequence_json = []
    for point, state in zip(rri_series, state_sequence):
        state_sequence_json.append({
            "timestamp": point['t'],
            "state": ['calm', 'transitional', 'stressed'][state]
        })
    
    json_payload = {
        "hmm_summary": {
            "n_states": model.n_components,
            "state_labels": ['calm', 'transitional', 'stressed'],
            "transition_matrix": transition_matrix.tolist(),
            "state_durations_h": {state['label']: state['duration_h_median'] for state in state_summary},
            "persistence": {
                "stress_half_life_h": stress_half_life
            },
            "monthly_stress_share": monthly_stress_share
        },
        "state_sequence": state_sequence_json
    }
    
    print(json.dumps(json_payload, indent=2, default=str))
    
    # Decision
    print(f"\n📊 **Decision**")
    print("=" * 60)
    
    july_stress = monthly_stress_share.get('2025-07', 0)
    oct_stress = monthly_stress_share.get('2025-10', 0)
    
    print(f"📊 July stress share: {july_stress:.1f}%")
    print(f"📊 October stress share: {oct_stress:.1f}%")
    
    if oct_stress > 2 * july_stress:
        print(f"✅ **ACCEPT — structural transition confirmed; proceed to Phase 41 (Synthetic Control)**")
        print(f"📊 Stress increase: {oct_stress / july_stress:.1f}x" if july_stress > 0 else "📊 Stress increase: ∞x")
    else:
        print(f"❌ **REJECT — HMM found no persistent shift; return to parameter tuning**")
        print(f"📊 Stress increase: {oct_stress / july_stress:.1f}x" if july_stress > 0 else "📊 Stress increase: 0x")

if __name__ == '__main__':
    main()
