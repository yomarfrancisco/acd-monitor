#!/usr/bin/env python3
"""
Lightweight experiment runner for ACD analysis.
Reuses existing analyzers without refactoring.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_experiment(snapshot, modules, notes):
    """Run experiment and generate outputs."""
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_dir = Path(f"experiments/out/{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[EXPERIMENT] Starting experiment {timestamp}")
    print(f"[EXPERIMENT] Snapshot: {snapshot}")
    print(f"[EXPERIMENT] Modules: {modules}")
    print(f"[EXPERIMENT] Notes: {notes}")

    # Initialize results
    results = {
        "timestamp": timestamp,
        "snapshot": snapshot,
        "modules": modules,
        "notes": notes,
        "metrics": {},
        "flags": {},
        "artifacts": [],
    }

    # Run each module
    for module in modules:
        print(f"[EXPERIMENT] Running {module}...")
        try:
            if module == "leadlag":
                run_leadlag(snapshot, output_dir, results)
            elif module == "infoshare":
                run_infoshare(snapshot, output_dir, results)
            elif module == "spread":
                run_spread(snapshot, output_dir, results)
            else:
                print(f"[EXPERIMENT:WARN] Unknown module: {module}")
        except Exception as e:
            print(f"[EXPERIMENT:ERROR] {module} failed: {e}")
            results["flags"][f"{module}_error"] = str(e)

    # Generate outputs
    write_summary_json(output_dir, results)
    write_summary_md(output_dir, results)
    write_artifact_links(output_dir, results)

    print(f"[EXPERIMENT] Complete: {output_dir}")
    return output_dir


def run_leadlag(snapshot, output_dir, results):
    """Run lead-lag analysis."""
    overlap_json = Path(snapshot) / "OVERLAP.json"
    if not overlap_json.exists():
        raise FileNotFoundError(f"OVERLAP.json not found in {snapshot}")

    # Call existing lead-lag script
    cmd = [
        "python",
        "scripts/run_leadlag_real.py",
        "--use-overlap-json",
        str(overlap_json),
        "--export-dir",
        str(output_dir / "evidence"),
        "--verbose",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Lead-lag failed: {result.stderr}")

    # Extract metrics from output
    leadlag_file = output_dir / "evidence" / "leadlag_results.json"
    if leadlag_file.exists():
        with open(leadlag_file) as f:
            leadlag_data = json.load(f)

        results["metrics"]["edges_count"] = len(leadlag_data.get("edges", []))
        results["metrics"]["top_leader"] = leadlag_data.get("top_leader", "unknown")
        results["artifacts"].append(str(leadlag_file))

    results["flags"]["leadlag_success"] = True


def run_infoshare(snapshot, output_dir, results):
    """Run info share analysis."""
    overlap_json = Path(snapshot) / "OVERLAP.json"
    if not overlap_json.exists():
        raise FileNotFoundError(f"OVERLAP.json not found in {snapshot}")

    # Call existing info share script
    cmd = [
        "python",
        "scripts/run_info_share_real.py",
        "--use-overlap-json",
        str(overlap_json),
        "--from-snapshot-ticks",
        "1",
        "--standardize",
        "none",
        "--gg-blend-alpha",
        "0.7",
        "--export-dir",
        str(output_dir / "evidence"),
        "--verbose",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Info share failed: {result.stderr}")

    # Extract metrics from output
    infoshare_file = output_dir / "evidence" / "info_share_results.json"
    if infoshare_file.exists():
        with open(infoshare_file) as f:
            infoshare_data = json.load(f)

        bounds = infoshare_data.get("bounds", {})
        results["metrics"]["bounds_present"] = len(bounds)
        results["metrics"]["bounds_sum"] = sum(b.get("point", 0) for b in bounds.values())
        results["artifacts"].append(str(infoshare_file))

    results["flags"]["infoshare_success"] = True


def run_spread(snapshot, output_dir, results):
    """Run spread analysis."""
    overlap_json = Path(snapshot) / "OVERLAP.json"
    if not overlap_json.exists():
        raise FileNotFoundError(f"OVERLAP.json not found in {snapshot}")

    # Call existing spread script
    cmd = [
        "python",
        "scripts/run_spread_compression_real.py",
        "--use-overlap-json",
        str(overlap_json),
        "--from-snapshot-ticks",
        "1",
        "--permutes",
        "1000",
        "--export-dir",
        str(output_dir / "evidence"),
        "--verbose",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Spread failed: {result.stderr}")

    # Extract metrics from output
    spread_file = output_dir / "evidence" / "spread_results.json"
    if spread_file.exists():
        with open(spread_file) as f:
            spread_data = json.load(f)

        results["metrics"]["permutes"] = spread_data.get("permutes", 0)
        results["metrics"]["episodes_count"] = spread_data.get("episodes", {}).get("count", 0)
        results["artifacts"].append(str(spread_file))

    results["flags"]["spread_success"] = True


def write_summary_json(output_dir, results):
    """Write summary.json with metrics."""
    summary = {
        "timestamp": results["timestamp"],
        "snapshot": results["snapshot"],
        "modules": results["modules"],
        "notes": results["notes"],
        "metrics": results["metrics"],
        "flags": results["flags"],
        "coverage": "unknown",  # Would need to extract from overlap data
        "top_pairs": [],  # Would need to extract from lead-lag data
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)


def write_summary_md(output_dir, results):
    """Write summary.md with human-readable rundown."""
    md_content = f"""# Experiment Summary

**Timestamp:** {results['timestamp']}
**Snapshot:** {results['snapshot']}
**Modules:** {', '.join(results['modules'])}
**Notes:** {results['notes']}

## Metrics
- **Edges Count:** {results['metrics'].get('edges_count', 'N/A')}
- **Bounds Present:** {results['metrics'].get('bounds_present', 'N/A')}
- **Permutations:** {results['metrics'].get('permutes', 'N/A')}
- **Top Leader:** {results['metrics'].get('top_leader', 'N/A')}

## Flags
{chr(10).join(f"- **{k}:** {v}" for k, v in results['flags'].items())}

## Artifacts
{chr(10).join(f"- {artifact}" for artifact in results['artifacts'])}
"""

    with open(output_dir / "summary.md", "w") as f:
        f.write(md_content)


def write_artifact_links(output_dir, results):
    """Write artifact_links.json with paths to evidence."""
    links = {
        "evidence_dir": str(output_dir / "evidence"),
        "artifacts": results["artifacts"],
        "summary_files": [
            str(output_dir / "summary.json"),
            str(output_dir / "summary.md"),
        ],
    }

    with open(output_dir / "artifact_links.json", "w") as f:
        json.dump(links, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Run ACD experiment")
    parser.add_argument(
        "--snapshot", required=True, help="Snapshot path (baselines/2s or court/1s)"
    )
    parser.add_argument(
        "--modules",
        default="leadlag,infoshare,spread",
        help="Comma-separated modules to run",
    )
    parser.add_argument("--notes", default="", help="Free text notes")

    args = parser.parse_args()

    modules = [m.strip() for m in args.modules.split(",")]

    try:
        output_dir = run_experiment(args.snapshot, modules, args.notes)
        print(f"[EXPERIMENT:SUCCESS] Output: {output_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"[EXPERIMENT:FAILURE] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
