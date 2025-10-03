#!/usr/bin/env python3
"""
ACD Cross-Venue Analysis

Analyzes cross-venue coordination and competition signals using aligned data
from Binance (conditionally accepted), Coinbase, and Kraken.
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
from scipy.stats import pearsonr


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_cross_venue_analysis.log"),
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


def align_time_bands(
    binance_df: pd.DataFrame,
    coinbase_df: pd.DataFrame,
    kraken_df: pd.DataFrame,
    bin_size_minutes: int = 1,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Align time bands across venues."""
    logger = logging.getLogger(__name__)

    # Convert timestamps and ensure timezone consistency
    binance_df["timestamp_dt"] = pd.to_datetime(binance_df["timestamp"], unit="ms", utc=True)
    coinbase_df["timestamp_dt"] = pd.to_datetime(coinbase_df["timestamp"], unit="ms", utc=True)
    kraken_df["timestamp_dt"] = pd.to_datetime(kraken_df["timestamp"], unit="ms", utc=True)

    # Find common time range
    all_times = pd.concat(
        [binance_df["timestamp_dt"], coinbase_df["timestamp_dt"], kraken_df["timestamp_dt"]]
    )

    common_start = all_times.min()
    common_end = all_times.max()
    common_duration = (common_end - common_start).total_seconds()

    logger.info(f"Common time range: {common_start} to {common_end} ({common_duration:.1f}s)")

    # Create time bins
    bin_size = timedelta(minutes=bin_size_minutes)
    time_bins = pd.date_range(start=common_start, end=common_end, freq=bin_size)

    # Bin data for each venue
    def bin_venue_data(df, venue_name):
        df_binned = df.copy()
        df_binned["time_bin"] = pd.cut(
            df_binned["timestamp_dt"], bins=time_bins, labels=time_bins[:-1]
        )

        # Aggregate within each bin
        binned_stats = (
            df_binned.groupby("time_bin")
            .agg({"price": ["mean", "std", "min", "max", "count"], "volume": ["sum", "mean"]})
            .reset_index()
        )

        # Flatten column names
        binned_stats.columns = [
            "time_bin",
            "price_mean",
            "price_std",
            "price_min",
            "price_max",
            "trade_count",
            "volume_total",
            "volume_avg",
        ]

        binned_stats["venue"] = venue_name
        binned_stats = binned_stats.dropna()

        logger.info(f"{venue_name} binned into {len(binned_stats)} time bins")
        return binned_stats

    binance_binned = bin_venue_data(binance_df, "binance")
    coinbase_binned = bin_venue_data(coinbase_df, "coinbase")
    kraken_binned = bin_venue_data(kraken_df, "kraken")

    # Find overlapping bins
    all_bins = set(binance_binned["time_bin"]).intersection(
        set(coinbase_binned["time_bin"]).intersection(set(kraken_binned["time_bin"]))
    )

    # If no overlap, try to find any two-venue overlap
    if len(all_bins) == 0:
        logger.warning("No three-venue overlap found, trying two-venue overlap")

        # Try Binance-Coinbase overlap
        bc_bins = set(binance_binned["time_bin"]).intersection(set(coinbase_binned["time_bin"]))
        if len(bc_bins) > 0:
            logger.info(f"Found Binance-Coinbase overlap: {len(bc_bins)} bins")
            all_bins = bc_bins
            # Create dummy Kraken data for the overlapping bins
            kraken_aligned = pd.DataFrame()
        else:
            # Try Binance-Kraken overlap
            bk_bins = set(binance_binned["time_bin"]).intersection(set(kraken_binned["time_bin"]))
            if len(bk_bins) > 0:
                logger.info(f"Found Binance-Kraken overlap: {len(bk_bins)} bins")
                all_bins = bk_bins
                # Create dummy Coinbase data for the overlapping bins
                coinbase_aligned = pd.DataFrame()
            else:
                # Try Coinbase-Kraken overlap
                ck_bins = set(coinbase_binned["time_bin"]).intersection(
                    set(kraken_binned["time_bin"])
                )
                if len(ck_bins) > 0:
                    logger.info(f"Found Coinbase-Kraken overlap: {len(ck_bins)} bins")
                    all_bins = ck_bins
                    # Create dummy Binance data for the overlapping bins
                    binance_aligned = pd.DataFrame()
                else:
                    logger.warning("No two-venue overlap found either")

    # Filter to overlapping bins only
    if len(all_bins) > 0:
        binance_aligned = binance_binned[binance_binned["time_bin"].isin(all_bins)].copy()
        if not coinbase_aligned.empty:
            coinbase_aligned = coinbase_binned[coinbase_binned["time_bin"].isin(all_bins)].copy()
        if not kraken_aligned.empty:
            kraken_aligned = kraken_binned[kraken_binned["time_bin"].isin(all_bins)].copy()
    else:
        binance_aligned = pd.DataFrame()
        coinbase_aligned = pd.DataFrame()
        kraken_aligned = pd.DataFrame()

    alignment_info = {
        "common_start": common_start.isoformat(),
        "common_end": common_end.isoformat(),
        "common_duration_seconds": common_duration,
        "bin_size_minutes": bin_size_minutes,
        "total_bins": len(time_bins) - 1,
        "overlapping_bins": len(all_bins),
        "overlap_percentage": (
            len(all_bins) / (len(time_bins) - 1) * 100 if len(time_bins) > 1 else 0
        ),
        "venues_aligned": len(all_bins) > 0,
    }

    logger.info(
        f"Time alignment: {len(all_bins)} overlapping bins out of {len(time_bins)-1} total bins"
    )

    return binance_aligned, coinbase_aligned, kraken_aligned, alignment_info


