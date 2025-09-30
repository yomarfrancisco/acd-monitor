#!/usr/bin/env python3
"""
Execute Wave-1 Econometric Tests (Baseline Statistical Screens)

Tests 1-5:
1. Variance Ratio Test
2. Autocorrelation & AR(1) Decay  
3. Cross-Correlation of Prices/Spreads
4. PCA Loadings / Common Factor Analysis
5. Rolling Volatility & Spread Convergence
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class Wave1TestExecutor:
    """Execute Wave-1 econometric tests."""
    
    def __init__(self, symbol: str, variables_file: str):
        self.symbol = symbol
        self.variables_file = variables_file
        self.variables = {}
        self.results = {}
        self.plots_dir = f"analysis/wave1/{symbol.replace('-', '_').lower()}"
        
        # Create output directory
        os.makedirs(self.plots_dir, exist_ok=True)
        
        # Load variables
        self._load_variables()
        
    def _load_variables(self):
        """Load prepared variables from file."""
        with open(self.variables_file, 'r') as f:
            data = json.load(f)
            self.variables = data['variables']
        
        print(f"📊 Loaded variables for {self.symbol}")
        print(f"  Venues: {list(self.variables.get('variance_ratios', {}).keys())}")
    
    def run_all_tests(self):
        """Execute all Wave-1 tests."""
        print(f"\n🚀 Running Wave-1 Tests for {self.symbol}")
        print("=" * 50)
        
        # Test 1: Variance Ratio Test
        self._test_variance_ratio()
        
        # Test 2: Autocorrelation & AR(1) Decay
        self._test_autocorrelation()
        
        # Test 3: Cross-Correlation of Prices/Spreads
        self._test_cross_correlation()
        
        # Test 4: PCA Loadings / Common Factor Analysis
        self._test_pca_analysis()
        
        # Test 5: Rolling Volatility & Spread Convergence
        self._test_volatility_convergence()
        
        # Save results
        self._save_results()
        
        print(f"\n✅ Wave-1 tests complete for {self.symbol}")
        print(f"📁 Results saved to {self.plots_dir}")
    
    def _test_variance_ratio(self):
        """Test 1: Variance Ratio Test."""
        print("\n📈 Test 1: Variance Ratio Test")
        
        if 'variance_ratios' not in self.variables:
            print("  ❌ No variance ratio data available")
            return
        
        vr_data = self.variables['variance_ratios']
        
        # Create variance ratio table
        venues = list(vr_data.keys())
        lags = ['vr_2', 'vr_4', 'vr_8', 'vr_16', 'vr_32']
        
        vr_table = pd.DataFrame(index=venues, columns=lags)
        for venue in venues:
            for lag in lags:
                vr_table.loc[venue, lag] = vr_data[venue].get(lag, np.nan)
        
        # Interpretation
        interpretation = {
            'vr_1': 'VR ≈ 1: Random walk (competitive)',
            'vr_gt_1': 'VR > 1: Trending (possible coordination)',
            'vr_lt_1': 'VR < 1: Mean reversion (competitive)'
        }
        
        # Generate plot
        plt.figure(figsize=(12, 8))
        vr_table.plot(kind='bar', ax=plt.gca())
        plt.title(f'{self.symbol} - Variance Ratios by Venue and Lag')
        plt.xlabel('Venue')
        plt.ylabel('Variance Ratio')
        plt.xticks(rotation=45)
        plt.legend(title='Lag', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{self.plots_dir}/variance_ratios.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save table
        vr_table.to_csv(f'{self.plots_dir}/variance_ratios.csv')
        
        self.results['variance_ratio'] = {
            'table': vr_table.to_dict(),
            'interpretation': interpretation,
            'summary': self._analyze_variance_ratios(vr_table)
        }
        
        print(f"  ✅ Variance ratio test complete")
        print(f"    Plot: {self.plots_dir}/variance_ratios.png")
        print(f"    Table: {self.plots_dir}/variance_ratios.csv")
    
    def _test_autocorrelation(self):
        """Test 2: Autocorrelation & AR(1) Decay."""
        print("\n🔄 Test 2: Autocorrelation & AR(1) Decay")
        
        if 'autocorrelations' not in self.variables:
            print("  ❌ No autocorrelation data available")
            return
        
        ac_data = self.variables['autocorrelations']
        
        # Create autocorrelation table
        venues = list(ac_data.keys())
        lags = ['ac_lag_1', 'ac_lag_2', 'ac_lag_3', 'ac_lag_5', 'ac_lag_10', 'ac_lag_20']
        
        ac_table = pd.DataFrame(index=venues, columns=lags)
        ar1_table = pd.DataFrame(index=venues, columns=['ar1_coef'])
        
        for venue in venues:
            for lag in lags:
                value = ac_data[venue].get(lag, np.nan)
                ac_table.loc[venue, lag] = float(value) if pd.notna(value) else np.nan
            ar1_value = ac_data[venue].get('ar1_coef', np.nan)
            ar1_table.loc[venue, 'ar1_coef'] = float(ar1_value) if pd.notna(ar1_value) else np.nan
        
        # Ensure numeric types
        ac_table = ac_table.astype(float)
        ar1_table = ar1_table.astype(float)
        
        # Generate plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Autocorrelation heatmap
        sns.heatmap(ac_table, annot=True, cmap='RdBu_r', center=0, ax=ax1)
        ax1.set_title(f'{self.symbol} - Autocorrelations by Venue and Lag')
        ax1.set_xlabel('Lag')
        ax1.set_ylabel('Venue')
        
        # AR(1) coefficients
        ar1_table.plot(kind='bar', ax=ax2, color='skyblue')
        ax2.set_title(f'{self.symbol} - AR(1) Coefficients by Venue')
        ax2.set_xlabel('Venue')
        ax2.set_ylabel('AR(1) Coefficient')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.plots_dir}/autocorrelations.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save tables
        ac_table.to_csv(f'{self.plots_dir}/autocorrelations.csv')
        ar1_table.to_csv(f'{self.plots_dir}/ar1_coefficients.csv')
        
        self.results['autocorrelation'] = {
            'ac_table': ac_table.to_dict(),
            'ar1_table': ar1_table.to_dict(),
            'summary': self._analyze_autocorrelations(ac_table, ar1_table)
        }
        
        print(f"  ✅ Autocorrelation test complete")
        print(f"    Plot: {self.plots_dir}/autocorrelations.png")
        print(f"    Tables: {self.plots_dir}/autocorrelations.csv, {self.plots_dir}/ar1_coefficients.csv")
    
    def _test_cross_correlation(self):
        """Test 3: Cross-Correlation of Prices/Spreads."""
        print("\n🔗 Test 3: Cross-Correlation of Prices/Spreads")
        
        if 'cross_correlations' not in self.variables:
            print("  ❌ No cross-correlation data available")
            return
        
        cc_data = self.variables['cross_correlations']
        
        # Price correlations
        if 'price_correlations' in cc_data:
            price_corrs = cc_data['price_correlations']
            self._create_correlation_heatmap(price_corrs, 'price', 'Price Correlations')
        
        # Spread correlations  
        if 'spread_correlations' in cc_data:
            spread_corrs = cc_data['spread_correlations']
            self._create_correlation_heatmap(spread_corrs, 'spread', 'Spread Correlations')
        
        self.results['cross_correlation'] = {
            'price_correlations': cc_data.get('price_correlations', {}),
            'spread_correlations': cc_data.get('spread_correlations', {}),
            'summary': self._analyze_cross_correlations(cc_data)
        }
        
        print(f"  ✅ Cross-correlation test complete")
    
    def _test_pca_analysis(self):
        """Test 4: PCA Loadings / Common Factor Analysis."""
        print("\n🎯 Test 4: PCA Loadings / Common Factor Analysis")
        
        if 'pca_analysis' not in self.variables:
            print("  ❌ No PCA data available")
            return
        
        pca_data = self.variables['pca_analysis']
        
        # Explained variance plot
        if 'explained_variance_ratio' in pca_data:
            plt.figure(figsize=(12, 6))
            
            # Explained variance
            plt.subplot(1, 2, 1)
            evr = pca_data['explained_variance_ratio']
            plt.bar(range(1, len(evr) + 1), evr)
            plt.title(f'{self.symbol} - Explained Variance by Component')
            plt.xlabel('Component')
            plt.ylabel('Explained Variance Ratio')
            plt.grid(True, alpha=0.3)
            
            # Cumulative variance
            plt.subplot(1, 2, 2)
            cvr = pca_data['cumulative_variance_ratio']
            plt.plot(range(1, len(cvr) + 1), cvr, 'o-')
            plt.title(f'{self.symbol} - Cumulative Variance Explained')
            plt.xlabel('Component')
            plt.ylabel('Cumulative Variance Ratio')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f'{self.plots_dir}/pca_variance.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # First component loadings
        if 'first_component_loadings' in pca_data:
            loadings = pca_data['first_component_loadings']
            venues = list(loadings.keys())
            values = list(loadings.values())
            
            plt.figure(figsize=(10, 6))
            plt.bar(venues, values, color='lightcoral')
            plt.title(f'{self.symbol} - First Component Loadings (Coordination Factor)')
            plt.xlabel('Venue')
            plt.ylabel('Loading')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{self.plots_dir}/pca_loadings.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # Save PCA data
        with open(f'{self.plots_dir}/pca_analysis.json', 'w') as f:
            json.dump(pca_data, f, indent=2, default=str)
        
        self.results['pca_analysis'] = {
            'data': pca_data,
            'summary': self._analyze_pca(pca_data)
        }
        
        print(f"  ✅ PCA analysis complete")
        print(f"    Plots: {self.plots_dir}/pca_variance.png, {self.plots_dir}/pca_loadings.png")
        print(f"    Data: {self.plots_dir}/pca_analysis.json")
    
    def _test_volatility_convergence(self):
        """Test 5: Rolling Volatility & Spread Convergence."""
        print("\n📊 Test 5: Rolling Volatility & Spread Convergence")
        
        if 'volatility_analysis' not in self.variables:
            print("  ❌ No volatility data available")
            return
        
        vol_data = self.variables['volatility_analysis']
        
        # Create volatility comparison table
        venues = list(vol_data.keys())
        metrics = ['mean_volatility', 'volatility_std', 'volatility_range', 
                  'mean_spread', 'spread_std', 'spread_convergence']
        
        vol_table = pd.DataFrame(index=venues, columns=metrics)
        for venue in venues:
            for metric in metrics:
                vol_table.loc[venue, metric] = vol_data[venue].get(metric, np.nan)
        
        # Generate plots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Volatility metrics
        vol_table[['mean_volatility', 'volatility_std']].plot(kind='bar', ax=axes[0,0])
        axes[0,0].set_title(f'{self.symbol} - Volatility Metrics by Venue')
        axes[0,0].set_ylabel('Volatility')
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # Spread metrics
        vol_table[['mean_spread', 'spread_std']].plot(kind='bar', ax=axes[0,1])
        axes[0,1].set_title(f'{self.symbol} - Spread Metrics by Venue')
        axes[0,1].set_ylabel('Spread')
        axes[0,1].tick_params(axis='x', rotation=45)
        
        # Volatility range
        vol_table['volatility_range'].plot(kind='bar', ax=axes[1,0], color='orange')
        axes[1,0].set_title(f'{self.symbol} - Volatility Range by Venue')
        axes[1,0].set_ylabel('Volatility Range')
        axes[1,0].tick_params(axis='x', rotation=45)
        
        # Spread convergence
        vol_table['spread_convergence'].plot(kind='bar', ax=axes[1,1], color='green')
        axes[1,1].set_title(f'{self.symbol} - Spread Convergence by Venue')
        axes[1,1].set_ylabel('Convergence Ratio')
        axes[1,1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(f'{self.plots_dir}/volatility_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save table
        vol_table.to_csv(f'{self.plots_dir}/volatility_analysis.csv')
        
        self.results['volatility_analysis'] = {
            'table': vol_table.to_dict(),
            'summary': self._analyze_volatility(vol_table)
        }
        
        print(f"  ✅ Volatility analysis complete")
        print(f"    Plot: {self.plots_dir}/volatility_analysis.png")
        print(f"    Table: {self.plots_dir}/volatility_analysis.csv")
    
    def _create_correlation_heatmap(self, correlations: Dict, corr_type: str, title: str):
        """Create correlation heatmap."""
        if not correlations:
            return
        
        # Create correlation matrix
        venues = set()
        for pair in correlations.keys():
            v1, v2 = pair.split('_')
            venues.add(v1)
            venues.add(v2)
        
        venues = sorted(list(venues))
        corr_matrix = pd.DataFrame(index=venues, columns=venues)
        
        # Fill diagonal with 1s
        for venue in venues:
            corr_matrix.loc[venue, venue] = 1.0
        
        # Fill off-diagonal with correlations
        for pair, corr in correlations.items():
            v1, v2 = pair.split('_')
            corr_matrix.loc[v1, v2] = corr
            corr_matrix.loc[v2, v1] = corr
        
        # Create heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='RdBu_r', center=0, 
                   square=True, fmt='.3f')
        plt.title(f'{self.symbol} - {title}')
        plt.tight_layout()
        plt.savefig(f'{self.plots_dir}/{corr_type}_correlations.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save correlation matrix
        corr_matrix.to_csv(f'{self.plots_dir}/{corr_type}_correlations.csv')
    
    def _analyze_variance_ratios(self, vr_table: pd.DataFrame) -> str:
        """Analyze variance ratio results."""
        summary = []
        
        for venue in vr_table.index:
            vr_2 = vr_table.loc[venue, 'vr_2']
            if pd.notna(vr_2):
                if vr_2 > 1.2:
                    summary.append(f"{venue}: Trending behavior (VR={vr_2:.3f})")
                elif vr_2 < 0.8:
                    summary.append(f"{venue}: Mean reversion (VR={vr_2:.3f})")
                else:
                    summary.append(f"{venue}: Random walk (VR={vr_2:.3f})")
        
        return "; ".join(summary)
    
    def _analyze_autocorrelations(self, ac_table: pd.DataFrame, ar1_table: pd.DataFrame) -> str:
        """Analyze autocorrelation results."""
        summary = []
        
        for venue in ac_table.index:
            ac_1 = ac_table.loc[venue, 'ac_lag_1']
            ar1 = ar1_table.loc[venue, 'ar1_coef']
            
            if pd.notna(ac_1):
                if abs(ac_1) > 0.1:
                    summary.append(f"{venue}: Persistent autocorr (AC1={ac_1:.3f})")
                else:
                    summary.append(f"{venue}: Low autocorr (AC1={ac_1:.3f})")
        
        return "; ".join(summary)
    
    def _analyze_cross_correlations(self, cc_data: Dict) -> str:
        """Analyze cross-correlation results."""
        summary = []
        
        if 'price_correlations' in cc_data:
            price_corrs = cc_data['price_correlations']
            high_corr_pairs = [pair for pair, corr in price_corrs.items() if abs(corr) > 0.8]
            if high_corr_pairs:
                summary.append(f"High price correlation: {', '.join(high_corr_pairs)}")
        
        if 'spread_correlations' in cc_data:
            spread_corrs = cc_data['spread_correlations']
            high_corr_pairs = [pair for pair, corr in spread_corrs.items() if abs(corr) > 0.8]
            if high_corr_pairs:
                summary.append(f"High spread correlation: {', '.join(high_corr_pairs)}")
        
        return "; ".join(summary) if summary else "No significant cross-correlations"
    
    def _analyze_pca(self, pca_data: Dict) -> str:
        """Analyze PCA results."""
        if 'explained_variance_ratio' in pca_data:
            evr = pca_data['explained_variance_ratio']
            first_component = evr[0] if evr else 0
            
            if first_component > 0.5:
                return f"Dominant first component ({first_component:.1%}) - possible coordination factor"
            else:
                return f"Distributed variance (first component: {first_component:.1%}) - competitive behavior"
        
        return "No PCA data available"
    
    def _analyze_volatility(self, vol_table: pd.DataFrame) -> str:
        """Analyze volatility results."""
        summary = []
        
        # Check for artificially low volatility
        mean_vol = vol_table['mean_volatility'].mean()
        low_vol_venues = vol_table[vol_table['mean_volatility'] < mean_vol * 0.5].index.tolist()
        if low_vol_venues:
            summary.append(f"Low volatility venues: {', '.join(low_vol_venues)}")
        
        # Check for spread convergence
        high_conv_venues = vol_table[vol_table['spread_convergence'] > 0.5].index.tolist()
        if high_conv_venues:
            summary.append(f"High spread convergence: {', '.join(high_conv_venues)}")
        
        return "; ".join(summary) if summary else "Normal volatility and spread patterns"
    
    def _save_results(self):
        """Save all test results."""
        results_data = {
            'symbol': self.symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'tests': self.results,
            'summary': self._generate_summary()
        }
        
        with open(f'{self.plots_dir}/wave1_results.json', 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        # Create limitations file
        self._create_limitations_file()
    
    def _generate_summary(self) -> str:
        """Generate overall summary of Wave-1 tests."""
        summary_parts = []
        
        for test_name, test_results in self.results.items():
            if 'summary' in test_results:
                summary_parts.append(f"{test_name}: {test_results['summary']}")
        
        return " | ".join(summary_parts)
    
    def _create_limitations_file(self):
        """Create LIMITATIONS.md file for Wave-1 tests."""
        limitations = f"""# Wave-1 Test Limitations - {self.symbol}

