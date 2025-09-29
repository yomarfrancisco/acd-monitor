"""
VMM Hardening Unit Tests

Tests for VMM stabilization, provenance, and reproducibility.
"""

from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig
from src.acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from src.acd.vmm.scalers import GlobalMomentScaler
from src.acd.vmm.engine import VMMEngine, VMMConfig


class TestVMMHardening:
    """Test VMM hardening and stabilization"""

    @pytest.fixture
    def setup_vmm(self):
        """Setup VMM engine with synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)

        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()
        price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        global_scaler = GlobalMomentScaler(method="minmax")
        crypto_config = CryptoMomentConfig()
        crypto_calculator = CryptoMomentCalculator(crypto_config, global_scaler)
        vmm_config = VMMConfig()
        vmm_engine = VMMEngine(vmm_config, crypto_calculator)

        return vmm_engine, competitive_data, coordinated_data, price_columns

    def test_moment_stabilization_std_bounds(self, setup_vmm):
        """Test that moment stabilization produces std ∈ [0.9, 1.1] for retained components"""
        vmm_engine, competitive_data, _, price_columns = setup_vmm

        # Run VMM to fit stabilizer
        vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check stabilizer parameters
        assert hasattr(vmm_engine, "_per_timestep_scaler")
        assert vmm_engine._per_timestep_scaler.get("fitted", False)

        # Get the stabilized moments
        moment_matrix = vmm_engine._get_per_timestep_moments(competitive_data, price_columns)

        # Apply stabilization pipeline
        moment_matrix_winsorized = np.clip(
            moment_matrix,
            vmm_engine._per_timestep_scaler["q01"],
            vmm_engine._per_timestep_scaler["q99"],
        )

        moment_matrix_centered = moment_matrix_winsorized - vmm_engine._per_timestep_scaler["mu0"]
        moment_matrix_scaled = moment_matrix_centered / vmm_engine._per_timestep_scaler["sigma0"]

        # Check for zero-variance components
        component_stds = np.std(moment_matrix_scaled, axis=0)
        valid_components = component_stds >= 1e-3

        if not np.all(valid_components):
            moment_matrix_scaled = moment_matrix_scaled[:, valid_components]
            component_stds = component_stds[valid_components]

        # Assert std bounds for retained components
        for i, std_val in enumerate(component_stds):
            assert 0.9 <= std_val <= 1.1, f"Component {i} std {std_val} not in [0.9, 1.1]"

    def test_hac_condition_number_bounds(self, setup_vmm):
        """Test that HAC condition number ≤ 1e6"""
        vmm_engine, competitive_data, _, price_columns = setup_vmm

        # Run VMM to fit weight matrix
        vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check condition number
        assert hasattr(vmm_engine, "_weight_matrix_metadata")
        condition_number = vmm_engine._weight_matrix_metadata.get("condition_number", float("inf"))
        ridge_lambda = vmm_engine._weight_matrix_metadata.get("ridge_lambda", 0.0)

        assert (
            condition_number <= 1e6
        ), f"HAC condition number {condition_number} > 1e6, ridge_lambda={ridge_lambda}"

    def test_seeded_p_behavior(self, setup_vmm):
        """Test that seeded synthetic produces correct p-behavior"""
        vmm_engine, competitive_data, coordinated_data, price_columns = setup_vmm

        # Run both scenarios with same seed
        competitive_result = vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )
        coordinated_result = vmm_engine.run_vmm(
            coordinated_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check p-behavior
        assert (
            competitive_result.over_identification_p_value > 0.05
        ), f"Competitive p={competitive_result.over_identification_p_value} should be > 0.05"
        assert (
            coordinated_result.over_identification_p_value < 0.05
        ), f"Coordinated p={coordinated_result.over_identification_p_value} should be < 0.05"

    def test_provenance_persistence(self, setup_vmm):
        """Test that provenance is saved and loaded correctly"""
        vmm_engine, competitive_data, _, price_columns = setup_vmm

        # Run VMM with seed
        vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check provenance file exists
        provenance_file = Path("artifacts/vmm/seed-42/provenance.json")
        assert provenance_file.exists(), "Provenance file not created"

        # Load and validate provenance
        with open(provenance_file, "r") as f:
            provenance = json.load(f)

        # Check required fields
        assert "seed" in provenance
        assert "moment_stabilization" in provenance
        assert "hac_estimation" in provenance
        assert "weight_matrix" in provenance

        # Check moment stabilization parameters
        stab = provenance["moment_stabilization"]
        assert "mu0" in stab
        assert "sigma0" in stab
        assert "q01" in stab
        assert "q99" in stab
        assert "valid_components" in stab
        assert "k_original" in stab
        assert "k_reduced" in stab

        # Check HAC parameters
        hac = provenance["hac_estimation"]
        assert "N" in hac
        assert "k" in hac
        assert "lag" in hac
        assert "ridge_lambda" in hac
        assert "condition_number" in hac

        # Check weight matrix
        wm = provenance["weight_matrix"]
        assert "W_diag" in wm
        assert "W_shape" in wm
        assert "W_condition" in wm

    def test_provenance_reproducibility(self, setup_vmm):
        """Test that loading provenance produces identical results"""
        vmm_engine1, competitive_data, coordinated_data, price_columns = setup_vmm
        vmm_engine2, _, _, _ = setup_vmm

        # Run first engine
        result1 = vmm_engine1.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Run second engine (should load provenance)
        result2 = vmm_engine2.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Results should be identical
        assert abs(result1.over_identification_stat - result2.over_identification_stat) < 1e-10
        assert (
            abs(result1.over_identification_p_value - result2.over_identification_p_value) < 1e-10
        )

    def test_zero_variance_component_handling(self, setup_vmm):
        """Test that zero-variance components are handled correctly"""
        vmm_engine, competitive_data, _, price_columns = setup_vmm

        # Run VMM
        vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check that valid_components is tracked
        assert hasattr(vmm_engine, "_per_timestep_scaler")
        if "valid_components" in vmm_engine._per_timestep_scaler:
            valid_components = vmm_engine._per_timestep_scaler["valid_components"]
            k_reduced = vmm_engine._per_timestep_scaler.get("k_reduced", len(valid_components))

            assert np.sum(valid_components) == k_reduced
            assert k_reduced <= len(valid_components)

    def test_weight_matrix_metadata(self, setup_vmm):
        """Test that weight matrix metadata is complete"""
        vmm_engine, competitive_data, _, price_columns = setup_vmm

        # Run VMM
        vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=42
        )

        # Check metadata
        assert hasattr(vmm_engine, "_weight_matrix_metadata")
        metadata = vmm_engine._weight_matrix_metadata

        required_fields = ["N", "k", "lag", "ridge_lambda", "condition_number"]
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"

        # Check reasonable values
        assert metadata["N"] > 0
        assert metadata["k"] > 0
        assert metadata["lag"] >= 0
        assert metadata["ridge_lambda"] >= 0
        assert metadata["condition_number"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


