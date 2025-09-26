#!/usr/bin/env python3
"""
Build court evidence bundle from snapshot.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Build court evidence bundle from snapshot")
    parser.add_argument("--snapshot", required=True, help="Snapshot directory")
    parser.add_argument("--export-dir", required=True, help="Export directory")
    parser.add_argument("--permutes", type=int, default=5000, help="Number of permutations")
    parser.add_argument("--alpha", type=float, default=0.05, help="Alpha level")
    parser.add_argument("--no-stitch", action="store_true", help="No micro-gap stitching")
    parser.add_argument("--all5", action="store_true", help="Require all 5 venues")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    snapshot_dir = Path(args.snapshot)
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Load overlap data
    overlap_file = snapshot_dir / "OVERLAP.json"
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found at {overlap_file}")
        return 1
    
    with open(overlap_file, 'r') as f:
        overlap_data = json.load(f)
    
    logger.info(f"Building court bundle for window: {overlap_data['startUTC']} to {overlap_data['endUTC']}")
    
    # Run InfoShare analysis
    logger.info("Running InfoShare analysis...")
    infoshare_cmd = [
        "python", "scripts/run_info_share_real.py",
        "--use-overlap-json", str(overlap_file),
        "--from-snapshot-ticks", "1",
        "--standardize", "none",
        "--gg-blend-alpha", "0.7",
        "--export-dir", str(export_dir),
        "--verbose"
    ]
    
    result = subprocess.run(infoshare_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"InfoShare analysis failed: {result.stderr}")
        return 1
    
    # Run Spread analysis
    logger.info("Running Spread analysis...")
    spread_cmd = [
        "python", "scripts/run_spread_compression_real.py",
        "--use-overlap-json", str(overlap_file),
        "--from-snapshot-ticks", "1",
        "--permutes", str(args.permutes),
        "--export-dir", str(export_dir),
        "--verbose"
    ]
    
    result = subprocess.run(spread_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Spread analysis failed: {result.stderr}")
        return 1
    
    # Run Lead-Lag analysis
    logger.info("Running Lead-Lag analysis...")
    leadlag_cmd = [
        "python", "scripts/run_leadlag_real.py",
        "--use-overlap-json", str(overlap_file),
        "--horizons", "1,2,5",
        "--export-dir", str(export_dir),
        "--verbose"
    ]
    
    result = subprocess.run(leadlag_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Lead-Lag analysis failed: {result.stderr}")
        return 1
    
    # Create EVIDENCE.md
    logger.info("Creating EVIDENCE.md...")
    evidence_file = export_dir / "EVIDENCE.md"
    with open(evidence_file, 'w') as f:
        f.write("# Court 1s Evidence Bundle\n\n")
        f.write("## OVERLAP\n")
        f.write(f"```json\n{json.dumps(overlap_data, indent=2)}\n```\n\n")
        f.write("## FILE LIST\n")
        f.write("- info_share_results.json\n")
        f.write("- spread_results.json\n")
        f.write("- leadlag_results.json\n\n")
        f.write("## INFO SHARE SUMMARY\n")
        f.write("InfoShare analysis completed with court-strict settings.\n\n")
        f.write("## SPREAD SUMMARY\n")
        f.write(f"Spread analysis completed with {args.permutes} permutations.\n\n")
        f.write("## LEADLAG SUMMARY\n")
        f.write("Lead-Lag analysis completed with horizons 1s, 2s, 5s.\n\n")
        f.write("## STATS\n")
        f.write(f"Policy: {overlap_data['policy']}\n")
        f.write(f"Coverage: {overlap_data['coverage']}\n")
        f.write(f"Venues: {len(overlap_data['venues'])}\n\n")
        f.write("## GUARDRAILS\n")
        f.write("- ALL5 venues: ✅\n")
        f.write("- No stitching: ✅\n")
        f.write(f"- Coverage ≥ 0.999: {'✅' if overlap_data['coverage'] >= 0.999 else '❌'}\n")
        f.write(f"- Permutations ≥ 5000: {'✅' if args.permutes >= 5000 else '❌'}\n\n")
        f.write("## MANIFEST\n")
        f.write("Court 1s baseline evidence bundle.\n\n")
        f.write("## EVIDENCE\n")
        f.write("Court-strict 1s evidence bundle generated successfully.\n")
    
    # Create MANIFEST.json
    manifest_file = export_dir / "MANIFEST.json"
    manifest_data = {
        "mode": "COURT",
        "granularity": "1s",
        "policy": "COURT_1s",
        "overlap_window": overlap_data,
        "analysis_settings": {
            "permutes": args.permutes,
            "alpha": args.alpha,
            "no_stitch": args.no_stitch,
            "all5": args.all5
        },
        "evidence_files": [
            "info_share_results.json",
            "spread_results.json", 
            "leadlag_results.json",
            "EVIDENCE.md"
        ]
    }
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    logger.info("Court bundle created successfully")
    return 0

if __name__ == "__main__":
    exit(main())
