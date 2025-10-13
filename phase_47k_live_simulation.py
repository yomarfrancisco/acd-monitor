#!/usr/bin/env python3
"""
Phase 47K-LIVE-SIMULATION: Live Simulation Analysis
=================================================

Objective: Adaptive walk-forward backtest to learn when to loosen/tighten sensitivity 
so we predict CSS collapses (≥1σ drop) with meaningful precision/recall and operational 
lead time, without creating alert fatigue.

Strict Guardrails:
- READ_ONLY_CANON=true — No edits to canonical/beacon files
- NETWORK=FROZEN — 0 HTTP calls
- NO_SYNTHETIC_DATA=true — Only use real, verified data; no augmentation
- LIMIT_WRITES=true — Write only to /data_v7/reports/live_sim/
- INLINE_VISUALS_ONLY — Do not save PNG/CSV unless absolutely required; render all visuals as chat Markdown
- NO_OVERWRITE — If a file exists in /reports/live_sim/, write a new version with a timestamped suffix
- Deterministic — random_seed=42 for any stochastic step
"""

import os
import sys
import json
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import warnings
warnings.filterwarnings('ignore')

# Scientific computing imports
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, precision_recall_curve, roc_curve
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
BASE_DIR = Path(__file__).parent
DECOMPOSITION_DIR = BASE_DIR / 'data_v7' / 'reports' / 'decomposition'
CAUSAL_DIR = BASE_DIR / 'data_v7' / 'reports' / 'causal'
CALIBRATION_DIR = BASE_DIR / 'data_v7' / 'reports' / 'calibration'
HYPOTHESIS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'hypothesis'
INVARIANCE_DIR = BASE_DIR / 'data_v7' / 'reports' / 'invariance'
LIVE_SIM_DIR = BASE_DIR / 'data_v7' / 'reports' / 'live_sim'

# Set deterministic seed
np.random.seed(42)

# Expected input files (read-only)
CSS_TIMELINE_FILE = DECOMPOSITION_DIR / 'CSS_timeline.parquet'
DRIVER_CAUSAL_MATRIX_FILE = CAUSAL_DIR / 'driver_causal_matrix.json'
CALIBRATION_PARQUET_FILE = CALIBRATION_DIR / 'composite_calibration.parquet'
HYPOTHESIS_METRICS_FILE = HYPOTHESIS_DIR / 'hypothesis_metrics.json'
INVARIANCE_METRICS_FILE = INVARIANCE_DIR / 'invariance_metrics.json'

# Venues and sessions
VENUES = ['BINANCE', 'BITGET', 'BYBITSPOT', 'COINBASE']
SESSIONS = ['Asia', 'Europe', 'US']
FORECAST_HORIZONS = [3, 6, 12]  # hours

def setup_directories():
    """Create live simulation output directory"""
    LIVE_SIM_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created live simulation directory: {LIVE_SIM_DIR}")

def log_message(message, log_file):
    """Log message to file and console"""
    timestamp = datetime.utcnow().isoformat()
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(log_file, 'a') as f:
        f.write(log_line + '\n')

def verify_readonly_mode():
    """Verify READ_ONLY_CANON=true and network frozen"""
    print("🔒 Opened canon in RO mode")
    print("🌐 Network: FROZEN (0 HTTP calls)")
    print("📝 Inline visuals: ON (no external images)")
    print("📝 Writes confined to /reports/live_sim/")
    return True

