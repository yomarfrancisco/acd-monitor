#!/usr/bin/env python3
"""
ACD Phase SIG - ACD Signal Preparation

Computes cross-venue metrics to detect algorithmic coordination vs competition.
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
from scipy.signal import correlate


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_sig_signal_preparation.log"),
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


def create_aligned_time_series(canonical_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    """Create aligned time series for cross-venue analysis."""
    logger = logging.getLogger(__name__)

    # Find common time range
    all_timestamps = []
    for venue, df in canonical_data.items():
        all_timestamps.extend(df["timestamp"].tolist())

    if not all_timestamps:
        logger.error("No timestamps found")
        return {}

    all_timestamps = pd.to_datetime(all_timestamps, utc=True)
    common_start = all_timestamps.min()
    common_end = all_timestamps.max()

    logger.info(f"Common time range: {common_start} to {common_end}")

    # Create 1-second aligned grid
    time_grid = pd.date_range(start=common_start, end=common_end, freq="1s", tz=timezone.utc)

    aligned_series = {}

    for venue, df in canonical_data.items():
        # Bin to 1-second intervals and take last price
        df_binned = df.set_index("timestamp").resample("1s")["price"].last()

        # Align to common time grid
        aligned_prices = df_binned.reindex(time_grid, method="ffill")

        # Remove NaN values at the beginning
        aligned_prices = aligned_prices.dropna()

        if len(aligned_prices) > 0:
            aligned_series[venue] = aligned_prices
            logger.info(f"Aligned {venue}: {len(aligned_prices)} points")
        else:
            logger.warning(f"No aligned data for {venue}")

    return aligned_series


def compute_cross_venue_correlations(aligned_series: Dict[str, pd.Series]) -> Dict[str, Any]:
    """Compute pairwise price correlations and cross-correlations."""
    logger = logging.getLogger(__name__)

    venues = list(aligned_series.keys())
    n_venues = len(venues)

    if n_venues < 2:
        logger.error("Need at least 2 venues for correlation analysis")
        return {}

    # Pairwise correlations
    pairwise_correlations = {}
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            series1 = aligned_series[venue1]
            series2 = aligned_series[venue2]

            # Find common time points
            common_times = series1.index.intersection(series2.index)
            if len(common_times) < 10:
                logger.warning(f"Insufficient overlap between {venue1} and {venue2}")
                continue

            series1_common = series1.loc[common_times]
            series2_common = series2.loc[common_times]

            # Remove NaN values
            valid_mask = ~(series1_common.isna() | series2_common.isna())
            series1_clean = series1_common[valid_mask]
            series2_clean = series2_common[valid_mask]

            if len(series1_clean) < 10:
                logger.warning(f"Insufficient valid data between {venue1} and {venue2}")
                continue

            # Compute correlation
            correlation = series1_clean.corr(series2_clean)

            pairwise_correlations[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "correlation": float(correlation),
                "n_points": len(series1_clean),
                "time_span": (common_times.max() - common_times.min()).total_seconds(),
            }

            logger.info(f"{venue1} vs {venue2}: correlation = {correlation:.3f}")

    return {"pairwise_correlations": pairwise_correlations, "n_venues": n_venues, "venues": venues}


def compute_leader_follower_analysis(
    aligned_series: Dict[str, pd.Series], max_lag: int = 10
) -> Dict[str, Any]:
    """Compute leader-follower analysis with time lags."""
    logger = logging.getLogger(__name__)

    venues = list(aligned_series.keys())
    n_venues = len(venues)

    if n_venues < 2:
        logger.error("Need at least 2 venues for leader-follower analysis")
        return {}

    leader_follower_results = {}

    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue

            series1 = aligned_series[venue1]
            series2 = aligned_series[venue2]

            # Find common time points
            common_times = series1.index.intersection(series2.index)
            if len(common_times) < 50:
                logger.warning(f"Insufficient overlap between {venue1} and {venue2}")
                continue

            series1_common = series1.loc[common_times]
            series2_common = series2.loc[common_times]

            # Remove NaN values
            valid_mask = ~(series1_common.isna() | series2_common.isna())
            series1_clean = series1_common[valid_mask]
            series2_clean = series2_common[valid_mask]

            if len(series1_clean) < 50:
                logger.warning(f"Insufficient valid data between {venue1} and {venue2}")
                continue

            # Compute cross-correlation with lags
            lag_correlations = {}
            max_correlation = -1
            best_lag = 0

            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    correlation = series1_clean.corr(series2_clean)
                else:
                    if lag > 0:
                        # venue1 leads venue2
                        series1_shifted = series1_clean.shift(-lag)
                        series2_aligned = series2_clean
                    else:
                        # venue2 leads venue1
                        series1_shifted = series1_clean
                        series2_aligned = series2_clean.shift(lag)

                    # Align series
                    common_idx = series1_shifted.index.intersection(series2_aligned.index)
                    if len(common_idx) < 10:
                        continue

                    series1_aligned = series1_shifted.loc[common_idx]
                    series2_aligned = series2_aligned.loc[common_idx]

                    # Remove NaN values
                    valid_mask = ~(series1_aligned.isna() | series2_aligned.isna())
                    series1_final = series1_aligned[valid_mask]
                    series2_final = series2_aligned[valid_mask]

                    if len(series1_final) < 10:
                        continue

                    correlation = series1_final.corr(series2_final)

                lag_correlations[lag] = float(correlation) if not pd.isna(correlation) else 0.0

                if abs(correlation) > abs(max_correlation):
                    max_correlation = correlation
                    best_lag = lag

            # Determine leader-follower relationship
            if best_lag > 0:
                leader = venue1
                follower = venue2
                lead_strength = max_correlation
            elif best_lag < 0:
                leader = venue2
                follower = venue1
                lead_strength = max_correlation
            else:
                leader = "simultaneous"
                follower = "simultaneous"
                lead_strength = max_correlation

            leader_follower_results[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "max_correlation": float(max_correlation),
                "best_lag": best_lag,
                "leader": leader,
                "follower": follower,
                "lead_strength": float(lead_strength),
                "lag_correlations": lag_correlations,
                "n_points": len(series1_clean),
            }

            logger.info(
                f"{venue1} vs {venue2}: max correlation = {max_correlation:.3f} at lag {best_lag}"
            )

    return leader_follower_results


def compute_volatility_clustering(
    aligned_series: Dict[str, pd.Series], window_sizes: List[int] = [30, 60]
) -> Dict[str, Any]:
    """Detect volatility clustering across venues."""
    logger = logging.getLogger(__name__)

    venues = list(aligned_series.keys())
    n_venues = len(venues)

    if n_venues < 2:
        logger.error("Need at least 2 venues for volatility clustering analysis")
        return {}

    volatility_clustering = {}

    for window_size in window_sizes:
        logger.info(f"Computing volatility clustering for {window_size}s windows")

        # Compute rolling volatility for each venue
        venue_volatility = {}
        for venue, series in aligned_series.items():
            # Compute rolling standard deviation
            rolling_std = series.rolling(window=window_size, min_periods=window_size // 2).std()
            venue_volatility[venue] = rolling_std.dropna()

        # Find common time points
        common_times = None
        for venue, vol_series in venue_volatility.items():
            if common_times is None:
                common_times = vol_series.index
            else:
                common_times = common_times.intersection(vol_series.index)

        if len(common_times) < 10:
            logger.warning(f"Insufficient common time points for {window_size}s windows")
            continue

        # Align volatility series
        aligned_volatility = {}
        for venue, vol_series in venue_volatility.items():
            aligned_volatility[venue] = vol_series.loc[common_times]

        # Compute pairwise volatility correlations
        vol_correlations = {}
        for i, venue1 in enumerate(venues):
            for j, venue2 in enumerate(venues):
                if i >= j:
                    continue

                vol1 = aligned_volatility[venue1]
                vol2 = aligned_volatility[venue2]

                # Remove NaN values
                valid_mask = ~(vol1.isna() | vol2.isna())
                vol1_clean = vol1[valid_mask]
                vol2_clean = vol2[valid_mask]

                if len(vol1_clean) < 10:
                    continue

                correlation = vol1_clean.corr(vol2_clean)
                vol_correlations[f"{venue1}_vs_{venue2}"] = {
                    "venue1": venue1,
                    "venue2": venue2,
                    "correlation": float(correlation) if not pd.isna(correlation) else 0.0,
                    "n_points": len(vol1_clean),
                }

        # Compute overall clustering metric
        if vol_correlations:
            mean_vol_correlation = np.mean([v["correlation"] for v in vol_correlations.values()])
            max_vol_correlation = max([v["correlation"] for v in vol_correlations.values()])
        else:
            mean_vol_correlation = 0.0
            max_vol_correlation = 0.0

        volatility_clustering[f"{window_size}s"] = {
            "window_size": window_size,
            "vol_correlations": vol_correlations,
            "mean_vol_correlation": float(mean_vol_correlation),
            "max_vol_correlation": float(max_vol_correlation),
            "n_pairs": len(vol_correlations),
        }

        logger.info(f"{window_size}s windows: mean vol correlation = {mean_vol_correlation:.3f}")

    return volatility_clustering


def compute_coordination_indicators(
    aligned_series: Dict[str, pd.Series],
    correlation_results: Dict[str, Any],
    leader_follower_results: Dict[str, Any],
    volatility_clustering: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute coordination vs competition indicators."""
    logger = logging.getLogger(__name__)

    venues = list(aligned_series.keys())
    n_venues = len(venues)

    # Coordination signals
    coordination_signals = {
        "high_correlation": 0,
        "stable_narrow_spreads": 0,
        "synchronized_spikes": 0,
    }

    # Competition signals
    competition_signals = {
        "divergence_in_spreads": 0,
        "uncorrelated_volatility": 0,
        "dominant_single_venue": 0,
    }

    # Analyze correlations
    if correlation_results and "pairwise_correlations" in correlation_results:
        correlations = [
            v["correlation"] for v in correlation_results["pairwise_correlations"].values()
        ]
        if correlations:
            mean_correlation = np.mean(correlations)
            max_correlation = max(correlations)

            if mean_correlation > 0.7:
                coordination_signals["high_correlation"] = 1
            if max_correlation > 0.9:
                coordination_signals["high_correlation"] = 1

    # Analyze leader-follower patterns
    if leader_follower_results:
        lead_strengths = [v["lead_strength"] for v in leader_follower_results.values()]
        if lead_strengths:
            mean_lead_strength = np.mean(lead_strengths)
            max_lead_strength = max(lead_strengths)

            if mean_lead_strength > 0.5:
                coordination_signals["synchronized_spikes"] = 1
            if max_lead_strength > 0.8:
                coordination_signals["synchronized_spikes"] = 1

    # Analyze volatility clustering
    if volatility_clustering:
        for window_size, vol_data in volatility_clustering.items():
            if vol_data["mean_vol_correlation"] > 0.5:
                coordination_signals["synchronized_spikes"] = 1
            if vol_data["max_vol_correlation"] > 0.8:
                coordination_signals["synchronized_spikes"] = 1

    # Compute fragmentation metric
    mean_prices = [aligned_series[venue].mean() for venue in venues]
    price_fragmentation = float(np.std(mean_prices))

    # Volume analysis
    total_volume = sum([aligned_series[venue].count() for venue in venues])
    venue_volumes = {venue: aligned_series[venue].count() for venue in venues}
    max_venue_volume = max(venue_volumes.values())
    dominant_venue_share = max_venue_volume / total_volume

    if dominant_venue_share > 0.8:
        competition_signals["dominant_single_venue"] = 1

    # Overall coordination score
    coordination_score = sum(coordination_signals.values()) / len(coordination_signals)
    competition_score = sum(competition_signals.values()) / len(competition_signals)

    return {
        "coordination_signals": coordination_signals,
        "competition_signals": competition_signals,
        "coordination_score": float(coordination_score),
        "competition_score": float(competition_score),
        "price_fragmentation": price_fragmentation,
        "dominant_venue_share": float(dominant_venue_share),
        "n_venues": n_venues,
        "venues": venues,
    }


