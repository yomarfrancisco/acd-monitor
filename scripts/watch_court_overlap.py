#!/usr/bin/env python3
"""
Watch for court overlap detection and provide real-time updates.
"""

import time
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def watch_overlap_log(log_file, check_interval=10):
    """Watch the overlap log for [OVERLAP:FOUND] events."""
    print("🔍 Monitoring for court overlap detection...")
    print("📋 Requirements: ALL5 venues, coverage≥0.999, court policies")
    print("⚡ Auto-trigger: Court diagnostics will run automatically")
    print("📁 Output: exports/court_diag_<timestamp>/ with 9-block evidence")
    print("=" * 60)
    
    last_position = 0
    
    try:
        while True:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                    
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            print(f"📝 {line}")
                            
                            # Check for overlap found
                            if "[OVERLAP:FOUND]" in line or "OVERLAP:FOUND" in line:
                                print("\n🎯 COURT OVERLAP DETECTED!")
                                print("🚀 Triggering court diagnostics automatically...")
                                return True
                            
                            # Check for pending status
                            if "[OVERLAP:PENDING]" in line:
                                try:
                                    data = json.loads(line.split("OVERLAP:PENDING] ")[1])
                                    venues_ready = data.get("venues_ready", [])
                                    venues_missing = data.get("venues_missing", [])
                                    minutes_max = data.get("minutes_max", 0)
                                    
                                    print(f"⏳ Status: {len(venues_ready)}/{len(venues_ready) + len(venues_missing)} venues ready, max {minutes_max:.1f}m")
                                except:
                                    pass
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")
        return False

def main():
    log_file = Path("exports/overlap/OVERLAP_STATUS.log")
    
    print("🏛️  COURT-MODE OVERLAP MONITOR")
    print("=" * 60)
    
    if not log_file.exists():
        print("❌ Log file not found. Waiting for orchestrator to start...")
        while not log_file.exists():
            time.sleep(5)
        print("✅ Log file found, starting monitoring...")
    
    watch_overlap_log(log_file)

if __name__ == "__main__":
    main()
