#!/usr/bin/env python3
"""
Promote Best 30s Snapshots

This script finds the best real 30s snapshots, cleans them, and rebuilds bundles.
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


def find_best_30s_snapshots(snapshots_dir: Path, min_duration: float = 8.0, min_coverage: float = 0.95) -> List[Dict]:
    """
    Find the best 30s snapshots based on duration and coverage.
    
    Args:
        snapshots_dir: Path to snapshots directory
        min_duration: Minimum duration in minutes
        min_coverage: Minimum coverage threshold
        
    Returns:
        List of snapshot metadata dictionaries
    """
    logger = logging.getLogger(__name__)
    
    # Find all 30s snapshots
    g30_snapshots = list(snapshots_dir.glob("sweep_loop_*_g30_*"))
    logger.info(f"Found {len(g30_snapshots)} 30s snapshots")
    
    best_snapshots = []
    
    for snapshot_dir in g30_snapshots:
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
            venues = overlap_data.get('venues', [])
            policy = overlap_data.get('policy', '')
            
            # Check if it's a real 30s snapshot
            if not policy.startswith('RESEARCH_g=30s'):
                continue
            
            # Check duration and venue count
            if duration_minutes < min_duration:
                continue
            
            if len(venues) < 5:
                continue
            
            # Get coverage from snapshot data
            coverage = overlap_data.get('coverage', 0.95)
            
            snapshot_info = {
                'snapshot': str(snapshot_dir),
                'minutes': duration_minutes,
                'coverage': coverage,
                'venues': venues,
                'policy': policy,
                'timestamp': overlap_data.get('start', ''),
                'end_timestamp': overlap_data.get('end', '')
            }
            
            best_snapshots.append(snapshot_info)
            logger.info(f"Found valid 30s snapshot: {duration_minutes:.1f}m, {len(venues)} venues")
            
        except Exception as e:
            logger.warning(f"Error processing snapshot {snapshot_dir}: {e}")
            continue
    
    # Sort by duration (descending) and take top 3
    best_snapshots.sort(key=lambda x: x['minutes'], reverse=True)
    return best_snapshots[:3]


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


def rebuild_bundle(snapshot_path: str, export_dir: str, verbose: bool = False) -> bool:
    """
    Rebuild evidence bundle for a snapshot.
    
    Args:
        snapshot_path: Path to snapshot directory
        export_dir: Export directory
        verbose: Verbose logging
        
    Returns:
        True if rebuild successful, False otherwise
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
            logger.error(f"Bundle rebuild failed for {snapshot_path}: {result.stderr}")
            return False
        
        logger.info(f"Successfully rebuilt bundle for {snapshot_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding bundle for {snapshot_path}: {e}")
        return False


def create_promotion_index(snapshots: List[Dict], export_dir: Path) -> None:
    """
    Create the REAL_30s_PROMOTED.json index file.
    
    Args:
        snapshots: List of promoted snapshot metadata
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
            "sha": git_sha,
            "timestamp": snapshot['timestamp'],
            "end_timestamp": snapshot['end_timestamp']
        }
        promotion_data.append(promotion_entry)
    
    # Write promotion index
    promotion_file = export_dir / "REAL_30s_PROMOTED.json"
    with open(promotion_file, 'w') as f:
        json.dump(promotion_data, f, indent=2)
    
    logger.info(f"Created promotion index: {promotion_file}")
    print(f"[PROMOTE:30s] created_index={promotion_file}, entries={len(promotion_data)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Promote best 30s snapshots")
    parser.add_argument("--snapshots-dir", default="exports/sweep_continuous/snapshots", 
                       help="Snapshots directory")
    parser.add_argument("--export-dir", default="exports/sweep", help="Export directory")
    parser.add_argument("--min-duration", type=float, default=8.0, 
                       help="Minimum duration in minutes")
    parser.add_argument("--min-coverage", type=float, default=0.95, 
                       help="Minimum coverage threshold")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Create export directory
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting 30s snapshot promotion")
    
    # Find best 30s snapshots
    snapshots_dir = Path(args.snapshots_dir)
    if not snapshots_dir.exists():
        logger.error(f"Snapshots directory not found: {snapshots_dir}")
        sys.exit(1)
    
    best_snapshots = find_best_30s_snapshots(
        snapshots_dir, 
        args.min_duration, 
        args.min_coverage
    )
    
    if not best_snapshots:
        logger.error("No valid 30s snapshots found")
        sys.exit(1)
    
    logger.info(f"Found {len(best_snapshots)} best 30s snapshots")
    
    # Process each snapshot
    promoted_snapshots = []
    for i, snapshot in enumerate(best_snapshots):
        logger.info(f"Processing snapshot {i+1}/{len(best_snapshots)}: {snapshot['snapshot']}")
        
        # Clean snapshot
        if not clean_snapshot(snapshot['snapshot'], args.verbose):
            logger.error(f"Failed to clean snapshot: {snapshot['snapshot']}")
            continue
        
        # Rebuild bundle
        bundle_dir = export_dir / f"promoted_30s_{i+1}"
        bundle_dir.mkdir(exist_ok=True)
        
        if not rebuild_bundle(snapshot['snapshot'], str(bundle_dir), args.verbose):
            logger.error(f"Failed to rebuild bundle for: {snapshot['snapshot']}")
            continue
        
        promoted_snapshots.append(snapshot)
        logger.info(f"Successfully promoted snapshot {i+1}")
    
    if not promoted_snapshots:
        logger.error("No snapshots were successfully promoted")
        sys.exit(1)
    
    # Create promotion index
    create_promotion_index(promoted_snapshots, export_dir)
    
    logger.info(f"Promotion completed: {len(promoted_snapshots)} snapshots promoted")


if __name__ == "__main__":
    main()
