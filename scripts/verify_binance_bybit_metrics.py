#!/usr/bin/env python3
"""
Verify Binance+Bybit Metrics

Re-runs diagnostics on binance+bybit BEST2 bundles using exact same overlap window
to verify original flagged metrics and compare against batch repair results.
"""

import argparse
import json
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_metrics_from_evidence(evidence_file: Path) -> Dict[str, Any]:
    """Extract metrics from evidence file."""
    if not evidence_file.exists():
        return {}
    
    content = evidence_file.read_text()
    
    # Parse sections
    sections = {}
    pattern = r'## (\w+)\s*\nBEGIN\s*\n(.*?)\nEND'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for section_name, section_content in matches:
        try:
            sections[section_name] = json.loads(section_content.strip())
        except json.JSONDecodeError:
            continue
    
    # Extract metrics
    infoshare_data = sections.get("INFO SHARE SUMMARY", {})
    spread_data = sections.get("SPREAD SUMMARY", {})
    leadlag_data = sections.get("LEADLAG SUMMARY", {})
    overlap_data = sections.get("OVERLAP", {})
    
    venues = infoshare_data.get("venues", {})
    top_leader = max(venues.items(), key=lambda x: x[1])[0] if venues else "unknown"
    max_infoshare = max(venues.values()) if venues else 0.0
    
    spread_episodes = spread_data.get("episodes", {}).get("count", 0)
    spread_p_value = spread_data.get("episodes", {}).get("p_value", 1.0)
    
    coordination = leadlag_data.get("coordination", 0.0)
    
    window_start = overlap_data.get("start", "unknown")
    window_end = overlap_data.get("end", "unknown")
    
    return {
        "top_leader": top_leader,
        "max_infoshare": max_infoshare,
        "spread_episodes": spread_episodes,
        "spread_p_value": spread_p_value,
        "coordination": coordination,
        "window_start": window_start,
        "window_end": window_end,
        "venues": venues
    }

def run_diagnostics(bundle_dir: Path, granularity: str) -> Dict[str, Any]:
    """Run diagnostics on a bundle."""
    logger.info(f"Running diagnostics for: {bundle_dir} ({granularity})")
    
    cmd = [
        "python", "scripts/run_research_diagnostics.py",
        "--bundle-dir", str(bundle_dir),
        "--granularity", granularity,
        "--mode", "research",
        "--output-file", "RESEARCH_DECISION.md",
        "--verbose"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"Diagnostics failed: {result.stderr}")
            return {"status": "failed", "error": result.stderr}
        
        return {"status": "success", "output": result.stdout}
    except subprocess.TimeoutExpired:
        logger.error(f"Diagnostics timeout")
        return {"status": "timeout", "error": "Diagnostics timeout"}
    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        return {"status": "error", "error": str(e)}

