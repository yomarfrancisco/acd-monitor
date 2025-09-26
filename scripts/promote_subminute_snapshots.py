#!/usr/bin/env python3
"""
Promote Sub-Minute Snapshots (15s & 5s)

This script finds and promotes the best 15s and 5s snapshots based on strict criteria.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def find_subminute_snapshots(snapshots_dir: Path, granularity: int, min_duration: float, 
                            min_coverage: float, max_entries: int = 5) -> List[Dict]:
    """
    Find sub-minute snapshots based on strict criteria.
    
    Args:
        snapshots_dir: Path to snapshots directory
        granularity: Target granularity (15 or 5)
        min_duration: Minimum duration in seconds
        min_coverage: Minimum coverage threshold
        max_entries: Maximum entries to return
        
    Returns:
        List of snapshot metadata dictionaries
    """
    logger = logging.getLogger(__name__)
    
    # Find snapshots with target granularity
    pattern = f"*_g{granularity}_*"
    g_snapshots = list(snapshots_dir.glob(pattern))
    logger.info(f"Found {len(g_snapshots)} {granularity}s snapshots")
    
    valid_snapshots = []
    
    for snapshot_dir in g_snapshots:
        try:
            # Check if OVERLAP.json exists
            overlap_file = snapshot_dir / "OVERLAP.json"
            if not overlap_file.exists():
                continue
            
            # Load overlap data
            with open(overlap_file, 'r') as f:
                overlap_data = json.load(f)
            
            # Extract metadata
            duration_minutes = overlap_data.get('duration_minutes', 0)
            duration_seconds = duration_minutes * 60
            venues = overlap_data.get('venues', [])
            policy = overlap_data.get('policy', '')
            coverage = overlap_data.get('coverage', 0.0)
            
            # Check if it's the target granularity
            expected_policy = f"RESEARCH_g={granularity}s"
            if not policy.startswith(expected_policy):
                continue
            
            # Check duration (convert to seconds)
            if duration_seconds < min_duration:
                continue
            
            # Check venue count
            if len(venues) < 5:
                continue
            
            # Check coverage
            if coverage < min_coverage:
                continue
            
            snapshot_info = {
                'snapshot': str(snapshot_dir),
                'minutes': duration_minutes,
                'seconds': duration_seconds,
                'coverage': coverage,
                'venues': venues,
                'policy': policy,
                'timestamp': overlap_data.get('start', ''),
                'end_timestamp': overlap_data.get('end', ''),
                'granularity': granularity
            }
            
            valid_snapshots.append(snapshot_info)
            logger.info(f"Found valid {granularity}s snapshot: {duration_seconds:.0f}s, {len(venues)} venues, coverage={coverage:.3f}")
            
        except Exception as e:
            logger.warning(f"Error processing snapshot {snapshot_dir}: {e}")
            continue
    
    # Sort by duration (descending) and take top entries
    valid_snapshots.sort(key=lambda x: x['seconds'], reverse=True)
    return valid_snapshots[:max_entries]


def clean_snapshot(snapshot_path: str, verbose: bool = False) -> bool:
    """
    Clean a snapshot using the clean_snapshot.py script.
    
    Args:
        snapshot_path: Path to snapshot directory
        verbose: Verbose logging
        
    Returns:
        True if cleaning successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        cmd = [
            sys.executable, 
            "scripts/clean_snapshot.py",
            "--snapshot", snapshot_path
        ]
        if verbose:
            cmd.append("--verbose")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"Cleaning failed for {snapshot_path}: {result.stderr}")
            return False
        
        # Check if any mock/demo files were removed
        if "files_removed=0" in result.stdout:
            logger.info(f"Snapshot {snapshot_path} is clean (no mock/demo files)")
            return True
        else:
            logger.warning(f"Mock/demo files removed from {snapshot_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error cleaning snapshot {snapshot_path}: {e}")
        return False


