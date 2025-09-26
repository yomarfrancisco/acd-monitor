#!/usr/bin/env python3
"""
Volatility Regime Analysis Integration Script

This script integrates the volatility regime analysis with the existing ACD data pipeline.
It fetches live OHLCV data, computes consensus leadership metrics, and runs volatility
regime analysis as specified in ACD_Working_Plan.md Step 1.

Usage:
    python scripts/run_volatility_regime_analysis.py [--days 90] [--output results.json]
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.analytics.volatility_regimes import VolatilityRegimeAnalyzer, create_volatility_regime_analyzer
from acd.data.features import FeatureEngineering

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VolatilityRegimeIntegration:
    """
    Integration class that connects volatility regime analysis with existing ACD pipeline.
    """
    
    def __init__(self):
        self.analyzer = create_volatility_regime_analyzer(window=20)
        self.feature_engineer = FeatureEngineering()
        self.venues = ['binance', 'okx', 'coinbase', 'kraken', 'bybit']
        
    def fetch_ohlcv_data(self, days: int = 90) -> pd.DataFrame:
        """
        Fetch OHLCV data from existing data sources.
        
        This is a placeholder that should be replaced with actual data fetching
        from the existing ACD data pipeline.
        
        Args:
            days: Number of days of data to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {days} days of OHLCV data")
        
        # For now, create synthetic data that mimics real OHLCV structure
        # In production, this would fetch from the actual data pipeline
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start_date, end_date, freq='D')
        
        # Create synthetic BTC-USD price data with realistic characteristics
        np.random.seed(42)
        base_price = 45000  # Starting BTC price
        
        # Generate price series with realistic volatility patterns
        returns = np.random.normal(0, 0.025, len(dates))  # 2.5% daily volatility
        # Add some regime changes
        returns[30:60] *= 2  # Higher volatility period
        returns[70:90] *= 0.5  # Lower volatility period
        
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Create OHLCV data
        ohlcv_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
            'close': prices,
            'volume': np.random.uniform(1000, 10000, len(dates))
        })
        
        # Set timestamp as index
        ohlcv_data.set_index('timestamp', inplace=True)
        
        logger.info(f"Generated synthetic OHLCV data: {len(ohlcv_data)} days")
        return ohlcv_data
    
    def compute_consensus_leadership(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute consensus leadership metrics from OHLCV data.
        
        This simulates the consensus proximity calculation that would be done
        in the actual ACD pipeline.
        
        Args:
            ohlcv_data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with leadership metrics for each venue
        """
        logger.info("Computing consensus leadership metrics")
        
        # Create synthetic leadership data based on price movements
        # In production, this would use the actual consensus proximity algorithm
        leadership_data = pd.DataFrame(index=ohlcv_data.index)
        
        # Generate leadership scores that vary with volatility
        base_volatility = ohlcv_data['close'].pct_change().rolling(20).std()
        
        for i, venue in enumerate(self.venues):
            # Create venue-specific leadership patterns
            # Binance tends to lead in high volatility
            # Coinbase leads in low volatility
            # Others have mixed patterns
            
            if venue == 'binance':
                leadership_scores = 0.3 + 0.4 * (base_volatility / base_volatility.mean())
            elif venue == 'coinbase':
                leadership_scores = 0.4 - 0.2 * (base_volatility / base_volatility.mean())
            else:
                leadership_scores = 0.2 + 0.1 * np.random.normal(0, 1, len(ohlcv_data))
            
            # Add some noise and ensure values are between 0 and 1
            leadership_scores += np.random.normal(0, 0.05, len(ohlcv_data))
            leadership_scores = np.clip(leadership_scores, 0, 1)
            
            leadership_data[venue] = leadership_scores
        
        # Normalize so that the highest score each day is 1
        max_scores = leadership_data.max(axis=1)
        for venue in self.venues:
            leadership_data[venue] = leadership_data[venue] / max_scores
        
        logger.info("Computed consensus leadership metrics")
        return leadership_data
    
    def run_analysis(self, days: int = 90, export_dir: str = "exports") -> Dict[str, Any]:
        """
        Run complete volatility regime analysis with structured logging.
        
        Args:
            days: Number of days of data to analyze
            export_dir: Directory for exported files
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting volatility regime analysis with structured logging")
        
        # Step 1: Fetch OHLCV data
        ohlcv_data = self.fetch_ohlcv_data(days)
        
        # Step 2: Compute consensus leadership
        leadership_data = self.compute_consensus_leadership(ohlcv_data)
        
        # Step 3: Run volatility regime analysis with structured logging
        results = self.analyzer.analyze_volatility_regimes(
            ohlcv_data=ohlcv_data,
            leadership_data=leadership_data,
            venue_columns=self.venues,
            price_column='close',
            export_results=True,
            output_dir=export_dir
        )
        
        # Step 4: Convert results to serializable format
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'volatility_regime_analysis',
            'parameters': {
                'window': 20,
                'days_analyzed': days,
                'venues': self.venues,
                'spec_version': '1.0.0',
                'pair': 'BTC-USD'
            },
            'regimes': [
                {
                    'regime': r.regime,
                    'lower_bound': r.lower_bound,
                    'upper_bound': r.upper_bound,
                    'count': r.count,
                    'percentage': r.percentage
                }
                for r in results.regimes
            ],
            'leadership_by_regime': [
                {
                    'regime': l.regime,
                    'venue_leadership': l.venue_leadership,
                    'total_days': l.total_days,
                    'venue_rankings': l.venue_rankings
                }
                for l in results.leadership_by_regime
            ],
            'summary': results.summary,
            'volatility_stats': {
                'mean': float(results.volatility_series.mean()),
                'std': float(results.volatility_series.std()),
                'min': float(results.volatility_series.min()),
                'max': float(results.volatility_series.max())
            },
            'export_files': [
                f"{export_dir}/vol_terciles_summary.json",
                f"{export_dir}/leadership_by_regime.json",
                f"{export_dir}/leadership_by_day.csv"
            ]
        }
        
        logger.info("Volatility regime analysis completed with structured logging")
        logger.info(f"Export files created in {export_dir}/")
        return analysis_results
    
    def save_results(self, results: Dict[str, Any], output_file: str) -> None:
        """
        Save analysis results to file.
        
        Args:
            results: Analysis results dictionary
            output_file: Output file path
        """
        logger.info(f"Saving results to {output_file}")
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """Main function to run volatility regime analysis with structured logging."""
    parser = argparse.ArgumentParser(description='Run volatility regime analysis with structured logging')
    parser.add_argument('--days', type=int, default=90, 
                       help='Number of days of data to analyze (default: 90)')
    parser.add_argument('--output', type=str, default='volatility_regime_results.json',
                       help='Output file path (default: volatility_regime_results.json)')
    parser.add_argument('--export-dir', type=str, default='exports',
                       help='Export directory for structured files (default: exports)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create integration instance
    integration = VolatilityRegimeIntegration()
    
    try:
        # Run analysis with structured logging
        results = integration.run_analysis(days=args.days, export_dir=args.export_dir)
        
        # Save results
        integration.save_results(results, args.output)
        
        # Print summary
        print("\n" + "="*80)
        print("VOLATILITY REGIME ANALYSIS WITH STRUCTURED LOGGING")
        print("="*80)
        print(f"Analysis completed: {results['timestamp']}")
        print(f"Days analyzed: {results['parameters']['days_analyzed']}")
        print(f"Venues: {', '.join(results['parameters']['venues'])}")
        print(f"Spec version: {results['parameters']['spec_version']}")
        print(f"Pair: {results['parameters']['pair']}")
        print(f"Results saved to: {args.output}")
        
        print(f"\nExport files created in {args.export_dir}/:")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("\nRegime Distribution:")
        for regime in results['regimes']:
            print(f"  {regime['regime'].upper()}: {regime['count']} days ({regime['percentage']:.1f}%)")
        
        print("\nLeadership by Regime:")
        for leadership in results['leadership_by_regime']:
            print(f"  {leadership['regime'].upper()} VOLATILITY:")
            for venue, percentage in leadership['venue_leadership'].items():
                print(f"    {venue}: {percentage:.1f}%")
        
        print("\nStructured Logging Tags Used:")
        print("  [ENV:volatility:config] - Configuration and metadata")
        print("  [ENV:volatility:terciles] - Tercile thresholds and bounds")
        print("  [ENV:volatility:assignments] - Regime assignments summary")
        print("  [LEADER:env:volatility:summary] - Leadership shares by regime")
        print("  [LEADER:env:volatility:table] - Full ranking table")
        print("  [LEADER:env:volatility:dropped] - Dropped day accounting")
        print("  [LEADER:env:volatility:ties] - Tie day statistics")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
