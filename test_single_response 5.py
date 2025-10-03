#!/usr/bin/env python3
"""
Test a single exchange operations query to see the actual response
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agent.providers.offline_mock import OfflineMockProvider


def test_single_response():
    provider = OfflineMockProvider()

    query = "Flag periods where our spread floor persisted despite high volatility last 7d; attach evidence pack."

    print("Testing Exchange Surveillance Query:")
    print("=" * 60)
    print(f"Query: {query}")
    print()

    response = provider.generate(prompt=query)

    print("Response:")
    print("=" * 60)
    print(response.content)
    print()

    print("Response Analysis:")
    print("=" * 60)
    print(f"Response Length: {len(response.content)}")
    print(f"Contains 'spread_floor': {'spread_floor' in response.content.lower()}")
    print(f"Contains 'volatility': {'volatility' in response.content.lower()}")
    print(f"Contains 'evidence_pack': {'evidence_pack' in response.content.lower()}")
    print(f"Contains 'evidence': {'evidence' in response.content.lower()}")
    print(f"Contains 'pack': {'pack' in response.content.lower()}")


if __name__ == "__main__":
    test_single_response()