## Test-Specific Limitations

### 1. Variance Ratio Test
- **Limitation**: Sensitive to volatility clustering
- **Impact**: May flag normal market stress as coordination
- **Mitigation**: Consider market regime context

### 2. Autocorrelation & AR(1) Decay  
- **Limitation**: Confounds with microstructure noise
- **Impact**: May misattribute venue-specific effects as coordination
- **Mitigation**: Control for venue-specific factors

### 3. Cross-Correlation of Prices/Spreads
- **Limitation**: Common shocks may confound results
- **Impact**: Macro events may appear as coordination
- **Mitigation**: Include macro controls in analysis

### 4. PCA Loadings / Common Factor Analysis
- **Limitation**: Factors may reflect macro shocks, not collusion
- **Impact**: May identify common risk factors as coordination
- **Mitigation**: Interpret in context of market conditions

### 5. Rolling Volatility & Spread Convergence
- **Limitation**: Could reflect liquidity improvements, not coordination
- **Impact**: Market efficiency gains may appear as collusion
- **Mitigation**: Consider liquidity and market structure changes

## General Limitations

- **Sample Size**: Limited to recent capture data
- **Time Period**: May not capture full market cycles
- **Venue Coverage**: Results depend on venue data quality
- **Market Regime**: Tests assume normal market conditions

