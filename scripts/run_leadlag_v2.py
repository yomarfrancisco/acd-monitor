#!/usr/bin/env python3
"""
Lead-Lag Analysis v2 Script

Research-grade lead-lag analysis with proper methodology:
- Log-returns instead of price levels
- Cross-correlation and lagged regression estimators
- HAC significance testing with bootstrap
- Multiple horizon support
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from acd.analytics.leadlag_v2 import LeadLagV2Engine  # noqa: E402
from acdlib.io.load_snapshot import load_ticks_snapshot, load_overlap  # noqa: E402

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_pairs(pairs_str: str) -> list:
    """Parse pairs string into list of tuples."""
    pairs = []
    for pair in pairs_str.split(","):
        if "-" in pair:
            venue1, venue2 = pair.split("-")
            pairs.append((venue1.strip(), venue2.strip()))
        else:
            logger.warning(f"[LLV2:skip] Invalid pair format: {pair}")
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Lead-Lag Analysis v2")
    parser.add_argument("--use-overlap-json", required=True, help="Path to OVERLAP.json file")
    parser.add_argument(
        "--pairs",
        required=True,
        help="Comma-separated pairs (e.g., binance-okx,binance-bybit)",
    )
    parser.add_argument("--freq", default="1s", help="Resampling frequency (default: 1s)")
    parser.add_argument(
        "--horizons",
        default="1,2,5,10,30",
        help="Comma-separated horizons in seconds (default: 1,2,5,10,30)",
    )
    parser.add_argument(
        "--method",
        default="xcorr,lagreg",
        help="Comma-separated methods (default: xcorr,lagreg)",
    )
    parser.add_argument("--export-dir", required=True, help="Export directory for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse arguments
    pairs = parse_pairs(args.pairs)
    horizons = [int(h) for h in args.horizons.split(",")]
    methods = args.method.split(",")

    logger.info("[LLV2:start] Lead-Lag v2 Analysis")
    logger.info(f"[LLV2:config] Pairs: {pairs}")
    logger.info(f"[LLV2:config] Horizons: {horizons}")
    logger.info(f"[LLV2:config] Methods: {methods}")
    logger.info(f"[LLV2:config] Frequency: {args.freq}")

    # Load overlap data
    try:
        overlap_data = load_overlap(args.use_overlap_json)
        logger.info(
            f"[LLV2:overlap] Loaded overlap: {overlap_data['start_utc']} "
            f"to {overlap_data['end_utc']}"
        )
        logger.info(f"[LLV2:overlap] Venues: {overlap_data['venues']}")
    except Exception as e:
        logger.error(f"[LLV2:error] Failed to load overlap: {e}")
        sys.exit(1)

    # Load tick data
    try:
        tick_data = load_ticks_snapshot(overlap_data)
        logger.info(f"[LLV2:data] Loaded tick data for {len(tick_data)} venues")
    except Exception as e:
        logger.error(f"[LLV2:error] Failed to load tick data: {e}")
        sys.exit(1)

    # Initialize engine
    engine = LeadLagV2Engine(min_obs=300, block_size=10, bootstrap_reps=1000)

    # Run analysis
    try:
        results = engine.run_analysis(
            data=tick_data,
            pairs=pairs,
            horizons=horizons,
            methods=methods,
            freq=args.freq,
        )

        if not results:
            logger.error("[LLV2:error] No results generated")
            sys.exit(1)

        # Create export directory
        export_path = Path(args.export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # Save results
        results_file = export_path / "leadlag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"[LLV2:save] Results saved to {results_file}")

        # Print summary
        print("\n[LLV2:summary] Lead-Lag v2 Analysis Complete")
        print(
            f"[LLV2:summary] Window: {results['window']['start']} " f"to {results['window']['end']}"
        )
        print(f"[LLV2:summary] Frequency: {results['window']['freq']}")
        print(f"[LLV2:summary] Edges analyzed: {len(results['edges'])}")

        # Show best results
        for edge in results["edges"]:
            if edge["score"] > 0:
                print(
                    f"[LLV2:result] {edge['from']}->{edge['to']}: "
                    f"score={edge['score']:.3f}, lag={edge['best_lag_s']}s, "
                    f"p={edge['p']:.3f}"
                )

        # Cross-tool validation
        print("\n[LLV2:validation] Cross-tool validation:")
        print("[LLV2:validation] - InfoShare analysis: Run separately for comparison")
        print("[LLV2:validation] - Spread episodes: Run separately for comparison")

    except Exception as e:
        logger.error(f"[LLV2:error] Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
