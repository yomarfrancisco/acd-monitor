#!/usr/bin/env python3
"""
Materialize YTD Minute Data Script

This script materializes minute-level data for the YTD period to ensure
sufficient coverage for information share analysis.
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.data.adapters import MinuteBarsAdapter
from acd.data.cache import DataCache
from _analysis_utils import inclusive_end_date, ensure_time_mid_volume, resample_minute


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def materialize_minute_data(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    cache_dir: str = "data/cache",
    min_coverage: float = 0.95
) -> Dict[str, Any]:
    """
    Materialize minute data for all venues.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        cache_dir: Cache directory
        min_coverage: Minimum coverage required
        
    Returns:
        Materialization results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Materializing minute data for {pair} across {len(venues)} venues")
    
    # Parse dates with inclusive end
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = inclusive_end_date(end_date)  # 23:59:59 inclusive
    
    # Create adapters and cache
    adapter = MinuteBarsAdapter()
    cache = DataCache(cache_dir)
    
    results = {
        'venues': {},
        'total_days': (end_utc - start_utc).days + 1,
        'successful_venues': 0,
        'failed_venues': 0
    }
    
    for venue in venues:
        try:
            logger.info(f"Materializing data for {venue}")
            
            # Get data from adapter
            df = adapter.get(pair, venue, start_utc, end_utc)
            
            if df.empty:
                logger.warning(f"No data for {venue}")
                results['venues'][venue] = {
                    'success': False,
                    'reason': 'no_data',
                    'bars': 0,
                    'coverage_pct': 0
                }
                results['failed_venues'] += 1
                continue
            
            # Calculate coverage
            expected_minutes = (end_utc - start_utc).total_seconds() / 60
            actual_bars = len(df)
            coverage_pct = (actual_bars / expected_minutes) * 100 if expected_minutes > 0 else 0
            
            # Check coverage requirement
            if coverage_pct < min_coverage * 100:
                logger.warning(f"Insufficient coverage for {venue}: {coverage_pct:.2f}% < {min_coverage*100}%")
                results['venues'][venue] = {
                    'success': False,
                    'reason': 'insufficient_coverage',
                    'bars': actual_bars,
                    'coverage_pct': coverage_pct
                }
                results['failed_venues'] += 1
                continue
            
            # Write to cache
            cache.put(venue, pair, "1m", df)
            
            # Log materialization
            materialize_log = {
                "venue": venue,
                "start": start_date,
                "end": end_date,
                "bars": actual_bars,
                "coveragePct": round(coverage_pct, 2)
            }
            print(f"[DATA:minute:materialize] {json.dumps(materialize_log, ensure_ascii=False)}")
            
            results['venues'][venue] = {
                'success': True,
                'bars': actual_bars,
                'coverage_pct': coverage_pct,
                'cache_path': cache.get_cache_path(venue, pair, "1m")
            }
            results['successful_venues'] += 1
            
            logger.info(f"Successfully materialized {actual_bars} bars for {venue} ({coverage_pct:.2f}% coverage)")
            
        except Exception as e:
            logger.error(f"Error materializing data for {venue}: {str(e)}")
            results['venues'][venue] = {
                'success': False,
                'reason': 'error',
                'error': str(e),
                'bars': 0,
                'coverage_pct': 0
            }
            results['failed_venues'] += 1
    
    logger.info(f"Materialization complete: {results['successful_venues']} successful, {results['failed_venues']} failed")
    
    return results


def main():
    """Main function to materialize minute data."""
    parser = argparse.ArgumentParser(description="Materialize YTD minute data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--min-coverage", type=float, default=0.95, help="Minimum coverage required")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Materialize data
        results = materialize_minute_data(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            cache_dir=args.cache_dir,
            min_coverage=args.min_coverage
        )
        
        # Print summary
        print("\n" + "="*80)
        print("MINUTE DATA MATERIALIZATION SUMMARY")
        print("="*80)
        print(f"Period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Successful venues: {results['successful_venues']}")
        print(f"Failed venues: {results['failed_venues']}")
        print(f"Total days: {results['total_days']}")
        
        for venue, result in results['venues'].items():
            if result['success']:
                print(f"  {venue}: {result['bars']} bars ({result['coverage_pct']:.2f}% coverage)")
            else:
                print(f"  {venue}: FAILED - {result['reason']}")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import json
    main()
