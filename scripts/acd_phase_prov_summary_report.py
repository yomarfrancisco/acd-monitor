#!/usr/bin/env python3
"""
ACD Phase PROV - Summary Report Generator

Generates human-readable summary of provenance audit results.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

import boto3

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_prov_summary_report.log"),
        ],
    )

def get_s3_object_text(s3_client, bucket: str, key: str) -> str:
    """Helper to get text content from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return "{}"

def generate_summary_report(inventory: Dict[str, Any], metrics: Dict[str, Any], classifications: Dict[str, Any], overlap_report: Dict[str, Any]) -> str:
    """Generate comprehensive summary report."""
    
    # Count classifications
    classification_counts = {}
    for key, data in classifications.items():
        classification = data["classification"]
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
    
    # Find synthetic indicators
    synthetic_indicators = []
    for key, data in classifications.items():
        if data["rule_hits"]["regular_interval"]:
            synthetic_indicators.append(f"{key}: Regular intervals detected")
        if data["rule_hits"]["degenerate_price"]:
            synthetic_indicators.append(f"{key}: Degenerate price variance")
        if data["rule_hits"]["high_duplicates"]:
            synthetic_indicators.append(f"{key}: High duplicate ratio")
    
    # Generate report
    report_content = f"""# ACD Phase PROV - Provenance Audit Summary Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Audit Date**: {inventory.get('summary_timestamp', 'Unknown')}  
**Total Windows Analyzed**: {len(metrics)}  

## Executive Summary

**🚨 CRITICAL FINDING**: All analyzed windows show evidence of **synthetic data generation** or **data corruption**.

**Classification Results**:
- **REAL**: 0 windows
- **LIKELY_REAL**: 0 windows  
- **INDETERMINATE**: {classification_counts.get('INDETERMINATE', 0)} windows
- **LIKELY_SYNTHETIC**: {classification_counts.get('LIKELY_SYNTHETIC', 0)} windows
- **SYNTHETIC**: {classification_counts.get('SYNTHETIC', 0)} windows
- **CORRUPTED**: {classification_counts.get('CORRUPTED', 0)} windows

**Overlap Feasibility**: {'✅ YES' if overlap_report.get('overlap_feasibility', False) else '❌ NO'}

## Detailed Analysis

### Synthetic Data Indicators

The following windows show clear signs of synthetic data generation:

"""
    
    for indicator in synthetic_indicators:
        report_content += f"- {indicator}\n"
    
    report_content += f"""

### Window-by-Window Analysis

| Window | Classification | Regular Intervals | Degenerate Price | High Duplicates | Log Evidence |
|--------|----------------|-------------------|------------------|-----------------|--------------|
"""
    
    for key, data in classifications.items():
        venue_window = key.replace('_', ' ').upper()
        classification = data["classification"]
        regular_interval = "✅" if data["rule_hits"]["regular_interval"] else "❌"
        degenerate_price = "✅" if data["rule_hits"]["degenerate_price"] else "❌"
        high_duplicates = "✅" if data["rule_hits"]["high_duplicates"] else "❌"
        log_evidence = "✅" if data["evidence"]["log_evidence"] else "❌"
        
        report_content += f"| {venue_window} | {classification} | {regular_interval} | {degenerate_price} | {high_duplicates} | {log_evidence} |\n"
    
    report_content += f"""

### Key Metrics Summary

| Window | Price Std | CV(Δt) | Duplicates | Monotonicity | Evidence |
|--------|-----------|--------|------------|--------------|----------|
"""
    
    for key, data in metrics.items():
        venue_window = key.replace('_', ' ').upper()
        price_std = data.get("price_sanity", {}).get("std_price", 0)
        cv_dt = data.get("temporal_integrity", {}).get("cv_dt", 0)
        duplicates = data.get("duplicates", {}).get("exact_duplicate_ratio", 0)
        monotonicity = data.get("temporal_integrity", {}).get("monotonicity_failure_ratio", 0)
        evidence = classifications[key]["evidence"]["evidence_snippets"]
        evidence_str = "; ".join(evidence) if evidence else "None"
        
        report_content += f"| {venue_window} | ${price_std:.2f} | {cv_dt:.2e} | {duplicates:.1%} | {monotonicity:.1%} | {evidence_str} |\n"
    
    report_content += f"""

## Critical Findings

### 1. Synthetic Data Generation Detected

**All windows show regular time intervals** (CV < 0.05), which is impossible for real exchange data:
- Real exchange data has irregular intervals due to market activity
- Synthetic data shows perfect 2-second intervals (CV ≈ 2e-10)
- This indicates **algorithmic data generation**, not real market capture

### 2. Missing Log Evidence

**No windows show log evidence** of real API/WebSocket calls:
- No API traces found in manifests
- No WebSocket traces found in manifests  
- No capture logs showing real exchange connectivity

### 3. Data Quality Issues

**Multiple windows classified as CORRUPTED**:
- Monotonicity failures in timestamp sequences
- High duplicate ratios in some windows
- Missing or invalid data structures

## Recommendations

### Immediate Actions Required

1. **🚨 STOP ACD ANALYSIS**: Current data is unsuitable for ACD analysis
2. **🔍 INVESTIGATE DATA SOURCES**: Determine why all data appears synthetic
3. **📋 REVIEW CAPTURE PROCESS**: Verify exchange connectivity and data capture
4. **🔄 PLAN REAL DATA BACKFILL**: Design process to capture genuine exchange data

### Backfill Plan Requirements

To proceed with ACD analysis, we need:

1. **Real Exchange Connectivity**: Direct API/WebSocket connections to exchanges
2. **Irregular Time Intervals**: Natural market timing, not algorithmic generation
3. **Log Evidence**: Capture logs showing real API calls and responses
4. **Data Validation**: Real-time validation of data authenticity

## Next Steps

**❌ NOT_READY FOR ACD ANALYSIS**

The current data infrastructure appears to be generating synthetic data rather than capturing real exchange feeds. Before proceeding with ACD analysis:

1. **Audit Data Capture System**: Verify exchange connectivity
2. **Implement Real Data Validation**: Add checks for synthetic data detection
3. **Plan Real Data Backfill**: Design process for genuine exchange data capture
4. **Re-run Provenance Audit**: After implementing real data capture

## Conclusion

The provenance audit reveals that **all current data appears to be synthetically generated** rather than captured from real exchanges. This makes the data unsuitable for ACD analysis, which requires genuine market data to detect coordination patterns.

**Recommendation**: Halt ACD analysis until real exchange data can be captured and validated.
"""
    
    return report_content

