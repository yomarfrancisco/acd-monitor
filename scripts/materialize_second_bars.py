#!/usr/bin/env python3
"""
Materialize second bars for specified venues and date range.

Usage:
    python scripts/materialize_second_bars.py \
        --start 2025-01-01 --end 2025-09-24 \
        --pair BTC-USD --venues binance,coinbase,kraken,bybit,okx \
        --synthetic yes --export-dir exports
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.data.adapters import SecondBarsAdapter
from acd.data.cache import DataCache
from _analysis_utils import inclusive_end_date, ensure_time_mid_volume, resample_second


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def materialize_second_bars(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    synthetic: bool = True,
    export_dir: str = "exports",
    cache_enabled: bool = True
) -> Dict[str, Any]:
    """
    Materialize second bars for all specified venues.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        synthetic: Whether to use synthetic second data
        export_dir: Export directory
        cache_enabled: Whether to use cache
        
    Returns:
        Dictionary with materialization results
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting second bars materialization")
    
    # Parse dates with inclusive end
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = inclusive_end_date(end_date)  # 23:59:59 inclusive
    
    print(f"[MZ:start] file=second_bars start={start_utc.isoformat()} end={end_utc.isoformat()} granularity=1s")
    
    # Initialize adapters
    second_adapter = SecondBarsAdapter(cache_enabled=cache_enabled, synthetic=synthetic)
    cache = DataCache() if cache_enabled else None
    
    # Results tracking
    results = {
        'start_date': start_date,
        'end_date': end_date,
        'pair': pair,
        'synthetic': synthetic,
        'venues': {},
        'total_bars': 0,
        'coverage_pct': 0.0,
        'gaps': []
    }
    
    # Process each venue
    for venue in venues:
        logger.info(f"Processing venue: {venue}")
        
        try:
            # Check cache first
            cached_data = None
            if cache:
                cached_data = cache.get(venue, pair, '1s', start_utc, end_utc)
            
            if cached_data is not None:
                df = cached_data
                logger.info(f"[DATA:cache:hit] {venue}:{pair} - {len(df)} bars from cache")
            else:
                # Fetch fresh data
                df = second_adapter.get(pair, venue, start_utc, end_utc)
                
                # Cache the data
                if cache:
                    cache.put(venue, pair, '1s', df)
            
            # Apply canonical schema normalization
            df = ensure_time_mid_volume(df)
            logger.info(f"[MZ:schema] venue={venue} cols={list(df.columns)}")
            
            # Analyze data quality with inclusive window
            venue_results = analyze_data_quality(df, venue, pair, start_utc, end_utc)
            results['venues'][venue] = venue_results
            results['total_bars'] += len(df)
            
            # Check for gaps
            if venue_results['coverage_pct'] < 95.0:
                gap_info = {
                    'venue': venue,
                    'coverage_pct': venue_results['coverage_pct'],
                    'missing_bars': venue_results['expected_bars'] - venue_results['actual_bars']
                }
                results['gaps'].append(gap_info)
                logger.warning(f"[DATA:gaps] {venue}:{pair} - {venue_results['coverage_pct']:.1f}% coverage")
            
        except Exception as e:
            logger.error(f"Error processing {venue}:{pair} - {str(e)}")
            results['venues'][venue] = {
                'bars': 0,
                'coverage_pct': 0.0,
                'error': str(e)
            }
    
    # Calculate overall coverage
    if results['total_bars'] > 0:
        expected_total = len(venues) * ((end_utc - start_utc).days + 1) * 24 * 60 * 60  # seconds per day
        results['coverage_pct'] = (results['total_bars'] / expected_total) * 100
    
    logger.info(f"Materialization complete: {results['total_bars']} total bars, {results['coverage_pct']:.1f}% coverage")
    
    return results


def analyze_data_quality(
    df,
    venue: str,
    pair: str,
    start_utc: datetime,
    end_utc: datetime
) -> Dict[str, Any]:
    """
    Analyze data quality and coverage for second bars.
    
    Args:
        df: DataFrame with second bars
        venue: Exchange venue
        pair: Trading pair
        start_utc: Start datetime
        end_utc: End datetime
        
    Returns:
        Dictionary with quality metrics
    """
    if df.empty:
        return {
            'bars': 0,
            'coverage_pct': 0.0,
            'expected_bars': 0,
            'actual_bars': 0,
            'start_time': None,
            'end_time': None
        }
    
    # Calculate expected bars with inclusive window
    expected_seconds = int((end_utc - start_utc).total_seconds()) + 1
    actual_seconds = len(df.index.unique())
    coverage = round(min(actual_seconds / expected_seconds, 1.0), 4)
    
    logger.info(f"[STATS:materialize:granularity=1s] venue={venue} expected={expected_seconds} actual={actual_seconds} coverage={coverage}")
    
    if coverage < 0.8:
        logger.warning(f"[WARN:materialize:low_coverage] venue={venue} coverage={coverage}")
    
    # Legacy fields for compatibility
    expected_bars = expected_seconds
    actual_bars = actual_seconds
    coverage_pct = coverage * 100
    
    # Get time range
    if 'time' in df.columns:
        start_time = df['time'].min()
        end_time = df['time'].max()
    else:
        start_time = end_time = None
    
    return {
        'bars': actual_bars,
        'coverage_pct': round(coverage_pct, 2),
        'expected_bars': expected_bars,
        'actual_bars': actual_bars,
        'start_time': start_time.isoformat() if start_time else None,
        'end_time': end_time.isoformat() if end_time else None
    }


def export_data_inventory(
    results: Dict[str, Any],
    export_dir: str
) -> None:
    """
    Export data inventory to JSON file.
    
    Args:
        results: Materialization results
        export_dir: Export directory
    """
    os.makedirs(export_dir, exist_ok=True)
    
    inventory = {
        'materialization': {
            'start_date': results['start_date'],
            'end_date': results['end_date'],
            'pair': results['pair'],
            'synthetic': results['synthetic'],
            'total_bars': results['total_bars'],
            'coverage_pct': results['coverage_pct']
        },
        'venues': results['venues'],
        'gaps': results['gaps'],
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'frequency': '1s',
            'sources': {
                'second': 'synthetic_v1' if results['synthetic'] else 'native'
            }
        }
    }
    
    inventory_path = os.path.join(export_dir, 'data_inventory.json')
    with open(inventory_path, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    
    print(f"Data inventory exported to: {inventory_path}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Materialize second bars for market data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--synthetic", choices=['yes', 'no'], default='yes', help="Use synthetic second data")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    # Parse synthetic flag
    synthetic = args.synthetic == 'yes'
    
    try:
        # Materialize second bars
        results = materialize_second_bars(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            synthetic=synthetic,
            export_dir=args.export_dir,
            cache_enabled=not args.no_cache
        )
        
        # Export data inventory
        export_data_inventory(results, args.export_dir)
        
        # Print summary
        print("\n" + "="*80)
        print("SECOND BARS MATERIALIZATION SUMMARY")
        print("="*80)
        print(f"Period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Synthetic: {synthetic}")
        print(f"Total bars: {results['total_bars']:,}")
        print(f"Coverage: {results['coverage_pct']:.1f}%")
        
        if results['gaps']:
            print("\nGaps detected:")
            for gap in results['gaps']:
                print(f"  {gap['venue']}: {gap['coverage_pct']:.1f}% coverage ({gap['missing_bars']} missing bars)")
        else:
            print("\n✅ No significant gaps detected")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
