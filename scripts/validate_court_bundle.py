#!/usr/bin/env python3
"""
Validate court bundle for compliance.
"""

import argparse
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Validate court bundle")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory")
    parser.add_argument("--strict", action="store_true", help="Strict validation")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    bundle_dir = Path(args.bundle_dir)
    
    if not bundle_dir.exists():
        logger.error(f"Bundle directory not found: {bundle_dir}")
        return 1
    
    # Check required files
    required_files = [
        "EVIDENCE.md",
        "MANIFEST.json",
        "info_share_results.json",
        "spread_results.json",
        "leadlag_results.json"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = bundle_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return 1
    
    # Validate MANIFEST.json
    manifest_file = bundle_dir / "MANIFEST.json"
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    # Check policy
    if manifest.get("policy") != "COURT_1s":
        logger.error(f"Invalid policy: {manifest.get('policy')}")
        return 1
    
    # Check coverage
    overlap_window = manifest.get("overlap_window", {})
    coverage = overlap_window.get("coverage", 0)
    if coverage < 0.999:
        logger.error(f"Coverage too low: {coverage} < 0.999")
        return 1
    
    # Check venues
    venues = overlap_window.get("venues", [])
    if len(venues) != 5:
        logger.error(f"Invalid venue count: {len(venues)} != 5")
        return 1
    
    # Check analysis settings
    analysis_settings = manifest.get("analysis_settings", {})
    if analysis_settings.get("permutes", 0) < 5000:
        logger.error(f"Permutations too low: {analysis_settings.get('permutes')} < 5000")
        return 1
    
    if not analysis_settings.get("no_stitch", False):
        logger.error("Micro-gap stitching not disabled")
        return 1
    
    if not analysis_settings.get("all5", False):
        logger.error("ALL5 policy not enforced")
        return 1
    
    # Check evidence files for consistency
    for file_name in ["info_share_results.json", "spread_results.json", "leadlag_results.json"]:
        file_path = bundle_dir / file_name
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check overlap window consistency
        file_overlap = data.get("overlap_window", {})
        if file_overlap.get("startUTC") != overlap_window.get("startUTC"):
            logger.error(f"Inconsistent startUTC in {file_name}")
            return 1
        
        if file_overlap.get("endUTC") != overlap_window.get("endUTC"):
            logger.error(f"Inconsistent endUTC in {file_name}")
            return 1
    
    logger.info("Court bundle validation passed")
    return 0

if __name__ == "__main__":
    exit(main())
