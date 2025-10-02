#!/usr/bin/env python3
"""
Test the failing exchange operations queries to see what's in the responses
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agent.providers.offline_mock import OfflineMockProvider


def test_failing_queries():
    provider = OfflineMockProvider()

    failing_queries = [
        {
            "id": "exch_003",
            "query": "List mirroring episodes on top-10 depth vs external venues; annotate arbitrage windows.",
            "expected": ["mirroring", "arbitrage_windows", "depth_analysis"],
        },
        {
            "id": "exch_010",
            "query": "Show order-book mirroring heatmap by depth tier for yesterday's U.S. trading hours.",
            "expected": ["heatmap", "depth_tier", "trading_hours"],
        },
        {
            "id": "exch_011",
            "query": "Identify undercut initiation episodes by market maker; escalate if repeated.",
            "expected": ["undercut_initiation", "market_maker", "escalation"],
        },
    ]

    for query_obj in failing_queries:
        print(f"Testing {query_obj['id']}:")
        print("=" * 60)
        print(f"Query: {query_obj['query']}")
        print()

        response = provider.generate(prompt=query_obj["query"])

        print("Response:")
        print("=" * 60)
        print(response.content)
        print()

        print("Component Analysis:")
        print("=" * 60)
        response_lower = response.content.lower()
        for component in query_obj["expected"]:
            search_terms = component.replace("_", " ").split()
            found = any(term.lower() in response_lower for term in search_terms)
            print(f"  {component}: {'✅' if found else '❌'}")
        print()
        print()


if __name__ == "__main__":
    test_failing_queries()


