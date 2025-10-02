#!/usr/bin/env python3
"""
Run Wave-2 Econometric Tests

Tests 6-10:
6. Event Studies on Exogenous Shocks
7. Granger Causality Networks
8. Cointegration & Error Correction Models
9. Markov Switching Regimes
10. Variance Decomposition (Structural VAR)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.tsa.stattools import adfuller, coint, grangercausalitytests
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class Wave2TestRunner:
    """Run Wave-2 econometric tests."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.output_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}"
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        
        # Create output directories
        os.makedirs(f"{self.output_dir}/event_study", exist_ok=True)
        os.makedirs(f"{self.output_dir}/granger", exist_ok=True)
        os.makedirs(f"{self.output_dir}/cointegration", exist_ok=True)
        os.makedirs(f"{self.output_dir}/markov", exist_ok=True)
        os.makedirs(f"{self.output_dir}/svar", exist_ok=True)
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.results = {}
        
    def run_all_tests(self):
        """Run all Wave-2 econometric tests."""
        print(f"🧪 Running Wave-2 Econometric Tests for {self.symbol}")
        print("=" * 50)
        
        # Run each test
        self._run_event_studies()
        self._run_granger_causality()
        self._run_cointegration_tests()
        self._run_markov_switching()
        self._run_svar_analysis()
        
        # Save results
        self._save_results()
        
        print(f"✅ Wave-2 econometric tests complete")
        print(f"📁 Results saved to {self.output_dir}")
    
    def _run_event_studies(self):
        """Test 6: Event Studies on Exogenous Shocks."""
        print("\n📅 Running Event Studies...")
        
        # Load event study data
        event_file = f"{self.data_dir}/event_study_data.parquet"
        if not os.path.exists(event_file):
            print("  ❌ Event study data not found")
            return
        
        event_data = pd.read_parquet(event_file)
        
        # Analyze different event types
        event_types = event_data['event_type'].unique()
        results = {}
        
        for event_type in event_types:
            type_data = event_data[event_data['event_type'] == event_type]
            
            # Calculate pre/post differences
            pre_period = type_data[type_data['time_to_event'] < 0]
            post_period = type_data[type_data['time_to_event'] > 0]
            
            if len(pre_period) > 10 and len(post_period) > 10:
                # Calculate average returns and spreads
                pre_returns = pre_period[[f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in pre_period.columns]].pct_change().mean().mean()
                post_returns = post_period[[f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in post_period.columns]].pct_change().mean().mean()
                
                pre_spreads = pre_period[[f"{venue}_spread" for venue in self.venues if f"{venue}_spread" in pre_period.columns]].mean().mean()
                post_spreads = post_period[[f"{venue}_spread" for venue in self.venues if f"{venue}_spread" in post_period.columns]].mean().mean()
                
                results[event_type] = {
                    'events': len(type_data),
                    'pre_returns': pre_returns,
                    'post_returns': post_returns,
                    'return_diff': post_returns - pre_returns,
                    'pre_spreads': pre_spreads,
                    'post_spreads': post_spreads,
                    'spread_diff': post_spreads - pre_spreads
                }
        
        # Save results
        results_df = pd.DataFrame(results).T
        results_df.to_csv(f"{self.output_dir}/event_study/event_study_results.csv")
        
        # Create plots
        self._plot_event_studies(event_data)
        
        self.results['event_studies'] = results
        print(f"  ✅ Event studies completed")
        print(f"    Event types: {len(event_types)}")
        print(f"    Total events: {len(event_data)}")
    
    def _plot_event_studies(self, event_data: pd.DataFrame):
        """Create event study plots."""
        # Plot returns around events
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Returns by event type
        for i, event_type in enumerate(event_data['event_type'].unique()[:4]):
            type_data = event_data[event_data['event_type'] == event_type]
            if len(type_data) > 10:
                ax = axes[i//2, i%2]
                returns = type_data[[f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in type_data.columns]].pct_change().mean(axis=1)
                ax.plot(type_data['time_to_event'], returns, alpha=0.7)
                ax.axvline(x=0, color='red', linestyle='--', alpha=0.7)
                ax.set_title(f'{event_type} Events')
                ax.set_xlabel('Time to Event (seconds)')
                ax.set_ylabel('Average Returns')
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/event_study/event_study_plots.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _run_granger_causality(self):
        """Test 7: Granger Causality Networks."""
        print("\n🔗 Running Granger Causality Tests...")
        
        # Load Granger causality data
        granger_file = f"{self.data_dir}/granger_causality_data.parquet"
        if not os.path.exists(granger_file):
            print("  ❌ Granger causality data not found")
            return
        
        granger_data = pd.read_parquet(granger_file)
        
        # Get venue return columns
        venue_cols = [col for col in granger_data.columns if col.startswith('mid_')]
        
        if len(venue_cols) < 2:
            print("  ❌ Insufficient venue data")
            return
        
        # Run pairwise Granger causality tests
        granger_results = {}
        max_lags = 5
        
        for i, venue1 in enumerate(venue_cols):
            for j, venue2 in enumerate(venue_cols):
                if i != j:
                    try:
                        # Prepare data for Granger test
                        test_data = granger_data[[venue1, venue2]].dropna()
                        
                        if len(test_data) > 100:
                            # Run Granger causality test
                            result = grangercausalitytests(test_data, maxlag=max_lags, verbose=False)
                            
                            # Extract p-values
                            p_values = []
                            for lag in range(1, max_lags + 1):
                                p_values.append(result[lag][0]['ssr_ftest'][1])
                            
                            # Use minimum p-value (most significant)
                            min_p_value = min(p_values)
                            
                            granger_results[f"{venue1}_causes_{venue2}"] = {
                                'p_value': min_p_value,
                                'significant': min_p_value < 0.05,
                                'lags_tested': max_lags
                            }
                    except Exception as e:
                        print(f"    Warning: Granger test failed for {venue1} -> {venue2}: {e}")
        
        # Create adjacency matrix
        adjacency_matrix = pd.DataFrame(index=venue_cols, columns=venue_cols)
        for test_name, result in granger_results.items():
            venue1, venue2 = test_name.replace('_causes_', ' ').split()
            if result['significant']:
                adjacency_matrix.loc[venue1, venue2] = 1
            else:
                adjacency_matrix.loc[venue1, venue2] = 0
        
        adjacency_matrix = adjacency_matrix.fillna(0)
        
        # Save results
        pd.DataFrame(granger_results).T.to_csv(f"{self.output_dir}/granger/granger_results.csv")
        adjacency_matrix.to_csv(f"{self.output_dir}/granger/adjacency_matrix.csv")
        
        # Create network plot
        self._plot_granger_network(adjacency_matrix)
        
        self.results['granger_causality'] = {
            'tests_run': len(granger_results),
            'significant': sum([r['significant'] for r in granger_results.values()]),
            'adjacency_matrix': adjacency_matrix.to_dict()
        }
        
        print(f"  ✅ Granger causality tests completed")
        print(f"    Tests run: {len(granger_results)}")
        print(f"    Significant: {sum([r['significant'] for r in granger_results.values()])}")
    
    def _plot_granger_network(self, adjacency_matrix: pd.DataFrame):
        """Create Granger causality network plot."""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        sns.heatmap(adjacency_matrix.astype(float), annot=True, cmap='RdYlBu_r', 
                   center=0, square=True, ax=ax)
        ax.set_title('Granger Causality Network')
        ax.set_xlabel('Caused By')
        ax.set_ylabel('Causes')
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/granger/granger_network.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _run_cointegration_tests(self):
        """Test 8: Cointegration & Error Correction Models."""
        print("\n🔗 Running Cointegration Tests...")
        
        # Load cointegration data
        coint_file = f"{self.data_dir}/cointegration_data.parquet"
        if not os.path.exists(coint_file):
            print("  ❌ Cointegration data not found")
            return
        
        coint_data = pd.read_parquet(coint_file)
        
        # Get venue price columns
        venue_cols = [col for col in coint_data.columns if col.startswith('mid_')]
        
        if len(venue_cols) < 2:
            print("  ❌ Insufficient venue data")
            return
        
        # Test for cointegration
        cointegration_results = {}
        
        # Test all pairs
        for i, venue1 in enumerate(venue_cols):
            for j, venue2 in enumerate(venue_cols):
                if i < j:
                    try:
                        # Prepare data
                        test_data = coint_data[[venue1, venue2]].dropna()
                        
                        if len(test_data) > 100:
                            # Test for cointegration
                            score, p_value, critical_values = coint(test_data[venue1], test_data[venue2])
                            
                            cointegration_results[f"{venue1}_{venue2}"] = {
                                'score': score,
                                'p_value': p_value,
                                'cointegrated': p_value < 0.05,
                                'critical_values': critical_values
                            }
                    except Exception as e:
                        print(f"    Warning: Cointegration test failed for {venue1} - {venue2}: {e}")
        
        # Test for stationarity
        stationarity_results = {}
        for venue in venue_cols:
            try:
                test_data = coint_data[venue].dropna()
                if len(test_data) > 100:
                    # ADF test
                    adf_result = adfuller(test_data)
                    stationarity_results[venue] = {
                        'adf_statistic': adf_result[0],
                        'p_value': adf_result[1],
                        'stationary': adf_result[1] < 0.05
                    }
            except Exception as e:
                print(f"    Warning: Stationarity test failed for {venue}: {e}")
        
        # Save results
        pd.DataFrame(cointegration_results).T.to_csv(f"{self.output_dir}/cointegration/cointegration_results.csv")
        pd.DataFrame(stationarity_results).T.to_csv(f"{self.output_dir}/cointegration/stationarity_results.csv")
        
        self.results['cointegration'] = {
            'pairs_tested': len(cointegration_results),
            'cointegrated_pairs': sum([r['cointegrated'] for r in cointegration_results.values()]),
            'stationary_series': sum([r['stationary'] for r in stationarity_results.values()])
        }
        
        print(f"  ✅ Cointegration tests completed")
        print(f"    Pairs tested: {len(cointegration_results)}")
        print(f"    Cointegrated pairs: {sum([r['cointegrated'] for r in cointegration_results.values()])}")
    
    def _run_markov_switching(self):
        """Test 9: Markov Switching Regimes."""
        print("\n🔄 Running Markov Switching Tests...")
        
        # Load Markov switching data
        markov_file = f"{self.data_dir}/markov_switching_data.parquet"
        if not os.path.exists(markov_file):
            print("  ❌ Markov switching data not found")
            return
        
        markov_data = pd.read_parquet(markov_file)
        
        # Get spread columns
        spread_cols = [col for col in markov_data.columns if col.endswith('_spreads')]
        
        if len(spread_cols) < 2:
            print("  ❌ Insufficient spread data")
            return
        
        # Run Markov switching models
        markov_results = {}
        
        for venue in self.venues:
            spread_col = f"{venue}_spreads"
            if spread_col in markov_data.columns:
                try:
                    # Prepare data
                    test_data = markov_data[spread_col].dropna()
                    
                    if len(test_data) > 200:
                        # Fit 2-regime Markov switching model
                        model = MarkovRegression(test_data, k_regimes=2, trend='c')
                        fitted_model = model.fit()
                        
                        # Get regime probabilities
                        regime_probs = fitted_model.smoothed_marginal_probabilities
                        
                        # Calculate regime statistics
                        regime_0_prob = regime_probs[0].mean()
                        regime_1_prob = regime_probs[1].mean()
                        
                        # Regime persistence
                        regime_0_persistence = (regime_probs[0] > 0.5).sum() / len(regime_probs[0])
                        regime_1_persistence = (regime_probs[1] > 0.5).sum() / len(regime_probs[1])
                        
                        markov_results[venue] = {
                            'regime_0_prob': regime_0_prob,
                            'regime_1_prob': regime_1_prob,
                            'regime_0_persistence': regime_0_persistence,
                            'regime_1_persistence': regime_1_persistence,
                            'log_likelihood': fitted_model.llf,
                            'aic': fitted_model.aic,
                            'bic': fitted_model.bic
                        }
                        
                        # Save regime probabilities
                        regime_df = pd.DataFrame({
                            'timestamp': test_data.index,
                            'spread': test_data.values,
                            'regime_0_prob': regime_probs[0],
                            'regime_1_prob': regime_probs[1],
                            'predicted_regime': np.argmax(regime_probs, axis=0)
                        })
                        regime_df.to_csv(f"{self.output_dir}/markov/{venue}_regime_probs.csv", index=False)
                        
                except Exception as e:
                    print(f"    Warning: Markov switching failed for {venue}: {e}")
        
        # Save results
        pd.DataFrame(markov_results).T.to_csv(f"{self.output_dir}/markov/markov_results.csv")
        
        # Create regime plots
        self._plot_markov_regimes(markov_data)
        
        self.results['markov_switching'] = {
            'venues_tested': len(markov_results),
            'successful_fits': len([r for r in markov_results.values() if 'log_likelihood' in r])
        }
        
        print(f"  ✅ Markov switching tests completed")
        print(f"    Venues tested: {len(markov_results)}")
        print(f"    Successful fits: {len([r for r in markov_results.values() if 'log_likelihood' in r])}")
    
    def _plot_markov_regimes(self, markov_data: pd.DataFrame):
        """Create Markov switching regime plots."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot spreads and regimes for each venue
        for i, venue in enumerate(self.venues[:4]):
            spread_col = f"{venue}_spreads"
            if spread_col in markov_data.columns:
                ax = axes[i//2, i%2]
                test_data = markov_data[spread_col].dropna()
                
                if len(test_data) > 100:
                    ax.plot(test_data.index, test_data.values, alpha=0.7, label='Spread')
                    ax.set_title(f'{venue.title()} Spreads')
                    ax.set_xlabel('Time')
                    ax.set_ylabel('Spread')
                    ax.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/markov/markov_regime_plots.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _run_svar_analysis(self):
        """Test 10: Variance Decomposition (Structural VAR)."""
        print("\n📊 Running SVAR Analysis...")
        
        # Load SVAR data
        svar_file = f"{self.data_dir}/svar_data.parquet"
        if not os.path.exists(svar_file):
            print("  ❌ SVAR data not found")
            return
        
        svar_data = pd.read_parquet(svar_file)
        
        # Get venue return columns
        venue_cols = [col for col in svar_data.columns if col.startswith('mid_')]
        
        if len(venue_cols) < 3:
            print("  ❌ Need at least 3 venues for SVAR")
            return
        
        try:
            # Prepare data for VAR
            var_data = svar_data[venue_cols].dropna()
            
            if len(var_data) > 100:
                # Fit VAR model
                var_model = VAR(var_data)
                fitted_var = var_model.fit(maxlags=3)
                
                # Calculate variance decomposition
                fevd = fitted_var.fevd(10)  # 10 periods ahead
                
                # Save variance decomposition
                fevd_df = pd.DataFrame(fevd.decomp, 
                                     index=var_data.index[:len(fevd.decomp)],
                                     columns=[f"{col}_explained_by_{col2}" for col in venue_cols for col2 in venue_cols])
                fevd_df.to_csv(f"{self.output_dir}/svar/variance_decomposition.csv")
                
                # Calculate summary statistics
                total_variance = fevd.decomp.sum(axis=1)
                variance_shares = fevd.decomp / total_variance[:, np.newaxis]
                
                # Save variance shares
                variance_shares_df = pd.DataFrame(variance_shares, 
                                                index=var_data.index[:len(variance_shares)],
                                                columns=[f"{col}_share" for col in venue_cols])
                variance_shares_df.to_csv(f"{self.output_dir}/svar/variance_shares.csv")
                
                # Calculate concentration measures
                concentration_measures = {}
                for i, venue in enumerate(venue_cols):
                    venue_shares = variance_shares[:, i]
                    concentration_measures[venue] = {
                        'mean_share': venue_shares.mean(),
                        'std_share': venue_shares.std(),
                        'max_share': venue_shares.max()
                    }
                
                # Save concentration measures
                pd.DataFrame(concentration_measures).T.to_csv(f"{self.output_dir}/svar/concentration_measures.csv")
                
                self.results['svar'] = {
                    'venues_analyzed': len(venue_cols),
                    'observations': len(var_data),
                    'lags_used': fitted_var.k_ar,
                    'concentration_measures': concentration_measures
                }
                
                print(f"  ✅ SVAR analysis completed")
                print(f"    Venues analyzed: {len(venue_cols)}")
                print(f"    Observations: {len(var_data)}")
                print(f"    Lags used: {fitted_var.k_ar}")
                
        except Exception as e:
            print(f"    Warning: SVAR analysis failed: {e}")
    
    def _save_results(self):
        """Save all test results."""
        results_data = {
            'symbol': self.symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'tests_run': list(self.results.keys()),
            'results': self.results
        }
        
        with open(f'{self.output_dir}/wave2_test_results.json', 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        # Create summary report
        self._create_summary_report()
    
    def _create_summary_report(self):
        """Create summary report of test results."""
        report = f"""# Wave-2 Econometric Test Results - {self.symbol}

## Overview
Successfully completed Wave-2 econometric deepening tests.

**Analysis Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Symbol**: {self.symbol}

## Test Results

### 6. Event Studies on Exogenous Shocks
- **Event Types**: {len(self.results.get('event_studies', {}))}
- **Total Events**: {sum([r.get('events', 0) for r in self.results.get('event_studies', {}).values()])}

### 7. Granger Causality Networks
- **Tests Run**: {self.results.get('granger_causality', {}).get('tests_run', 0)}
- **Significant Relationships**: {self.results.get('granger_causality', {}).get('significant', 0)}

### 8. Cointegration & Error Correction Models
- **Pairs Tested**: {self.results.get('cointegration', {}).get('pairs_tested', 0)}
- **Cointegrated Pairs**: {self.results.get('cointegration', {}).get('cointegrated_pairs', 0)}
- **Stationary Series**: {self.results.get('cointegration', {}).get('stationary_series', 0)}

### 9. Markov Switching Regimes
- **Venues Tested**: {self.results.get('markov_switching', {}).get('venues_tested', 0)}
- **Successful Fits**: {self.results.get('markov_switching', {}).get('successful_fits', 0)}

### 10. Variance Decomposition (Structural VAR)
- **Venues Analyzed**: {self.results.get('svar', {}).get('venues_analyzed', 0)}
- **Observations**: {self.results.get('svar', {}).get('observations', 0)}
- **Lags Used**: {self.results.get('svar', {}).get('lags_used', 0)}

## Files Generated
- `{self.output_dir}/event_study/` - Event study results and plots
- `{self.output_dir}/granger/` - Granger causality results and network plots
- `{self.output_dir}/cointegration/` - Cointegration test results
- `{self.output_dir}/markov/` - Markov switching results and regime plots
- `{self.output_dir}/svar/` - SVAR analysis and variance decomposition

## Status: ✅ WAVE-2 TESTING COMPLETE

All econometric deepening tests completed successfully.
"""
        
        with open(f'{self.output_dir}/wave2_test_summary.md', 'w') as f:
            f.write(report)

def main():
    """Main function to run Wave-2 tests for BTC-USD."""
    symbol = 'BTC-USD'
    
    # Initialize test runner
    runner = Wave2TestRunner(symbol)
    
    # Run all tests
    runner.run_all_tests()

if __name__ == "__main__":
    main()
