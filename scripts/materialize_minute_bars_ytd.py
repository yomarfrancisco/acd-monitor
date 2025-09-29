#!/usr/bin/env python3
"""
Materialize YTD Minute Bars with Cointegrated Synthetic Data

This script generates cointegrated synthetic minute data for information share analysis.
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.data.adapters.synthetic_info_share import create_cointegrated_generator
from acd.data.cache import DataCache


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def materialize_cointegrated_data(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    source: str = "synthetic_info_share_v1",
    mode: str = "vecm_cointegrated_v2",
    leader_bias: str = '{"binance":0.5,"coinbase":0.25,"kraken":0.15,"okx":0.05,"bybit":0.05}',
    cache_dir: str = "data/cache",
    start_price: float = 50000.0
) -> None:
    """
    Materialize cointegrated synthetic minute data.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        source: Data source identifier
        cache_dir: Cache directory
        start_price: Starting price for BTC-USD
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Materializing cointegrated synthetic data for {pair}")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Parse leader bias
    import json
    try:
        leader_bias_dict = json.loads(leader_bias)
    except json.JSONDecodeError:
        logger.warning(f"Invalid leader bias JSON: {leader_bias}, using default")
        leader_bias_dict = {"binance": 0.5, "coinbase": 0.25, "kraken": 0.15, "okx": 0.05, "bybit": 0.05}
    
    # Create generator and cache
    from acd.data.adapters.synthetic_info_share import CointegratedSyntheticGenerator
    generator = CointegratedSyntheticGenerator(seed=42, mode=mode)
    
    # Update leader bias if provided
    if hasattr(generator, 'leader_bias'):
        generator.leader_bias = leader_bias_dict
    
    cache = DataCache(cache_dir)
    
    # Generate cointegrated data for all venues
    venue_data = generator.generate_cointegrated_data(
        venues=venues,
        start_price=start_price,
        start_time=start_utc,
        end_time=end_utc
    )
    
    # Cache data for each venue
    for venue, df in venue_data.items():
        # Write to cache
        cache.put(venue, pair, "1m", df)
        
        # Calculate coverage
        expected_minutes = (end_utc - start_utc).total_seconds() / 60
        actual_bars = len(df)
        coverage_pct = (actual_bars / expected_minutes) * 100 if expected_minutes > 0 else 0
        
        # Log materialization
        materialize_log = {
            "venue": venue,
            "start": start_date,
            "end": end_date,
            "bars": actual_bars,
            "coveragePct": round(coverage_pct, 2),
            "source": source
        }
        print(f"[DATA:minute:materialize] {json.dumps(materialize_log, ensure_ascii=False)}")
        
        logger.info(f"Cached {actual_bars} bars for {venue} ({coverage_pct:.2f}% coverage)")
    
    logger.info(f"Successfully materialized cointegrated data for {len(venues)} venues")


def main():
    """Main function to materialize cointegrated minute data."""
    parser = argparse.ArgumentParser(description="Materialize cointegrated synthetic minute data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--source", default="synthetic_info_share_v1", help="Data source identifier")
    parser.add_argument("--mode", default="vecm_cointegrated_v2", help="Generator mode")
    parser.add_argument("--leader-bias", default='{"binance":0.5,"coinbase":0.25,"kraken":0.15,"okx":0.05,"bybit":0.05}', help="Leader bias JSON")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--start-price", type=float, default=50000.0, help="Starting price")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Materialize data
        materialize_cointegrated_data(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            source=args.source,
            mode=args.mode,
            leader_bias=args.leader_bias,
            cache_dir=args.cache_dir,
            start_price=args.start_price
        )
        
        print("\n" + "="*80)
        print("COINTEGRATED SYNTHETIC DATA MATERIALIZATION COMPLETE")
        print("="*80)
        print(f"Period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Source: {args.source}")
        print(f"Starting price: ${args.start_price:,.2f}")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import json
    main()
