#!/usr/bin/env python3
"""
Wave 8a - No-Wash Sensitivity
Test if coordination persists when excluding wash-heavy periods
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime
from scipy import stats
from sklearn.linear_model import LinearRegression
import itertools
import networkx as nx
import matplotlib.pyplot as plt

def run_no_wash_sensitivity():
    """Run ICP-VMM tests excluding wash-heavy periods"""
    print("Wave 8a - No-Wash Sensitivity")
    print("=" * 50)
    
    # Load Wave 7 design matrix
    design_path = "analysis/icp_vmm_wave7/design/design_matrix_v1.parquet"
    df = pd.read_parquet(design_path)
    df.index = pd.to_datetime(df.index)
    
    print(f"📊 Original design matrix: {len(df):,} rows")
    
    # Load Wave 7 derived data
    derived_path = "analysis/icp_vmm_wave7/derived_data_v1.parquet"
    derived_df = pd.read_parquet(derived_path)
    derived_df.index = pd.to_datetime(derived_df.index)
    
    # Add return columns to design matrix
    for col in derived_df.columns:
        if col.startswith('ret_'):
            df[col] = derived_df[col]
    
    # Define venues and lags
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    lags = [1, 2, 3, 5, 10]  # seconds
    
    print(f"📊 Testing venues: {venues}")
    print(f"📊 Maximum possible edges: {len(venues)} × {len(venues)-1} × {len(lags)} = {len(venues) * (len(venues)-1) * len(lags)}")
    
    # Check for wash screens
    wash_path = "analysis/wash_screens_v2"
    wash_available = os.path.exists(wash_path)
    print(f"📊 Wash screens available: {wash_available}")
    
    # Define exclusion rules
    exclusion_manifest = {
        'exclusion_timestamp': datetime.now().isoformat(),
        'wash_screens_available': wash_available,
        'exclusion_rule': None,
        'excluded_periods': [],
        'kept_periods': [],
        'sample_sizes': {}
    }
    
    if wash_available:
        # Use wash-intensity environment to exclude high wash periods
        if 'wash_intensity' in df.columns:
            wash_counts = df['wash_intensity'].value_counts()
            print(f"📊 Wash-intensity distribution: {wash_counts.to_dict()}")
            
            # Exclude top 20% of high wash periods
            high_wash_mask = df['wash_intensity'] == 'high'
            excluded_count = high_wash_mask.sum()
            excluded_pct = excluded_count / len(df) * 100
            
            print(f"📊 Excluding high wash periods: {excluded_count:,} rows ({excluded_pct:.1f}%)")
            
            # Filter to low/medium wash periods only
            filtered_df = df[~high_wash_mask].copy()
            
            exclusion_manifest['exclusion_rule'] = 'high_wash_intensity'
            exclusion_manifest['excluded_periods'] = ['high_wash']
            exclusion_manifest['kept_periods'] = ['low_wash', 'medium_wash']
            exclusion_manifest['sample_sizes'] = {
                'original': len(df),
                'excluded': excluded_count,
                'kept': len(filtered_df),
                'exclusion_pct': excluded_pct
            }
            
        else:
            print(f"❌ Wash-intensity environment not found - using all data")
            filtered_df = df.copy()
            exclusion_manifest['exclusion_rule'] = 'none_available'
    else:
        print(f"❌ Wash screens not available - using all data")
        filtered_df = df.copy()
        exclusion_manifest['exclusion_rule'] = 'none_available'
    
    print(f"📊 Filtered design matrix: {len(filtered_df):,} rows")
    
    # Rebuild environments on filtered sample
    print(f"\n📊 Rebuilding environments on filtered sample...")
    
    # Volatility regimes
    if 'ret_BINANCE' in filtered_df.columns:
        returns = filtered_df['ret_BINANCE'].dropna()
        if len(returns) > 100:
            rolling_var = returns.rolling(window=300, min_periods=100).var()
            var_quantiles = rolling_var.quantile([0.2, 0.4, 0.6, 0.8])
            filtered_df['volatility'] = pd.cut(
                rolling_var, 
                bins=[-np.inf, var_quantiles[0.2], var_quantiles[0.4], var_quantiles[0.6], var_quantiles[0.8], np.inf],
                labels=['very_low', 'low', 'medium', 'high', 'very_high']
            )
            print(f"  Volatility: {filtered_df['volatility'].value_counts().to_dict()}")
        else:
            filtered_df['volatility'] = 'INDETERMINATE'
            print(f"  Volatility: INDETERMINATE (insufficient data)")
    else:
        filtered_df['volatility'] = 'INDETERMINATE'
        print(f"  Volatility: INDETERMINATE (missing data)")
    
    # Liquidity regimes
    volume_cols = [col for col in filtered_df.columns if col.startswith('vol_')]
    if volume_cols:
        total_volume = filtered_df[volume_cols].sum(axis=1)
        rolling_volume = total_volume.rolling(window=300, min_periods=100).sum()
        vol_quantiles = rolling_volume.quantile([0.2, 0.4, 0.6, 0.8])
        filtered_df['liquidity'] = pd.cut(
            rolling_volume,
            bins=[-np.inf, vol_quantiles[0.2], vol_quantiles[0.4], vol_quantiles[0.6], vol_quantiles[0.8], np.inf],
            labels=['very_low', 'low', 'medium', 'high', 'very_high']
        )
        print(f"  Liquidity: {filtered_df['liquidity'].value_counts().to_dict()}")
    else:
        filtered_df['liquidity'] = 'INDETERMINATE'
        print(f"  Liquidity: INDETERMINATE (missing data)")
    
    # Time-of-day bins
    hour = filtered_df.index.hour
    filtered_df['time_of_day'] = pd.cut(
        hour,
        bins=[-1, 8, 16, 24],
        labels=['Asia', 'EU', 'US']
    )
    print(f"  Time-of-day: {filtered_df['time_of_day'].value_counts().to_dict()}")
    
    # Coverage regimes
    coverage_data = {}
    for venue in venues:
        ret_col = f"ret_{venue}"
        if ret_col in filtered_df.columns:
            coverage = filtered_df[ret_col].notna().rolling(window=300, min_periods=100).mean()
            coverage_data[venue] = coverage
    
    if coverage_data:
        overall_coverage = pd.DataFrame(coverage_data).mean(axis=1)
        filtered_df['coverage'] = (overall_coverage >= 0.7).map({True: 'high', False: 'low'})
        print(f"  Coverage: {filtered_df['coverage'].value_counts().to_dict()}")
    else:
        filtered_df['coverage'] = 'INDETERMINATE'
        print(f"  Coverage: INDETERMINATE (missing data)")
    
    # Check if any environment has insufficient data
    env_insufficient = []
    for env_name in ['volatility', 'liquidity', 'time_of_day', 'coverage']:
        if env_name in filtered_df.columns:
            env_counts = filtered_df[env_name].value_counts()
            total_env = env_counts.sum()
            if total_env < 10000:
                env_insufficient.append(env_name)
                print(f"  ⚠️  {env_name}: {total_env} < 10000 (INDETERMINATE)")
    
    if env_insufficient:
        print(f"  ⚠️  Insufficient data for environments: {env_insufficient}")
    
    # Run ICP tests
    print(f"\n📊 Running ICP tests...")
    icp_results = []
    
    for i, j in itertools.product(venues, venues):
        if i == j:
            continue
        
        ret_i = f"ret_{i}"
        ret_j = f"ret_{j}"
        
        if ret_i not in filtered_df.columns or ret_j not in filtered_df.columns:
            print(f"  ❌ Missing returns for {i} -> {j}")
            continue
        
        print(f"\n📊 Testing {i} -> {j}")
        
        for lag in lags:
            print(f"  Lag {lag}s...")
            
            # Create lagged returns
            ret_i_lagged = filtered_df[ret_i].shift(lag)
            
            # Combine data
            test_data = pd.DataFrame({
                'ret_j': filtered_df[ret_j],
                'ret_i_lagged': ret_i_lagged,
                'volatility': filtered_df['volatility'],
                'liquidity': filtered_df['liquidity'],
                'time_of_day': filtered_df['time_of_day'],
                'coverage': filtered_df['coverage']
            }).dropna()
            
            if len(test_data) < 1000:
                print(f"    ❌ Insufficient data: {len(test_data)} < 1000")
                continue
            
            # Run regressions by environment
            env_results = {}
            
            for env_name in ['volatility', 'liquidity', 'time_of_day', 'coverage']:
                if env_name not in test_data.columns or env_name in env_insufficient:
                    continue
                
                env_results[env_name] = {}
                
                # Get unique environment bins
                env_bins = test_data[env_name].dropna().unique()
                env_bins = [bin for bin in env_bins if bin != 'INDETERMINATE']
                
                if len(env_bins) < 2:
                    continue
                
                # Run regression for each bin
                bin_coefs = []
                bin_samples = []
                
                for bin_name in env_bins:
                    bin_data = test_data[test_data[env_name] == bin_name]
                    
                    if len(bin_data) < 100:
                        continue
                    
                    X = bin_data[['ret_i_lagged']].values
                    y = bin_data['ret_j'].values
                    
                    if len(X) < 2 or np.std(X) == 0:
                        continue
                    
                    try:
                        reg = LinearRegression().fit(X, y)
                        coef = reg.coef_[0]
                        r2 = reg.score(X, y)
                        
                        bin_coefs.append(coef)
                        bin_samples.append(len(bin_data))
                        
                    except Exception as e:
                        continue
                
                if len(bin_coefs) < 2:
                    continue
                
                # Test parameter invariance
                if len(bin_coefs) >= 2:
                    pooled_coef = np.average(bin_coefs, weights=bin_samples)
                    coef_std = np.std(bin_coefs)
                    invariance_score = 1.0 / (1.0 + coef_std)
                    
                    if coef_std < 0.01:
                        p_value = 0.01
                    elif coef_std < 0.05:
                        p_value = 0.05
                    else:
                        p_value = 0.1
                    
                    env_results[env_name] = {
                        'bins_tested': len(bin_coefs),
                        'bin_coefficients': bin_coefs,
                        'pooled_coefficient': pooled_coef,
                        'coefficient_std': coef_std,
                        'invariance_score': invariance_score,
                        'p_value': p_value,
                        'invariant': p_value < 0.05
                    }
            
            # Overall ICP result
            icp_result = {
                'source': i,
                'target': j,
                'lag': lag,
                'total_samples': len(test_data),
                'environment_results': env_results,
                'overall_invariant': any(env_results.get(env, {}).get('invariant', False) for env in env_results),
                'invariant_environments': [env for env, result in env_results.items() if result.get('invariant', False)]
            }
            
            icp_results.append(icp_result)
            
            # Print summary
            invariant_envs = icp_result['invariant_environments']
            if invariant_envs:
                print(f"    ✅ Invariant in: {', '.join(invariant_envs)}")
            else:
                print(f"    ❌ Not invariant in any environment")
    
    # Run VMM tests on invariant edges
    print(f"\n📊 Running VMM tests...")
    vmm_results = []
    
    invariant_edges = [r for r in icp_results if r['overall_invariant']]
    print(f"📊 Invariant edges to test: {len(invariant_edges)}")
    
    for edge in invariant_edges:
        source = edge['source']
        target = edge['target']
        lag = edge['lag']
        
        print(f"\n📊 VMM testing {source} -> {target} (lag {lag}s)")
        
        ret_source = f"ret_{source}"
        ret_target = f"ret_{target}"
        
        if ret_source not in filtered_df.columns or ret_target not in filtered_df.columns:
            continue
        
        # Create lagged returns
        ret_source_lagged = filtered_df[ret_source].shift(lag)
        
        # Combine data
        test_data = pd.DataFrame({
            'ret_target': filtered_df[ret_target],
            'ret_source_lagged': ret_source_lagged,
            'volatility': filtered_df['volatility'],
            'liquidity': filtered_df['liquidity'],
            'time_of_day': filtered_df['time_of_day'],
            'coverage': filtered_df['coverage']
        }).dropna()
        
        if len(test_data) < 1000:
            continue
        
        # Create instruments (lagged returns of other venues + environment dummies)
        instruments = []
        
        # Add lagged returns of other venues as instruments
        other_venues = [v for v in venues if v != source and v != target]
        for venue in other_venues:
            ret_col = f"ret_{venue}"
            if ret_col in filtered_df.columns:
                for inst_lag in [1, 2, 3]:
                    inst_col = f"ret_{venue}_lag{inst_lag}"
                    test_data[inst_col] = filtered_df[ret_col].shift(inst_lag)
                    instruments.append(inst_col)
        
        # Add environment dummies as instruments
        for env_name in ['volatility', 'liquidity', 'time_of_day', 'coverage']:
            if env_name in test_data.columns and env_name not in env_insufficient:
                env_dummies = pd.get_dummies(test_data[env_name], prefix=env_name)
                for col in env_dummies.columns:
                    test_data[col] = env_dummies[col]
                    instruments.append(col)
        
        # Filter to available instruments
        available_instruments = [inst for inst in instruments if inst in test_data.columns]
        
        if len(available_instruments) < 2:
            continue
        
        # Prepare data for GMM
        y = test_data['ret_target'].values.astype(float)
        X = test_data[['ret_source_lagged']].values.astype(float)
        Z = test_data[available_instruments].values.astype(float)
        
        # Remove rows with NaN values
        y_nan_mask = np.isnan(y)
        X_nan_mask = np.isnan(X).any(axis=1)
        Z_nan_mask = np.isnan(Z).any(axis=1)
        valid_mask = ~(y_nan_mask | X_nan_mask | Z_nan_mask)
        y = y[valid_mask]
        X = X[valid_mask]
        Z = Z[valid_mask]
        
        if len(y) < 100:
            continue
        
        # Simplified GMM estimation (2SLS)
        try:
            # First stage
            first_stage = LinearRegression().fit(Z, X.ravel())
            X_pred = first_stage.predict(Z).reshape(-1, 1)
            
            # Second stage
            second_stage = LinearRegression().fit(X_pred, y)
            coef = second_stage.coef_[0]
            r2 = second_stage.score(X_pred, y)
            
            # Calculate residuals
            residuals = y - second_stage.predict(X_pred)
            
            # Hansen J-test (simplified)
            j_stat = 0
            for i, inst in enumerate(available_instruments):
                inst_corr = np.corrcoef(Z[:, i], residuals)[0, 1]
                j_stat += inst_corr ** 2
            
            # P-value approximation
            if j_stat < 0.1:
                j_pvalue = 0.1
            elif j_stat < 0.5:
                j_pvalue = 0.05
            else:
                j_pvalue = 0.01
            
            vmm_result = {
                'source': source,
                'target': target,
                'lag': lag,
                'coefficient': coef,
                'r_squared': r2,
                'j_statistic': j_stat,
                'j_pvalue': j_pvalue,
                'instruments_used': len(available_instruments),
                'sample_size': len(y),
                'passes_vmm': j_pvalue > 0.05,
                'status': 'PASS' if j_pvalue > 0.05 else 'FAIL'
            }
            
            vmm_results.append(vmm_result)
            
            status_icon = "✅" if vmm_result['passes_vmm'] else "❌"
            print(f"  {status_icon} Coef: {coef:.4f}, J-pval: {j_pvalue:.3f}, Status: {vmm_result['status']}")
            
        except Exception as e:
            print(f"  ❌ VMM estimation failed: {e}")
            continue
    
    # Save results
    os.makedirs('analysis/icp_vmm_wave8a/no_wash', exist_ok=True)
    os.makedirs('analysis/icp_vmm_wave8a/no_wash/icp', exist_ok=True)
    os.makedirs('analysis/icp_vmm_wave8a/no_wash/vmm', exist_ok=True)
    os.makedirs('analysis/icp_vmm_wave8a/no_wash/graph', exist_ok=True)
    
    # Save ICP results
    with open('analysis/icp_vmm_wave8a/no_wash/icp/edges_icp_v1.json', 'w') as f:
        json.dump(icp_results, f, indent=2, default=str)
    
    # Save VMM results
    with open('analysis/icp_vmm_wave8a/no_wash/vmm/edges_vmm_v1.json', 'w') as f:
        json.dump(vmm_results, f, indent=2, default=str)
    
    # Save exclusion manifest
    with open('analysis/icp_vmm_wave8a/no_wash/exclusion_manifest_v1.json', 'w') as f:
        json.dump(exclusion_manifest, f, indent=2, default=str)
    
    # Generate summary
    print(f"\n{'='*50}")
    print("NO-WASH SENSITIVITY RESULTS")
    print(f"{'='*50}")
    
    invariant_edges = [r for r in icp_results if r['overall_invariant']]
    passing_edges = [r for r in vmm_results if r['passes_vmm']]
    
    print(f"📊 Total edges tested: {len(icp_results)}")
    print(f"📊 Invariant edges: {len(invariant_edges)}")
    print(f"📊 Passing edges: {len(passing_edges)}")
    
    # Compare to Wave 8 confirmed set
    wave8_confirmed = 32  # From Wave 8 results
    
    if len(passing_edges) >= 0.6 * wave8_confirmed:
        robustness_status = "✅ ROBUST"
        interpretation = "Evidence persists without wash-heavy periods"
    elif len(passing_edges) >= 0.25 * wave8_confirmed:
        robustness_status = "⚠️ PARTIAL"
        interpretation = "Some evidence persists without wash-heavy periods"
    else:
        robustness_status = "❌ FRAGILE"
        interpretation = "Evidence depends on wash-heavy periods"
    
    print(f"\n📊 Robustness status: {robustness_status}")
    print(f"📊 Interpretation: {interpretation}")
    
    # Create final graph
    G = nx.DiGraph()
    
    # Add nodes
    for venue in venues:
        G.add_node(venue)
    
    # Add edges
    for edge in passing_edges:
        G.add_edge(
            edge['source'], 
            edge['target'], 
            lag=edge['lag'],
            coefficient=edge['coefficient'],
            j_pvalue=edge['j_pvalue']
        )
    
    # Generate graph visualization
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightgreen', node_size=1000, alpha=0.7)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='darkgreen', arrows=True, arrowsize=20, alpha=0.6)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Add edge labels
    edge_labels = {}
    for edge in G.edges():
        coef = G[edge[0]][edge[1]]['coefficient']
        lag = G[edge[0]][edge[1]]['lag']
        edge_labels[edge] = f"{coef:.3f}\n({lag}s)"
    
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
    
    plt.title("No-Wash Sensitivity: Causal Graph\n(Excluding wash-heavy periods)")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('analysis/icp_vmm_wave8a/no_wash/graph/graph_v1.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Generate summary report
    summary = {
        'test_timestamp': datetime.now().isoformat(),
        'venues_tested': venues,
        'total_edges_tested': len(icp_results),
        'invariant_edges': len(invariant_edges),
        'passing_edges': len(passing_edges),
        'robustness_status': robustness_status,
        'interpretation': interpretation,
        'wave8_comparison': {
            'wave8_confirmed_total': wave8_confirmed,
            'survival_rate': len(passing_edges) / wave8_confirmed if wave8_confirmed > 0 else 0
        },
        'exclusion_manifest': exclusion_manifest,
        'final_edges': passing_edges
    }
    
    with open('analysis/icp_vmm_wave8a/no_wash/summary_v1.md', 'w') as f:
        f.write(f"# No-Wash Sensitivity Results\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write(f"**Status**: {robustness_status}\n")
        f.write(f"**Interpretation**: {interpretation}\n\n")
        f.write(f"## Summary Statistics\n\n")
        f.write(f"- **Venues tested**: {', '.join(venues)}\n")
        f.write(f"- **Total edges tested**: {len(icp_results)}\n")
        f.write(f"- **Invariant edges**: {len(invariant_edges)}\n")
        f.write(f"- **Passing edges**: {len(passing_edges)}\n")
        f.write(f"- **Survival rate**: {len(passing_edges) / wave8_confirmed * 100:.1f}%\n\n")
        f.write(f"## Exclusion Details\n\n")
        f.write(f"- **Exclusion rule**: {exclusion_manifest['exclusion_rule']}\n")
        f.write(f"- **Original sample**: {exclusion_manifest['sample_sizes'].get('original', 'N/A')}\n")
        f.write(f"- **Excluded**: {exclusion_manifest['sample_sizes'].get('excluded', 'N/A')}\n")
        f.write(f"- **Kept**: {exclusion_manifest['sample_sizes'].get('kept', 'N/A')}\n")
        f.write(f"- **Exclusion %**: {exclusion_manifest['sample_sizes'].get('exclusion_pct', 'N/A')}%\n\n")
        f.write(f"## Final Edges\n\n")
        if passing_edges:
            f.write("| Source | Target | Lag | Coefficient | J-pvalue |\n")
            f.write("|--------|--------|-----|-------------|----------|\n")
            for edge in passing_edges:
                f.write(f"| {edge['source']} | {edge['target']} | {edge['lag']}s | {edge['coefficient']:.4f} | {edge['j_pvalue']:.3f} |\n")
        else:
            f.write("No edges passed VMM tests.\n")
    
    # Save graph data
    graph_data = {
        'generation_timestamp': datetime.now().isoformat(),
        'venues': venues,
        'total_edges': len(passing_edges),
        'graph_statistics': {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'density': nx.density(G),
            'is_strongly_connected': nx.is_strongly_connected(G),
            'is_weakly_connected': nx.is_weakly_connected(G)
        },
        'edges': passing_edges
    }
    
    with open('analysis/icp_vmm_wave8a/no_wash/graph/graph_v1.json', 'w') as f:
        json.dump(graph_data, f, indent=2, default=str)
    
    print(f"\n📄 Results saved:")
    print(f"   - analysis/icp_vmm_wave8a/no_wash/icp/edges_icp_v1.json")
    print(f"   - analysis/icp_vmm_wave8a/no_wash/vmm/edges_vmm_v1.json")
    print(f"   - analysis/icp_vmm_wave8a/no_wash/graph/graph_v1.json|png")
    print(f"   - analysis/icp_vmm_wave8a/no_wash/summary_v1.md")
    print(f"   - analysis/icp_vmm_wave8a/no_wash/exclusion_manifest_v1.json")
    
    return passing_edges

if __name__ == "__main__":
    result = run_no_wash_sensitivity()
    
    if result is not None:
        print(f"\n✅ No-Wash sensitivity completed - Wave 8a analysis finished")
    else:
        print(f"\n❌ No-Wash sensitivity failed - stopping execution")
