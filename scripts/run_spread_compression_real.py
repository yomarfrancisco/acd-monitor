#!/usr/bin/env python3
"""
Run spread compression analysis on real tick data.

This script:
1. Loads real tick data from cache
2. Runs spread convergence analysis
3. Detects compression episodes and attributes leadership
4. Exports court-ready evidence
"""

import argparse
import logging
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.data.cache import DataCache
from acd.analytics.spread_convergence import SpreadConvergenceAnalyzer


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('spread_compression_real.log')
        ]
    )


def load_real_tick_data(venues: list, pair: str, cache_dir: str, start_date: str, end_date: str) -> dict:
    """
    Load real tick data from cache.
    
    Args:
        venues: List of venues
        pair: Trading pair
        cache_dir: Cache directory
        
    Returns:
        Dictionary mapping venue names to DataFrames
    """
    logger = logging.getLogger(__name__)
    cache = DataCache(cache_dir)
    venue_data = {}
    
    for venue in venues:
        try:
            # Load from cache
            start_utc = datetime.strptime(start_date, "%Y-%m-%d")
            end_utc = datetime.strptime(end_date, "%Y-%m-%d")
            df = cache.get(venue=venue, pair=pair, frequency="1s", 
                          start_utc=start_utc, end_utc=end_utc)
            
            if df is not None and len(df) > 0:
                # Ensure proper column names and types
                if 'timestamp' in df.columns:
                    df = df.rename(columns={'timestamp': 'time'})
                if 'price' in df.columns:
                    df = df.rename(columns={'price': 'mid'})
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')
                
                venue_data[venue] = df
                logger.info(f"Loaded {len(df)} ticks for {venue}")
            else:
                logger.warning(f"No data found for {venue}")
                
        except Exception as e:
            logger.error(f"Failed to load data for {venue}: {e}")
            continue
    
    return venue_data


def run_spread_compression_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: list,
    cache_dir: str,
    export_dir: str,
    verbose: bool = False
) -> None:
    """
    Run spread compression analysis on real data.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        cache_dir: Cache directory
        export_dir: Export directory
        verbose: Verbose logging
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting spread compression analysis on real data")
    
    # Load real tick data
    venue_data = load_real_tick_data(venues, pair, cache_dir, start_date, end_date)
    
    if len(venue_data) < 3:
        logger.error(f"Insufficient venues with data: {len(venue_data)} < 3")
        return
    
    # Create analyzer
    analyzer = SpreadConvergenceAnalyzer()
    
    # Run analysis
    try:
        # Parse dates for the analyzer
        start_utc = datetime.strptime(start_date, "%Y-%m-%d")
        end_utc = datetime.strptime(end_date, "%Y-%m-%d")
        
        results = analyzer.analyze_spread_convergence(
            pair=pair,
            venues=list(venue_data.keys()),
            start_utc=start_utc,
            end_utc=end_utc,
            output_dir=export_dir,
            start_date=start_date,
            end_date=end_date
        )
        
        if results:
            logger.info("Spread compression analysis completed successfully")
            
            # Print evidence blocks
            print_evidence_blocks(export_dir, results)
        else:
            logger.warning("No compression episodes detected")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)


def print_evidence_blocks(export_dir: str, results: dict) -> None:
    """Print court-ready evidence blocks."""
    print("\n" + "="*80)
    print("SPREAD COMPRESSION ANALYSIS - REAL DATA EVIDENCE")
    print("="*80)
    
    # Evidence Block 1: Files created
    print("\n📁 SPREAD FILES (Real Data)")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['ls', '-lh', f'{export_dir}/spread_*'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No spread files found")
    except Exception as e:
        print(f"Error listing files: {e}")
    
    # Evidence Block 2: Episodes summary
    print("\n📊 SPREAD EPISODES (Real Data)")
    print("-" * 40)
    try:
        episodes_file = Path(export_dir) / "spread_episodes.csv"
        if episodes_file.exists():
            import pandas as pd
            df = pd.read_csv(episodes_file)
            print(f"Total episodes detected: {len(df)}")
            if len(df) > 0:
                print(f"Median duration: {df['duration'].median():.2f}s")
                print(f"Duration range: {df['duration'].min():.2f}s - {df['duration'].max():.2f}s")
                print(f"Leaders: {df['leader'].value_counts().to_dict()}")
        else:
            print("No episodes file found")
    except Exception as e:
        print(f"Error reading episodes: {e}")
    
    # Evidence Block 3: Leaders summary
    print("\n👑 SPREAD LEADERS (Real Data)")
    print("-" * 40)
    try:
        leaders_file = Path(export_dir) / "spread_leaders.json"
        if leaders_file.exists():
            with open(leaders_file, 'r') as f:
                leaders_data = json.load(f)
            print(json.dumps(leaders_data, indent=2, ensure_ascii=False))
        else:
            print("No leaders file found")
    except Exception as e:
        print(f"Error reading leaders: {e}")
    
    # Evidence Block 4: Stats logs
    print("\n📈 SPREAD STATS (Real Data)")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['grep', '-E', '\\[STATS:spread:', 'spread_compression_real.log'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No stats logs found")
    except Exception as e:
        print(f"Error reading stats: {e}")
    
    print("\n" + "="*80)


def main():
    """Main function to run spread compression analysis."""
    parser = argparse.ArgumentParser(description="Run spread compression analysis on real data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", default="BTC-USD", help="Trading pair")
    parser.add_argument("--venues", default="binance,coinbase,kraken,okx,bybit", 
                       help="Comma-separated list of venues")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--export-dir", default="exports/real_data_runs", help="Export directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    # Create export directory
    Path(args.export_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Run analysis
        run_spread_compression_analysis(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            cache_dir=args.cache_dir,
            export_dir=args.export_dir,
            verbose=args.verbose
        )
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
