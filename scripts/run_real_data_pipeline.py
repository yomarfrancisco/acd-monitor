#!/usr/bin/env python3
"""
Master script for real data pipeline.

This script orchestrates:
1. Materializing real tick data
2. Running spread compression analysis
3. Running information share analysis
4. Generating court-ready evidence
"""

import argparse
import logging
import sys
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
            logging.FileHandler('real_data_pipeline.log')
        ]
    )


def run_complete_pipeline(
    start_date: str,
    end_date: str,
    pair: str,
    venues: list,
    cache_dir: str,
    export_dir: str,
    verbose: bool = False
) -> None:
    """
    Run the complete real data pipeline.
    
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
    logger.info("Starting complete real data pipeline")
    
    # Step 1: Materialize real tick data
    print("\n" + "="*80)
    print("STEP 1: MATERIALIZING REAL TICK DATA")
    print("="*80)
    
    try:
        # Import and run materialization directly
        from acd.data.adapters.real_tick_adapters import fetch_real_tick_data
        from acd.data.cache import DataCache
        import json
        
        # Parse dates
        start_time = datetime.strptime(start_date, "%Y-%m-%d")
        end_time = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Fetch real tick data
        venue_data = fetch_real_tick_data(
            venues=venues,
            pair=pair,
            start_time=start_time,
            end_time=end_time,
            cache_dir=cache_dir
        )
        
        if len(venue_data) >= 3:
            print("✅ Real tick data materialization completed")
            print(f"Successfully cached data for {len(venue_data)} venues")
        else:
            print("❌ Insufficient venues with data")
            return
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        return
    
    # Step 2: Run spread compression analysis
    print("\n" + "="*80)
    print("STEP 2: SPREAD COMPRESSION ANALYSIS")
    print("="*80)
    
    try:
        import subprocess
        cmd = [
            'python', 'scripts/run_spread_compression_real.py',
            '--start', start_date,
            '--end', end_date,
            '--pair', pair,
            '--venues', ','.join(venues),
            '--cache-dir', cache_dir,
            '--export-dir', export_dir
        ]
        if verbose:
            cmd.append('--verbose')
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Spread compression analysis completed")
            print(result.stdout)
        else:
            print("❌ Spread compression analysis failed")
            print(result.stderr)
    except Exception as e:
        logger.error(f"Step 2 failed: {e}")
    
    # Step 3: Run information share analysis
    print("\n" + "="*80)
    print("STEP 3: INFORMATION SHARE ANALYSIS")
    print("="*80)
    
    try:
        import subprocess
        cmd = [
            'python', 'scripts/run_info_share_real.py',
            '--start', start_date,
            '--end', end_date,
            '--pair', pair,
            '--venues', ','.join(venues),
            '--cache-dir', cache_dir,
            '--export-dir', export_dir
        ]
        if verbose:
            cmd.append('--verbose')
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Information share analysis completed")
            print(result.stdout)
        else:
            print("❌ Information share analysis failed")
            print(result.stderr)
    except Exception as e:
        logger.error(f"Step 3 failed: {e}")
    
    # Step 4: Generate final evidence summary
    print("\n" + "="*80)
    print("STEP 4: FINAL EVIDENCE SUMMARY")
    print("="*80)
    
    try:
        generate_final_summary(export_dir, start_date, end_date)
        print("✅ Final evidence summary generated")
    except Exception as e:
        logger.error(f"Step 4 failed: {e}")
    
    print("\n" + "="*80)
    print("REAL DATA PIPELINE COMPLETED")
    print("="*80)
    print(f"Period: {start_date} to {end_date}")
    print(f"Pair: {pair}")
    print(f"Venues: {', '.join(venues)}")
    print(f"Export directory: {export_dir}")
    print("="*80 + "\n")


def generate_final_summary(export_dir: str, start_date: str, end_date: str) -> None:
    """Generate final evidence summary."""
    import json
    from pathlib import Path
    
    summary = {
        "analysis_type": "real_data_pipeline",
        "start_date": start_date,
        "end_date": end_date,
        "export_directory": export_dir,
        "files_generated": [],
        "analysis_results": {}
    }
    
    # List all generated files
    export_path = Path(export_dir)
    if export_path.exists():
        for file_path in export_path.rglob("*"):
            if file_path.is_file():
                summary["files_generated"].append(str(file_path.relative_to(export_path)))
    
    # Save summary
    summary_file = export_path / "pipeline_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"Pipeline summary saved to: {summary_file}")


def main():
    """Main function to run the complete pipeline."""
    parser = argparse.ArgumentParser(description="Run complete real data pipeline")
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
        # Run complete pipeline
        run_complete_pipeline(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            cache_dir=args.cache_dir,
            export_dir=args.export_dir,
            verbose=args.verbose
        )
        
    except Exception as e:
        logging.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
