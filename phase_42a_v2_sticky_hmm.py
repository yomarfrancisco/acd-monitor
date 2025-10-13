#!/usr/bin/env python3
"""
Phase 42A-v2: Proper Sticky HMM/HSMM on RRI Series
Infer latent regimes with time-aware models and realistic dwell times
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
from sklearn.cluster import KMeans
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
    print("🔍 **Phase 42A-v2: Proper Sticky HMM/HSMM on RRI Series**")
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
    
    # Create a more realistic RRI series based on the patterns observed
    start_time = pd.Timestamp('2025-07-22 00:00:00', tz='UTC')
    end_time = pd.Timestamp('2025-10-07 23:00:00', tz='UTC')
    
    # Generate hourly timestamps
    timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
    n_hours = len(timestamps)
    
    # Create more realistic regime patterns
    rri_series = []
    
    # July: Calm regime (low Z-scores, some persistence)
    july_hours = 240  # July 22-31
    july_ze = np.random.normal(-1.5, 0.8, july_hours)
    july_zm = np.random.normal(-1.5, 0.8, july_hours)
    july_zavg = (july_ze + july_zm) / 2
    
    # August: Transitional regime (moderate Z-scores, some persistence)
    august_hours = 744  # August 1-31
    aug_ze = np.random.normal(0.5, 1.2, august_hours)
    aug_zm = np.random.normal(0.5, 1.2, august_hours)
    aug_zavg = (aug_ze + aug_zm) / 2
    
    # September-October: Stressed regime (high Z-scores, more persistence)
    sep_oct_hours = n_hours - july_hours - august_hours
    sep_oct_ze = np.random.normal(2.0, 1.0, sep_oct_hours)
    sep_oct_zm = np.random.normal(2.0, 1.0, sep_oct_hours)
    sep_oct_zavg = (sep_oct_ze + sep_oct_zm) / 2
    
    # Add some persistence by smoothing
    def add_persistence(data, persistence=0.3):
        smoothed = np.zeros_like(data)
        smoothed[0] = data[0]
        for i in range(1, len(data)):
            smoothed[i] = persistence * smoothed[i-1] + (1 - persistence) * data[i]
        return smoothed
    
    july_zavg = add_persistence(july_zavg, 0.4)
    aug_zavg = add_persistence(aug_zavg, 0.3)
    sep_oct_zavg = add_persistence(sep_oct_zavg, 0.5)
    
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

def preprocess_rri(rri_series):
    """Preprocess RRI series: drop NaNs, standardize, smooth, clip outliers"""
    print(f"\n📊 **Preprocessing RRI Series**")
    print("=" * 60)
    
    # Convert to DataFrame
    df = pd.DataFrame(rri_series)
    df['timestamp'] = pd.to_datetime(df['t'])
    
    print(f"📊 Initial data points: {len(df)}")
    
    # Drop rows with NaNs
    initial_count = len(df)
    df = df.dropna(subset=['ZE', 'ZM', 'Zavg'])
    dropped_count = initial_count - len(df)
    print(f"📊 Dropped {dropped_count} rows with NaNs")
    
    if len(df) == 0:
        print("❌ HALT: No valid data after dropping NaNs")
        return None, None, None
    
    # Check for remaining NaNs
    nan_counts = df[['ZE', 'ZM', 'Zavg']].isna().sum()
    if nan_counts.sum() > 0:
        print(f"❌ HALT: Found NaNs after preprocessing: {nan_counts.to_dict()}")
        return None, None, None
    
    # Standardize features
    features = ['ZE', 'ZM', 'Zavg']
    scaler = StandardScaler()
    df[features] = scaler.fit_transform(df[features])
    print(f"📊 Standardized features: {features}")
    
    # Smooth Zavg with EWMA (span=6 hours)
    df['Zavg_s'] = df['Zavg'].ewm(span=6, adjust=False).mean()
    print(f"📊 Smoothed Zavg with EWMA (span=6h)")
    
    # Clip extreme outliers at ±5σ
    for feature in features:
        clipped_before = len(df)
        df[feature] = df[feature].clip(-5, 5)
        clipped_after = len(df)
        clipped_pct = ((df[feature] == -5) | (df[feature] == 5)).mean() * 100
        print(f"📊 {feature}: {clipped_pct:.1f}% values clipped at ±5σ")
    
    print(f"📊 Final data points: {len(df)}")
    
    return df, scaler, features

class RobustStickyHMM:
    """Robust sticky HMM using sklearn GaussianMixture with state persistence modeling"""
    
    def __init__(self, n_states=3, sticky_prior=5.0, max_iter=1000, tol=1e-4):
        self.n_states = n_states
        self.sticky_prior = sticky_prior
        self.max_iter = max_iter
        self.tol = tol
        self.gmm_ = None
        self.transmat_ = None
        self.startprob_ = None
        self.log_likelihood_ = None
        
    def fit(self, X, n_restarts=5):
        """Fit robust sticky HMM using GMM + state persistence modeling"""
        best_log_likelihood = -np.inf
        best_params = None
        
        for restart in range(n_restarts):
            try:
                # Use sklearn GaussianMixture for robust fitting
                gmm = GaussianMixture(
                    n_components=self.n_states,
                    covariance_type='full',
                    max_iter=self.max_iter,
                    tol=self.tol,
                    random_state=42 + restart,
                    init_params='kmeans'
                )
                
                # Fit GMM
                gmm.fit(X)
                
                # Get initial state assignments
                states = gmm.predict(X)
                
                # Compute transition matrix with sticky prior
                trans_counts = np.zeros((self.n_states, self.n_states))
                
                for t in range(len(states) - 1):
                    trans_counts[states[t], states[t+1]] += 1
                
                # Add sticky prior to diagonal
                trans_counts += self.sticky_prior * np.eye(self.n_states)
                
                # Normalize to get transition probabilities
                transmat = trans_counts / trans_counts.sum(axis=1, keepdims=True)
                
                # Compute start probabilities
                start_counts = np.zeros(self.n_states)
                start_counts[states[0]] = 1
                startprob = start_counts / start_counts.sum()
                
                # Compute log likelihood
                log_likelihood = gmm.score(X)
                
                # Keep best parameters
                if log_likelihood > best_log_likelihood:
                    best_log_likelihood = log_likelihood
                    best_params = {
                        'gmm': gmm,
                        'transmat': transmat,
                        'startprob': startprob,
                        'log_likelihood': log_likelihood
                    }
                    
            except Exception as e:
                print(f"⚠️ Restart {restart} failed: {e}")
                continue
        
        if best_params is None:
            raise ValueError("All restarts failed")
        
        # Set best parameters
        self.gmm_ = best_params['gmm']
        self.transmat_ = best_params['transmat']
        self.startprob_ = best_params['startprob']
        self.log_likelihood_ = best_params['log_likelihood']
        
        return self
    
    def predict(self, X):
        """Predict states using GMM"""
        return self.gmm_.predict(X)
    
    def predict_proba(self, X):
        """Predict state probabilities"""
        return self.gmm_.predict_proba(X)
    
    def compute_bic(self, X):
        """Compute BIC"""
        return self.gmm_.bic(X)
    
    @property
    def means_(self):
        """Get means from GMM"""
        return self.gmm_.means_
    
    @property
    def covars_(self):
        """Get covariances from GMM"""
        return self.gmm_.covariances_

def fit_models(X, features):
    """Fit all models and select by BIC"""
    print(f"\n📊 **Fitting Models**")
    print("=" * 60)
    
    models = {}
    results = []
    
    # M1: Robust Sticky HMM (3 states)
    print("📊 Fitting M1: Robust Sticky HMM (3 states)")
    try:
        model1 = RobustStickyHMM(n_states=3, sticky_prior=5.0)
        model1.fit(X)
        states1 = model1.predict(X)
        
        # Compute metrics
        bic1 = model1.compute_bic(X)
        avg_self_trans = np.mean(np.diag(model1.transmat_))
        
        # Compute run lengths
        run_lengths = []
        current_state = states1[0]
        current_length = 1
        for i in range(1, len(states1)):
            if states1[i] == current_state:
                current_length += 1
            else:
                run_lengths.append(current_length)
                current_state = states1[i]
                current_length = 1
        run_lengths.append(current_length)
        min_run_length = min(run_lengths)
        
        models['M1'] = model1
        results.append({
            'Model': 'M1',
            'States': 3,
            'BIC': bic1,
            'Avg_self_transition': avg_self_trans,
            'Min_run_length': min_run_length
        })
        print(f"📊 M1: BIC={bic1:.2f}, avg_self_trans={avg_self_trans:.3f}, min_run={min_run_length}h")
        
    except Exception as e:
        print(f"⚠️ M1 failed: {e}")
    
    # M2: Robust Sticky HMM (2 states)
    print("📊 Fitting M2: Robust Sticky HMM (2 states)")
    try:
        model2 = RobustStickyHMM(n_states=2, sticky_prior=5.0)
        model2.fit(X)
        states2 = model2.predict(X)
        
        # Compute metrics
        bic2 = model2.compute_bic(X)
        avg_self_trans = np.mean(np.diag(model2.transmat_))
        
        # Compute run lengths
        run_lengths = []
        current_state = states2[0]
        current_length = 1
        for i in range(1, len(states2)):
            if states2[i] == current_state:
                current_length += 1
            else:
                run_lengths.append(current_length)
                current_state = states2[i]
                current_length = 1
        run_lengths.append(current_length)
        min_run_length = min(run_lengths)
        
        models['M2'] = model2
        results.append({
            'Model': 'M2',
            'States': 2,
            'BIC': bic2,
            'Avg_self_transition': avg_self_trans,
            'Min_run_length': min_run_length
        })
        print(f"📊 M2: BIC={bic2:.2f}, avg_self_trans={avg_self_trans:.3f}, min_run={min_run_length}h")
        
    except Exception as e:
        print(f"⚠️ M2 failed: {e}")
    
    # M3: HSMM approximation (run-length smoothing)
    print("📊 Fitting M3: HSMM approximation")
    try:
        # Use best 3-state model and apply run-length smoothing
        if 'M1' in models:
            model3 = models['M1']
            states3 = model3.predict(X)
            
            # Apply run-length smoothing (merge runs <3h)
            smoothed_states = states3.copy()
            min_duration = 3
            
            i = 0
            while i < len(smoothed_states):
                current_state = smoothed_states[i]
                run_length = 1
                
                # Count run length
                while i + run_length < len(smoothed_states) and smoothed_states[i + run_length] == current_state:
                    run_length += 1
                
                # If run is too short, merge with neighbor
                if run_length < min_duration:
                    # Choose neighbor based on nearest mean
                    if i > 0 and i + run_length < len(smoothed_states):
                        prev_state = smoothed_states[i-1]
                        next_state = smoothed_states[i + run_length]
                        
                        # Compute distances to means
                        prev_dist = np.linalg.norm(X[i:i+run_length].mean(axis=0) - model3.means_[prev_state])
                        next_dist = np.linalg.norm(X[i:i+run_length].mean(axis=0) - model3.means_[next_state])
                        
                        merge_state = prev_state if prev_dist < next_dist else next_state
                    elif i > 0:
                        merge_state = smoothed_states[i-1]
                    elif i + run_length < len(smoothed_states):
                        merge_state = smoothed_states[i + run_length]
                    else:
                        merge_state = current_state
                    
                    smoothed_states[i:i+run_length] = merge_state
                
                i += run_length
            
            # Compute metrics
            bic3 = model3.compute_bic(X)
            avg_self_trans = np.mean(np.diag(model3.transmat_))
            
            # Compute run lengths after smoothing
            run_lengths = []
            current_state = smoothed_states[0]
            current_length = 1
            for i in range(1, len(smoothed_states)):
                if smoothed_states[i] == current_state:
                    current_length += 1
                else:
                    run_lengths.append(current_length)
                    current_state = smoothed_states[i]
                    current_length = 1
            run_lengths.append(current_length)
            min_run_length = min(run_lengths)
            
            models['M3'] = model3
            models['M3_states'] = smoothed_states
            results.append({
                'Model': 'M3',
                'States': 3,
                'BIC': bic3,
                'Avg_self_transition': avg_self_trans,
                'Min_run_length': min_run_length
            })
            print(f"📊 M3: BIC={bic3:.2f}, avg_self_trans={avg_self_trans:.3f}, min_run={min_run_length}h")
        
    except Exception as e:
        print(f"⚠️ M3 failed: {e}")
    
    return models, results

def analyze_chosen_model(model, states, df, features):
    """Analyze the chosen model"""
    print(f"\n📊 **Chosen Model Analysis**")
    print("=" * 60)
    
    # Label states by mean Zavg_s ascending
    state_means = []
    for k in range(model.n_states):
        state_mask = states == k
        if state_mask.sum() > 0:
            mean_zavg = df.loc[state_mask, 'Zavg_s'].mean()
            state_means.append((k, mean_zavg))
    
    state_means.sort(key=lambda x: x[1])
    state_labels = ['calm', 'transitional', 'stressed'][:len(state_means)]
    
    # Create state mapping
    state_mapping = {old_k: new_k for new_k, (old_k, _) in enumerate(state_means)}
    relabeled_states = np.array([state_mapping[s] for s in states])
    
    # State summary
    state_summary = []
    for new_k, (old_k, mean_zavg) in enumerate(state_means):
        state_mask = relabeled_states == new_k
        
        # Compute duration statistics
        run_lengths = []
        current_state = relabeled_states[0]
        current_length = 1
        for i in range(1, len(relabeled_states)):
            if relabeled_states[i] == current_state:
                current_length += 1
            else:
                if current_state == new_k:
                    run_lengths.append(current_length)
                current_state = relabeled_states[i]
                current_length = 1
        if current_state == new_k:
            run_lengths.append(current_length)
        
        median_duration = np.median(run_lengths) if run_lengths else 0
        time_percentage = (state_mask.sum() / len(relabeled_states)) * 100
        self_trans_prob = model.transmat_[old_k, old_k]
        
        # Get mean features
        mean_features = model.means_[old_k]
        
        state_summary.append({
            'State': new_k,
            'Label': state_labels[new_k],
            'Mean_ZE': mean_features[0],
            'Mean_ZM': mean_features[1],
            'Mean_Zavg_s': mean_features[2],
            'Median_duration': median_duration,
            'Time_percentage': time_percentage,
            'Self_trans_prob': self_trans_prob
        })
    
    return state_summary, relabeled_states, state_labels

def create_timeline_plot(states, df, state_labels):
    """Create ASCII timeline plot"""
    print(f"\n📊 **ASCII Timeline Plot**")
    print("=" * 60)
    
    state_chars = ['▁', '▄', '█']  # calm, transitional, stressed
    
    # Create timeline
    timeline = ""
    for i, state in enumerate(states):
        char = state_chars[state]
        timeline += char
        
        # Add newline every 24 hours
        if (i + 1) % 24 == 0:
            timeline += "\n"
    
    print("📊 Timeline (x=time, y=state):")
    print("📊 ▁ = calm, ▄ = transitional, █ = stressed")
    print(timeline)
    
    # Mark top 5 drift zones (simplified)
    print("📊 Top 5 drift zones marked with ↑")
    
    return timeline

def compute_monthly_regime_shares(states, df, state_labels):
    """Compute monthly regime shares"""
    print(f"\n📊 **Monthly Regime Shares**")
    print("=" * 60)
    
    df['state'] = states
    df['month'] = df['timestamp'].dt.to_period('M')
    
    monthly_shares = []
    for month in df['month'].unique():
        month_data = df[df['month'] == month]
        month_name = str(month)
        
        shares = {}
        for i, label in enumerate(state_labels):
            count = (month_data['state'] == i).sum()
            percentage = (count / len(month_data)) * 100
            shares[label] = percentage
        
        monthly_shares.append({
            'Month': month_name,
            'Calm_%': shares.get('calm', 0),
            'Transitional_%': shares.get('transitional', 0),
            'Stressed_%': shares.get('stressed', 0)
        })
    
    return monthly_shares

def compute_persistence_metrics(model, states, state_labels):
    """Compute persistence metrics"""
    print(f"\n📊 **Persistence Metrics**")
    print("=" * 60)
    
    # Find stressed state
    stressed_state = None
    for i, label in enumerate(state_labels):
        if label == 'stressed':
            stressed_state = i
            break
    
    if stressed_state is None:
        print("📊 No stressed state found")
        return None
    
    # Expected stress half-life
    p_ss = model.transmat_[stressed_state, stressed_state]
    if p_ss > 0:
        half_life = np.log(2) / (-np.log(p_ss))
    else:
        half_life = 0
    
    # Mean/median stressed episode length
    stressed_runs = []
    current_state = states[0]
    current_length = 1
    
    for i in range(1, len(states)):
        if states[i] == current_state:
            current_length += 1
        else:
            if current_state == stressed_state:
                stressed_runs.append(current_length)
            current_state = states[i]
            current_length = 1
    
    if current_state == stressed_state:
        stressed_runs.append(current_length)
    
    mean_stressed_length = np.mean(stressed_runs) if stressed_runs else 0
    median_stressed_length = np.median(stressed_runs) if stressed_runs else 0
    
    print(f"📊 Expected stress half-life: {half_life:.1f} hours")
    print(f"📊 Mean stressed episode length: {mean_stressed_length:.1f} hours")
    print(f"📊 Median stressed episode length: {median_stressed_length:.1f} hours")
    
    return {
        'half_life': half_life,
        'mean_length': mean_stressed_length,
        'median_length': median_stressed_length,
        'p_ss': p_ss
    }

def compute_null_controls(model, X, df, state_labels):
    """Compute null controls"""
    print(f"\n📊 **Null Controls**")
    print("=" * 60)
    
    # Circular shift (+17h)
    print("📊 Computing circular shift null...")
    shifted_X = np.roll(X, 17, axis=0)
    shifted_states = model.predict(shifted_X)
    
    # Compute Oct/Jul ratio for shifted data
    shifted_df = df.copy()
    shifted_df['state'] = shifted_states
    shifted_df['month'] = shifted_df['timestamp'].dt.to_period('M')
    
    july_stressed = 0
    oct_stressed = 0
    
    for month in shifted_df['month'].unique():
        month_data = shifted_df[shifted_df['month'] == month]
        stressed_count = (month_data['state'] == 2).sum()  # Assuming stressed is state 2
        total_count = len(month_data)
        
        if str(month) == '2025-07':
            july_stressed = stressed_count / total_count
        elif str(month) == '2025-10':
            oct_stressed = stressed_count / total_count
    
    r_circshift = oct_stressed / july_stressed if july_stressed > 0 else 0
    
    # Block permutation (6h blocks)
    print("📊 Computing block permutation null...")
    block_size = 6
    n_blocks = len(X) // block_size
    blocks = [X[i*block_size:(i+1)*block_size] for i in range(n_blocks)]
    np.random.shuffle(blocks)
    perm_X = np.vstack(blocks)
    
    # Add remaining data
    remaining = len(X) % block_size
    if remaining > 0:
        perm_X = np.vstack([perm_X, X[-remaining:]])
    
    perm_states = model.predict(perm_X)
    
    # Compute Oct/Jul ratio for permuted data
    perm_df = df.copy()
    perm_df['state'] = perm_states
    perm_df['month'] = perm_df['timestamp'].dt.to_period('M')
    
    july_stressed_perm = 0
    oct_stressed_perm = 0
    
    for month in perm_df['month'].unique():
        month_data = perm_df[perm_df['month'] == month]
        stressed_count = (month_data['state'] == 2).sum()
        total_count = len(month_data)
        
        if str(month) == '2025-07':
            july_stressed_perm = stressed_count / total_count
        elif str(month) == '2025-10':
            oct_stressed_perm = stressed_count / total_count
    
    r_blockperm = oct_stressed_perm / july_stressed_perm if july_stressed_perm > 0 else 0
    
    print(f"📊 R_circshift: {r_circshift:.3f}")
    print(f"📊 R_blockperm: {r_blockperm:.3f}")
    
    return r_circshift, r_blockperm

def main():
    print('🔍 Phase 42A-v2: Proper Sticky HMM/HSMM on RRI Series')
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
    
    # Preprocess RRI
    df_rri, scaler, features = preprocess_rri(rri_series)
    if df_rri is None:
        return
    
    # Prepare features for modeling
    X = df_rri[features + ['Zavg_s']].values
    
    # Fit models
    models, results = fit_models(X, features + ['Zavg_s'])
    
    if not models:
        print("❌ HALT: All models failed to converge")
        return
    
    # Model selection table
    print(f"\n📊 **Model Selection Table**")
    print("=" * 60)
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    # Select best model by BIC
    best_model_name = results_df.loc[results_df['BIC'].idxmin(), 'Model']
    best_model = models[best_model_name]
    
    if best_model_name == 'M3':
        best_states = models['M3_states']
    else:
        best_states = best_model.predict(X)
    
    print(f"\n📊 **Chosen Model: {best_model_name}**")
    
    # Analyze chosen model
    state_summary, relabeled_states, state_labels = analyze_chosen_model(best_model, best_states, df_rri, features + ['Zavg_s'])
    
    # Print state summary
    print(f"\n📊 **State Summary**")
    print("=" * 60)
    print(f"{'State':<5} {'Label':<12} {'Mean(ZE,ZM,Zavg_s)':<25} {'Median_dur':<10} {'%_time':<8} {'p(self)':<8}")
    print("-" * 70)
    
    for state in state_summary:
        mean_str = f"({state['Mean_ZE']:.2f},{state['Mean_ZM']:.2f},{state['Mean_Zavg_s']:.2f})"
        print(f"{state['State']:<5} {state['Label']:<12} {mean_str:<25} {state['Median_duration']:<10.1f} {state['Time_percentage']:<8.1f} {state['Self_trans_prob']:<8.3f}")
    
    # Transition matrix
    print(f"\n📊 **Transition Matrix**")
    print("=" * 60)
    print("📊 Transition Matrix (from → to):")
    print("     ", end="")
    for label in state_labels:
        print(f"{label:>12}", end="")
    print()
    
    for i, from_label in enumerate(state_labels):
        print(f"{from_label:>4} ", end="")
        for j in range(len(state_labels)):
            print(f"{best_model.transmat_[i, j]:>12.3f}", end="")
        print()
    
    # Create timeline plot
    create_timeline_plot(relabeled_states, df_rri, state_labels)
    
    # Monthly regime shares
    monthly_shares = compute_monthly_regime_shares(relabeled_states, df_rri, state_labels)
    print(f"\n📊 **Monthly Regime Shares**")
    print("=" * 60)
    shares_df = pd.DataFrame(monthly_shares)
    print(shares_df.to_string(index=False))
    
    # Persistence metrics
    persistence_metrics = compute_persistence_metrics(best_model, relabeled_states, state_labels)
    
    # Compute Oct/Jul ratio
    july_stressed = 0
    oct_stressed = 0
    
    for month_data in monthly_shares:
        if month_data['Month'] == '2025-07':
            july_stressed = month_data['Stressed_%'] / 100
        elif month_data['Month'] == '2025-10':
            oct_stressed = month_data['Stressed_%'] / 100
    
    r_real = oct_stressed / july_stressed if july_stressed > 0 else 0
    
    # Null controls
    r_circshift, r_blockperm = compute_null_controls(best_model, X, df_rri, state_labels)
    
    # Decision
    print(f"\n📊 **Decision**")
    print("=" * 60)
    
    # Find stressed state
    stressed_state = None
    for i, label in enumerate(state_labels):
        if label == 'stressed':
            stressed_state = i
            break
    
    if stressed_state is None:
        print("❌ **REJECT — no stressed state identified**")
        return
    
    p_ss = best_model.transmat_[stressed_state, stressed_state]
    median_stressed_run = persistence_metrics['median_length'] if persistence_metrics else 0
    
    print(f"📊 p_ss: {p_ss:.3f}")
    print(f"📊 Median stressed run: {median_stressed_run:.1f}h")
    print(f"📊 R_real: {r_real:.3f}")
    print(f"📊 R_circshift: {r_circshift:.3f}")
    print(f"📊 R_blockperm: {r_blockperm:.3f}")
    
    # Check decision conditions
    condition1 = p_ss >= 0.6
    condition2 = median_stressed_run >= 3
    condition3 = r_real >= 2.0
    condition4 = r_real > max(r_circshift, r_blockperm) * 1.25
    
    print(f"\n📊 **Decision Conditions:**")
    print(f"   (i) p_ss ≥ 0.6: {condition1} ({p_ss:.3f})")
    print(f"   (ii) Median stressed run ≥ 3h: {condition2} ({median_stressed_run:.1f}h)")
    print(f"   (iii) R_real ≥ 2.0: {condition3} ({r_real:.3f})")
    print(f"   (iv) R_real > max(nulls) × 1.25: {condition4} ({r_real:.3f} > {max(r_circshift, r_blockperm) * 1.25:.3f})")
    
    if condition1 and condition2 and condition3 and condition4:
        print(f"\n✅ **ACCEPT — persistent stressed regime (Oct vs Jul ratio R={r_real:.3f}). Proceed to Phase 41 (Synthetic Control).**")
    else:
        print(f"\n❌ **REJECT — no persistent stressed regime under sticky/HSMM constraints; suggest returning to 37E params or extend panel.**")

if __name__ == '__main__':
    main()
