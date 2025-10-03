#!/usr/bin/env python3
"""
Binance Provenance Audit Script

Performs forensic provenance audit on Binance data to determine real vs synthetic classification.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("binance_provenance_audit.log"),
        ],
    )


def load_binance_data(
    s3_client, bucket: str, slice_name: str, date: str
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    """
    Load Binance data, manifest, and capture log for a specific slice.
    """
    logger = logging.getLogger(__name__)

    try:
        # Load parquet data
        sample_key = f"raw_probes/{date}/venue=binance/slice={slice_name}/sample.parquet"
        response = s3_client.get_object(Bucket=bucket, Key=sample_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Load manifest
        manifest_key = f"raw_probes/{date}/venue=binance/slice={slice_name}/probe_manifest.json"
        response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
        manifest = json.loads(response["Body"].read())

        # Load capture log
        log_key = f"raw_probes/{date}/venue=binance/slice={slice_name}/capture.log.txt"
        response = s3_client.get_object(Bucket=bucket, Key=log_key)
        capture_log = response["Body"].read().decode("utf-8")

        return df, manifest, capture_log

    except Exception as e:
        logger.error(f"Error loading Binance {slice_name}: {e}")
        return pd.DataFrame(), {}, ""


def analyze_provenance_metadata(
    manifest: Dict[str, Any], capture_log: str, slice_name: str
) -> Dict[str, Any]:
    """
    Analyze provenance metadata from manifest and capture logs.
    """
    logger = logging.getLogger(__name__)

    # Check manifest for provenance flags
    provenance_flags = {
        "data_source": manifest.get("data_source", "unknown"),
        "provenance": manifest.get("provenance", "unknown"),
        "synthetic": "synthetic" in str(manifest).lower(),
        "fallback": "fallback" in str(manifest).lower(),
        "real": "real" in str(manifest).lower(),
    }

    # Analyze capture log for API traces
    api_indicators = {
        "has_http_calls": any(
            keyword in capture_log.lower() for keyword in ["http", "api", "get", "post"]
        ),
        "has_websocket": "websocket" in capture_log.lower(),
        "has_trades_endpoint": "/api/v3/trades" in capture_log,
        "has_binance_api": "binance" in capture_log.lower(),
        "log_length": len(capture_log),
        "has_timestamps": any(char.isdigit() for char in capture_log),
    }

    # Extract timestamps from manifest
    manifest_timestamps = {
        "start_time": manifest.get("start_time"),
        "end_time": manifest.get("end_time"),
        "timestamp": manifest.get("timestamp"),
        "msgs": manifest.get("msgs", 0),
        "parse_rate": manifest.get("parse_rate", 0.0),
    }

    return {
        "slice": slice_name,
        "provenance_flags": provenance_flags,
        "api_indicators": api_indicators,
        "manifest_timestamps": manifest_timestamps,
        "capture_log_preview": capture_log[:500] if capture_log else "No log available",
    }


def analyze_temporal_patterns(df: pd.DataFrame, slice_name: str) -> Dict[str, Any]:
    """
    Analyze temporal patterns to detect synthetic data.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {
            "slice": slice_name,
            "temporal_analysis": "empty_dataframe",
            "synthetic_indicators": {},
        }

    # Sort by timestamp
    df_sorted = df.sort_values("dt").reset_index(drop=True)

    # Calculate time differences
    time_diffs = df_sorted["dt"].diff().dropna()
    time_diffs_ms = time_diffs.dt.total_seconds() * 1000

    # Check for regular intervals (synthetic indicator)
    regular_intervals = False
    if len(time_diffs_ms) > 1:
        interval_std = np.std(time_diffs_ms)
        interval_mean = np.mean(time_diffs_ms)
        # If std dev is very low relative to mean, likely regular intervals
        regular_intervals = (
            interval_std < (interval_mean * 0.1) and interval_std < 1000
        )  # < 1 second std

    # Check for perfect 1-second spacing
    perfect_1s_spacing = False
    if len(time_diffs_ms) > 1:
        perfect_1s_spacing = all(
            abs(diff - 1000) < 100 for diff in time_diffs_ms
        )  # Within 100ms of 1s

    # Check for geometric Brownian motion patterns
    prices = df_sorted["price"].values
    price_changes = np.diff(prices)

    # Geometric Brownian motion indicators
    gbm_indicators = {
        "constant_volatility": np.std(price_changes) < 1.0,  # Very low volatility
        "smooth_transitions": len(np.where(np.abs(price_changes) > 10)[0])
        < len(price_changes) * 0.1,  # <10% large changes
        "no_jumps": np.max(np.abs(price_changes)) < 50,  # No large price jumps
    }

    # Duplicate analysis
    exact_duplicates = df_sorted.duplicated().sum()
    timestamp_duplicates = df_sorted["timestamp"].duplicated().sum()
    price_duplicates = df_sorted["price"].duplicated().sum()

    duplicate_ratio = exact_duplicates / len(df_sorted) if len(df_sorted) > 0 else 0

    # Synthetic indicators
    synthetic_indicators = {
        "regular_intervals": regular_intervals,
        "perfect_1s_spacing": perfect_1s_spacing,
        "high_duplicate_ratio": duplicate_ratio > 0.3,  # >30% duplicates
        "geometric_brownian": all(gbm_indicators.values()),
        "no_api_traces": True,  # Will be updated based on capture log analysis
        "synthetic_score": 0,  # Will be calculated
    }

    # Calculate synthetic score (0-100, higher = more likely synthetic)
    synthetic_score = 0
    if regular_intervals:
        synthetic_score += 30
    if perfect_1s_spacing:
        synthetic_score += 25
    if duplicate_ratio > 0.3:
        synthetic_score += 20
    if all(gbm_indicators.values()):
        synthetic_score += 15
    if duplicate_ratio > 0.4:
        synthetic_score += 10

    synthetic_indicators["synthetic_score"] = synthetic_score

    return {
        "slice": slice_name,
        "temporal_analysis": {
            "total_rows": len(df_sorted),
            "time_span_seconds": (df_sorted["dt"].max() - df_sorted["dt"].min()).total_seconds(),
            "mean_interval_ms": float(np.mean(time_diffs_ms)) if len(time_diffs_ms) > 0 else 0,
            "std_interval_ms": float(np.std(time_diffs_ms)) if len(time_diffs_ms) > 0 else 0,
            "first_timestamp": df_sorted["dt"].min().isoformat(),
            "last_timestamp": df_sorted["dt"].max().isoformat(),
        },
        "synthetic_indicators": synthetic_indicators,
        "duplicate_analysis": {
            "exact_duplicates": int(exact_duplicates),
            "timestamp_duplicates": int(timestamp_duplicates),
            "price_duplicates": int(price_duplicates),
            "duplicate_ratio": float(duplicate_ratio),
        },
    }


