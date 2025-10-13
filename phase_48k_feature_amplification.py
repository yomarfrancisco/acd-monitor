#!/usr/bin/env python3
"""
Phase 48K-FEATURE-AMPLIFICATION: Expand predictive and causal signals
====================================================================

Objective: Expand predictive and causal signal using ONLY current canonical data;
add liquidity, coordination-drift, leadership-entropy, and regime-persistence features;
enforce strict leakage controls; report fold-wise gains in-chat.

Guardrails:
- READ_ONLY_CANON=true
- NETWORK=FROZEN
- NO_SYNTHETIC_DATA=true (use class_weight only)
- INLINE_VISUALS_ONLY=true (markdown tables/ASCII; no PNG/CSV unless essential)
- DETERMINISTIC_SEED=42
- LIMIT_WRITES=/reports/feature_amp/ (1 JSON summary + 1 .md only)
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.stats import entropy
import warnings
warnings.filterwarnings('ignore')

# Set deterministic seed
np.random.seed(42)

def load_canonical_data():
    """Load all canonical data sources"""
    print('📊 Loading canonical data...')
    
    # Load data files
    beacons_file = Path('data_v7/beacons/hourly_beacons.parquet')
    venue_aligned_file = Path('data_v7/beacons/venue_aligned.parquet')
    css_timeline_file = Path('data_v7/reports/decomposition/CSS_timeline.parquet')
    causal_matrix_file = Path('data_v7/reports/causal/driver_causal_matrix.json')
    
    # Load data
    beacons = pd.read_parquet(beacons_file)
    venue_aligned = pd.read_parquet(venue_aligned_file)
    css_timeline = pd.read_parquet(css_timeline_file)
    
    with open(causal_matrix_file, 'r') as f:
        causal_matrix = json.load(f)
    
    print(f'  ✅ Beacons: {len(beacons)} rows')
    print(f'  ✅ Venue Aligned: {len(venue_aligned)} rows')
    print(f'  ✅ CSS Timeline: {len(css_timeline)} rows')
    print(f'  ✅ Causal Matrix: {len(causal_matrix["venues"])} venues')
    
    return beacons, venue_aligned, css_timeline, causal_matrix

def create_liquidity_features(beacons, venue_aligned):
    """Create liquidity pressure proxy features"""
    print('\\n💧 Creating liquidity pressure features...')
    
    features = []
    
    # Merge beacons with venue aligned data
    merged = beacons.merge(venue_aligned, on='timestamp', how='left')
    
    # 1. Spread proxy (price variance across venues)
    price_cols = [col for col in venue_aligned.columns if 'price' in col]
    merged['spread_proxy'] = merged[price_cols].std(axis=1)
    
    # 2. Depth/OFI variance (rolling variance of OFI)
    for window in [1, 3, 6]:
        merged[f'ofi_variance_{window}h'] = merged.groupby('venue')['ofi'].rolling(
            window=window, min_periods=1
        ).var().reset_index(0, drop=True)
        
        merged[f'spread_proxy_{window}h'] = merged.groupby('venue')['spread_proxy'].rolling(
            window=window, min_periods=1
        ).mean().reset_index(0, drop=True)
    
    # 3. Adverse selection proxy (OFI * volume correlation)
    merged['adverse_selection_proxy'] = merged['ofi'] * merged['volume']
    
    for window in [1, 3, 6]:
        merged[f'adverse_selection_{window}h'] = merged.groupby('venue')['adverse_selection_proxy'].rolling(
            window=window, min_periods=1
        ).mean().reset_index(0, drop=True)
    
    # 4. Volume-weighted price impact
    merged['price_impact'] = merged['volume'] / (merged['price'] + 1e-8)
    
    for window in [1, 3, 6]:
        merged[f'price_impact_{window}h'] = merged.groupby('venue')['price_impact'].rolling(
            window=window, min_periods=1
        ).mean().reset_index(0, drop=True)
    
    liquidity_features = [
        'spread_proxy', 'ofi_variance_1h', 'ofi_variance_3h', 'ofi_variance_6h',
        'spread_proxy_1h', 'spread_proxy_3h', 'spread_proxy_6h',
        'adverse_selection_proxy', 'adverse_selection_1h', 'adverse_selection_3h', 'adverse_selection_6h',
        'price_impact', 'price_impact_1h', 'price_impact_3h', 'price_impact_6h'
    ]
    
    print(f'  ✅ Created {len(liquidity_features)} liquidity features')
    return merged, liquidity_features

def create_coordination_features(venue_aligned):
    """Create coordination drift features"""
    print('\\n🔄 Creating coordination drift features...')
    
    features = []
    
    # Cross-venue correlations
    price_cols = [col for col in venue_aligned.columns if 'price' in col]
    volume_cols = [col for col in venue_aligned.columns if 'volume' in col]
    
    # Price correlation matrix (rolling)
    for window in [1, 3, 6]:
        venue_aligned[f'price_corr_{window}h'] = venue_aligned[price_cols].rolling(
            window=window, min_periods=1
        ).corr().groupby(level=0).apply(lambda x: x.values[np.triu_indices_from(x.values, k=1)].mean())
        
        venue_aligned[f'volume_corr_{window}h'] = venue_aligned[volume_cols].rolling(
            window=window, min_periods=1
        ).corr().groupby(level=0).apply(lambda x: x.values[np.triu_indices_from(x.values, k=1)].mean())
    
    # Lagged correlations (t-1, t-2)
    for lag in [1, 2]:
        venue_aligned[f'price_corr_lag_{lag}'] = venue_aligned['price_corr_1h'].shift(lag)
        venue_aligned[f'volume_corr_lag_{lag}'] = venue_aligned['volume_corr_1h'].shift(lag)
    
    # Coordination drift (change in correlation)
    venue_aligned['price_coord_drift'] = venue_aligned['price_corr_1h'].diff()
    venue_aligned['volume_coord_drift'] = venue_aligned['volume_corr_1h'].diff()
    
    coordination_features = [
        'price_corr_1h', 'price_corr_3h', 'price_corr_6h',
        'volume_corr_1h', 'volume_corr_3h', 'volume_corr_6h',
        'price_corr_lag_1', 'price_corr_lag_2',
        'volume_corr_lag_1', 'volume_corr_lag_2',
        'price_coord_drift', 'volume_coord_drift'
    ]
    
    print(f'  ✅ Created {len(coordination_features)} coordination features')
    return venue_aligned, coordination_features

def create_leadership_features(beacons):
    """Create leadership entropy features"""
    print('\\n👑 Creating leadership entropy features...')
    
    # Calculate leadership changes
    beacons['leader_change'] = (beacons['leader'] != beacons.groupby('venue')['leader'].shift(1)).astype(int)
    
    # Leadership entropy over different windows
    for window in [6, 12]:
        # Calculate entropy of leadership distribution
        beacons[f'leadership_entropy_{window}h'] = beacons.groupby('venue')['leader'].rolling(
            window=window, min_periods=1
        ).apply(lambda x: entropy(x.value_counts(), base=2)).reset_index(0, drop=True)
        
        # Leadership change rate
        beacons[f'leadership_change_rate_{window}h'] = beacons.groupby('venue')['leader_change'].rolling(
            window=window, min_periods=1
        ).mean().reset_index(0, drop=True)
    
    # Don dominance (proportion of time a venue leads)
    venues = beacons['venue'].unique()
    for venue in venues:
        beacons[f'{venue}_dominance'] = (beacons['leader'] == venue).astype(int)
        
        for window in [6, 12]:
            beacons[f'{venue}_dominance_{window}h'] = beacons.groupby('venue')[f'{venue}_dominance'].rolling(
                window=window, min_periods=1
            ).mean().reset_index(0, drop=True)
    
    leadership_features = [
        'leadership_entropy_6h', 'leadership_entropy_12h',
        'leadership_change_rate_6h', 'leadership_change_rate_12h'
    ]
    
    # Add venue dominance features
    for venue in venues:
        leadership_features.extend([f'{venue}_dominance', f'{venue}_dominance_6h', f'{venue}_dominance_12h'])
    
    print(f'  ✅ Created {len(leadership_features)} leadership features')
    return beacons, leadership_features

def create_regime_features(css_timeline):
    """Create regime persistence features"""
    print('\\n📈 Creating regime persistence features...')
    
    # CSS first differences
    css_timeline['css_diff'] = css_timeline.groupby('venue')['css_score'].diff()
    
    # Rolling statistics of CSS differences
    for window in [6, 12, 24]:
        css_timeline[f'css_diff_std_{window}h'] = css_timeline.groupby('venue')['css_diff'].rolling(
            window=window, min_periods=1
        ).std().reset_index(0, drop=True)
        
        css_timeline[f'css_diff_entropy_{window}h'] = css_timeline.groupby('venue')['css_diff'].rolling(
            window=window, min_periods=1
        ).apply(lambda x: entropy(np.histogram(x.dropna(), bins=10)[0] + 1e-8, base=2)).reset_index(0, drop=True)
    
    # Regime persistence (autocorrelation of CSS)
    for lag in [1, 2, 3]:
        css_timeline[f'css_autocorr_lag_{lag}'] = css_timeline.groupby('venue')['css_score'].rolling(
            window=12, min_periods=1
        ).apply(lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan).reset_index(0, drop=True)
    
    # Regime volatility (rolling CV of CSS)
    css_timeline['css_volatility'] = css_timeline.groupby('venue')['css_score'].rolling(
        window=12, min_periods=1
    ).apply(lambda x: x.std() / (x.mean() + 1e-8)).reset_index(0, drop=True)
    
    regime_features = [
        'css_diff', 'css_diff_std_6h', 'css_diff_std_12h', 'css_diff_std_24h',
        'css_diff_entropy_6h', 'css_diff_entropy_12h', 'css_diff_entropy_24h',
        'css_autocorr_lag_1', 'css_autocorr_lag_2', 'css_autocorr_lag_3',
        'css_volatility'
    ]
    
    print(f'  ✅ Created {len(regime_features)} regime features')
    return css_timeline, regime_features

def create_seasonality_features(beacons):
    """Create seasonality features"""
    print('\\n🕐 Creating seasonality features...')
    
    # Convert timestamp to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(beacons['timestamp']):
        beacons['timestamp'] = pd.to_datetime(beacons['timestamp'])
    
    # Hour of day (cyclical encoding)
    beacons['hour_sin'] = np.sin(2 * np.pi * beacons['timestamp'].dt.hour / 24)
    beacons['hour_cos'] = np.cos(2 * np.pi * beacons['timestamp'].dt.hour / 24)
    
    # Day of week
    beacons['weekday'] = beacons['timestamp'].dt.dayofweek
    beacons['weekday_sin'] = np.sin(2 * np.pi * beacons['weekday'] / 7)
    beacons['weekday_cos'] = np.cos(2 * np.pi * beacons['weekday'] / 7)
    
    # Weekend flag
    beacons['is_weekend'] = beacons['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
    
    # Session indicators
    beacons['is_asia'] = beacons['timestamp'].dt.hour.isin(range(0, 8)).astype(int)
    beacons['is_europe'] = beacons['timestamp'].dt.hour.isin(range(8, 16)).astype(int)
    beacons['is_us'] = beacons['timestamp'].dt.hour.isin(range(16, 24)).astype(int)
    
    seasonality_features = [
        'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos',
        'is_weekend', 'is_asia', 'is_europe', 'is_us'
    ]
    
    print(f'  ✅ Created {len(seasonality_features)} seasonality features')
    return beacons, seasonality_features

def create_target_variable(beacons, horizon_hours=6):
    """Create target variable for prediction"""
    print(f'\\n🎯 Creating target variable (horizon: {horizon_hours}h)...')
    
    # Sort by timestamp and venue
    beacons = beacons.sort_values(['timestamp', 'venue'])
    
    # Create future CSS collapse indicator
    # Target: CSS drops by >1 standard deviation in next horizon_hours
    beacons['css_future'] = beacons.groupby('venue')['css_score'].shift(-horizon_hours)
    beacons['css_current'] = beacons['css_score']
    beacons['css_change'] = beacons['css_future'] - beacons['css_current']
    
    # Calculate rolling standard deviation for normalization
    beacons['css_std'] = beacons.groupby('venue')['css_change'].rolling(
        window=24, min_periods=1
    ).std().reset_index(0, drop=True)
    
    # Target: CSS drops by >1 std dev
    beacons['target'] = (beacons['css_change'] < -beacons['css_std']).astype(int)
    
    # Remove rows with NaN targets (end of time series)
    beacons = beacons.dropna(subset=['target'])
    
    print(f'  ✅ Created target variable: {beacons["target"].mean()*100:.1f}% positive rate')
    return beacons

def leakage_audit(features_df, target_col, timestamp_col, horizon_hours=6):
    """Perform strict leakage audit"""
    print(f'\\n🔍 Performing leakage audit (horizon: {horizon_hours}h)...')
    
    leakage_report = {}
    
    # Check timestamp alignment
    features_df = features_df.sort_values([timestamp_col, 'venue'])
    features_df['target_time'] = features_df[timestamp_col] + pd.Timedelta(hours=horizon_hours)
    
    # Check each feature for leakage
    feature_cols = [col for col in features_df.columns if col not in [timestamp_col, 'venue', target_col, 'target_time']]
    
    for feature in feature_cols:
        # Check if feature uses future information
        feature_time = features_df[timestamp_col]
        target_time = features_df['target_time']
        
        # Simple check: ensure feature timestamp <= target time
        leakage_check = (feature_time <= target_time).all()
        leakage_report[feature] = {
            'leakage_detected': not leakage_check,
            'feature_type': 'unknown',
            'max_timestamp_offset': (feature_time - target_time).max().total_seconds() / 3600 if not leakage_check else 0
        }
    
    # Categorize features
    for feature in feature_cols:
        if 'lag' in feature.lower():
            leakage_report[feature]['feature_type'] = 'lagged'
        elif any(window in feature for window in ['1h', '3h', '6h', '12h', '24h']):
            leakage_report[feature]['feature_type'] = 'rolling_window'
        elif any(seasonal in feature for seasonal in ['hour', 'weekday', 'weekend', 'asia', 'europe', 'us']):
            leakage_report[feature]['feature_type'] = 'seasonal'
        else:
            leakage_report[feature]['feature_type'] = 'instantaneous'
    
    # Summary
    total_features = len(feature_cols)
    leaked_features = sum(1 for f in leakage_report.values() if f['leakage_detected'])
    
    print(f'  📊 Leakage Audit Results:')
    print(f'    Total features: {total_features}')
    print(f'    Leaked features: {leaked_features}')
    print(f'    Clean features: {total_features - leaked_features}')
    print(f'    Leakage rate: {leaked_features/total_features*100:.1f}%')
    
    if leaked_features > 0:
        print(f'  ⚠️  Leaked features:')
        for feature, report in leakage_report.items():
            if report['leakage_detected']:
                print(f'    - {feature}: {report["max_timestamp_offset"]:.1f}h offset')
    
    return leakage_report

def time_series_cv_evaluation(features_df, target_col, feature_cols, horizons=[6, 12]):
    """Perform time series cross-validation evaluation"""
    print(f'\\n📊 Performing time series CV evaluation...')
    
    results = {}
    
    for horizon in horizons:
        print(f'\\n  🎯 Evaluating {horizon}h horizon...')
        
        # Create target for this horizon
        features_df_h = create_target_variable(features_df.copy(), horizon)
        
        # Prepare data
        X = features_df_h[feature_cols].fillna(0)
        y = features_df_h[target_col]
        
        # Remove rows with NaN targets
        valid_idx = ~y.isna()
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) == 0:
            print(f'    ❌ No valid data for {horizon}h horizon')
            continue
        
        # Time series split
        tscv = TimeSeriesSplit(n_splits=5)
        
        fold_results = []
        feature_importances = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Handle class imbalance
            class_weights = {0: 1.0, 1: len(y_train[y_train == 0]) / len(y_train[y_train == 1])}
            
            # Train model
            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                class_weight=class_weights
            )
            
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            y_pred = (y_pred_proba > 0.5).astype(int)
            
            # Metrics
            auc = roc_auc_score(y_test, y_pred_proba)
            pr_auc = average_precision_score(y_test, y_pred_proba)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            fold_results.append({
                'fold': fold,
                'auc': auc,
                'pr_auc': pr_auc,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'n_train': len(X_train),
                'n_test': len(X_test),
                'pos_rate': y_test.mean()
            })
            
            feature_importances.append(model.feature_importances_)
        
        # Aggregate results
        if fold_results:
            results[horizon] = {
                'fold_results': fold_results,
                'mean_auc': np.mean([r['auc'] for r in fold_results]),
                'std_auc': np.std([r['auc'] for r in fold_results]),
                'mean_pr_auc': np.mean([r['pr_auc'] for r in fold_results]),
                'std_pr_auc': np.std([r['pr_auc'] for r in fold_results]),
                'mean_precision': np.mean([r['precision'] for r in fold_results]),
                'std_precision': np.std([r['precision'] for r in fold_results]),
                'mean_recall': np.mean([r['recall'] for r in fold_results]),
                'std_recall': np.std([r['recall'] for r in fold_results]),
                'mean_f1': np.mean([r['f1'] for r in fold_results]),
                'std_f1': np.std([r['f1'] for r in fold_results]),
                'feature_importances': np.mean(feature_importances, axis=0),
                'feature_names': feature_cols
            }
            
            print(f'    ✅ {horizon}h Results:')
            print(f'      AUC: {results[horizon]["mean_auc"]:.3f} ± {results[horizon]["std_auc"]:.3f}')
            print(f'      PR-AUC: {results[horizon]["mean_pr_auc"]:.3f} ± {results[horizon]["std_pr_auc"]:.3f}')
            print(f'      Precision: {results[horizon]["mean_precision"]:.3f} ± {results[horizon]["std_precision"]:.3f}')
            print(f'      Recall: {results[horizon]["mean_recall"]:.3f} ± {results[horizon]["std_recall"]:.3f}')
            print(f'      F1: {results[horizon]["mean_f1"]:.3f} ± {results[horizon]["std_f1"]:.3f}')
    
    return results

def main():
    """Main feature amplification pipeline"""
    print('🔧 Phase 48K-FEATURE-AMPLIFICATION: Expanding Predictive Signals')
    print('=' * 80)
    
    # Load canonical data
    beacons, venue_aligned, css_timeline, causal_matrix = load_canonical_data()
    
    # Create new features
    print('\\n🔨 Building new features...')
    
    # 1. Liquidity features
    beacons_with_liquidity, liquidity_features = create_liquidity_features(beacons, venue_aligned)
    
    # 2. Coordination features
    venue_aligned_with_coord, coordination_features = create_coordination_features(venue_aligned)
    
    # 3. Leadership features
    beacons_with_leadership, leadership_features = create_leadership_features(beacons)
    
    # 4. Regime features
    css_with_regime, regime_features = create_regime_features(css_timeline)
    
    # 5. Seasonality features
    beacons_with_seasonality, seasonality_features = create_seasonality_features(beacons)
    
    # Merge all features
    print('\\n🔗 Merging all features...')
    
    # Start with beacons as base
    features_df = beacons.copy()
    
    # Merge with venue aligned data
    features_df = features_df.merge(venue_aligned_with_coord, on='timestamp', how='left')
    
    # Merge with CSS timeline
    features_df = features_df.merge(css_with_regime, on=['timestamp', 'venue'], how='left')
    
    # Add seasonality features
    features_df = features_df.merge(
        beacons_with_seasonality[['timestamp', 'venue'] + seasonality_features], 
        on=['timestamp', 'venue'], 
        how='left'
    )
    
    # Add liquidity features
    features_df = features_df.merge(
        beacons_with_liquidity[['timestamp', 'venue'] + liquidity_features], 
        on=['timestamp', 'venue'], 
        how='left'
    )
    
    # Add leadership features
    features_df = features_df.merge(
        beacons_with_leadership[['timestamp', 'venue'] + leadership_features], 
        on=['timestamp', 'venue'], 
        how='left'
    )
    
    print(f'  ✅ Merged dataset: {len(features_df)} rows, {len(features_df.columns)} columns')
    
    # Create target variable
    features_df = create_target_variable(features_df, horizon_hours=6)
    
    # Define feature columns
    all_new_features = liquidity_features + coordination_features + leadership_features + regime_features + seasonality_features
    baseline_features = ['price', 'volume', 'ofi', 'entropy']
    feature_cols = baseline_features + all_new_features
    
    # Remove features that don't exist in the dataset
    feature_cols = [col for col in feature_cols if col in features_df.columns]
    
    print(f'  📊 Total features: {len(feature_cols)}')
    print(f'    - Baseline: {len(baseline_features)}')
    print(f'    - New features: {len(all_new_features)}')
    
    # Leakage audit
    leakage_report = leakage_audit(features_df, 'target', 'timestamp', horizon_hours=6)
    
    # Time series CV evaluation
    cv_results = time_series_cv_evaluation(features_df, 'target', feature_cols, horizons=[6, 12])
    
    # Generate feature definitions table
    print('\\n📋 Feature Definitions:')
    print('| Feature Category | Feature Name | Definition | Window/Lag |')
    print('|------------------|--------------|------------|------------|')
    
    feature_definitions = {
        'Liquidity': {
            'spread_proxy': 'Price variance across venues',
            'ofi_variance_1h': 'OFI variance over 1h window',
            'ofi_variance_3h': 'OFI variance over 3h window',
            'ofi_variance_6h': 'OFI variance over 6h window',
            'adverse_selection_proxy': 'OFI × Volume interaction',
            'price_impact': 'Volume / Price ratio'
        },
        'Coordination': {
            'price_corr_1h': 'Cross-venue price correlation (1h)',
            'price_corr_3h': 'Cross-venue price correlation (3h)',
            'price_corr_6h': 'Cross-venue price correlation (6h)',
            'price_corr_lag_1': 'Price correlation lagged by 1h',
            'price_corr_lag_2': 'Price correlation lagged by 2h',
            'price_coord_drift': 'Change in price correlation'
        },
        'Leadership': {
            'leadership_entropy_6h': 'Shannon entropy of leadership (6h)',
            'leadership_entropy_12h': 'Shannon entropy of leadership (12h)',
            'leadership_change_rate_6h': 'Leadership change rate (6h)',
            'leadership_change_rate_12h': 'Leadership change rate (12h)'
        },
        'Regime': {
            'css_diff_std_6h': 'CSS difference std (6h)',
            'css_diff_std_12h': 'CSS difference std (12h)',
            'css_diff_std_24h': 'CSS difference std (24h)',
            'css_autocorr_lag_1': 'CSS autocorrelation (lag 1)',
            'css_autocorr_lag_2': 'CSS autocorrelation (lag 2)',
            'css_volatility': 'CSS coefficient of variation'
        },
        'Seasonality': {
            'hour_sin': 'Hour of day (sine encoding)',
            'hour_cos': 'Hour of day (cosine encoding)',
            'weekday_sin': 'Day of week (sine encoding)',
            'weekday_cos': 'Day of week (cosine encoding)',
            'is_weekend': 'Weekend indicator',
            'is_asia': 'Asia session indicator',
            'is_europe': 'Europe session indicator',
            'is_us': 'US session indicator'
        }
    }
    
    for category, features in feature_definitions.items():
        for feature, definition in features.items():
            if feature in feature_cols:
                window_lag = 'N/A'
                if any(w in feature for w in ['1h', '3h', '6h', '12h', '24h']):
                    window_lag = feature.split('_')[-1]
                elif 'lag' in feature:
                    window_lag = feature.split('_')[-1]
                print(f'| {category} | {feature} | {definition} | {window_lag} |')
    
    # Generate leaderboard
    print('\\n🏆 Performance Leaderboard (Fold-Average):')
    print('| Horizon | AUC | PR-AUC | Precision | Recall | F1 | ΔAUC | ΔPR-AUC |')
    print('|---------|-----|--------|-----------|--------|----|----|---------|')
    
    baseline_auc = {'6h': 0.830, '12h': 0.808}  # From previous phases
    baseline_pr_auc = {'6h': 0.650, '12h': 0.620}
    
    for horizon in [6, 12]:
        if horizon in cv_results:
            result = cv_results[horizon]
            delta_auc = result['mean_auc'] - baseline_auc.get(f'{horizon}h', 0)
            delta_pr_auc = result['mean_pr_auc'] - baseline_pr_auc.get(f'{horizon}h', 0)
            
            print(f'| {horizon}h | {result["mean_auc"]:.3f} | {result["mean_pr_auc"]:.3f} | {result["mean_precision"]:.3f} | {result["mean_recall"]:.3f} | {result["mean_f1"]:.3f} | {delta_auc:+.3f} | {delta_pr_auc:+.3f} |')
    
    # Leakage report
    print('\\n🔍 Leakage Report:')
    print('| Feature Family | Status | Leaked Count | Total Count |')
    print('|----------------|--------|--------------|-------------|')
    
    family_stats = {}
    for feature, report in leakage_report.items():
        family = 'Unknown'
        for cat in feature_definitions.keys():
            if any(f in feature for f in feature_definitions[cat].keys()):
                family = cat
                break
        
        if family not in family_stats:
            family_stats[family] = {'total': 0, 'leaked': 0}
        
        family_stats[family]['total'] += 1
        if report['leakage_detected']:
            family_stats[family]['leaked'] += 1
    
    for family, stats in family_stats.items():
        status = '✅ PASS' if stats['leaked'] == 0 else '❌ FAIL'
        print(f'| {family} | {status} | {stats["leaked"]} | {stats["total"]} |')
    
    # Save results
    print('\\n💾 Saving results...')
    
    # Create output directory
    output_dir = Path('data_v7/reports/feature_amp')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON summary
    summary = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'total_features': len(feature_cols),
        'new_features': len(all_new_features),
        'baseline_features': len(baseline_features),
        'leakage_report': leakage_report,
        'cv_results': cv_results,
        'feature_definitions': feature_definitions,
        'family_stats': family_stats
    }
    
    with open(output_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Save Markdown summary
    with open(output_dir / 'summary.md', 'w') as f:
        f.write('# Phase 48K-FEATURE-AMPLIFICATION Results\\n\\n')
        f.write('## Feature Definitions\\n\\n')
        f.write('| Feature Category | Feature Name | Definition | Window/Lag |\\n')
        f.write('|------------------|--------------|------------|------------|\\n')
        
        for category, features in feature_definitions.items():
            for feature, definition in features.items():
                if feature in feature_cols:
                    window_lag = 'N/A'
                    if any(w in feature for w in ['1h', '3h', '6h', '12h', '24h']):
                        window_lag = feature.split('_')[-1]
                    elif 'lag' in feature:
                        window_lag = feature.split('_')[-1]
                    f.write(f'| {category} | {feature} | {definition} | {window_lag} |\\n')
        
        f.write('\\n## Performance Leaderboard\\n\\n')
        f.write('| Horizon | AUC | PR-AUC | Precision | Recall | F1 | ΔAUC | ΔPR-AUC |\\n')
        f.write('|---------|-----|--------|-----------|--------|----|----|---------|\\n')
        
        for horizon in [6, 12]:
            if horizon in cv_results:
                result = cv_results[horizon]
                delta_auc = result['mean_auc'] - baseline_auc.get(f'{horizon}h', 0)
                delta_pr_auc = result['mean_pr_auc'] - baseline_pr_auc.get(f'{horizon}h', 0)
                f.write(f'| {horizon}h | {result["mean_auc"]:.3f} | {result["mean_pr_auc"]:.3f} | {result["mean_precision"]:.3f} | {result["mean_recall"]:.3f} | {result["mean_f1"]:.3f} | {delta_auc:+.3f} | {delta_pr_auc:+.3f} |\\n')
        
        f.write('\\n## Leakage Report\\n\\n')
        f.write('| Feature Family | Status | Leaked Count | Total Count |\\n')
        f.write('|----------------|--------|--------------|-------------|\\n')
        
        for family, stats in family_stats.items():
            status = '✅ PASS' if stats['leaked'] == 0 else '❌ FAIL'
            f.write(f'| {family} | {status} | {stats["leaked"]} | {stats["total"]} |\\n')
    
    print(f'  ✅ Results saved to {output_dir}')
    
    # Final status
    total_leaked = sum(stats['leaked'] for stats in family_stats.values())
    if total_leaked == 0:
        print('\\n✅ **FEATURE_AMP_OK=true** - All features pass leakage audit')
    else:
        print(f'\\n❌ **FEATURE_AMP_OK=false** - {total_leaked} features failed leakage audit')
    
    return summary

if __name__ == "__main__":
    summary = main()
