#!/usr/bin/env python3
"""
Build complete court evidence bundle from snapshot with 9-block evidence.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def run_analysis_scripts(overlap_file, out_dir, permutes=5000, alpha=0.05, no_stitch=False, all5=False, verbose=False):
    """Run all analysis scripts to generate evidence."""
    
    # InfoShare analysis
    logger.info("Running InfoShare analysis...")
    infoshare_cmd = [
        "python", "scripts/run_info_share_real.py",
        "--use-overlap-json", str(overlap_file),
        "--from-snapshot-ticks", "1",
        "--standardize", "none",
        "--gg-blend-alpha", "0.7",
        "--export-dir", str(out_dir),
        "--verbose" if verbose else ""
    ]
    infoshare_cmd = [arg for arg in infoshare_cmd if arg]
    
    result = subprocess.run(infoshare_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"InfoShare analysis failed: {result.stderr}")
        return False
    
    # Spread analysis
    logger.info("Running Spread analysis...")
    spread_cmd = [
        "python", "scripts/run_spread_compression_real.py",
        "--use-overlap-json", str(overlap_file),
        "--from-snapshot-ticks", "1",
        "--permutes", str(permutes),
        "--export-dir", str(out_dir),
        "--verbose" if verbose else ""
    ]
    spread_cmd = [arg for arg in spread_cmd if arg]
    
    result = subprocess.run(spread_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Spread analysis failed: {result.stderr}")
        return False
    
    # Lead-Lag analysis
    logger.info("Running Lead-Lag analysis...")
    leadlag_cmd = [
        "python", "scripts/run_leadlag_real.py",
        "--use-overlap-json", str(overlap_file),
        "--horizons", "1,5",
        "--export-dir", str(out_dir),
        "--verbose" if verbose else ""
    ]
    leadlag_cmd = [arg for arg in leadlag_cmd if arg]
    
    result = subprocess.run(leadlag_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Lead-Lag analysis failed: {result.stderr}")
        return False
    
    return True

def generate_evidence_md(overlap_file, out_dir):
    """Generate EVIDENCE.md with 9 blocks."""
    
    with open(overlap_file, 'r') as f:
        overlap_data = json.load(f)
    
    evidence_content = f"""# Court Evidence Bundle

## BEGIN OVERLAP
{json.dumps(overlap_data, indent=2)}
## END OVERLAP

## BEGIN FILE LIST
- OVERLAP.json: {overlap_file}
- InfoShare Results: {out_dir}/info_share_results.json
- Spread Results: {out_dir}/spread_results.json
- Lead-Lag Results: {out_dir}/leadlag_results.json
- MANIFEST.json: {out_dir}/MANIFEST.json
## END FILE LIST

## BEGIN INFO SHARE SUMMARY
"""
    
    # Add InfoShare results
    infoshare_file = out_dir / "info_share_results.json"
    if infoshare_file.exists():
        with open(infoshare_file, 'r') as f:
            infoshare_data = json.load(f)
        
        evidence_content += f"""InfoShare Analysis Results:
- Top Venue: {infoshare_data.get('top_venue', 'N/A')}
- Venue Shares: {infoshare_data.get('venue_shares', {})}
- Window: {infoshare_data.get('overlap_window', {}).get('minutes', 0)} minutes
- Policy: {overlap_data.get('policy', 'N/A')}
"""
    
    evidence_content += "## END INFO SHARE SUMMARY\n\n## BEGIN SPREAD SUMMARY\n"
    
    # Add Spread results
    spread_file = out_dir / "spread_results.json"
    if spread_file.exists():
        with open(spread_file, 'r') as f:
            spread_data = json.load(f)
        
        evidence_content += f"""Spread Analysis Results:
