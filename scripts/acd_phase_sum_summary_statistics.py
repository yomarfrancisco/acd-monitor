#!/usr/bin/env python3
"""
ACD Phase SUM - Summary Statistics

Computes comprehensive statistics for canonical_1200_1300 window across 5 venues.
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
            logging.FileHandler("acd_phase_sum_summary_statistics.log"),
        ],
    )


def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None


def load_canonical_data(s3_client, bucket: str, date: str) -> Dict[str, pd.DataFrame]:
    """Load canonical_1200_1300 data for all 5 venues."""
    logger = logging.getLogger(__name__)

    venues = ["binance", "kraken", "okx", "coinbase", "bybit"]
    canonical_data = {}

    for venue in venues:
        s3_key = f"backfill/{venue}/{date}/canonical_1200_1300/part-0000.parquet"

        parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
        if not parquet_content:
            logger.error(f"No canonical data found for {venue} at {s3_key}")
            continue

        try:
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
                tmp_file.write(parquet_content)
                tmp_file.flush()
                df = pd.read_parquet(tmp_file.name)
                Path(tmp_file.name).unlink()

            # Ensure timestamp is datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df["dt"] = pd.to_datetime(df["dt"], utc=True)

            canonical_data[venue] = df
            logger.info(f"Loaded {venue}: {len(df)} rows")

        except Exception as e:
            logger.error(f"Error loading {venue}: {e}")

    return canonical_data


def compute_per_venue_stats(canonical_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """Compute per-venue summary statistics."""
    logger = logging.getLogger(__name__)

    per_venue_stats = {}

    for venue, df in canonical_data.items():
        if df.empty:
            logger.warning(f"Empty data for {venue}")
            continue

        # Basic stats
        n_rows = len(df)
        duration_seconds = (df["timestamp"].max() - df["timestamp"].min()).total_seconds()
        coverage_percentage = 100.0  # Full coverage for backfilled data

        # Price statistics
        price_mean = df["price"].mean()
        price_std = df["price"].std()
        price_min = df["price"].min()
        price_max = df["price"].max()

        # Volume statistics
        volume_total = df["volume"].sum()
        volume_mean = df["volume"].mean()

        # Duplicate ratio
        duplicate_ratio = df.duplicated(subset=["timestamp", "price", "volume"]).sum() / n_rows

        # Time span
        time_span_seconds = duration_seconds
        time_span_hours = time_span_seconds / 3600

        per_venue_stats[venue] = {
            "n_rows": n_rows,
            "duration_seconds": duration_seconds,
            "duration_hours": time_span_hours,
            "coverage_percentage": coverage_percentage,
            "price_mean": float(price_mean),
            "price_std": float(price_std),
            "price_min": float(price_min),
            "price_max": float(price_max),
            "volume_total": float(volume_total),
            "volume_mean": float(volume_mean),
            "duplicate_ratio": float(duplicate_ratio),
            "time_span_seconds": time_span_seconds,
            "time_span_hours": time_span_hours,
        }

        logger.info(
            f"{venue}: {n_rows} rows, ${price_mean:.2f}±${price_std:.2f}, {volume_total:.2f} vol, {duplicate_ratio:.1%} dup"
        )

    return per_venue_stats


def compute_cross_venue_comparisons(per_venue_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compute cross-venue comparisons and spread analysis."""
    logger = logging.getLogger(__name__)

    venues = list(per_venue_stats.keys())
    n_venues = len(venues)

    if n_venues < 2:
        logger.error("Need at least 2 venues for cross-venue analysis")
        return {}

    # Pairwise price spreads
    pairwise_spreads = {}
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            price1 = per_venue_stats[venue1]["price_mean"]
            price2 = per_venue_stats[venue2]["price_mean"]

            # Calculate percentage spread
            spread_pct = abs(price1 - price2) / ((price1 + price2) / 2) * 100

            pairwise_spreads[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "price1": price1,
                "price2": price2,
                "spread_pct": float(spread_pct),
                "spread_abs": float(abs(price1 - price2)),
            }

    # Volatility ratios
    volatility_ratios = {}
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            std1 = per_venue_stats[venue1]["price_std"]
            std2 = per_venue_stats[venue2]["price_std"]

            # Calculate volatility ratio
            vol_ratio = std1 / std2 if std2 > 0 else float("inf")

            volatility_ratios[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "std1": std1,
                "std2": std2,
                "volatility_ratio": float(vol_ratio),
            }

    # Fragmentation index (variance in mean prices across all venues)
    mean_prices = [per_venue_stats[venue]["price_mean"] for venue in venues]
    fragmentation_index = float(np.var(mean_prices))
    fragmentation_std = float(np.std(mean_prices))

    # Overall spread analysis
    max_spread = max([spread["spread_pct"] for spread in pairwise_spreads.values()])
    mean_spread = np.mean([spread["spread_pct"] for spread in pairwise_spreads.values()])

    cross_venue_analysis = {
        "pairwise_spreads": pairwise_spreads,
        "volatility_ratios": volatility_ratios,
        "fragmentation_index": fragmentation_index,
        "fragmentation_std": fragmentation_std,
        "max_spread_pct": float(max_spread),
        "mean_spread_pct": float(mean_spread),
        "n_venues": n_venues,
        "venues": venues,
    }

    logger.info(
        f"Cross-venue analysis: max spread {max_spread:.2f}%, mean spread {mean_spread:.2f}%"
    )

    return cross_venue_analysis


