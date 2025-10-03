#!/usr/bin/env python3
"""
ACD Phase SIG - Pre-ACD Signals

Computes exploratory ACD signals for tick-aligned data.
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
from scipy import stats


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_sig_pre_acd_signals.log"),
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


def get_s3_object_text(s3_client, bucket: str, key: str) -> Optional[str]:
    """Helper to get text content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None


def load_clean_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load cleaned data for a venue."""
    logger = logging.getLogger(__name__)

    s3_key = f"analysis/{date}/ACD/_cln/{venue}/part-0000.parquet"
    parquet_content = get_s3_object_content(s3_client, bucket, s3_key)

    if not parquet_content:
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()

        # Ensure timestamp is datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        logger.info(f"Loaded {venue} clean data: {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} clean data: {e}")
        return None


def create_aligned_bins(
    venues_data: Dict[str, pd.DataFrame], bin_size_seconds: int = 1
) -> Dict[str, pd.DataFrame]:
    """Create 1-second aligned bins for all venues."""
    logger = logging.getLogger(__name__)

    aligned_data = {}

    for venue, df in venues_data.items():
        if df.empty:
            continue

        # Sort by timestamp
        df = df.sort_values("timestamp")

        # Create 1-second bins
        df["bin"] = df["timestamp"].dt.floor(f"{bin_size_seconds}S")

        # Aggregate within bins
        bin_data = (
            df.groupby("bin")
            .agg(
                {
                    "price": "last",  # Last price in bin
                    "volume": "sum",  # Total volume in bin
                    "timestamp": "count",  # Number of trades in bin
                }
            )
            .rename(columns={"timestamp": "n_trades"})
        )

        # Reset index to get bin as column
        bin_data = bin_data.reset_index()
        bin_data["venue"] = venue

        aligned_data[venue] = bin_data

        logger.info(f"{venue}: {len(bin_data)} bins created")

    return aligned_data


def compute_return_correlations(aligned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute return correlations with time lags."""
    logger = logging.getLogger(__name__)

    if len(aligned_data) < 2:
        return {
            "status": "insufficient_venues",
            "message": "Need at least 2 venues for correlation analysis",
            "available_venues": list(aligned_data.keys()),
        }

    venues = list(aligned_data.keys())
    correlation_results = []

    # Pairwise analysis
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            df1 = aligned_data[venue1]
            df2 = aligned_data[venue2]

            if df1.empty or df2.empty:
                continue

            # Find common time bins
            common_bins = pd.merge(df1, df2, on="bin", suffixes=("_1", "_2"))

            if len(common_bins) < 10:  # Need minimum data points
                continue

            # Compute returns
            common_bins["return_1"] = common_bins["price_1"].pct_change()
            common_bins["return_2"] = common_bins["price_2"].pct_change()

            # Remove NaN values
            returns_data = common_bins[["return_1", "return_2"]].dropna()

            if len(returns_data) < 5:
                continue

            # Compute correlations with different lags
            max_lag = min(5, len(returns_data) // 4)  # Limit lag to avoid overfitting
            lag_correlations = []

            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    # Simultaneous correlation
                    corr = returns_data["return_1"].corr(returns_data["return_2"])
                elif lag > 0:
                    # venue1 leads venue2
                    if len(returns_data) > lag:
                        corr = (
                            returns_data["return_1"]
                            .iloc[:-lag]
                            .corr(returns_data["return_2"].iloc[lag:])
                        )
                    else:
                        corr = np.nan
                else:
                    # venue2 leads venue1
                    lag_abs = abs(lag)
                    if len(returns_data) > lag_abs:
                        corr = (
                            returns_data["return_1"]
                            .iloc[lag_abs:]
                            .corr(returns_data["return_2"].iloc[:-lag_abs])
                        )
                    else:
                        corr = np.nan

                lag_correlations.append(
                    {"lag": lag, "correlation": float(corr) if not np.isnan(corr) else None}
                )

            # Find best correlation
            valid_correlations = [c for c in lag_correlations if c["correlation"] is not None]
            if valid_correlations:
                best_corr = max(valid_correlations, key=lambda x: abs(x["correlation"]))
                leader = (
                    venue1
                    if best_corr["lag"] > 0
                    else venue2 if best_corr["lag"] < 0 else "simultaneous"
                )
            else:
                best_corr = {"lag": 0, "correlation": 0}
                leader = "indeterminate"

            correlation_results.append(
                {
                    "venue_pair": f"{venue1}_vs_{venue2}",
                    "venue1": venue1,
                    "venue2": venue2,
                    "n_common_bins": len(common_bins),
                    "best_correlation": best_corr["correlation"],
                    "best_lag": best_corr["lag"],
                    "leader": leader,
                    "all_correlations": lag_correlations,
                }
            )

            logger.info(
                f"{venue1} vs {venue2}: best lag={best_corr['lag']}, corr={best_corr['correlation']:.3f}, leader={leader}"
            )

    return {"status": "success", "correlation_results": correlation_results}


def compute_volatility_clustering(aligned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute volatility clustering across venues."""
    logger = logging.getLogger(__name__)

    if len(aligned_data) < 2:
        return {
            "status": "insufficient_venues",
            "message": "Need at least 2 venues for volatility clustering analysis",
        }

    venues = list(aligned_data.keys())
    volatility_results = []

    # Pairwise analysis
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            df1 = aligned_data[venue1]
            df2 = aligned_data[venue2]

            if df1.empty or df2.empty:
                continue

            # Find common time bins
            common_bins = pd.merge(df1, df2, on="bin", suffixes=("_1", "_2"))

            if len(common_bins) < 20:  # Need minimum data points
                continue

            # Compute rolling volatility (30s and 60s windows)
            common_bins["return_1"] = common_bins["price_1"].pct_change()
            common_bins["return_2"] = common_bins["price_2"].pct_change()

            # Remove NaN values
            returns_data = common_bins[["return_1", "return_2"]].dropna()

            if len(returns_data) < 10:
                continue

            # Compute rolling volatility
            window_30s = min(30, len(returns_data) // 3)
            window_60s = min(60, len(returns_data) // 2)

            vol_1_30s = returns_data["return_1"].rolling(window=window_30s).std()
            vol_2_30s = returns_data["return_2"].rolling(window=window_30s).std()
            vol_1_60s = returns_data["return_1"].rolling(window=window_60s).std()
            vol_2_60s = returns_data["return_2"].rolling(window=window_60s).std()

            # Compute volatility correlations
            vol_corr_30s = vol_1_30s.corr(vol_2_30s)
            vol_corr_60s = vol_1_60s.corr(vol_2_60s)

            volatility_results.append(
                {
                    "venue_pair": f"{venue1}_vs_{venue2}",
                    "venue1": venue1,
                    "venue2": venue2,
                    "n_common_bins": len(common_bins),
                    "volatility_correlation_30s": (
                        float(vol_corr_30s) if not np.isnan(vol_corr_30s) else None
                    ),
                    "volatility_correlation_60s": (
                        float(vol_corr_60s) if not np.isnan(vol_corr_60s) else None
                    ),
                    "window_30s": window_30s,
                    "window_60s": window_60s,
                }
            )

            logger.info(
                f"{venue1} vs {venue2}: vol_corr_30s={vol_corr_30s:.3f}, vol_corr_60s={vol_corr_60s:.3f}"
            )

    return {"status": "success", "volatility_results": volatility_results}


def compute_spread_synchronization(aligned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute spread synchronization across venues."""
    logger = logging.getLogger(__name__)

    if len(aligned_data) < 2:
        return {
            "status": "insufficient_venues",
            "message": "Need at least 2 venues for spread synchronization analysis",
        }

    venues = list(aligned_data.keys())
    spread_results = []

    # Pairwise analysis
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            df1 = aligned_data[venue1]
            df2 = aligned_data[venue2]

            if df1.empty or df2.empty:
                continue

            # Find common time bins
            common_bins = pd.merge(df1, df2, on="bin", suffixes=("_1", "_2"))

            if len(common_bins) < 10:
                continue

            # Compute price spreads
            common_bins["price_spread_abs"] = abs(common_bins["price_1"] - common_bins["price_2"])
            common_bins["price_spread_pct"] = (
                common_bins["price_spread_abs"] / common_bins["price_1"]
            ) * 100

            # Compute synchronization rates
            epsilon_abs = 5.0  # $5 threshold
            epsilon_pct = 0.05  # 0.05% threshold

            sync_abs = (common_bins["price_spread_abs"] <= epsilon_abs).mean()
            sync_pct = (common_bins["price_spread_pct"] <= epsilon_pct).mean()

            spread_results.append(
                {
                    "venue_pair": f"{venue1}_vs_{venue2}",
                    "venue1": venue1,
                    "venue2": venue2,
                    "n_common_bins": len(common_bins),
                    "mean_spread_abs": float(common_bins["price_spread_abs"].mean()),
                    "mean_spread_pct": float(common_bins["price_spread_pct"].mean()),
                    "sync_rate_abs": float(sync_abs),
                    "sync_rate_pct": float(sync_pct),
                    "epsilon_abs": epsilon_abs,
                    "epsilon_pct": epsilon_pct,
                }
            )

            logger.info(f"{venue1} vs {venue2}: sync_abs={sync_abs:.1%}, sync_pct={sync_pct:.1%}")

    return {"status": "success", "spread_results": spread_results}


def generate_markdown_report(signal_results: Dict[str, Any]) -> str:
    """Generate markdown report for signal analysis."""

    report = f"""# ACD Phase SIG - Pre-ACD Signals Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Signal Analysis Summary

**Status**: {signal_results.get('status', 'unknown')}
**Venues Analyzed**: {len(signal_results.get('venues_analyzed', []))}
**Analysis Type**: Exploratory (single venue - limited scope)

"""

    # Return correlations
    if "return_correlations" in signal_results:
        corr_data = signal_results["return_correlations"]
        if corr_data.get("status") == "success":
            report += "## Return Correlations\n\n"
            report += "| Venue Pair | Best Correlation | Best Lag | Leader | Common Bins |\n"
            report += "|------------|------------------|----------|--------|------------|\n"

            for result in corr_data.get("correlation_results", []):
                report += f"| {result['venue_pair'].upper()} | {result['best_correlation']:.3f} | {result['best_lag']} | {result['leader']} | {result['n_common_bins']} |\n"

            report += "\n"
        else:
            report += f"## Return Correlations\n\n**Status**: {corr_data.get('message', 'Unknown error')}\n\n"

    # Volatility clustering
    if "volatility_clustering" in signal_results:
        vol_data = signal_results["volatility_clustering"]
        if vol_data.get("status") == "success":
            report += "## Volatility Clustering\n\n"
            report += "| Venue Pair | Vol Corr (30s) | Vol Corr (60s) | Common Bins |\n"
            report += "|------------|----------------|----------------|------------|\n"

            for result in vol_data.get("volatility_results", []):
                corr_30s = result.get("volatility_correlation_30s", "N/A")
                corr_60s = result.get("volatility_correlation_60s", "N/A")
                report += f"| {result['venue_pair'].upper()} | {corr_30s:.3f if corr_30s is not None else 'N/A'} | {corr_60s:.3f if corr_60s is not None else 'N/A'} | {result['n_common_bins']} |\n"

            report += "\n"
        else:
            report += f"## Volatility Clustering\n\n**Status**: {vol_data.get('message', 'Unknown error')}\n\n"

    # Spread synchronization
    if "spread_synchronization" in signal_results:
        spread_data = signal_results["spread_synchronization"]
        if spread_data.get("status") == "success":
            report += "## Spread Synchronization\n\n"
            report += "| Venue Pair | Mean Spread ($) | Mean Spread (%) | Sync Rate ($5) | Sync Rate (0.05%) |\n"
            report += "|------------|----------------|-----------------|----------------|-------------------|\n"

            for result in spread_data.get("spread_results", []):
                report += f"| {result['venue_pair'].upper()} | ${result['mean_spread_abs']:.2f} | {result['mean_spread_pct']:.2f}% | {result['sync_rate_abs']:.1%} | {result['sync_rate_pct']:.1%} |\n"

            report += "\n"
        else:
            report += f"## Spread Synchronization\n\n**Status**: {spread_data.get('message', 'Unknown error')}\n\n"

    # Limitations
    report += "## Limitations\n\n"
    report += (
        "- **Single Venue**: Only Kraken data available - insufficient for cross-venue analysis\n"
    )
    report += "- **Exploratory Only**: Results are exploratory and not statistically reliable\n"
    report += "- **Limited Scope**: Need additional venues for meaningful ACD analysis\n"
    report += "- **Backfill Required**: Consider backfilling additional venues for comprehensive analysis\n\n"

    # Recommendations
    report += "## Recommendations\n\n"
    report += "1. **Backfill Additional Venues**: Obtain data from Binance, Coinbase, OKX\n"
    report += "2. **Extend Time Window**: Target 1+ hour windows for robust analysis\n"
    report += "3. **Validate Data Quality**: Ensure all venues pass provenance validation\n"
    report += "4. **Cross-Venue Analysis**: Focus on venues with overlapping time windows\n\n"

    return report


def main():
    """Main Phase SIG function."""
    parser = argparse.ArgumentParser(description="ACD Phase SIG - Pre-ACD Signals")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE SIG - PRE-ACD SIGNALS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")
    print(f"⚠️  EXPLORATORY ANALYSIS - Single venue only")

    # Load clean data
    print(f"\n🔍 Loading clean data...")

    # Try to load from clean results
    clean_results_key = f"analysis/{args.date}/ACD/_cln/clean_results.json"
    clean_results_content = get_s3_object_text(s3_client, args.bucket, clean_results_key)

    if clean_results_content:
        clean_results = json.loads(clean_results_content)
        venues = clean_results.get("clean_results", {}).keys()
    else:
        # Fallback to trying common venues
        venues = ["kraken"]

    venues_data = {}
    for venue in venues:
        print(f"\n📊 Loading {venue.upper()}...")

        df = load_clean_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No clean data found for {venue}")
            continue

        venues_data[venue] = df
        print(f"   ✅ Loaded {len(df)} rows")

    if not venues_data:
        print(f"❌ No clean data found for any venue")
        sys.exit(1)

    print(f"✅ Loaded {len(venues_data)} venues with clean data")

    # Create aligned bins
    print(f"\n🔍 Creating aligned bins...")

    aligned_data = create_aligned_bins(venues_data, bin_size_seconds=1)

    print(f"✅ Created aligned bins for {len(aligned_data)} venues")

    # Compute return correlations
    print(f"\n📊 Computing return correlations...")

    return_correlations = compute_return_correlations(aligned_data)

    print(f"✅ Return correlations computed")

    # Compute volatility clustering
    print(f"\n📊 Computing volatility clustering...")

    volatility_clustering = compute_volatility_clustering(aligned_data)

    print(f"✅ Volatility clustering computed")

    # Compute spread synchronization
    print(f"\n📊 Computing spread synchronization...")

    spread_synchronization = compute_spread_synchronization(aligned_data)

    print(f"✅ Spread synchronization computed")

    # Generate markdown report
    print(f"\n📝 Generating markdown report...")

    signal_results = {
        "date": args.date,
        "venues_analyzed": list(venues_data.keys()),
        "return_correlations": return_correlations,
        "volatility_clustering": volatility_clustering,
        "spread_synchronization": spread_synchronization,
        "limitations": {
            "single_venue": len(venues_data) == 1,
            "exploratory_only": True,
            "insufficient_for_acd": len(venues_data) < 2,
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    markdown_report = generate_markdown_report(signal_results)

    # Save results
    print(f"\n💾 Saving results...")

    # Save JSON results
    results_key = f"analysis/{args.date}/ACD/_sig/signals.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(signal_results, indent=2),
        ContentType="application/json",
    )

    # Save markdown report
    report_key = f"analysis/{args.date}/ACD/_sig/signals.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=report_key,
        Body=markdown_report.encode("utf-8"),
        ContentType="text/markdown",
    )

    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")
    print(f"💾 Saved report: s3://{args.bucket}/{report_key}")

    # Final summary
    print(f"\n📊 PHASE SIG SUMMARY")
    print("=" * 60)
    print(f"Venues analyzed: {len(venues_data)}")
    print(f"Analysis type: Exploratory only")
    print(f"Limitations: Single venue - insufficient for ACD")

    if return_correlations.get("status") == "insufficient_venues":
        print(f"\n⚠️  RETURN CORRELATIONS: {return_correlations['message']}")

    if volatility_clustering.get("status") == "insufficient_venues":
        print(f"⚠️  VOLATILITY CLUSTERING: {volatility_clustering['message']}")

    if spread_synchronization.get("status") == "insufficient_venues":
        print(f"⚠️  SPREAD SYNCHRONIZATION: {spread_synchronization['message']}")

    print(f"\n✅ PHASE SIG COMPLETE - Exploratory analysis finished")
    print(f"   Consider backfilling additional venues for comprehensive ACD analysis")


if __name__ == "__main__":
    main()
