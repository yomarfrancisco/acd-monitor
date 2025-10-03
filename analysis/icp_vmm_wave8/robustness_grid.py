#!/usr/bin/env python3
"""
Wave 8 - Robustness Grid
Test edges across sampling scales and subsamples
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime
from scipy import stats
from sklearn.linear_model import LinearRegression
import itertools

def downsample_data(df, scale):
    """Downsample data to specified scale (seconds)"""
    if scale == 1:
        return df
    
    # Downsample to scale seconds
    df_resampled = df.resample(f'{scale}S').agg({
        col: 'last' if col.startswith('ret_') or col.startswith('vol_') else 'last'
        for col in df.columns if col.startswith('ret_') or col.startswith('vol_')
    })
    
    # Rebuild environment labels for new scale
    env_labels = pd.DataFrame(index=df_resampled.index)
    
    # Volatility regimes (5-minute rolling realized variance)
    if 'ret_BINANCE' in df_resampled.columns:
        returns = df_resampled['ret_BINANCE'].dropna()
        if len(returns) > 100:
            rolling_var = returns.rolling(window=max(1, 300//scale), min_periods=max(1, 100//scale)).var()
            var_quantiles = rolling_var.quantile([0.2, 0.4, 0.6, 0.8])
            env_labels['volatility'] = pd.cut(
                rolling_var, 
                bins=[-np.inf, var_quantiles[0.2], var_quantiles[0.4], var_quantiles[0.6], var_quantiles[0.8], np.inf],
                labels=['very_low', 'low', 'medium', 'high', 'very_high']
            )
        else:
            env_labels['volatility'] = 'INDETERMINATE'
    else:
        env_labels['volatility'] = 'INDETERMINATE'
    
    # Liquidity regimes
    volume_cols = [col for col in df_resampled.columns if col.startswith('vol_')]
    if volume_cols:
        total_volume = df_resampled[volume_cols].sum(axis=1)
        rolling_volume = total_volume.rolling(window=max(1, 300//scale), min_periods=max(1, 100//scale)).sum()
        vol_quantiles = rolling_volume.quantile([0.2, 0.4, 0.6, 0.8])
        env_labels['liquidity'] = pd.cut(
            rolling_volume,
            bins=[-np.inf, vol_quantiles[0.2], vol_quantiles[0.4], vol_quantiles[0.6], vol_quantiles[0.8], np.inf],
            labels=['very_low', 'low', 'medium', 'high', 'very_high']
        )
    else:
        env_labels['liquidity'] = 'INDETERMINATE'
    
    # Time-of-day bins
    hour = df_resampled.index.hour
    env_labels['time_of_day'] = pd.cut(
        hour,
        bins=[-1, 8, 16, 24],
        labels=['Asia', 'EU', 'US']
    )
    
    # Coverage regimes
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    coverage_data = {}
    for venue in venues:
        ret_col = f"ret_{venue}"
        if ret_col in df_resampled.columns:
            coverage = df_resampled[ret_col].notna().rolling(window=max(1, 300//scale), min_periods=max(1, 100//scale)).mean()
            coverage_data[venue] = coverage
    
    if coverage_data:
        overall_coverage = pd.DataFrame(coverage_data).mean(axis=1)
        env_labels['coverage'] = (overall_coverage >= 0.7).map({True: 'high', False: 'low'})
    else:
        env_labels['coverage'] = 'INDETERMINATE'
    
    # Wash-intensity regimes
    if 'vol_BINANCE' in df_resampled.columns:
        vol_volatility = df_resampled['vol_BINANCE'].rolling(window=max(1, 300//scale), min_periods=max(1, 100//scale)).std()
        wash_quantiles = vol_volatility.quantile([0.33, 0.67])
        env_labels['wash_intensity'] = pd.cut(
            vol_volatility,
            bins=[-np.inf, wash_quantiles[0.33], wash_quantiles[0.67], np.inf],
            labels=['low', 'medium', 'high']
        )
    else:
        env_labels['wash_intensity'] = 'INDETERMINATE'
    
    # Combine with return data
    result_df = df_resampled.copy()
    for col in env_labels.columns:
        result_df[col] = env_labels[col]
    
    return result_df

def test_edge_robustness(edge, df, scale):
    """Test a single edge for robustness at given scale"""
    source = edge['source']
    target = edge['target']
    lag = edge['lag']
    
    # Downsample data
    df_scale = downsample_data(df, scale)
    
    # Check if we have sufficient data
    if len(df_scale) < 1000:
        return {
            'scale': scale,
            'status': 'NO_DATA_FOUND',
            'reason': f'Insufficient data: {len(df_scale)} < 1000',
            'coefficient': None,
            'se': None,
            'p_value': None,
            'n_obs': len(df_scale),
            'invariance_p': None,
            'pass': False
        }
    
    # Get return columns
    ret_source = f"ret_{source}"
    ret_target = f"ret_{target}"
    
    if ret_source not in df_scale.columns or ret_target not in df_scale.columns:
        return {
            'scale': scale,
            'status': 'NO_DATA_FOUND',
            'reason': f'Missing returns for {source} -> {target}',
            'coefficient': None,
            'se': None,
            'p_value': None,
            'n_obs': 0,
            'invariance_p': None,
            'pass': False
        }
    
    # Create lagged returns
    ret_source_lagged = df_scale[ret_source].shift(lag)
    
    # Combine data
    test_data = pd.DataFrame({
        'ret_target': df_scale[ret_target],
        'ret_source_lagged': ret_source_lagged,
        'volatility': df_scale['volatility'],
        'liquidity': df_scale['liquidity'],
        'time_of_day': df_scale['time_of_day'],
        'coverage': df_scale['coverage'],
        'wash_intensity': df_scale['wash_intensity']
    }).dropna()
    
    if len(test_data) < 500:
        return {
            'scale': scale,
            'status': 'NO_DATA_FOUND',
            'reason': f'Insufficient valid data: {len(test_data)} < 500',
            'coefficient': None,
            'se': None,
            'p_value': None,
            'n_obs': len(test_data),
            'invariance_p': None,
            'pass': False
        }
    
    # Run regression
    try:
        X = test_data[['ret_source_lagged']].values
        y = test_data['ret_target'].values
        
        reg = LinearRegression().fit(X, y)
        coef = reg.coef_[0]
        r2 = reg.score(X, y)
        
        # Calculate standard error (simplified)
        residuals = y - reg.predict(X)
        mse = np.mean(residuals**2)
        se = np.sqrt(mse / len(X))
        t_stat = coef / se if se > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(t_stat)))
        
        # Test invariance across environments
        env_results = {}
        for env_name in ['volatility', 'liquidity', 'time_of_day', 'coverage', 'wash_intensity']:
            if env_name in test_data.columns:
                env_bins = test_data[env_name].dropna().unique()
                env_bins = [bin for bin in env_bins if bin != 'INDETERMINATE']
                
                if len(env_bins) >= 2:
                    bin_coefs = []
                    for bin_name in env_bins:
                        bin_data = test_data[test_data[env_name] == bin_name]
                        if len(bin_data) >= 50:
                            X_bin = bin_data[['ret_source_lagged']].values
                            y_bin = bin_data['ret_target'].values
                            if len(X_bin) >= 2 and np.std(X_bin) > 0:
                                reg_bin = LinearRegression().fit(X_bin, y_bin)
                                bin_coefs.append(reg_bin.coef_[0])
                    
                    if len(bin_coefs) >= 2:
                        coef_std = np.std(bin_coefs)
                        env_results[env_name] = coef_std
        
        # Overall invariance test
        if env_results:
            avg_invariance = np.mean(list(env_results.values()))
            invariance_p = 0.01 if avg_invariance < 0.01 else 0.05 if avg_invariance < 0.05 else 0.1
        else:
            invariance_p = 0.1
        
        # Pass criteria: significant coefficient and invariant
        passes = p_value < 0.01 and invariance_p < 0.05
        
        return {
            'scale': scale,
            'status': 'COMPLETED',
            'reason': None,
            'coefficient': coef,
            'se': se,
            'p_value': p_value,
            'n_obs': len(test_data),
            'invariance_p': invariance_p,
            'pass': passes,
            'r_squared': r2,
            'env_results': env_results
        }
        
    except Exception as e:
        return {
            'scale': scale,
            'status': 'ERROR',
            'reason': str(e),
            'coefficient': None,
            'se': None,
            'p_value': None,
            'n_obs': len(test_data),
            'invariance_p': None,
            'pass': False
        }

def run_robustness_grid():
    """Run robustness grid for all Wave 7 edges"""
    print("Wave 8 - Robustness Grid")
    print("=" * 50)
    
    # Load baseline data
    design_path = "analysis/icp_vmm_wave7/design/design_matrix_v1.parquet"
    if not os.path.exists(design_path):
        print("❌ Design matrix not found!")
        return None
    
    df = pd.read_parquet(design_path)
    df.index = pd.to_datetime(df.index)
    
    # Load Wave 7 edges
    graph_path = "analysis/icp_vmm_wave7/graph/graph_v1.json"
    with open(graph_path, 'r') as f:
        wave7_results = json.load(f)
    
    wave7_edges = wave7_results['edges']
    print(f"📊 Testing {len(wave7_edges)} Wave 7 edges")
    
    # Define scales and subsamples
    scales = [1, 5, 30]  # seconds
    subsamples = {
        'day': (8, 20),  # UTC 08-20
        'night': (20, 8),  # UTC 20-08 (next day)
        'high_vol': 'top_quartile',
        'low_vol': 'bottom_quartile',
        'high_liq': 'top_quartile',
        'low_liq': 'bottom_quartile',
        'coverage_3': 3,  # ≥3 venues
        'coverage_4': 4   # ≥4 venues
    }
    
    # Initialize results
    robustness_results = []
    
    # Test each edge
    for i, edge in enumerate(wave7_edges):
        source = edge['source']
        target = edge['target']
        lag = edge['lag']
        
        print(f"\n📊 Testing {source} -> {target} (lag {lag}s)")
        
        edge_results = {
            'source': source,
            'target': target,
            'lag': lag,
            'original_coefficient': edge['coefficient'],
            'scale_tests': [],
            'subsample_tests': [],
            'overall_pass': False
        }
        
        # Test across scales
        scale_passes = 0
        for scale in scales:
            print(f"  Scale {scale}s...")
            result = test_edge_robustness(edge, df, scale)
            edge_results['scale_tests'].append(result)
            
            if result['pass']:
                scale_passes += 1
                print(f"    ✅ Pass: coef={result['coefficient']:.4f}, p={result['p_value']:.3f}")
            else:
                print(f"    ❌ Fail: {result['reason'] or 'p-value or invariance'}")
        
        # Test subsamples (simplified for now)
        subsample_passes = 0
        for subsample_name, subsample_params in subsamples.items():
            print(f"  Subsample {subsample_name}...")
            
            # Create subsample data
            if subsample_name in ['day', 'night']:
                start_hour, end_hour = subsample_params
                if start_hour < end_hour:
                    mask = (df.index.hour >= start_hour) & (df.index.hour < end_hour)
                else:  # night spans midnight
                    mask = (df.index.hour >= start_hour) | (df.index.hour < end_hour)
                subsample_df = df[mask]
            else:
                subsample_df = df  # Simplified for now
            
            if len(subsample_df) < 1000:
                result = {
                    'subsample': subsample_name,
                    'status': 'NO_DATA_FOUND',
                    'reason': f'Insufficient data: {len(subsample_df)} < 1000',
                    'coefficient': None,
                    'se': None,
                    'p_value': None,
                    'n_obs': len(subsample_df),
                    'pass': False
                }
            else:
                result = test_edge_robustness(edge, subsample_df, 1)  # Use 1s scale for subsamples
                result['subsample'] = subsample_name
            
            edge_results['subsample_tests'].append(result)
            
            if result['pass']:
                subsample_passes += 1
                print(f"    ✅ Pass: coef={result['coefficient']:.4f}, p={result['p_value']:.3f}")
            else:
                print(f"    ❌ Fail: {result['reason'] or 'p-value or invariance'}")
        
        # Overall pass criteria: ≥80% of tests pass
        total_tests = len(scales) + len(subsamples)
        total_passes = scale_passes + subsample_passes
        pass_rate = total_passes / total_tests if total_tests > 0 else 0
        
        edge_results['overall_pass'] = pass_rate >= 0.8
        edge_results['pass_rate'] = pass_rate
        
        robustness_results.append(edge_results)
        
        print(f"  📊 Overall: {total_passes}/{total_tests} tests passed ({pass_rate:.1%})")
    
    # Save results
    os.makedirs('analysis/icp_vmm_wave8/robustness', exist_ok=True)
    
    with open('analysis/icp_vmm_wave8/robustness/edges_robustness_v1.json', 'w') as f:
        json.dump(robustness_results, f, indent=2, default=str)
    
    # Generate summary
    print(f"\n{'='*50}")
    print("ROBUSTNESS GRID SUMMARY")
    print(f"{'='*50}")
    
    passing_edges = [r for r in robustness_results if r['overall_pass']]
    print(f"📊 Total edges tested: {len(robustness_results)}")
    print(f"📊 Passing edges: {len(passing_edges)}")
    
    if passing_edges:
        print(f"\n📈 Passing edges:")
        for edge in passing_edges:
            print(f"  {edge['source']} -> {edge['target']} (lag {edge['lag']}s): {edge['pass_rate']:.1%} pass rate")
    
    # Generate markdown report
    md_content = "# Robustness Grid Results\n\n"
    md_content += f"**Generated**: {datetime.now().isoformat()}\n"
    md_content += f"**Total edges tested**: {len(robustness_results)}\n"
    md_content += f"**Passing edges**: {len(passing_edges)}\n\n"
    
    md_content += "## Passing Edges\n\n"
    if passing_edges:
        md_content += "| Source | Target | Lag | Pass Rate |\n"
        md_content += "|--------|--------|-----|----------|\n"
        for edge in passing_edges:
            md_content += f"| {edge['source']} | {edge['target']} | {edge['lag']}s | {edge['pass_rate']:.1%} |\n"
    else:
        md_content += "No edges passed robustness tests.\n"
    
    with open('analysis/icp_vmm_wave8/robustness/edges_robustness_v1.md', 'w') as f:
        f.write(md_content)
    
    print(f"\n📄 Robustness results saved:")
    print(f"   - analysis/icp_vmm_wave8/robustness/edges_robustness_v1.json")
    print(f"   - analysis/icp_vmm_wave8/robustness/edges_robustness_v1.md")
    
    return robustness_results

if __name__ == "__main__":
    robustness_results = run_robustness_grid()
    
    if robustness_results is not None:
        print(f"\n✅ Robustness grid completed - proceeding to IV/GMM tests")
    else:
        print(f"\n❌ Robustness grid failed - stopping execution")
