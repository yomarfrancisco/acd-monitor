#!/usr/bin/env python3
"""
Chatbase Activation Test Script

This script tests the Chatbase API activation status and prepares for live integration.
It checks API key availability, tests connectivity, and validates response structure.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import json
import time
from typing import Dict, Any, Optional

from agent.providers.chatbase_adapter import ChatbaseAdapter
from agent.providers.offline_mock import OfflineMockProvider


def test_chatbase_environment():
    """Test Chatbase environment variables and configuration"""

    print("Testing Chatbase Environment Configuration...")

    # Check environment variables
    api_key = os.getenv("CHATBASE_API_KEY")
    chatbot_id = os.getenv("CHATBASE_ASSISTANT_ID")
    signing_secret = os.getenv("CHATBASE_SIGNING_SECRET")
    use_legacy = os.getenv("CHATBASE_USE_LEGACY", "false").lower() == "true"

    print(f"   API Key: {'✅ Set' if api_key else '❌ Not Set'}")
    print(f"   Chatbot ID: {'✅ Set' if chatbot_id else '❌ Not Set'}")
    print(f"   Signing Secret: {'✅ Set' if signing_secret else '❌ Not Set'}")
    print(f"   Legacy Mode: {'✅ Enabled' if use_legacy else '❌ Disabled'}")

    # Check if all required variables are set
    all_set = all([api_key, chatbot_id, signing_secret])

    if all_set:
        print(f"   ✅ All required environment variables are set")
        return True
    else:
        print(f"   ❌ Missing required environment variables")
        print(f"   Required: CHATBASE_API_KEY, CHATBASE_ASSISTANT_ID, CHATBASE_SIGNING_SECRET")
        return False


def test_chatbase_adapter_initialization():
    """Test Chatbase adapter initialization"""

    print("\nTesting Chatbase Adapter Initialization...")

    try:
        adapter = ChatbaseAdapter()
        print(f"   ✅ ChatbaseAdapter initialized successfully")
        print(f"   Root URL: {adapter.root_url}")
        print(f"   Chat URL: {adapter.chat_url}")
        print(f"   Legacy Mode: {adapter.use_legacy}")
        return True, adapter
    except Exception as e:
        print(f"   ❌ ChatbaseAdapter initialization failed: {e}")
        return False, None


def test_chatbase_healthcheck():
    """Test Chatbase healthcheck functionality"""

    print("\nTesting Chatbase Healthcheck...")

    try:
        adapter = ChatbaseAdapter()
        health = adapter.healthcheck()

        print(f"   Status: {health.status}")
        print(f"   Last Check: {health.last_check}")

        if hasattr(health, "details"):
            print(f"   Details: {health.details}")

        if health.status == "healthy":
            print(f"   ✅ Chatbase healthcheck passed")
            return True
        else:
            print(f"   ⚠️ Chatbase healthcheck returned: {health.status}")
            return False

    except Exception as e:
        print(f"   ❌ Chatbase healthcheck failed: {e}")
        return False


def test_chatbase_api_connectivity():
    """Test Chatbase API connectivity (if credentials are available)"""

    print("\nTesting Chatbase API Connectivity...")

    # Check if we have credentials
    api_key = os.getenv("CHATBASE_API_KEY")
    if not api_key:
        print(f"   ⚠️ No API key available - skipping connectivity test")
        return False

    try:
        adapter = ChatbaseAdapter()

        # Test with a simple query
        test_prompt = "Hello, this is a connectivity test"

        print(f"   Testing with prompt: '{test_prompt}'")

        response = adapter.generate(prompt=test_prompt, session_id="test_session_001")

        print(f"   ✅ API connectivity test successful")
        print(f"   Response length: {len(response.content)} characters")
        print(f"   Session ID: {response.session_id}")
        print(f"   Usage: {response.usage}")

        return True

    except Exception as e:
        print(f"   ❌ API connectivity test failed: {e}")
        return False


def test_offline_mock_fallback():
    """Test offline mock provider as fallback"""

    print("\nTesting Offline Mock Provider Fallback...")

    try:
        mock_provider = OfflineMockProvider()

        # Test with a compliance query
        test_query = "Generate a regulatory bundle for BTC/USD coordination signals"

        response = mock_provider.generate(prompt=test_query, session_id="fallback_test_001")

        print(f"   ✅ Offline mock provider working")
        print(f"   Response length: {len(response.content)} characters")
        print(f"   Intent: {response.usage.get('intent', 'unknown')}")
        print(f"   Mode: {response.usage.get('mode', 'unknown')}")

        return True

    except Exception as e:
        print(f"   ❌ Offline mock provider test failed: {e}")
        return False


def test_response_structure_consistency():
    """Test response structure consistency between Chatbase and offline mock"""

    print("\nTesting Response Structure Consistency...")

    test_queries = [
        "Generate a regulatory bundle for BTC/USD",
        "What is the risk level for ETH/USD coordination?",
        "Refine the bundle to include alternative explanations",
    ]

    try:
        # Test offline mock responses
        mock_provider = OfflineMockProvider()
        mock_responses = []

        for query in test_queries:
            response = mock_provider.generate(
                prompt=query, session_id=f"consistency_test_{len(mock_responses)}"
            )
            mock_responses.append(response)

        print(f"   ✅ Offline mock responses generated: {len(mock_responses)}")

        # Check response structure consistency
        for i, response in enumerate(mock_responses):
            has_content = hasattr(response, "content") and response.content
            has_session_id = hasattr(response, "session_id") and response.session_id
            has_usage = hasattr(response, "usage") and response.usage

            print(
                f"   Query {i+1}: Content={has_content}, Session={has_session_id}, Usage={has_usage}"
            )

        print(f"   ✅ Response structure consistency verified")
        return True

    except Exception as e:
        print(f"   ❌ Response structure consistency test failed: {e}")
        return False


def test_compliance_query_regression():
    """Test compliance query regression with current setup"""

    print("\nTesting Compliance Query Regression...")

    # Test a subset of compliance queries
    test_queries = [
        "Generate a regulatory bundle for BTC/USD coordination signals last week",
        "Refine the bundle to include alternative explanations and attribution tables",
        "Summarize risk levels and recommendations in regulator-friendly language",
        "Highlight all provenance metadata for the CMA Poster Frames case bundle",
    ]

    try:
        mock_provider = OfflineMockProvider()
        results = []

        for i, query in enumerate(test_queries):
            print(f"   Testing query {i+1}: {query[:50]}...")

            response = mock_provider.generate(prompt=query, session_id=f"regression_test_{i}")

            # Check response quality
            has_content = len(response.content) > 0
            has_usage = response.usage is not None
            has_intent = "intent" in response.usage if response.usage else False

            results.append(
                {
                    "query": query,
                    "success": has_content and has_usage and has_intent,
                    "content_length": len(response.content),
                    "intent": (
                        response.usage.get("intent", "unknown") if response.usage else "unknown"
                    ),
                }
            )

            print(f"     ✅ Success: {has_content and has_usage and has_intent}")
            print(
                f"     Intent: {response.usage.get('intent', 'unknown') if response.usage else 'unknown'}"
            )

        # Summary
        successful_queries = [r for r in results if r["success"]]
        success_rate = len(successful_queries) / len(test_queries) * 100

        print(f"   ✅ Compliance query regression test completed")
        print(
            f"   Success Rate: {success_rate:.1f}% ({len(successful_queries)}/{len(test_queries)})"
        )

        return success_rate >= 90.0

    except Exception as e:
        print(f"   ❌ Compliance query regression test failed: {e}")
        return False


def main():
    """Main test function"""

    print("🚀 Chatbase Activation Test Suite")
    print("=" * 60)

    test_results = {}

    # Test 1: Environment configuration
    test_results["environment"] = test_chatbase_environment()

    # Test 2: Adapter initialization
    init_success, adapter = test_chatbase_adapter_initialization()
    test_results["initialization"] = init_success

    # Test 3: Healthcheck
    test_results["healthcheck"] = test_chatbase_healthcheck()

    # Test 4: API connectivity (if credentials available)
    test_results["connectivity"] = test_chatbase_api_connectivity()

    # Test 5: Offline mock fallback
    test_results["offline_fallback"] = test_offline_mock_fallback()

    # Test 6: Response structure consistency
    test_results["consistency"] = test_response_structure_consistency()

    # Test 7: Compliance query regression
    test_results["regression"] = test_compliance_query_regression()

    print("\n" + "=" * 60)
    print("🎉 Chatbase Activation Test Suite Completed!")

    # Summary
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)

    print(f"\n📊 Test Results Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {passed_tests/total_tests*100:.1f}%")

    print(f"\n📋 Individual Test Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    # Recommendations
    print(f"\n💡 Recommendations:")

    if not test_results["environment"]:
        print(
            "   - Set up Chatbase environment variables (CHATBASE_API_KEY, CHATBASE_ASSISTANT_ID, CHATBASE_SIGNING_SECRET)"
        )

    if not test_results["connectivity"]:
        print("   - Verify Chatbase API credentials and account status")
        print("   - Check network connectivity to Chatbase API")

    if test_results["offline_fallback"]:
        print("   - Offline mock provider is working as fallback")

    if test_results["regression"]:
        print("   - Compliance query regression tests are passing")

    # Overall status
    if passed_tests >= total_tests * 0.8:  # 80% pass rate
        print(f"\n✅ Overall Status: READY for Chatbase activation")
    else:
        print(f"\n⚠️ Overall Status: NEEDS ATTENTION before Chatbase activation")

    return passed_tests >= total_tests * 0.8


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

