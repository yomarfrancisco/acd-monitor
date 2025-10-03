#!/usr/bin/env python3
"""
Leadership Rotation Detector

This detector computes cross-window leadership scores to identify
systematic leadership patterns and rotation dynamics across venues.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Add src to sys.path for acdlib imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

logger = logging.getLogger(__name__)


class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types"""

    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super().default(obj)


def compute_leadership_scores(tick_data, window_size=300):
    """
    Compute leadership scores for each venue within a window
    """
    logger.info(f"Computing leadership scores with window_size={window_size}")

    venues = list(tick_data.keys())
    if len(venues) < 2:
        logger.warning("Insufficient venues for leadership analysis")
        return {}

    leadership_scores = {}

    for venue in venues:
        venue_data = tick_data[venue]

        # Calculate price leadership metrics
        price_changes = venue_data["mid"].pct_change().dropna()

        # Price impact (how much price moves per unit volume)
        price_impact = abs(price_changes) / (venue_data["volume"] + 1e-8)

        # Price discovery (first to move)
        # This is simplified - would need cross-venue correlation analysis
        price_discovery = (
            price_changes.rolling(window=window_size)
            .apply(lambda x: 1 if x.iloc[0] != 0 else 0, raw=False)
            .mean()
        )

        # Volume leadership (volume-weighted price changes)
        volume_leadership = (
            (abs(price_changes) * venue_data["volume"]).rolling(window=window_size).mean()
        )

        # Overall leadership score (weighted combination)
        leadership_score = (
            0.4 * price_impact.mean() + 0.3 * price_discovery + 0.3 * volume_leadership.mean()
        )

        leadership_scores[venue] = {
            "leadership_score": float(leadership_score),
            "price_impact": float(price_impact.mean()),
            "price_discovery": float(price_discovery),
            "volume_leadership": float(volume_leadership.mean()),
        }

    logger.info(f"Computed leadership scores for {len(leadership_scores)} venues")
    return leadership_scores


def compute_rotation_metrics(leadership_scores):
    """
    Compute rotation metrics across venues
    """
    logger.info("Computing rotation metrics")

    venues = list(leadership_scores.keys())
    if len(venues) < 2:
        return {}

    # Sort venues by leadership score
    sorted_venues = sorted(
        venues, key=lambda v: leadership_scores[v]["leadership_score"], reverse=True
    )

    # Calculate rotation metrics
    rotation_metrics = {
        "leader": sorted_venues[0],
        "leader_score": leadership_scores[sorted_venues[0]]["leadership_score"],
        "rotation_entropy": 0.0,
        "dominance_ratio": 0.0,
        "venue_rankings": {},
    }

    # Calculate entropy (measure of rotation)
    scores = [leadership_scores[v]["leadership_score"] for v in venues]
    total_score = sum(scores)

    if total_score > 0:
        probabilities = [score / total_score for score in scores]
        rotation_entropy = -sum(p * np.log(p + 1e-8) for p in probabilities)
        rotation_metrics["rotation_entropy"] = float(rotation_entropy)

    # Calculate dominance ratio (leader vs others)
    if len(scores) > 1:
        leader_score = max(scores)
        others_score = sum(scores) - leader_score
        if others_score > 0:
            rotation_metrics["dominance_ratio"] = float(leader_score / others_score)

    # Store venue rankings
    for i, venue in enumerate(sorted_venues):
        rotation_metrics["venue_rankings"][venue] = {
            "rank": i + 1,
            "score": leadership_scores[venue]["leadership_score"],
            "percentile": float((len(venues) - i) / len(venues) * 100),
        }

    logger.info(f"Rotation metrics computed: leader={rotation_metrics['leader']}")
    return rotation_metrics


def run_leadership_rotation_analysis(snapshot_path, window_size=300, seed=42):
    """
    Run complete Leadership Rotation analysis
    """
    logger.info("Starting Leadership Rotation analysis")

    # Set random seed for reproducibility
    np.random.seed(seed)

    # Load snapshot data
    logger.info(f"Loading snapshot from: {snapshot_path}")
    tick_data = load_snapshot_data(snapshot_path)

    if not tick_data:
        logger.error("Failed to load tick data")
        return None

    logger.info(f"Loaded tick data for {len(tick_data)} venues")

    # Compute leadership scores
    leadership_scores = compute_leadership_scores(tick_data, window_size)

    # Compute rotation metrics
    rotation_metrics = compute_rotation_metrics(leadership_scores)

    # Generate results
    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "parameters": {"window_size": window_size, "seed": seed},
        "leadership_scores": leadership_scores,
        "rotation_metrics": rotation_metrics,
        "summary": {
            "venues_analyzed": len(tick_data),
            "leader": rotation_metrics.get("leader", "none"),
            "rotation_entropy": rotation_metrics.get("rotation_entropy", 0.0),
            "dominance_ratio": rotation_metrics.get("dominance_ratio", 0.0),
        },
    }

    logger.info(f"Leadership Rotation analysis complete")
    return results


def main():
    """
    Main function for Leadership Rotation detector
    """
    parser = argparse.ArgumentParser(description="Leadership Rotation Detector")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--window-size", type=int, default=300, help="Analysis window size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--export-dir", required=True, help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    # Create export directory
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Run analysis
        results = run_leadership_rotation_analysis(args.snapshot, args.window_size, args.seed)

        if results is None:
            logger.error("Analysis failed")
            sys.exit(1)

        # Save results
        results_file = export_dir / "leadership_rotation_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, cls=PandasJSONEncoder)

        logger.info(f"Results saved to: {results_file}")

        # Generate summary report
        report_file = export_dir / "leadership_rotation_report.md"
        with open(report_file, "w") as f:
            f.write("# Leadership Rotation Analysis Report\n\n")
            f.write(f"**Analysis Date**: {results['analysis_timestamp']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Venues Analyzed**: {results['summary']['venues_analyzed']}\n")
            f.write(f"- **Leader**: {results['summary']['leader']}\n")
            f.write(f"- **Rotation Entropy**: {results['summary']['rotation_entropy']:.3f}\n")
            f.write(f"- **Dominance Ratio**: {results['summary']['dominance_ratio']:.3f}\n\n")
            f.write("## Parameters\n\n")
            for key, value in results["parameters"].items():
                f.write(f"- **{key}**: {value}\n")

        logger.info(f"Report saved to: {report_file}")

    except Exception as e:
        logger.error(f"Leadership Rotation analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