## Interpretation Guidelines

- **Wave-1 tests are screening tools, not conclusive evidence**
- **Results should be interpreted in context of market conditions**
- **Multiple tests showing similar patterns increase confidence**
- **Consider alternative explanations before concluding coordination**

## Next Steps

- **Wave-2**: Deeper econometric analysis with controls
- **Wave-3**: Advanced ML methods for pattern detection
- **Validation**: Cross-check with independent data sources
"""
        
        with open(f'{self.plots_dir}/LIMITATIONS.md', 'w') as f:
            f.write(limitations)

def main():
    """Main function to run Wave-1 tests for both symbols."""
    print("🚀 Wave-1 Econometric Test Execution")
    print("=" * 50)
    
    symbols = ['BTC-USD', 'ETH-USD']
    
    for symbol in symbols:
        print(f"\n📊 Processing {symbol}...")
        
        # Check if variables file exists
        variables_file = f"reports/wave1_variables_{symbol.replace('-', '_').lower()}.json"
        if not os.path.exists(variables_file):
            print(f"  ❌ Variables file not found: {variables_file}")
            continue
        
        # Initialize executor
        executor = Wave1TestExecutor(symbol, variables_file)
        
        # Run tests
        executor.run_all_tests()
        
        # Flag ETH as exploratory
        if symbol == 'ETH-USD':
            print(f"  ⚠️  ETH-USD results are EXPLORATORY ONLY (insufficient data history)")
    
    print(f"\n🎯 Wave-1 test execution complete!")
    print(f"📁 Check analysis/wave1/ directory for results")

if __name__ == "__main__":
    main()
