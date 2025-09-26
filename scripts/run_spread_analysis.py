#!/usr/bin/env python3
"""
Cross-Venue Spread Compression Analysis Script

This script detects convergence episodes where venues move toward consensus pricing,
which may reflect coordinated algorithmic behavior.

Usage:
    python scripts/run_spread_analysis.py \
        --start 2025-01-01 --end 2025-01-03 \
        --pair BTC-USD --venues binance,coinbase,kraken,bybit,okx \
        --export-dir exports --verbose
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.analytics.spread_convergence import SpreadConvergenceAnalyzer, create_spread_convergence_analyzer


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_spread_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    export_dir: str = "exports",
    print_evidence: bool = False
) -> Dict[str, Any]:
    """
    Run complete spread convergence analysis.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        export_dir: Export directory
        print_evidence: Whether to print evidence blocks
        
    Returns:
        Analysis results dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting spread convergence analysis")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Create analyzer
    analyzer = create_spread_convergence_analyzer()
    
    # Run analysis
    result = analyzer.analyze_spread_convergence(
        pair=pair,
        venues=venues,
        start_utc=start_utc,
        end_utc=end_utc,
        output_dir=export_dir,
        start_date=start_date,
        end_date=end_date
    )
    
    # Create summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "start_date": start_date,
            "end_date": end_date,
            "pair": pair,
            "venues": venues,
            "export_dir": export_dir
        },
        "results": {
            "total_episodes": len(result.episodes),
            "min_duration": analyzer.min_duration,
            "compression_threshold": analyzer.compression_threshold,
            "venues_analyzed": len(venues)
        },
        "export_files": [
            "spread_episodes.csv",
            "spread_leaders.json",
            "MANIFEST.json"
        ]
    }
    
    # Print evidence if requested
    if print_evidence:
        print_evidence_blocks(export_dir)
    
    return summary


def print_evidence_blocks(export_dir: str) -> None:
    """Print evidence blocks for verification."""
    print("\n" + "="*80)
    print("CROSS-VENUE SPREAD COMPRESSION EVIDENCE BLOCKS")
    print("="*80)
    
    # File list
    print("-----BEGIN SPREAD FILES-----")
    import subprocess
    try:
        result = subprocess.run(
            ["ls", "-lh", export_dir],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'spread' in line or 'MANIFEST' in line:
                print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  Error listing files")
    print("-----END SPREAD FILES-----")
    
    # Episodes CSV
    print("-----BEGIN SPREAD EPISODES (top)-----")
    try:
        episodes_path = os.path.join(export_dir, "spread_episodes.csv")
        if os.path.exists(episodes_path):
            result = subprocess.run(
                ["head", "-n", "10", episodes_path],
                capture_output=True, text=True, check=True
            )
            print(result.stdout)
        else:
            print("No episodes file found")
    except subprocess.CalledProcessError:
        print("Error reading episodes file")
    print("-----END SPREAD EPISODES (top)-----")
    
    # Leaders JSON
    print("-----BEGIN SPREAD LEADERS-----")
    try:
        leaders_path = os.path.join(export_dir, "spread_leaders.json")
        if os.path.exists(leaders_path):
            with open(leaders_path, "r") as f:
                import json
                leaders_data = json.load(f)
                print(json.dumps(leaders_data, indent=2, default=str))
        else:
            print("No leaders file found")
    except Exception as e:
        print(f"Error reading leaders file: {e}")
    print("-----END SPREAD LEADERS-----")
    
    # Stats from logs
    print("-----BEGIN SPREAD STATS (grep)-----")
    print("Pattern: grep -E '^\\[STATS:spread:' /tmp/acd_spread.log")
    print("Note: Stats are printed during analysis execution")
    print("-----END SPREAD STATS (grep)-----")
    
    print("="*80)


def main():
    """Main function to run spread convergence analysis."""
    parser = argparse.ArgumentParser(description="Run spread convergence analysis")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--print-evidence", action="store_true", help="Print evidence blocks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Run analysis
        results = run_spread_analysis(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            export_dir=args.export_dir,
            print_evidence=args.print_evidence
        )
        
        # Print summary
        print("\n" + "="*80)
        print("CROSS-VENUE SPREAD COMPRESSION SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Total episodes: {results['results']['total_episodes']}")
        print(f"Minimum duration: {results['results']['min_duration']}s")
        print(f"Compression threshold: {results['results']['compression_threshold']*100}%")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
