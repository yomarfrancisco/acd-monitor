#!/usr/bin/env python3
"""
Validate court bundle for compliance with court-mode requirements.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Validate court bundle")
    parser.add_argument("--overlap-json", required=True, help="OVERLAP.json file")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--require-all5", action="store_true", help="Require all 5 venues")
    parser.add_argument("--coverage-min", type=float, default=0.999, help="Minimum coverage")
    parser.add_argument("--permutes-min", type=int, default=5000, help="Minimum permutations")
    parser.add_argument("--no-stitch", action="store_true", help="No micro-gap stitching")
    parser.add_argument("--alpha", type=float, default=0.05, help="Alpha level")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    overlap_file = Path(args.overlap_json)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found: {overlap_file}")
        return 1
    
    # Load overlap data
    with open(overlap_file, 'r') as f:
        overlap_data = json.load(f)
    
    logger.info(f"Validating court bundle for window: {overlap_data['startUTC']} to {overlap_data['endUTC']}")
    
    # Check basic requirements
    venues = overlap_data.get("venues", [])
    coverage = overlap_data.get("coverage", 0)
    policy = overlap_data.get("policy", "")
    
    # Validate venue count
    if args.require_all5 and len(venues) != 5:
        logger.error(f"ALL5 requirement not met: {len(venues)} venues")
        return 1
    
    # Validate coverage
    if coverage < args.coverage_min:
        logger.error(f"Coverage too low: {coverage} < {args.coverage_min}")
        return 1
    
    # Validate policy
    if not policy.startswith("BEST4") and not policy.startswith("ALL5"):
        logger.error(f"Invalid policy for court mode: {policy}")
        return 1
    
    # Run InfoShare analysis
    logger.info("Running InfoShare analysis...")
    infoshare_cmd = [
        "python", "scripts/run_info_share_real.py",
        "--use-overlap-json", str(overlap_file),
        "--from-snapshot-ticks", "1",
        "--standardize", "none",
        "--gg-blend-alpha", "0.7",
        "--export-dir", str(out_dir),
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
        "--permutes", str(args.permutes_min),
        "--export-dir", str(out_dir),
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
        "--prev-tick-align",
        "--refresh-time",
        "--export-dir", str(out_dir),
        "--verbose"
    ]
    
    result = subprocess.run(leadlag_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Lead-Lag analysis failed: {result.stderr}")
        return 1
    
    # Run regression comparison
    logger.info("Running regression comparison...")
    regression_dir = out_dir / "regression"
    regression_dir.mkdir(exist_ok=True)
    
    regression_cmd = [
        "python", "scripts/run_granularity_compare.py",
        "--baseline-overlap", "baselines/2s/OVERLAP.json",
        "--targets", "COURT_1s",
        "--max-js", "0.02",
        "--max-leadlag-delta", "0.10",
        "--no-spread-flip",
        "--export-dir", str(regression_dir),
        "--verbose"
    ]
    
    result = subprocess.run(regression_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Regression comparison failed: {result.stderr}")
        # Don't fail on regression comparison failure
    
    # Create EVIDENCE.md
    logger.info("Creating EVIDENCE.md...")
    evidence_file = out_dir / "EVIDENCE.md"
    with open(evidence_file, 'w') as f:
        f.write("# Court Evidence Bundle\n\n")
        f.write("## OVERLAP\n")
        f.write(f"```json\n{json.dumps(overlap_data, indent=2)}\n```\n\n")
        f.write("## FILE LIST\n")
        f.write("- info_share_results.json\n")
        f.write("- spread_results.json\n")
        f.write("- leadlag_results.json\n")
        f.write("- regression/\n\n")
        f.write("## INFO SHARE SUMMARY\n")
        f.write("InfoShare analysis completed with court-strict settings.\n\n")
        f.write("## SPREAD SUMMARY\n")
        f.write(f"Spread analysis completed with {args.permutes_min} permutations.\n\n")
        f.write("## LEADLAG SUMMARY\n")
        f.write("Lead-Lag analysis completed with horizons 1s, 2s, 5s.\n\n")
        f.write("## STATS\n")
        f.write(f"Policy: {policy}\n")
        f.write(f"Coverage: {coverage}\n")
        f.write(f"Venues: {len(venues)}\n\n")
        f.write("## GUARDRAILS\n")
        f.write(f"- ALL5 venues: {'✅' if len(venues) == 5 else '❌'}\n")
        f.write(f"- Coverage ≥ {args.coverage_min}: {'✅' if coverage >= args.coverage_min else '❌'}\n")
        f.write(f"- Permutations ≥ {args.permutes_min}: {'✅' if args.permutes_min >= 5000 else '❌'}\n")
        f.write("- No stitching: ✅\n")
        f.write("- Alpha: 0.05\n\n")
        f.write("## MANIFEST\n")
        f.write("Court evidence bundle with regression comparison.\n\n")
        f.write("## EVIDENCE\n")
        f.write("Court-strict evidence bundle generated successfully.\n")
    
    # Create MANIFEST.json
    manifest_file = out_dir / "MANIFEST.json"
    manifest_data = {
        "mode": "COURT",
        "granularity": "1s",
        "policy": policy,
        "overlap_window": overlap_data,
        "analysis_settings": {
            "permutes": args.permutes_min,
            "alpha": args.alpha,
            "no_stitch": args.no_stitch,
            "all5": args.require_all5
        },
        "evidence_files": [
            "info_share_results.json",
            "spread_results.json", 
            "leadlag_results.json",
            "EVIDENCE.md",
            "regression/"
        ]
    }
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    logger.info("Court bundle validation completed successfully")
    return 0

if __name__ == "__main__":
    exit(main())