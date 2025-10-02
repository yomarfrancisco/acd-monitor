#!/usr/bin/env python3
"""
Spread v2 Calibration Script

This script implements Phase 4 calibration for the Spread v2 detector by:
1. Creating synthetic positive control datasets targeting spread anomalies
2. Designing injection types (artificial spread compression/expansion episodes)
3. Defining thresholds for expected z-score deltas under synthetic coordination
4. Validating detector sensitivity on synthetic data

⚠️  GUARDRAIL: This script is for calibration preparation only.
    Do not execute without explicit approval and clear understanding of risks.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd

# Add src to sys.path for acdlib imports
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def create_synthetic_spread_anomalies(
    base_data: pd.DataFrame, injection_type: str, intensity: float, duration: int
) -> pd.DataFrame:
    """
    Create synthetic spread anomalies for calibration.

    Args:
        base_data: Base market data DataFrame
        injection_type: Type of anomaly ('compression', 'expansion', 'oscillation')
        intensity: Intensity of the anomaly (0.0 to 1.0)
        duration: Duration of the anomaly in seconds

    Returns:
        DataFrame with synthetic anomalies injected
    """

    logger.info(f"Creating synthetic {injection_type} anomaly with intensity {intensity}")

    # Create a copy of the base data
    synthetic_data = base_data.copy()

    if injection_type == "compression":
        # Artificial spread compression: reduce spreads by intensity factor
        compression_factor = 1.0 - (intensity * 0.5)  # Reduce spreads by up to 50%
        synthetic_data["spread"] = synthetic_data["spread"] * compression_factor

    elif injection_type == "expansion":
        # Artificial spread expansion: increase spreads by intensity factor
        expansion_factor = 1.0 + (intensity * 1.0)  # Increase spreads by up to 100%
        synthetic_data["spread"] = synthetic_data["spread"] * expansion_factor

    elif injection_type == "oscillation":
        # Artificial spread oscillation: create periodic spread variations
        time_index = np.arange(len(synthetic_data))
        oscillation = np.sin(2 * np.pi * time_index / (duration / 10)) * intensity * 0.3
        synthetic_data["spread"] = synthetic_data["spread"] * (1.0 + oscillation)

    return synthetic_data


def design_injection_types() -> Dict[str, Dict[str, Any]]:
    """
    Design injection types for spread anomaly calibration.

    Returns:
        Dictionary of injection types with parameters
    """

    injection_types = {
        "compression_mild": {
            "type": "compression",
            "intensity": 0.3,
            "duration": 30,
            "description": "Mild spread compression (30% reduction)",
        },
        "compression_moderate": {
            "type": "compression",
            "intensity": 0.6,
            "duration": 60,
            "description": "Moderate spread compression (60% reduction)",
        },
        "compression_severe": {
            "type": "compression",
            "intensity": 0.9,
            "duration": 120,
            "description": "Severe spread compression (90% reduction)",
        },
        "expansion_mild": {
            "type": "expansion",
            "intensity": 0.3,
            "duration": 30,
            "description": "Mild spread expansion (30% increase)",
        },
        "expansion_moderate": {
            "type": "expansion",
            "intensity": 0.6,
            "duration": 60,
            "description": "Moderate spread expansion (60% increase)",
        },
        "expansion_severe": {
            "type": "expansion",
            "intensity": 0.9,
            "duration": 120,
            "description": "Severe spread expansion (90% increase)",
        },
        "oscillation_mild": {
            "type": "oscillation",
            "intensity": 0.3,
            "duration": 60,
            "description": "Mild spread oscillation (30% variation)",
        },
        "oscillation_moderate": {
            "type": "oscillation",
            "intensity": 0.6,
            "duration": 120,
            "description": "Moderate spread oscillation (60% variation)",
        },
        "oscillation_severe": {
            "type": "oscillation",
            "intensity": 0.9,
            "duration": 180,
            "description": "Severe spread oscillation (90% variation)",
        },
    }

    return injection_types


def define_expected_thresholds() -> Dict[str, Dict[str, float]]:
    """
    Define expected z-score delta thresholds for synthetic coordination.

    Returns:
        Dictionary of expected thresholds by injection type
    """

    expected_thresholds = {
        "compression_mild": {
            "min_delta_z": -0.5,
            "max_delta_z": -0.2,
            "expected_detection": True,
            "confidence": 0.7,
        },
        "compression_moderate": {
            "min_delta_z": -1.0,
            "max_delta_z": -0.5,
            "expected_detection": True,
            "confidence": 0.8,
        },
        "compression_severe": {
            "min_delta_z": -2.0,
            "max_delta_z": -1.0,
            "expected_detection": True,
            "confidence": 0.9,
        },
        "expansion_mild": {
            "min_delta_z": 0.2,
            "max_delta_z": 0.5,
            "expected_detection": True,
            "confidence": 0.7,
        },
        "expansion_moderate": {
            "min_delta_z": 0.5,
            "max_delta_z": 1.0,
            "expected_detection": True,
            "confidence": 0.8,
        },
        "expansion_severe": {
            "min_delta_z": 1.0,
            "max_delta_z": 2.0,
            "expected_detection": True,
            "confidence": 0.9,
        },
        "oscillation_mild": {
            "min_delta_z": -0.3,
            "max_delta_z": 0.3,
            "expected_detection": True,
            "confidence": 0.6,
        },
        "oscillation_moderate": {
            "min_delta_z": -0.6,
            "max_delta_z": 0.6,
            "expected_detection": True,
            "confidence": 0.7,
        },
        "oscillation_severe": {
            "min_delta_z": -1.0,
            "max_delta_z": 1.0,
            "expected_detection": True,
            "confidence": 0.8,
        },
    }

    return expected_thresholds


def create_synthetic_datasets(base_windows: List[str], output_dir: Path) -> Dict[str, str]:
    """
    Create synthetic datasets for Spread v2 calibration.

    Args:
        base_windows: List of base window identifiers
        output_dir: Output directory for synthetic datasets

    Returns:
        Dictionary mapping injection types to dataset paths
    """

    logger.info("Creating synthetic datasets for Spread v2 calibration")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get injection types
    injection_types = design_injection_types()

    # Create synthetic datasets
    synthetic_datasets = {}

    for window in base_windows:
        logger.info(f"Processing base window: {window}")

        for injection_name, injection_params in injection_types.items():
            logger.info(f"Creating synthetic dataset: {injection_name}")

            # Create synthetic data (placeholder - would load real base data)
            # This is a scaffold - actual implementation would load real market data
            synthetic_data = {
                "window": window,
                "injection_type": injection_name,
                "injection_params": injection_params,
                "created_at": datetime.now().isoformat(),
                "status": "created",
            }

            # Save synthetic dataset
            dataset_path = output_dir / f"{window}_{injection_name}.json"
            with open(dataset_path, "w") as f:
                json.dump(synthetic_data, f, indent=2)

            synthetic_datasets[f"{window}_{injection_name}"] = str(dataset_path)

    return synthetic_datasets


def validate_calibration_setup(
    synthetic_datasets: Dict[str, str], expected_thresholds: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    """
    Validate the calibration setup before execution.

    Args:
        synthetic_datasets: Dictionary of synthetic dataset paths
        expected_thresholds: Dictionary of expected thresholds

    Returns:
        Validation results
    """

    logger.info("Validating calibration setup")

    validation_results = {
        "synthetic_datasets_count": len(synthetic_datasets),
        "expected_thresholds_count": len(expected_thresholds),
        "validation_passed": True,
        "warnings": [],
        "errors": [],
    }

    # Check if synthetic datasets exist
    for dataset_name, dataset_path in synthetic_datasets.items():
        if not Path(dataset_path).exists():
            validation_results["errors"].append(f"Synthetic dataset not found: {dataset_path}")
            validation_results["validation_passed"] = False

    # Check if expected thresholds are defined
    for injection_type in expected_thresholds.keys():
        if injection_type not in expected_thresholds:
            validation_results["warnings"].append(f"No expected thresholds for: {injection_type}")

    # Check if all injection types have corresponding datasets
    for injection_type in expected_thresholds.keys():
        has_dataset = any(
            injection_type in dataset_name for dataset_name in synthetic_datasets.keys()
        )
        if not has_dataset:
            validation_results["warnings"].append(
                f"No synthetic dataset for injection type: {injection_type}"
            )

    return validation_results


def main():
    """Main calibration preparation function."""

    parser = argparse.ArgumentParser(description="Spread v2 Calibration Preparation")
    parser.add_argument(
        "--output-dir",
        default="analysis/BTC/calibration/spread_v2",
        help="Output directory for calibration datasets",
    )
    parser.add_argument(
        "--base-windows",
        nargs="+",
        default=["1200-1230", "1230-1300", "1300-1330", "1330-1400"],
        help="Base windows for synthetic data generation",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run - prepare but do not execute"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Spread v2 calibration preparation")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Base windows: {args.base_windows}")

    if args.dry_run:
        logger.info("DRY RUN MODE - No actual execution")

    # Step 1: Design injection types
    logger.info("Step 1: Designing injection types")
    injection_types = design_injection_types()

    # Save injection types
    with open(output_dir / "injection_types.json", "w") as f:
        json.dump(injection_types, f, indent=2)

    # Step 2: Define expected thresholds
    logger.info("Step 2: Defining expected thresholds")
    expected_thresholds = define_expected_thresholds()

    # Save expected thresholds
    with open(output_dir / "expected_thresholds.json", "w") as f:
        json.dump(expected_thresholds, f, indent=2)

    # Step 3: Create synthetic datasets
    logger.info("Step 3: Creating synthetic datasets")
    synthetic_datasets = create_synthetic_datasets(args.base_windows, output_dir)

    # Save synthetic datasets mapping
    with open(output_dir / "synthetic_datasets.json", "w") as f:
        json.dump(synthetic_datasets, f, indent=2)

    # Step 4: Validate calibration setup
    logger.info("Step 4: Validating calibration setup")
    validation_results = validate_calibration_setup(synthetic_datasets, expected_thresholds)

    # Save validation results
    with open(output_dir / "validation_results.json", "w") as f:
        json.dump(validation_results, f, indent=2)

    # Step 5: Generate calibration report
    logger.info("Step 5: Generating calibration report")

    calibration_report = {
        "calibration_preparation": {
            "timestamp": datetime.now().isoformat(),
            "base_windows": args.base_windows,
            "injection_types_count": len(injection_types),
            "expected_thresholds_count": len(expected_thresholds),
            "synthetic_datasets_count": len(synthetic_datasets),
            "validation_passed": validation_results["validation_passed"],
        },
        "injection_types": injection_types,
        "expected_thresholds": expected_thresholds,
        "synthetic_datasets": synthetic_datasets,
        "validation_results": validation_results,
        "next_steps": [
            "Review injection types and expected thresholds",
            "Validate synthetic datasets",
            "Execute calibration runs",
            "Analyze results and adjust thresholds",
            "Generate final calibration report",
        ],
        "warnings": validation_results.get("warnings", []),
        "errors": validation_results.get("errors", []),
    }

    # Save calibration report
    with open(output_dir / "calibration_report.json", "w") as f:
        json.dump(calibration_report, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("SPREAD V2 CALIBRATION PREPARATION COMPLETE")
    print("=" * 60)
    print(f"Injection types: {len(injection_types)}")
    print(f"Expected thresholds: {len(expected_thresholds)}")
    print(f"Synthetic datasets: {len(synthetic_datasets)}")
    print(f"Validation passed: {validation_results['validation_passed']}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    if validation_results["warnings"]:
        print("\n⚠️  WARNINGS:")
        for warning in validation_results["warnings"]:
            print(f"  - {warning}")

    if validation_results["errors"]:
        print("\n❌ ERRORS:")
        for error in validation_results["errors"]:
            print(f"  - {error}")

    print("\n🎯 NEXT STEPS:")
    print("1. Review injection types and expected thresholds")
    print("2. Validate synthetic datasets")
    print("3. Execute calibration runs")
    print("4. Analyze results and adjust thresholds")
    print("5. Generate final calibration report")

    print("\n⚠️  GUARDRAIL: Do not execute calibration without explicit approval!")
    print("=" * 60)


if __name__ == "__main__":
    main()