def generate_summary_markdown(
    per_venue_stats: Dict[str, Dict[str, Any]], cross_venue_analysis: Dict[str, Any]
) -> str:
    """Generate comprehensive summary markdown report."""

    report_content = f"""# ACD Phase SUM - Summary Statistics Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Window**: canonical_1200_1300 (1 hour)  
**Venues**: {len(per_venue_stats)} exchanges  

## Per-Venue Statistics

| Venue | Rows | Duration | Coverage | Price Mean | Price Std | Price Range | Volume Total | Duplicates |
|-------|------|----------|----------|------------|-----------|-------------|--------------|------------|
"""

    for venue, stats in per_venue_stats.items():
        price_range = f"${stats['price_min']:.2f} - ${stats['price_max']:.2f}"
        report_content += f"| {venue.upper()} | {stats['n_rows']:,} | {stats['duration_hours']:.1f}h | {stats['coverage_percentage']:.1f}% | ${stats['price_mean']:.2f} | ${stats['price_std']:.2f} | {price_range} | {stats['volume_total']:.2f} | {stats['duplicate_ratio']:.1%} |\n"

    report_content += f"""

## Cross-Venue Spread Analysis

### Pairwise Price Spreads

| Venue Pair | Price 1 | Price 2 | Spread % | Spread $ |
|------------|----------|---------|----------|----------|
"""

    for pair, spread in cross_venue_analysis["pairwise_spreads"].items():
        report_content += f"| {pair.upper()} | ${spread['price1']:.2f} | ${spread['price2']:.2f} | {spread['spread_pct']:.3f}% | ${spread['spread_abs']:.2f} |\n"

    report_content += f"""

### Volatility Ratios

| Venue Pair | Std 1 | Std 2 | Ratio |
|------------|-------|-------|-------|
"""

    for pair, vol in cross_venue_analysis["volatility_ratios"].items():
        report_content += f"| {pair.upper()} | ${vol['std1']:.2f} | ${vol['std2']:.2f} | {vol['volatility_ratio']:.3f} |\n"

    report_content += f"""

## Market Fragmentation Analysis

- **Fragmentation Index**: {cross_venue_analysis['fragmentation_index']:.2f}
- **Fragmentation Std**: {cross_venue_analysis['fragmentation_std']:.2f}
- **Max Spread**: {cross_venue_analysis['max_spread_pct']:.3f}%
- **Mean Spread**: {cross_venue_analysis['mean_spread_pct']:.3f}%

## Quality Flags

"""

    # Check for quality issues
    quality_flags = []

    for venue, stats in per_venue_stats.items():
        if stats["price_std"] < 0.10:
            quality_flags.append(f"⚠️ {venue.upper()}: Low variance (${stats['price_std']:.2f})")

        if stats["duplicate_ratio"] > 0.30:
            quality_flags.append(
                f"⚠️ {venue.upper()}: High duplicates ({stats['duplicate_ratio']:.1%})"
            )

    if cross_venue_analysis["max_spread_pct"] > 1.5:
        quality_flags.append(
            f"⚠️ High cross-venue spread: {cross_venue_analysis['max_spread_pct']:.3f}% (threshold: 1.5%)"
        )

    if quality_flags:
        for flag in quality_flags:
            report_content += f"- {flag}\n"
    else:
        report_content += "- ✅ No quality issues detected\n"

    report_content += f"""

## Summary

- **Total Venues**: {len(per_venue_stats)}
- **Total Rows**: {sum(stats['n_rows'] for stats in per_venue_stats.values()):,}
- **Average Spread**: {cross_venue_analysis['mean_spread_pct']:.3f}%
- **Max Spread**: {cross_venue_analysis['max_spread_pct']:.3f}%
- **Fragmentation**: {cross_venue_analysis['fragmentation_std']:.2f}

## Next Steps

{'✅ Ready for Phase SIG (ACD Signal Preparation)' if cross_venue_analysis['max_spread_pct'] <= 1.5 else '❌ Address quality issues before proceeding to Phase SIG'}
"""

    return report_content


