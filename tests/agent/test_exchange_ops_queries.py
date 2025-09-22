#!/usr/bin/env python3
"""
Exchange Operations Queries Test Suite

Tests the ACD system's ability to handle exchange operations queries
specifically designed for Head of Surveillance, CCO, and Market Operations teams.

This test suite validates the system's capability to:
1. Detect coordination patterns in exchange operations
2. Generate surveillance reports and case files
3. Provide operator runbooks and escalation procedures
4. Support regulatory compliance and reporting
"""

import os
import sys
import time
from datetime import datetime

# from typing import Dict  # noqa: F401, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agent.providers.offline_mock import OfflineMockProvider
from agent.bundle_generator import ACDBundleGenerator


class ExchangeOpsQueryTester:
    """Test suite for exchange operations queries"""

    def __init__(self):
        self.provider = OfflineMockProvider()
        self.bundle_generator = ACDBundleGenerator()
        self.test_results = []
        self.start_time = time.time()

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all exchange operations query tests"""
        print("🚀 Starting Exchange Operations Query Tests...")
        print("=" * 60)

        # Define exchange operations queries
        exchange_queries = [
            {
                "id": "exch_001",
                "query": (
                    "Flag periods where our spread floor persisted despite high volatility last 7d; "  # noqa: E501
                    "attach evidence pack."
                ),
                "category": "surveillance",
                "expected_components": ["spread_floor", "volatility", "evidence_pack"],
            },
            {
                "id": "exch_002",
                "query": "Who led BTC/USDT on our venue vs Coinbase and Binance between 10:00–14:00 UTC yesterday? Show persistence & switching entropy.",  # noqa: E501
                "category": "lead_lag",
                "expected_components": ["lead_lag", "persistence", "switching_entropy"],
            },
            {
                "id": "exch_003",
                "query": "List mirroring episodes on top-10 depth vs external venues; annotate arbitrage windows.",  # noqa: E501
                "category": "mirroring",
                "expected_components": ["mirroring", "depth_analysis", "arbitrage_windows"],
            },
            {
                "id": "exch_004",
                "query": "Explain whether our VIP fee ladder or inventory shocks could explain the signal on 2025-09-15.",  # noqa: E501
                "category": "analysis",
                "expected_components": ["fee_ladder", "inventory_shocks", "signal_explanation"],
            },
            {
                "id": "exch_005",
                "query": "Generate a case file for alert #23198 with ICP/VMM excerpts and provenance hashes.",  # noqa: E501
                "category": "case_management",
                "expected_components": ["case_file", "icp_vmm", "provenance_hashes"],
            },
            {
                "id": "exch_006",
                "query": "Compare today's AMBER period to last week's baseline; what changed in moments/validation layers?",  # noqa: E501
                "category": "comparison",
                "expected_components": [
                    "baseline_comparison",
                    "moment_changes",
                    "validation_layers",
                ],
            },
            {
                "id": "exch_007",
                "query": "Simulate stricter latency-arb constraints; does the red flag persist?",
                "category": "simulation",
                "expected_components": ["latency_arb", "constraints", "red_flag_persistence"],
            },
            {
                "id": "exch_008",
                "query": "Summarize risk bands for BTC/ETH spot; include ops actions taken and open tickets.",  # noqa: E501
                "category": "risk_summary",
                "expected_components": ["risk_bands", "ops_actions", "open_tickets"],
            },
            {
                "id": "exch_009",
                "query": "Export an internal memo for CCO: findings, caveats, alternative explanations, next steps.",  # noqa: E501
                "category": "reporting",
                "expected_components": [
                    "internal_memo",
                    "findings",
                    "caveats",
                    "alternative_explanations",
                ],
            },
            {
                "id": "exch_010",
                "query": "Show order-book mirroring heatmap by depth tier for yesterday's U.S. trading hours.",  # noqa: E501
                "category": "visualization",
                "expected_components": ["heatmap", "depth_tier", "trading_hours"],
            },
            {
                "id": "exch_011",
                "query": "Identify undercut initiation episodes by market maker; escalate if repeated.",  # noqa: E501
                "category": "market_maker",
                "expected_components": ["undercut_initiation", "market_maker", "escalation"],
            },
            {
                "id": "exch_012",
                "query": "Produce a pre-submission pack we can send to our regulator on request.",
                "category": "regulatory",
                "expected_components": ["pre_submission", "regulatory_pack", "compliance"],
            },
        ]

        # Run tests for each query
        for query_obj in exchange_queries:
            self._test_exchange_query(query_obj)

        # Generate summary report
        return self._generate_summary_report()

    def _test_exchange_query(self, query_obj: Dict[str, Any]) -> None:
        """Test a single exchange operations query"""
        query_id = query_obj["id"]
        query_text = query_obj["query"]
        category = query_obj["category"]
        expected_components = query_obj["expected_components"]

        print("\n🔍 Testing Query {query_id}: {category}")
        print("Query: {query_text}")

        start_time = time.time()

        try:
            # Generate response using offline mock provider
            response = self.provider.generate(prompt=query_text)

            # Check if response is valid
            if not response or not hasattr(response, "content"):
                raise ValueError("Invalid response format")

            # Check for expected components (flexible matching)
            response_text = response.content
            components_found = []
            for component in expected_components:
                # Convert component to flexible search terms
                search_terms = component.replace("_", " ").split()
                if any(term.lower() in response_text.lower() for term in search_terms):
                    components_found.append(component)

            # Calculate success metrics
            execution_time = time.time() - start_time
            component_coverage = len(components_found) / len(expected_components)
            success = component_coverage >= 0.5  # At least 50% component coverage

            # Store test result
            test_result = {
                "query_id": query_id,
                "category": category,
                "query": query_text,
                "success": success,
                "execution_time": execution_time,
                "component_coverage": component_coverage,
                "components_found": components_found,
                "expected_components": expected_components,
                "response_length": len(response_text),
                "timestamp": datetime.now().isoformat(),
            }

            self.test_results.append(test_result)

            # Print result
            status = "✅ PASS" if success else "❌ FAIL"
            print("Result: {status}")
            print("Execution Time: {execution_time:.3f}s")
            print("Component Coverage: {component_coverage:.1%}")
            print("Components Found: {components_found}")

        except Exception as e:
            execution_time = time.time() - start_time
            test_result = {
                "query_id": query_id,
                "category": category,
                "query": query_text,
                "success": False,
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            self.test_results.append(test_result)

            print("Result: ❌ ERROR")
            print("Error: {str(e)}")
            print("Execution Time: {execution_time:.3f}s")

    def _generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of all tests"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests

        total_execution_time = time.time() - self.start_time
        avg_execution_time = (
            sum(result["execution_time"] for result in self.test_results) / total_tests
        )

        # Calculate success rate by category
        category_stats = {}
        for result in self.test_results:
            category = result["category"]
            if category not in category_stats:
                category_stats[category] = {"total": 0, "successful": 0}
            category_stats[category]["total"] += 1
            if result["success"]:
                category_stats[category]["successful"] += 1

        # Calculate overall success rate
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        summary = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "total_execution_time": total_execution_time,
                "avg_execution_time": avg_execution_time,
            },
            "category_stats": category_stats,
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
        }

        # Print summary
        print("\n" + "=" * 60)
        print("📊 EXCHANGE OPERATIONS QUERY TEST SUMMARY")
        print("=" * 60)
        print("Total Tests: {total_tests}")
        print("Successful: {successful_tests}")
        print("Failed: {failed_tests}")
        print("Success Rate: {success_rate:.1f}%")
        print("Total Execution Time: {total_execution_time:.3f}s")
        print("Average Execution Time: {avg_execution_time:.3f}s")

        print("\n📈 Category Breakdown:")
        for category, stats in category_stats.items():
            category_success_rate = (stats["successful"] / stats["total"]) * 100
            print(
                f"  {category}: {stats['successful']}/{stats['total']} ({category_success_rate:.1f}%)"  # noqa: E501
            )

        # Determine overall status
        if success_rate >= 90:
            status = "✅ EXCELLENT"
        elif success_rate >= 80:
            status = "✅ GOOD"
        elif success_rate >= 70:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ NEEDS IMPROVEMENT"

        print("\n🎯 Overall Status: {status}")

        return summary


def main():
    """Main test execution function"""
    print("🚀 Exchange Operations Query Test Suite")
    print("Testing ACD system's exchange operations capabilities")
    print("=" * 60)

    # Create test suite
    tester = ExchangeOpsQueryTester()

    # Run all tests
    results = tester.run_all_tests()

    # Save results
    output_file = "artifacts/exchange_ops_query_test_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n💾 Results saved to: {output_file}")

    # Return exit code based on success rate
    success_rate = results["test_summary"]["success_rate"]
    if success_rate >= 80:
        print("🎉 Exchange operations query tests PASSED!")
        return 0
    else:
        print("❌ Exchange operations query tests FAILED!")
        return 1


if __name__ == "__main__":
    exit(main())
