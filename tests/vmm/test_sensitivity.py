"""
VMM Sensitivity Tests and Wire Tests for Normalization Issues
"""

import pytest
import numpy as np
import pandas as pd
import hashlib
from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig
from src.acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from src.acd.vmm.engine import VMMEngine, VMMConfig


class TestVMMSensitivity:
    """Test VMM sensitivity to coordination strength and normalization issues"""

    @pytest.fixture
    def base_config(self):
        """Base configuration for synthetic data"""
        return CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)

    @pytest.fixture
    def crypto_config(self):
        """Crypto moment configuration"""
        return CryptoMomentConfig()

    @pytest.fixture
    def vmm_config(self):
        """VMM configuration"""
        return VMMConfig()

    def test_coordination_strength_sensitivity(self, base_config, crypto_config, vmm_config):
        """Test that VMM results change monotonically with coordination strength"""
        coordination_strengths = [0.0, 0.25, 0.5, 0.75, 1.0]
        results = []

        for strength in coordination_strengths:
            # Generate data with specific coordination strength
            np.random.seed(42)  # Fixed seed for reproducibility
            generator = SyntheticCryptoGenerator(base_config)

            # Modify generator to use coordination strength parameter
            generator.config.coordination_strength = strength

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

            # Run VMM analysis
            crypto_calculator = CryptoMomentCalculator(crypto_config)
            vmm_engine = VMMEngine(vmm_config, crypto_calculator)

            price_columns = [col for col in data.columns if col.startswith("Exchange_")]
            result = vmm_engine.run_vmm(data, price_columns)

            results.append(
                {
                    "strength": strength,
                    "j_stat": result.over_identification_stat,
                    "p_value": result.over_identification_p_value,
                    "stability": result.structural_stability,
                }
            )

        # Print results table
        print("\nCoordination Strength Sensitivity Test:")
        print("=" * 60)
        print(f"{'Strength':<10} {'J-stat':<10} {'p-value':<10} {'Stability':<10}")
        print("-" * 60)
        for r in results:
            print(
                f"{r['strength']:<10.2f} {r['j_stat']:<10.6f} {r['p_value']:<10.6f} {r['stability']:<10.6f}"
            )

        # Assert monotonic behavior
        j_stats = [r["j_stat"] for r in results]
        p_values = [r["p_value"] for r in results]

        # J-stat should generally increase with coordination strength
        # (allowing for some noise, but trend should be upward)
        j_increases = sum(1 for i in range(1, len(j_stats)) if j_stats[i] > j_stats[i - 1])
        assert (
            j_increases >= 2
        ), f"J-stat should increase with coordination strength, got {j_increases} increases"

        # p-values should generally decrease with coordination strength
        p_decreases = sum(1 for i in range(1, len(p_values)) if p_values[i] < p_values[i - 1])
        assert (
            p_decreases >= 2
        ), f"p-values should decrease with coordination strength, got {p_decreases} decreases"

        # Competitive (strength=0.0) should have p > 0.05
        competitive_p = results[0]["p_value"]
        assert (
            competitive_p > 0.05
        ), f"Competitive scenario should have p > 0.05, got {competitive_p}"

        # High coordination (strength=1.0) should have p < 0.05
        coordinated_p = results[-1]["p_value"]
        assert (
            coordinated_p < 0.05
        ), f"Coordinated scenario should have p < 0.05, got {coordinated_p}"

    def test_moment_vector_differentiation(self, base_config, crypto_config):
        """Test that raw moment vectors are different between competitive and coordinated"""
        np.random.seed(42)

        # Generate both scenarios
        generator = SyntheticCryptoGenerator(base_config)
        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()

        price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]
        calculator = CryptoMomentCalculator(crypto_config)

        # Calculate raw moments (no normalization)
        competitive_moments = calculator.calculate_moments(competitive_data, price_columns)
        coordinated_moments = calculator.calculate_moments(coordinated_data, price_columns)

        # Extract raw moment vectors
        comp_vector = np.concatenate(
            [
                competitive_moments.lead_lag_betas.flatten(),
                competitive_moments.mirroring_ratios.flatten(),
                competitive_moments.spread_floor_dwell_times.flatten(),
                competitive_moments.undercut_initiation_rate.flatten(),
            ]
        )

        coord_vector = np.concatenate(
            [
                coordinated_moments.lead_lag_betas.flatten(),
                coordinated_moments.mirroring_ratios.flatten(),
                coordinated_moments.spread_floor_dwell_times.flatten(),
                coordinated_moments.undercut_initiation_rate.flatten(),
            ]
        )

        # Calculate distances and similarities
        l2_distance = np.linalg.norm(comp_vector - coord_vector)
        cosine_sim = np.dot(comp_vector, coord_vector) / (
            np.linalg.norm(comp_vector) * np.linalg.norm(coord_vector)
        )

        # Calculate hashes
        comp_hash = hashlib.sha256(comp_vector.tobytes()).hexdigest()[:16]
        coord_hash = hashlib.sha256(coord_vector.tobytes()).hexdigest()[:16]

        print(f"\nRaw Moment Vector Analysis:")
        print(f"Competitive hash: {comp_hash}")
        print(f"Coordinated hash: {coord_hash}")
        print(f"L2 distance: {l2_distance:.6f}")
        print(f"Cosine similarity: {cosine_sim:.6f}")

        # Assert differentiation
        assert comp_hash != coord_hash, "Raw moment vectors should have different hashes"
        assert l2_distance > 0.001, f"L2 distance should be > 0.001, got {l2_distance}"
        assert abs(cosine_sim) < 0.99, f"Cosine similarity should be < 0.99, got {cosine_sim}"

    def test_normalization_preserves_differentiation(self, base_config, crypto_config):
        """Test that normalization doesn't collapse differences between datasets"""
        np.random.seed(42)

        # Generate both scenarios
        generator = SyntheticCryptoGenerator(base_config)
        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()

        price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]
        calculator = CryptoMomentCalculator(crypto_config)

        # Calculate moments
        competitive_moments = calculator.calculate_moments(competitive_data, price_columns)
        coordinated_moments = calculator.calculate_moments(coordinated_data, price_columns)

        # Extract moment vectors
        comp_vector = np.concatenate(
            [
                competitive_moments.lead_lag_betas.flatten(),
                competitive_moments.mirroring_ratios.flatten(),
                competitive_moments.spread_floor_dwell_times.flatten(),
                competitive_moments.undercut_initiation_rate.flatten(),
            ]
        )

        coord_vector = np.concatenate(
            [
                coordinated_moments.lead_lag_betas.flatten(),
                coordinated_moments.mirroring_ratios.flatten(),
                coordinated_moments.spread_floor_dwell_times.flatten(),
                coordinated_moments.undercut_initiation_rate.flatten(),
            ]
        )

        # Calculate pre-normalization distances
        pre_l2 = np.linalg.norm(comp_vector - coord_vector)
        pre_cosine = np.dot(comp_vector, coord_vector) / (
            np.linalg.norm(comp_vector) * np.linalg.norm(coord_vector)
        )

        # Apply normalization (min-max scaling)
        combined_vector = np.concatenate([comp_vector, coord_vector])
        min_val = np.min(combined_vector)
        max_val = np.max(combined_vector)

        if max_val > min_val:
            comp_normalized = (comp_vector - min_val) / (max_val - min_val)
            coord_normalized = (coord_vector - min_val) / (max_val - min_val)
        else:
            comp_normalized = comp_vector
            coord_normalized = coord_vector

        # Calculate post-normalization distances
        post_l2 = np.linalg.norm(comp_normalized - coord_normalized)
        post_cosine = np.dot(comp_normalized, coord_normalized) / (
            np.linalg.norm(comp_normalized) * np.linalg.norm(coord_normalized)
        )

        print(f"\nNormalization Impact Analysis:")
        print(f"Pre-normalization  - L2: {pre_l2:.6f}, Cosine: {pre_cosine:.6f}")
        print(f"Post-normalization - L2: {post_l2:.6f}, Cosine: {post_cosine:.6f}")
        print(f"L2 ratio (post/pre): {post_l2/pre_l2:.6f}")
        print(f"Cosine change: {post_cosine - pre_cosine:.6f}")

        # Assert that normalization doesn't collapse differences
        assert post_l2 > 0.001, f"Post-normalization L2 distance should be > 0.001, got {post_l2}"
        assert (
            abs(post_cosine) < 0.99
        ), f"Post-normalization cosine similarity should be < 0.99, got {post_cosine}"

        # L2 distance should not decrease by more than 90%
        assert (
            post_l2 / pre_l2 > 0.1
        ), f"L2 distance should not decrease by more than 90%, ratio: {post_l2/pre_l2}"

    def test_vmm_differentiation_with_global_scaler(self, base_config, crypto_config, vmm_config):
        """Test VMM differentiation with proper global scaling"""
        np.random.seed(42)

        # Generate both scenarios
        generator = SyntheticCryptoGenerator(base_config)
        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()

        price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        # Create VMM engine with crypto calculator
        crypto_calculator = CryptoMomentCalculator(crypto_config)
        vmm_engine = VMMEngine(vmm_config, crypto_calculator)

        # Run VMM analysis on both scenarios
        competitive_result = vmm_engine.run_vmm(competitive_data, price_columns)
        coordinated_result = vmm_engine.run_vmm(coordinated_data, price_columns)

        print(f"\nVMM Differentiation Test:")
        print("=" * 50)
        print(f"{'Scenario':<12} {'J-stat':<10} {'p-value':<10} {'Stability':<10}")
        print("-" * 50)
        print(
            f"{'Competitive':<12} {competitive_result.over_identification_stat:<10.6f} {competitive_result.over_identification_p_value:<10.6f} {competitive_result.structural_stability:<10.6f}"
        )
        print(
            f"{'Coordinated':<12} {coordinated_result.over_identification_stat:<10.6f} {coordinated_result.over_identification_p_value:<10.6f} {coordinated_result.structural_stability:<10.6f}"
        )

        # Assert differentiation
        assert (
            competitive_result.over_identification_stat
            != coordinated_result.over_identification_stat
        ), "J-statistics should be different between scenarios"

        assert (
            competitive_result.over_identification_p_value
            != coordinated_result.over_identification_p_value
        ), "p-values should be different between scenarios"

        assert (
            competitive_result.structural_stability != coordinated_result.structural_stability
        ), "Stability values should be different between scenarios"

        # Assert expected patterns
        assert (
            competitive_result.over_identification_p_value > 0.05
        ), f"Competitive scenario should have p > 0.05, got {competitive_result.over_identification_p_value}"

        assert (
            coordinated_result.over_identification_p_value < 0.05
        ), f"Coordinated scenario should have p < 0.05, got {coordinated_result.over_identification_p_value}"
