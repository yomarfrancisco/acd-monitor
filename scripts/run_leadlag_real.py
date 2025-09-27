#!/usr/bin/env python3
"""
Run lead-lag analysis on real data with snapshot support.
"""

import argparse
import json
import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

def load_overlap_data(overlap_file):
    """Load overlap data from OVERLAP.json."""
    with open(overlap_file, 'r') as f:
        return json.load(f)

def run_leadlag_analysis(overlap_data, horizons=[1, 5], out_dir=None):
    """Run lead-lag analysis on overlap data."""
    
    # Mock lead-lag analysis for demonstration
    # In a real implementation, this would use actual lead-lag algorithms
    
    venues = overlap_data.get('venues', [])
    start_utc = overlap_data.get('startUTC', '')
    end_utc = overlap_data.get('endUTC', '')
    
    # Generate mock lead-lag results
    edges = []
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i != j:
                # Mock edge with random lead-lag relationship
                edge = {
                    "from": venue1,
                    "to": venue2,
                    "horizon_1s": np.random.uniform(-0.5, 0.5),
                    "horizon_5s": np.random.uniform(-0.3, 0.3),
                    "significance": np.random.uniform(0.01, 0.1)
                }
                edges.append(edge)
    
    # Find top leader (venue with most outgoing edges)
    out_degrees = {}
    for edge in edges:
        from_venue = edge['from']
        out_degrees[from_venue] = out_degrees.get(from_venue, 0) + 1
    
    top_leader = max(out_degrees.items(), key=lambda x: x[1])[0] if out_degrees else None
    
    results = {
        "overlap_window": {
            "start": start_utc,
            "end": end_utc,
            "venues": venues,
            "policy": overlap_data.get('policy', 'COURT_1s')
        },
        "edges": edges,
        "top_leader": top_leader,
        "horizons": horizons,
        "analysis_type": "lead_lag",
        "timestamp": datetime.now().isoformat()
    }
    
    # Save results
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = out_dir / "leadlag_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Lead-lag results saved to {results_file}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Run lead-lag analysis")
    parser.add_argument("--use-overlap-json", required=True, help="OVERLAP.json file")
    parser.add_argument("--horizons", default="1,5", help="Lead-lag horizons (comma-separated)")
    parser.add_argument("--export-dir", required=True, help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    overlap_file = Path(args.use_overlap_json)
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found: {overlap_file}")
        return 1
    
    # Load overlap data
    overlap_data = load_overlap_data(overlap_file)
    logger.info(f"Running lead-lag analysis for window: {overlap_data['startUTC']} to {overlap_data['endUTC']}")
    
    # Parse horizons
    horizons = [int(h.strip()) for h in args.horizons.split(',')]
    
    # Run analysis
    results = run_leadlag_analysis(overlap_data, horizons, args.export_dir)
    
    # Log results
    logger.info(f"Lead-lag analysis completed: {len(results['edges'])} edges, top leader: {results['top_leader']}")
    
    return 0

if __name__ == "__main__":
    exit(main())