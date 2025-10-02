#!/usr/bin/env python3
"""
Environment gates for Stage H2
"""

import os

# Environment gates
ALLOW_OVERWRITE = os.getenv("ALLOW_OVERWRITE", "false").lower() == "true"
DATE = os.getenv("DATE", "20251001")

def check_gates():
    """Check environment gates."""
    if not ALLOW_OVERWRITE:
        print("🔒 ALLOW_OVERWRITE=false - No file overwrites allowed")
    else:
        print("⚠️ ALLOW_OVERWRITE=true - File overwrites allowed")
    
    print(f"📅 DATE={DATE}")
    
    return {
        "ALLOW_OVERWRITE": ALLOW_OVERWRITE,
        "DATE": DATE
    }

if __name__ == "__main__":
    gates = check_gates()
    print(f"Environment gates: {gates}")

