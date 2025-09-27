#!/usr/bin/env python3
"""
Generate provenance.json for auditability and reproducibility.
"""
import json
import sys
import hashlib
import subprocess
import platform
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


def get_python_version() -> str:
    """Get Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_pip_freeze_hash() -> str:
    """Get hash of pip freeze output for dependency fingerprinting."""
    try:
        result = subprocess.run(['pip', 'freeze'], 
                              capture_output=True, text=True, check=True)
        return hashlib.sha256(result.stdout.encode()).hexdigest()[:16]
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


def generate_provenance(
    snapshot_path: str,
    analysis_params: Dict[str, Any] = None,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Generate provenance.json for a run.
    
    Args:
        snapshot_path: Path to snapshot directory
        analysis_params: Analysis parameters used
        output_path: Output path for provenance.json (default: snapshot_path/provenance.json)
        
    Returns:
        Provenance dictionary
    """
    if analysis_params is None:
        analysis_params = {}
    
    if output_path is None:
        output_path = str(Path(snapshot_path) / "provenance.json")
    
    # Generate provenance
    provenance = {
        "git_sha": get_git_sha(),
        "python_version": get_python_version(),
        "pip_freeze_hash": get_pip_freeze_hash(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine()
        },
        "seeds": {
            "numpy": 42,
            "random": 123
        },
        "snapshot_path": str(Path(snapshot_path).resolve()),
        "analysis_params": analysis_params,
        "created_at": datetime.now().isoformat() + "Z",
        "artifacts": {}
    }
    
    # Add artifact hashes if they exist
    snapshot_dir = Path(snapshot_path)
    evidence_dir = snapshot_dir / "evidence"
    
    if evidence_dir.exists():
        for artifact in ["leadlag_results.json", "spread_results.json", 
                        "info_share_results.json", "EVIDENCE.md", "MANIFEST.json"]:
            artifact_path = evidence_dir / artifact
            if artifact_path.exists():
                provenance["artifacts"][artifact] = get_file_sha256(artifact_path)
    
    # Write provenance file
    with open(output_path, 'w') as f:
        json.dump(provenance, f, indent=2)
    
    print(f"[PROVENANCE:generated] {output_path}")
    return provenance


def main():
    """Generate provenance for current run."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate provenance.json")
    parser.add_argument("--snapshot", required=True, help="Snapshot directory path")
    parser.add_argument("--output", help="Output path for provenance.json")
    parser.add_argument("--permutes", type=int, default=1000, help="Number of permutations")
    parser.add_argument("--alpha", type=float, default=0.05, help="Alpha level")
    parser.add_argument("--gg-blend-alpha", type=float, default=0.7, help="GG blend alpha")
    
    args = parser.parse_args()
    
    analysis_params = {
        "permutes": args.permutes,
        "alpha": args.alpha,
        "gg_blend_alpha": args.gg_blend_alpha
    }
    
    provenance = generate_provenance(
        snapshot_path=args.snapshot,
        analysis_params=analysis_params,
        output_path=args.output
    )
    
    print(f"[PROVENANCE:done] Generated provenance with {len(provenance['artifacts'])} artifacts")


if __name__ == "__main__":
    main()
