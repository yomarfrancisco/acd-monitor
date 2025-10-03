#!/usr/bin/env python3
"""
Phase-2 Validation Layer Test Script

Tests the first two validation layers (lead-lag and mirroring) on synthetic data
to demonstrate their ability to distinguish competitive vs coordinated scenarios.
"""

import numpy as np
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig
from acd.validation.lead_lag import LeadLagValidator, LeadLagConfig
from acd.validation.mirroring import MirroringValidator, MirroringConfig


def generate_test_data(seed: int = 42, scenario: str = "competitive"):
    """Generate test data for validation layers"""
    np.random.seed(seed)

    config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=4)
    generator = SyntheticCryptoGenerator(config)

    if scenario == "competitive":
        data = generator.generate_competitive_scenario()
    else:
        data = generator.generate_coordinated_scenario()

    return data


def test_lead_lag_validation(data, scenario_name):
    """Test lead-lag validation layer"""
    print(f"\n=== Lead-Lag Validation - {scenario_name} ===")

    config = LeadLagConfig(
        window_size=100, step_size=20, significance_level=0.05, min_observations=50
    )

    validator = LeadLagValidator(config)

    # Run analysis
    result = validator.analyze_lead_lag(
        data,
        ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"],
        environment_column="environment",
    )

    # Print results
    print(f"Significant Lead Fraction:")
    for pair, fraction in result.significant_lead_fraction.items():
        print(f"  {pair}: {fraction:.3f}")

    print(f"\nPersistence Metrics:")
    for pair, persistence in result.persistence_metrics.items():
        print(f"  {pair}: {persistence:.3f}")

    print(f"\nSwitching Entropy:")
    for pair, entropy in result.switching_entropy.items():
        print(f"  {pair}: {entropy:.3f}")

    print(f"\nEnvironment Sensitivity:")
    for pair, sensitivity in result.environment_sensitivity.items():
        print(f"  {pair}: {sensitivity:.3f}")

    # Granger causality results
    print(f"\nGranger Causality (min p-values):")
    for pair, granger_result in result.granger_results.items():
        min_p = granger_result["min_p_value"]
        significant_lags = granger_result["significant_lags"]
        print(f"  {pair}: p={min_p:.3f}, significant_lags={significant_lags}")

    return result


def test_mirroring_validation(data, scenario_name):
    """Test mirroring validation layer"""
    print(f"\n=== Mirroring Validation - {scenario_name} ===")

    config = MirroringConfig(
        top_k_levels=5,
        similarity_threshold=0.8,
        window_size=100,
        step_size=20,
        significance_level=0.05,
        min_observations=50,
    )

    validator = MirroringValidator(config)

    # Run analysis
    result = validator.analyze_mirroring(
        data,
        ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"],
        environment_column="environment",
    )

    # Print results
    print(f"Median Mirroring Ratio:")
    for pair, ratio in result.median_mirroring_ratio.items():
        print(f"  {pair}: {ratio:.3f}")

    print(f"\nHigh Mirroring Fraction (>0.8):")
    for pair, fraction in result.high_mirroring_fraction.items():
        print(f"  {pair}: {fraction:.3f}")

    print(f"\nEnvironment Invariance:")
    for pair, invariance in result.environment_invariance.items():
        print(f"  {pair}: {invariance:.3f}")

    # Summary statistics
    avg_mirroring = np.mean(list(result.median_mirroring_ratio.values()))
    avg_high_mirroring = np.mean(list(result.high_mirroring_fraction.values()))
    avg_invariance = np.mean(list(result.environment_invariance.values()))

    print(f"\nSummary:")
    print(f"  Average Mirroring Ratio: {avg_mirroring:.3f}")
    print(f"  Average High Mirroring Fraction: {avg_high_mirroring:.3f}")
    print(f"  Average Environment Invariance: {avg_invariance:.3f}")

    return result


def main():
    """Main test function"""
    print("Phase-2 Validation Layer Test")
    print("=" * 50)

    # Test on competitive data
    print("\nGenerating competitive synthetic data...")
    competitive_data = generate_test_data(seed=42, scenario="competitive")

    competitive_lead_lag = test_lead_lag_validation(competitive_data, "Competitive")
    competitive_mirroring = test_mirroring_validation(competitive_data, "Competitive")

    # Test on coordinated data
    print("\nGenerating coordinated synthetic data...")
    coordinated_data = generate_test_data(seed=42, scenario="coordinated")

    coordinated_lead_lag = test_lead_lag_validation(coordinated_data, "Coordinated")
    coordinated_mirroring = test_mirroring_validation(coordinated_data, "Coordinated")

    # Compare results
    print("\n" + "=" * 50)
    print("COMPARISON SUMMARY")
    print("=" * 50)

    # Lead-lag comparison
    print("\nLead-Lag Analysis Comparison:")
    comp_avg_persistence = np.mean(list(competitive_lead_lag.persistence_metrics.values()))
    coord_avg_persistence = np.mean(list(coordinated_lead_lag.persistence_metrics.values()))

    comp_avg_entropy = np.mean(list(competitive_lead_lag.switching_entropy.values()))
    coord_avg_entropy = np.mean(list(coordinated_lead_lag.switching_entropy.values()))

    print(
        f"  Average Persistence - Competitive: {comp_avg_persistence:.3f}, Coordinated: {coord_avg_persistence:.3f}"
    )
    print(
        f"  Average Switching Entropy - Competitive: {comp_avg_entropy:.3f}, Coordinated: {coord_avg_entropy:.3f}"
    )

    # Mirroring comparison
    print("\nMirroring Analysis Comparison:")
    comp_avg_mirroring = np.mean(list(competitive_mirroring.median_mirroring_ratio.values()))
    coord_avg_mirroring = np.mean(list(coordinated_mirroring.median_mirroring_ratio.values()))

    comp_avg_high_mirroring = np.mean(list(competitive_mirroring.high_mirroring_fraction.values()))
    coord_avg_high_mirroring = np.mean(list(coordinated_mirroring.high_mirroring_fraction.values()))

    print(
        f"  Average Mirroring Ratio - Competitive: {comp_avg_mirroring:.3f}, Coordinated: {coord_avg_mirroring:.3f}"
    )
    print(
        f"  Average High Mirroring Fraction - Competitive: {comp_avg_high_mirroring:.3f}, Coordinated: {coord_avg_high_mirroring:.3f}"
    )

    # Success criteria
    print("\nSuccess Criteria Check:")
    print(
        f"  Lead-lag persistence higher for coordinated: {coord_avg_persistence > comp_avg_persistence}"
    )
    print(f"  Lead-lag entropy lower for coordinated: {coord_avg_entropy < comp_avg_entropy}")
    print(f"  Mirroring ratio higher for coordinated: {coord_avg_mirroring > comp_avg_mirroring}")
    print(
        f"  High mirroring fraction higher for coordinated: {coord_avg_high_mirroring > comp_avg_high_mirroring}"
    )

    # Overall success
    success_criteria = [
        coord_avg_persistence > comp_avg_persistence,
        coord_avg_entropy < comp_avg_entropy,
        coord_avg_mirroring > comp_avg_mirroring,
        coord_avg_high_mirroring > comp_avg_high_mirroring,
    ]

    overall_success = all(success_criteria)
    print(f"\nOverall Success: {overall_success} ({sum(success_criteria)}/4 criteria met)")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
