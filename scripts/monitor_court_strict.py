#!/usr/bin/env python3
"""
Monitor for court-mode strict overlaps and trigger diagnostics automatically.
"""

import argparse
import json
import time
import subprocess
import sys
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def check_for_strict_overlap(overlap_dir):
    """Check for strict court-mode overlap (ALL5, coverage≥0.999)."""
    overlap_file = Path(overlap_dir) / "OVERLAP.json"
    
    if not overlap_file.exists():
        return None
    
    try:
        with open(overlap_file, 'r') as f:
            overlap_data = json.load(f)
        
        venues = overlap_data.get("venues", [])
        coverage = overlap_data.get("coverage", 0)
        policy = overlap_data.get("policy", "")
        
        # Check strict court requirements
        if (len(venues) == 5 and 
            coverage >= 0.999 and 
            (policy.startswith("ALL5") or policy.startswith("BEST4"))):
            return overlap_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error reading overlap file: {e}")
        return None

def run_court_diagnostics(overlap_data, overlap_file, timestamp):
    """Run court diagnostics on detected overlap."""
    # Create output directory with timestamp
    out_dir = Path("exports") / f"court_diag_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Running court diagnostics on {out_dir}")
    
    # Run court diagnostics with strict settings
    cmd = [
        "python", "scripts/run_court_diagnostics.py",
        "--overlap-json", str(overlap_file),
        "--out-dir", str(out_dir),
        "--strict",
        "--permutes", "5000",
        "--no-stitch",
        "--all5",
        "--real-only",
        "--verbose"
    ]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("Court diagnostics completed successfully")
        print(result.stdout)
        
        # Check for [COURT:decision] in output
        if "[COURT:decision]" in result.stdout:
            print(f"\n=== COURT DIAGNOSTICS COMPLETED ===")
            print(f"Results saved to: {out_dir}")
            print(f"Decision: {result.stdout.split('[COURT:decision]')[-1].strip()}")
        
        return True
    else:
        logger.error(f"Court diagnostics failed: {result.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Monitor for strict court overlaps")
    parser.add_argument("--overlap-dir", default="exports/overlap", help="Overlap directory")
    parser.add_argument("--check-interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    overlap_dir = Path(args.overlap_dir)
    processed_overlaps = set()
    
    logger.info(f"Monitoring for strict court overlaps in {overlap_dir}")
    logger.info(f"Requirements: ALL5 venues, coverage≥0.999, court policies")
    logger.info(f"Check interval: {args.check_interval}s")
    
    try:
        while True:
            # Check for strict overlap
            overlap_data = check_for_strict_overlap(overlap_dir)
            
            if overlap_data:
                overlap_key = f"{overlap_data['startUTC']}_{overlap_data['endUTC']}"
                
                if overlap_key not in processed_overlaps:
                    logger.info(f"Strict court overlap detected: {overlap_key}")
                    logger.info(f"Venues: {overlap_data.get('venues', [])}")
                    logger.info(f"Coverage: {overlap_data.get('coverage', 0)}")
                    logger.info(f"Policy: {overlap_data.get('policy', '')}")
                    
                    processed_overlaps.add(overlap_key)
                    
                    # Create timestamp for output directory
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Run court diagnostics
                    success = run_court_diagnostics(
                        overlap_data, 
                        overlap_dir / "OVERLAP.json", 
                        timestamp
                    )
                    
                    if success:
                        logger.info("Court diagnostics completed successfully")
                        print(f"\n[OVERLAP:FOUND] Strict court overlap detected and analyzed")
                        print(f"Results: exports/court_diag_{timestamp}/")
                    else:
                        logger.error("Court diagnostics failed")
            
            # Wait for next check
            time.sleep(args.check_interval)
            
    except KeyboardInterrupt:
        logger.info("Court strict monitor stopped")
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
