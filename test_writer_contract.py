#!/usr/bin/env python3
"""Unit tests for BTC writer contract validation."""

import sys
import os

sys.path.append(".")

# Load the fixed writer module
import importlib.util

spec = importlib.util.spec_from_file_location("btc_usd", "writer/pipelines/btc_usd_fixed.py")
btc_usd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(btc_usd)


def test_bad_2025_median():
    """Test that low 2025 prices trigger sanity failure."""
    print("🧪 Test 1: Bad 2025 median...")
    try:
        ticks = []
        for px in [50100.0] * 100:  # ~$50k prices
            ticks.append({"last_px": px, "best_bid": px - 50, "best_ask": px + 50})

        btc_usd.batch_contract(ticks, "2025-09-28")
        print("❌ Test 1 FAILED: Should have raised ValueError for bad 2025 median")
        return False
    except ValueError as e:
        if "Sanity fail" in str(e):
            print("✅ Test 1 PASSED: Correctly detected bad 2025 median")
            return True
        else:
            print(f"❌ Test 1 FAILED: Wrong error: {e}")
            return False
    except Exception as e:
        print(f"❌ Test 1 FAILED: Unexpected error: {e}")
        return False


def test_good_2025_median():
    """Test that reasonable 2025 prices pass sanity."""
    print("🧪 Test 2: Good 2025 median...")
    try:
        ticks = []
        for px in [110_000.0] * 100:  # ~$110k prices
            ticks.append({"last_px": px, "best_bid": px - 30, "best_ask": px + 30})

        btc_usd.batch_contract(ticks, "2025-09-28")
        print("✅ Test 2 PASSED: Correctly accepted good 2025 median")
        return True
    except Exception as e:
        print(f"❌ Test 2 FAILED: Should not have raised error: {e}")
        return False


def test_symbol_validation():
    """Test that only BTC-USD symbol is accepted."""
    print("🧪 Test 3: Symbol validation...")
    try:
        payload = {
            "symbol": "BTC-USDT",  # Wrong symbol
            "ts_exchange": 1727481600,
            "last_px": 110000.0,
            "best_bid": 109970.0,
            "best_ask": 110030.0,
            "venue": "binance",
        }

        btc_usd.normalize_tick(payload)
        print("❌ Test 3 FAILED: Should have raised ValueError for wrong symbol")
        return False
    except ValueError as e:
        if "Unexpected symbol" in str(e):
            print("✅ Test 3 PASSED: Correctly rejected wrong symbol")
            return True
        else:
            print(f"❌ Test 3 FAILED: Wrong error: {e}")
            return False
    except Exception as e:
        print(f"❌ Test 3 FAILED: Unexpected error: {e}")
        return False


def test_timestamp_validation():
    """Test timestamp window validation."""
    print("🧪 Test 4: Timestamp validation...")
    try:
        from datetime import datetime, timezone

        ts_ok = datetime(2025, 9, 28, 2, 0, 0, tzinfo=timezone.utc).timestamp()
        btc_usd.validate_timestamp_window(ts_ok, "20250928", "0200-0230")
        print("✅ Test 4 PASSED: Correctly accepted valid timestamp")
        return True
    except Exception as e:
        print(f"❌ Test 4 FAILED: Should not have raised error: {e}")
        return False


def main():
    """Run all unit tests."""
    print("🧪 Running unit tests for BTC writer contract...")
    print("=" * 50)

    tests = [
        test_bad_2025_median,
        test_good_2025_median,
        test_symbol_validation,
        test_timestamp_validation,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print("📊 Unit Test Summary:")
    print(f"✅ {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("✅ All unit tests passed - ready for canary")
        return True
    else:
        print("❌ Some tests failed - fix before canary")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
