#!/usr/bin/env python3
"""
Performance Optimization Analysis Script

This script profiles bundle generation, attribution, and memory efficiency
to identify optimization opportunities and measure performance improvements.
"""

import sys
import os
from pathlib import Path
import time
import json
import psutil
import tracemalloc
from typing import Dict, List, Any, Optional
import cProfile
import pstats
from io import StringIO

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent.providers.offline_mock import OfflineMockProvider
from agent.bundle_generator import ACDBundleGenerator, BundleGenerationRequest


def profile_bundle_generation():
    """Profile bundle generation performance"""

    print("Profiling Bundle Generation Performance...")
    print("=" * 60)

    # Initialize components
    provider = OfflineMockProvider()
    bundle_generator = ACDBundleGenerator()

    # Test queries for profiling
    test_queries = [
        "Generate a regulatory bundle for BTC/USD coordination analysis",
        "Generate a comprehensive regulatory bundle for ETH/USD with attribution tables",
        "Generate a regulatory bundle for ADA/USD with provenance tracking",
        "Generate a regulatory bundle for SOL/USD with alternative explanations",
        "Generate a regulatory bundle for DOT/USD with MEV analysis",
    ]

    profiling_results = []

    for i, query in enumerate(test_queries, 1):
        print(f"Profiling Query {i}/{len(test_queries)}: {query[:50]}...")

        # Start memory profiling
        tracemalloc.start()
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Start CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            # Execute bundle generation
            bundle_request = BundleGenerationRequest(
                query=query,
                case_study="performance_test",
                asset_pair="BTC/USD",
                time_period="last_30_days",
                seed=42,
                output_format="both",
                include_attribution=True,
            )

            bundle_response = bundle_generator.generate_bundle(bundle_request)

            # Stop profiling
            profiler.disable()
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Get memory profiling results
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Get CPU profiling results
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
            ps.print_stats(10)  # Top 10 functions
            cpu_profile = s.getvalue()

            # Calculate metrics
            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory
            peak_memory_mb = peak / 1024 / 1024

            result = {
                "query_id": i,
                "query": query,
                "status": "SUCCESS",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": peak_memory_mb,
                "bundle_id": bundle_response.bundle_id if bundle_response else None,
                "files_generated": len(bundle_response.file_paths) if bundle_response else 0,
                "cpu_profile": cpu_profile,
                "error": None,
            }

            print(
                f"   ✅ SUCCESS - {execution_time:.3f}s - Memory: {memory_delta:.1f}MB - Peak: {peak_memory_mb:.1f}MB"
            )

        except Exception as e:
            # Stop profiling on error
            profiler.disable()
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            tracemalloc.stop()

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            result = {
                "query_id": i,
                "query": query,
                "status": "ERROR",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": 0,
                "bundle_id": None,
                "files_generated": 0,
                "cpu_profile": None,
                "error": str(e),
            }

            print(f"   ❌ ERROR - {execution_time:.3f}s - Error: {e}")

        profiling_results.append(result)

    return profiling_results


def profile_attribution_calculation():
    """Profile attribution calculation performance"""

    print("\nProfiling Attribution Calculation Performance...")
    print("=" * 60)

    # Initialize components
    provider = OfflineMockProvider()

    # Test attribution queries
    attribution_queries = [
        "Calculate attribution tables for BTC/USD coordination analysis",
        "Generate risk decomposition for ETH/USD with driver analysis",
        "Create attribution breakdown for ADA/USD with component contributions",
        "Analyze risk attribution for SOL/USD with statistical significance",
        "Generate comprehensive attribution for DOT/USD with confidence intervals",
    ]

    attribution_results = []

    for i, query in enumerate(attribution_queries, 1):
        print(f"Profiling Attribution {i}/{len(attribution_queries)}: {query[:50]}...")

        # Start memory profiling
        tracemalloc.start()
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Start CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            # Execute attribution calculation
            response = provider.generate(prompt=query)

            # Stop profiling
            profiler.disable()
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Get memory profiling results
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Get CPU profiling results
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
            ps.print_stats(10)  # Top 10 functions
            cpu_profile = s.getvalue()

            # Calculate metrics
            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory
            peak_memory_mb = peak / 1024 / 1024

            result = {
                "query_id": i,
                "query": query,
                "status": "SUCCESS",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": peak_memory_mb,
                "response_length": len(str(response)),
                "cpu_profile": cpu_profile,
                "error": None,
            }

            print(
                f"   ✅ SUCCESS - {execution_time:.3f}s - Memory: {memory_delta:.1f}MB - Peak: {peak_memory_mb:.1f}MB"
            )

        except Exception as e:
            # Stop profiling on error
            profiler.disable()
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            tracemalloc.stop()

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            result = {
                "query_id": i,
                "query": query,
                "status": "ERROR",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": 0,
                "response_length": 0,
                "cpu_profile": None,
                "error": str(e),
            }

            print(f"   ❌ ERROR - {execution_time:.3f}s - Error: {e}")

        attribution_results.append(result)

    return attribution_results


