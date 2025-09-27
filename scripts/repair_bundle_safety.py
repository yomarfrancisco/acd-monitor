#!/usr/bin/env python3
"""
Safety guard for bundle repair script.
Refuses to overwrite bundles with [RESEARCH:FLAGGED] dominance >= 0.55 unless --force is provided.
"""

import argparse
import json
import os
import sys
from pathlib import Path

def check_flagged_bundle(bundle_path: str, force: bool = False) -> bool:
    """Check if bundle is flagged and should be protected."""
    bundle_path = Path(bundle_path)
    
    # Look for RESEARCH_DECISION.md
    decision_file = bundle_path / "RESEARCH_DECISION.md"
    if not decision_file.exists():
        return True  # No decision file, safe to proceed
    
    try:
        with open(decision_file, 'r') as f:
            content = f.read()
            
        # Check for [RESEARCH:FLAGGED] status
        if "[RESEARCH:FLAGGED]" in content:
            # Extract dominance value if present
            lines = content.split('\n')
            dominance = None
            for line in lines:
                if "dominance" in line.lower() and ":" in line:
                    try:
                        dominance = float(line.split(':')[-1].strip())
                        break
                    except (ValueError, IndexError):
                        continue
            
            if dominance is not None and dominance >= 0.55:
                if not force:
                    print(f"[ABORT:FLAGGED_BUNDLE] Bundle {bundle_path} has [RESEARCH:FLAGGED] with dominance {dominance} >= 0.55")
                    print("Use --force to override this protection")
                    return False
                else:
                    print(f"[WARN:FORCED_OVERWRITE] Overwriting flagged bundle {bundle_path} with dominance {dominance}")
    
    except Exception as e:
        print(f"[WARN:SAFETY_CHECK] Could not check bundle {bundle_path}: {e}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Safety guard for bundle repair")
    parser.add_argument("--bundle-path", required=True, help="Path to bundle directory")
    parser.add_argument("--force", action="store_true", help="Force overwrite even flagged bundles")
    
    args = parser.parse_args()
    
    if not check_flagged_bundle(args.bundle_path, args.force):
        sys.exit(1)
    
    print(f"[SAFETY:PASS] Bundle {args.bundle_path} is safe to repair")
    sys.exit(0)

if __name__ == "__main__":
    main()