def build_research_bundle(snapshot_path: str, export_dir: str, granularity: int, verbose: bool = False) -> bool:
    """
    Build research bundle for a snapshot.
    
    Args:
        snapshot_path: Path to snapshot directory
        export_dir: Export directory
        granularity: Granularity (15 or 5)
        verbose: Verbose logging
        
    Returns:
        True if build successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        cmd = [
            sys.executable,
            "scripts/build_research_bundle_from_snapshot.py",
            "--snapshot", snapshot_path,
            "--export-dir", export_dir,
            "--pair", "BTC-USD",
            "--gg-blend-alpha", "0.7",
            "--permutes", "1000"
        ]
        if verbose:
            cmd.append("--verbose")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Bundle build failed for {snapshot_path}: {result.stderr}")
            return False
        
        logger.info(f"Successfully built bundle for {snapshot_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error building bundle for {snapshot_path}: {e}")
        return False


def create_promotion_index(snapshots: List[Dict], granularity: int, export_dir: Path) -> None:
    """
    Create the promotion index file for a granularity.
    
    Args:
        snapshots: List of promoted snapshot metadata
        granularity: Granularity (15 or 5)
        export_dir: Export directory
    """
    logger = logging.getLogger(__name__)
    
    # Get git SHA
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              capture_output=True, text=True)
        git_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        git_sha = "unknown"
    
    # Create promotion index
    promotion_data = []
    for snapshot in snapshots:
        promotion_entry = {
            "snapshot": snapshot['snapshot'],
            "minutes": snapshot['minutes'],
            "coverage": snapshot['coverage'],
            "venues": snapshot['venues'],
            "policy": snapshot['policy'],
            "sha": git_sha,
            "timestamp": snapshot['timestamp'],
            "end_timestamp": snapshot['end_timestamp']
        }
        promotion_data.append(promotion_entry)
    
    # Write promotion index
    promotion_file = export_dir / f"REAL_{granularity}s_PROMOTED.json"
    with open(promotion_file, 'w') as f:
        json.dump(promotion_data, f, indent=2)
    
    logger.info(f"Created promotion index: {promotion_file}")
    print(f"[PROMOTE:{granularity}s] created_index={promotion_file}, entries={len(promotion_data)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Promote sub-minute snapshots")
    parser.add_argument("--snapshots-dir", default="exports/sweep_continuous/snapshots", 
                       help="Snapshots directory")
    parser.add_argument("--export-dir", default="exports/sweep", help="Export directory")
    parser.add_argument("--granularity", type=int, choices=[15, 5], required=True,
                       help="Target granularity (15 or 5)")
    parser.add_argument("--min-duration", type=float, default=90.0,
                       help="Minimum duration in seconds (default: 90s for 15s, 60s for 5s)")
    parser.add_argument("--min-coverage", type=float, default=0.96,
                       help="Minimum coverage threshold")
    parser.add_argument("--max-entries", type=int, default=5,
                       help="Maximum entries to promote")
    parser.add_argument("--build-bundles", action="store_true",
                       help="Build research bundles for promoted snapshots")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Set default min duration based on granularity
    if args.granularity == 15 and args.min_duration == 90.0:
        args.min_duration = 90.0  # 1.5 minutes
    elif args.granularity == 5 and args.min_duration == 90.0:
        args.min_duration = 60.0  # 1 minute
    
    # Set default coverage based on granularity
    if args.granularity == 15 and args.min_coverage == 0.96:
        args.min_coverage = 0.96
    elif args.granularity == 5 and args.min_coverage == 0.96:
        args.min_coverage = 0.97
    
    # Create export directory
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting {args.granularity}s snapshot promotion")
    logger.info(f"Min duration: {args.min_duration}s")
    logger.info(f"Min coverage: {args.min_coverage}")
    
    # Find sub-minute snapshots
    snapshots_dir = Path(args.snapshots_dir)
    if not snapshots_dir.exists():
        logger.error(f"Snapshots directory not found: {snapshots_dir}")
        sys.exit(1)
    
    valid_snapshots = find_subminute_snapshots(
        snapshots_dir, 
        args.granularity, 
        args.min_duration, 
        args.min_coverage,
        args.max_entries
    )
    
    if not valid_snapshots:
        logger.error(f"No valid {args.granularity}s snapshots found")
        sys.exit(1)
    
    logger.info(f"Found {len(valid_snapshots)} valid {args.granularity}s snapshots")
    
    # Process snapshots
    promoted_snapshots = []
    for i, snapshot in enumerate(valid_snapshots):
        logger.info(f"Processing snapshot {i+1}/{len(valid_snapshots)}: {snapshot['snapshot']}")
        
        # Clean snapshot (skip if no ticks directory)
        ticks_dir = Path(snapshot['snapshot']) / "ticks"
        if ticks_dir.exists():
            if not clean_snapshot(snapshot['snapshot'], args.verbose):
                logger.error(f"Failed to clean snapshot: {snapshot['snapshot']}")
                continue
        else:
            logger.info(f"No ticks directory found, skipping cleaning for: {snapshot['snapshot']}")
        
        # Build bundle if requested
        if args.build_bundles:
            bundle_dir = export_dir / f"promoted_{args.granularity}s_{i+1}"
            bundle_dir.mkdir(exist_ok=True)
            
            if not build_research_bundle(snapshot['snapshot'], str(bundle_dir), args.granularity, args.verbose):
                logger.error(f"Failed to build bundle for: {snapshot['snapshot']}")
                continue
        
        promoted_snapshots.append(snapshot)
        logger.info(f"Successfully promoted snapshot {i+1}")
    
    if not promoted_snapshots:
        logger.error("No snapshots were successfully promoted")
        sys.exit(1)
    
    # Create promotion index
    create_promotion_index(promoted_snapshots, args.granularity, export_dir)
    
    logger.info(f"Promotion completed: {len(promoted_snapshots)} {args.granularity}s snapshots promoted")


if __name__ == "__main__":
    main()