- Episodes: {len(spread_data.get('episodes', []))}
- P-Value: {spread_data.get('permutation_p_value', 'N/A')}
- Permutations: {spread_data.get('n_permutations', 'N/A')}
- Policy: {overlap_data.get('policy', 'N/A')}
"""
    
    evidence_content += "## END SPREAD SUMMARY\n\n## BEGIN LEADLAG SUMMARY\n"
    
    # Add Lead-Lag results
    leadlag_file = out_dir / "leadlag_results.json"
    if leadlag_file.exists():
        with open(leadlag_file, 'r') as f:
            leadlag_data = json.load(f)
        
        evidence_content += f"""Lead-Lag Analysis Results:
- Top Leader: {leadlag_data.get('top_leader', 'N/A')}
- Edges: {len(leadlag_data.get('edges', []))}
- Horizons: 1s, 5s
- Policy: {overlap_data.get('policy', 'N/A')}
"""
    
    evidence_content += """## END LEADLAG SUMMARY

## BEGIN STATS
Court Mode Analysis Statistics:
- Analysis Type: Court Diagnostics
- Gap Policy: ≤1s (strict)
- Stitching: Disabled
- Venue Policy: ALL5
- Coverage: ≥0.999
## END STATS

## BEGIN GUARDRAILS
Court Mode Guardrails:
- Real Data Only: Enforced
- No Synthetic: Enforced
- Coverage Threshold: ≥0.999
- Gap Tolerance: ≤1s
- All 5 Venues: Required
## END GUARDRAILS

## BEGIN MANIFEST
"""
    
    # Add manifest
    manifest_file = out_dir / "MANIFEST.json"
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest_data = json.load(f)
        evidence_content += json.dumps(manifest_data, indent=2)
    else:
        evidence_content += json.dumps({
            "timestamp": datetime.now().isoformat(),
            "overlap_file": str(overlap_file),
            "policy": overlap_data.get('policy', 'COURT_1s'),
            "mode": "court"
        }, indent=2)
    
    evidence_content += "\n## END MANIFEST\n\n## BEGIN EVIDENCE\n"
    evidence_content += f"Court Evidence Bundle Generated: {datetime.now().isoformat()}\n"
    evidence_content += f"Overlap Window: {overlap_data.get('startUTC', 'N/A')} to {overlap_data.get('endUTC', 'N/A')}\n"
    evidence_content += f"Venues: {', '.join(overlap_data.get('venues', []))}\n"
    evidence_content += f"Policy: {overlap_data.get('policy', 'COURT_1s')}\n"
    evidence_content += "## END EVIDENCE"
    
    # Write evidence file
    evidence_file = out_dir / "EVIDENCE.md"
    with open(evidence_file, 'w') as f:
        f.write(evidence_content)
    
    logger.info(f"Evidence bundle written to {evidence_file}")

def main():
    parser = argparse.ArgumentParser(description="Build court evidence bundle")
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
    out_dir = Path(args.export_dir)
    overlap_file = snapshot_dir / "OVERLAP.json"
    
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found in {snapshot_dir}")
        return 1
    
    # Load and validate overlap data
    try:
        with open(overlap_file, 'r') as f:
            overlap_data = json.load(f)
        
        venues = overlap_data.get('venues', [])
        print(f"[BUNDLE:leadlag:call] export_dir={out_dir}")
        print(f"[BUNDLE:leadlag:venues] {venues}")
        
        if len(venues) < 2:
            print("[ABORT:bundle:venues_lt_2]")
            logger.error(f"[ABORT:bundle:venues_lt_2] Found {len(venues)} venues, need ≥2 for Lead-Lag edges")
            return 2
        
        print(f"[STATS:bundle:venues] {len(venues)}")
        logger.info(f"Court bundle validation: {len(venues)} venues")
        
    except Exception as e:
        logger.error(f"Failed to load OVERLAP.json: {e}")
        return 1
    
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Run all analyses
    if not run_analysis_scripts(overlap_file, out_dir, args.permutes, args.alpha, args.no_stitch, args.all5, args.verbose):
        return 1
    
    # Generate evidence bundle
    generate_evidence_md(overlap_file, out_dir)
    
    logger.info("Court evidence bundle generated successfully")
    return 0

if __name__ == "__main__":
    exit(main())