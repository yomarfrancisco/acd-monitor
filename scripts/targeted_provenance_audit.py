#!/usr/bin/env python3
"""
Targeted Forensic Provenance Audit

Directly analyzes the available 20251002 data for comprehensive provenance audit.
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
            logging.FileHandler("targeted_provenance_audit.log"),
        ],
    )


def analyze_slice_provenance(
    s3_client, bucket: str, venue: str, date: str, slice_name: str
) -> Dict[str, Any]:
    """
    Analyze provenance for a specific venue/date/slice combination.
    """
    logger = logging.getLogger(__name__)

    try:
        # Load data
        sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
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
        manifest_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
        response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
        manifest = json.loads(response["Body"].read())

        # Load capture log
        log_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/capture.log.txt"
        try:
            response = s3_client.get_object(Bucket=bucket, Key=log_key)
            capture_log = response["Body"].read().decode("utf-8")
        except:
            capture_log = ""

        # Analyze temporal patterns
        if df.empty:
            return {
                "venue": venue,
                "date": date,
                "slice": slice_name,
                "verdict": "NO_DATA",
                "confidence": "N/A",
                "synthetic_score": 0,
                "duplicate_ratio": 0.0,
                "price_std": 0.0,
                "outlier_count": 0,
                "api_traces": False,
                "evidence_summary": "No data available",
            }

        # Calculate duplicates
        exact_duplicates = df.duplicated().sum()
        duplicate_ratio = exact_duplicates / len(df)

        # Calculate price statistics
        prices = df["price"].values
        price_mean = np.mean(prices)
        price_std = np.std(prices)

        # Outlier detection (3σ rule)
        outliers = 0
        if price_std > 0:
            outliers = np.sum(np.abs(prices - price_mean) > (3 * price_std))

        # Check for regular intervals
        time_diffs = df["dt"].diff().dropna()
        time_diffs_ms = time_diffs.dt.total_seconds() * 1000
        regular_intervals = False
        if len(time_diffs_ms) > 1:
            interval_std = np.std(time_diffs_ms)
            interval_mean = np.mean(time_diffs_ms)
            regular_intervals = interval_std < (interval_mean * 0.1) and interval_std < 1000

        # Check for perfect 1s spacing
        perfect_1s_spacing = False
        if len(time_diffs_ms) > 1:
            perfect_1s_spacing = all(abs(diff - 1000) < 100 for diff in time_diffs_ms)

        # API trace analysis
        api_traces = {
            "has_http_calls": any(
                keyword in capture_log.lower() for keyword in ["http", "api", "get", "post"]
            ),
            "has_websocket": "websocket" in capture_log.lower(),
            "has_trades_endpoint": "/api/v3/trades" in capture_log,
            "has_venue_api": venue in capture_log.lower(),
            "log_length": len(capture_log),
        }

        # Calculate synthetic score
        synthetic_score = 0
        if regular_intervals:
            synthetic_score += 30
        if perfect_1s_spacing:
            synthetic_score += 25
        if duplicate_ratio > 0.3:
            synthetic_score += 20
        if duplicate_ratio > 0.4:
            synthetic_score += 15
        if not any(api_traces.values()):
            synthetic_score += 10

        # Determine verdict
        if synthetic_score >= 70:
            verdict = "SYNTHETIC"
            confidence = "HIGH"
        elif synthetic_score >= 40:
            verdict = "LIKELY_SYNTHETIC"
            confidence = "MEDIUM"
        elif duplicate_ratio > 0.3 and not any(api_traces.values()):
            verdict = "SUSPICIOUS"
            confidence = "MEDIUM"
        elif any(api_traces.values()) and synthetic_score < 30:
            verdict = "REAL"
            confidence = "HIGH"
        elif duplicate_ratio < 0.1 and synthetic_score < 20:
            verdict = "REAL"
            confidence = "MEDIUM"
        else:
            verdict = "INDETERMINATE"
            confidence = "LOW"

        # Evidence summary
        evidence_parts = []
        if duplicate_ratio > 0.1:
            evidence_parts.append(f"{duplicate_ratio:.1%} duplicates")
        if regular_intervals:
            evidence_parts.append("regular intervals")
        if perfect_1s_spacing:
            evidence_parts.append("perfect 1s spacing")
        if any(api_traces.values()):
            evidence_parts.append("API traces present")
        else:
            evidence_parts.append("no API traces")
        if outliers > 0:
            evidence_parts.append(f"{outliers} outliers")

        evidence_summary = ", ".join(evidence_parts) if evidence_parts else "no clear indicators"

        return {
            "venue": venue,
            "date": date,
            "slice": slice_name,
            "verdict": verdict,
            "confidence": confidence,
            "synthetic_score": synthetic_score,
            "duplicate_ratio": float(duplicate_ratio),
            "price_std": float(price_std),
            "outlier_count": int(outliers),
            "api_traces": any(api_traces.values()),
            "evidence_summary": evidence_summary,
            "total_rows": len(df),
            "time_span_seconds": (df["dt"].max() - df["dt"].min()).total_seconds(),
            "price_mean": float(price_mean),
            "price_min": float(np.min(prices)),
            "price_max": float(np.max(prices)),
            "first_timestamp": df["dt"].min().isoformat(),
            "last_timestamp": df["dt"].max().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error analyzing {venue} {date} {slice_name}: {e}")
        return {
            "venue": venue,
            "date": date,
            "slice": slice_name,
            "verdict": "ERROR",
            "confidence": "N/A",
            "synthetic_score": 0,
            "duplicate_ratio": 0.0,
            "price_std": 0.0,
            "outlier_count": 0,
            "api_traces": False,
            "evidence_summary": f"Error: {str(e)}",
        }


def cross_venue_consistency_check(
    venue_results: Dict[str, Dict[str, Any]], date: str, slice_name: str
) -> Dict[str, Any]:
    """
    Check cross-venue consistency for a specific date/slice.
    """
    logger = logging.getLogger(__name__)

    # Get results for this date/slice
    slice_results = {}
    for venue, results in venue_results.items():
        if date in results and slice_name in results[date]:
            slice_results[venue] = results[date][slice_name]

    if len(slice_results) < 2:
        return {
            "date": date,
            "slice": slice_name,
            "consistency_check": "insufficient_data",
            "spread_analysis": {},
            "volatility_analysis": {},
            "anomalies": [],
        }

    # Price level comparison
    price_means = {}
    price_stds = {}
    for venue, result in slice_results.items():
        if result["verdict"] != "ERROR" and result["total_rows"] > 0:
            price_means[venue] = result["price_mean"]
            price_stds[venue] = result["price_std"]

    spread_analysis = {}
    volatility_analysis = {}
    anomalies = []

    if len(price_means) >= 2:
        # Calculate spreads
        prices = list(price_means.values())
        min_price = min(prices)
        max_price = max(prices)
        spread_absolute = max_price - min_price
        spread_percentage = (spread_absolute / min_price) * 100 if min_price > 0 else 0

        spread_analysis = {
            "min_price": min_price,
            "max_price": max_price,
            "spread_absolute": spread_absolute,
            "spread_percentage": spread_percentage,
            "significant_spread": spread_percentage > 1.0,
        }

        if spread_percentage > 1.0:
            anomalies.append(f"Significant price spread: {spread_percentage:.2f}%")

    if len(price_stds) >= 2:
        # Calculate volatility differences
        stds = list(price_stds.values())
        min_std = min(stds)
        max_std = max(stds)
        volatility_ratio = max_std / min_std if min_std > 0 else 0

        volatility_analysis = {
            "min_volatility": min_std,
            "max_volatility": max_std,
            "volatility_ratio": volatility_ratio,
            "significant_volatility_diff": volatility_ratio > 10.0,
        }

        if volatility_ratio > 10.0:
            anomalies.append(f"Significant volatility difference: {volatility_ratio:.1f}x")

    return {
        "date": date,
        "slice": slice_name,
        "consistency_check": "completed",
        "spread_analysis": spread_analysis,
        "volatility_analysis": volatility_analysis,
        "anomalies": anomalies,
        "venues_compared": list(slice_results.keys()),
    }


def identify_switch_points(venue_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identify switch points for Binance (earliest REAL, first SYNTHETIC).
    """
    logger = logging.getLogger(__name__)

    binance_results = venue_results.get("binance", {})

    # Find earliest REAL data
    earliest_real = None
    first_synthetic = None

    for date in sorted(binance_results.keys()):
        for slice_name in sorted(binance_results[date].keys()):
            result = binance_results[date][slice_name]

            if result["verdict"] == "REAL" and earliest_real is None:
                earliest_real = {"date": date, "slice": slice_name, "result": result}

            if result["verdict"] in ["SYNTHETIC", "LIKELY_SYNTHETIC"] and first_synthetic is None:
                first_synthetic = {"date": date, "slice": slice_name, "result": result}

    return {
        "earliest_real": earliest_real,
        "first_synthetic": first_synthetic,
        "has_real_data": earliest_real is not None,
        "has_synthetic_data": first_synthetic is not None,
    }


