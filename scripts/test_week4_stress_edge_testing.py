#!/usr/bin/env python3
"""
Week 4 Stress & Edge Testing Script

This script executes high-complexity compliance queries and stress testing
for edge cases including MEV shocks, flash crashes, and latency coordination.
"""

import sys
import os
from pathlib import Path
import time
import json
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent.providers.offline_mock import OfflineMockProvider


def get_week4_stress_edge_queries() -> List[Dict[str, Any]]:
    """Get the Week 4 stress and edge testing queries (≥10 new high-complexity queries)"""

    # New high-complexity stress and edge testing queries
    stress_edge_queries = [
        # MEV Shock Scenarios (46-48)
        {
            "id": 46,
            "query": "Analyze the impact of MEV (Miner Extractable Value) shocks on apparent coordination patterns in BTC/USD. How do sudden MEV events affect coordination detection and what alternative explanations should be considered?",
            "category": "stress_test",
            "subcategory": "mev_shocks",
            "expected_complexity": "extreme",
            "stress_factors": ["mev_events", "sudden_shocks", "alternative_explanations"],
        },
        {
            "id": 47,
            "query": "Generate a regulatory bundle for ETH/USD during a major MEV extraction event. How should MEV coordination be distinguished from traditional market coordination, and what evidence would be needed to prove MEV-based coordination?",
            "category": "stress_test",
            "subcategory": "mev_shocks",
            "expected_complexity": "extreme",
            "stress_factors": [
                "mev_extraction",
                "coordination_distinction",
                "evidence_requirements",
            ],
        },
        {
            "id": 48,
            "query": "Refine the ADA/USD bundle to handle scenarios with multiple simultaneous MEV events across different blockchains. How does cross-chain MEV coordination affect traditional coordination detection methods?",
            "category": "stress_test",
            "subcategory": "mev_shocks",
            "expected_complexity": "extreme",
            "stress_factors": ["cross_chain_mev", "simultaneous_events", "coordination_methods"],
        },
        # Flash Crash Scenarios (49-51)
        {
            "id": 49,
            "query": "Analyze coordination patterns during a flash crash event in BTC/USD where prices dropped 20% in 5 minutes. How should flash crash coordination be distinguished from normal market volatility, and what evidence indicates intentional coordination vs. cascading effects?",
            "category": "stress_test",
            "subcategory": "flash_crashes",
            "expected_complexity": "extreme",
            "stress_factors": ["flash_crash", "rapid_price_movement", "coordination_vs_cascading"],
        },
        {
            "id": 50,
            "query": "Generate a compliance report for ETH/USD during a coordinated flash crash across multiple exchanges. What analysis methods are most effective for detecting coordinated flash crash attacks, and how should regulatory responses be prioritized?",
            "category": "stress_test",
            "subcategory": "flash_crashes",
            "expected_complexity": "extreme",
            "stress_factors": ["coordinated_attack", "multi_exchange", "regulatory_response"],
        },
        {
            "id": 51,
            "query": "Create a regulatory memo for ADA/USD analyzing the difference between organic flash crashes and coordinated manipulation. What statistical thresholds should be used to distinguish between natural market events and coordinated attacks?",
            "category": "stress_test",
            "subcategory": "flash_crashes",
            "expected_complexity": "extreme",
            "stress_factors": [
                "organic_vs_coordinated",
                "statistical_thresholds",
                "manipulation_detection",
            ],
        },
        # Latency Coordination Scenarios (52-54)
        {
            "id": 52,
            "query": "Analyze ultra-low latency coordination patterns in BTC/USD where coordination occurs within 1-5 milliseconds. How does microsecond-level coordination affect traditional analysis methods, and what new detection techniques are needed for high-frequency coordination?",
            "category": "stress_test",
            "subcategory": "latency_coordination",
            "expected_complexity": "extreme",
            "stress_factors": [
                "ultra_low_latency",
                "microsecond_coordination",
                "detection_techniques",
            ],
        },
        {
            "id": 53,
            "query": "Generate a bundle for ETH/USD analyzing coordination patterns that exploit colocation advantages. How should colocation-based coordination be detected and regulated, and what evidence is needed to prove colocation coordination?",
            "category": "stress_test",
            "subcategory": "latency_coordination",
            "expected_complexity": "extreme",
            "stress_factors": ["colocation", "exploitation", "regulatory_detection"],
        },
        {
            "id": 54,
            "query": "Refine the ADA/USD bundle to handle scenarios where coordination occurs through high-frequency trading algorithms with sub-millisecond response times. How should algorithmic coordination be distinguished from normal HFT behavior?",
            "category": "stress_test",
            "subcategory": "latency_coordination",
            "expected_complexity": "extreme",
            "stress_factors": ["hft_algorithms", "sub_millisecond", "algorithmic_coordination"],
        },
        # Extreme Market Conditions (55-57)
        {
            "id": 55,
            "query": "Analyze coordination patterns during extreme market stress when BTC/USD experiences 50% volatility in a single day. How should coordination detection be adjusted for extreme market conditions, and what confidence intervals are appropriate during market stress?",
            "category": "stress_test",
            "subcategory": "extreme_conditions",
            "expected_complexity": "extreme",
            "stress_factors": ["extreme_volatility", "market_stress", "confidence_intervals"],
        },
        {
            "id": 56,
            "query": "Generate a regulatory bundle for ETH/USD during a market-wide liquidity crisis where bid-ask spreads widen to 10% of mid-price. How does liquidity crisis affect coordination detection, and what alternative explanations should be considered during liquidity stress?",
            "category": "stress_test",
            "subcategory": "extreme_conditions",
            "expected_complexity": "extreme",
            "stress_factors": ["liquidity_crisis", "wide_spreads", "alternative_explanations"],
        },
        {
            "id": 57,
            "query": "Create a compliance report for ADA/USD analyzing coordination patterns during a regulatory announcement that causes 30% price movement. How should event-driven coordination be distinguished from market reaction to news, and what evidence indicates coordinated response vs. natural market reaction?",
            "category": "stress_test",
            "subcategory": "extreme_conditions",
            "expected_complexity": "extreme",
            "stress_factors": ["regulatory_announcement", "event_driven", "coordinated_vs_natural"],
        },
        # Advanced Edge Cases (58-60)
        {
            "id": 58,
            "query": "Analyze coordination patterns in BTC/USD when one major exchange goes offline for 2 hours during peak trading. How does exchange outage affect coordination detection across remaining exchanges, and what analysis adjustments are needed for partial market data?",
            "category": "stress_test",
            "subcategory": "advanced_edge_cases",
            "expected_complexity": "extreme",
            "stress_factors": ["exchange_outage", "partial_data", "coordination_detection"],
        },
        {
            "id": 59,
            "query": "Generate a bundle for ETH/USD analyzing coordination patterns during a hard fork event where the network splits into two chains. How should coordination analysis be adapted for blockchain network splits, and what new coordination patterns emerge during chain splits?",
            "category": "stress_test",
            "subcategory": "advanced_edge_cases",
            "expected_complexity": "extreme",
            "stress_factors": ["hard_fork", "chain_split", "network_coordination"],
        },
        {
            "id": 60,
            "query": "Refine the ADA/USD bundle to handle scenarios with conflicting coordination signals where some indicators suggest coordination while others suggest competition. How should conflicting signals be resolved, and what methodology should be used to determine the dominant pattern?",
            "category": "stress_test",
            "subcategory": "advanced_edge_cases",
            "expected_complexity": "extreme",
            "stress_factors": ["conflicting_signals", "signal_resolution", "dominant_pattern"],
        },
    ]

    return stress_edge_queries