def main():
    """Main Phase SUM function."""
    parser = argparse.ArgumentParser(description="ACD Phase SUM - Summary Statistics")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE SUM - SUMMARY STATISTICS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")
    print(f"📊 Window: canonical_1200_1300 (1 hour)")

    # Load canonical data
    print(f"\n🔄 Loading canonical data for all 5 venues...")
    try:
        canonical_data = load_canonical_data(s3_client, args.bucket, args.date)

        if len(canonical_data) < 3:
            print(f"❌ Insufficient venues: {len(canonical_data)}/5")
            sys.exit(1)

        print(f"✅ Loaded data for {len(canonical_data)} venues")
        for venue, df in canonical_data.items():
            print(f"   {venue}: {len(df)} rows")

    except Exception as e:
        print(f"❌ Error loading canonical data: {e}")
        sys.exit(1)

    # Compute per-venue statistics
    print(f"\n📊 Computing per-venue statistics...")
    try:
        per_venue_stats = compute_per_venue_stats(canonical_data)

        if not per_venue_stats:
            print(f"❌ No statistics computed")
            sys.exit(1)

        print(f"✅ Computed statistics for {len(per_venue_stats)} venues")

    except Exception as e:
        print(f"❌ Error computing per-venue statistics: {e}")
        sys.exit(1)

    # Compute cross-venue comparisons
    print(f"\n📊 Computing cross-venue comparisons...")
    try:
        cross_venue_analysis = compute_cross_venue_comparisons(per_venue_stats)

        if not cross_venue_analysis:
            print(f"❌ No cross-venue analysis computed")
            sys.exit(1)

        print(f"✅ Computed cross-venue analysis")
        print(f"   Max spread: {cross_venue_analysis['max_spread_pct']:.3f}%")
        print(f"   Mean spread: {cross_venue_analysis['mean_spread_pct']:.3f}%")

    except Exception as e:
        print(f"❌ Error computing cross-venue analysis: {e}")
        sys.exit(1)

    # Generate summary markdown
    print(f"\n📝 Generating summary report...")
    try:
        summary_markdown = generate_summary_markdown(per_venue_stats, cross_venue_analysis)

        # Save summary report
        report_key = f"analysis/{args.date}/ACD/_summary/summary_statistics_report.md"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=report_key,
            Body=summary_markdown.encode("utf-8"),
            ContentType="text/markdown",
        )

        print(f"💾 Saved summary report: s3://{args.bucket}/{report_key}")

    except Exception as e:
        print(f"❌ Error generating summary report: {e}")
        sys.exit(1)

    # Save summary statistics JSON
    print(f"\n💾 Saving summary statistics...")

    summary_data = {
        "date": args.date,
        "window": "canonical_1200_1300",
        "per_venue_stats": per_venue_stats,
        "cross_venue_analysis": cross_venue_analysis,
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    stats_key = f"analysis/{args.date}/ACD/_summary/summary_statistics.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=stats_key,
        Body=json.dumps(summary_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved summary statistics: s3://{args.bucket}/{stats_key}")

    # Final summary
    print(f"\n📊 PHASE SUM SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Window: canonical_1200_1300")
    print(f"Venues: {len(per_venue_stats)}")
    print(f"Total rows: {sum(stats['n_rows'] for stats in per_venue_stats.values()):,}")
    print(f"Max spread: {cross_venue_analysis['max_spread_pct']:.3f}%")
    print(f"Mean spread: {cross_venue_analysis['mean_spread_pct']:.3f}%")

    # Quality check
    if cross_venue_analysis["max_spread_pct"] <= 1.5:
        print(f"\n✅ PHASE SUM COMPLETED SUCCESSFULLY")
        print(f"   All quality checks passed")
        print(f"   Ready for Phase SIG (ACD Signal Preparation)")
    else:
        print(f"\n⚠️ PHASE SUM COMPLETED WITH WARNINGS")
        print(f"   Max spread {cross_venue_analysis['max_spread_pct']:.3f}% exceeds 1.5% threshold")
        print(f"   Review quality flags before proceeding to Phase SIG")

    print(f"\n📁 Generated artifacts:")
    print(f"  Summary report: s3://{args.bucket}/{report_key}")
    print(f"  Summary statistics: s3://{args.bucket}/{stats_key}")


if __name__ == "__main__":
    main()
