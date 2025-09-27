#!/usr/bin/env python3
"""
Regression Analysis Script

Compares BEST2 bundles against BEST4 baseline to check:
- JS distance ≤ 0.02
- No spread p-value flip (sig↔non-sig)
- Lead-lag delta ≤ 0.10
- Same top leader
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_overlap_data(overlap_file: Path) -> Dict[str, Any]:
    """Load OVERLAP.json data."""
    if not overlap_file.exists():
        raise FileNotFoundError(f"OVERLAP.json not found: {overlap_file}")
    
    with open(overlap_file, 'r') as f:
        return json.load(f)

def load_evidence_data(evidence_file: Path) -> Dict[str, Any]:
    """Load EVIDENCE.md data."""
    if not evidence_file.exists():
        raise FileNotFoundError(f"EVIDENCE.md not found: {evidence_file}")
    
    content = evidence_file.read_text()
    sections = {}
    
    # Parse BEGIN/END blocks
    import re
    pattern = r'## (\w+)\s*\nBEGIN\s*\n(.*?)\nEND'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for section_name, section_content in matches:
        try:
            sections[section_name] = json.loads(section_content.strip())
        except json.JSONDecodeError:
            sections[section_name] = section_content.strip()
    
    return sections

def calculate_js_distance(venues1: Dict[str, float], venues2: Dict[str, float]) -> float:
    """Calculate Jensen-Shannon distance between two venue distributions."""
    # Get common venues
    common_venues = set(venues1.keys()) & set(venues2.keys())
    if not common_venues:
        return 1.0  # Maximum distance if no common venues
    
    # Normalize distributions
    sum1 = sum(venues1.get(v, 0) for v in common_venues)
    sum2 = sum(venues2.get(v, 0) for v in common_venues)
    
    if sum1 == 0 or sum2 == 0:
        return 1.0
    
    p = np.array([venues1.get(v, 0) / sum1 for v in common_venues])
    q = np.array([venues2.get(v, 0) / sum2 for v in common_venues])
    
    # Calculate JS distance
    m = 0.5 * (p + q)
    kl_pm = np.sum(p * np.log(p / m + 1e-10))
    kl_qm = np.sum(q * np.log(q / m + 1e-10))
    js_distance = 0.5 * (kl_pm + kl_qm)
    
    return js_distance

def analyze_regression(baseline_dir: Path, target_dir: Path, max_js: float, max_leadlag_delta: float, no_spread_flip: bool) -> Dict[str, Any]:
    """Analyze regression between baseline and target."""
    logger.info(f"Analyzing regression: {baseline_dir} vs {target_dir}")
    
    # Load overlap data
    baseline_overlap = load_overlap_data(baseline_dir / "OVERLAP.json")
    target_overlap = load_overlap_data(target_dir / "OVERLAP.json")
    
    # Load evidence data
    baseline_evidence = load_evidence_data(baseline_dir / "EVIDENCE.md")
    target_evidence = load_evidence_data(target_dir / "EVIDENCE.md")
    
    # Extract metrics
    baseline_infoshare = baseline_evidence.get("INFO SHARE SUMMARY", {})
    target_infoshare = target_evidence.get("INFO SHARE SUMMARY", {})
    
    baseline_spread = baseline_evidence.get("SPREAD SUMMARY", {})
    target_spread = target_evidence.get("SPREAD SUMMARY", {})
    
    baseline_leadlag = baseline_evidence.get("LEADLAG SUMMARY", {})
    target_leadlag = target_evidence.get("LEADLAG SUMMARY", {})
    
    # Calculate JS distance
    baseline_venues = baseline_infoshare.get("venues", {})
    target_venues = target_infoshare.get("venues", {})
    js_distance = calculate_js_distance(baseline_venues, target_venues)
    
    # Check spread p-value flip
    baseline_p = baseline_spread.get("p_value", 1.0)
    target_p = target_spread.get("p_value", 1.0)
    spread_flip = (baseline_p < 0.05) != (target_p < 0.05)
    
    # Check lead-lag delta
    baseline_coord = baseline_leadlag.get("coordination", 0.0)
    target_coord = target_leadlag.get("coordination", 0.0)
    leadlag_delta = abs(target_coord - baseline_coord)
    
    # Check top leader
    baseline_leader = baseline_leadlag.get("top_leader", "")
    target_leader = target_leadlag.get("top_leader", "")
    leader_stable = baseline_leader == target_leader
    
    # Determine regression status
    regression_passed = (
        js_distance <= max_js and
        not (spread_flip and no_spread_flip) and
        leadlag_delta <= max_leadlag_delta and
        leader_stable
    )
    
    result = {
        "regression_passed": regression_passed,
        "js_distance": js_distance,
        "js_threshold": max_js,
        "spread_flip": spread_flip,
        "spread_p_baseline": baseline_p,
        "spread_p_target": target_p,
        "leadlag_delta": leadlag_delta,
        "leadlag_delta_threshold": max_leadlag_delta,
        "leader_stable": leader_stable,
        "baseline_leader": baseline_leader,
        "target_leader": target_leader,
        "baseline_venues": list(baseline_venues.keys()),
        "target_venues": list(target_venues.keys()),
        "baseline_coordination": baseline_coord,
        "target_coordination": target_coord
    }
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Run regression analysis between BEST4 and BEST2 bundles")
    parser.add_argument("--baseline-overlap", required=True, help="Baseline OVERLAP.json file")
    parser.add_argument("--target-overlap", required=True, help="Target OVERLAP.json file")
    parser.add_argument("--max-js", type=float, default=0.02, help="Maximum JS distance")
    parser.add_argument("--max-leadlag-delta", type=float, default=0.10, help="Maximum lead-lag delta")
    parser.add_argument("--no-spread-flip", action="store_true", help="No spread p-value flip allowed")
    parser.add_argument("--out", required=True, help="Output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    baseline_dir = Path(args.baseline_overlap).parent
    target_dir = Path(args.target_overlap).parent
    output_file = Path(args.out)
    
    try:
        # Run regression analysis
        result = analyze_regression(
            baseline_dir, 
            target_dir, 
            args.max_js, 
            args.max_leadlag_delta, 
            args.no_spread_flip
        )
        
        # Write results
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Print summary
        status = "PASS" if result["regression_passed"] else "FAIL"
        print(f"[REGRESSION:{status}] JS={result['js_distance']:.4f}, LeadLagΔ={result['leadlag_delta']:.4f}, Leader={result['leader_stable']}")
        
        if not result["regression_passed"]:
            print("Regression failed:")
            if result["js_distance"] > args.max_js:
                print(f"  - JS distance {result['js_distance']:.4f} > {args.max_js}")
            if result["spread_flip"] and args.no_spread_flip:
                print(f"  - Spread p-value flip: {result['spread_p_baseline']:.4f} → {result['spread_p_target']:.4f}")
            if result["leadlag_delta"] > args.max_leadlag_delta:
                print(f"  - Lead-lag delta {result['leadlag_delta']:.4f} > {args.max_leadlag_delta}")
            if not result["leader_stable"]:
                print(f"  - Leader changed: {result['baseline_leader']} → {result['target_leader']}")
        
        return 0 if result["regression_passed"] else 1
        
    except Exception as e:
        logger.error(f"Regression analysis failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
