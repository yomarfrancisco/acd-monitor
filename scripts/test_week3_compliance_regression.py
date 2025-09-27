#!/usr/bin/env python3
"""
Week 3 Compliance Regression Testing Script

This script executes the expanded compliance regression testing suite,
including the original 30 queries plus 15 new stress-test queries.
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


def get_week3_query_suite() -> List[Dict[str, Any]]:
    """Get the complete Week 3 query suite (45 queries)"""

    # Original 30 queries from Week 2
    original_queries = [
        "Generate a regulatory bundle for BTC/USD coordination signals last week",
        "Refine the bundle to include alternative explanations and attribution tables",
        "Summarize risk levels and recommendations in regulator-friendly language",
        "Generate a full regulatory bundle (PDF + JSON) for ETH/USD for the past 14 days",
        "Explain which validation layers contributed most to the coordination score in the latest bundle",
        "Highlight all provenance metadata for the CMA Poster Frames case bundle",
        "Compare bundle outputs for BTC/USD between seed 42 and seed 99 — note differences",
        "Produce an executive summary bundle for Q3 2025 coordination monitoring",
        "Refine the ETH/USD bundle to emphasize MEV coordination risks",
        "Prepare a draft escalation memo suitable for submission to regulators from last week's BTC/USD findings",
        "List alternative explanations explicitly addressed in the current bundle, with references",
        "Summarize attribution tables for BTC/USD and ETH/USD side by side",
        "Generate a highly compressed bundle for BTC/USD with only essential information",
        "Create a verbose, detailed bundle for ETH/USD with all possible explanations",
        "Refine the bundle to handle missing data scenarios and conflicting signals",
        "Generate a compliance memo for ADA/USD coordination analysis",
        "Create a risk assessment bundle for multiple crypto pairs simultaneously",
        "Refine the bundle to include cross-venue arbitrage analysis",
        "Generate a regulatory bundle with focus on spread floor detection",
        "Create a compliance report for undercut initiation patterns",
        "Generate a bundle with emphasis on lead-lag relationships",
        "Refine the bundle to include mirroring pattern analysis",
        "Create a regulatory memo for HMM regime detection results",
        "Generate a bundle with information flow analysis",
        "Refine the bundle to include MEV coordination scoring",
        "Create a compliance report for inventory shock analysis",
        "Generate a bundle with fee tier impact assessment",
        "Refine the bundle to include volatility regime analysis",
        "Create a regulatory memo for regulatory event impact",
        "Generate a bundle with comprehensive alternative explanations",
    ]

    # New 15 stress-test queries for Week 3
    stress_test_queries = [
        # Latency-Arbitrage Scenarios (31-33)
        "Analyze the impact of cross-venue latency differences on apparent coordination patterns in BTC/USD. How do 10ms vs 100ms latency differentials affect coordination detection?",
        "Generate a bundle for ETH/USD that explicitly accounts for arbitrage latency constraints. What coordination patterns could be explained by latency-arbitrage rather than actual coordination?",
        "Refine the BTC/USD bundle to include latency-adjusted coordination analysis. How does adjusting for known latency differentials change the coordination assessment?",
        # Partial Data Loss Scenarios (34-36)
        "Generate a regulatory bundle for ADA/USD with 25% missing order book data. How does partial data loss affect coordination detection confidence?",
        "Create a compliance report for ETH/USD with intermittent data gaps. What alternative explanations should be considered when data is incomplete?",
        "Refine the BTC/USD bundle to handle scenarios where one exchange has 50% data loss. How does this impact the overall coordination assessment?",
        # Conflicting Signals Scenarios (37-39)
        "Generate a bundle for BTC/USD where ICP suggests coordination but VMM suggests no coordination. How should conflicting signals be resolved and presented to regulators?",
        "Create a regulatory memo for ETH/USD with conflicting validation layer results. What methodology should be used to reconcile contradictory findings?",
        "Refine the ADA/USD bundle to address scenarios where lead-lag analysis suggests coordination but mirroring analysis suggests competition. How should these conflicts be explained?",
        # Regulator-Style "Why Not Coordination" Questions (40-42)
        "Why might the observed BTC/USD patterns NOT indicate coordination? Provide a comprehensive analysis of alternative explanations including market structure, fee tiers, and inventory management.",
        "Generate a regulatory bundle for ETH/USD that explicitly addresses the question: 'Could these patterns be explained by normal competitive behavior rather than coordination?'",
        "Create a compliance report that answers: 'What evidence would be needed to definitively rule out coordination in the observed ADA/USD patterns?'",
        # Advanced Edge Cases (43-45)
        "Generate a bundle for BTC/USD during a major market event (e.g., regulatory announcement) where coordination patterns appear. How should event-driven coordination be distinguished from structural coordination?",
        "Create a regulatory memo for ETH/USD with very small sample sizes (n<100). How does sample size affect coordination detection reliability and what confidence intervals should be reported?",
        "Refine the ADA/USD bundle to handle scenarios with extreme volatility (σ>5x normal). How does high volatility affect coordination detection and what adjustments should be made?",
    ]

    # Combine all queries
    all_queries = original_queries + stress_test_queries

    # Create query objects with metadata
    query_suite = []
    for i, query in enumerate(all_queries, 1):
        query_obj = {
            "id": i,
            "query": query,
            "category": "original" if i <= 30 else "stress_test",
            "subcategory": _get_subcategory(i),
            "expected_complexity": _get_expected_complexity(i),
        }
        query_suite.append(query_obj)

    return query_suite


def _get_subcategory(query_id: int) -> str:
    """Get subcategory for query based on ID"""
    if query_id <= 30:
        return "standard"
    elif query_id <= 33:
        return "latency_arbitrage"
    elif query_id <= 36:
        return "partial_data_loss"
    elif query_id <= 39:
        return "conflicting_signals"
    elif query_id <= 42:
        return "regulator_questions"
    else:
        return "advanced_edge_cases"


def _get_expected_complexity(query_id: int) -> str:
    """Get expected complexity for query based on ID"""
    if query_id <= 30:
        return "medium"
    elif query_id <= 33:
        return "high"
    elif query_id <= 36:
        return "high"
    elif query_id <= 39:
        return "very_high"
    elif query_id <= 42:
        return "very_high"
    else:
        return "extreme"


def execute_query_test(provider: OfflineMockProvider, query_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single query test"""

    start_time = time.time()

    try:
        # Execute query
        response = provider.generate(prompt=query_obj["query"])

        end_time = time.time()
        response_time = end_time - start_time

        # Assess response quality
        quality_score = assess_response_quality(response, query_obj)

        return {
            "query_id": query_obj["id"],
            "query": query_obj["query"],
            "category": query_obj["category"],
            "subcategory": query_obj["subcategory"],
            "expected_complexity": query_obj["expected_complexity"],
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
            "status": "FAIL",
            "response_time": response_time,
            "quality_score": 0.0,
            "response_length": 0,
            "error": str(e),
        }


