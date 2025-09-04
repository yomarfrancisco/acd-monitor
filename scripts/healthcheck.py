#!/usr/bin/env python3
"""Health check script for ACD Monitor runs."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acd.monitoring import HealthChecker, MetricsCollector, RegressionDetector
from acd.monitoring.metrics import RunMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_metrics_from_file(metrics_path: Path) -> RunMetrics:
    """Load metrics from a JSON file."""
    try:
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)

        # Create RunMetrics object from dictionary
        return RunMetrics(**metrics_data)

    except Exception as e:
        logger.error(f"Failed to load metrics from {metrics_path}: {e}")
        raise


def get_adaptive_threshold(metrics: RunMetrics) -> float:
    """Get adaptive threshold for spurious rate based on dataset size."""
    dataset_size = metrics.dataset_size

    if dataset_size <= 200:
        return 0.02  # 2% for small datasets
    elif dataset_size <= 800:
        return 0.05  # 5% for medium datasets
    else:
        return 0.08  # 8% for large datasets


def run_health_check(
    metrics_path: Path,
    config_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    check_regressions: bool = False,
) -> int:
    """Run health check on metrics file.

    Args:
        metrics_path: Path to metrics JSON file
        config_path: Optional path to health check configuration
        output_dir: Optional directory for outputs
        check_regressions: Whether to run regression detection

    Returns:
        Exit code (0=PASS, 1=WARN, 2=FAIL)
    """
    try:
        # Load metrics
        logger.info(f"Loading metrics from {metrics_path}")
        metrics = load_metrics_from_file(metrics_path)

        # Initialize health checker
        health_checker = HealthChecker(config_path)

        # Get adaptive threshold
        adaptive_threshold = get_adaptive_threshold(metrics)
        logger.info(f"Using adaptive threshold: {adaptive_threshold:.3f}")

        # Run health check
        logger.info("Running health check...")
        health_result = health_checker.check_health(metrics, adaptive_threshold)

        # Print health table
        health_checker.print_health_table(health_result)

        # Save health check results if output directory specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save health check results
            health_output_path = output_dir / "health_check_results.json"
            health_data = {
                "overall_status": health_result.overall_status.value,
                "exit_code": health_result.exit_code,
                "summary": health_result.summary,
                "recommendations": health_result.recommendations,
                "gates": [
                    {
                        "name": gate.name,
                        "status": gate.status.value,
                        "value": gate.value,
                        "threshold": gate.threshold,
                        "message": gate.message,
                    }
                    for gate in health_result.gates
                ],
            }

            with open(health_output_path, "w") as f:
                json.dump(health_data, f, indent=2)

            logger.info(f"Health check results saved to {health_output_path}")

        # Run regression detection if requested
        if check_regressions:
            logger.info("Running regression detection...")

            # Initialize regression detector
            metrics_log_path = Path("demo/outputs/artifacts/metrics/run_log.parquet")
            regressions_dir = Path("docs/regressions")

            regression_detector = RegressionDetector(metrics_log_path, regressions_dir)
            regression_result = regression_detector.detect_regressions(metrics)

            if regression_result["regressions_detected"]:
                logger.warning(
                    f"Regressions detected: {len(regression_result['regression_notes'])}"
                )
                for note in regression_result["regression_notes"]:
                    logger.warning(f"  - {note}")
            else:
                logger.info("No regressions detected")

            # Save regression results if output directory specified
            if output_dir:
                regression_output_path = output_dir / "regression_analysis.json"
                with open(regression_output_path, "w") as f:
                    json.dump(regression_result, f, indent=2)

                logger.info(f"Regression analysis saved to {regression_output_path}")

        return health_result.exit_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 2


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="ACD Monitor Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/healthcheck.py --metrics demo/outputs/run_summary.json
  python scripts/healthcheck.py --metrics run_summary.json --config health_config.yaml
  python scripts/healthcheck.py --metrics run_summary.json --output health_results/ --regressions
        """,
    )

    parser.add_argument(
        "--metrics", "-m", type=Path, required=True, help="Path to metrics JSON file"
    )

    parser.add_argument(
        "--config", "-c", type=Path, help="Path to health check configuration YAML file"
    )

    parser.add_argument(
        "--output", "-o", type=Path, help="Output directory for health check results"
    )

    parser.add_argument(
        "--regressions",
        "-r",
        action="store_true",
        help="Run regression detection in addition to health check",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate metrics file
    if not args.metrics.exists():
        logger.error(f"Metrics file not found: {args.metrics}")
        sys.exit(1)

    # Run health check
    try:
        exit_code = run_health_check(
            metrics_path=args.metrics,
            config_path=args.config,
            output_dir=args.output,
            check_regressions=args.regressions,
        )

        # Exit with appropriate code
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(f"❌ Health check failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