def execute_stress_query_test(
    provider: OfflineMockProvider, query_obj: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a single stress query test"""

    start_time = time.time()

    try:
        # Execute query
        response = provider.generate(prompt=query_obj["query"])

        end_time = time.time()
        response_time = end_time - start_time

        # Assess response quality with stress-specific criteria
        quality_score = assess_stress_response_quality(response, query_obj)

        return {
            "query_id": query_obj["id"],
            "query": query_obj["query"],
            "category": query_obj["category"],
            "subcategory": query_obj["subcategory"],
            "expected_complexity": query_obj["expected_complexity"],
            "stress_factors": query_obj["stress_factors"],
            "status": "PASS",
            "response_time": response_time,
            "quality_score": quality_score,
            "response_length": len(str(response)),
            "error": None,
        }

    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time

        return {
            "query_id": query_obj["id"],
            "query": query_obj["query"],
            "category": query_obj["category"],
            "subcategory": query_obj["subcategory"],
            "expected_complexity": query_obj["expected_complexity"],
            "stress_factors": query_obj["stress_factors"],
            "status": "FAIL",
            "response_time": response_time,
            "quality_score": 0.0,
            "response_length": 0,
            "error": str(e),
        }


def assess_stress_response_quality(response: Any, query_obj: Dict[str, Any]) -> float:
    """Assess stress response quality on a 0-5 scale with stress-specific criteria"""

    if response is None:
        return 0.0

    response_str = str(response)

    # Base score
    score = 2.0

    # Length check (should be substantial for complex queries)
    if len(response_str) > 200:
        score += 0.5
    if len(response_str) > 800:
        score += 0.5

    # Stress-specific quality indicators
    stress_indicators = [
        "coordination",
        "analysis",
        "risk",
        "regulatory",
        "bundle",
        "attribution",
        "provenance",
        "alternative",
        "explanation",
        "confidence",
        "statistical",
        "methodology",
        "validation",
        "mev",
        "flash",
        "crash",
        "latency",
        "coordination",
        "extreme",
        "stress",
        "crisis",
        "outage",
        "fork",
    ]

    indicator_count = sum(
        1 for indicator in stress_indicators if indicator.lower() in response_str.lower()
    )
    score += min(indicator_count * 0.1, 1.0)

    # Complexity bonus for extreme stress queries
    if query_obj["expected_complexity"] == "extreme":
        score += 0.5

    # Stress factor bonus
    stress_factor_count = len(query_obj["stress_factors"])
    score += min(stress_factor_count * 0.1, 0.5)

    # Cap at 5.0
    return min(score, 5.0)


def run_stress_testing(
    provider: OfflineMockProvider, stress_queries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run stress testing with high-complexity queries"""

    print("Running Stress & Edge Testing...")
    print("=" * 60)

    start_time = time.time()
    results = []

    for i, query_obj in enumerate(stress_queries, 1):
        print(
            f"Stress Query {i:2d}/{len(stress_queries)}: {query_obj['subcategory']} - {query_obj['expected_complexity']} complexity"
        )

        result = execute_stress_query_test(provider, query_obj)
        results.append(result)

        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(
            f"   {status_icon} {result['status']} - {result['response_time']:.3f}s - Quality: {result['quality_score']:.1f}/5.0"
        )

        if result["error"]:
            print(f"   Error: {result['error']}")

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate stress test metrics
    successful_queries = [r for r in results if r["status"] == "PASS"]
    success_rate = len(successful_queries) / len(results) * 100

    avg_response_time = sum(r["response_time"] for r in results) / len(results)
    avg_quality_score = sum(r["quality_score"] for r in results) / len(results)

    throughput = len(results) / total_time * 60  # queries per minute

    return {
        "total_queries": len(results),
        "successful_queries": len(successful_queries),
        "success_rate": success_rate,
        "total_time": total_time,
        "avg_response_time": avg_response_time,
        "avg_quality_score": avg_quality_score,
        "throughput": throughput,
        "results": results,
    }


def run_bundle_stress_testing(provider: OfflineMockProvider) -> Dict[str, Any]:
    """Run bundle generation under stress conditions"""

    print("\nRunning Bundle Generation Stress Testing...")
    print("=" * 60)

    # Test bundle generation with various stress conditions
    stress_conditions = [
        {
            "name": "Long Data Span",
            "description": "Bundle generation with 180 days of data",
            "query": "Generate a regulatory bundle for BTC/USD covering the last 180 days with comprehensive analysis",
        },
        {
            "name": "Large Dataset",
            "description": "Bundle generation with >100k data points",
            "query": "Generate a regulatory bundle for ETH/USD with high-frequency data (>100k data points) and detailed analysis",
        },
        {
            "name": "Multiple Asset Pairs",
            "description": "Bundle generation with 5+ asset pairs",
            "query": "Generate a regulatory bundle covering BTC/USD, ETH/USD, ADA/USD, SOL/USD, and DOT/USD with cross-pair analysis",
        },
        {
            "name": "Complex Refinement",
            "description": "Bundle generation with multiple refinement steps",
            "query": "Generate a regulatory bundle for BTC/USD, then refine it to include MEV analysis, flash crash detection, latency coordination analysis, and extreme market condition handling",
        },
        {
            "name": "Concurrent Generation",
            "description": "Multiple bundle generation requests",
            "query": "Generate regulatory bundles for BTC/USD, ETH/USD, and ADA/USD simultaneously with comprehensive analysis",
        },
    ]

    stress_results = []

    for i, condition in enumerate(stress_conditions, 1):
        print(f"Stress Condition {i}/{len(stress_conditions)}: {condition['name']}")
        print(f"   Description: {condition['description']}")

        start_time = time.time()

        try:
            response = provider.generate(prompt=condition["query"])
            end_time = time.time()
            response_time = end_time - start_time

            quality_score = assess_stress_response_quality(
                response,
                {
                    "expected_complexity": "extreme",
                    "stress_factors": ["bundle_generation", "stress_condition"],
                },
            )

            result = {
                "condition_name": condition["name"],
                "description": condition["description"],
                "status": "PASS",
                "response_time": response_time,
                "quality_score": quality_score,
                "response_length": len(str(response)),
                "error": None,
            }

            print(f"   ✅ PASS - {response_time:.3f}s - Quality: {quality_score:.1f}/5.0")

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time

            result = {
                "condition_name": condition["name"],
                "description": condition["description"],
                "status": "FAIL",
                "response_time": response_time,
                "quality_score": 0.0,
                "response_length": 0,
                "error": str(e),
            }

            print(f"   ❌ FAIL - {response_time:.3f}s - Error: {e}")

        stress_results.append(result)

    # Calculate stress test metrics
    successful_conditions = [r for r in stress_results if r["status"] == "PASS"]
    success_rate = len(successful_conditions) / len(stress_results) * 100

    avg_response_time = sum(r["response_time"] for r in stress_results) / len(stress_results)
    avg_quality_score = sum(r["quality_score"] for r in stress_results) / len(stress_results)

    return {
        "total_conditions": len(stress_results),
        "successful_conditions": len(successful_conditions),
        "success_rate": success_rate,
        "avg_response_time": avg_response_time,
        "avg_quality_score": avg_quality_score,
        "results": stress_results,
    }


def generate_stress_test_report(
    stress_results: Dict[str, Any], bundle_stress_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate comprehensive stress test report"""

    # Calculate overall metrics
    total_queries = stress_results["total_queries"]
    successful_queries = stress_results["successful_queries"]
    success_rate = successful_queries / total_queries * 100

    avg_response_time = stress_results["avg_response_time"]
    avg_quality_score = stress_results["avg_quality_score"]

    # Subcategory breakdown
    subcategories = {}
    for result in stress_results["results"]:
        subcategory = result["subcategory"]
        if subcategory not in subcategories:
            subcategories[subcategory] = {"total": 0, "successful": 0, "avg_quality": 0.0}

        subcategories[subcategory]["total"] += 1
        if result["status"] == "PASS":
            subcategories[subcategory]["successful"] += 1
        subcategories[subcategory]["avg_quality"] += result["quality_score"]

    # Calculate subcategory averages
    for subcategory in subcategories:
        if subcategories[subcategory]["total"] > 0:
            subcategories[subcategory]["avg_quality"] /= subcategories[subcategory]["total"]
            subcategories[subcategory]["success_rate"] = (
                subcategories[subcategory]["successful"] / subcategories[subcategory]["total"] * 100
            )

    return {
        "test_metadata": {
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stress_queries": total_queries,
            "total_bundle_conditions": bundle_stress_results["total_conditions"],
            "test_duration": stress_results["total_time"],
            "test_type": "Week 4 Stress & Edge Testing",
        },
        "overall_metrics": {
            "stress_query_success_rate": success_rate,
            "bundle_stress_success_rate": bundle_stress_results["success_rate"],
            "avg_response_time": avg_response_time,
            "avg_quality_score": avg_quality_score,
            "throughput": stress_results["throughput"],
        },
        "subcategory_breakdown": subcategories,
        "stress_test_results": stress_results,
        "bundle_stress_results": bundle_stress_results,
    }


def main():
    """Main stress testing function"""

    print("🚀 Week 4 Stress & Edge Testing")
    print("=" * 60)

    try:
        # Initialize provider
        provider = OfflineMockProvider()

        # Get stress and edge testing queries
        stress_queries = get_week4_stress_edge_queries()
        print(f"Loaded {len(stress_queries)} stress and edge testing queries")

        # Run stress testing
        stress_results = run_stress_testing(provider, stress_queries)

        # Run bundle stress testing
        bundle_stress_results = run_bundle_stress_testing(provider)

        # Generate comprehensive report
        test_report = generate_stress_test_report(stress_results, bundle_stress_results)

        # Save results
        results_file = Path("artifacts/week4_stress_edge_testing_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(test_report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("🎉 Week 4 Stress & Edge Testing Completed!")

        print(f"\n📊 Stress Testing Summary:")
        print(
            f"   Stress Queries: {test_report['overall_metrics']['stress_query_success_rate']:.1f}% success rate"
        )
        print(
            f"   Bundle Stress: {test_report['overall_metrics']['bundle_stress_success_rate']:.1f}% success rate"
        )
        print(
            f"   Average Response Time: {test_report['overall_metrics']['avg_response_time']:.3f}s"
        )
        print(
            f"   Average Quality Score: {test_report['overall_metrics']['avg_quality_score']:.1f}/5.0"
        )
        print(f"   Throughput: {test_report['overall_metrics']['throughput']:.1f} queries/minute")

        print(f"\n📋 Subcategory Breakdown:")
        for subcategory, metrics in test_report["subcategory_breakdown"].items():
            print(
                f"   {subcategory}: {metrics['success_rate']:.1f}% success, {metrics['avg_quality']:.1f}/5.0 quality"
            )

        print(f"\n📁 Results saved to: {results_file}")

        return True

    except Exception as e:
        print(f"\n❌ Stress testing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
