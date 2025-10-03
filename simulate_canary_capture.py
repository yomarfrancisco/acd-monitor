#!/usr/bin/env python3
"""
Simulate canary capture for testing purposes
"""

import os
import sys
from datetime import datetime

# Set environment variables for canary mode
os.environ["BTC_CANARY_ENABLED"] = "true"
os.environ["BTC_SANITY_MIN_2025"] = "80000"

print("🔧 Environment variables set:")
print(f"   BTC_CANARY_ENABLED = {os.environ.get('BTC_CANARY_ENABLED')}")
print(f"   BTC_SANITY_MIN_2025 = {os.environ.get('BTC_SANITY_MIN_2025')}")

print("\n🎯 Simulating canary capture for 2025-09-28 02:00-02:30 UTC")
print("📊 Target window: 2025-09-28T02:00:00Z to 2025-09-28T02:30:00Z")

# Simulate the capture command that would be run
capture_command = [
    "python",
    "scripts/capture/capture_window_enhanced.py",
    "--symbol",
    "BTC-USD",
    "--start",
    "2025-09-28T02:00:00Z",
    "--end",
    "2025-09-28T02:30:00Z",
    "--venues",
    "binance,coinbase,kraken,okx,bybit",
    "--bucket",
    "acd-monitor-snapshots",
    "--prefix",
    "snapshots",
    "--canary",  # This enables canary mode
    "--verbose",
]

print("\n🚀 Capture command:")
print(" ".join(capture_command))

print("\n📝 Expected S3 output path:")
print("s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/")

print("\n📊 Expected log output:")
print("✅ Symbol validation: BTC-USD")
print("✅ Timestamp unit detected: microseconds")
print("✅ Price median: ~110,000 USD")
print("✅ Cross-field pass-rate: >90%")
print("✅ Written S3 keys:")
print(
    "   - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/binance/part-0000.parquet"
)
print(
    "   - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/coinbase/part-0000.parquet"
)
print(
    "   - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/kraken/part-0000.parquet"
)
print(
    "   - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/okx/part-0000.parquet"
)
print(
    "   - s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/bybit/part-0000.parquet"
)

print("\n⏱️  Simulation complete - ready for validation gates")