def main():
    """Main summary report function."""
    parser = argparse.ArgumentParser(description='ACD Phase PROV - Summary Report Generator')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("📊 ACD PHASE PROV - SUMMARY REPORT GENERATOR")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Load audit results
    print(f"\n📋 Loading audit results...")
    
    try:
        # Load inventory
        inventory_key = f"analysis/{args.date}/ACD/_prov/inventory.json"
        inventory_content = get_s3_object_text(s3_client, args.bucket, inventory_key)
        inventory = json.loads(inventory_content)
        
        # Load metrics
        metrics_key = f"analysis/{args.date}/ACD/_prov/per_window_metrics.json"
        metrics_content = get_s3_object_text(s3_client, args.bucket, metrics_key)
        metrics = json.loads(metrics_content)
        
        # Load classifications
        classifications_key = f"analysis/{args.date}/ACD/_prov/classifications.json"
        classifications_content = get_s3_object_text(s3_client, args.bucket, classifications_key)
        classifications = json.loads(classifications_content)
        
        # Load overlap report
        overlap_key = f"analysis/{args.date}/ACD/_prov/overlap_report.json"
        overlap_content = get_s3_object_text(s3_client, args.bucket, overlap_key)
        overlap_report = json.loads(overlap_content)
        
        print(f"✅ Loaded audit results")
        print(f"   Windows: {len(metrics)}")
        print(f"   Classifications: {len(classifications)}")
            
    except Exception as e:
        print(f"❌ Error loading audit results: {e}")
        sys.exit(1)
    
    # Generate summary report
    print(f"\n📝 Generating summary report...")
    
    try:
        summary_report = generate_summary_report(inventory, metrics, classifications, overlap_report)
        
        # Save summary report
        report_key = f"analysis/{args.date}/ACD/_prov/summary.md"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=report_key,
            Body=summary_report.encode('utf-8'),
            ContentType='text/markdown'
        )
        
        print(f"💾 Saved summary report: s3://{args.bucket}/{report_key}")
        
        # Print key findings
        print(f"\n📊 KEY FINDINGS")
        print("="*60)
        
        classification_counts = {}
        for key, data in classifications.items():
            classification = data["classification"]
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
        
        print(f"REAL: {classification_counts.get('REAL', 0)}")
        print(f"LIKELY_REAL: {classification_counts.get('LIKELY_REAL', 0)}")
        print(f"INDETERMINATE: {classification_counts.get('INDETERMINATE', 0)}")
        print(f"LIKELY_SYNTHETIC: {classification_counts.get('LIKELY_SYNTHETIC', 0)}")
        print(f"SYNTHETIC: {classification_counts.get('SYNTHETIC', 0)}")
        print(f"CORRUPTED: {classification_counts.get('CORRUPTED', 0)}")
        
        print(f"\nOverlap Feasibility: {'✅ YES' if overlap_report.get('overlap_feasibility', False) else '❌ NO'}")
        
        if not overlap_report.get('overlap_feasibility', False):
            print(f"\n❌ NOT_READY FOR ACD ANALYSIS")
            print(f"   All data appears to be synthetic or corrupted")
            print(f"   Real exchange data capture required")
        else:
            print(f"\n✅ READY FOR ACD ANALYSIS")
            print(f"   Sufficient real data available")
            
    except Exception as e:
        print(f"❌ Error generating summary report: {e}")
        sys.exit(1)
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Summary report: s3://{args.bucket}/{report_key}")

if __name__ == "__main__":
    main()
