#!/usr/bin/env python3
"""
Test script to verify VMM differentiation with enhanced crypto moments
"""

import numpy as np
import pandas as pd
import hashlib
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig
from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.vmm.scalers import GlobalMomentScaler
from acd.vmm.engine import VMMEngine, VMMConfig


def test_vmm_differentiation():
    """Test VMM differentiation with enhanced crypto moments"""

    print("VMM Differentiation Test with Enhanced Crypto Moments")
    print("=" * 60)

    # Set seed for reproducibility
    np.random.seed(42)

    # Generate data
    config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
    generator = SyntheticCryptoGenerator(config)

    competitive_data = generator.generate_competitive_scenario()
    coordinated_data = generator.generate_coordinated_scenario()

    price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    # Create global scaler
    global_scaler = GlobalMomentScaler(method="minmax")

    # Create crypto calculator with global scaler
    crypto_config = CryptoMomentConfig()
    crypto_calculator = CryptoMomentCalculator(crypto_config, global_scaler)

    # Fit scaler on competitive data first
    print("Fitting global scaler on competitive data...")
    competitive_moment_vector = crypto_calculator.get_combined_moment_vector(
        competitive_data, price_columns, environment_column="volatility_regime", fit_scaler=True
    )

    # Get moment vectors for both scenarios
    print("Calculating moment vectors...")
    competitive_moment_vector = crypto_calculator.get_combined_moment_vector(
        competitive_data, price_columns, environment_column="volatility_regime", fit_scaler=False
    )

    coordinated_moment_vector = crypto_calculator.get_combined_moment_vector(
        coordinated_data, price_columns, environment_column="volatility_regime", fit_scaler=False
    )

    # Calculate distances and hashes
    l2_distance = np.linalg.norm(competitive_moment_vector - coordinated_moment_vector)
    cosine_sim = np.dot(competitive_moment_vector, coordinated_moment_vector) / (
        np.linalg.norm(competitive_moment_vector) * np.linalg.norm(coordinated_moment_vector)
    )

    comp_hash = hashlib.sha256(competitive_moment_vector.tobytes()).hexdigest()[:16]
    coord_hash = hashlib.sha256(coordinated_moment_vector.tobytes()).hexdigest()[:16]

    print(f"\nMoment Vector Analysis:")
    print(f"Competitive hash: {comp_hash}")
    print(f"Coordinated hash: {coord_hash}")
    print(f"L2 distance: {l2_distance:.6f}")
    print(f"Cosine similarity: {cosine_sim:.6f}")
    print(
        f"Vector lengths: competitive={len(competitive_moment_vector)}, coordinated={len(coordinated_moment_vector)}"
    )

    # Check after-scaling differences (using the same global scaler)
    if (
        hasattr(crypto_calculator, "_fitted_scaler")
        and crypto_calculator._fitted_scaler is not None
    ):
        # Get scaled vectors using the same scaler
        comp_scaled = crypto_calculator.get_combined_moment_vector(
            competitive_data,
            price_columns,
            environment_column="volatility_regime",
            fit_scaler=False,
        )
        coord_scaled = crypto_calculator.get_combined_moment_vector(
            coordinated_data,
            price_columns,
            environment_column="volatility_regime",
            fit_scaler=False,
        )

        # Calculate after-scaling distances
        scaled_l2 = np.linalg.norm(comp_scaled - coord_scaled)
        scaled_cosine = np.dot(comp_scaled, coord_scaled) / (
            np.linalg.norm(comp_scaled) * np.linalg.norm(coord_scaled)
        )

        print(f"\nAfter-Scaling Analysis:")
        print(f"L2 distance: {scaled_l2:.6f}")
        print(f"Cosine similarity: {scaled_cosine:.6f}")
        print(f"Differences persist: {scaled_l2 > 0.001 and abs(scaled_cosine) < 0.99}")

    # Create VMM engine
    vmm_config = VMMConfig()
    vmm_engine = VMMEngine(vmm_config, crypto_calculator)

    # Run VMM analysis
    print(f"\nRunning VMM analysis...")
    competitive_result = vmm_engine.run_vmm(
        competitive_data, price_columns, environment_column="volatility_regime"
    )
    coordinated_result = vmm_engine.run_vmm(
        coordinated_data, price_columns, environment_column="volatility_regime"
    )

    # Get metadata for reporting
    metadata = getattr(vmm_engine, "_weight_matrix_metadata", {})
    N = metadata.get("N", "N/A")
    k = metadata.get("k", "N/A")
    dof = k - len(competitive_result.beta_estimates) if isinstance(k, int) else "N/A"

    # Print results
    print(f"\nVMM Results (HAC GMM):")
    print("=" * 70)
    print(
        f"{'Scenario':<12} {'N/env':<8} {'k':<4} {'dof':<4} {'J-stat':<12} {'p-value':<12} {'Stability':<12}"
    )
    print("-" * 70)
    print(
        f"{'Competitive':<12} {N:<8} {k:<4} {dof:<4} {competitive_result.over_identification_stat:<12.6f} {competitive_result.over_identification_p_value:<12.6f} {competitive_result.structural_stability:<12.6f}"
    )
    print(
        f"{'Coordinated':<12} {N:<8} {k:<4} {dof:<4} {coordinated_result.over_identification_stat:<12.6f} {coordinated_result.over_identification_p_value:<12.6f} {coordinated_result.structural_stability:<12.6f}"
    )

    # Check differentiation
    print(f"\nDifferentiation Check:")
    print(
        f"J-statistic different: {competitive_result.over_identification_stat != coordinated_result.over_identification_stat}"
    )
    print(
        f"p-value different: {competitive_result.over_identification_p_value != coordinated_result.over_identification_p_value}"
    )
    print(
        f"Stability different: {competitive_result.structural_stability != coordinated_result.structural_stability}"
    )

    # Check expected patterns
    print(f"\nExpected Patterns:")
    print(f"Competitive p > 0.05: {competitive_result.over_identification_p_value > 0.05}")
    print(f"Coordinated p < 0.05: {coordinated_result.over_identification_p_value < 0.05}")

    # Print scaler parameters
    scaler_params = global_scaler.get_params()
    print(f"\nGlobal Scaler Parameters:")
    for moment_name, params in scaler_params.items():
        print(f"{moment_name}: {params}")

    # Print HAC provenance and weight matrix details
    if (
        hasattr(vmm_engine, "_global_weight_matrix")
        and vmm_engine._global_weight_matrix is not None
    ):
        W = vmm_engine._global_weight_matrix
        metadata = getattr(vmm_engine, "_weight_matrix_metadata", {})

        print(f"\nHAC Weight Matrix Provenance:")
        print(f"W derived from: competitive dataset")
        print(f"W shape: {W.shape}")
        print(f"N (samples): {metadata.get('N', 'N/A')}")
        print(f"k (moments): {metadata.get('k', 'N/A')}")
        print(f"Lag L: {metadata.get('lag', 'N/A')}")
        print(f"Ridge λ: {metadata.get('ridge_lambda', 'N/A')}")
        print(f"Condition number: {metadata.get('condition_number', 'N/A')}")
        print(f"First 3 diagonal entries: {np.diag(W)[:3]}")
    else:
        print(f"\nWeight Matrix: Not fitted")

    return {
        "competitive_result": competitive_result,
        "coordinated_result": coordinated_result,
        "moment_hashes": (comp_hash, coord_hash),
        "l2_distance": l2_distance,
        "cosine_similarity": cosine_sim,
        "scaler_params": scaler_params,
    }