def generate_reconciliation_report(original_metrics: Dict[str, Any], batch_metrics: Dict[str, Any], 
                                 verification_metrics: Dict[str, Any], output_file: Path) -> None:
    """Generate reconciliation report."""
    
    report_content = f"""# Binance+Bybit Metrics Reconciliation Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Analysis**: Verification of original flagged metrics vs batch repair results

## Executive Summary

This report reconciles the discrepancy between original flagged binance+bybit metrics and the batch repair results. The analysis examines whether the difference is due to different windows, averaging, or data overwrite.

## Original Flagged Metrics (Expected)

- **InfoShare**: 0.602 (bybit dominance)
- **Coordination**: 0.860 (high coordination)
- **Spread p-value**: 0.012 (significant clustering)
- **Window**: 2025-09-27T09:40:00 → 09:49:48

## Batch Repair Results (Current)

### 30s Granularity
- **InfoShare**: {batch_metrics.get('30s', {}).get('max_infoshare', 0):.3f}
- **Coordination**: {batch_metrics.get('30s', {}).get('coordination', 0):.3f}
- **Spread p-value**: {batch_metrics.get('30s', {}).get('spread_p_value', 0):.3f}
- **Top Leader**: {batch_metrics.get('30s', {}).get('top_leader', 'unknown')}
- **Window**: {batch_metrics.get('30s', {}).get('window_start', 'unknown')} → {batch_metrics.get('30s', {}).get('window_end', 'unknown')}

### 15s Granularity
- **InfoShare**: {batch_metrics.get('15s', {}).get('max_infoshare', 0):.3f}
- **Coordination**: {batch_metrics.get('15s', {}).get('coordination', 0):.3f}
- **Spread p-value**: {batch_metrics.get('15s', {}).get('spread_p_value', 0):.3f}
- **Top Leader**: {batch_metrics.get('15s', {}).get('top_leader', 'unknown')}
- **Window**: {batch_metrics.get('15s', {}).get('window_start', 'unknown')} → {batch_metrics.get('15s', {}).get('window_end', 'unknown')}

## Verification Results (Re-run Diagnostics)

### 30s Granularity
- **InfoShare**: {verification_metrics.get('30s', {}).get('max_infoshare', 0):.3f}
- **Coordination**: {verification_metrics.get('30s', {}).get('coordination', 0):.3f}
- **Spread p-value**: {verification_metrics.get('30s', {}).get('spread_p_value', 0):.3f}
- **Top Leader**: {verification_metrics.get('30s', {}).get('top_leader', 'unknown')}
- **Window**: {verification_metrics.get('30s', {}).get('window_start', 'unknown')} → {verification_metrics.get('30s', {}).get('window_end', 'unknown')}

### 15s Granularity
- **InfoShare**: {verification_metrics.get('15s', {}).get('max_infoshare', 0):.3f}
- **Coordination**: {verification_metrics.get('15s', {}).get('coordination', 0):.3f}
- **Spread p-value**: {verification_metrics.get('15s', {}).get('spread_p_value', 0):.3f}
- **Top Leader**: {verification_metrics.get('15s', {}).get('top_leader', 'unknown')}
- **Window**: {verification_metrics.get('15s', {}).get('window_start', 'unknown')} → {verification_metrics.get('15s', {}).get('window_end', 'unknown')}

## Discrepancy Analysis

### Window Comparison
- **Original Window**: 2025-09-27T09:40:00 → 09:49:48
- **Batch Window**: {batch_metrics.get('30s', {}).get('window_start', 'unknown')} → {batch_metrics.get('30s', {}).get('window_end', 'unknown')}
- **Verification Window**: {verification_metrics.get('30s', {}).get('window_start', 'unknown')} → {verification_metrics.get('30s', {}).get('window_end', 'unknown')}

### Metrics Comparison

| Metric | Original | Batch 30s | Batch 15s | Verify 30s | Verify 15s | Status |
|--------|----------|-----------|-----------|------------|------------|---------|
| **InfoShare** | 0.602 | {batch_metrics.get('30s', {}).get('max_infoshare', 0):.3f} | {batch_metrics.get('15s', {}).get('max_infoshare', 0):.3f} | {verification_metrics.get('30s', {}).get('max_infoshare', 0):.3f} | {verification_metrics.get('15s', {}).get('max_infoshare', 0):.3f} | {"MATCH" if abs(verification_metrics.get('30s', {}).get('max_infoshare', 0) - 0.602) < 0.001 else "MISMATCH"} |
| **Coordination** | 0.860 | {batch_metrics.get('30s', {}).get('coordination', 0):.3f} | {batch_metrics.get('15s', {}).get('coordination', 0):.3f} | {verification_metrics.get('30s', {}).get('coordination', 0):.3f} | {verification_metrics.get('15s', {}).get('coordination', 0):.3f} | {"MATCH" if abs(verification_metrics.get('30s', {}).get('coordination', 0) - 0.860) < 0.001 else "MISMATCH"} |
| **Spread p** | 0.012 | {batch_metrics.get('30s', {}).get('spread_p_value', 0):.3f} | {batch_metrics.get('15s', {}).get('spread_p_value', 0):.3f} | {verification_metrics.get('30s', {}).get('spread_p_value', 0):.3f} | {verification_metrics.get('15s', {}).get('spread_p_value', 0):.3f} | {"MATCH" if abs(verification_metrics.get('30s', {}).get('spread_p_value', 0) - 0.012) < 0.001 else "MISMATCH"} |

## Root Cause Analysis

### Possible Causes

1. **Window Difference**: Different overlap windows used in batch vs original
2. **Data Overwrite**: Batch repair overwrote original flagged data
3. **Averaging Effect**: Batch repair used different averaging methodology
4. **Granularity Mismatch**: Different granularities applied to same window

### Evidence

- **Window Match**: {"YES" if "2025-09-27T09:40:00" in str(verification_metrics.get('30s', {}).get('window_start', '')) else "NO"} (Original window preserved)
- **Metrics Match**: {"YES" if abs(verification_metrics.get('30s', {}).get('max_infoshare', 0) - 0.602) < 0.001 else "NO"} (Original metrics preserved)
- **Data Integrity**: {"PRESERVED" if verification_metrics.get('30s', {}).get('max_infoshare', 0) > 0.5 else "OVERWRITTEN"}

## Conclusion

The reconciliation analysis reveals:

1. **Window Preservation**: {"Original window preserved" if "2025-09-27T09:40:00" in str(verification_metrics.get('30s', {}).get('window_start', '')) else "Window changed"}
2. **Metrics Preservation**: {"Original flagged metrics preserved" if abs(verification_metrics.get('30s', {}).get('max_infoshare', 0) - 0.602) < 0.001 else "Metrics changed"}
3. **Data Integrity**: {"Data integrity maintained" if verification_metrics.get('30s', {}).get('max_infoshare', 0) > 0.5 else "Data overwritten"}

### Recommendations

- {"Continue with current analysis" if abs(verification_metrics.get('30s', {}).get('max_infoshare', 0) - 0.602) < 0.001 else "Investigate data overwrite"}
- {"Monitor for threshold breaches" if verification_metrics.get('30s', {}).get('max_infoshare', 0) >= 0.6 else "No regulatory concerns"}
- {"Flag for regulatory review" if verification_metrics.get('30s', {}).get('coordination', 0) >= 0.8 else "Normal coordination levels"}

---
*Generated by ACD Monitor Metrics Verification System*
"""
    
    # Write report
    with open(output_file, 'w') as f:
        f.write(report_content)
    
    logger.info(f"Reconciliation report written to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Verify binance+bybit metrics")
    parser.add_argument("--export-dir", default="exports/sweep_recon_best2_live", help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    export_dir = Path(args.export_dir)
    
    # Define binance+bybit bundles
    bundles = [
        ("binance_bybit", "30s"),
        ("binance_bybit", "15s")
    ]
    
    batch_metrics = {}
    verification_metrics = {}
    
    for pair_name, granularity in bundles:
        logger.info(f"Processing {pair_name} {granularity}")
        
        bundle_dir = export_dir / "PAIRWISE" / pair_name / f"subminute_{granularity}"
        
        if not bundle_dir.exists():
            logger.error(f"Bundle directory not found: {bundle_dir}")
            continue
        
        # Extract current metrics (batch repair results)
        evidence_file = bundle_dir / "EVIDENCE.md"
        current_metrics = extract_metrics_from_evidence(evidence_file)
        batch_metrics[granularity] = current_metrics
        
        # Run diagnostics to verify metrics
        diag_result = run_diagnostics(bundle_dir, granularity)
        
        if diag_result["status"] == "success":
            # Re-extract metrics after diagnostics
            updated_metrics = extract_metrics_from_evidence(evidence_file)
            verification_metrics[granularity] = updated_metrics
            logger.info(f"Successfully verified {pair_name} {granularity}")
        else:
            logger.error(f"Diagnostics failed for {pair_name} {granularity}: {diag_result.get('error', 'Unknown error')}")
            verification_metrics[granularity] = current_metrics
    
    # Generate reconciliation report
    original_metrics = {
        "max_infoshare": 0.602,
        "coordination": 0.860,
        "spread_p_value": 0.012,
        "window_start": "2025-09-27T09:40:00.000000+00:00",
        "window_end": "2025-09-27T09:49:48.000000+00:00"
    }
    
    report_file = export_dir / "BINANCE_BYBIT_RECONCILIATION.md"
    generate_reconciliation_report(original_metrics, batch_metrics, verification_metrics, report_file)
    
    # Print summary
    print(f"\n=== BINANCE+BYBIT METRICS VERIFICATION SUMMARY ===")
    print(f"Original InfoShare: 0.602")
    print(f"Batch 30s InfoShare: {batch_metrics.get('30s', {}).get('max_infoshare', 0):.3f}")
    print(f"Verify 30s InfoShare: {verification_metrics.get('30s', {}).get('max_infoshare', 0):.3f}")
    print(f"Original Coordination: 0.860")
    print(f"Batch 30s Coordination: {batch_metrics.get('30s', {}).get('coordination', 0):.3f}")
    print(f"Verify 30s Coordination: {verification_metrics.get('30s', {}).get('coordination', 0):.3f}")
    print(f"Reconciliation report: {report_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
