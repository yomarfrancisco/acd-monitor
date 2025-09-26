#!/usr/bin/env python3
"""
Snapshot copy utility for court baseline promotion.
"""

import argparse
import shutil
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Copy snapshot ticks to court baseline")
    parser.add_argument("--from-snapshot", required=True, help="Source snapshot directory")
    parser.add_argument("--to", required=True, help="Target directory")
    parser.add_argument("--strict", action="store_true", help="Strict mode - fail on any issues")
    parser.add_argument("--echo", action="store_true", help="Echo operations")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    source_dir = Path(args.from_snapshot)
    target_dir = Path(args.to)
    
    if not source_dir.exists():
        logger.error(f"Source snapshot directory not found: {source_dir}")
        return 1
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy ticks directory
    source_ticks = source_dir / "ticks"
    target_ticks = target_dir / "ticks"
    
    if source_ticks.exists():
        if args.echo:
            print(f"Copying {source_ticks} to {target_ticks}")
        shutil.copytree(source_ticks, target_ticks, dirs_exist_ok=True)
        logger.info(f"Copied ticks from {source_ticks} to {target_ticks}")
    else:
        logger.warning(f"No ticks directory found at {source_ticks}")
        if args.strict:
            return 1
    
    # Copy MANIFEST.json if it exists
    source_manifest = source_dir / "MANIFEST.json"
    target_manifest = target_dir / "MANIFEST.json"
    
    if source_manifest.exists():
        if args.echo:
            print(f"Copying {source_manifest} to {target_manifest}")
        shutil.copy2(source_manifest, target_manifest)
        logger.info(f"Copied manifest from {source_manifest} to {target_manifest}")
    
    logger.info("Snapshot copy completed successfully")
    return 0

if __name__ == "__main__":
    exit(main())