def main():
    """Main audit function."""
    parser = argparse.ArgumentParser(description="Targeted provenance audit")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to analyze (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 TARGETED FORENSIC PROVENANCE AUDIT")
    print("=" * 80)

    # Step 1: Analyze provenance for each venue
    logger.info("Step 1: Analyzing provenance timeline...")

    venues = ["binance", "coinbase", "kraken"]
    venue_results = {}

    for venue in venues:
        logger.info(f"Analyzing {venue}...")
        venue_results[venue] = {}
        venue_results[venue][args.date] = {}

        # Analyze both slices
        for slice_name in ["slice_00", "slice_01"]:
            result = analyze_slice_provenance(s3_client, args.bucket, venue, args.date, slice_name)
            venue_results[venue][args.date][slice_name] = result

    # Step 2: Cross-venue consistency checks
    logger.info("Step 2: Performing cross-venue consistency checks...")

    consistency_results = {}
    for slice_name in ["slice_00", "slice_01"]:
        consistency = cross_venue_consistency_check(venue_results, args.date, slice_name)
        consistency_results[f"{args.date}_{slice_name}"] = consistency

    # Step 3: Identify switch points
    logger.info("Step 3: Identifying switch points...")
    switch_points = identify_switch_points(venue_results)

    # Step 4: Generate comprehensive report
    logger.info("Step 4: Generating comprehensive report...")

    # Print summary
    print(f"\n📊 PROVENANCE SUMMARY")
    print("-" * 60)

    for venue in venues:
        print(f"\n🏢 {venue.upper()}")

        # Count verdicts
        verdict_counts = {}
        for date, slices in venue_results[venue].items():
            for slice_name, result in slices.items():
                verdict = result["verdict"]
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        for verdict, count in verdict_counts.items():
            print(f"  {verdict}: {count} slices")

    # Switch points
    print(f"\n🔄 SWITCH POINTS")
    print("-" * 60)

    if switch_points["earliest_real"]:
        earliest = switch_points["earliest_real"]
        print(f"✅ Earliest REAL Binance data: {earliest['date']} {earliest['slice']}")
    else:
        print("❌ No REAL Binance data found")

    if switch_points["first_synthetic"]:
        first_synth = switch_points["first_synthetic"]
        print(f"⚠️ First SYNTHETIC Binance data: {first_synth['date']} {first_synth['slice']}")
    else:
        print("✅ No SYNTHETIC Binance data found")

    # Detailed results
    print(f"\n📋 DETAILED PROVENANCE TIMELINE")
    print("-" * 60)
    print(
        "| Date     | Slice     | Venue     | Verdict           | Confidence | Synthetic Score | Duplicates | API Traces | Evidence |"
    )
    print(
        "|----------|-----------|-----------|-------------------|------------|-----------------|------------|------------|---------|"
    )

    for venue in venues:
        for slice_name in ["slice_00", "slice_01"]:
            result = venue_results[venue][args.date][slice_name]
            print(
                f"| {result['date']} | {result['slice']} | {result['venue'].upper():<9} | {result['verdict']:<17} | {result['confidence']:<10} | {result['synthetic_score']:<15} | {result['duplicate_ratio']:<10.1%} | {'✅' if result['api_traces'] else '❌':<10} | {result['evidence_summary']} |"
            )

    # Cross-venue consistency
    print(f"\n📈 CROSS-VENUE CONSISTENCY")
    print("-" * 60)

    for slice_name in ["slice_00", "slice_01"]:
        consistency = consistency_results[f"{args.date}_{slice_name}"]
        print(f"\n{slice_name.upper()}:")
        if consistency["spread_analysis"]:
            spread = consistency["spread_analysis"]
            print(
                f"  Price Spread: ${spread['spread_absolute']:,.2f} ({spread['spread_percentage']:.2f}%)"
            )
            if spread["significant_spread"]:
                print(f"  ⚠️ Significant spread detected!")

        if consistency["volatility_analysis"]:
            vol = consistency["volatility_analysis"]
            print(f"  Volatility Ratio: {vol['volatility_ratio']:.1f}x")
            if vol["significant_volatility_diff"]:
                print(f"  ⚠️ Significant volatility difference!")

        if consistency["anomalies"]:
            for anomaly in consistency["anomalies"]:
                print(f"  ⚠️ {anomaly}")

    # Step 5: Store results
    logger.info("Step 5: Storing results to S3...")

    # Create comprehensive audit report
    audit_report = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_date": args.date,
        "venue_results": venue_results,
        "consistency_results": consistency_results,
        "switch_points": switch_points,
        "summary": {
            "total_venues": len(venue_results),
            "total_slices_analyzed": sum(
                len(slices) for results in venue_results.values() for slices in results.values()
            ),
        },
    }

    # Store to S3
    s3_prefix = f"analysis/{args.date}/provenance_timeline"

    # JSON report
    json_key = f"{s3_prefix}/targeted_provenance_audit.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=json_key,
        Body=json.dumps(audit_report, indent=2, default=str),
        ContentType="application/json",
    )

    # Markdown report
    markdown_content = generate_markdown_report(audit_report)
    markdown_key = f"{s3_prefix}/targeted_provenance_audit.md"
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
    local_json_file = f"targeted_provenance_audit_{args.date}.json"
    local_md_file = f"targeted_provenance_audit_{args.date}.md"

    with open(local_json_file, "w") as f:
        json.dump(audit_report, f, indent=2, default=str)

    with open(local_md_file, "w") as f:
        f.write(markdown_content)

    logger.info(f"📁 Local copies saved:")
    logger.info(f"  JSON: {local_json_file}")
    logger.info(f"  Markdown: {local_md_file}")


