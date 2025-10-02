#!/usr/bin/env python3
"""
Trigger GitHub Actions workflow for canary capture
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta

def trigger_canary_capture():
    """Trigger the capture workflow with canary mode enabled."""
    
    # Calculate the target window (2025-09-28 02:00-02:30 UTC)
    target_date = "2025-09-28"
    target_start = "2025-09-28T02:00:00Z"
    target_end = "2025-09-28T02:30:00Z"
    
    print(f"🎯 Triggering canary capture for {target_date} 02:00-02:30 UTC")
    print(f"📊 Target window: {target_start} to {target_end}")
    print(f"🔧 Canary mode: ENABLED (writes to ticks_canary/)")
    
    # GitHub Actions workflow dispatch payload
    workflow_inputs = {
        "symbols": "BTC-USD",
        "venues": "binance,coinbase,kraken,okx,bybit", 
        "canary_mode": True
    }
    
    print(f"📋 Workflow inputs: {json.dumps(workflow_inputs, indent=2)}")
    
    # Note: This would require GitHub CLI (gh) and proper authentication
    # For now, we'll provide the manual steps
    print("\n" + "="*60)
    print("🚀 MANUAL TRIGGER STEPS:")
    print("="*60)
    print("1. Go to GitHub Actions: https://github.com/your-org/acd-monitor/actions")
    print("2. Select 'Continuous Snapshot Capture' workflow")
    print("3. Click 'Run workflow'")
    print("4. Fill in the form:")
    print(f"   - Symbols: BTC-USD")
    print(f"   - Venues: binance,coinbase,kraken,okx,bybit")
    print(f"   - Canary mode: ✅ CHECKED")
    print("5. Click 'Run workflow'")
    print("\n📝 Expected S3 output path:")
    print(f"   s3://acd-monitor-snapshots/snapshots/BTC-USD/20250928/0200-0230/ticks_canary/")
    print("\n⏱️  Workflow should complete in ~5-10 minutes")
    print("📊 Check logs for: symbol validation, timestamp unit, median price, cross-field pass-rate")

if __name__ == "__main__":
    trigger_canary_capture()