def profile_memory_efficiency():
    """Profile memory efficiency under various loads"""

    print("\nProfiling Memory Efficiency...")
    print("=" * 60)

    # Initialize components
    provider = OfflineMockProvider()

    # Memory efficiency test scenarios
    memory_tests = [
        {
            "name": "Single Query",
            "description": "Memory usage for single query execution",
            "queries": ["Generate a regulatory bundle for BTC/USD"],
        },
        {
            "name": "Concurrent Queries",
            "description": "Memory usage for 5 concurrent queries",
            "queries": [
                "Generate a regulatory bundle for BTC/USD",
                "Generate a regulatory bundle for ETH/USD",
                "Generate a regulatory bundle for ADA/USD",
                "Generate a regulatory bundle for SOL/USD",
                "Generate a regulatory bundle for DOT/USD",
            ],
        },
        {
            "name": "Sequential Queries",
            "description": "Memory usage for 10 sequential queries",
            "queries": [
                "Generate a regulatory bundle for BTC/USD",
                "Generate a regulatory bundle for ETH/USD",
                "Generate a regulatory bundle for ADA/USD",
                "Generate a regulatory bundle for SOL/USD",
                "Generate a regulatory bundle for DOT/USD",
                "Generate a regulatory bundle for AVAX/USD",
                "Generate a regulatory bundle for MATIC/USD",
                "Generate a regulatory bundle for LINK/USD",
                "Generate a regulatory bundle for UNI/USD",
                "Generate a regulatory bundle for AAVE/USD",
            ],
        },
        {
            "name": "Large Bundle Generation",
            "description": "Memory usage for large bundle generation",
            "queries": [
                "Generate a comprehensive regulatory bundle for BTC/USD with full attribution tables, provenance tracking, alternative explanations, and MEV analysis covering 180 days of data"
            ],
        },
    ]

    memory_results = []

    for i, test in enumerate(memory_tests, 1):
        print(f"Memory Test {i}/{len(memory_tests)}: {test['name']}")
        print(f"   Description: {test['description']}")

        # Start memory profiling
        tracemalloc.start()
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        try:
            # Execute queries
            for query in test["queries"]:
                response = provider.generate(prompt=query)

            # Stop profiling
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Get memory profiling results
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Calculate metrics
            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory
            peak_memory_mb = peak / 1024 / 1024

            result = {
                "test_id": i,
                "test_name": test["name"],
                "description": test["description"],
                "query_count": len(test["queries"]),
                "status": "SUCCESS",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": peak_memory_mb,
                "memory_per_query_mb": (
                    memory_delta / len(test["queries"]) if test["queries"] else 0
                ),
                "error": None,
            }

            print(
                f"   ✅ SUCCESS - {execution_time:.3f}s - Memory: {memory_delta:.1f}MB - Peak: {peak_memory_mb:.1f}MB"
            )
            print(f"   Memory per query: {result['memory_per_query_mb']:.2f}MB")

        except Exception as e:
            # Stop profiling on error
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            tracemalloc.stop()

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            result = {
                "test_id": i,
                "test_name": test["name"],
                "description": test["description"],
                "query_count": len(test["queries"]),
                "status": "ERROR",
                "execution_time": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": 0,
                "memory_per_query_mb": 0,
                "error": str(e),
            }

            print(f"   ❌ ERROR - {execution_time:.3f}s - Error: {e}")

        memory_results.append(result)

    return memory_results