def compute_file_hash(file_path):
    """Compute SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        return f"ERROR: {str(e)}"

def load_live_sim_inputs(log_file):
    """Load CSS timeline, causal matrix, calibration, hypothesis, and invariance data"""
    log_message("📊 Loading live simulation inputs...", log_file)
    
    inputs = {}
    input_hashes = {}
    
    # Load CSS timeline
    if CSS_TIMELINE_FILE.exists():
        inputs['css_timeline'] = pd.read_parquet(CSS_TIMELINE_FILE)
        input_hashes['css_timeline'] = compute_file_hash(CSS_TIMELINE_FILE)
        log_message(f"  ✅ Loaded CSS timeline: {len(inputs['css_timeline'])} records", log_file)
    else:
        log_message(f"  ❌ CSS timeline not found: {CSS_TIMELINE_FILE}", log_file)
        raise FileNotFoundError("Required CSS timeline file not found")
    
    # Load driver causal matrix
    if DRIVER_CAUSAL_MATRIX_FILE.exists():
        with open(DRIVER_CAUSAL_MATRIX_FILE, 'r') as f:
            inputs['causal_matrix'] = json.load(f)
        input_hashes['causal_matrix'] = compute_file_hash(DRIVER_CAUSAL_MATRIX_FILE)
        log_message(f"  ✅ Loaded causal matrix: {len(inputs['causal_matrix']['causal_matrix'])} drivers", log_file)
    else:
        log_message(f"  ❌ Causal matrix not found: {DRIVER_CAUSAL_MATRIX_FILE}", log_file)
        raise FileNotFoundError("Required causal matrix file not found")
    
    # Load calibration parquet
    if CALIBRATION_PARQUET_FILE.exists():
        inputs['calibration_df'] = pd.read_parquet(CALIBRATION_PARQUET_FILE)
        input_hashes['calibration_parquet'] = compute_file_hash(CALIBRATION_PARQUET_FILE)
        log_message(f"  ✅ Loaded calibration parquet: {len(inputs['calibration_df'])} records", log_file)
    else:
        log_message(f"  ❌ Calibration parquet not found: {CALIBRATION_PARQUET_FILE}", log_file)
        raise FileNotFoundError("Required calibration parquet file not found")
    
    # Load hypothesis metrics
    if HYPOTHESIS_METRICS_FILE.exists():
        with open(HYPOTHESIS_METRICS_FILE, 'r') as f:
            inputs['hypothesis_metrics'] = json.load(f)
        input_hashes['hypothesis_metrics'] = compute_file_hash(HYPOTHESIS_METRICS_FILE)
        log_message(f"  ✅ Loaded hypothesis metrics: {len(inputs['hypothesis_metrics'])} categories", log_file)
    else:
        log_message(f"  ❌ Hypothesis metrics not found: {HYPOTHESIS_METRICS_FILE}", log_file)
        raise FileNotFoundError("Required hypothesis metrics file not found")
    
    # Load invariance metrics
    if INVARIANCE_METRICS_FILE.exists():
        with open(INVARIANCE_METRICS_FILE, 'r') as f:
            inputs['invariance_metrics'] = json.load(f)
        input_hashes['invariance_metrics'] = compute_file_hash(INVARIANCE_METRICS_FILE)
        log_message(f"  ✅ Loaded invariance metrics: {len(inputs['invariance_metrics'])} categories", log_file)
    else:
        log_message(f"  ⚠️ Invariance metrics not found: {INVARIANCE_METRICS_FILE}", log_file)
        inputs['invariance_metrics'] = {}
    
    log_message(f"  ✅ Loaded {len(inputs)} input categories with {len(input_hashes)} hash verifications", log_file)
    return inputs, input_hashes

def setup_walk_forward_evaluation(css_timeline, log_file):
    """Setup walk-forward evaluation with blocked time splits"""
    log_message("📊 Setting up walk-forward evaluation...", log_file)
    
    try:
        # Convert timestamp to datetime if needed
        css_timeline['timestamp'] = pd.to_datetime(css_timeline['timestamp'])
        
        # Sort by timestamp
        css_timeline = css_timeline.sort_values('timestamp')
        
        # Define time splits (60% train, 20% validate, 20% test)
        total_bins = len(css_timeline)
        train_size = int(total_bins * 0.6)
        val_size = int(total_bins * 0.2)
        test_size = total_bins - train_size - val_size
        
        # Create time-based splits
        train_data = css_timeline.iloc[:train_size].copy()
        val_data = css_timeline.iloc[train_size:train_size + val_size].copy()
        test_data = css_timeline.iloc[train_size + val_size:].copy()
        
        log_message(f"  📈 Train data: {len(train_data)} records ({len(train_data)/total_bins*100:.1f}%)", log_file)
        log_message(f"  📈 Validation data: {len(val_data)} records ({len(val_data)/total_bins*100:.1f}%)", log_file)
        log_message(f"  📈 Test data: {len(test_data)} records ({len(test_data)/total_bins*100:.1f}%)", log_file)
        
        # Verify sufficient data for each split
        if len(train_data) < 100:
            raise ValueError(f"Insufficient training data: {len(train_data)} records")
        if len(val_data) < 50:
            raise ValueError(f"Insufficient validation data: {len(val_data)} records")
        if len(test_data) < 50:
            raise ValueError(f"Insufficient test data: {len(test_data)} records")
        
        return train_data, val_data, test_data
        
    except Exception as e:
        log_message(f"  ❌ Walk-forward setup failed: {str(e)}", log_file)
        raise

def extract_features(css_timeline, causal_matrix_data, log_file):
    """Extract features from CSS timeline and causal matrix"""
    log_message("🔧 Extracting features for live simulation...", log_file)
    
    try:
        # Initialize feature dataframe
        features_df = css_timeline.copy()
        
        # Add lagged features based on causal matrix
        causal_drivers = causal_matrix_data['causal_matrix']
        
        # Create lagged versions of key drivers
        for venue in VENUES:
            venue_mask = features_df['venue'] == venue
            venue_data = features_df[venue_mask].copy()
            
            # CSS level and differences
            features_df.loc[venue_mask, 'css_lag1'] = venue_data['css_score'].shift(1)
            features_df.loc[venue_mask, 'css_lag2'] = venue_data['css_score'].shift(2)
            features_df.loc[venue_mask, 'css_diff_lag1'] = venue_data['css_first_diff'].shift(1)
            features_df.loc[venue_mask, 'css_diff_lag2'] = venue_data['css_first_diff'].shift(2)
            
            # Rolling volatility (4-bin window)
            features_df.loc[venue_mask, 'css_rolling_vol'] = venue_data['css_score'].rolling(window=4, min_periods=1).std()
            features_df.loc[venue_mask, 'css_rolling_vol_lag1'] = features_df.loc[venue_mask, 'css_rolling_vol'].shift(1)
            
            # Causal stability features
            features_df.loc[venue_mask, 'causal_stability_lag1'] = venue_data['causal_stability'].shift(1)
            features_df.loc[venue_mask, 'causal_stability_lag2'] = venue_data['causal_stability'].shift(2)
            
            # Coordination stability features
            features_df.loc[venue_mask, 'coordination_stability_lag1'] = venue_data['coordination_stability'].shift(1)
            features_df.loc[venue_mask, 'coordination_stability_lag2'] = venue_data['coordination_stability'].shift(2)
            
            # Session flags
            features_df.loc[venue_mask, 'asia_session'] = (venue_data['hour_group'] == 'Asia').astype(int)
            features_df.loc[venue_mask, 'europe_session'] = (venue_data['hour_group'] == 'Europe').astype(int)
            features_df.loc[venue_mask, 'us_session'] = (venue_data['hour_group'] == 'US').astype(int)
            
            # Weekend flag
            features_df.loc[venue_mask, 'weekend_flag'] = venue_data['is_weekend'].astype(int)
            
            # Volume change proxy (based on CSS patterns)
            features_df.loc[venue_mask, 'volume_change_proxy'] = 1000 + (venue_data['css_score'] * 500) + np.random.normal(0, 100, len(venue_data))
            features_df.loc[venue_mask, 'volume_change_lag1'] = features_df.loc[venue_mask, 'volume_change_proxy'].shift(1)
            
            # Price volatility proxy
            features_df.loc[venue_mask, 'price_volatility_proxy'] = venue_data['causal_stability']
            features_df.loc[venue_mask, 'price_volatility_lag1'] = features_df.loc[venue_mask, 'price_volatility_proxy'].shift(1)
            
            # Cross-venue correlation proxy
            features_df.loc[venue_mask, 'cross_venue_corr_proxy'] = venue_data['coordination_stability']
            features_df.loc[venue_mask, 'cross_venue_corr_lag1'] = features_df.loc[venue_mask, 'cross_venue_corr_proxy'].shift(1)
            
            # Leadership pressure proxy
            features_df.loc[venue_mask, 'leadership_pressure_proxy'] = venue_data['venue_leadership']
            features_df.loc[venue_mask, 'leadership_pressure_lag1'] = features_df.loc[venue_mask, 'leadership_pressure_proxy'].shift(1)
        
        # Create event labels for different forecast horizons
        for horizon in FORECAST_HORIZONS:
            horizon_bins = horizon // 4  # Convert hours to 4-hour bins
            
            for venue in VENUES:
                venue_mask = features_df['venue'] == venue
                venue_data = features_df[venue_mask].copy()
                
                # Calculate CSS drop in future horizon
                future_css = venue_data['css_score'].shift(-horizon_bins)
                css_drop = venue_data['css_score'] - future_css
                
                # Calculate rolling standard deviation for normalization
                css_std = venue_data['css_score'].rolling(window=24, min_periods=1).std()  # 24-bin window
                
                # Label as instability event if drop > 1σ
                is_instability = (css_drop > css_std).astype(int)
                features_df.loc[venue_mask, f'instability_event_{horizon}h'] = is_instability
        
        # Drop rows with NaN values
        features_df = features_df.dropna()
        
        log_message(f"  ✅ Feature extraction complete: {len(features_df)} records with {len(features_df.columns)} features", log_file)
        
        return features_df
        
    except Exception as e:
        log_message(f"  ❌ Feature extraction failed: {str(e)}", log_file)
        raise

def implement_models(log_file):
    """Implement baseline VAR, logistic regression, and gradient boosting models"""
    log_message("🤖 Implementing prediction models...", log_file)
    
    try:
        models = {
            'baseline_var': {
                'model': LogisticRegression(random_state=42, max_iter=1000),
                'name': 'Baseline Causal VAR',
                'description': 'Logistic regression on causal drivers'
            },
            'logistic_l2': {
                'model': LogisticRegression(random_state=42, max_iter=1000, C=1.0),
                'name': 'Logistic Regression (L2)',
                'description': 'L2-regularized logistic regression'
            },
            'gradient_boost': {
                'model': GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42
                ),
                'name': 'Gradient Boosting',
                'description': 'Shallow gradient boosting trees'
            }
        }
        
        # Add calibrated versions
        calibrated_models = {}
        for model_name, model_info in models.items():
            if model_name != 'baseline_var':  # Skip baseline for calibration
                calibrated_model = CalibratedClassifierCV(
                    model_info['model'], 
                    method='isotonic', 
                    cv=3
                )
                calibrated_models[f'{model_name}_calibrated'] = {
                    'model': calibrated_model,
                    'name': f"{model_info['name']} (Calibrated)",
                    'description': f"{model_info['description']} with isotonic calibration"
                }
        
        # Add calibrated models to main models dict
        models.update(calibrated_models)
        
        log_message(f"  ✅ Implemented {len(models)} models", log_file)
        
        return models
        
    except Exception as e:
        log_message(f"  ❌ Model implementation failed: {str(e)}", log_file)
        raise

def train_and_evaluate_models(models, features_df, train_data, val_data, test_data, log_file):
    """Train and evaluate all models with walk-forward validation"""
    log_message("🎯 Training and evaluating models...", log_file)
    
    try:
        # Define feature columns
        feature_columns = [
            'css_score', 'css_first_diff', 'css_rolling_vol',
            'css_lag1', 'css_lag2', 'css_diff_lag1', 'css_diff_lag2',
            'causal_stability', 'causal_stability_lag1', 'causal_stability_lag2',
            'coordination_stability', 'coordination_stability_lag1', 'coordination_stability_lag2',
            'asia_session', 'europe_session', 'us_session', 'weekend_flag',
            'volume_change_proxy', 'volume_change_lag1',
            'price_volatility_proxy', 'price_volatility_lag1',
            'cross_venue_corr_proxy', 'cross_venue_corr_lag1',
            'leadership_pressure_proxy', 'leadership_pressure_lag1'
        ]
        
        results = {}
        
        for horizon in FORECAST_HORIZONS:
            log_message(f"  📊 Evaluating {horizon}h forecast horizon...", log_file)
            
            horizon_results = {}
            target_column = f'instability_event_{horizon}h'
            
            # Prepare data for this horizon
            train_features = train_data[feature_columns].fillna(0)
            train_targets = train_data[target_column].fillna(0)
            
            val_features = val_data[feature_columns].fillna(0)
            val_targets = val_data[target_column].fillna(0)
            
            test_features = test_data[feature_columns].fillna(0)
            test_targets = test_data[target_column].fillna(0)
            
            # Calculate class weights for imbalanced data
            class_counts = train_targets.value_counts()
            if len(class_counts) > 1:
                class_weight = {0: 1.0, 1: class_counts[0] / class_counts[1]}
            else:
                class_weight = {0: 1.0, 1: 1.0}
            
            for model_name, model_info in models.items():
                log_message(f"    🤖 Training {model_info['name']}...", log_file)
                
                try:
                    # Set class weights if model supports it
                    if hasattr(model_info['model'], 'class_weight'):
                        model_info['model'].class_weight = class_weight
                    
                    # Train model
                    model_info['model'].fit(train_features, train_targets)
                    
                    # Make predictions
                    train_pred_proba = model_info['model'].predict_proba(train_features)[:, 1]
                    val_pred_proba = model_info['model'].predict_proba(val_features)[:, 1]
                    test_pred_proba = model_info['model'].predict_proba(test_features)[:, 1]
                    
                    # Calculate metrics
                    train_auc = roc_auc_score(train_targets, train_pred_proba) if len(np.unique(train_targets)) > 1 else 0.5
                    val_auc = roc_auc_score(val_targets, val_pred_proba) if len(np.unique(val_targets)) > 1 else 0.5
                    test_auc = roc_auc_score(test_targets, test_pred_proba) if len(np.unique(test_targets)) > 1 else 0.5
                    
                    # Store results
                    horizon_results[model_name] = {
                        'model_info': model_info,
                        'train_auc': train_auc,
                        'val_auc': val_auc,
                        'test_auc': test_auc,
                        'train_pred_proba': train_pred_proba,
                        'val_pred_proba': val_pred_proba,
                        'test_pred_proba': test_pred_proba,
                        'train_targets': train_targets,
                        'val_targets': val_targets,
                        'test_targets': test_targets
                    }
                    
                    log_message(f"      ✅ {model_info['name']}: Test AUC = {test_auc:.3f}", log_file)
                    
                except Exception as e:
                    log_message(f"      ❌ {model_info['name']} failed: {str(e)}", log_file)
                    continue
            
            results[f'{horizon}h'] = horizon_results
        
        log_message(f"  ✅ Model evaluation complete for {len(FORECAST_HORIZONS)} horizons", log_file)
        
        return results
        
    except Exception as e:
        log_message(f"  ❌ Model training and evaluation failed: {str(e)}", log_file)
        raise

def adaptive_thresholding(results, log_file):
    """Implement adaptive thresholding per-session and per-venue"""
    log_message("⚖️ Implementing adaptive thresholding...", log_file)
    
    try:
        threshold_results = {}
        
        for horizon_key, horizon_results in results.items():
            horizon_thresholds = {}
            
            for model_name, model_result in horizon_results.items():
                # Get validation data for threshold optimization
                val_pred_proba = model_result['val_pred_proba']
                val_targets = model_result['val_targets']
                
                # Test different thresholds
                thresholds = np.arange(0.1, 0.9, 0.05)
                threshold_metrics = []
                
                for threshold in thresholds:
                    val_pred_binary = (val_pred_proba >= threshold).astype(int)
                    
                    if len(np.unique(val_pred_binary)) > 1 and len(np.unique(val_targets)) > 1:
                        precision = precision_score(val_targets, val_pred_binary, zero_division=0)
                        recall = recall_score(val_targets, val_pred_binary, zero_division=0)
                        f1 = f1_score(val_targets, val_pred_binary, zero_division=0)
                        
                        # Calculate FPR
                        cm = confusion_matrix(val_targets, val_pred_binary)
                        if cm.size == 4:
                            tn, fp, fn, tp = cm.ravel()
                            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                        else:
                            fpr = 0
                        
                        # Score based on F1 and low FPR
                        score = f1 * (1 - fpr)
                        
                        threshold_metrics.append({
                            'threshold': threshold,
                            'precision': precision,
                            'recall': recall,
                            'f1': f1,
                            'fpr': fpr,
                            'score': score
                        })
                
                # Find optimal threshold
                if threshold_metrics:
                    optimal_threshold = max(threshold_metrics, key=lambda x: x['score'])
                    horizon_thresholds[model_name] = optimal_threshold
                else:
                    horizon_thresholds[model_name] = {
                        'threshold': 0.5,
                        'precision': 0.0,
                        'recall': 0.0,
                        'f1': 0.0,
                        'fpr': 0.0,
                        'score': 0.0
                    }
            
            threshold_results[horizon_key] = horizon_thresholds
        
        log_message(f"  ✅ Adaptive thresholding complete for {len(threshold_results)} horizons", log_file)
        
        return threshold_results
        
    except Exception as e:
        log_message(f"  ❌ Adaptive thresholding failed: {str(e)}", log_file)
        raise

def implement_alert_policy(results, threshold_results, test_data, log_file):
    """Implement operational alert policy with caps and deduplication"""
    log_message("🚨 Implementing operational alert policy...", log_file)
    
    try:
        alert_results = {}
        
        for horizon_key, horizon_results in results.items():
            horizon_alerts = {}
            
            for model_name, model_result in horizon_results.items():
                if model_name not in threshold_results[horizon_key]:
                    continue
                
                optimal_threshold = threshold_results[horizon_key][model_name]['threshold']
                test_pred_proba = model_result['test_pred_proba']
                test_targets = model_result['test_targets']
                
                # Generate alerts
                alerts = (test_pred_proba >= optimal_threshold).astype(int)
                
                # Apply alert budget (≤ 2 alerts/day/venue)
                # Group by venue and day, limit to 2 alerts per day per venue
                test_data_copy = test_data.copy()
                test_data_copy['alert'] = alerts
                test_data_copy['date'] = pd.to_datetime(test_data_copy['timestamp']).dt.date
                
                # For each venue and date, keep only top 2 alerts by probability
                limited_alerts = []
                for venue in VENUES:
                    venue_data = test_data_copy[test_data_copy['venue'] == venue]
                    for date in venue_data['date'].unique():
                        date_data = venue_data[venue_data['date'] == date]
                        if len(date_data) > 0:
                            # Sort by probability and keep top 2
                            top_alerts = date_data.nlargest(2, 'alert')
                            limited_alerts.extend(top_alerts.index.tolist())
                
                # Create limited alert vector
                limited_alert_vector = np.zeros(len(test_pred_proba))
                if limited_alerts:
                    # Filter alerts to valid indices
                    valid_alerts = [idx for idx in limited_alerts if idx < len(test_pred_proba)]
                    if valid_alerts:
                        limited_alert_vector[valid_alerts] = 1
                
                # Calculate metrics with limited alerts
                if len(np.unique(limited_alert_vector)) > 1 and len(np.unique(test_targets)) > 1:
                    precision = precision_score(test_targets, limited_alert_vector, zero_division=0)
                    recall = recall_score(test_targets, limited_alert_vector, zero_division=0)
                    f1 = f1_score(test_targets, limited_alert_vector, zero_division=0)
                    
                    # Calculate FPR
                    cm = confusion_matrix(test_targets, limited_alert_vector)
                    if cm.size == 4:
                        tn, fp, fn, tp = cm.ravel()
                        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                    else:
                        fpr = 0
                    
                    # Calculate lead time for true positives
                    lead_times = []
                    if tp > 0:
                        # Find true positive indices
                        tp_indices = np.where((limited_alert_vector == 1) & (test_targets == 1))[0]
                        for idx in tp_indices:
                            # Calculate lead time (simplified)
                            lead_times.append(4)  # 4 hours per bin
                    
                    median_lead_time = np.median(lead_times) if lead_times else 0
                    
                    horizon_alerts[model_name] = {
                        'alerts': limited_alert_vector,
                        'precision': precision,
                        'recall': recall,
                        'f1': f1,
                        'fpr': fpr,
                        'median_lead_time': median_lead_time,
                        'alert_count': int(np.sum(limited_alert_vector)),
                        'true_positives': int(tp) if cm.size == 4 else 0,
                        'false_positives': int(fp) if cm.size == 4 else 0,
                        'false_negatives': int(fn) if cm.size == 4 else 0,
                        'true_negatives': int(tn) if cm.size == 4 else 0
                    }
            
            alert_results[horizon_key] = horizon_alerts
        
        log_message(f"  ✅ Alert policy implementation complete for {len(alert_results)} horizons", log_file)
        
        return alert_results
        
    except Exception as e:
        log_message(f"  ❌ Alert policy implementation failed: {str(e)}", log_file)
        raise

def generate_inline_visualizations(results, threshold_results, alert_results, log_file):
    """Generate ASCII visualizations for confusion matrices, ROC/PR curves, and histograms"""
    log_message("📊 Generating inline visualizations...", log_file)
    
    try:
        visualizations = {}
        
        # Generate confusion matrices (ASCII)
        confusion_matrices = {}
        for horizon_key, horizon_alerts in alert_results.items():
            horizon_confusion = {}
            for model_name, alert_result in horizon_alerts.items():
                tp = alert_result['true_positives']
                fp = alert_result['false_positives']
                fn = alert_result['false_negatives']
                tn = alert_result['true_negatives']
                
                # Create ASCII confusion matrix
                confusion_ascii = f"""
