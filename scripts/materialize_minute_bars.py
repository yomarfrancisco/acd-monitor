#!/usr/bin/env python3
"""
Materialize minute bars for specified venues and date range.

Usage:
    python scripts/materialize_minute_bars.py \
        --start 2025-01-01 --end 2025-09-24 \
        --pair BTC-USD --venues binance,coinbase,kraken,bybit,okx \
        --export-dir exports
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

from acd.data.adapters import MinuteBarsAdapter
from acd.data.cache import DataCache


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def materialize_minute_bars(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    export_dir: str = "exports",
    cache_enabled: bool = True
) -> Dict[str, Any]:
    """
    Materialize minute bars for all specified venues.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        export_dir: Export directory
        cache_enabled: Whether to use cache
        
    Returns:
        Dictionary with materialization results
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting minute bars materialization")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Initialize adapters
    minute_adapter = MinuteBarsAdapter(cache_enabled=cache_enabled)
    cache = DataCache() if cache_enabled else None
    
    # Results tracking
    results = {
        'start_date': start_date,
        'end_date': end_date,
        'pair': pair,
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
                cached_data = cache.get(venue, pair, '1min', start_utc, end_utc)
            
            if cached_data is not None:
                df = cached_data
                logger.info(f"[DATA:cache:hit] {venue}:{pair} - {len(df)} bars from cache")
            else:
                # Fetch fresh data
                df = minute_adapter.get(pair, venue, start_utc, end_utc)
                
                # Cache the data
                if cache:
                    cache.put(venue, pair, '1min', df)
            
            # Analyze data quality
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
        expected_total = len(venues) * ((end_utc - start_utc).days + 1) * 24 * 60  # minutes per day
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
    Analyze data quality and coverage.
    
    Args:
        df: DataFrame with minute bars
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
    
    # Calculate expected bars
    total_minutes = (end_utc - start_utc).total_seconds() / 60
    expected_bars = int(total_minutes)
    actual_bars = len(df)
    
    # Calculate coverage
    coverage_pct = (actual_bars / expected_bars) * 100 if expected_bars > 0 else 0
    
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
            'total_bars': results['total_bars'],
            'coverage_pct': results['coverage_pct']
        },
        'venues': results['venues'],
        'gaps': results['gaps'],
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'frequency': '1min',
            'sources': {
                'minute': 'ohlcv_resample'
            }
        }
    }
    
    inventory_path = os.path.join(export_dir, 'data_inventory.json')
    with open(inventory_path, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    
    print(f"Data inventory exported to: {inventory_path}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Materialize minute bars for market data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Materialize minute bars
        results = materialize_minute_bars(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            export_dir=args.export_dir,
            cache_enabled=not args.no_cache
        )
        
        # Export data inventory
        export_data_inventory(results, args.export_dir)
        
        # Print summary
        print("\n" + "="*80)
        print("MINUTE BARS MATERIALIZATION SUMMARY")
        print("="*80)
        print(f"Period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
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