def analyze_price_sanity(df: pd.DataFrame, slice_name: str) -> Dict[str, Any]:
    """
    Analyze price sanity and statistical properties.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {"slice": slice_name, "price_analysis": "empty_dataframe"}

    prices = df["price"].values

    # Basic statistics
    price_stats = {
        "mean": float(np.mean(prices)),
        "std": float(np.std(prices)),
        "min": float(np.min(prices)),
        "max": float(np.max(prices)),
        "range": float(np.max(prices) - np.min(prices)),
        "first_price": float(prices[0]),
        "last_price": float(prices[-1]),
        "price_drift": float(prices[-1] - prices[0]),
    }

    # Sanity bounds check
    sanity_bounds = {
        "below_50k": np.sum(prices < 50000),
        "above_500k": np.sum(prices > 500000),
        "sanity_violations": np.sum((prices < 50000) | (prices > 500000)),
    }

    # Outlier detection (3σ rule)
    price_mean = np.mean(prices)
    price_std = np.std(prices)
    outliers = 0
    if price_std > 0:
        outliers = np.sum(np.abs(prices - price_mean) > (3 * price_std))

    return {
        "slice": slice_name,
        "price_analysis": price_stats,
        "sanity_bounds": sanity_bounds,
        "outliers_3sigma": int(outliers),
        "outlier_ratio": float(outliers / len(prices)) if len(prices) > 0 else 0,
    }


def cross_venue_consistency_check(
    binance_stats: Dict[str, Any], reference_venues: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Check if Binance deviates >1% from Coinbase/Kraken means.
    """
    logger = logging.getLogger(__name__)

    binance_mean = binance_stats.get("price_analysis", {}).get("mean", 0)

    if binance_mean == 0:
        return {"consistency_check": "no_binance_data", "deviations": {}}

    deviations = {}
    for venue, stats in reference_venues.items():
        venue_mean = stats.get("price_analysis", {}).get("mean", 0)
        if venue_mean > 0:
            deviation = abs(binance_mean - venue_mean) / venue_mean * 100
            deviations[venue] = {
                "mean_price": venue_mean,
                "deviation_percent": float(deviation),
                "significant_deviation": deviation > 1.0,
            }

    return {
        "consistency_check": "completed",
        "binance_mean": binance_mean,
        "deviations": deviations,
        "any_significant_deviations": any(
            dev.get("significant_deviation", False) for dev in deviations.values()
        ),
    }


