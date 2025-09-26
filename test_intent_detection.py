#!/usr/bin/env python3
"""
Test intent detection for exchange operations queries
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agent.providers.offline_mock import OfflineMockProvider


def test_intent_detection():
    provider = OfflineMockProvider()

    test_queries = [
        "Flag periods where our spread floor persisted despite high volatility last 7d; attach evidence pack.",
        "Who led BTC/USDT on our venue vs Coinbase and Binance between 10:00–14:00 UTC yesterday? Show persistence & switching entropy.",
        "List mirroring episodes on top-10 depth vs external venues; annotate arbitrage windows.",
        "Explain whether our VIP fee ladder or inventory shocks could explain the signal on 2025-09-15.",
        "Generate a case file for alert #23198 with ICP/VMM excerpts and provenance hashes.",
        "Compare today's AMBER period to last week's baseline; what changed in moments/validation layers?",
        "Simulate stricter latency-arb constraints; does the red flag persist?",
        "Summarize risk bands for BTC/ETH spot; include ops actions taken and open tickets.",
        "Export an internal memo for CCO: findings, caveats, alternative explanations, next steps.",
        "Show order-book mirroring heatmap by depth tier for yesterday's U.S. trading hours.",
        "Identify undercut initiation episodes by market maker; escalate if repeated.",
        "Produce a pre-submission pack we can send to our regulator on request.",
    ]

    print("Intent Detection Test Results:")
    print("=" * 60)

    for i, query in enumerate(test_queries, 1):
        intent = provider._detect_intent(query)
        print(f"Query {i}: {intent}")
        print(f"  Query: {query[:80]}...")
        print()

    # Show available templates
    print("Available Templates:")
    print("=" * 60)
    for intent, template in provider.templates.items():
        print(f"{intent}: {template.pattern}")


if __name__ == "__main__":
    test_intent_detection()


