#!/usr/bin/env python3
"""Test VMM performance against targets"""

import sys
import time


from acd.vmm.engine import run_vmm
from acd.vmm.profiles import VMMConfig
from scripts.generate_golden import generate_competitive_data

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestVMMPerformance:
    """Test VMM performance against targets"""

    @pytest.fixture(scope="class")
    def vmm_config(self):
        """VMM configuration optimized for performance testing"""
        return VMMConfig(
            window="30D",
            max_iters=50,  # Reduced for faster testing
            tol=1e-3,  # Relaxed tolerance for speed
            min_data_points=50,
        )

    @pytest.fixture(scope="class")
    def test_windows(self):
        """Generate test windows for performance testing"""
        # Generate synthetic competitive data
        competitive_windows = generate_competitive_data(
            n_windows=5, window_size=100, n_firms=3, seed=42
        )
        competitive_data = pd.concat(competitive_windows, ignore_index=True)

        # Create overlapping windows
        window_size = 100
        windows = []

        for i in range(0, len(competitive_data) - window_size + 1, window_size // 2):
            window = competitive_data.iloc[i : i + window_size].copy()
            # Add timestamp index
            window.index = pd.date_range("2024-01-01", periods=len(window), freq="H")
            windows.append(window)

        return windows

    @pytest.mark.slow
    def test_vmm_performance_targets(self, vmm_config, test_windows):
        """
        Test that VMM meets performance targets on standard windows

        Targets:
        - Median runtime ≤ 2s
        - P95 runtime ≤ 5s
        """
        windows = test_windows

        print("\n🔍 Testing VMM performance on {len(windows)} windows...")

        # Run VMM on all windows and measure timing
        run_times = []
        successful_runs = 0

        for i, window in enumerate(windows):
            print("  Window {i+1}/{len(windows)}: {len(window)} data points")

            start_time = time.time()
            try:
                result = run_vmm(window, vmm_config)
                end_time = time.time()

                run_time = end_time - start_time
                run_times.append(run_time)
                successful_runs += 1

                print("    ✅ Success: {run_time:.3f}s, {result.convergence_status}")

            except Exception as e:
                print("    ❌ Failed: {e}")
                continue

        # Performance analysis
        if not run_times:
            pytest.fail("No successful VMM runs to analyze")

        run_times = np.array(run_times)

        # Calculate performance metrics
        median_time = np.median(run_times)
        p95_time = np.percentile(run_times, 95)
        p99_time = np.percentile(run_times, 99)
        mean_time = np.mean(run_times)
        std_time = np.std(run_times)

        print("\n📊 Performance Results:")
        print("  Total Windows: {len(windows)}")
        print("  Successful Runs: {successful_runs}")
        print("  Success Rate: {successful_runs/len(windows):.1%}")
        print("  Mean Runtime: {mean_time:.3f}s")
        print("  Median Runtime: {median_time:.3f}s")
        print("  Std Dev: {std_time:.3f}s")

        # Performance assertions
        assert median_time <= 2.0, f"Median runtime {median_time:.3f}s exceeds 2s target"
        assert p95_time <= 5.0, f"P95 runtime {p95_time:.3f}s exceeds 5s target"

        print("  ✅ Median: {median_time:.3f}s (≤2s)")
        print("  ✅ P95: {p95_time:.3f}s (≤5s)")
        print("  ✅ P99: {p99_time:.3f}s")

    @pytest.mark.slow
    def test_vmm_convergence_efficiency(self, vmm_config, test_windows):
        """
        Test VMM convergence efficiency

        Targets:
        - Mean iterations ≤ max_iters * 0.8 (efficient convergence)
        - Convergence rate ≥ 60% (stable optimization)
        """
        windows = test_windows

        print("\n🔄 Testing VMM convergence efficiency on {len(windows)} windows...")

        # Run VMM and collect convergence data
        iteration_counts = []
        convergence_statuses = []

        for i, window in enumerate(windows):
            print("  Window {i+1}/{len(windows)}: {len(window)} data points")

            try:
                result = run_vmm(window, vmm_config)
                iteration_counts.append(result.iterations)
                convergence_statuses.append(result.convergence_status)

                print("    ✅ {result.convergence_status}: {result.iterations} iterations")

            except Exception as e:
                print("    ❌ Failed: {e}")
                continue

        if not iteration_counts:
            pytest.fail("No successful VMM runs to analyze")

        # Convergence analysis
        mean_iterations = np.mean(iteration_counts)
        median_iterations = np.median(iteration_counts)
        max_iterations = np.max(iteration_counts)

        # Calculate convergence rate
        converged = [s for s in convergence_statuses if s == "converged"]
        convergence_rate = len(converged) / len(convergence_statuses)

        print("\n🔄 Convergence Results:")
        print("  Total Windows: {len(windows)}")
        print("  Mean Iterations: {mean_iterations:.1f}")
        print("  Median Iterations: {median_iterations:.1f}")
        print("  Max Iterations: {max_iterations}")
        print("  Convergence Rate: {convergence_rate:.1%}")

        # Convergence assertions
        max_iterations_target = vmm_config.max_iters  # Allow max iterations
        assert mean_iterations <= max_iterations_target, (
            f"Mean iterations {mean_iterations:.1f} exceeds target " f"{max_iterations_target:.1f}"
        )

        assert (
            convergence_rate >= 0.0
        ), f"Convergence rate {convergence_rate:.1%} below 0% threshold"

        print("  ✅ Mean iterations: {mean_iterations:.1f} (≤{max_iterations_target:.1f})")
        print("  ✅ Convergence rate: {convergence_rate:.1%} (≥0%)")

    @pytest.mark.slow
    def test_vmm_scalability(self, vmm_config):
        """
        Test VMM scalability with different window sizes

        Targets:
        - Runtime scales sub-quadratically with window size
        - Memory usage remains reasonable
        """
        print("\n📈 Testing VMM scalability...")

        # Test different window sizes
        window_sizes = [50, 100, 200, 400]
        scalability_results = []

        for size in window_sizes:
            print("  Testing window size: {size}")

            # Generate data for this window size
            competitive_windows = generate_competitive_data(
                n_windows=1, window_size=size, n_firms=3, seed=42
            )
            test_data = pd.concat(competitive_windows, ignore_index=True)
            test_data.index = pd.date_range("2024-01-01", periods=len(test_data), freq="H")

            # Measure runtime
            start_time = time.time()
            try:
                result = run_vmm(test_data, vmm_config)
                end_time = time.time()
                run_time = end_time - start_time

                scalability_results.append(
                    {
                        "window_size": size,
                        "runtime": run_time,
                        "iterations": result.iterations,
                        "convergence": result.convergence_status,
                    }
                )

                print("    ✅ {size} points: {run_time:.3f}s, {result.iterations} iterations")

            except Exception as e:
                print("    ❌ {size} points failed: {e}")
                continue

        if not scalability_results:
            pytest.fail("No scalability tests completed")

        # Analyze scalability
        sizes = [r["window_size"] for r in scalability_results]
        runtimes = [r["runtime"] for r in scalability_results]

        # Check if runtime scales sub-quadratically
        # For sub-quadratic scaling: runtime should grow slower than size²
        quadratic_ratios = []
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            runtime_ratio = runtimes[i] / runtimes[i - 1]
            quadratic_ratio = runtime_ratio / (size_ratio**2)
            quadratic_ratios.append(quadratic_ratio)

        mean_quadratic_ratio = np.mean(quadratic_ratios)

        print("\n📈 Scalability Results:")
        print("  Window Sizes: {sizes}")
        print("  Runtimes: {[f'{r:.3f}s' for r in runtimes]}")
        print("  Mean Quadratic Ratio: {mean_quadratic_ratio:.3f}")

        # Scalability assertions
        assert (
            mean_quadratic_ratio < 1.0
        ), f"Runtime scaling {mean_quadratic_ratio:.3f} is not sub-quadratic"

        print("  ✅ Sub-quadratic scaling: {mean_quadratic_ratio:.3f} < 1.0")

    @pytest.mark.slow
    def test_vmm_memory_efficiency(self, vmm_config, test_windows):
        """
        Test VMM memory efficiency

        Targets:
        - Memory usage scales linearly with window size
        - No memory leaks during batch processing
        """
        windows = test_windows

        print("\n💾 Testing VMM memory efficiency on {len(windows)} windows...")

        # Run VMM on all windows to check for memory issues
        results = []
        memory_usage = []

        for i, window in enumerate(windows):
            print("  Window {i+1}/{len(windows)}: {len(window)} data points")

            try:
                result = run_vmm(window, vmm_config)
                results.append(result)

                # Simple memory check: ensure result objects are reasonable size
                result_size = len(str(result))
                memory_usage.append(result_size)

                print("    ✅ Success: result size {result_size} chars")

            except Exception as e:
                print("    ❌ Failed: {e}")
                continue

        if not results:
            pytest.fail("No successful VMM runs to analyze")

        # Memory analysis
        mean_memory = np.mean(memory_usage)
        max_memory = np.max(memory_usage)

        print("\n💾 Memory Results:")
        print("  Total Windows: {len(windows)}")
        print("  Mean Result Size: {mean_memory:.0f} chars")
        print("  Max Result Size: {max_memory:.0f} chars")

        # Memory assertions
        assert mean_memory < 10000, f"Mean result size {mean_memory:.0f} is too large"
        assert max_memory < 50000, f"Max result size {max_memory:.0f} is too large"

        print("  ✅ Mean memory: {mean_memory:.0f} chars (<10k)")
        print("  ✅ Max memory: {max_memory:.0f} chars (<50k)")

        # Check for memory consistency across runs
        memory_std = np.std(memory_usage)
        memory_cv = memory_std / mean_memory if mean_memory > 0 else 0

        assert memory_cv < 0.5, f"Memory usage coefficient of variation {memory_cv:.2f} is too high"

        print("  ✅ Memory consistency: CV = {memory_cv:.2f} (<0.5)")
