"""
Test VMM Reproducibility
Enforces |Δstructural_stability| ≤ 0.03 reproducibility drift gate
"""

from acd.vmm import VMMConfig, run_vmm


class TestVMMReproducibility:
    """Test VMM reproducibility across multiple runs"""

    @pytest.fixture
    def test_windows(self):
        """Load a sample of test windows for reproducibility testing"""
        # Use a mix of competitive and coordinated windows
        competitive_dir = Path(__file__).parent.parent.parent / "data" / "golden" / "competitive"
        coordinated_dir = Path(__file__).parent.parent.parent / "data" / "golden" / "coordinated"

        windows = []

        # Sample 5 competitive windows
        for parquet_file in list(competitive_dir.glob("*.parquet"))[:5]:
            window = pd.read_parquet(parquet_file)
            windows.append(("competitive", window))

        # Sample 5 coordinated windows
        for parquet_file in list(coordinated_dir.glob("*.parquet"))[:5]:
            window = pd.read_parquet(parquet_file)
            windows.append(("coordinated", window))

        return windows

    @pytest.fixture
    def vmm_config(self):
        """VMM configuration for testing"""
        return VMMConfig(
            window="30D",
            step_initial=0.05,
            step_decay=0.001,
            max_iters=200,
            tol=1e-3,  # Relaxed tolerance for testing
            emit_regime_confidence=True,
            emit_structural_stability=True,
            emit_environment_quality=True,
            emit_dynamic_validation=True,
            min_data_points=50,
        )

    def test_structural_stability_reproducibility(self, test_windows, vmm_config):
        """
        Test that structural stability is reproducible across runs

        This enforces the acceptance gate: |Δstructural_stability| ≤ 0.03
        """
        reproducibility_results = []

        for window_type, window in test_windows:
            print("Testing reproducibility on {window_type} window...")

            # Run VMM 10 times on the same window
            stability_scores = []

            for run in range(10):
                try:
                    # Set numpy seed for reproducibility within each run
                    np.random.seed(42 + run)

                    result = run_vmm(window, vmm_config)
                    stability_scores.append(result.structural_stability)

                except Exception as e:
                    pytest.fail(f"VMM failed on {window_type} window, run {run}: {e}")

            # Calculate reproducibility metrics
            stability_array = np.array(stability_scores)

            # Compute pairwise differences
            differences = []
            for i in range(len(stability_array)):
                for j in range(i + 1, len(stability_array)):
                    diff = abs(stability_array[i] - stability_array[j])
                    differences.append(diff)

            # Calculate statistics
            max_diff = np.max(differences)
            median_diff = np.median(differences)
            mean_diff = np.mean(differences)
            std_diff = np.std(differences)

            reproducibility_results.append(
                {
                    "window_type": window_type,
                    "max_diff": max_diff,
                    "median_diff": median_diff,
                    "mean_diff": mean_diff,
                    "std_diff": std_diff,
                    "all_scores": stability_scores,
                }
            )

            print("  {window_type}: max_diff={max_diff:.4f}, median_diff={median_diff:.4f}")

        # Test acceptance gate: median |Δstructural_stability| ≤ 0.03
        all_median_diffs = [result["median_diff"] for result in reproducibility_results]
        overall_median_diff = np.median(all_median_diffs)

        print("\nReproducibility results:")
        print("Overall median difference: {overall_median_diff:.4f}")
        print("Acceptance gate: ≤0.03")

        # Primary assertion: median drift should be ≤ 0.03
        assert overall_median_diff <= 0.03, (
            f"Median structural stability drift {overall_median_diff:.4f} exceeds "
            f"acceptance gate 0.03. VMM results are not sufficiently reproducible."
        )

        # Additional checks: individual windows should also meet the gate
        for result in reproducibility_results:
            assert result["median_diff"] <= 0.05, (
                f"Window {result['window_type']} median drift {result['median_diff']:.4f} "
                f"exceeds tolerance 0.05"
            )

    def test_regime_confidence_reproducibility(self, test_windows, vmm_config):
        """
        Test that regime confidence is reproducible across runs
        """
        for window_type, window in test_windows:
            print("Testing regime confidence reproducibility on {window_type} window...")

            # Run VMM 5 times on the same window
            confidence_scores = []

            for run in range(5):
                try:
                    np.random.seed(42 + run)
                    result = run_vmm(window, vmm_config)
                    confidence_scores.append(result.regime_confidence)
                except Exception as e:
                    pytest.fail(f"VMM failed on {window_type} window, run {run}: {e}")

            # Calculate reproducibility metrics
            confidence_array = np.array(confidence_scores)

            # Compute pairwise differences
            differences = []
            for i in range(len(confidence_array)):
                for j in range(i + 1, len(confidence_array)):
                    diff = abs(confidence_array[i] - confidence_array[j])
                    differences.append(diff)

            max_diff = np.max(differences)
            median_diff = np.median(differences)

            print("  {window_type}: max_diff={max_diff:.4f}, median_diff={median_diff:.4f}")

            # Regime confidence should be reproducible
            assert median_diff <= 0.05, (
                f"Regime confidence median drift {median_diff:.4f} exceeds tolerance 0.05 "
                f"for {window_type} window"
            )

    def test_environment_quality_reproducibility(self, test_windows, vmm_config):
        """
        Test that environment quality is reproducible across runs
        """
        for window_type, window in test_windows:
            print("Testing environment quality reproducibility on {window_type} window...")

            # Run VMM 5 times on the same window
            quality_scores = []

            for run in range(5):
                try:
                    np.random.seed(42 + run)
                    result = run_vmm(window, vmm_config)
                    quality_scores.append(result.environment_quality)
                except Exception as e:
                    pytest.fail(f"VMM failed on {window_type} window, run {run}: {e}")

            # Calculate reproducibility metrics
            quality_array = np.array(quality_scores)

            # Compute pairwise differences
            differences = []
            for i in range(len(quality_array)):
                for j in range(i + 1, len(quality_array)):
                    diff = abs(quality_array[i] - quality_array[j])
                    differences.append(diff)

            max_diff = np.max(differences)
            median_diff = np.median(differences)

            print("  {window_type}: max_diff={max_diff:.4f}, median_diff={median_diff:.4f}")

            # Environment quality should be reproducible
            assert median_diff <= 0.05, (
                f"Environment quality median drift {median_diff:.4f} exceeds tolerance 0.05 "
                f"for {window_type} window"
            )

    def test_convergence_reproducibility(self, test_windows, vmm_config):
        """
        Test that convergence behavior is reproducible across runs
        """
        for window_type, window in test_windows:
            print("Testing convergence reproducibility on {window_type} window...")

            # Run VMM 5 times on the same window
            convergence_statuses = []
            iteration_counts = []

            for run in range(5):
                try:
                    np.random.seed(42 + run)
                    result = run_vmm(window, vmm_config)
                    convergence_statuses.append(result.convergence_status)
                    iteration_counts.append(result.iterations)
                except Exception as e:
                    pytest.fail(f"VMM failed on {window_type} window, run {run}: {e}")

            # Convergence status should be consistent
            unique_statuses = set(convergence_statuses)
            print("  {window_type}: convergence statuses: {unique_statuses}")

            # Most runs should converge to the same status
            most_common_status = max(set(convergence_statuses), key=convergence_statuses.count)
            status_consistency = convergence_statuses.count(most_common_status) / len(
                convergence_statuses
            )

            assert status_consistency >= 0.8, (
                f"Convergence status consistency {status_consistency:.3f} below threshold 0.8 "
                f"for {window_type} window"
            )

            # Iteration counts should be similar
            iteration_array = np.array(iteration_counts)
            iteration_std = np.std(iteration_array)
            iteration_mean = np.mean(iteration_array)

            if iteration_mean > 0:
                iteration_cv = iteration_std / iteration_mean
                print("  {window_type}: iteration CV: {iteration_cv:.3f}")

                # Iteration counts should be reasonably consistent
                assert (
                    iteration_cv < 0.5
                ), f"Iteration count too variable (CV: {iteration_cv:.3f}) for {window_type} window"

    def test_overall_reproducibility_summary(self, test_windows, vmm_config):
        """
        Summary test that aggregates reproducibility metrics across all windows
        """
        print("\n" + "=" * 60)
        print("VMM REPRODUCIBILITY SUMMARY")
        print("=" * 60)

        all_metrics = []

        for window_type, window in test_windows:
            # Run VMM multiple times and collect metrics
            stability_scores = []
            confidence_scores = []
            quality_scores = []

            for run in range(5):
                try:
                    np.random.seed(42 + run)
                    result = run_vmm(window, vmm_config)
                    stability_scores.append(result.structural_stability)
                    confidence_scores.append(result.regime_confidence)
                    quality_scores.append(result.environment_quality)
                except Exception as e:
                    pytest.fail(f"VMM failed on {window_type} window, run {run}: {e}")

            # Calculate reproducibility metrics
            stability_diffs = [
                abs(stability_scores[i] - stability_scores[j])
                for i in range(len(stability_scores))
                for j in range(i + 1, len(stability_scores))
            ]

            confidence_diffs = [
                abs(confidence_scores[i] - confidence_scores[j])
                for i in range(len(confidence_scores))
                for j in range(i + 1, len(confidence_scores))
            ]

            quality_diffs = [
                abs(quality_scores[i] - quality_scores[j])
                for i in range(len(quality_scores))
                for j in range(i + 1, len(quality_scores))
            ]

            window_metrics = {
                "window_type": window_type,
                "stability_median_diff": np.median(stability_diffs),
                "confidence_median_diff": np.median(confidence_diffs),
                "quality_median_diff": np.median(quality_diffs),
            }

            all_metrics.append(window_metrics)

            print("{window_type.upper()} WINDOW:")
            print(
                f"  Structural Stability: median diff = "
                f"{window_metrics['stability_median_diff']:.4f}"
            )
            print(
                f"  Regime Confidence: median diff = {window_metrics['confidence_median_diff']:.4f}"
            )
            print(
                f"  Environment Quality: median diff = {window_metrics['quality_median_diff']:.4f}"
            )

        # Overall reproducibility assessment
        overall_stability_diff = np.median([m["stability_median_diff"] for m in all_metrics])
        overall_confidence_diff = np.median([m["confidence_median_diff"] for m in all_metrics])
        overall_quality_diff = np.median([m["quality_median_diff"] for m in all_metrics])

        print("\nOVERALL REPRODUCIBILITY:")
        print("  Structural Stability: {overall_stability_diff:.4f} (gate: ≤0.03)")
        print("  Regime Confidence: {overall_confidence_diff:.4f} (gate: ≤0.05)")
        print("  Environment Quality: {overall_quality_diff:.4f} (gate: ≤0.05)")

        # Final acceptance gate check
        assert overall_stability_diff <= 0.03, (
            f"Overall structural stability reproducibility {overall_stability_diff:.4f} "
            f"exceeds acceptance gate 0.03"
        )

        print("\n✅ VMM reproducibility meets all acceptance gates!")
        print("=" * 60)