def test_coordination_strength_sensitivity():
    """Test VMM sensitivity to coordination strength"""

    print(f"\n\nCoordination Strength Sensitivity Test")
    print("=" * 60)

    coordination_strengths = [0.0, 0.25, 0.5, 0.75, 1.0]
    results = []

    for strength in coordination_strengths:
        np.random.seed(42)  # Fixed seed for reproducibility

        # Generate data
        config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)

        if strength == 0.0:
            data = generator.generate_competitive_scenario()
        else:
            data = generator.generate_coordinated_scenario()
            # Apply coordination strength scaling
            price_columns = [col for col in data.columns if col.startswith("Exchange_")]
            for col in price_columns:
                # Scale coordination effects by strength parameter
                base_volatility = np.std(np.diff(data[col]))
                coordination_effect = (1 - strength) * base_volatility
                data[col] = data[col] * (1 + coordination_effect * 0.1)

        # Create VMM engine
        global_scaler = GlobalMomentScaler(method="minmax")
        crypto_config = CryptoMomentConfig()
        crypto_calculator = CryptoMomentCalculator(crypto_config, global_scaler)
        vmm_config = VMMConfig()
        vmm_engine = VMMEngine(vmm_config, crypto_calculator)

        # Run VMM analysis
        price_columns = [col for col in data.columns if col.startswith("Exchange_")]
        result = vmm_engine.run_vmm(data, price_columns, environment_column="volatility_regime")

        results.append(
            {
                "strength": strength,
                "j_stat": result.over_identification_stat,
                "p_value": result.over_identification_p_value,
                "stability": result.structural_stability,
            }
        )

    # Print results table
    print(f"{'Strength':<10} {'J-stat':<12} {'p-value':<12} {'Stability':<12}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['strength']:<10.2f} {r['j_stat']:<12.6f} {r['p_value']:<12.6f} {r['stability']:<12.6f}"
        )

    return results


if __name__ == "__main__":
    # Run differentiation test
    diff_results = test_vmm_differentiation()

    # Run sensitivity test
    sensitivity_results = test_coordination_strength_sensitivity()

    print(f"\n\nTest Summary:")
    print("=" * 60)

    # Check if differentiation is working
    comp_result = diff_results["competitive_result"]
    coord_result = diff_results["coordinated_result"]

    differentiation_working = (
        comp_result.over_identification_stat != coord_result.over_identification_stat
        and comp_result.over_identification_p_value != coord_result.over_identification_p_value
        and comp_result.structural_stability != coord_result.structural_stability
    )

    print(f"VMM Differentiation Working: {differentiation_working}")
    print(
        f"Moment Vector Hashes Different: {diff_results['moment_hashes'][0] != diff_results['moment_hashes'][1]}"
    )
    print(f"L2 Distance: {diff_results['l2_distance']:.6f}")
    print(f"Cosine Similarity: {diff_results['cosine_similarity']:.6f}")

    if differentiation_working:
        print("✅ VMM differentiation is working correctly!")
    else:
        print("❌ VMM differentiation is not working - need further debugging")
