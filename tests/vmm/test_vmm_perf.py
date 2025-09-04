"""
VMM Performance Tests

Tests to validate VMM meets performance targets:
- Median runtime ≤ 2s for standard windows
- P95 runtime ≤ 5s for standard windows
"""

import pytest
import time
import numpy as np
import pandas as pd
from pathlib import Path

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from acd.vmm.engine import run_vmm
from acd.vmm.profiles import VMMConfig
from scripts.generate_golden import generate_competitive_data


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
        price_cols = ["firm_0_price", "firm_1_price", "firm_2_price"]

        for i in range(0, len(competitive_data) - window_size + 1, window_size // 2):
            window = competitive_data.iloc[i : i + window_size].copy()
            # Add timestamp index
            window.index = pd.date_range("2024-01-01", periods=len(window), freq="H")
            windows.append(window)

        return windows, price_cols

    @pytest.mark.slow
    def test_vmm_performance_targets(self, vmm_config, test_windows):
        """
        Test that VMM meets performance targets on standard windows

        Targets:
        - Median runtime ≤ 2s
        - P95 runtime ≤ 5s
        """
        windows, price_cols = test_windows

        print(f"\n🔍 Testing VMM performance on {len(windows)} windows...")

        # Run VMM on all windows and measure timing
        run_times = []
        successful_runs = 0

        for i, window in enumerate(windows):
            print(f"  Window {i+1}/{len(windows)}: {len(window)} data points")

            start_time = time.time()
            try:
                result = run_vmm(window, vmm_config)
                end_time = time.time()

                run_time = end_time - start_time
                run_times.append(run_time)
                successful_runs += 1

                print(f"    ✅ Success: {run_time:.3f}s, {result.convergence_status}")

            except Exception as e:
                print(f"    ❌ Failed: {e}")
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

        print(f"\n📊 Performance Results:")
        print(f"  Total Windows: {len(windows)}")
        print(f"  Successful Runs: {successful_runs}")
        print(f"  Success Rate: {successful_runs/len(windows):.1%}")
        print(f"  Mean Runtime: {mean_time:.3f}s")
        print(f"  Median Runtime: {median_time:.3f}s")
        print(f"  Std Dev: {std_time:.3f}s")
        print(f"  P95 Runtime: {p95_time:.3f}s")
        print(f"  P99 Runtime: {p99_time:.3f}s")

        # Performance targets
        median_target = 2.0  # seconds
        p95_target = 5.0  # seconds

        print(f"\n🎯 Performance Targets:")
        print(f"  Median ≤ {median_target}s: {'✅' if median_time <= median_target else '❌'}")
        print(f"  P95 ≤ {p95_target}s: {'✅' if p95_time <= p95_target else '❌'}")

        # Assertions
        assert (
            median_time <= median_target
        ), f"Median runtime {median_time:.3f}s exceeds target {median_target}s"

        assert p95_time <= p95_target, f"P95 runtime {p95_time:.3f}s exceeds target {p95_target}s"

        # Additional quality checks
        assert (
            successful_runs >= len(windows) * 0.9
        ), f"Success rate {successful_runs/len(windows):.1%} below 90% threshold"

        # Check for outliers
        outlier_threshold = 10.0  # seconds
        outliers = run_times[run_times > outlier_threshold]
        assert (
            len(outliers) == 0
        ), f"Found {len(outliers)} runs exceeding {outlier_threshold}s outlier threshold"

        print(f"\n✅ All performance targets met!")

    @pytest.mark.slow
    def test_vmm_scalability(self, vmm_config):
        """
        Test VMM performance scaling with different window sizes

        Verify that runtime scales reasonably with data size
        """
        # Generate data with different sizes
        window_sizes = [50, 100, 200, 300]
        results = {}

        for size in window_sizes:
            print(f"\n🔍 Testing window size: {size}")

            # Generate data
            data = generate_synthetic_data(
                n_samples=size * 2,  # Ensure enough data
                n_firms=3,
                behavior_type="competitive",
                random_state=42,
            )

            # Create window
            window = data.iloc[:size].copy()
            window.index = pd.date_range("2024-01-01", periods=len(window), freq="H")
            price_cols = ["firm_0_price", "firm_1_price", "firm_2_price"]

            # Run VMM and measure time
            start_time = time.time()
            try:
                result = run_vmm(window, vmm_config)
                end_time = time.time()

                run_time = end_time - start_time
                results[size] = {
                    "time": run_time,
                    "success": True,
                    "convergence": result.convergence_status,
                    "iterations": result.iterations,
                }

                print(f"  ✅ Size {size}: {run_time:.3f}s, {result.convergence_status}")

            except Exception as e:
                results[size] = {"time": None, "success": False, "error": str(e)}
                print(f"  ❌ Size {size}: Failed - {e}")

        # Analyze scalability
        successful_sizes = [size for size, result in results.items() if result["success"]]

        if len(successful_sizes) >= 2:
            # Check that runtime scales reasonably (not exponentially)
            times = [results[size]["time"] for size in successful_sizes]
            sizes = successful_sizes

            # Simple scalability check: runtime should not grow faster than O(n²)
            # For small datasets, we expect roughly linear scaling
            expected_linear = times[0] * (np.array(sizes) / sizes[0])
            actual_times = np.array(times)

            # Allow some variance but check for reasonable scaling
            scaling_ratio = actual_times / expected_linear

            print(f"\n📈 Scalability Analysis:")
            print(f"  Window Sizes: {sizes}")
            print(f"  Actual Times: {[f'{t:.3f}s' for t in actual_times]}")
            print(f"  Expected Linear: {[f'{t:.3f}s' for t in expected_linear]}")
            print(f"  Scaling Ratio: {scaling_ratio}")

            # Check that scaling is reasonable (not exponential)
            max_scaling_ratio = max(scaling_ratio)
            assert (
                max_scaling_ratio < 5.0
            ), f"Scaling ratio {max_scaling_ratio:.2f} suggests poor scalability"

            print(f"  ✅ Scalability check passed (max ratio: {max_scaling_ratio:.2f})")

        # Ensure at least some sizes work
        assert (
            len(successful_sizes) >= 2
        ), f"Need at least 2 successful runs for scalability analysis, got {len(successful_sizes)}"

    def test_vmm_convergence_efficiency(self, vmm_config, test_windows):
        """
        Test that VMM converges efficiently (not too many iterations)

        This affects overall performance
        """
        windows, price_cols = test_windows

        # Test on a subset for speed
        test_subset = windows[:5]

        print(f"\n🔍 Testing convergence efficiency on {len(test_subset)} windows...")

        iteration_counts = []
        convergence_statuses = []

        for i, window in enumerate(test_subset):
            try:
                result = run_vmm(window, vmm_config)
                iteration_counts.append(result.iterations)
                convergence_statuses.append(result.convergence_status)

                print(
                    f"  Window {i+1}: {result.iterations} iterations, {result.convergence_status}"
                )

            except Exception as e:
                print(f"  Window {i+1}: Failed - {e}")
                continue

        if not iteration_counts:
            pytest.fail("No successful runs to analyze convergence")

        # Convergence efficiency metrics
        mean_iterations = np.mean(iteration_counts)
        median_iterations = np.median(iteration_counts)
        max_iterations = max(iteration_counts)

        print(f"\n📊 Convergence Efficiency:")
        print(f"  Mean Iterations: {mean_iterations:.1f}")
        print(f"  Median Iterations: {median_iterations:.1f}")
        print(f"  Max Iterations: {max_iterations}")

        # Efficiency targets
        max_iterations_target = vmm_config.max_iters * 0.8  # Should converge before max
        mean_iterations_target = vmm_config.max_iters * 0.5  # Average should be much lower

        print(f"\n🎯 Efficiency Targets:")
        print(
            f"  Max ≤ {max_iterations_target:.0f}: {'✅' if max_iterations <= max_iterations_target else '❌'}"
        )
        print(
            f"  Mean ≤ {mean_iterations_target:.0f}: {'✅' if mean_iterations <= mean_iterations_target else '❌'}"
        )

        # Assertions
        assert (
            max_iterations <= max_iterations_target
        ), f"Max iterations {max_iterations} exceeds target {max_iterations_target:.0f}"

        assert (
            mean_iterations <= mean_iterations_target
        ), f"Mean iterations {mean_iterations:.1f} exceeds target {mean_iterations_target:.0f}"

        # Check convergence quality
        converged_count = sum(1 for status in convergence_statuses if status == "converged")
        convergence_rate = converged_count / len(convergence_statuses)

        assert (
            convergence_rate >= 0.8
        ), f"Convergence rate {convergence_rate:.1%} below 80% threshold"

        print(f"  ✅ Convergence efficiency targets met!")
        print(f"  ✅ Convergence rate: {convergence_rate:.1%}")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