def compute_cross_venue_stats(
    binance_aligned: pd.DataFrame, coinbase_aligned: pd.DataFrame, kraken_aligned: pd.DataFrame
) -> Dict[str, Any]:
    """Compute cross-venue summary statistics."""
    logger = logging.getLogger(__name__)

    # Merge aligned data
    merged_data = pd.concat([binance_aligned, coinbase_aligned, kraken_aligned])

    # Per-venue statistics
    venue_stats = {}
    for venue in ["binance", "coinbase", "kraken"]:
        venue_data = merged_data[merged_data["venue"] == venue]
        if len(venue_data) > 0:
            venue_stats[venue] = {
                "bins": len(venue_data),
                "price_mean": float(venue_data["price_mean"].mean()),
                "price_std": float(venue_data["price_std"].mean()),
                "price_min": float(venue_data["price_min"].min()),
                "price_max": float(venue_data["price_max"].max()),
                "volume_total": float(venue_data["volume_total"].sum()),
                "trade_count": int(venue_data["trade_count"].sum()),
                "volatility": float(venue_data["price_std"].mean()),
            }
        else:
            venue_stats[venue] = {
                "bins": 0,
                "price_mean": None,
                "price_std": None,
                "price_min": None,
                "price_max": None,
                "volume_total": None,
                "trade_count": 0,
                "volatility": None,
            }

    # Cross-venue spreads
    spreads = {}
    if venue_stats["binance"]["price_mean"] and venue_stats["coinbase"]["price_mean"]:
        spreads["binance_coinbase"] = (
            abs(venue_stats["binance"]["price_mean"] - venue_stats["coinbase"]["price_mean"])
            / venue_stats["coinbase"]["price_mean"]
            * 100
        )
    if venue_stats["binance"]["price_mean"] and venue_stats["kraken"]["price_mean"]:
        spreads["binance_kraken"] = (
            abs(venue_stats["binance"]["price_mean"] - venue_stats["kraken"]["price_mean"])
            / venue_stats["kraken"]["price_mean"]
            * 100
        )
    if venue_stats["coinbase"]["price_mean"] and venue_stats["kraken"]["price_mean"]:
        spreads["coinbase_kraken"] = (
            abs(venue_stats["coinbase"]["price_mean"] - venue_stats["kraken"]["price_mean"])
            / venue_stats["kraken"]["price_mean"]
            * 100
        )

    # Volatility ratios
    volatility_ratios = {}
    if venue_stats["binance"]["volatility"] and venue_stats["coinbase"]["volatility"]:
        volatility_ratios["binance_coinbase"] = (
            venue_stats["binance"]["volatility"] / venue_stats["coinbase"]["volatility"]
        )
    if venue_stats["binance"]["volatility"] and venue_stats["kraken"]["volatility"]:
        volatility_ratios["binance_kraken"] = (
            venue_stats["binance"]["volatility"] / venue_stats["kraken"]["volatility"]
        )
    if venue_stats["coinbase"]["volatility"] and venue_stats["kraken"]["volatility"]:
        volatility_ratios["coinbase_kraken"] = (
            venue_stats["coinbase"]["volatility"] / venue_stats["kraken"]["volatility"]
        )

    cross_venue_stats = {
        "venue_stats": venue_stats,
        "spreads": spreads,
        "volatility_ratios": volatility_ratios,
        "total_aligned_bins": len(merged_data["time_bin"].unique()),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        f"Cross-venue stats computed for {len(merged_data['time_bin'].unique())} aligned bins"
    )

    return cross_venue_stats


