#!/usr/bin/env python3
"""
Simple Markov Analysis - Avoid Alignment Issues

Use a simpler approach to avoid array length mismatches.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class SimpleMarkovAnalyzer:
    """Simple Markov analysis avoiding alignment issues."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.output_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}/markov"
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        
    def run_simple_analysis(self):
        """Run simple Markov analysis."""
        print(f"🔄 Simple Markov Analysis for {self.symbol}")
        print("=" * 50)
        
        # Load panel data
        panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        if not os.path.exists(panel_file):
            print("❌ Panel file not found")
            return
        
        panel_data = pd.read_parquet(panel_file)
        print(f"📊 Loaded panel: {len(panel_data)} observations")
        
        # Analyze spread regimes
        self._analyze_spread_regimes(panel_data)
        
        # Analyze price regimes
        self._analyze_price_regimes(panel_data)
        
        # Create limitations
        self._create_limitations()
        
        print(f"✅ Simple Markov analysis completed")
        print(f"📁 Results saved to {self.output_dir}")
    
    def _analyze_spread_regimes(self, panel_data: pd.DataFrame):
        """Analyze spread-based regimes."""
        print("\n📊 Analyzing Spread Regimes...")
        
        # Get spread columns
        spread_columns = [f"{venue}_spread" for venue in self.venues if f"{venue}_spread" in panel_data.columns]
        
        if len(spread_columns) < 2:
            print("  ❌ Insufficient spread data")
            return
        
        # Calculate median spread
        spreads_df = panel_data[spread_columns].dropna()
        spread_median = spreads_df.median(axis=1)
        
        # Simple regime identification based on quantiles
        q33 = spread_median.quantile(0.33)
        q67 = spread_median.quantile(0.67)
        
        # Assign regimes
        regimes = pd.Series(index=spread_median.index, dtype=int)
        regimes[spread_median <= q33] = 0  # Low spread regime
        regimes[(spread_median > q33) & (spread_median <= q67)] = 1  # Medium spread regime
        regimes[spread_median > q67] = 2  # High spread regime
        
        # Calculate regime statistics
        regime_counts = regimes.value_counts()
        regime_0_count = regime_counts.get(0, 0)
        regime_1_count = regime_counts.get(1, 0)
        regime_2_count = regime_counts.get(2, 0)
        
        total_obs = len(regimes)
        regime_0_prob = regime_0_count / total_obs
        regime_1_prob = regime_1_count / total_obs
        regime_2_prob = regime_2_count / total_obs
        
        # Calculate regime persistence
        regime_changes = (regimes.diff() != 0).sum()
        persistence = 1 - (regime_changes / total_obs)
        
        # Save results
        results = {
            'regime_0_count': regime_0_count,
            'regime_1_count': regime_1_count,
            'regime_2_count': regime_2_count,
            'regime_0_prob': regime_0_prob,
            'regime_1_prob': regime_1_prob,
            'regime_2_prob': regime_2_prob,
            'persistence': persistence,
            'regime_changes': regime_changes
        }
        
        # Save regime data
        regime_df = pd.DataFrame({
            'timestamp': spread_median.index,
            'spread_median': spread_median.values,
            'regime': regimes.values
        })
        regime_df.to_csv(f"{self.output_dir}/spread_regime_analysis.csv", index=False)
        
        # Save results
        pd.DataFrame([results]).to_csv(f"{self.output_dir}/spread_regime_results.csv", index=False)
        
        # Create plots
        self._plot_regime_analysis(spread_median, regimes, "spread")
        
        print(f"  ✅ Spread regime analysis completed")
        print(f"    Regime 0 (Low): {regime_0_prob:.3f} prob, {regime_0_count} obs")
        print(f"    Regime 1 (Medium): {regime_1_prob:.3f} prob, {regime_1_count} obs")
        print(f"    Regime 2 (High): {regime_2_prob:.3f} prob, {regime_2_count} obs")
        print(f"    Persistence: {persistence:.3f}")
    
    def _analyze_price_regimes(self, panel_data: pd.DataFrame):
        """Analyze price-based regimes."""
        print("\n📊 Analyzing Price Regimes...")
        
        # Get mid price columns
        mid_columns = [f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in panel_data.columns]
        
        if len(mid_columns) < 2:
            print("  ❌ Insufficient mid price data")
            return
        
        # Calculate median mid price
        mid_prices_df = panel_data[mid_columns].dropna()
        mid_median = mid_prices_df.median(axis=1)
        
        # Calculate price changes
        price_changes = mid_median.pct_change().dropna()
        
        # Simple regime identification based on volatility
        rolling_std = price_changes.rolling(window=60, min_periods=30).std()
        
        # Assign regimes based on volatility
        q33 = rolling_std.quantile(0.33)
        q67 = rolling_std.quantile(0.67)
        
        regimes = pd.Series(index=price_changes.index, dtype=int)
        regimes[rolling_std <= q33] = 0  # Low volatility regime
        regimes[(rolling_std > q33) & (rolling_std <= q67)] = 1  # Medium volatility regime
        regimes[rolling_std > q67] = 2  # High volatility regime
        
        # Calculate regime statistics
        regime_counts = regimes.value_counts()
        regime_0_count = regime_counts.get(0, 0)
        regime_1_count = regime_counts.get(1, 0)
        regime_2_count = regime_counts.get(2, 0)
        
        total_obs = len(regimes)
        regime_0_prob = regime_0_count / total_obs
        regime_1_prob = regime_1_count / total_obs
        regime_2_prob = regime_2_count / total_obs
        
        # Calculate regime persistence
        regime_changes = (regimes.diff() != 0).sum()
        persistence = 1 - (regime_changes / total_obs)
        
        # Save results
        results = {
            'regime_0_count': regime_0_count,
            'regime_1_count': regime_1_count,
            'regime_2_count': regime_2_count,
            'regime_0_prob': regime_0_prob,
            'regime_1_prob': regime_1_prob,
            'regime_2_prob': regime_2_prob,
            'persistence': persistence,
            'regime_changes': regime_changes
        }
        
        # Save regime data
        regime_df = pd.DataFrame({
            'timestamp': price_changes.index,
            'price_changes': price_changes.values,
            'rolling_std': rolling_std.values,
            'regime': regimes.values
        })
        regime_df.to_csv(f"{self.output_dir}/price_regime_analysis.csv", index=False)
        
        # Save results
        pd.DataFrame([results]).to_csv(f"{self.output_dir}/price_regime_results.csv", index=False)
        
        # Create plots
        self._plot_regime_analysis(price_changes, regimes, "price")
        
        print(f"  ✅ Price regime analysis completed")
        print(f"    Regime 0 (Low Vol): {regime_0_prob:.3f} prob, {regime_0_count} obs")
        print(f"    Regime 1 (Medium Vol): {regime_1_prob:.3f} prob, {regime_1_count} obs")
        print(f"    Regime 2 (High Vol): {regime_2_prob:.3f} prob, {regime_2_count} obs")
        print(f"    Persistence: {persistence:.3f}")
    
    def _plot_regime_analysis(self, series: pd.Series, regimes: pd.Series, name: str):
        """Create regime analysis plots."""
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot 1: Time series with regime coloring
        ax1 = axes[0]
        colors = ['blue', 'green', 'red']
        for regime in [0, 1, 2]:
            mask = regimes == regime
            if mask.any():
                ax1.scatter(series.index[mask], series.values[mask], 
                           c=colors[regime], alpha=0.6, label=f'Regime {regime}', s=1)
        ax1.set_title(f'Regime Analysis - {name.title()}')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Value')
        ax1.legend()
        
        # Plot 2: Regime sequence
        ax2 = axes[1]
        ax2.plot(regimes.index, regimes.values, 'o-', markersize=2)
        ax2.set_title('Regime Sequence')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Regime')
        ax2.set_yticks([0, 1, 2])
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{name}_regime_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_limitations(self):
        """Create limitations document."""
        limitations = """# Simple Markov Analysis - Limitations

## Analysis Limitations
- **Simple Regime Identification**: Based on quantiles rather than statistical models
- **No Transition Probabilities**: No formal Markov chain analysis
- **No Model Fitting**: No likelihood-based regime identification
- **Fixed Window**: 60-second rolling window for volatility calculation

## Data Limitations
- **Sample Size**: 2.5 hours of data may limit regime identification
- **Alignment Issues**: Avoided complex alignment to prevent array length mismatches
- **Single Observable**: Analysis limited to spread median and price changes

## Interpretation Limitations
- **Regime Identification**: Regimes based on simple quantiles, not economic states
- **Persistence**: Simple persistence calculation, not formal transition analysis
- **No Exogenous Variables**: Model does not include session or event indicators

## Recommendations
- Implement proper Markov switching models with better data alignment
- Include exogenous variables (sessions, events)
- Test alternative regime specifications
- Validate with out-of-sample data
- Use longer time series for robust analysis

---
*Generated by Simple Markov Analysis*  
*Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
        
        with open(f"{self.output_dir}/LIMITATIONS.md", 'w') as f:
            f.write(limitations)

def main():
    """Main function."""
    symbol = 'BTC-USD'
    
    # Initialize analyzer
    analyzer = SimpleMarkovAnalyzer(symbol)
    
    # Run simple analysis
    analyzer.run_simple_analysis()

if __name__ == "__main__":
    main()