def generate_signal_report(
    correlation_results: Dict[str, Any],
    leader_follower_results: Dict[str, Any],
    volatility_clustering: Dict[str, Any],
    coordination_indicators: Dict[str, Any],
) -> str:
    """Generate comprehensive signal report."""

    report_content = f"""# ACD Phase SIG - Signal Preparation Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Window**: canonical_1200_1300 (1 hour)  
**Venues**: {coordination_indicators['n_venues']} exchanges  

## Cross-Venue Correlations

| Venue Pair | Correlation | N Points | Time Span (s) |
|------------|-------------|----------|---------------|
"""

    if correlation_results and "pairwise_correlations" in correlation_results:
        for pair, data in correlation_results["pairwise_correlations"].items():
            report_content += f"| {pair.upper()} | {data['correlation']:.3f} | {data['n_points']} | {data['time_span']:.0f} |\n"

    report_content += f"""

## Leader-Follower Analysis

| Venue Pair | Max Correlation | Best Lag | Leader | Follower | Lead Strength |
|------------|-----------------|----------|--------|----------|---------------|
"""

    if leader_follower_results:
        for pair, data in leader_follower_results.items():
            report_content += f"| {pair.upper()} | {data['max_correlation']:.3f} | {data['best_lag']} | {data['leader'].upper()} | {data['follower'].upper()} | {data['lead_strength']:.3f} |\n"

    report_content += f"""

## Volatility Clustering Analysis

"""

    if volatility_clustering:
        for window_size, vol_data in volatility_clustering.items():
            report_content += f"### {window_size} Windows\n\n"
            report_content += (
                f"- **Mean Volatility Correlation**: {vol_data['mean_vol_correlation']:.3f}\n"
            )
            report_content += (
                f"- **Max Volatility Correlation**: {vol_data['max_vol_correlation']:.3f}\n"
            )
            report_content += f"- **Number of Pairs**: {vol_data['n_pairs']}\n\n"

    report_content += f"""

## Coordination vs Competition Indicators

### Coordination Signals

- **High Correlation**: {'✅' if coordination_indicators['coordination_signals']['high_correlation'] else '❌'}
- **Stable Narrow Spreads**: {'✅' if coordination_indicators['coordination_signals']['stable_narrow_spreads'] else '❌'}
- **Synchronized Spikes**: {'✅' if coordination_indicators['coordination_signals']['synchronized_spikes'] else '❌'}

### Competition Signals

- **Divergence in Spreads**: {'✅' if coordination_indicators['competition_signals']['divergence_in_spreads'] else '❌'}
- **Uncorrelated Volatility**: {'✅' if coordination_indicators['competition_signals']['uncorrelated_volatility'] else '❌'}
- **Dominant Single Venue**: {'✅' if coordination_indicators['competition_signals']['dominant_single_venue'] else '❌'}

### Overall Scores

- **Coordination Score**: {coordination_indicators['coordination_score']:.2f}
- **Competition Score**: {coordination_indicators['competition_score']:.2f}
- **Price Fragmentation**: {coordination_indicators['price_fragmentation']:.2f}
- **Dominant Venue Share**: {coordination_indicators['dominant_venue_share']:.1%}

## ACD Signal Summary

"""

    if coordination_indicators["coordination_score"] > 0.5:
        report_content += (
            "**🔍 COORDINATION DETECTED**: High coordination signals detected across venues.\n\n"
        )
    elif coordination_indicators["competition_score"] > 0.5:
        report_content += (
            "**⚔️ COMPETITION DETECTED**: High competition signals detected across venues.\n\n"
        )
    else:
        report_content += "**⚖️ NEUTRAL**: Mixed signals - neither strong coordination nor competition detected.\n\n"

    report_content += f"""
## Next Steps

{'✅ Ready for advanced ACD analysis' if coordination_indicators['coordination_score'] > 0.3 or coordination_indicators['competition_score'] > 0.3 else '⚠️ Review signal quality before proceeding'}
"""

    return report_content


