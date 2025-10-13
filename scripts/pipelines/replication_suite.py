#!/usr/bin/env python3
"""
Replication Suite: Compare episodes across windows for stability analysis.

This script calculates replication metrics between two windows:
- Replication rate: fraction of episodes from base window that have matches in new window
- Duration-weighted Jaccard similarity: intersection over union of episode durations
- Match criteria: episodes overlap by ≥5s OR start times within ±5s
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np


# Import custom JSON encoder
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""

    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return super().default(obj)


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def load_episodes(episodes_file: str) -> List[Dict]:
    """Load episodes from JSON file."""
    try:
        with open(episodes_file, "r") as f:
            data = json.load(f)

        if "episodes" in data:
            return data["episodes"]
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Unexpected episodes file format: {episodes_file}")
            return []
    except Exception as e:
        logger.error(f"Failed to load episodes from {episodes_file}: {e}")
        return []


def parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp string to datetime object."""
    try:
        # Handle ISO format with Z suffix
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except Exception as e:
        logger.error(f"Failed to parse timestamp {ts_str}: {e}")
        return datetime.now()


def calculate_episode_duration(episode: Dict) -> float:
    """Calculate episode duration in seconds."""
    try:
        # Handle nested episode structure
        if "episode" in episode:
            episode_data = episode["episode"]
        else:
            episode_data = episode

        start_time = parse_timestamp(episode_data["start_time"])
        end_time = parse_timestamp(episode_data["end_time"])
        return (end_time - start_time).total_seconds()
    except Exception as e:
        logger.error(f"Failed to calculate duration for episode: {e}")
        return 0.0


def episodes_overlap(
    ep1: Dict, ep2: Dict, min_intersection: float = 5.0, start_tolerance: float = 5.0
) -> bool:
    """Check if two episodes overlap based on duration or start time proximity."""
    try:
        # Handle nested episode structure
        if "episode" in ep1:
            ep1_data = ep1["episode"]
        else:
            ep1_data = ep1

        if "episode" in ep2:
            ep2_data = ep2["episode"]
        else:
            ep2_data = ep2

        # Parse timestamps
        start1 = parse_timestamp(ep1_data["start_time"])
        end1 = parse_timestamp(ep1_data["end_time"])
        start2 = parse_timestamp(ep2_data["start_time"])
        end2 = parse_timestamp(ep2_data["end_time"])

        # Check start time proximity
        start_diff = abs((start1 - start2).total_seconds())
        if start_diff <= start_tolerance:
            return True

        # Check duration overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start < overlap_end:
            overlap_duration = (overlap_end - overlap_start).total_seconds()
            return overlap_duration >= min_intersection

        return False
    except Exception as e:
        logger.error(f"Failed to check episode overlap: {e}")
        return False


def find_matches(
    base_episodes: List[Dict],
    new_episodes: List[Dict],
    min_intersection: float = 5.0,
    start_tolerance: float = 5.0,
) -> List[Tuple[int, int]]:
    """Find matching episodes between base and new windows."""
    matches = []
    used_new_indices = set()

    for i, base_ep in enumerate(base_episodes):
        for j, new_ep in enumerate(new_episodes):
            if j in used_new_indices:
                continue

            if episodes_overlap(base_ep, new_ep, min_intersection, start_tolerance):
                matches.append((i, j))
                used_new_indices.add(j)
                break

    return matches


def calculate_jaccard_similarity(
    base_episodes: List[Dict], new_episodes: List[Dict], matches: List[Tuple[int, int]]
) -> float:
    """Calculate duration-weighted Jaccard similarity."""
    try:
        if not base_episodes and not new_episodes:
            return 1.0
        if not base_episodes or not new_episodes:
            return 0.0

        # Calculate total duration of matched episodes (intersection)
        intersection_duration = 0.0
        for base_idx, new_idx in matches:
            base_duration = calculate_episode_duration(base_episodes[base_idx])
            new_duration = calculate_episode_duration(new_episodes[new_idx])
            # Use minimum duration for intersection
            intersection_duration += min(base_duration, new_duration)

        # Calculate total duration of all episodes (union)
        base_total = sum(calculate_episode_duration(ep) for ep in base_episodes)
        new_total = sum(calculate_episode_duration(ep) for ep in new_episodes)
        union_duration = base_total + new_total - intersection_duration

        if union_duration == 0:
            return 0.0

        return intersection_duration / union_duration
    except Exception as e:
        logger.error(f"Failed to calculate Jaccard similarity: {e}")
        return 0.0


def run_replication_analysis(
    base_window_file: str,
    new_window_file: str,
    min_intersection: float = 5.0,
    start_tolerance: float = 5.0,
    export_dir: str = "experiments/phase5/replication",
) -> Dict:
    """Run replication analysis between two windows."""

    # Load episodes
    base_episodes = load_episodes(base_window_file)
    new_episodes = load_episodes(new_window_file)

    logger.info(f"Base window: {len(base_episodes)} episodes")
    logger.info(f"New window: {len(new_episodes)} episodes")

    # Find matches
    matches = find_matches(base_episodes, new_episodes, min_intersection, start_tolerance)

    # Calculate metrics
    replication_rate = len(matches) / len(base_episodes) if base_episodes else 0.0
    jaccard_similarity = calculate_jaccard_similarity(base_episodes, new_episodes, matches)

    # Determine replication flag
    replication_flag = (
        "PASS" if (replication_rate >= 0.50 or jaccard_similarity >= 0.35) else "FAIL"
    )

    # Prepare results
    results = {
        "base_window_file": base_window_file,
        "new_window_file": new_window_file,
        "base_episode_count": len(base_episodes),
        "new_episode_count": len(new_episodes),
        "match_count": len(matches),
        "replication_rate": replication_rate,
        "jaccard_similarity": jaccard_similarity,
        "replication_flag": replication_flag,
        "min_intersection_seconds": min_intersection,
        "start_tolerance_seconds": start_tolerance,
        "matches": [
            {
                "base_index": base_idx,
                "new_index": new_idx,
                "base_episode": base_episodes[base_idx],
                "new_episode": new_episodes[new_idx],
            }
            for base_idx, new_idx in matches
        ],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return results


def main():
    """Main function for replication analysis."""
    parser = argparse.ArgumentParser(description="Replication Suite Analysis")
    parser.add_argument("--base-window", required=True, help="Path to base window episodes.json")
    parser.add_argument("--new-window", required=True, help="Path to new window episodes.json")
    parser.add_argument(
        "--t-start-tol", type=float, default=5.0, help="Start time tolerance in seconds"
    )
    parser.add_argument(
        "--min-intersection",
        type=float,
        default=5.0,
        help="Minimum intersection duration in seconds",
    )
    parser.add_argument("--export-dir", required=True, help="Export directory for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Create export directory
    export_path = Path(args.export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    try:
        # Run replication analysis
        results = run_replication_analysis(
            base_window_file=args.base_window,
            new_window_file=args.new_window,
            min_intersection=args.min_intersection,
            start_tolerance=args.t_start_tol,
            export_dir=args.export_dir,
        )

        # Write results
        results_file = export_path / "replication.json"
        results_file.write_text(json.dumps(results, cls=PandasJSONEncoder, indent=2))

        logger.info(f"Replication analysis completed. Results saved to {results_file}")
        logger.info(f"Replication rate: {results['replication_rate']:.3f}")
        logger.info(f"Jaccard similarity: {results['jaccard_similarity']:.3f}")
        logger.info(f"Replication flag: {results['replication_flag']}")

    except Exception as e:
        logger.error(f"Replication analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
