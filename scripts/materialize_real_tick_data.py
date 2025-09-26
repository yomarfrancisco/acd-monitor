#!/usr/bin/env python3
"""
Materialize real tick data for BTC-USD across multiple venues.

This script fetches real tick/trade data from:
- Binance
- Coinbase
- Kraken  
- OKX
- Bybit

And stores it in Parquet format for analysis.
"""

import argparse
import logging
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.data.adapters.real_tick_adapters import fetch_real_tick_data
from acd.data.cache import DataCache


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('real_tick_materialization.log')
        ]
    )


def materialize_real_data(
    start_date: str,
    end_date: str,
    pair: str,
    venues: list,
    cache_dir: str = "data/cache",
    min_days: int = 30
) -> None:
    """
    Materialize real tick data for specified period.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        cache_dir: Cache directory
        min_days: Minimum days of data required
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Materializing real tick data for {pair}")
    
    # Parse dates
    start_time = datetime.strptime(start_date, "%Y-%m-%d")
    end_time = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Calculate expected days
    expected_days = (end_time - start_time).days
    if expected_days < min_days:
        logger.warning(f"Period {expected_days} days < minimum {min_days} days")
    
    # Create cache
    cache = DataCache(cache_dir)
    
    # Fetch data for all venues
    venue_data = fetch_real_tick_data(
        venues=venues,
        pair=pair,
        start_time=start_time,
        end_time=end_time,
        cache_dir=cache_dir
    )
    
    # Validate data quality
    successful_venues = []
    for venue, df in venue_data.items():
        if len(df) > 0:
            # Calculate coverage
            total_seconds = (end_time - start_time).total_seconds()
            actual_ticks = len(df)
            coverage_pct = (actual_ticks / total_seconds) * 100 if total_seconds > 0 else 0
            
            # Log materialization
            materialize_log = {
                "venue": venue,
                "start": start_date,
                "end": end_date,
                "ticks": actual_ticks,
                "coveragePct": round(coverage_pct, 2),
                "source": "real_tick_data"
            }
            print(f"[DATA:tick:materialize] {json.dumps(materialize_log, ensure_ascii=False)}")
            
            successful_venues.append(venue)
            logger.info(f"Cached {actual_ticks} ticks for {venue} ({coverage_pct:.2f}% coverage)")
        else:
            logger.warning(f"No data retrieved for {venue}")
    
    # Export data inventory
    inventory = {
        "source": "real_tick_data",
        "pair": pair,
        "start_date": start_date,
        "end_date": end_date,
        "venues": successful_venues,
        "total_venues": len(venues),
        "success_rate": len(successful_venues) / len(venues),
        "coverage": {
            venue: {
                "ticks": len(venue_data.get(venue, [])),
                "coverage_pct": round((len(venue_data.get(venue, [])) / (end_time - start_time).total_seconds()) * 100, 2)
            } for venue in successful_venues
        }
    }
    
    # Write inventory
    import json
    inventory_path = Path(cache_dir) / "real_tick_inventory.json"
    with open(inventory_path, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    
    logger.info(f"Successfully materialized real tick data for {len(successful_venues)}/{len(venues)} venues")
    logger.info(f"Data inventory saved to {inventory_path}")


def main():
    """Main function to materialize real tick data."""
    parser = argparse.ArgumentParser(description="Materialize real tick data for BTC-USD")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", default="BTC-USD", help="Trading pair")
    parser.add_argument("--venues", default="binance,coinbase,kraken,okx,bybit", 
                       help="Comma-separated list of venues")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--min-days", type=int, default=30, help="Minimum days of data required")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Materialize data
        materialize_real_data(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            cache_dir=args.cache_dir,
            min_days=args.min_days
        )
        
        print("\n" + "="*80)
        print("REAL TICK DATA MATERIALIZATION COMPLETE")
        print("="*80)
        print(f"Period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Cache directory: {args.cache_dir}")
        print("="*80 + "\n")
        
    except Exception as e:
        logging.error(f"An error occurred during data materialization: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