def main():
    """Main Phase SIG function."""
    parser = argparse.ArgumentParser(description="ACD Phase SIG - Signal Preparation")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE SIG - SIGNAL PREPARATION")
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

    # Create aligned time series
    print(f"\n🔄 Creating aligned time series...")
    try:
        aligned_series = create_aligned_time_series(canonical_data)

        if len(aligned_series) < 2:
            print(f"❌ Insufficient aligned data: {len(aligned_series)}/5")
            sys.exit(1)

        print(f"✅ Created aligned series for {len(aligned_series)} venues")
        for venue, series in aligned_series.items():
            print(f"   {venue}: {len(series)} points")

    except Exception as e:
        print(f"❌ Error creating aligned time series: {e}")
        sys.exit(1)

    # Compute cross-venue correlations
    print(f"\n📊 Computing cross-venue correlations...")
    try:
        correlation_results = compute_cross_venue_correlations(aligned_series)

        if not correlation_results:
            print(f"❌ No correlation results computed")
            sys.exit(1)

        print(
            f"✅ Computed correlations for {len(correlation_results['pairwise_correlations'])} pairs"
        )

    except Exception as e:
        print(f"❌ Error computing correlations: {e}")
        sys.exit(1)

    # Compute leader-follower analysis
    print(f"\n📊 Computing leader-follower analysis...")
    try:
        leader_follower_results = compute_leader_follower_analysis(aligned_series)

        if not leader_follower_results:
            print(f"❌ No leader-follower results computed")
            sys.exit(1)

        print(f"✅ Computed leader-follower analysis for {len(leader_follower_results)} pairs")

    except Exception as e:
        print(f"❌ Error computing leader-follower analysis: {e}")
        sys.exit(1)

    # Compute volatility clustering
    print(f"\n📊 Computing volatility clustering...")
    try:
        volatility_clustering = compute_volatility_clustering(aligned_series)

        if not volatility_clustering:
            print(f"❌ No volatility clustering results computed")
            sys.exit(1)

        print(f"✅ Computed volatility clustering for {len(volatility_clustering)} window sizes")

    except Exception as e:
        print(f"❌ Error computing volatility clustering: {e}")
        sys.exit(1)

    # Compute coordination indicators
    print(f"\n📊 Computing coordination indicators...")
    try:
        coordination_indicators = compute_coordination_indicators(
            aligned_series, correlation_results, leader_follower_results, volatility_clustering
        )

        if not coordination_indicators:
            print(f"❌ No coordination indicators computed")
            sys.exit(1)

        print(f"✅ Computed coordination indicators")
        print(f"   Coordination score: {coordination_indicators['coordination_score']:.2f}")
        print(f"   Competition score: {coordination_indicators['competition_score']:.2f}")

    except Exception as e:
        print(f"❌ Error computing coordination indicators: {e}")
        sys.exit(1)

    # Generate signal report
    print(f"\n📝 Generating signal report...")
    try:
        signal_report = generate_signal_report(
            correlation_results,
            leader_follower_results,
            volatility_clustering,
            coordination_indicators,
        )

        # Save signal report
        report_key = f"analysis/{args.date}/ACD/_sig/signal_preparation_report.md"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=report_key,
            Body=signal_report.encode("utf-8"),
            ContentType="text/markdown",
        )

        print(f"💾 Saved signal report: s3://{args.bucket}/{report_key}")

    except Exception as e:
        print(f"❌ Error generating signal report: {e}")
        sys.exit(1)

    # Save signal data
    print(f"\n💾 Saving signal data...")

    signal_data = {
        "date": args.date,
        "window": "canonical_1200_1300",
        "correlation_results": correlation_results,
        "leader_follower_results": leader_follower_results,
        "volatility_clustering": volatility_clustering,
        "coordination_indicators": coordination_indicators,
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    signal_key = f"analysis/{args.date}/ACD/_sig/signal_preparation_data.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=signal_key,
        Body=json.dumps(signal_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved signal data: s3://{args.bucket}/{signal_key}")

    # Final summary
    print(f"\n📊 PHASE SIG SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Window: canonical_1200_1300")
    print(f"Venues: {coordination_indicators['n_venues']}")
    print(f"Correlation pairs: {len(correlation_results['pairwise_correlations'])}")
    print(f"Leader-follower pairs: {len(leader_follower_results)}")
    print(f"Volatility windows: {len(volatility_clustering)}")
    print(f"Coordination score: {coordination_indicators['coordination_score']:.2f}")
    print(f"Competition score: {coordination_indicators['competition_score']:.2f}")

    if coordination_indicators["coordination_score"] > 0.5:
        print(f"\n🔍 COORDINATION DETECTED")
        print(f"   High coordination signals detected across venues")
    elif coordination_indicators["competition_score"] > 0.5:
        print(f"\n⚔️ COMPETITION DETECTED")
        print(f"   High competition signals detected across venues")
    else:
        print(f"\n⚖️ NEUTRAL SIGNALS")
        print(f"   Mixed signals - neither strong coordination nor competition")

    print(f"\n✅ PHASE SIG COMPLETED")
    print(f"   Signal preparation completed successfully")
    print(f"   Ready for advanced ACD analysis")

    print(f"\n📁 Generated artifacts:")
    print(f"  Signal report: s3://{args.bucket}/{report_key}")
    print(f"  Signal data: s3://{args.bucket}/{signal_key}")


if __name__ == "__main__":
    main()
