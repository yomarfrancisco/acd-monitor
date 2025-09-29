#!/usr/bin/env python3
"""
Run funding regime analysis for BTC perpetuals.

This script fetches funding rate data, computes regime analysis,
and generates structured logs and exports.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.analytics.funding_regimes import create_funding_regime_analyzer
from acd.data.synthetic_crypto import generate_synthetic_funding_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_funding_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch funding rate data for BTC perpetuals."""
    logger.info(f"Fetching funding data from {start_date} to {end_date}")
    
    # For now, generate synthetic data
    # In production, this would fetch from exchanges
    funding_data = generate_synthetic_funding_data(
        start_date=start_date,
        end_date=end_date,
        venues=["binance", "coinbase", "kraken", "bybit", "okx"]
    )
    
    logger.info(f"Fetched {len(funding_data)} funding rate records")
    return funding_data


def fetch_leadership_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch leadership data for cross-analysis."""
    logger.info(f"Fetching leadership data from {start_date} to {end_date}")
    
    # For now, generate synthetic leadership data
    # In production, this would fetch from the consensus proximity analysis
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    leadership_data = []
    
    for date in date_range:
        # Simulate leadership distribution
        leaders = ["binance", "coinbase", "kraken", "bybit", "okx"]
        leader = leaders[hash(str(date)) % len(leaders)]
        
        leadership_data.append({
            "date": date,
            "leader": leader,
            "consensus_price": 50000 + (hash(str(date)) % 10000)
        })
    
    df = pd.DataFrame(leadership_data)
    df.set_index("date", inplace=True)
    
    logger.info(f"Generated {len(df)} leadership records")
    return df


def run_analysis(start_date: str, end_date: str, export_dir: str = "exports") -> None:
    """Run the complete funding regime analysis."""
    logger.info("Starting funding regime analysis")
    
    # Fetch data
    funding_data = fetch_funding_data(start_date, end_date)
    leadership_data = fetch_leadership_data(start_date, end_date)
    
    # Create analyzer
    analyzer = create_funding_regime_analyzer(pair="BTC-USD")
    
    # Run analysis
    results = analyzer.analyze_funding_regimes(funding_data, leadership_data)
    
    # Export results
    analyzer._export_results(results, export_dir)
    
    logger.info("Funding regime analysis completed")
    
    # Print summary
    print("\n=== FUNDING REGIME ANALYSIS SUMMARY ===")
    print(f"Analysis period: {start_date} to {end_date}")
    print(f"Total days analyzed: {len(results.regime_assignments)}")
    print(f"Funding terciles: {results.funding_terciles}")
    print(f"Leadership regimes: {len(results.leadership_by_regime)}")
    print(f"Export files created in: {export_dir}/")
    print("  - funding_terciles_summary.json")
    print("  - leadership_by_funding.json") 
    print("  - leadership_by_day_funding.csv")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run funding regime analysis")
    parser.add_argument("--start-date", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-09-24", help="End date (YYYY-MM-DD)")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        run_analysis(args.start_date, args.end_date, args.export_dir)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
