#!/usr/bin/env python3
"""
ACD Simplified Cross-Venue Analysis

Simplified analysis focusing on available data without requiring perfect time alignment.
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
            logging.FileHandler("acd_simplified_analysis.log"),
        ],
    )


def load_venue_data(
    s3_client, bucket: str, date: str, venue: str, slice_name: str, use_backfill: bool = False
) -> pd.DataFrame:
    """Load venue data from S3."""
    logger = logging.getLogger(__name__)

    if use_backfill and venue == "binance":
        # Use backfilled Binance data
        data_key = f"backfill/binance/{date}/slice_01/part-0000.parquet"
    else:
        # Use original probe data
        data_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"

    try:
        response = s3_client.get_object(Bucket=bucket, Key=data_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        logger.info(f"Loaded {len(df)} rows from {venue} {slice_name}")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} {slice_name}: {e}")
        raise


def analyze_venue_data(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Analyze individual venue data."""
    logger = logging.getLogger(__name__)

    if df.empty:
        return {
            "venue": venue,
            "rows": 0,
            "duration_seconds": 0,
            "price_mean": None,
            "price_std": None,
            "price_min": None,
            "price_max": None,
            "volume_total": None,
            "trade_count": 0,
            "time_range": None,
            "usable": False,
        }

    # Convert timestamps
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # Basic stats
    rows = len(df)
    duration_seconds = (df["timestamp_dt"].max() - df["timestamp_dt"].min()).total_seconds()

    # Price analysis
    prices = df["price"]
    price_mean = prices.mean()
    price_std = prices.std()
    price_min = prices.min()
    price_max = prices.max()

    # Volume analysis
    volumes = df["volume"]
    volume_total = volumes.sum()

    # Time range
    time_range = {
        "start": df["timestamp_dt"].min().isoformat(),
        "end": df["timestamp_dt"].max().isoformat(),
        "duration_seconds": duration_seconds,
    }

    # Usability criteria
    usable = (
        rows > 10  # At least 10 trades
        and duration_seconds > 0  # Non-zero duration
        and price_std > 0  # Non-zero price variance
        and not pd.isna(price_mean)  # Valid price mean
    )

    stats = {
        "venue": venue,
        "rows": rows,
        "duration_seconds": duration_seconds,
        "price_mean": float(price_mean),
        "price_std": float(price_std),
        "price_min": float(price_min),
        "price_max": float(price_max),
        "volume_total": float(volume_total),
        "trade_count": rows,
        "time_range": time_range,
        "usable": usable,
    }

    logger.info(
        f"{venue}: {rows} rows, {duration_seconds:.1f}s, ${price_mean:.2f}±${price_std:.2f}, usable: {usable}"
    )

    return stats


