#!/usr/bin/env python3
"""
Information Share Analysis Script

This script implements Hasbrouck information share bounds to determine
which venue embeds fundamental information first using minute-level data.

Usage:
    python scripts/run_info_share.py \
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

from acd.analytics.info_share import InfoShareAnalyzer, create_info_share_analyzer


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_info_share_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    export_dir: str = "exports",
    max_lag: int = 5,
    bootstrap: int = 500,
    print_evidence: bool = False
) -> Dict[str, Any]:
    """
    Run complete information share analysis.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        pair: Trading pair
        venues: List of venues
        export_dir: Export directory
        max_lag: Maximum lag for VECM estimation
        bootstrap: Number of bootstrap samples
        print_evidence: Whether to print evidence blocks
        
    Returns:
        Analysis results dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting information share analysis")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Create analyzer
    analyzer = create_info_share_analyzer(
        max_lag=max_lag,
        bootstrap_samples=bootstrap
    )
    
    # Run analysis
    result = analyzer.analyze_info_share(
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
            "export_dir": export_dir,
            "max_lag": max_lag,
            "bootstrap_samples": bootstrap
        },
        "results": {
            "total_days": len(result.daily_results),
            "kept_days": result.assignments.get('keptDays', 0),
            "dropped_days": result.assignments.get('droppedDays', 0),
            "venues_analyzed": len(venues)
        },
        "export_files": [
            "info_share.json",
            "info_share_by_env.csv",
            "info_share_assignments.json",
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
    print("INFORMATION SHARE ANALYSIS EVIDENCE BLOCKS")
    print("="*80)
    
    # File list
    print("-----BEGIN INFO SHARE FILES-----")
    import subprocess
    try:
        result = subprocess.run(
            ["ls", "-lh", export_dir],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'info_share' in line or 'MANIFEST' in line:
                print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  Error listing files")
    print("-----END INFO SHARE FILES-----")
    
    # Overall results
    print("-----BEGIN INFO SHARE OVERALL-----")
    try:
        info_share_path = os.path.join(export_dir, "info_share.json")
        if os.path.exists(info_share_path):
            with open(info_share_path, "r") as f:
                import json
                info_data = json.load(f)
                print(json.dumps(info_data.get("overall", []), indent=2))
        else:
            print("No info_share.json file found")
    except Exception as e:
        print(f"Error reading info_share.json: {e}")
    print("-----END INFO SHARE OVERALL-----")
    
    # Volatility results
    print("-----BEGIN INFO SHARE (VOLATILITY)-----")
    try:
        info_share_path = os.path.join(export_dir, "info_share.json")
        if os.path.exists(info_share_path):
            with open(info_share_path, "r") as f:
                import json
                info_data = json.load(f)
                print(json.dumps(info_data["by_env"].get("volatility", {}), indent=2))
        else:
            print("No info_share.json file found")
    except Exception as e:
        print(f"Error reading volatility data: {e}")
    print("-----END INFO SHARE (VOLATILITY)-----")
    
    # Funding results
    print("-----BEGIN INFO SHARE (FUNDING)-----")
    try:
        info_share_path = os.path.join(export_dir, "info_share.json")
        if os.path.exists(info_share_path):
            with open(info_share_path, "r") as f:
                import json
                info_data = json.load(f)
                print(json.dumps(info_data["by_env"].get("funding", {}), indent=2))
        else:
            print("No info_share.json file found")
    except Exception as e:
        print(f"Error reading funding data: {e}")
    print("-----END INFO SHARE (FUNDING)-----")
    
    # Liquidity results
    print("-----BEGIN INFO SHARE (LIQUIDITY)-----")
    try:
        info_share_path = os.path.join(export_dir, "info_share.json")
        if os.path.exists(info_share_path):
            with open(info_share_path, "r") as f:
                import json
                info_data = json.load(f)
                print(json.dumps(info_data["by_env"].get("liquidity", {}), indent=2))
        else:
            print("No info_share.json file found")
    except Exception as e:
        print(f"Error reading liquidity data: {e}")
    print("-----END INFO SHARE (LIQUIDITY)-----")
    
    # Assignments
    print("-----BEGIN INFO SHARE ASSIGNMENTS-----")
    try:
        assignments_path = os.path.join(export_dir, "info_share_assignments.json")
        if os.path.exists(assignments_path):
            with open(assignments_path, "r") as f:
                import json
                assignments_data = json.load(f)
                print(json.dumps(assignments_data, indent=2))
        else:
            print("No assignments file found")
    except Exception as e:
        print(f"Error reading assignments: {e}")
    print("-----END INFO SHARE ASSIGNMENTS-----")
    
    # Stats from logs
    print("-----BEGIN INFO SHARE STATS (grep)-----")
    print("Pattern: grep -E '^\\[(MICRO:infoShare:env|STATS:infoShare:bootstrap|INFO:infoShare:assignments)' /tmp/acd_info_share.log")
    print("Note: Stats are printed during analysis execution")
    print("-----END INFO SHARE STATS (grep)-----")
    
    print("="*80)


def main():
    """Main function to run information share analysis."""
    parser = argparse.ArgumentParser(description="Run information share analysis")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pair", required=True, help="Trading pair (e.g., BTC-USD)")
    parser.add_argument("--venues", required=True, help="Comma-separated list of venues")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--max-lag", type=int, default=5, help="Maximum lag for VECM estimation")
    parser.add_argument("--bootstrap", type=int, default=500, help="Number of bootstrap samples")
    parser.add_argument("--print-evidence", action="store_true", help="Print evidence blocks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse venues
    venues = [v.strip() for v in args.venues.split(',')]
    
    try:
        # Run analysis
        results = run_info_share_analysis(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            export_dir=args.export_dir,
            max_lag=args.max_lag,
            bootstrap=args.bootstrap,
            print_evidence=args.print_evidence
        )
        
        # Print summary
        print("\n" + "="*80)
        print("INFORMATION SHARE ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Kept days: {results['results']['kept_days']}")
        print(f"Dropped days: {results['results']['dropped_days']}")
        print(f"Max lag: {args.max_lag}")
        print(f"Bootstrap samples: {args.bootstrap}")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