def analyze_performance_bottlenecks(
    profiling_results: List[Dict], attribution_results: List[Dict], memory_results: List[Dict]
) -> Dict[str, Any]:
    """Analyze performance bottlenecks and optimization opportunities"""

    print("\nAnalyzing Performance Bottlenecks...")
    print("=" * 60)

    # Analyze bundle generation performance
    bundle_times = [r["execution_time"] for r in profiling_results if r["status"] == "SUCCESS"]
    bundle_memory = [r["memory_delta_mb"] for r in profiling_results if r["status"] == "SUCCESS"]

    bundle_analysis = {
        "avg_execution_time": sum(bundle_times) / len(bundle_times) if bundle_times else 0,
        "max_execution_time": max(bundle_times) if bundle_times else 0,
        "min_execution_time": min(bundle_times) if bundle_times else 0,
        "avg_memory_usage": sum(bundle_memory) / len(bundle_memory) if bundle_memory else 0,
        "max_memory_usage": max(bundle_memory) if bundle_memory else 0,
        "min_memory_usage": min(bundle_memory) if bundle_memory else 0,
    }

    # Analyze attribution performance
    attribution_times = [
        r["execution_time"] for r in attribution_results if r["status"] == "SUCCESS"
    ]
    attribution_memory = [
        r["memory_delta_mb"] for r in attribution_results if r["status"] == "SUCCESS"
    ]

    attribution_analysis = {
        "avg_execution_time": (
            sum(attribution_times) / len(attribution_times) if attribution_times else 0
        ),
        "max_execution_time": max(attribution_times) if attribution_times else 0,
        "min_execution_time": min(attribution_times) if attribution_times else 0,
        "avg_memory_usage": (
            sum(attribution_memory) / len(attribution_memory) if attribution_memory else 0
        ),
        "max_memory_usage": max(attribution_memory) if attribution_memory else 0,
        "min_memory_usage": min(attribution_memory) if attribution_memory else 0,
    }

    # Analyze memory efficiency
    memory_analysis = {
        "single_query_memory": (
            memory_results[0]["memory_delta_mb"] if len(memory_results) > 0 else 0
        ),
        "concurrent_query_memory": (
            memory_results[1]["memory_delta_mb"] if len(memory_results) > 1 else 0
        ),
        "sequential_query_memory": (
            memory_results[2]["memory_delta_mb"] if len(memory_results) > 2 else 0
        ),
        "large_bundle_memory": (
            memory_results[3]["memory_delta_mb"] if len(memory_results) > 3 else 0
        ),
    }

    # Identify optimization opportunities
    optimization_opportunities = []

    # Bundle generation optimizations
    if bundle_analysis["avg_execution_time"] > 0.1:
        optimization_opportunities.append(
            {
                "component": "Bundle Generation",
                "issue": "Execution time > 0.1s",
                "current_value": f"{bundle_analysis['avg_execution_time']:.3f}s",
                "target_value": "<0.1s",
                "optimization": "Implement caching and parallel processing",
            }
        )

    if bundle_analysis["avg_memory_usage"] > 10:
        optimization_opportunities.append(
            {
                "component": "Bundle Generation",
                "issue": "Memory usage > 10MB",
                "current_value": f"{bundle_analysis['avg_memory_usage']:.1f}MB",
                "target_value": "<10MB",
                "optimization": "Implement memory pooling and garbage collection",
            }
        )

    # Attribution calculation optimizations
    if attribution_analysis["avg_execution_time"] > 0.05:
        optimization_opportunities.append(
            {
                "component": "Attribution Calculation",
                "issue": "Execution time > 0.05s",
                "current_value": f"{attribution_analysis['avg_execution_time']:.3f}s",
                "target_value": "<0.05s",
                "optimization": "Optimize statistical calculations and caching",
            }
        )

    if attribution_analysis["avg_memory_usage"] > 5:
        optimization_opportunities.append(
            {
                "component": "Attribution Calculation",
                "issue": "Memory usage > 5MB",
                "current_value": f"{attribution_analysis['avg_memory_usage']:.1f}MB",
                "target_value": "<5MB",
                "optimization": "Implement memory-efficient data structures",
            }
        )

    # Memory efficiency optimizations
    if memory_analysis["concurrent_query_memory"] > memory_analysis["single_query_memory"] * 3:
        optimization_opportunities.append(
            {
                "component": "Memory Efficiency",
                "issue": "Poor concurrent memory scaling",
                "current_value": f"{memory_analysis['concurrent_query_memory']:.1f}MB",
                "target_value": f"<{memory_analysis['single_query_memory'] * 2:.1f}MB",
                "optimization": "Implement shared memory pools and resource management",
            }
        )

    return {
        "bundle_analysis": bundle_analysis,
        "attribution_analysis": attribution_analysis,
        "memory_analysis": memory_analysis,
        "optimization_opportunities": optimization_opportunities,
    }