def generate_markdown_report(audit_report: Dict[str, Any]) -> str:
    """Generate comprehensive Markdown report."""
    report = []

    # Header
    report.append("# Targeted Forensic Provenance Audit")
    report.append(f"**Generated**: {audit_report['audit_timestamp']}")
    report.append(f"**Analysis Date**: {audit_report['analysis_date']}")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    summary = audit_report["summary"]
    report.append(f"- **Total Venues Analyzed**: {summary['total_venues']}")
    report.append(f"- **Total Slices Analyzed**: {summary['total_slices_analyzed']}")
    report.append("")

    # Switch Points
    report.append("## Switch Points Analysis")
    report.append("")
    switch_points = audit_report["switch_points"]

    if switch_points["earliest_real"]:
        earliest = switch_points["earliest_real"]
        report.append(f"**✅ Earliest REAL Binance Data**: {earliest['date']} {earliest['slice']}")
        report.append(f"- Synthetic Score: {earliest['result']['synthetic_score']}/100")
        report.append(f"- Duplicate Ratio: {earliest['result']['duplicate_ratio']:.1%}")
        report.append(
            f"- API Traces: {'✅ Present' if earliest['result']['api_traces'] else '❌ Absent'}"
        )
    else:
        report.append("**❌ No REAL Binance data found**")

    report.append("")

    if switch_points["first_synthetic"]:
        first_synth = switch_points["first_synthetic"]
        report.append(
            f"**⚠️ First SYNTHETIC Binance Data**: {first_synth['date']} {first_synth['slice']}"
        )
        report.append(f"- Synthetic Score: {first_synth['result']['synthetic_score']}/100")
        report.append(f"- Duplicate Ratio: {first_synth['result']['duplicate_ratio']:.1%}")
        report.append(
            f"- API Traces: {'✅ Present' if first_synth['result']['api_traces'] else '❌ Absent'}"
        )
    else:
        report.append("**✅ No SYNTHETIC Binance data found**")

    report.append("")

    # Detailed Results
    report.append("## Detailed Analysis")
    report.append("")

    for venue, results in audit_report["venue_results"].items():
        report.append(f"### {venue.upper()}")
        report.append("")

        for date, slices in results.items():
            for slice_name, result in slices.items():
                report.append(
                    f"**{slice_name.upper()}**: {result['verdict']} ({result['confidence']} confidence)"
                )
                report.append(f"- Synthetic Score: {result['synthetic_score']}/100")
                report.append(f"- Duplicate Ratio: {result['duplicate_ratio']:.1%}")
                report.append(
                    f"- API Traces: {'✅ Present' if result['api_traces'] else '❌ Absent'}"
                )
                report.append(f"- Evidence: {result['evidence_summary']}")
                report.append("")

    # Cross-Venue Consistency
    report.append("## Cross-Venue Consistency")
    report.append("")

    for key, consistency in audit_report["consistency_results"].items():
        report.append(f"### {key}")
        report.append("")

        if consistency["spread_analysis"]:
            spread = consistency["spread_analysis"]
            report.append(
                f"**Price Spread**: ${spread['spread_absolute']:,.2f} ({spread['spread_percentage']:.2f}%)"
            )
            if spread["significant_spread"]:
                report.append("⚠️ **Significant spread detected!**")

        if consistency["volatility_analysis"]:
            vol = consistency["volatility_analysis"]
            report.append(f"**Volatility Ratio**: {vol['volatility_ratio']:.1f}x")
            if vol["significant_volatility_diff"]:
                report.append("⚠️ **Significant volatility difference!**")

        if consistency["anomalies"]:
            report.append("**Anomalies**:")
            for anomaly in consistency["anomalies"]:
                report.append(f"- ⚠️ {anomaly}")

        report.append("")

    # Recommendations
    report.append("## Recommendations")
    report.append("")

    # Count synthetic data
    synthetic_count = 0
    for venue, results in audit_report["venue_results"].items():
        for date, slices in results.items():
            for slice_name, result in slices.items():
                if result["verdict"] in ["SYNTHETIC", "LIKELY_SYNTHETIC"]:
                    synthetic_count += 1

    if synthetic_count > 0:
        report.append(
            "⚠️ **Synthetic data detected** - Consider excluding affected venues from ACD analysis."
        )
    else:
        report.append("✅ **No synthetic data detected** - All venues appear to have real data.")

    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    main()
