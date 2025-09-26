#!/usr/bin/env python3
"""
Snapshot Decontamination Script

This script scans a snapshot directory for mock/demo parquet files and removes them
to ensure only real data is used for analysis.
"""

import argparse
import logging
import sys
from pathlib import Path
import os

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def clean_snapshot(snapshot_dir: str, verbose: bool = False):
    """
    Clean snapshot directory of mock/demo parquet files.
    
    Args:
        snapshot_dir: Path to snapshot directory
        verbose: Verbose logging
    """
    logger = logging.getLogger(__name__)
    
    snapshot_path = Path(snapshot_dir)
    if not snapshot_path.exists():
        logger.error(f"Snapshot directory not found: {snapshot_dir}")
        sys.exit(1)
    
    ticks_dir = snapshot_path / "ticks"
    if not ticks_dir.exists():
        logger.error(f"Ticks directory not found: {ticks_dir}")
        sys.exit(1)
    
    logger.info(f"Cleaning snapshot: {snapshot_dir}")
    
    # Track venues and their parquet files
    venue_files = {}
    removed_files = []
    
    # Scan for parquet files
    for parquet_file in ticks_dir.rglob("*.parquet"):
        venue = parquet_file.parent.name
        if venue not in venue_files:
            venue_files[venue] = []
        
        # Check for mock/demo indicators
        file_name = parquet_file.name.lower()
        file_path = str(parquet_file).lower()
        
        should_remove = False
        reason = ""
        
        if "mock" in file_name or "mock" in file_path:
            should_remove = True
            reason = "contains 'mock'"
        elif "_demo" in file_name or "_demo" in file_path:
            should_remove = True
            reason = "contains '_demo'"
        elif parquet_file.stat().st_size == 0:
            should_remove = True
            reason = "zero-length file"
        
        if should_remove:
            logger.warning(f"[CLEAN:removed] {parquet_file} - {reason}")
            print(f"[CLEAN:removed] {parquet_file} - {reason}")
            parquet_file.unlink()
            removed_files.append(str(parquet_file))
        else:
            venue_files[venue].append(parquet_file)
    
    # Check for empty venues
    empty_venues = []
    for venue, files in venue_files.items():
        if not files:
            empty_venues.append(venue)
            logger.error(f"[ABORT:snapshot:empty] {venue} - no valid parquet files found")
            print(f"[ABORT:snapshot:empty] {venue} - no valid parquet files found")
    
    if empty_venues:
        logger.error(f"Aborting: {len(empty_venues)} venues have no valid parquet files")
        sys.exit(1)
    
    # Summary
    total_venues = len(venue_files)
    total_files = sum(len(files) for files in venue_files.values())
    total_removed = len(removed_files)
    
    logger.info(f"Cleaning complete: {total_venues} venues, {total_files} files kept, {total_removed} files removed")
    print(f"[CLEAN:summary] venues={total_venues}, files_kept={total_files}, files_removed={total_removed}")
    
    if removed_files:
        print(f"[CLEAN:removed_files] {removed_files}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean snapshot directory of mock/demo files")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Clean snapshot
    clean_snapshot(args.snapshot, args.verbose)


if __name__ == "__main__":
    main()
