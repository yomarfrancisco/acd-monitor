#!/usr/bin/env python3
"""
Run court diagnostics on overlap windows with substantive flag detection.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def check_substantive_flags(overlap_file, out_dir):
    """Check for substantive flags that indicate court-ready evidence."""
    flags = []
    
    # Load analysis results
    infoshare_file = out_dir / "info_share_results.json"
    spread_file = out_dir / "spread_results.json"
    leadlag_file = out_dir / "leadlag_results.json"
    
    if not all(f.exists() for f in [infoshare_file, spread_file, leadlag_file]):
        logger.error("Missing analysis result files")
        return flags
    
    # Load results
    with open(infoshare_file, 'r') as f:
        infoshare_data = json.load(f)
    
    with open(spread_file, 'r') as f:
        spread_data = json.load(f)
    
    with open(leadlag_file, 'r') as f:
        leadlag_data = json.load(f)
    
    # Flag 1: Spread clustering
    spread_episodes = spread_data.get("episodes", [])
    spread_pval = spread_data.get("permutation_p_value", 1.0)
    window_minutes = infoshare_data.get("overlap_window", {}).get("minutes", 0)
    
    if (spread_pval < 0.01 and 
        len(spread_episodes) >= 3 * (window_minutes / 10) and
        spread_episodes and spread_episodes[0].get("leader") == infoshare_data.get("top_venue")):
        flags.append("spread_clustering")
    
    # Flag 2: Leader persistence
    leadlag_edges = leadlag_data.get("edges", [])
    top_leader = leadlag_data.get("top_leader")
    
    if top_leader:
        out_edges = [e for e in leadlag_edges if e.get("from") == top_leader]
        out_degree_ratio = len(out_edges) / len(leadlag_edges) if leadlag_edges else 0
        
        if out_degree_ratio >= 0.65:
            flags.append("leader_persistence")
    
    # Flag 3: InfoShare concentration
    venue_shares = infoshare_data.get("venue_shares", {})
    top_venue_share = max(venue_shares.values()) if venue_shares else 0
    
    if top_venue_share >= 0.35:
        flags.append("infoshare_concentration")
    
    # Flag 4: Cross-test coherence
    infoshare_top = infoshare_data.get("top_venue")
    spread_top = spread_episodes[0].get("leader") if spread_episodes else None
    leadlag_top = leadlag_data.get("top_leader")
    
    if infoshare_top and spread_top and leadlag_top and infoshare_top == spread_top == leadlag_top:
        flags.append("cross_test_coherence")
    
    return flags

def main():
    parser = argparse.ArgumentParser(description="Run court diagnostics")
    parser.add_argument("--overlap-json", required=True, help="OVERLAP.json file")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--strict", action="store_true", help="Strict court mode")
    parser.add_argument("--permutes", type=int, default=5000, help="Number of permutations")
    parser.add_argument("--no-stitch", action="store_true", help="No micro-gap stitching")
    parser.add_argument("--all5", action="store_true", help="Require all 5 venues")
    parser.add_argument("--real-only", action="store_true", help="Real data only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    overlap_file = Path(args.overlap_json)
    out_dir = Path(args.out_dir)
    
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found: {overlap_file}")
        return 1
    
    # Load overlap data
    with open(overlap_file, 'r') as f:
        overlap_data = json.load(f)
    
    logger.info(f"Running court diagnostics for window: {overlap_data['startUTC']} to {overlap_data['endUTC']}")
    
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Run court bundle validation
    logger.info("Running court bundle validation...")
    validation_cmd = [
        "python", "scripts/validate_court_bundle.py",
        "--overlap-json", str(overlap_file),
        "--out-dir", str(out_dir),
        "--require-all5" if args.all5 else "",
        "--coverage-min", "0.999",
        "--permutes-min", str(args.permutes),
        "--no-stitch" if args.no_stitch else "",
        "--alpha", "0.05",
        "--verbose" if args.verbose else ""
    ]
    # Remove empty arguments
    validation_cmd = [arg for arg in validation_cmd if arg]
    
    result = subprocess.run(validation_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Court bundle validation failed: {result.stderr}")
        return 1
    
    # Generate complete evidence bundle
    logger.info("Generating complete evidence bundle...")
    evidence_cmd = [
        "python", "scripts/build_court_bundle_from_snapshot.py",
        "--snapshot", str(overlap_file.parent),
        "--export-dir", str(out_dir),
        "--permutes", str(args.permutes),
        "--alpha", "0.05",
        "--no-stitch" if args.no_stitch else "",
        "--all5" if args.all5 else "",
        "--verbose" if args.verbose else ""
    ]
    # Remove empty arguments
    evidence_cmd = [arg for arg in evidence_cmd if arg]
    
    result = subprocess.run(evidence_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Evidence bundle generation failed: {result.stderr}")
        return 1
    
    logger.info("Evidence bundle generated successfully")
    
    # Check substantive flags
    logger.info("Checking substantive flags...")
    flags = check_substantive_flags(overlap_file, out_dir)
    
    # Make decision
    if flags:
        decision = "FLAGGED"
        reasons = flags
    else:
        decision = "CLEAR"
        reasons = []
    
    # Get git SHA
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        sha = result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        sha = "unknown"
    
    # Print final decision
    decision_json = {
        "status": decision,
        "reasons": reasons,
        "sha": sha
    }
    
    print(f"[COURT:decision] {json.dumps(decision_json)}")
    
    # If flagged, commit the evidence
    if decision == "FLAGGED":
        logger.info("Court evidence flagged - committing evidence bundle")
        try:
            subprocess.run(["git", "add", str(out_dir)], check=True)
            subprocess.run(["git", "commit", "-m", f"Court evidence: {decision} - {', '.join(reasons)}"], check=True)
            logger.info("Evidence bundle committed successfully")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to commit evidence: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())
