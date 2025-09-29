#!/usr/bin/env python3
"""
Monitor court orchestrator for overlap windows and run diagnostics.
"""

import argparse
import json
import time
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def check_for_new_overlap(overlap_dir):
    """Check for new court-mode overlap windows."""
    overlap_file = Path(overlap_dir) / "OVERLAP.json"
    
    if not overlap_file.exists():
        return None
    
    # Check if this is a court-mode overlap
    with open(overlap_file, 'r') as f:
        overlap_data = json.load(f)
    
    policy = overlap_data.get("policy", "")
    venues = overlap_data.get("venues", [])
    coverage = overlap_data.get("coverage", 0)
    
    # Check if it meets court-mode requirements
    if (policy.startswith("BEST4") or policy.startswith("ALL5")) and len(venues) >= 4 and coverage >= 0.999:
        return overlap_data
    
    return None

def run_court_diagnostics(overlap_data, overlap_dir):
    """Run court diagnostics on detected overlap."""
    # Create snapshot directory
    start_iso = overlap_data["startUTC"].replace(":", "").replace("-", "")
    end_iso = overlap_data["endUTC"].replace(":", "").replace("-", "")
    snapshot_dir = Path("real_data_runs") / f"{start_iso}__{end_iso}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy overlap.json to snapshot
    snapshot_overlap = snapshot_dir / "OVERLAP.json"
    with open(snapshot_overlap, 'w') as f:
        json.dump(overlap_data, f, indent=2)
    
    # Run court diagnostics
    out_dir = snapshot_dir / "court_bundle"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Running court diagnostics on {snapshot_dir}")
    
    cmd = [
        "python", "scripts/run_court_diagnostics.py",
        "--overlap-json", str(snapshot_overlap),
        "--out-dir", str(out_dir),
        "--verbose"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("Court diagnostics completed successfully")
        print(result.stdout)
    else:
        logger.error(f"Court diagnostics failed: {result.stderr}")
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="Monitor court orchestrator")
    parser.add_argument("--overlap-dir", default="exports/overlap", help="Overlap directory")
    parser.add_argument("--check-interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    overlap_dir = Path(args.overlap_dir)
    processed_overlaps = set()
    
    logger.info(f"Monitoring court orchestrator in {overlap_dir}")
    logger.info(f"Check interval: {args.check_interval}s")
    
    try:
        while True:
            # Check for new overlap
            overlap_data = check_for_new_overlap(overlap_dir)
            
            if overlap_data:
                overlap_key = f"{overlap_data['startUTC']}_{overlap_data['endUTC']}"
                
                if overlap_key not in processed_overlaps:
                    logger.info(f"New court-mode overlap detected: {overlap_key}")
                    processed_overlaps.add(overlap_key)
                    
                    # Run court diagnostics
                    success = run_court_diagnostics(overlap_data, overlap_dir)
                    
                    if success:
                        logger.info("Court diagnostics completed successfully")
                    else:
                        logger.error("Court diagnostics failed")
            
            # Wait for next check
            time.sleep(args.check_interval)
            
    except KeyboardInterrupt:
        logger.info("Court orchestrator monitor stopped")
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