def compute_leader_follower_metrics(
    binance_aligned: pd.DataFrame, coinbase_aligned: pd.DataFrame, kraken_aligned: pd.DataFrame
) -> Dict[str, Any]:
    """Compute leader-follower metrics between venues."""
    logger = logging.getLogger(__name__)

    # Merge data by time bin
    merged_data = pd.merge(
        binance_aligned[["time_bin", "price_mean"]].rename(columns={"price_mean": "binance_price"}),
        coinbase_aligned[["time_bin", "price_mean"]].rename(
            columns={"price_mean": "coinbase_price"}
        ),
        on="time_bin",
        how="inner",
    )
    merged_data = pd.merge(
        merged_data,
        kraken_aligned[["time_bin", "price_mean"]].rename(columns={"price_mean": "kraken_price"}),
        on="time_bin",
        how="inner",
    )

    if len(merged_data) < 3:
        logger.warning("Insufficient data for leader-follower analysis")
        return {"insufficient_data": True, "reason": "Less than 3 aligned time bins"}

    # Compute price changes
    merged_data["binance_change"] = merged_data["binance_price"].pct_change()
    merged_data["coinbase_change"] = merged_data["coinbase_price"].pct_change()
    merged_data["kraken_change"] = merged_data["kraken_price"].pct_change()

    # Remove NaN values
    merged_data = merged_data.dropna()

    if len(merged_data) < 2:
        logger.warning("Insufficient data after removing NaN values")
        return {"insufficient_data": True, "reason": "Less than 2 valid price changes"}

    # Lag correlations (1-bin lag)
    correlations = {}
    lags = [0, 1]  # Current and 1-bin lag

    for lag in lags:
        if lag == 0:
            # Current correlations
            try:
                corr_bc, p_bc = pearsonr(
                    merged_data["binance_change"], merged_data["coinbase_change"]
                )
                corr_bk, p_bk = pearsonr(
                    merged_data["binance_change"], merged_data["kraken_change"]
                )
                corr_ck, p_ck = pearsonr(
                    merged_data["coinbase_change"], merged_data["kraken_change"]
                )

                correlations[f"lag_{lag}"] = {
                    "binance_coinbase": {"correlation": corr_bc, "p_value": p_bc},
                    "binance_kraken": {"correlation": corr_bk, "p_value": p_bk},
                    "coinbase_kraken": {"correlation": corr_ck, "p_value": p_ck},
                }
            except Exception as e:
                logger.warning(f"Error computing correlations for lag {lag}: {e}")
                correlations[f"lag_{lag}"] = None
        else:
            # Lagged correlations
            try:
                if len(merged_data) > lag:
                    corr_bc, p_bc = pearsonr(
                        merged_data["binance_change"].iloc[lag:],
                        merged_data["coinbase_change"].iloc[:-lag],
                    )
                    corr_bk, p_bk = pearsonr(
                        merged_data["binance_change"].iloc[lag:],
                        merged_data["kraken_change"].iloc[:-lag],
                    )
                    corr_ck, p_ck = pearsonr(
                        merged_data["coinbase_change"].iloc[lag:],
                        merged_data["kraken_change"].iloc[:-lag],
                    )

                    correlations[f"lag_{lag}"] = {
                        "binance_coinbase": {"correlation": corr_bc, "p_value": p_bc},
                        "binance_kraken": {"correlation": corr_bk, "p_value": p_bk},
                        "coinbase_kraken": {"correlation": corr_ck, "p_value": p_ck},
                    }
                else:
                    correlations[f"lag_{lag}"] = None
            except Exception as e:
                logger.warning(f"Error computing lagged correlations for lag {lag}: {e}")
                correlations[f"lag_{lag}"] = None

    # Rotation scores (which venue leads)
    rotation_scores = {}
    if correlations.get("lag_0") and correlations.get("lag_1"):
        lag_0 = correlations["lag_0"]
        lag_1 = correlations["lag_1"]

        # Binance leads if lag-1 correlation is higher than lag-0
        if lag_0 and lag_1:
            for pair in ["binance_coinbase", "binance_kraken", "coinbase_kraken"]:
                if pair in lag_0 and pair in lag_1:
                    lag_0_corr = lag_0[pair]["correlation"]
                    lag_1_corr = lag_1[pair]["correlation"]
                    rotation_scores[pair] = {
                        "lag_0_correlation": lag_0_corr,
                        "lag_1_correlation": lag_1_corr,
                        "rotation_score": lag_1_corr - lag_0_corr,
                        "leader": "first_venue" if lag_1_corr > lag_0_corr else "second_venue",
                    }

    leader_follower_metrics = {
        "correlations": correlations,
        "rotation_scores": rotation_scores,
        "data_points": len(merged_data),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Leader-follower metrics computed for {len(merged_data)} data points")

    return leader_follower_metrics


def generate_acd_indicators(
    cross_venue_stats: Dict[str, Any], leader_follower_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate preliminary ACD indicators."""
    logger = logging.getLogger(__name__)

    indicators = {
        "coordination_signals": {},
        "competition_signals": {},
        "market_structure": {},
        "risk_indicators": {},
    }

    # Coordination signals
    if leader_follower_metrics.get("correlations"):
        lag_0_corrs = leader_follower_metrics["correlations"].get("lag_0", {})
        if lag_0_corrs:
            avg_correlation = np.mean(
                [
                    lag_0_corrs.get("binance_coinbase", {}).get("correlation", 0),
                    lag_0_corrs.get("binance_kraken", {}).get("correlation", 0),
                    lag_0_corrs.get("coinbase_kraken", {}).get("correlation", 0),
                ]
            )

            indicators["coordination_signals"] = {
                "average_correlation": float(avg_correlation),
                "high_coordination": avg_correlation > 0.7,
                "moderate_coordination": 0.3 < avg_correlation <= 0.7,
                "low_coordination": avg_correlation <= 0.3,
            }

    # Competition signals
    if cross_venue_stats.get("spreads"):
        spreads = cross_venue_stats["spreads"]
        max_spread = max(spreads.values()) if spreads else 0

        indicators["competition_signals"] = {
            "max_spread": float(max_spread),
            "high_competition": max_spread > 2.0,
            "moderate_competition": 1.0 < max_spread <= 2.0,
            "low_competition": max_spread <= 1.0,
        }

    # Market structure
    if cross_venue_stats.get("venue_stats"):
        venue_stats = cross_venue_stats["venue_stats"]
        binance_vol = venue_stats.get("binance", {}).get("volatility", 0)
        coinbase_vol = venue_stats.get("coinbase", {}).get("volatility", 0)
        kraken_vol = venue_stats.get("kraken", {}).get("volatility", 0)

        if binance_vol and coinbase_vol and kraken_vol:
            vol_ratio = binance_vol / ((coinbase_vol + kraken_vol) / 2)
            indicators["market_structure"] = {
                "binance_volatility_ratio": float(vol_ratio),
                "binance_dominant": vol_ratio > 1.5,
                "balanced_market": 0.5 <= vol_ratio <= 1.5,
                "binance_subordinate": vol_ratio < 0.5,
            }

    # Risk indicators
    if cross_venue_stats.get("spreads"):
        spreads = cross_venue_stats["spreads"]
        high_spread_pairs = [pair for pair, spread in spreads.items() if spread > 1.5]

        indicators["risk_indicators"] = {
            "high_spread_pairs": high_spread_pairs,
            "spread_risk": len(high_spread_pairs) > 0,
            "market_fragmentation": len(high_spread_pairs) > 1,
        }

    logger.info("ACD indicators generated")

    return indicators


def main():
    """Main cross-venue analysis function."""
    parser = argparse.ArgumentParser(description="ACD Cross-Venue Analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")
    parser.add_argument("--bin-size", type=int, default=1, help="Time bin size in minutes")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD CROSS-VENUE ANALYSIS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")
    print(f"⏰ Bin size: {args.bin_size} minutes")

    # Load venue data
    print(f"\n🔄 Loading venue data...")
    try:
        # Use backfilled Binance data for slice_01
        binance_df = load_venue_data(
            s3_client, args.bucket, args.date, "binance", "slice_01", use_backfill=True
        )
        coinbase_df = load_venue_data(s3_client, args.bucket, args.date, "coinbase", "slice_01")
        kraken_df = load_venue_data(s3_client, args.bucket, args.date, "kraken", "slice_01")

        print(
            f"✅ Loaded data: Binance ({len(binance_df)} rows), Coinbase ({len(coinbase_df)} rows), Kraken ({len(kraken_df)} rows)"
        )
    except Exception as e:
        print(f"❌ Error loading venue data: {e}")
        sys.exit(1)

    # Time-band alignment
    print(f"\n🔍 Aligning time bands...")
    try:
        binance_aligned, coinbase_aligned, kraken_aligned, alignment_info = align_time_bands(
            binance_df, coinbase_df, kraken_df, args.bin_size
        )

        print(
            f"⏰ Time alignment: {alignment_info['overlapping_bins']} overlapping bins out of {alignment_info['total_bins']} total"
        )
        print(f"📊 Overlap percentage: {alignment_info['overlap_percentage']:.1f}%")

        if not alignment_info["venues_aligned"]:
            print("❌ No overlapping time bands found")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error aligning time bands: {e}")
        sys.exit(1)

    # Cross-venue statistics
    print(f"\n📊 Computing cross-venue statistics...")
    try:
        cross_venue_stats = compute_cross_venue_stats(
            binance_aligned, coinbase_aligned, kraken_aligned
        )

        print(f"📈 Cross-venue spreads:")
        for pair, spread in cross_venue_stats["spreads"].items():
            print(f"   {pair}: {spread:.2f}%")

    except Exception as e:
        print(f"❌ Error computing cross-venue stats: {e}")
        sys.exit(1)

    # Leader-follower metrics
    print(f"\n🔍 Computing leader-follower metrics...")
    try:
        leader_follower_metrics = compute_leader_follower_metrics(
            binance_aligned, coinbase_aligned, kraken_aligned
        )

        if leader_follower_metrics.get("insufficient_data"):
            print(
                f"⚠️ Insufficient data for leader-follower analysis: {leader_follower_metrics['reason']}"
            )
        else:
            print(
                f"📊 Leader-follower analysis completed for {leader_follower_metrics['data_points']} data points"
            )

    except Exception as e:
        print(f"❌ Error computing leader-follower metrics: {e}")
        sys.exit(1)

    # ACD indicators
    print(f"\n🎯 Generating ACD indicators...")
    try:
        acd_indicators = generate_acd_indicators(cross_venue_stats, leader_follower_metrics)

        print(f"📊 ACD indicators generated")

    except Exception as e:
        print(f"❌ Error generating ACD indicators: {e}")
        sys.exit(1)

    # Save results
    print(f"\n💾 Saving results...")

    results_data = {
        "date": args.date,
        "bin_size_minutes": args.bin_size,
        "alignment_info": alignment_info,
        "cross_venue_stats": cross_venue_stats,
        "leader_follower_metrics": leader_follower_metrics,
        "acd_indicators": acd_indicators,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"analysis/{args.date}/_diag/acd_cross_venue_analysis.json"
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
    print(f"Bin size: {args.bin_size} minutes")
    print(f"Aligned bins: {alignment_info['overlapping_bins']}")
    print(f"Overlap: {alignment_info['overlap_percentage']:.1f}%")

    # Decision table
    print(f"\n📋 DECISION TABLE")
    print("=" * 60)
    print(f"| Venue | Bins | Price Mean | Volatility | Status |")
    print(f"|-------|------|------------|------------|--------|")

    for venue in ["binance", "coinbase", "kraken"]:
        stats = cross_venue_stats["venue_stats"][venue]
        status = "✅ Usable" if stats["bins"] > 0 else "❌ Unusable"
        print(
            f"| {venue.capitalize()} | {stats['bins']} | ${stats['price_mean']:.2f} | {stats['volatility']:.2f} | {status} |"
        )

    # ACD indicators summary
    if acd_indicators.get("coordination_signals"):
        coord = acd_indicators["coordination_signals"]
        print(f"\n🎯 COORDINATION SIGNALS")
        print(f"   Average correlation: {coord['average_correlation']:.3f}")
        print(
            f"   Level: {'High' if coord['high_coordination'] else 'Moderate' if coord['moderate_coordination'] else 'Low'}"
        )

    if acd_indicators.get("competition_signals"):
        comp = acd_indicators["competition_signals"]
        print(f"\n🏆 COMPETITION SIGNALS")
        print(f"   Max spread: {comp['max_spread']:.2f}%")
        print(
            f"   Level: {'High' if comp['high_competition'] else 'Moderate' if comp['moderate_competition'] else 'Low'}"
        )

    print(f"\n📁 Generated artifacts:")
    print(f"  Analysis results: s3://{args.bucket}/{results_key}")


if __name__ == "__main__":
    main()
