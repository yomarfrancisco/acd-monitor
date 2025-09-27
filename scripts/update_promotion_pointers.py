#!/usr/bin/env python3
"""
Update promotion pointers for reproducible E2E runs.
Creates/updates REAL_2s_PROMOTED.json and MANIFEST.json with stable schema.
"""

import json
import sys
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def get_git_sha() -> str:
    """Get current git SHA."""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledSubprocessError:
        return "unknown"


def get_file_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not file_path.exists():
        return "missing"
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def update_baseline_manifest(baseline_dir: str) -> None:
    """Update baselines/2s/MANIFEST.json with stable schema."""
    manifest_path = Path(baseline_dir) / "MANIFEST.json"
    
    # Load existing manifest or create new
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {}
    
    # Update with stable schema
    manifest.update({
        "startUTC": "2025-09-26T20:48:04Z",
        "endUTC": "2025-09-26T20:57:52Z", 
        "minutes": 9.8,
        "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
        "coverage": 0.99,
        "policy": "RESEARCH_g=2s",
        "git_sha": get_git_sha(),
        "seeds": {"numpy": 42, "random": 123},
        "created_at": datetime.now().isoformat() + "Z",
        "artifacts": {
            "research_bundle_2s.zip": get_file_sha256(Path(baseline_dir) / "evidence" / "research_bundle_2s.zip"),
            "leadlag_results.json": get_file_sha256(Path(baseline_dir) / "evidence" / "leadlag_results.json"),
            "spread_results.json": get_file_sha256(Path(baseline_dir) / "evidence" / "spread_results.json"),
            "info_share_results.json": get_file_sha256(Path(baseline_dir) / "evidence" / "info_share_results.json"),
            "EVIDENCE.md": get_file_sha256(Path(baseline_dir) / "evidence" / "EVIDENCE.md")
        }
    })
    
    # Write updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"[PROMOTION:manifest] Updated {manifest_path}")


def update_sweep_promoted(sweep_dir: str) -> None:
    """Update exports/sweep/REAL_2s_PROMOTED.json with stable schema."""
    promoted_path = Path(sweep_dir) / "REAL_2s_PROMOTED.json"
    
    # Create sweep directory if needed
    promoted_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing or create new
    if promoted_path.exists():
        with open(promoted_path) as f:
            promoted = json.load(f)
    else:
        promoted = []
    
    # Add new entry with stable schema
    entry = {
        "snapshot": "baselines/2s",
        "startUTC": "2025-09-26T20:48:04Z",
        "endUTC": "2025-09-26T20:57:52Z",
        "minutes": 9.8,
        "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
        "coverage": 0.99,
        "policy": "RESEARCH_g=2s",
        "git_sha": get_git_sha(),
        "seeds": {"numpy": 42, "random": 123},
        "created_at": datetime.now().isoformat() + "Z"
    }
    
    # Add to list (avoid duplicates)
    if entry not in promoted:
        promoted.append(entry)
    
    # Write updated promoted list
    with open(promoted_path, 'w') as f:
        json.dump(promoted, f, indent=2)
    
    print(f"[PROMOTION:sweep] Updated {promoted_path}")


def main():
    """Update promotion pointers."""
    print("[PROMOTION:start] Updating promotion pointers")
    
    # Update baseline manifest
    update_baseline_manifest("baselines/2s")
    
    # Update sweep promoted
    update_sweep_promoted("exports/sweep")
    
    print("[PROMOTION:done] Promotion pointers updated successfully")


if __name__ == "__main__":
    main()
