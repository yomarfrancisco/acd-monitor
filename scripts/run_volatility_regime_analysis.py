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
        
        This creates synthetic data that mimics real OHLCV structure with
        venue-specific price data for consensus leadership computation.
        
        Args:
            days: Number of days of data to fetch
            
        Returns:
            DataFrame with OHLCV data including venue prices
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
        
        # Create OHLCV data with venue-specific prices
        ohlcv_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
            'close': prices,
            'volume': np.random.uniform(1000, 10000, len(dates))
        })
        
        # Add venue-specific price data for consensus leadership computation
        for venue in self.venues:
            # Each venue has slightly different prices with realistic spreads
            venue_spread = np.random.normal(0, 0.0005, len(dates))  # 0.05% spread
            ohlcv_data[venue] = prices * (1 + venue_spread)
        
        # Set timestamp as index
        ohlcv_data.set_index('timestamp', inplace=True)
        
        logger.info(f"Generated synthetic OHLCV data: {len(ohlcv_data)} days")
        return ohlcv_data
    
    def fetch_ohlcv_data_by_date(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch OHLCV data for specific date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with OHLCV data including venue prices
        """
        logger.info(f"Fetching OHLCV data from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        dates = pd.date_range(start_dt, end_dt, freq='D')
        
        # Create synthetic BTC-USD price data with realistic characteristics
        np.random.seed(42)
        base_price = 45000  # Starting BTC price
        
        # Generate price series with realistic volatility patterns
        returns = np.random.normal(0, 0.025, len(dates))  # 2.5% daily volatility
        # Add some regime changes
        mid_point = len(dates) // 2
        returns[:mid_point] *= 1.5  # Higher volatility period
        returns[mid_point:] *= 0.7  # Lower volatility period
        
        prices = [base_price]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data with venue-specific prices
        ohlcv_data = pd.DataFrame(index=dates)
        
        # Add a 'close' column (required by volatility analyzer)
        ohlcv_data['close'] = prices[1:]
        
        for venue in self.venues:
            # Add small venue-specific price variations (±0.1%)
            venue_variation = np.random.normal(0, 0.001, len(dates))
            venue_prices = [p * (1 + v) for p, v in zip(prices[1:], venue_variation)]
            
            ohlcv_data[venue] = venue_prices
        
        logger.info(f"Generated synthetic OHLCV data: {len(ohlcv_data)} days")
        return ohlcv_data
    
    def compute_consensus_leadership(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute consensus leadership metrics from OHLCV data.
        
        This is now a placeholder since leadership will be computed directly
        from venue prices in the volatility regime analyzer.
        
        Args:
            ohlcv_data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with leadership metrics for each venue (placeholder)
        """
        logger.info("Leadership will be computed from venue prices in the analyzer")
        
        # Return empty DataFrame - leadership will be computed in the analyzer
        return pd.DataFrame(index=ohlcv_data.index)
    
    def run_analysis(self, days: int = 90, start_date: str = None, end_date: str = None, export_dir: str = "exports") -> Dict[str, Any]:
        """
        Run complete volatility regime analysis with structured logging.
        
        Args:
            days: Number of days of data to analyze (used if start/end not provided)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            export_dir: Directory for exported files
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting volatility regime analysis with structured logging")
        
        # Step 1: Fetch OHLCV data
        if start_date and end_date:
            logger.info(f"Fetching data from {start_date} to {end_date}")
            ohlcv_data = self.fetch_ohlcv_data_by_date(start_date, end_date)
        else:
            logger.info(f"Fetching {days} days of OHLCV data")
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
    parser.add_argument('--start', type=str, default=None,
                       help='Start date in YYYY-MM-DD format (overrides --days)')
    parser.add_argument('--end', type=str, default=None,
                       help='End date in YYYY-MM-DD format (overrides --days)')
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
        results = integration.run_analysis(
            days=args.days, 
            start_date=args.start, 
            end_date=args.end, 
            export_dir=args.export_dir
        )
        
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
