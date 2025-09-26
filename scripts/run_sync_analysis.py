#!/usr/bin/env python3
"""
Synchronous Move Detection Script

This script detects abnormal simultaneity in venue price movements
to identify potential coordinated algorithmic behavior.

Usage:
    python scripts/run_sync_analysis.py \
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

from acd.analytics.sync_moves import SynchronousMoveDetector, create_sync_move_detector


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_sync_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    export_dir: str = "exports",
    print_evidence: bool = False
) -> Dict[str, Any]:
    """
    Run complete synchronous move analysis.
    
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
    logger.info("Starting synchronous move detection")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Create detector
    detector = create_sync_move_detector()
    
    # Run analysis
    result = detector.analyze_sync_moves(
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
            "total_events": len(result.events),
            "dt_windows": detector.dt_windows,
            "theta_pct": detector.theta_pct,
            "venues_analyzed": len(venues)
        },
        "export_files": [
            "sync_events.csv",
            "sync_summary.json",
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
    print("SYNCHRONOUS MOVE DETECTION EVIDENCE BLOCKS")
    print("="*80)
    
    # File list
    print("-----BEGIN SYNC FILES-----")
    import subprocess
    try:
        result = subprocess.run(
            ["ls", "-lh", export_dir],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'sync' in line or 'MANIFEST' in line:
                print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  Error listing files")
    print("-----END SYNC FILES-----")
    
    # Events CSV
    print("-----BEGIN SYNC EVENTS (top)-----")
    try:
        events_path = os.path.join(export_dir, "sync_events.csv")
        if os.path.exists(events_path):
            result = subprocess.run(
                ["head", "-n", "10", events_path],
                capture_output=True, text=True, check=True
            )
            print(result.stdout)
        else:
            print("No events file found")
    except subprocess.CalledProcessError:
        print("Error reading events file")
    print("-----END SYNC EVENTS (top)-----")
    
    # Summary JSON
    print("-----BEGIN SYNC SUMMARY-----")
    try:
        summary_path = os.path.join(export_dir, "sync_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                import json
                summary_data = json.load(f)
                print(json.dumps(summary_data, indent=2, default=str))
        else:
            print("No summary file found")
    except Exception as e:
        print(f"Error reading summary file: {e}")
    print("-----END SYNC SUMMARY-----")
    
    # Config and summary from logs
    print("-----BEGIN SYNC CONFIG (grep)-----")
    print("Pattern: grep -E '^\\[SYNC:(config|summary)]' /tmp/acd_sync.log")
    print("Note: Config and summary are printed during analysis execution")
    print("-----END SYNC CONFIG (grep)-----")
    
    print("="*80)


def main():
    """Main function to run synchronous move analysis."""
    parser = argparse.ArgumentParser(description="Run synchronous move detection")
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
        results = run_sync_analysis(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            export_dir=args.export_dir,
            print_evidence=args.print_evidence
        )
        
        # Print summary
        print("\n" + "="*80)
        print("SYNCHRONOUS MOVE DETECTION SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Total events: {results['results']['total_events']}")
        print(f"Time windows: {', '.join(map(str, results['results']['dt_windows']))}s")
        print(f"Threshold: {results['results']['theta_pct']}th percentile")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