def assess_response_quality(response: Any, query_obj: Dict[str, Any]) -> float:
    """Assess response quality on a 0-5 scale"""

    if response is None:
        return 0.0

    response_str = str(response)

    # Base score
    score = 2.0

    # Length check (should be substantial)
    if len(response_str) > 100:
        score += 0.5
    if len(response_str) > 500:
        score += 0.5

    # Content quality indicators
    quality_indicators = [
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
    ]

    indicator_count = sum(
        1 for indicator in quality_indicators if indicator.lower() in response_str.lower()
    )
    score += min(indicator_count * 0.1, 1.0)

    # Complexity bonus for stress-test queries
    if query_obj["category"] == "stress_test":
        if query_obj["expected_complexity"] in ["high", "very_high", "extreme"]:
            score += 0.5

    # Cap at 5.0
    return min(score, 5.0)


def run_individual_tests(
    provider: OfflineMockProvider, query_suite: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Run individual query tests"""

    print("Running Individual Query Tests...")
    print("=" * 60)

    results = []

    for i, query_obj in enumerate(query_suite, 1):
        print(
            f"Query {i:2d}/{len(query_suite)}: {query_obj['subcategory']} - {query_obj['expected_complexity']} complexity"
        )

        result = execute_query_test(provider, query_obj)
        results.append(result)

        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(
            f"   {status_icon} {result['status']} - {result['response_time']:.3f}s - Quality: {result['quality_score']:.1f}/5.0"
        )

        if result["error"]:
            print(f"   Error: {result['error']}")

    return results


def run_batch_tests(
    provider: OfflineMockProvider, query_suite: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run batch testing"""

    print("\nRunning Batch Testing...")
    print("=" * 60)

    start_time = time.time()
    results = []

    for i, query_obj in enumerate(query_suite, 1):
        result = execute_query_test(provider, query_obj)
        results.append(result)

        if i % 10 == 0:
            print(f"   Completed {i}/{len(query_suite)} queries...")

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate metrics
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


def run_stress_tests(
    provider: OfflineMockProvider, query_suite: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run stress testing"""

    print("\nRunning Stress Testing...")
    print("=" * 60)

    # Test with concurrent-like execution (rapid succession)
    start_time = time.time()
    results = []

    # Run all queries in rapid succession
    for query_obj in query_suite:
        result = execute_query_test(provider, query_obj)
        results.append(result)

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate stress test metrics
    successful_queries = [r for r in results if r["status"] == "PASS"]
    success_rate = len(successful_queries) / len(results) * 100

    avg_response_time = sum(r["response_time"] for r in results) / len(results)
    max_response_time = max(r["response_time"] for r in results)

    return {
        "total_queries": len(results),
        "successful_queries": len(successful_queries),
        "success_rate": success_rate,
        "total_time": total_time,
        "avg_response_time": avg_response_time,
        "max_response_time": max_response_time,
        "results": results,
    }


def generate_test_report(
    individual_results: List[Dict[str, Any]],
    batch_results: Dict[str, Any],
    stress_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate comprehensive test report"""

    # Calculate overall metrics
    total_queries = len(individual_results)
    successful_queries = len([r for r in individual_results if r["status"] == "PASS"])
    success_rate = successful_queries / total_queries * 100

    avg_response_time = sum(r["response_time"] for r in individual_results) / total_queries
    avg_quality_score = sum(r["quality_score"] for r in individual_results) / total_queries

    # Category breakdown
    categories = {}
    for result in individual_results:
        category = result["category"]
        if category not in categories:
            categories[category] = {"total": 0, "successful": 0, "avg_quality": 0.0}

        categories[category]["total"] += 1
        if result["status"] == "PASS":
            categories[category]["successful"] += 1
        categories[category]["avg_quality"] += result["quality_score"]

    # Calculate category averages
    for category in categories:
        if categories[category]["total"] > 0:
            categories[category]["avg_quality"] /= categories[category]["total"]
            categories[category]["success_rate"] = (
                categories[category]["successful"] / categories[category]["total"] * 100
            )

    # Subcategory breakdown
    subcategories = {}
    for result in individual_results:
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
            "total_queries": total_queries,
            "test_duration": batch_results["total_time"],
            "test_type": "Week 3 Compliance Regression",
        },
        "overall_metrics": {
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "avg_quality_score": avg_quality_score,
            "throughput": batch_results["throughput"],
        },
        "category_breakdown": categories,
        "subcategory_breakdown": subcategories,
        "batch_test_results": batch_results,
        "stress_test_results": stress_results,
        "individual_results": individual_results,
    }


