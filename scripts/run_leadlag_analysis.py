#!/usr/bin/env python3
"""
Lead-Lag Matrix Analysis Script

This script runs lead-lag analysis to identify who moves first in short horizons
and detect coordination patterns between venues.

Usage:
    python scripts/run_leadlag_analysis.py \
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

from acd.analytics.leadlag import LeadLagMatrixAnalyzer, create_leadlag_analyzer


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_leadlag_analysis(
    start_date: str,
    end_date: str,
    pair: str,
    venues: List[str],
    export_dir: str = "exports",
    print_evidence: bool = False
) -> Dict[str, Any]:
    """
    Run complete lead-lag analysis.
    
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
    logger.info("Starting lead-lag matrix analysis")
    
    # Parse dates
    start_utc = datetime.strptime(start_date, "%Y-%m-%d")
    end_utc = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Create analyzer
    analyzer = create_leadlag_analyzer()
    
    # Run analysis
    result = analyzer.analyze_leadlag(
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
            "horizons_analyzed": len(result.edges),
            "total_edges": sum(len(edges) for edges in result.edges.values()),
            "significant_edges": sum(
                len([e for e in edges if e['valid'] and e['p_value'] < 0.05])
                for edges in result.edges.values()
            ),
            "venues_analyzed": len(venues)
        },
        "export_files": [
            "leadlag_edges_h=1s.csv",
            "leadlag_edges_h=5s.csv", 
            "leadlag_edges_h=30s.csv",
            "leadlag_ranks.csv",
            "leadlag_by_env.json",
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
    print("LEAD-LAG MATRIX ANALYSIS EVIDENCE BLOCKS")
    print("="*80)
    
    # File list
    print("-----BEGIN LEADLAG FILES-----")
    import subprocess
    try:
        result = subprocess.run(
            ["ls", "-lh", export_dir],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'leadlag' in line or 'MANIFEST' in line:
                print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  Error listing files")
    print("-----END LEADLAG FILES-----")
    
    # Edges for 1s horizon
    print("-----BEGIN LEADLAG EDGES (1s)-----")
    try:
        edges_path = os.path.join(export_dir, "leadlag_edges_h=1s.csv")
        if os.path.exists(edges_path):
            result = subprocess.run(
                ["head", "-n", "10", edges_path],
                capture_output=True, text=True, check=True
            )
            print(result.stdout)
        else:
            print("No 1s edges file found")
    except subprocess.CalledProcessError:
        print("Error reading edges file")
    print("-----END LEADLAG EDGES (1s)-----")
    
    # Leader rankings
    print("-----BEGIN LEADER RANKINGS-----")
    try:
        ranks_path = os.path.join(export_dir, "leadlag_ranks.csv")
        if os.path.exists(ranks_path):
            result = subprocess.run(
                ["head", "-n", "20", ranks_path],
                capture_output=True, text=True, check=True
            )
            print(result.stdout)
        else:
            print("No rankings file found")
    except subprocess.CalledProcessError:
        print("Error reading rankings file")
    print("-----END LEADER RANKINGS-----")
    
    # Cross-environment results
    print("-----BEGIN CROSS-ENVIRONMENT RESULTS-----")
    try:
        cross_env_path = os.path.join(export_dir, "leadlag_by_env.json")
        if os.path.exists(cross_env_path):
            with open(cross_env_path, "r") as f:
                import json
                cross_data = json.load(f)
                print(json.dumps(cross_data, indent=2, default=str))
        else:
            print("No cross-environment file found")
    except Exception as e:
        print(f"Error reading cross-environment file: {e}")
    print("-----END CROSS-ENVIRONMENT RESULTS-----")
    
    # Stats from logs
    print("-----BEGIN LEADLAG STATS (grep)-----")
    print("Pattern: grep -E '^\\[STATS:leadlag:' /tmp/acd_leadlag.log")
    print("Note: Stats are printed during analysis execution")
    print("-----END LEADLAG STATS (grep)-----")
    
    print("="*80)


def main():
    """Main function to run lead-lag analysis."""
    parser = argparse.ArgumentParser(description="Run lead-lag matrix analysis")
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
        results = run_leadlag_analysis(
            start_date=args.start,
            end_date=args.end,
            pair=args.pair,
            venues=venues,
            export_dir=args.export_dir,
            print_evidence=args.print_evidence
        )
        
        # Print summary
        print("\n" + "="*80)
        print("LEAD-LAG MATRIX ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start} to {args.end}")
        print(f"Pair: {args.pair}")
        print(f"Venues: {', '.join(venues)}")
        print(f"Horizons analyzed: {results['results']['horizons_analyzed']}")
        print(f"Total edges: {results['results']['total_edges']}")
        print(f"Significant edges: {results['results']['significant_edges']}")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
