#!/usr/bin/env python3
"""
VMM Performance Profiler

This script profiles VMM performance to identify bottlenecks and measure
runtime performance against the <2s p95 target for standard windows.
"""

import cProfile
import io
import sys
import time
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pstats

from generate_golden import generate_competitive_data
from acd.vmm.engine import VMMEngine, run_vmm
from acd.vmm.profiles import VMMConfig

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class VMMProfiler:
    """Performance profiler for VMM continuous monitoring"""

    def __init__(self, config: VMMConfig):
        """Initialize profiler with VMM configuration"""
        self.config = config
        self.engine = VMMEngine(config)
        self.profile_results = []

    def profile_single_run(self, window: pd.DataFrame, price_cols: List[str]) -> Dict:
        """Profile a single VMM run with detailed timing"""

        # Profile the VMM execution
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.time()
        try:
            result = run_vmm(window, self.config)
            success = True
        except Exception as e:
            result = None
            success = False
            error_msg = str(e)

        end_time = time.time()
        profiler.disable()

        # Get profiling statistics
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(20)  # Top 20 functions by cumulative time
        profile_stats = s.getvalue()

        # Extract key timing metrics
        total_time = end_time - start_time

        # Parse profile stats for function-level timing
        function_times = self._parse_profile_stats(profile_stats)

        profile_result = {
            "window_size": len(window),
            "total_time": total_time,
            "success": success,
            "convergence_status": result.convergence_status if result else "failed",
            "iterations": result.iterations if result else 0,
            "elbo_final": result.elbo_final if result else 0.0,
            "function_times": function_times,
            "profile_stats": profile_stats,
            "error_msg": error_msg if not success else None,
        }

        return profile_result

    def _parse_profile_stats(self, profile_stats: str) -> Dict[str, float]:
        """Parse profile statistics to extract function timing"""
        function_times = {}

        for line in profile_stats.split("\n"):
            if "function calls" in line or "ncalls" in line:
                continue
            if line.strip() == "":
                continue

            try:
                # Parse lines like: "1234    0.123    0.001    0.123    0.001 function_name"
                parts = line.strip().split()
                if len(parts) >= 6:
                    ncalls = int(parts[0])
                    total_time = float(parts[1])
                    per_call = float(parts[2])
                    cum_time = float(parts[3])
                    cum_per_call = float(parts[4])
                    function_name = parts[5]

                    function_times[function_name] = {
                        "ncalls": ncalls,
                        "total_time": total_time,
                        "per_call": per_call,
                        "cum_time": cum_time,
                        "cum_per_call": cum_per_call,
                    }
            except (ValueError, IndexError):
                continue

        return function_times

    def profile_batch(self, windows: List[pd.DataFrame], price_cols: List[str]) -> List[Dict]:
        """Profile a batch of VMM runs"""
        print(f"Profiling {len(windows)} VMM runs...")

        for i, window in enumerate(windows):
            print(f"  Run {i+1}/{len(windows)}: {len(window)} data points")
            profile_result = self.profile_single_run(window, price_cols)
            self.profile_results.append(profile_result)

        return self.profile_results

    def analyze_performance(self) -> Dict:
        """Analyze performance results and generate summary"""
        if not self.profile_results:
            return {}

        # Extract timing data
        successful_runs = [r for r in self.profile_results if r["success"]]
        failed_runs = [r for r in self.profile_results if not r["success"]]

        if not successful_runs:
            return {"error": "No successful runs to analyze"}

        # Timing statistics
        run_times = [r["total_time"] for r in successful_runs]

        performance_summary = {
            "total_runs": len(self.profile_results),
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "success_rate": len(successful_runs) / len(self.profile_results),
            # Timing metrics
            "mean_time": np.mean(run_times),
            "median_time": np.median(run_times),
            "std_time": np.std(run_times),
            "min_time": np.min(run_times),
            "max_time": np.max(run_times),
            # Percentile metrics
            "p50_time": np.percentile(run_times, 50),
            "p75_time": np.percentile(run_times, 75),
            "p90_time": np.percentile(run_times, 90),
            "p95_time": np.percentile(run_times, 95),
            "p99_time": np.percentile(run_times, 99),
            # Performance targets
            "target_p95": 2.0,  # seconds
            "target_median": 1.0,  # seconds
            "meets_p95_target": np.percentile(run_times, 95) <= 2.0,
            "meets_median_target": np.median(run_times) <= 1.0,
            # Convergence analysis
            "convergence_stats": self._analyze_convergence(successful_runs),
            # Function-level bottlenecks
            "function_bottlenecks": self._identify_bottlenecks(),
        }

        return performance_summary

    def _analyze_convergence(self, successful_runs: List[Dict]) -> Dict:
        """Analyze convergence patterns"""
        convergence_counts = {}
        iteration_counts = []

        for run in successful_runs:
            status = run["convergence_status"]
            convergence_counts[status] = convergence_counts.get(status, 0) + 1
            iteration_counts.append(run["iterations"])

        return {
            "convergence_distribution": convergence_counts,
            "mean_iterations": np.mean(iteration_counts),
            "median_iterations": np.median(iteration_counts),
            "max_iterations": np.max(iteration_counts),
        }

    def _identify_bottlenecks(self) -> List[Dict]:
        """Identify performance bottlenecks from function timing"""
        if not self.profile_results:
            return []

        # Aggregate function times across all runs
        function_aggregates = {}

        for result in self.profile_results:
            if result["success"] and result["function_times"]:
                for func_name, func_stats in result["function_times"].items():
                    if func_name not in function_aggregates:
                        function_aggregates[func_name] = []
                    function_aggregates[func_name].append(func_stats["cum_time"])

        # Calculate average time per function
        bottlenecks = []
        for func_name, times in function_aggregates.items():
            avg_time = np.mean(times)
            bottlenecks.append(
                {"function": func_name, "avg_time": avg_time, "total_calls": len(times)}
            )

        # Sort by average time (descending)
        bottlenecks.sort(key=lambda x: x["avg_time"], reverse=True)
        return bottlenecks[:10]  # Top 10 bottlenecks

    def generate_performance_report(self, output_dir: str = "reports/performance") -> Path:
        """Generate comprehensive performance report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Analyze performance
        summary = self.analyze_performance()

        # Generate markdown report
        report_path = output_path / "vmm_performance_report.md"

        with open(report_path, "w") as f:
            f.write("# VMM Performance Report\n\n")

            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Runs**: {summary['total_runs']}\n")
            f.write(f"- **Success Rate**: {summary['success_rate']:.1%}\n")
            f.write(f"- **P95 Runtime**: {summary['p95_time']:.3f}s\n")
            f.write(f"- **Target P95**: {summary['target_p95']:.1f}s\n")
            f.write(f"- **Meets P95 Target**: {'✅' if summary['meets_p95_target'] else '❌'}\n")
            f.write(f"- **Median Runtime**: {summary['median_time']:.3f}s\n")
            f.write(f"- **Target Median**: {summary['target_median']:.1f}s\n")
            f.write(
                f"- **Meets Median Target**: {'✅' if summary['meets_median_target'] else '❌'}\n\n"
            )

            f.write("## Detailed Timing Statistics\n\n")
            f.write("| Metric | Value (seconds) |\n")
            f.write("|--------|----------------|\n")
            f.write(f"| Mean | {summary['mean_time']:.3f} |\n")
            f.write(f"| Median | {summary['median_time']:.3f} |\n")
            f.write(f"| Std Dev | {summary['std_time']:.3f} |\n")
            f.write(f"| Min | {summary['min_time']:.3f} |\n")
            f.write(f"| Max | {summary['max_time']:.3f} |\n")
            f.write(f"| P50 | {summary['p50_time']:.3f} |\n")
            f.write(f"| P75 | {summary['p75_time']:.3f} |\n")
            f.write(f"| P90 | {summary['p90_time']:.3f} |\n")
            f.write(f"| P95 | {summary['p95_time']:.3f} |\n")
            f.write(f"| P99 | {summary['p99_time']:.3f} |\n\n")

            f.write("## Convergence Analysis\n\n")
            conv_stats = summary["convergence_stats"]
            f.write(f"- **Mean Iterations**: {conv_stats['mean_iterations']:.1f}\n")
            f.write(f"- **Median Iterations**: {conv_stats['median_iterations']:.1f}\n")
            f.write(f"- **Max Iterations**: {conv_stats['max_iterations']}\n\n")

            f.write("**Convergence Distribution**:\n")
            for status, count in conv_stats["convergence_distribution"].items():
                f.write(f"- {status}: {count} runs\n")
            f.write("\n")

            f.write("## Performance Bottlenecks\n\n")
            bottlenecks = summary["function_bottlenecks"]
            f.write("| Function | Avg Time (s) | Total Calls |\n")
            f.write("|----------|--------------|-------------|\n")
            for bottleneck in bottlenecks:
                f.write(
                    f"| {bottleneck['function']} | "
                    f"{bottleneck['avg_time']:.4f} | "
                    f"{bottleneck['total_calls']} |\n"
                )
            f.write("\n")

            f.write("## Recommendations\n\n")
            if not summary["meets_p95_target"]:
                f.write("- **Critical**: P95 runtime exceeds 2s target\n")
                f.write("- Investigate bottlenecks in top functions\n")
                f.write("- Consider vectorization and caching strategies\n")
            else:
                f.write("- **✅**: P95 runtime meets 2s target\n")

            if not summary["meets_median_target"]:
                f.write("- **Warning**: Median runtime exceeds 1s target\n")
                f.write("- Optimize common execution paths\n")
            else:
                f.write("- **✅**: Median runtime meets 1s target\n")

        # Generate performance plots
        self._generate_performance_plots(output_path)

        print(f"Performance report generated: {report_path}")
        return report_path

    def _generate_performance_plots(self, output_path: Path):
        """Generate performance visualization plots"""
        if not self.profile_results:
            return

        successful_runs = [r for r in self.profile_results if r["success"]]
        if not successful_runs:
            return

        run_times = [r["total_time"] for r in successful_runs]

        # Runtime distribution
        plt.figure(figsize=(12, 8))

        plt.subplot(2, 2, 1)
        plt.hist(run_times, bins=20, alpha=0.7, edgecolor="black")
        plt.axvline(
            np.median(run_times),
            color="red",
            linestyle="--",
            label=f"Median: {np.median(run_times):.3f}s",
        )
        plt.axvline(
            np.percentile(run_times, 95),
            color="orange",
            linestyle="--",
            label=f"P95: {np.percentile(run_times, 95):.3f}s",
        )
        plt.axvline(2.0, color="green", linestyle="-", label="Target P95: 2.0s")
        plt.xlabel("Runtime (seconds)")
        plt.ylabel("Frequency")
        plt.title("VMM Runtime Distribution")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Runtime vs window size
        plt.subplot(2, 2, 2)
        window_sizes = [r["window_size"] for r in successful_runs]
        plt.scatter(window_sizes, run_times, alpha=0.6)
        plt.xlabel("Window Size (data points)")
        plt.ylabel("Runtime (seconds)")
        plt.title("Runtime vs Window Size")
        plt.grid(True, alpha=0.3)

        # Convergence status
        plt.subplot(2, 2, 3)
        convergence_counts = {}
        for run in successful_runs:
            status = run["convergence_status"]
            convergence_counts[status] = convergence_counts.get(status, 0) + 1

        if convergence_counts:
            plt.pie(
                convergence_counts.values(), labels=convergence_counts.keys(), autopct="%1.1f%%"
            )
            plt.title("Convergence Status Distribution")

        # Iterations vs runtime
        plt.subplot(2, 2, 4)
        iterations = [r["iterations"] for r in successful_runs]
        plt.scatter(iterations, run_times, alpha=0.6)
        plt.xlabel("Iterations")
        plt.ylabel("Runtime (seconds)")
        plt.title("Runtime vs Iterations")
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_path / "vmm_performance_plots.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"Performance plots generated: {plot_path}")


def main():
    """Main profiling function"""
    print("🚀 VMM Performance Profiler")
    print("=" * 50)

    # Configuration
    config = VMMConfig(
        window="30D", max_iters=100, tol=1e-4, min_data_points=50  # Reduced for faster profiling
    )

    # Initialize profiler
    profiler = VMMProfiler(config)

    # Generate synthetic test data
    print("📊 Generating synthetic test data...")
    competitive_windows = generate_competitive_data(
        n_windows=10, window_size=100, n_firms=3, seed=42
    )
    competitive_data = pd.concat(competitive_windows, ignore_index=True)

    # Create windows for testing
    window_size = 100
    windows = []
    price_cols = ["firm_0_price", "firm_1_price", "firm_2_price"]

    for i in range(0, len(competitive_data) - window_size + 1, window_size // 2):
        window = competitive_data.iloc[i : i + window_size].copy()
        window.index = pd.date_range("2024-01-01", periods=len(window), freq="H")
        windows.append(window)

    print(f"Created {len(windows)} test windows of size {window_size}")

    # Run profiling
    print("\n🔍 Running VMM performance profiling...")
    profiler.profile_batch(windows, price_cols)

    # Generate report
    print("\n📈 Generating performance report...")
    report_path = profiler.generate_performance_report()

    # Print summary
    summary = profiler.analyze_performance()
    print("\n📋 Performance Summary:")
    print(f"  Total Runs: {summary['total_runs']}")
    print(f"  Success Rate: {summary['success_rate']:.1%}")
    print(f"  P95 Runtime: {summary['p95_time']:.3f}s")
    print(f"  Target P95: {summary['target_p95']:.1f}s")
    print(f"  Meets Target: {'✅' if summary['meets_p95_target'] else '❌'}")

    print(f"\n📄 Detailed report: {report_path}")


if __name__ == "__main__":
    main()