def main():
    """Main test execution function"""

    print("🚀 Week 3 Compliance Regression Testing")
    print("=" * 60)

    try:
        # Initialize provider
        provider = OfflineMockProvider()

        # Get query suite
        query_suite = get_week3_query_suite()
        print(f"Loaded {len(query_suite)} queries for testing")

        # Run individual tests
        individual_results = run_individual_tests(provider, query_suite)

        # Run batch tests
        batch_results = run_batch_tests(provider, query_suite)

        # Run stress tests
        stress_results = run_stress_tests(provider, query_suite)

        # Generate comprehensive report
        test_report = generate_test_report(individual_results, batch_results, stress_results)

        # Save results
        results_file = Path("artifacts/week3_compliance_regression_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(test_report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("🎉 Week 3 Compliance Regression Testing Completed!")

        print(f"\n📊 Test Summary:")
        print(
            f"   Total Queries: {test_report['overall_metrics']['success_rate']:.1f}% success rate"
        )
        print(
            f"   Average Response Time: {test_report['overall_metrics']['avg_response_time']:.3f}s"
        )
        print(
            f"   Average Quality Score: {test_report['overall_metrics']['avg_quality_score']:.1f}/5.0"
        )
        print(f"   Throughput: {test_report['overall_metrics']['throughput']:.1f} queries/minute")

        print(f"\n📋 Category Breakdown:")
        for category, metrics in test_report["category_breakdown"].items():
            print(
                f"   {category}: {metrics['success_rate']:.1f}% success, {metrics['avg_quality']:.1f}/5.0 quality"
            )

        print(f"\n📁 Results saved to: {results_file}")

        return True

    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