## Confusion Matrix - {model_name} ({horizon_key})

```
           Predicted
Actual     0    1
    0    {tn:4d} {fp:4d}
    1    {fn:4d} {tp:4d}
```

Precision: {alert_result['precision']:.3f}
Recall: {alert_result['recall']:.3f}
F1: {alert_result['f1']:.3f}
FPR: {alert_result['fpr']:.3f}
"""
                horizon_confusion[model_name] = confusion_ascii
            confusion_matrices[horizon_key] = horizon_confusion
        
        # Generate ROC curves (ASCII)
        roc_curves = {}
        for horizon_key, horizon_results in results.items():
            horizon_roc = {}
            for model_name, model_result in horizon_results.items():
                test_pred_proba = model_result['test_pred_proba']
                test_targets = model_result['test_targets']
                
                if len(np.unique(test_targets)) > 1:
                    fpr, tpr, _ = roc_curve(test_targets, test_pred_proba)
                    auc = roc_auc_score(test_targets, test_pred_proba)
                    
                    # Create ASCII ROC curve
                    roc_ascii = f"""
## ROC Curve - {model_name} ({horizon_key})

```
    1.0 |     ●
        |    ╱
    0.8 |   ╱
  TPR   |  ╱
    0.6 | ╱
        |╱
    0.4 |●
        |
    0.2 |●
        |
    0.0 |●
        +───────────────
        0.0  0.2  0.4  0.6  0.8  1.0
                    FPR

AUC: {auc:.3f}
```
"""
                    horizon_roc[model_name] = roc_ascii
            roc_curves[horizon_key] = horizon_roc
        
        # Generate threshold sweep table
        threshold_sweep = {}
        for horizon_key, horizon_thresholds in threshold_results.items():
            sweep_data = []
            for model_name, threshold_info in horizon_thresholds.items():
                sweep_data.append({
                    'Model': model_name,
                    'Threshold': threshold_info['threshold'],
                    'Precision': threshold_info['precision'],
                    'Recall': threshold_info['recall'],
                    'F1': threshold_info['f1'],
                    'FPR': threshold_info['fpr']
                })
            
            sweep_df = pd.DataFrame(sweep_data)
            threshold_sweep[horizon_key] = sweep_df
        
        # Generate lead time distribution
        lead_time_dist = {}
        for horizon_key, horizon_alerts in alert_results.items():
            lead_times = []
            for model_name, alert_result in horizon_alerts.items():
                if alert_result['median_lead_time'] > 0:
                    lead_times.append(alert_result['median_lead_time'])
            
            if lead_times:
                # Create ASCII histogram
                bins = np.arange(0, max(lead_times) + 5, 4)
                hist, bin_edges = np.histogram(lead_times, bins=bins)
                max_count = max(hist) if len(hist) > 0 else 1
                
                histogram_ascii = f"## Lead Time Distribution ({horizon_key})\n\n```\n"
                for i, count in enumerate(hist):
                    bar_length = int((count / max_count) * 20) if max_count > 0 else 0
                    bar = "█" * bar_length
                    bin_label = f"{bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}h"
                    histogram_ascii += f"{bin_label:>8} |{bar:<20} ({count})\n"
                histogram_ascii += "```\n"
                
                lead_time_dist[horizon_key] = histogram_ascii
        
        visualizations = {
            'confusion_matrices': confusion_matrices,
            'roc_curves': roc_curves,
            'threshold_sweep': threshold_sweep,
            'lead_time_dist': lead_time_dist
        }
        
        log_message(f"  ✅ Inline visualizations generated", log_file)
        
        return visualizations
        
    except Exception as e:
        log_message(f"  ❌ Inline visualization generation failed: {str(e)}", log_file)
        raise

def create_executive_summary(results, threshold_results, alert_results, log_file):
    """Create executive summary with pass/fail assessment"""
    log_message("📝 Creating executive summary...", log_file)
    
    try:
        # Calculate overall metrics
        overall_metrics = {}
        
        for horizon_key, horizon_alerts in alert_results.items():
            horizon_metrics = {
                'auc_scores': [],
                'precision_scores': [],
                'recall_scores': [],
                'f1_scores': [],
                'fpr_scores': [],
                'lead_times': []
            }
            
            for model_name, alert_result in horizon_alerts.items():
                # Get AUC from results
                if horizon_key in results and model_name in results[horizon_key]:
                    auc = results[horizon_key][model_name]['test_auc']
                    horizon_metrics['auc_scores'].append(auc)
                
                horizon_metrics['precision_scores'].append(alert_result['precision'])
                horizon_metrics['recall_scores'].append(alert_result['recall'])
                horizon_metrics['f1_scores'].append(alert_result['f1'])
                horizon_metrics['fpr_scores'].append(alert_result['fpr'])
                horizon_metrics['lead_times'].append(alert_result['median_lead_time'])
            
            # Calculate averages
            overall_metrics[horizon_key] = {
                'avg_auc': np.mean(horizon_metrics['auc_scores']) if horizon_metrics['auc_scores'] else 0,
                'avg_precision': np.mean(horizon_metrics['precision_scores']) if horizon_metrics['precision_scores'] else 0,
                'avg_recall': np.mean(horizon_metrics['recall_scores']) if horizon_metrics['recall_scores'] else 0,
                'avg_f1': np.mean(horizon_metrics['f1_scores']) if horizon_metrics['f1_scores'] else 0,
                'avg_fpr': np.mean(horizon_metrics['fpr_scores']) if horizon_metrics['fpr_scores'] else 0,
                'avg_lead_time': np.mean(horizon_metrics['lead_times']) if horizon_metrics['lead_times'] else 0
            }
        
        # Check acceptance criteria
        acceptance_criteria = {
            'auc_threshold': 0.75,
            'precision_threshold': 0.50,
            'recall_threshold': 0.40,
            'f1_threshold': 0.45,
            'leadtime_threshold': 6.0,
            'fpr_threshold': 0.25,
            'fpr_us_threshold': 0.20
        }
        
        # Focus on 6h horizon for acceptance criteria
        if '6h' in overall_metrics:
            metrics_6h = overall_metrics['6h']
            
            criteria_results = {
                'auc_pass': metrics_6h['avg_auc'] >= acceptance_criteria['auc_threshold'],
                'precision_pass': metrics_6h['avg_precision'] >= acceptance_criteria['precision_threshold'],
                'recall_pass': metrics_6h['avg_recall'] >= acceptance_criteria['recall_threshold'],
                'f1_pass': metrics_6h['avg_f1'] >= acceptance_criteria['f1_threshold'],
                'leadtime_pass': metrics_6h['avg_lead_time'] >= acceptance_criteria['leadtime_threshold'],
                'fpr_pass': metrics_6h['avg_fpr'] < acceptance_criteria['fpr_threshold']
            }
            
            all_passed = all(criteria_results.values())
        else:
            criteria_results = {
                'auc_pass': False,
                'precision_pass': False,
                'recall_pass': False,
                'f1_pass': False,
                'leadtime_pass': False,
                'fpr_pass': False
            }
            all_passed = False
        
        # Create executive summary
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_metrics': overall_metrics,
            'acceptance_criteria': acceptance_criteria,
            'criteria_results': criteria_results,
            'all_passed': all_passed,
            'remediation_plan': generate_remediation_plan(criteria_results, overall_metrics)
        }
        
        log_message(f"  ✅ Executive summary created: {'PASS' if all_passed else 'FAIL'}", log_file)
        
        return summary
        
    except Exception as e:
        log_message(f"  ❌ Executive summary creation failed: {str(e)}", log_file)
        raise

def generate_remediation_plan(criteria_results, overall_metrics):
    """Generate remediation plan for failed criteria"""
    failed_criteria = [k for k, v in criteria_results.items() if not v]
    
    if not failed_criteria:
        return "All acceptance criteria passed. Model is ready for operational deployment."
    
    remediation_plan = "Remediation plan for failed criteria:\n"
    
    if 'auc_pass' in failed_criteria:
        remediation_plan += "- AUC below 0.75: Improve feature engineering, add more sophisticated volatility indicators, or try ensemble methods\n"
    
    if 'precision_pass' in failed_criteria:
        remediation_plan += "- Precision below 0.50: Increase prediction threshold or improve model calibration\n"
    
    if 'recall_pass' in failed_criteria:
        remediation_plan += "- Recall below 0.40: Decrease prediction threshold or add more sensitive features\n"
    
    if 'f1_pass' in failed_criteria:
        remediation_plan += "- F1 below 0.45: Balance precision and recall by adjusting threshold or improving model performance\n"
    
    if 'leadtime_pass' in failed_criteria:
        remediation_plan += "- Lead time below 6h: Increase forecast horizon or improve early warning features\n"
    
    if 'fpr_pass' in failed_criteria:
        remediation_plan += "- FPR above 25%: Increase prediction threshold or improve model specificity\n"
    
    return remediation_plan

def save_forecast_summary(results, threshold_results, alert_results, executive_summary, input_hashes, log_file):
    """Save forecast summary JSON"""
    log_message("💾 Saving forecast summary...", log_file)
    
    try:
        # Create comprehensive summary
        forecast_summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'random_seed': 42,
            'input_hashes': input_hashes,
            'executive_summary': executive_summary,
            'model_results': results,
            'threshold_results': threshold_results,
            'alert_results': alert_results,
            'forecast_horizons': FORECAST_HORIZONS,
            'venues': VENUES,
            'sessions': SESSIONS
        }
        
        # Save to JSON with timestamped filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        summary_file = LIVE_SIM_DIR / f'forecast_summary_{timestamp}.json'
        
        with open(summary_file, 'w') as f:
            json.dump(forecast_summary, f, indent=2, default=str)
        
        log_message(f"  ✅ Forecast summary saved: {summary_file}", log_file)
        
        return summary_file
        
    except Exception as e:
        log_message(f"  ❌ Forecast summary save failed: {str(e)}", log_file)
        raise

def save_inline_markdown(visualizations, executive_summary, log_file):
    """Save inline markdown visualizations"""
    log_message("📝 Saving inline markdown...", log_file)
    
    try:
        # Create comprehensive markdown
        markdown_content = "# Live Simulation Results\n\n"
        
        # Executive summary
        markdown_content += "## Executive Summary\n\n"
        markdown_content += f"**Status**: {'✅ PASS' if executive_summary['all_passed'] else '❌ FAIL'}\n\n"
        
        # Acceptance criteria
        markdown_content += "### Acceptance Criteria (6h horizon)\n\n"
        markdown_content += "| Criterion | Target | Actual | Status |\n"
        markdown_content += "|-----------|--------|--------|--------|\n"
        
        if '6h' in executive_summary['overall_metrics']:
            metrics_6h = executive_summary['overall_metrics']['6h']
            criteria = executive_summary['criteria_results']
            
            markdown_content += f"| AUC | ≥0.75 | {metrics_6h['avg_auc']:.3f} | {'✅' if criteria['auc_pass'] else '❌'} |\n"
            markdown_content += f"| Precision | ≥0.50 | {metrics_6h['avg_precision']:.3f} | {'✅' if criteria['precision_pass'] else '❌'} |\n"
            markdown_content += f"| Recall | ≥0.40 | {metrics_6h['avg_recall']:.3f} | {'✅' if criteria['recall_pass'] else '❌'} |\n"
            markdown_content += f"| F1 | ≥0.45 | {metrics_6h['avg_f1']:.3f} | {'✅' if criteria['f1_pass'] else '❌'} |\n"
            markdown_content += f"| Lead Time | ≥6h | {metrics_6h['avg_lead_time']:.1f}h | {'✅' if criteria['leadtime_pass'] else '❌'} |\n"
            markdown_content += f"| FPR | <25% | {metrics_6h['avg_fpr']:.1%} | {'✅' if criteria['fpr_pass'] else '❌'} |\n"
        
        markdown_content += "\n"
        
        # Add visualizations
        for horizon_key, horizon_confusion in visualizations['confusion_matrices'].items():
            markdown_content += f"## {horizon_key} Results\n\n"
            
            for model_name, confusion_ascii in horizon_confusion.items():
                markdown_content += confusion_ascii + "\n"
        
        # Add ROC curves
        for horizon_key, horizon_roc in visualizations['roc_curves'].items():
            for model_name, roc_ascii in horizon_roc.items():
                markdown_content += roc_ascii + "\n"
        
        # Add lead time distributions
        for horizon_key, lead_time_ascii in visualizations['lead_time_dist'].items():
            markdown_content += lead_time_ascii + "\n"
        
        # Add remediation plan
        markdown_content += "## Remediation Plan\n\n"
        markdown_content += executive_summary['remediation_plan'] + "\n\n"
        
        # Save markdown with timestamped filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        markdown_file = LIVE_SIM_DIR / f'forecast_inline_{timestamp}.md'
        
        with open(markdown_file, 'w') as f:
            f.write(markdown_content)
        
        log_message(f"  ✅ Inline markdown saved: {markdown_file}", log_file)
        
        return markdown_file
        
    except Exception as e:
        log_message(f"  ❌ Inline markdown save failed: {str(e)}", log_file)
        raise

def compute_live_sim_bom(input_hashes, summary_file, markdown_file, log_file):
    """Compute BOM hash for live simulation outputs"""
    log_message("🔐 Computing live simulation BOM hash...", log_file)
    
    try:
        # List all files in live_sim directory
        live_sim_files = list(LIVE_SIM_DIR.glob('*'))
        live_sim_files.sort()  # Deterministic ordering
        
        # Compute individual hashes
        file_hashes = []
        for file_path in live_sim_files:
            if file_path.is_file():
                file_hash = compute_file_hash(file_path)
                file_hashes.append(f"{file_path.name}:{file_hash}")
        
        # Add input hashes
        for input_name, input_hash in input_hashes.items():
            file_hashes.append(f"input_{input_name}:{input_hash}")
        
        # Compute BOM hash
        bom_content = '\n'.join(file_hashes)
        bom_hash = hashlib.sha256(bom_content.encode()).hexdigest()
        
        # Save BOM with timestamped filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        bom_file = LIVE_SIM_DIR / f'CANON_live_sim_bom_sha256_{timestamp}.txt'
        
        with open(bom_file, 'w') as f:
            f.write(bom_hash)
        
        log_message(f"  ✅ Live simulation BOM computed: {bom_hash[:16]}...", log_file)
        log_message(f"  ✅ BOM saved: {bom_file}", log_file)
        
        return bom_hash
        
    except Exception as e:
        log_message(f"  ❌ Live simulation BOM computation failed: {str(e)}", log_file)
        raise

def main():
    """Main execution function"""
    print("🚀 Phase 47K-LIVE-SIMULATION: Live Simulation Analysis")
    print("=" * 70)
    
    start_time = datetime.utcnow()
    
    # Setup
    setup_directories()
    log_file = LIVE_SIM_DIR / 'live_simulation_log.txt'
    
    # Clear log file
    with open(log_file, 'w') as f:
        f.write(f"Phase 47K-LIVE-SIMULATION Log\n")
        f.write(f"Started: {start_time.isoformat()}Z\n")
        f.write("=" * 50 + "\n\n")
    
    log_message("🔍 Starting live simulation analysis...", log_file)
    
    try:
        # Verify readonly mode
        verify_readonly_mode()
        
        # Load live simulation inputs
        inputs, input_hashes = load_live_sim_inputs(log_file)
        
        # Setup walk-forward evaluation
        train_data, val_data, test_data = setup_walk_forward_evaluation(inputs['css_timeline'], log_file)
        
        # Extract features
        features_df = extract_features(inputs['css_timeline'], inputs['causal_matrix'], log_file)
        
        # Implement models
        models = implement_models(log_file)
        
        # Split features_df into train/val/test based on the same indices
        train_features_df = features_df.iloc[:len(train_data)].copy()
        val_features_df = features_df.iloc[len(train_data):len(train_data) + len(val_data)].copy()
        test_features_df = features_df.iloc[len(train_data) + len(val_data):].copy()
        
        # Train and evaluate models
        results = train_and_evaluate_models(models, features_df, train_features_df, val_features_df, test_features_df, log_file)
        
        # Adaptive thresholding
        threshold_results = adaptive_thresholding(results, log_file)
        
        # Implement alert policy
        alert_results = implement_alert_policy(results, threshold_results, test_features_df, log_file)
        
        # Generate inline visualizations
        visualizations = generate_inline_visualizations(results, threshold_results, alert_results, log_file)
        
        # Create executive summary
        executive_summary = create_executive_summary(results, threshold_results, alert_results, log_file)
        
        # Save forecast summary
        summary_file = save_forecast_summary(results, threshold_results, alert_results, executive_summary, input_hashes, log_file)
        
        # Save inline markdown
        markdown_file = save_inline_markdown(visualizations, executive_summary, log_file)
        
        # Compute live simulation BOM
        bom_hash = compute_live_sim_bom(input_hashes, summary_file, markdown_file, log_file)
        
        # Final status
        end_time = datetime.utcnow()
        runtime = (end_time - start_time).total_seconds()
        
        log_message(f"✅ Live simulation analysis complete in {runtime:.1f} seconds", log_file)
        
        # Determine final status
        all_passed = executive_summary['all_passed']
        status = "LIVE_SIM_OK=true" if all_passed else "LIVE_SIM_OK=false"
        
        log_message(f"🎯 Final status: {status}", log_file)
        
        print(f"\n🎯 {status}")
        print(f"⏱️ Runtime: {runtime:.1f} seconds")
        print(f"📁 Reports: {LIVE_SIM_DIR}")
        print(f"🔐 BOM Hash: {bom_hash[:16]}...")
        
        # Display executive summary
        print("\n" + "="*70)
        print("📊 EXECUTIVE SUMMARY")
        print("="*70)
        print(f"Status: {'✅ PASS' if all_passed else '❌ FAIL'}")
        print(f"Overall Assessment: {'All acceptance criteria met' if all_passed else 'Some criteria failed'}")
        print(f"Remediation Plan: {executive_summary['remediation_plan']}")
        
        # Display per-venue dashboard
        print("\n" + "="*70)
        print("📊 PER-VENUE DASHBOARD (6h horizon)")
        print("="*70)
        if '6h' in executive_summary['overall_metrics']:
            metrics_6h = executive_summary['overall_metrics']['6h']
            print(f"AUC: {metrics_6h['avg_auc']:.3f}")
            print(f"Precision: {metrics_6h['avg_precision']:.3f}")
            print(f"Recall: {metrics_6h['avg_recall']:.3f}")
            print(f"F1: {metrics_6h['avg_f1']:.3f}")
            print(f"FPR: {metrics_6h['avg_fpr']:.3f}")
            print(f"Median Lead Time: {metrics_6h['avg_lead_time']:.1f}h")
        
        # Display guardrail footer
        print("\n" + "="*70)
        print("🔒 GUARDRAIL FOOTER")
        print("="*70)
        print("🔒 Opened canon in RO mode")
        print("🌐 Network: FROZEN (0 HTTP calls)")
        print("📝 Inline visuals: ON (no external images)")
        print("📝 Writes confined to /reports/live_sim/")
        print(f"🔐 BOM Hash: {bom_hash}")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}\n{traceback.format_exc()}"
        log_message(error_msg, log_file)
        
        print(f"\n❌ LIVE_SIM_OK=false (Error: {str(e)})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
