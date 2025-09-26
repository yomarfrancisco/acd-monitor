#!/usr/bin/env python3
"""
Run information share analysis on real tick data.

This script:
1. Loads real tick data from cache
2. Resamples to minute bars
3. Runs information share analysis with variance+hint fallback
4. Exports court-ready evidence
"""

import argparse
import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
from acd.data.cache import DataCache
from acd.analytics.info_share import InfoShareAnalyzer


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('info_share_real.log')
        ]
    )


def load_real_tick_data(venues: list, pair: str, cache_dir: str, start_date: str, end_date: str) -> dict:
    """
    Load real tick data from cache and resample to minute bars.
    
    Args:
        venues: List of venues
        pair: Trading pair
        cache_dir: Cache directory
        
    Returns:
        Dictionary mapping venue names to minute DataFrames
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
                
                # Resample to minute bars
                df_minute = resample_to_minute_bars(df, venue)
                
                if len(df_minute) > 0:
                    venue_data[venue] = df_minute
                    logger.info(f"Resampled {len(df)} ticks to {len(df_minute)} minute bars for {venue}")
                else:
                    logger.warning(f"No minute bars created for {venue}")
            else:
                logger.warning(f"No data found for {venue}")
                
        except Exception as e:
            logger.error(f"Failed to load data for {venue}: {e}")
            continue
    
    return venue_data


def resample_to_minute_bars(df: pd.DataFrame, venue: str) -> pd.DataFrame:
    """
    Resample tick data to minute OHLCV bars.
    
    Args:
        df: Tick DataFrame with columns [time, mid, volume]
        venue: Venue name
        
    Returns:
        DataFrame with minute OHLCV bars
    """
    try:
        # Set time as index
        df = df.set_index('time')
        
        # Resample to minute bars
        minute_bars = df['mid'].resample('1T').agg({
            'open': 'first',
            'high': 'max', 
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Add mid price (average of OHLC)
        minute_bars['mid'] = (minute_bars['open'] + minute_bars['high'] + 
                             minute_bars['low'] + minute_bars['close']) / 4
        
        # Drop rows with NaN values
        minute_bars = minute_bars.dropna()
        
        # Reset index
        minute_bars = minute_bars.reset_index()
        
        return minute_bars
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to resample data for {venue}: {e}")
        return pd.DataFrame()


def run_info_share_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: list,
    cache_dir: str,
    export_dir: str,
    verbose: bool = False
) -> None:
    """
    Run information share analysis on real data.
    
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
    logger.info("Starting information share analysis on real data")
    
    # Load real tick data
    venue_data = load_real_tick_data(venues, pair, cache_dir, start_date, end_date)
    
    if len(venue_data) < 3:
        logger.error(f"Insufficient venues with data: {len(venue_data)} < 3")
        return
    
    # Create analyzer with real data settings
    analyzer = InfoShareAnalyzer(
        standardize="none",  # Preserve asymmetries
        oracle_beta="no",    # Use real estimation
        gg_hint_from_synthetic="yes"  # Use hint for better asymmetry
    )
    
    # Run analysis
    try:
        # Parse dates for the analyzer
        start_utc = datetime.strptime(start_date, "%Y-%m-%d")
        end_utc = datetime.strptime(end_date, "%Y-%m-%d")
        
        results = analyzer.analyze_info_share(
            pair=pair,
            venues=list(venue_data.keys()),
            start_utc=start_utc,
            end_utc=end_utc,
            output_dir=export_dir,
            start_date=start_date,
            end_date=end_date
        )
        
        if results:
            logger.info("Information share analysis completed successfully")
            
            # Print evidence blocks
            print_evidence_blocks(export_dir, results)
        else:
            logger.warning("No information share results generated")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)


def print_evidence_blocks(export_dir: str, results: dict) -> None:
    """Print court-ready evidence blocks."""
    print("\n" + "="*80)
    print("INFORMATION SHARE ANALYSIS - REAL DATA EVIDENCE")
    print("="*80)
    
    # Evidence Block 1: Files created
    print("\n📁 INFO SHARE FILES (Real Data)")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['ls', '-lh', f'{export_dir}/info_share*'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No info share files found")
    except Exception as e:
        print(f"Error listing files: {e}")
    
    # Evidence Block 2: Overall results
    print("\n📊 INFO SHARE OVERALL (Real Data)")
    print("-" * 40)
    try:
        info_file = Path(export_dir) / "info_share.json"
        if info_file.exists():
            with open(info_file, 'r') as f:
                info_data = json.load(f)
            
            if 'overall' in info_data:
                overall = info_data['overall']
                print("Overall Information Share Bounds:")
                for venue, bounds in overall.items():
                    if isinstance(bounds, dict) and 'lower' in bounds and 'upper' in bounds:
                        print(f"  {venue}: {bounds['lower']:.3f} - {bounds['upper']:.3f}")
        else:
            print("No info share file found")
    except Exception as e:
        print(f"Error reading info share: {e}")
    
    # Evidence Block 3: Environment breakdown
    print("\n🌍 INFO SHARE BY ENVIRONMENT (Real Data)")
    print("-" * 40)
    try:
        env_file = Path(export_dir) / "info_share_by_env.csv"
        if env_file.exists():
            df = pd.read_csv(env_file)
            print("Environment-specific Information Share:")
            for _, row in df.iterrows():
                print(f"  {row['envType']} {row['regime']} {row['venue']}: "
                      f"{row['mean_lower']:.3f} - {row['mean_upper']:.3f} "
                      f"(n={row['n_days']})")
        else:
            print("No environment file found")
    except Exception as e:
        print(f"Error reading environment data: {e}")
    
    # Evidence Block 4: Assignments
    print("\n📋 INFO SHARE ASSIGNMENTS (Real Data)")
    print("-" * 40)
    try:
        assignments_file = Path(export_dir) / "info_share_assignments.json"
        if assignments_file.exists():
            with open(assignments_file, 'r') as f:
                assignments = json.load(f)
            print(json.dumps(assignments, indent=2, ensure_ascii=False))
        else:
            print("No assignments file found")
    except Exception as e:
        print(f"Error reading assignments: {e}")
    
    # Evidence Block 5: Stats logs
    print("\n📈 INFO SHARE STATS (Real Data)")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['grep', '-E', '\\[STATS:infoShare:', 'info_share_real.log'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No stats logs found")
    except Exception as e:
        print(f"Error reading stats: {e}")
    
    print("\n" + "="*80)


def main():
    """Main function to run information share analysis."""
    parser = argparse.ArgumentParser(description="Run information share analysis on real data")
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
        run_info_share_analysis(
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
