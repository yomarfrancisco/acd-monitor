#!/usr/bin/env python3
"""
ICP-VMM Single Window Analysis

Analyzes a single window for ICP-VMM patterns.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from icp_vmm.environments import EnvironmentLabeler
from icp_vmm.transforms import DataTransformer
from icp_vmm.tests import PreconditionTester
from icp_vmm.vmm import VMMAnalyzer
from icp_vmm.icp import ICPTester
from icp_vmm.export import ICPVMMExporter


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def load_window_data(s3_uri: str) -> tuple:
    """
    Load window data from S3.

    Args:
        s3_uri: S3 URI to window data

    Returns:
        Tuple of (venue_data, continuous_metrics)
    """
    # For now, return mock data
    # In production, this would load from S3
    venue_data = {
        "binance": pd.DataFrame(
            {
                "ts_exchange": pd.date_range("2025-09-29 12:00:00", periods=100, freq="1s"),
                "last_px": 50000 + np.random.randn(100) * 10,
                "best_bid": 50000 + np.random.randn(100) * 10 - 1,
                "best_ask": 50000 + np.random.randn(100) * 10 + 1,
                "spread_bps": np.random.uniform(0.1, 2.0, 100),
                "bid_sz": np.random.uniform(0.1, 10.0, 100),
                "ask_sz": np.random.uniform(0.1, 10.0, 100),
                "imbalance": np.random.uniform(-0.5, 0.5, 100),
            }
        ),
        "coinbase": pd.DataFrame(
            {
                "ts_exchange": pd.date_range("2025-09-29 12:00:00", periods=100, freq="1s"),
                "last_px": 50000 + np.random.randn(100) * 10,
                "best_bid": 50000 + np.random.randn(100) * 10 - 1,
                "best_ask": 50000 + np.random.randn(100) * 10 + 1,
                "spread_bps": np.random.uniform(0.1, 2.0, 100),
                "bid_sz": np.random.uniform(0.1, 10.0, 100),
                "ask_sz": np.random.uniform(0.1, 10.0, 100),
                "imbalance": np.random.uniform(-0.5, 0.5, 100),
            }
        ),
    }

    continuous_metrics = {
        "daily_vwap": 50000.0,
        "day_high": 50100.0,
        "day_low": 49900.0,
        "liquidity_ratio": pd.Series(np.random.uniform(0.5, 2.0, 100)),
        "liquidity_volatility": pd.Series(np.random.uniform(0.1, 0.5, 100)),
        "leadership_shares": pd.Series(np.random.uniform(0.2, 0.8, 100)),
    }

    return venue_data, continuous_metrics


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="ICP-VMM Single Window Analysis")
    parser.add_argument("--symbol", required=True, help="Symbol to analyze (e.g., BTC-USD)")
    parser.add_argument("--s3-window", required=True, help="S3 URI to window data")
    parser.add_argument("--out-prefix", required=True, help="S3 output prefix")
    parser.add_argument(
        "--min-per-env",
        type=int,
        default=5,
        help="Minimum observations per environment",
    )
    parser.add_argument("--bootstrap", type=int, default=500, help="Bootstrap samples")
    parser.add_argument("--fdr", type=float, default=0.05, help="FDR alpha level")
    parser.add_argument("--mode", default="provisional", help="Analysis mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load window data
        logger.info(f"Loading window data from {args.s3_window}")
        venue_data, continuous_metrics = load_window_data(args.s3_window)

        # Initialize components
        env_labeler = EnvironmentLabeler(min_obs_per_env=args.min_per_env)
        transformer = DataTransformer()
        tester = PreconditionTester()
        vmm_analyzer = VMMAnalyzer()
        icp_tester = ICPTester(fdr_alpha=args.fdr, bootstrap_samples=args.bootstrap)
        exporter = ICPVMMExporter("acd-monitor-snapshots", "analysis")

        # Prepare data
        logger.info("Preparing data for analysis")
        prepared_data, processed_metrics, warnings = transformer.prepare_analysis_data(
            venue_data, continuous_metrics
        )

        # Label environments
        logger.info("Labeling environments")
        labeled_data = {}
        for venue, data in prepared_data.items():
            labeled_data[venue] = env_labeler.label_all_environments(data, processed_metrics)

        # Get environment counts
        env_counts = {}
        for venue, data in labeled_data.items():
            venue_counts = env_labeler.get_environment_counts(data)
            for env_type, counts in venue_counts.items():
                if env_type not in env_counts:
                    env_counts[env_type] = {}
                for env, count in counts.items():
                    key = f"{venue}_{env}"
                    env_counts[env_type][key] = env_counts[env_type].get(key, 0) + count

        # Run precondition tests
        logger.info("Running precondition tests")
        test_results = tester.run_all_tests(prepared_data, env_counts)

        if test_results["overall"]["status"] == "INSUFFICIENT":
            logger.warning("Insufficient data for analysis")
            status = "INSUFFICIENT"
        else:
            # Run VMM analysis
            logger.info("Running VMM analysis")
            vmm_results = vmm_analyzer.analyze_vmm(prepared_data)

            # Run ICP tests
            logger.info("Running ICP tests")
            icp_tests = icp_tester.run_all_icp_tests(
                labeled_data,
                {},  # env_leadership - would be extracted from labeled_data
                {},  # env_residuals - would be calculated from VMM residuals
            )

            status = "PROVISIONAL"

        # Prepare results
        results = {
            "window_id": args.s3_window.split("/")[-1],
            "symbol": args.symbol,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {
                "min_per_env": args.min_per_env,
                "bootstrap_samples": args.bootstrap,
                "fdr_alpha": args.fdr,
                "mode": args.mode,
            },
            "env_counts": env_counts,
            "test_results": test_results,
            "vmm_results": vmm_results if "vmm_results" in locals() else {},
            "icp_tests": icp_tests if "icp_tests" in locals() else {},
            "warnings": warnings,
        }

        # Export results
        logger.info("Exporting results")
        export_status = exporter.export_to_s3(results, results["window_id"], args.symbol)

        if export_status["status"] == "SUCCESS":
            logger.info(f"Analysis completed successfully: {status}")
            print(json.dumps(results, indent=2))
        else:
            logger.error(f"Export failed: {export_status.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