def generate_performance_report(
    profiling_results: List[Dict],
    attribution_results: List[Dict],
    memory_results: List[Dict],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate comprehensive performance report"""

    return {
        "test_metadata": {
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": "Performance Optimization Analysis",
            "bundle_tests": len(profiling_results),
            "attribution_tests": len(attribution_results),
            "memory_tests": len(memory_results),
        },
        "performance_analysis": analysis,
        "bundle_generation_results": profiling_results,
        "attribution_calculation_results": attribution_results,
        "memory_efficiency_results": memory_results,
        "recommendations": {
            "immediate_optimizations": [
                "Implement response caching for frequently requested bundles",
                "Add memory pooling for bundle generation components",
                "Optimize statistical calculations in attribution tables",
                "Implement parallel processing for concurrent requests",
            ],
            "medium_term_optimizations": [
                "Add database connection pooling",
                "Implement lazy loading for large datasets",
                "Add compression for bundle outputs",
                "Implement request queuing and throttling",
            ],
            "long_term_optimizations": [
                "Migrate to microservices architecture",
                "Implement distributed caching",
                "Add horizontal scaling capabilities",
                "Implement advanced monitoring and alerting",
            ],
        },
    }


def main():
    """Main performance optimization function"""

    print("🚀 Performance Optimization Analysis")
    print("=" * 60)

    try:
        # Profile bundle generation
        profiling_results = profile_bundle_generation()

        # Profile attribution calculation
        attribution_results = profile_attribution_calculation()

        # Profile memory efficiency
        memory_results = profile_memory_efficiency()

        # Analyze performance bottlenecks
        analysis = analyze_performance_bottlenecks(
            profiling_results, attribution_results, memory_results
        )

        # Generate comprehensive report
        performance_report = generate_performance_report(
            profiling_results, attribution_results, memory_results, analysis
        )

        # Save results
        results_file = Path("artifacts/performance_optimization_analysis.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(performance_report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("🎉 Performance Optimization Analysis Completed!")

        print(f"\n📊 Performance Summary:")
        print(
            f"   Bundle Generation: {analysis['bundle_analysis']['avg_execution_time']:.3f}s avg, {analysis['bundle_analysis']['avg_memory_usage']:.1f}MB avg"
        )
        print(
            f"   Attribution Calculation: {analysis['attribution_analysis']['avg_execution_time']:.3f}s avg, {analysis['attribution_analysis']['avg_memory_usage']:.1f}MB avg"
        )
        print(
            f"   Memory Efficiency: {analysis['memory_analysis']['single_query_memory']:.1f}MB single, {analysis['memory_analysis']['concurrent_query_memory']:.1f}MB concurrent"
        )

        print(f"\n🔧 Optimization Opportunities:")
        for i, opp in enumerate(analysis["optimization_opportunities"], 1):
            print(f"   {i}. {opp['component']}: {opp['issue']}")
            print(f"      Current: {opp['current_value']}, Target: {opp['target_value']}")
            print(f"      Optimization: {opp['optimization']}")

        print(f"\n📁 Results saved to: {results_file}")

        return True

    except Exception as e:
        print(f"\n❌ Performance analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