def generate_provenance_timeline(
    provenance_metadata: Dict[str, Any],
    temporal_patterns: Dict[str, Any],
    price_sanity: Dict[str, Any],
    consistency_check: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate clear timeline with provenance verdicts.
    """
    logger = logging.getLogger(__name__)

    # Determine provenance verdict
    synthetic_score = temporal_patterns.get("synthetic_indicators", {}).get("synthetic_score", 0)
    duplicate_ratio = temporal_patterns.get("duplicate_analysis", {}).get("duplicate_ratio", 0)
    has_api_traces = provenance_metadata.get("api_indicators", {}).get("has_http_calls", False)

    # Provenance classification logic
    if synthetic_score >= 70:
        verdict = "SYNTHETIC"
        confidence = "HIGH"
    elif synthetic_score >= 40:
        verdict = "LIKELY_SYNTHETIC"
        confidence = "MEDIUM"
    elif duplicate_ratio > 0.4 and not has_api_traces:
        verdict = "SUSPICIOUS"
        confidence = "MEDIUM"
    elif has_api_traces and synthetic_score < 30:
        verdict = "REAL"
        confidence = "HIGH"
    else:
        verdict = "INDETERMINATE"
        confidence = "LOW"

    # Evidence summary
    evidence = {
        "synthetic_score": synthetic_score,
        "duplicate_ratio": duplicate_ratio,
        "has_api_traces": has_api_traces,
        "regular_intervals": temporal_patterns.get("synthetic_indicators", {}).get(
            "regular_intervals", False
        ),
        "perfect_1s_spacing": temporal_patterns.get("synthetic_indicators", {}).get(
            "perfect_1s_spacing", False
        ),
        "high_duplicates": duplicate_ratio > 0.3,
        "geometric_brownian": temporal_patterns.get("synthetic_indicators", {}).get(
            "geometric_brownian", False
        ),
    }

    return {
        "slice": temporal_patterns.get("slice", "unknown"),
        "verdict": verdict,
        "confidence": confidence,
        "evidence": evidence,
        "timestamp_range": temporal_patterns.get("temporal_analysis", {}).get(
            "first_timestamp", "unknown"
        ),
        "price_mean": price_sanity.get("price_analysis", {}).get("mean", 0),
        "total_rows": temporal_patterns.get("temporal_analysis", {}).get("total_rows", 0),
    }


def main():
    """Main audit function."""
    parser = argparse.ArgumentParser(description="Binance provenance audit")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--date", default="20251002", help="Date to analyze (YYYYMMDD)")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 BINANCE PROVENANCE AUDIT")
    print("=" * 80)

    # Step 1: Load Binance data for all slices
    logger.info("Step 1: Loading Binance data and metadata...")

    binance_slices = ["slice_00", "slice_01"]
    all_audit_results = {}

    for slice_name in binance_slices:
        logger.info(f"Analyzing Binance {slice_name}...")

        # Load data
        df, manifest, capture_log = load_binance_data(s3_client, args.bucket, slice_name, args.date)

        if df.empty:
            logger.warning(f"No data for Binance {slice_name}")
            continue

        # Step 2: Analyze provenance metadata
        provenance_metadata = analyze_provenance_metadata(manifest, capture_log, slice_name)

        # Step 3: Analyze temporal patterns
        temporal_patterns = analyze_temporal_patterns(df, slice_name)

        # Step 4: Analyze price sanity
        price_sanity = analyze_price_sanity(df, slice_name)

        # Step 5: Cross-venue consistency (using previous analysis if available)
        consistency_check = {"consistency_check": "pending_reference_data", "deviations": {}}

        # Step 6: Generate provenance timeline
        timeline = generate_provenance_timeline(
            provenance_metadata, temporal_patterns, price_sanity, consistency_check
        )

        all_audit_results[slice_name] = {
            "provenance_metadata": provenance_metadata,
            "temporal_patterns": temporal_patterns,
            "price_sanity": price_sanity,
            "consistency_check": consistency_check,
            "timeline": timeline,
        }

    # Step 7: Generate comprehensive report
    logger.info("Step 7: Generating comprehensive audit report...")

    # Print summary
    print(f"\n📊 BINANCE PROVENANCE AUDIT RESULTS")
    print("-" * 60)

    for slice_name, results in all_audit_results.items():
        timeline = results["timeline"]
        temporal = results["temporal_patterns"]

        print(f"\n🔍 {slice_name.upper()}")
        print(f"   Verdict: {timeline['verdict']} ({timeline['confidence']} confidence)")
        print(f"   Synthetic Score: {timeline['evidence']['synthetic_score']}/100")
        print(f"   Duplicate Ratio: {timeline['evidence']['duplicate_ratio']:.1%}")
        print(f"   API Traces: {'✅ Yes' if timeline['evidence']['has_api_traces'] else '❌ No'}")
        print(
            f"   Regular Intervals: {'⚠️ Yes' if timeline['evidence']['regular_intervals'] else '✅ No'}"
        )
        print(
            f"   Perfect 1s Spacing: {'⚠️ Yes' if timeline['evidence']['perfect_1s_spacing'] else '✅ No'}"
        )
        print(f"   Rows: {temporal.get('temporal_analysis', {}).get('total_rows', 0)}")
        print(
            f"   Time Span: {temporal.get('temporal_analysis', {}).get('time_span_seconds', 0):.1f}s"
        )

    # Step 8: Generate timeline table
    print(f"\n📋 PROVENANCE TIMELINE")
    print("-" * 60)
    print(
        "| Slice     | Verdict           | Confidence | Synthetic Score | Duplicates | API Traces |"
    )
    print(
        "|-----------|-------------------|------------|-----------------|------------|------------|"
    )

    for slice_name, results in all_audit_results.items():
        timeline = results["timeline"]
        print(
            f"| {slice_name:<9} | {timeline['verdict']:<17} | {timeline['confidence']:<10} | {timeline['evidence']['synthetic_score']:<15} | {timeline['evidence']['duplicate_ratio']:<10.1%} | {'✅' if timeline['evidence']['has_api_traces'] else '❌':<10} |"
        )

    # Step 9: Store results to S3
    logger.info("Step 9: Storing audit results to S3...")

    # Create comprehensive audit report
    audit_report = {
        "audit_date": args.date,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "binance_slices": all_audit_results,
        "summary": {
            "total_slices": len(all_audit_results),
            "synthetic_slices": len(
                [r for r in all_audit_results.values() if r["timeline"]["verdict"] == "SYNTHETIC"]
            ),
            "real_slices": len(
                [r for r in all_audit_results.values() if r["timeline"]["verdict"] == "REAL"]
            ),
            "indeterminate_slices": len(
                [
                    r
                    for r in all_audit_results.values()
                    if r["timeline"]["verdict"] == "INDETERMINATE"
                ]
            ),
        },
    }

    # Store to S3
    s3_prefix = f"analysis/{args.date}/binance_provenance_audit"

    # JSON report
    json_key = f"{s3_prefix}/binance_provenance_audit.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=json_key,
        Body=json.dumps(audit_report, indent=2, default=str),
        ContentType="application/json",
    )

    # Markdown report
    markdown_content = generate_markdown_report(audit_report)
    markdown_key = f"{s3_prefix}/binance_provenance_audit.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=markdown_key,
        Body=markdown_content.encode("utf-8"),
        ContentType="text/markdown",
    )

    logger.info(f"📁 Audit results stored to S3:")
    logger.info(f"  JSON: s3://{args.bucket}/{json_key}")
    logger.info(f"  Markdown: s3://{args.bucket}/{markdown_key}")

    print(f"\n📁 Audit results stored to S3:")
    print(f"  JSON: s3://{args.bucket}/{json_key}")
    print(f"  Markdown: s3://{args.bucket}/{markdown_key}")

    # Save local copy
    local_json_file = f"binance_provenance_audit_{args.date}.json"
    local_md_file = f"binance_provenance_audit_{args.date}.md"

    with open(local_json_file, "w") as f:
        json.dump(audit_report, f, indent=2, default=str)

    with open(local_md_file, "w") as f:
        f.write(markdown_content)

    logger.info(f"📁 Local copies saved:")
    logger.info(f"  JSON: {local_json_file}")
    logger.info(f"  Markdown: {local_md_file}")


def generate_markdown_report(audit_report: Dict[str, Any]) -> str:
    """Generate Markdown report."""
    report = []

    # Header
    report.append("# Binance Provenance Audit Report")
    report.append(f"**Generated**: {audit_report['audit_timestamp']}")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    summary = audit_report["summary"]
    report.append(f"- **Total Slices Analyzed**: {summary['total_slices']}")
    report.append(f"- **Synthetic Slices**: {summary['synthetic_slices']}")
    report.append(f"- **Real Slices**: {summary['real_slices']}")
    report.append(f"- **Indeterminate Slices**: {summary['indeterminate_slices']}")
    report.append("")

    # Detailed Results
    report.append("## Detailed Analysis")
    report.append("")

    for slice_name, results in audit_report["binance_slices"].items():
        timeline = results["timeline"]
        temporal = results["temporal_patterns"]
        price = results["price_sanity"]

        report.append(f"### {slice_name.upper()}")
        report.append("")
        report.append(f"**Verdict**: {timeline['verdict']} ({timeline['confidence']} confidence)")
        report.append(f"**Synthetic Score**: {timeline['evidence']['synthetic_score']}/100")
        report.append("")

        # Evidence
        report.append("**Evidence**:")
        report.append(f"- Duplicate Ratio: {timeline['evidence']['duplicate_ratio']:.1%}")
        report.append(
            f"- API Traces: {'✅ Present' if timeline['evidence']['has_api_traces'] else '❌ Absent'}"
        )
        report.append(
            f"- Regular Intervals: {'⚠️ Yes' if timeline['evidence']['regular_intervals'] else '✅ No'}"
        )
        report.append(
            f"- Perfect 1s Spacing: {'⚠️ Yes' if timeline['evidence']['perfect_1s_spacing'] else '✅ No'}"
        )
        report.append(
            f"- High Duplicates: {'⚠️ Yes' if timeline['evidence']['high_duplicates'] else '✅ No'}"
        )
        report.append(
            f"- Geometric Brownian: {'⚠️ Yes' if timeline['evidence']['geometric_brownian'] else '✅ No'}"
        )
        report.append("")

        # Statistics
        report.append("**Statistics**:")
        report.append(f"- Total Rows: {temporal.get('temporal_analysis', {}).get('total_rows', 0)}")
        report.append(
            f"- Time Span: {temporal.get('temporal_analysis', {}).get('time_span_seconds', 0):.1f} seconds"
        )
        report.append(f"- Mean Price: ${price.get('price_analysis', {}).get('mean', 0):,.2f}")
        report.append(
            f"- Price Range: ${price.get('price_analysis', {}).get('min', 0):,.2f} - ${price.get('price_analysis', {}).get('max', 0):,.2f}"
        )
        report.append("")

    # Recommendations
    report.append("## Recommendations")
    report.append("")

    synthetic_count = summary["synthetic_slices"]
    if synthetic_count > 0:
        report.append(
            "⚠️ **Synthetic data detected** - Consider excluding Binance from ACD analysis until provenance is resolved."
        )
    else:
        report.append("✅ **No synthetic data detected** - Binance data appears to be real.")

    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    main()