def compute_cross_venue_metrics(venue_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compute cross-venue metrics from individual venue stats."""
    logger = logging.getLogger(__name__)

    usable_venues = {venue: stats for venue, stats in venue_stats.items() if stats["usable"]}

    if len(usable_venues) < 2:
        return {
            "insufficient_venues": True,
            "usable_venues": list(usable_venues.keys()),
            "reason": f"Only {len(usable_venues)} usable venues (need at least 2)",
        }

    # Cross-venue spreads
    spreads = {}
    venues = list(usable_venues.keys())

    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            price1 = usable_venues[venue1]["price_mean"]
            price2 = usable_venues[venue2]["price_mean"]
            spread = abs(price1 - price2) / price2 * 100
            spreads[f"{venue1}_{venue2}"] = spread

    # Volatility comparison
    volatilities = {venue: stats["price_std"] for venue, stats in usable_venues.items()}
    max_vol = max(volatilities.values())
    min_vol = min(volatilities.values())
    vol_ratio = max_vol / min_vol if min_vol > 0 else float("inf")

    # Volume comparison
    volumes = {venue: stats["volume_total"] for venue, stats in usable_venues.items()}
    max_vol_vol = max(volumes.values())
    min_vol_vol = min(volumes.values())
    vol_vol_ratio = max_vol_vol / min_vol_vol if min_vol_vol > 0 else float("inf")

    # Time overlap analysis
    time_ranges = {venue: stats["time_range"] for venue, stats in usable_venues.items()}

    # Find common time window
    all_starts = [pd.to_datetime(tr["start"]) for tr in time_ranges.values()]
    all_ends = [pd.to_datetime(tr["end"]) for tr in time_ranges.values()]

    common_start = max(all_starts)
    common_end = min(all_ends)

    if common_start < common_end:
        overlap_seconds = (common_end - common_start).total_seconds()
        overlap_percentage = (
            overlap_seconds / max([tr["duration_seconds"] for tr in time_ranges.values()]) * 100
        )
    else:
        overlap_seconds = 0
        overlap_percentage = 0

    cross_venue_metrics = {
        "usable_venues": list(usable_venues.keys()),
        "venue_count": len(usable_venues),
        "spreads": spreads,
        "max_spread": max(spreads.values()) if spreads else 0,
        "volatilities": volatilities,
        "volatility_ratio": vol_ratio,
        "volumes": volumes,
        "volume_ratio": vol_vol_ratio,
        "time_overlap": {
            "overlap_seconds": overlap_seconds,
            "overlap_percentage": overlap_percentage,
            "common_start": common_start.isoformat() if overlap_seconds > 0 else None,
            "common_end": common_end.isoformat() if overlap_seconds > 0 else None,
        },
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Cross-venue metrics computed for {len(usable_venues)} venues")

    return cross_venue_metrics


def generate_acd_indicators_simplified(
    venue_stats: Dict[str, Dict[str, Any]], cross_venue_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate simplified ACD indicators."""
    logger = logging.getLogger(__name__)

    indicators = {
        "data_quality": {},
        "market_structure": {},
        "coordination_signals": {},
        "competition_signals": {},
        "risk_indicators": {},
    }

    # Data quality indicators
    usable_venues = [venue for venue, stats in venue_stats.items() if stats["usable"]]
    total_venues = len(venue_stats)

    indicators["data_quality"] = {
        "total_venues": total_venues,
        "usable_venues": len(usable_venues),
        "data_quality_score": len(usable_venues) / total_venues,
        "sufficient_data": len(usable_venues) >= 2,
    }

    # Market structure indicators
    if cross_venue_metrics.get("volatility_ratio"):
        vol_ratio = cross_venue_metrics["volatility_ratio"]
        indicators["market_structure"] = {
            "volatility_ratio": vol_ratio,
            "market_fragmentation": vol_ratio > 5.0,
            "balanced_volatility": 1.5 <= vol_ratio <= 5.0,
            "coordinated_volatility": vol_ratio < 1.5,
        }

    # Coordination signals (based on spread consistency)
    if cross_venue_metrics.get("spreads"):
        spreads = cross_venue_metrics["spreads"]
        max_spread = max(spreads.values()) if spreads else 0
        avg_spread = np.mean(list(spreads.values())) if spreads else 0

        indicators["coordination_signals"] = {
            "max_spread": max_spread,
            "average_spread": avg_spread,
            "high_coordination": max_spread < 1.0,
            "moderate_coordination": 1.0 <= max_spread < 2.0,
            "low_coordination": max_spread >= 2.0,
        }

    # Competition signals (based on volume and volatility differences)
    if cross_venue_metrics.get("volume_ratio"):
        vol_ratio = cross_venue_metrics["volume_ratio"]
        indicators["competition_signals"] = {
            "volume_ratio": vol_ratio,
            "high_competition": vol_ratio > 10.0,
            "moderate_competition": 3.0 < vol_ratio <= 10.0,
            "low_competition": vol_ratio <= 3.0,
        }

    # Risk indicators
    risk_factors = []

    if cross_venue_metrics.get("max_spread", 0) > 2.0:
        risk_factors.append("high_spread")

    if cross_venue_metrics.get("volatility_ratio", 0) > 5.0:
        risk_factors.append("high_volatility_ratio")

    if cross_venue_metrics.get("time_overlap", {}).get("overlap_percentage", 0) < 50:
        risk_factors.append("poor_time_alignment")

    indicators["risk_indicators"] = {
        "risk_factors": risk_factors,
        "risk_level": (
            "high" if len(risk_factors) > 1 else "moderate" if len(risk_factors) == 1 else "low"
        ),
        "time_alignment_risk": cross_venue_metrics.get("time_overlap", {}).get(
            "overlap_percentage", 0
        )
        < 50,
    }

    logger.info("Simplified ACD indicators generated")

    return indicators


def main():
    """Main simplified analysis function."""
    parser = argparse.ArgumentParser(description="ACD Simplified Cross-Venue Analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD SIMPLIFIED CROSS-VENUE ANALYSIS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")

    # Load venue data
    print(f"\n🔄 Loading venue data...")
    venues_data = {}

    try:
        # Load all venues
        venues_data["binance"] = load_venue_data(
            s3_client, args.bucket, args.date, "binance", "slice_01", use_backfill=True
        )
        venues_data["coinbase"] = load_venue_data(
            s3_client, args.bucket, args.date, "coinbase", "slice_01"
        )
        venues_data["kraken"] = load_venue_data(
            s3_client, args.bucket, args.date, "kraken", "slice_01"
        )

        print(
            f"✅ Loaded data: Binance ({len(venues_data['binance'])} rows), Coinbase ({len(venues_data['coinbase'])} rows), Kraken ({len(venues_data['kraken'])} rows)"
        )
    except Exception as e:
        print(f"❌ Error loading venue data: {e}")
        sys.exit(1)

    # Analyze individual venues
    print(f"\n📊 Analyzing individual venues...")
    venue_stats = {}

    for venue, df in venues_data.items():
        venue_stats[venue] = analyze_venue_data(df, venue)

    # Cross-venue metrics
    print(f"\n🔍 Computing cross-venue metrics...")
    try:
        cross_venue_metrics = compute_cross_venue_metrics(venue_stats)

        if cross_venue_metrics.get("insufficient_venues"):
            print(f"❌ Insufficient usable venues: {cross_venue_metrics['reason']}")
            sys.exit(1)

        print(f"✅ Cross-venue metrics computed for {cross_venue_metrics['venue_count']} venues")

    except Exception as e:
        print(f"❌ Error computing cross-venue metrics: {e}")
        sys.exit(1)

    # ACD indicators
    print(f"\n🎯 Generating ACD indicators...")
    try:
        acd_indicators = generate_acd_indicators_simplified(venue_stats, cross_venue_metrics)

        print(f"✅ ACD indicators generated")

    except Exception as e:
        print(f"❌ Error generating ACD indicators: {e}")
        sys.exit(1)

    # Save results
    print(f"\n💾 Saving results...")

    results_data = {
        "date": args.date,
        "venue_stats": venue_stats,
        "cross_venue_metrics": cross_venue_metrics,
        "acd_indicators": acd_indicators,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"analysis/{args.date}/_diag/acd_simplified_analysis.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")

    # Final summary
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Usable venues: {cross_venue_metrics['venue_count']}")
    print(f"Max spread: {cross_venue_metrics['max_spread']:.2f}%")
    print(f"Volatility ratio: {cross_venue_metrics['volatility_ratio']:.2f}")
    print(f"Time overlap: {cross_venue_metrics['time_overlap']['overlap_percentage']:.1f}%")

    # Decision table
    print(f"\n📋 DECISION TABLE")
    print("=" * 60)
    print(f"| Venue | Rows | Duration | Price Mean | Volatility | Usable |")
    print(f"|-------|------|----------|------------|------------|--------|")

    for venue, stats in venue_stats.items():
        status = "✅ Yes" if stats["usable"] else "❌ No"
        print(
            f"| {venue.capitalize()} | {stats['rows']} | {stats['duration_seconds']:.1f}s | ${stats['price_mean']:.2f} | {stats['price_std']:.2f} | {status} |"
        )

    # ACD indicators summary
    if acd_indicators.get("coordination_signals"):
        coord = acd_indicators["coordination_signals"]
        print(f"\n🎯 COORDINATION SIGNALS")
        print(f"   Max spread: {coord['max_spread']:.2f}%")
        print(
            f"   Level: {'High' if coord['high_coordination'] else 'Moderate' if coord['moderate_coordination'] else 'Low'}"
        )

    if acd_indicators.get("competition_signals"):
        comp = acd_indicators["competition_signals"]
        print(f"\n🏆 COMPETITION SIGNALS")
        print(f"   Volume ratio: {comp['volume_ratio']:.2f}")
        print(
            f"   Level: {'High' if comp['high_competition'] else 'Moderate' if comp['moderate_competition'] else 'Low'}"
        )

    if acd_indicators.get("risk_indicators"):
        risk = acd_indicators["risk_indicators"]
        print(f"\n⚠️ RISK INDICATORS")
        print(f"   Risk level: {risk['risk_level']}")
        print(
            f"   Risk factors: {', '.join(risk['risk_factors']) if risk['risk_factors'] else 'None'}"
        )

    print(f"\n📁 Generated artifacts:")
    print(f"  Analysis results: s3://{args.bucket}/{results_key}")


if __name__ == "__main__":
    main()
