#!/usr/bin/env python3
"""
Test Enhanced Kraken Parser
Tests the hardened Kraken WebSocket message parser
"""

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

# Add the capture directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from websocket_capture import VenueWebSocket


def test_kraken_parser():
    """Test the enhanced Kraken parser with various message formats."""

    # Create a test WebSocket instance
    ws = VenueWebSocket("kraken", "BTC-USD")

    # Test cases for different Kraken message formats
    test_cases = [
        {
            "name": "Standard format - numeric timestamp",
            "data": [50000.0, 0.1, 1695758400],
            "expected": True,
        },
        {
            "name": "Standard format - string timestamp",
            "data": [50000.0, 0.1, "1695758400"],
            "expected": True,
        },
        {
            "name": "Standard format - string with prefix",
            "data": [50000.0, 0.1, "s1695758400"],
            "expected": True,
        },
        {
            "name": "Nested format - numeric timestamp",
            "data": ["trade", [50000.0, 0.1, 1695758400]],
            "expected": True,
        },
        {
            "name": "Nested format - string timestamp",
            "data": ["trade", [50000.0, 0.1, "1695758400"]],
            "expected": True,
        },
        {
            "name": "Nested format - string with prefix",
            "data": ["trade", [50000.0, 0.1, "s1695758400"]],
            "expected": True,
        },
        {
            "name": "Invalid format - too short",
            "data": [50000.0, 0.1],
            "expected": False,
        },
        {"name": "Invalid format - empty list", "data": [], "expected": False},
        {
            "name": "Invalid format - not a list",
            "data": {"price": 50000.0, "volume": 0.1, "timestamp": 1695758400},
            "expected": False,
        },
    ]

    print("Testing Enhanced Kraken Parser:")
    print("=" * 60)

    success_count = 0
    total_count = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        try:
            result = ws._parse_kraken_message(test_case["data"])
            success = (result is not None) == test_case["expected"]

            status = "✅" if success else "❌"
            print(f"{status} Test {i:2d}: {test_case['name']}")

            if result:
                print(
                    f"    → Price: {result['last_px']}, Volume: {result['last_sz']}, Time: {result['ts_exchange']}"
                )
            else:
                print(f"    → No result (expected: {test_case['expected']})")

            if success:
                success_count += 1

        except Exception as e:
            print(f"❌ Test {i:2d}: {test_case['name']} - ERROR: {e}")

    print("=" * 60)
    print(f"Results: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


def test_feature_flag():
    """Test the KRAKEN_TS_FLEX feature flag."""
    print("\nTesting Feature Flag:")
    print("=" * 30)

    # Test with flag enabled (default)
    os.environ["KRAKEN_TS_FLEX"] = "1"
    ws = VenueWebSocket("kraken", "BTC-USD")
    result_enabled = ws._parse_kraken_message([50000.0, 0.1, "s1695758400"])
    print(f"✅ KRAKEN_TS_FLEX=1: {'Enabled' if result_enabled else 'Disabled'}")

    # Test with flag disabled
    os.environ["KRAKEN_TS_FLEX"] = "0"
    ws = VenueWebSocket("kraken", "BTC-USD")
    result_disabled = ws._parse_kraken_message([50000.0, 0.1, "s1695758400"])
    print(f"❌ KRAKEN_TS_FLEX=0: {'Enabled' if result_disabled else 'Disabled'}")

    # Restore default
    os.environ["KRAKEN_TS_FLEX"] = "1"


if __name__ == "__main__":
    # Test the parser
    parser_success = test_kraken_parser()

    # Test the feature flag
    test_feature_flag()

    # Exit with appropriate code
    sys.exit(0 if parser_success else 1)
