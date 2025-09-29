#!/usr/bin/env python3
"""
Liquidity Regime Analysis Integration Script

This script integrates the liquidity regime analysis with the existing ACD data pipeline.
It fetches liquidity data, computes consensus leadership metrics, and runs liquidity
regime analysis.

Usage:
    python scripts/run_liquidity_regime_analysis.py [--start-date 2025-01-01] [--end-date 2025-09-24] [--export-dir exports]
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

from acd.analytics.liquidity_regimes import LiquidityRegimeAnalyzer, create_liquidity_regime_analyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiquidityRegimeIntegration:
    """
    Integration class that connects liquidity regime analysis with existing ACD pipeline.
    """
    
    def __init__(self):
        self.analyzer = create_liquidity_regime_analyzer()
        self.venues = ['binance', 'okx', 'coinbase', 'kraken', 'bybit']
        
    def fetch_liquidity_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch liquidity data for analysis.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with liquidity metrics
        """
        logger.info(f"Fetching liquidity data from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        dates = pd.date_range(start_dt, end_dt, freq='D')
        
        # Generate synthetic liquidity data
        np.random.seed(42)
        liquidity_data = []
        
        for date in dates:
            for venue in self.venues:
                # Generate realistic liquidity metrics
                base_volume = np.random.lognormal(15, 1)  # Volume in USD
                true_range = np.random.lognormal(-8, 0.5)  # True range as fraction of price
                close_price = 45000 + np.random.normal(0, 1000)  # BTC price
                daily_return = np.random.normal(0, 0.02)  # Daily return
                sigma20 = np.random.uniform(0.1, 0.5)  # 20-day volatility
                
                liquidity_data.append({
                    'dayUTC': date,
                    'venue': venue,
                    'volumeUSD': base_volume,
                    'trueRange': true_range,
                    'close': close_price,
                    'return': daily_return,
                    'sigma20': sigma20
                })
        
        df = pd.DataFrame(liquidity_data)
        logger.info(f"Generated synthetic liquidity data: {len(df)} records")
        return df
    
    def fetch_leadership_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch leadership data for consensus analysis.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with leadership data
        """
        logger.info(f"Fetching leadership data from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        dates = pd.date_range(start_dt, end_dt, freq='D')
        
        # Generate synthetic leadership data with venue prices
        np.random.seed(42)
        leadership_data = []
        
        for date in dates:
            # Generate base price with some trend
            base_price = 45000 + (date - start_dt).days * 10 + np.random.normal(0, 500)
            
            row = {'dayKey': date.strftime('%Y-%m-%d')}
            
            # Add venue-specific prices with small variations
            for venue in self.venues:
                venue_variation = np.random.normal(0, 0.001)  # 0.1% variation
                row[venue] = base_price * (1 + venue_variation)
            
            leadership_data.append(row)
        
        df = pd.DataFrame(leadership_data)
        df.set_index('dayKey', inplace=True)
        logger.info(f"Generated {len(df)} leadership records")
        return df
    
    def run_analysis(self, start_date: str, end_date: str, export_dir: str = "exports") -> Dict[str, Any]:
        """
        Run complete liquidity regime analysis.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            export_dir: Directory for exported files
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting liquidity regime analysis")
        
        # Step 1: Fetch liquidity data
        liquidity_data = self.fetch_liquidity_data(start_date, end_date)
        
        # Step 2: Fetch leadership data
        leadership_data = self.fetch_leadership_data(start_date, end_date)
        
        # Step 3: Run liquidity regime analysis
        results = self.analyzer.analyze_liquidity_regimes(liquidity_data, leadership_data)
        
        # Step 4: Export results
        self.analyzer._export_results(results, export_dir)
        
        # Step 5: Create summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "start_date": start_date,
                "end_date": end_date,
                "venues": self.venues,
                "spec_version": self.analyzer.spec_version
            },
            "results": {
                "total_days": len(results.regime_assignments),
                "regime_counts": results.regime_assignments["regime"].value_counts().to_dict(),
                "leadership_regimes": len(results.leadership_by_regime)
            },
            "export_files": [
                "liquidity_terciles_summary.json",
                "leadership_by_liquidity.json", 
                "leadership_by_day_liquidity.csv",
                "liquidity_assignments.json",
                "MANIFEST.json"
            ]
        }
        
        return summary
    
    def save_results(self, results: Dict[str, Any], output_file: str) -> None:
        """Save analysis results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main function to run liquidity regime analysis."""
    parser = argparse.ArgumentParser(description="Run liquidity regime analysis")
    parser.add_argument("--start-date", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-09-24", help="End date (YYYY-MM-DD)")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create integration instance
    integration = LiquidityRegimeIntegration()
    
    try:
        # Run analysis
        results = integration.run_analysis(
            start_date=args.start_date,
            end_date=args.end_date,
            export_dir=args.export_dir
        )
        
        # Save results
        integration.save_results(results, "liquidity_regime_results.json")
        
        # Print summary
        print("\n" + "="*80)
        print("LIQUIDITY REGIME ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start_date} to {args.end_date}")
        print(f"Total days analyzed: {results['results']['total_days']}")
        print(f"Liquidity regimes: {results['results']['leadership_regimes']}")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("\nRegime Distribution:")
        for regime, count in results['results']['regime_counts'].items():
            pct = (count / results['results']['total_days']) * 100
            print(f"  {regime.upper()}: {count} days ({pct:.1f}%)")
        
        print("\n" + "="*80)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
