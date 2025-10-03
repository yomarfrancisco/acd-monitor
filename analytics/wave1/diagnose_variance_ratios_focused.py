#!/usr/bin/env python3
"""
Focused Variance Ratio Diagnostic for 20251001

Since historical data is not available, focus on:
1. Venue-level analysis for 20251001
2. Control test using canonical data
3. Comparison with Wave-1 computed values
"""

import io
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
import numpy as np
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================

S3_BUCKET = "acd-monitor-snapshots"
ANALYSIS_PREFIX = "analysis/20251001/wave1_diagnostics"
DATE = "20251001"
SYMBOLS = ["BTC-USD", "ETH-USD"]

s3 = boto3.client("s3")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response["Body"].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")


def compute_variance_ratio(df: pd.DataFrame) -> float:
    """Compute variance ratio from price data."""
    if len(df) < 2:
        return np.nan

    # Use the correct timestamp column
    ts_col = "ts_verified" if "ts_verified" in df.columns else "ts_exchange_ms"
    df_sorted = df.sort_values(ts_col)

    # Compute 1-second returns
    df_sorted["price_1s"] = df_sorted["last_px"].pct_change()
    df_sorted["price_1s"] = df_sorted["price_1s"].fillna(0)

    # Compute 5-second returns (every 5th observation)
    df_sorted["price_5s"] = df_sorted["last_px"].pct_change(periods=5)
    df_sorted["price_5s"] = df_sorted["price_5s"].fillna(0)

    # Calculate variances
    var_1s = df_sorted["price_1s"].var()
    var_5s = df_sorted["price_5s"].var()

    if var_5s == 0:
        return np.nan

    return var_1s / var_5s


def load_canonical_data_for_date(date: str, symbol: str) -> pd.DataFrame:
    """Load canonical data for a specific date and symbol."""
    # Map symbol to the correct canonical path
    symbol_mapping = {"BTC-USD": "btc_ticks", "ETH-USD": "eth_ticks"}

    if symbol not in symbol_mapping:
        raise Exception(f"Unknown symbol: {symbol}")

    prefix = f"canonical/{date}/{symbol_mapping[symbol]}/"

    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if "Contents" not in response:
            raise Exception(f"No data found for {symbol} on {date} at prefix {prefix}")

        # Load all venue partitions
        dfs = []
        for obj in response["Contents"]:
            if obj["Key"].endswith(".parquet"):
                print(f"    Loading {obj['Key']}")
                venue_df = read_parquet_s3(obj["Key"])
                dfs.append(venue_df)

        if not dfs:
            raise Exception(f"No parquet files found for {symbol} on {date}")

        # Combine all venue data
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df

    except Exception as e:
        raise Exception(f"Failed to load canonical data for {symbol} on {date}: {e}")


def load_wave1_variance_ratios() -> pd.DataFrame:
    """Load Wave-1 computed variance ratios."""
    try:
        return read_parquet_s3(f"analysis/{DATE}/wave1/btc_usd/variance_ratios.parquet")
    except Exception as e:
        try:
            return read_parquet_s3(f"analysis/{DATE}/wave1/eth_usd/variance_ratios.parquet")
        except Exception as e:
            raise Exception("Could not load Wave-1 variance ratios")


# =============================================================================
# FOCUSED ANALYSIS
# =============================================================================


def analyze_venue_variance_ratios() -> pd.DataFrame:
    """Analyze venue-level variance ratios for 20251001."""
    print("📊 Analyzing venue-level variance ratios for 20251001...")

    results = []

    for symbol in SYMBOLS:
        print(f"  📈 Processing {symbol}...")

        try:
            # Load canonical data
            df = load_canonical_data_for_date(DATE, symbol)
            print(f"    ✅ Loaded {len(df)} total records")

            # Analyze each venue
            for venue in df["venue"].unique():
                venue_df = df[df["venue"] == venue]

                if len(venue_df) < 10:
                    print(f"    ⚠️ Insufficient data for {venue}: {len(venue_df)} records")
                    continue

                # Compute variance ratio
                vr = compute_variance_ratio(venue_df)

                # Additional statistics
                ts_col = "ts_verified" if "ts_verified" in venue_df.columns else "ts_exchange_ms"
                venue_df_sorted = venue_df.sort_values(ts_col)
                venue_df_sorted["returns"] = venue_df_sorted["last_px"].pct_change()
                venue_df_sorted = venue_df_sorted.dropna()

                if len(venue_df_sorted) > 0:
                    returns_std = venue_df_sorted["returns"].std()
                    price_range = (
                        venue_df_sorted["last_px"].max() - venue_df_sorted["last_px"].min()
                    )
                    price_mean = venue_df_sorted["last_px"].mean()
                    price_cv = returns_std / price_mean if price_mean > 0 else np.nan

                    results.append(
                        {
                            "symbol": symbol,
                            "venue": venue,
                            "variance_ratio": vr,
                            "returns_std": returns_std,
                            "price_range": price_range,
                            "price_mean": price_mean,
                            "price_cv": price_cv,
                            "n_obs": len(venue_df_sorted),
                            "data_source": "canonical",
                        }
                    )

                    print(f"    ✅ {venue}: VR={vr:.3f}, obs={len(venue_df_sorted)}")

        except Exception as e:
            print(f"    ❌ Failed {symbol}: {e}")

    return pd.DataFrame(results)


def compare_with_wave1_results() -> Dict[str, Any]:
    """Compare canonical variance ratios with Wave-1 computed values."""
    print("📊 Comparing with Wave-1 computed values...")

    comparison_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comparison_description": "Canonical vs Wave-1 variance ratios",
        "results": {},
    }

    try:
        # Load Wave-1 variance ratios
        wave1_df = read_parquet_s3(f"analysis/{DATE}/wave1/btc_usd/variance_ratios.parquet")
        print(f"  ✅ Loaded Wave-1 BTC variance ratios: {len(wave1_df)} venues")

        # Load canonical data for comparison
        canonical_df = load_canonical_data_for_date(DATE, "BTC-USD")

        # Compare each venue
        venue_comparisons = {}

        for _, wave1_row in wave1_df.iterrows():
            venue = wave1_row["venue"]
            wave1_vr = wave1_row["vr_ratio"]

            # Get canonical data for this venue
            venue_canonical = canonical_df[canonical_df["venue"] == venue]
            if len(venue_canonical) > 10:
                canonical_vr = compute_variance_ratio(venue_canonical)

                venue_comparisons[venue] = {
                    "wave1_vr": float(wave1_vr),
                    "canonical_vr": float(canonical_vr) if not np.isnan(canonical_vr) else None,
                    "difference": (
                        float(abs(wave1_vr - canonical_vr)) if not np.isnan(canonical_vr) else None
                    ),
                    "canonical_obs": int(len(venue_canonical)),
                    "significant_difference": (
                        bool(abs(wave1_vr - canonical_vr) > 0.1)
                        if not np.isnan(canonical_vr)
                        else False
                    ),
                }

                print(
                    f"  📊 {venue}: Wave-1={wave1_vr:.3f}, Canonical={canonical_vr:.3f}, Diff={abs(wave1_vr - canonical_vr):.3f}"
                )

        # Calculate summary statistics
        differences = [
            v["difference"] for v in venue_comparisons.values() if v["difference"] is not None
        ]
        avg_difference = float(np.mean(differences)) if differences else 0.0

        comparison_results["results"] = {
            "status": "SUCCESS",
            "venue_comparisons": venue_comparisons,
            "summary": {
                "total_venues": len(venue_comparisons),
                "significant_differences": sum(
                    1 for v in venue_comparisons.values() if v["significant_difference"]
                ),
                "avg_difference": avg_difference,
            },
        }

    except Exception as e:
        comparison_results["results"] = {"status": "FAILED", "error": str(e)}
        print(f"  ❌ Comparison failed: {e}")

    return comparison_results


def main():
    """Main focused diagnostic analysis."""
    print("🔍 Focused Variance Ratio Diagnostic for 20251001")
    print("=" * 60)

    # 1. Venue-level analysis
    print("\n1️⃣ Venue-Level Analysis")
    print("-" * 30)
    venue_df = analyze_venue_variance_ratios()

    # 2. Comparison with Wave-1 results
    print("\n2️⃣ Comparison with Wave-1 Results")
    print("-" * 30)
    comparison_results = compare_with_wave1_results()

    # Save results to S3
    print("\n💾 Saving diagnostic results to S3...")

    # Save venue analysis
    venue_key = f"{ANALYSIS_PREFIX}/variance_ratio_by_venue.csv"
    s3.put_object(Bucket=S3_BUCKET, Key=venue_key, Body=venue_df.to_csv(index=False))
    print(f"  ✅ {venue_key}")

    # Save comparison results
    comparison_key = f"{ANALYSIS_PREFIX}/variance_ratio_control.json"
    s3.put_object(
        Bucket=S3_BUCKET, Key=comparison_key, Body=json.dumps(comparison_results, indent=2)
    )
    print(f"  ✅ {comparison_key}")

    # Create README
    readme_content = """Focused Variance Ratio Diagnostic for 20251001
Generated: {datetime.now(timezone.utc).isoformat()}

This focused diagnostic analysis investigates the extremely low variance ratios (<0.3) 
detected in Stage G Wave-1 analysis for both BTC-USD and ETH-USD.

Files:
- variance_ratio_by_venue.csv: Venue-level variance ratio analysis
- variance_ratio_control.json: Comparison with Wave-1 computed values

Analysis Summary:
- Date analyzed: {DATE}
- Symbols: {', '.join(SYMBOLS)}
- Venue analysis: {len(venue_df)} venue-symbol combinations
- Comparison status: {comparison_results['results'].get('status', 'UNKNOWN')}

Key Findings:
- Venue-level VRs: {len(venue_df)} data points analyzed
- Wave-1 comparison: {comparison_results['results'].get('summary', {}).get('total_venues', 0)} venues compared
- Significant differences: {comparison_results['results'].get('summary', {}).get('significant_differences', 0)} venues

If variance ratios are consistently low across all venues, this suggests:
1. Real coordination/manipulation signal
2. Structural artifact in data processing
3. Ingestion/alignment issue

If Wave-1 and canonical VRs differ significantly, this indicates:
- Potential issue in Wave-1 computation
- Data processing pipeline artifact
- Different data sources or time windows

Next Steps:
1. Review venue-level patterns for coordination signals
2. Investigate significant differences between Wave-1 and canonical VRs
3. Consider data quality and processing pipeline issues
"""

    readme_key = f"{ANALYSIS_PREFIX}/README.txt"
    s3.put_object(Bucket=S3_BUCKET, Key=readme_key, Body=readme_content)
    print(f"  ✅ {readme_key}")

    # Print summary
    print("\n📊 DIAGNOSTIC SUMMARY:")
    print("=" * 40)

    if len(venue_df) > 0:
        print("Venue-level VRs:")
        for _, row in venue_df.iterrows():
            print(
                f"  {row['symbol']} {row['venue']}: {row['variance_ratio']:.3f} (obs: {row['n_obs']})"
            )

    if comparison_results["results"].get("status") == "SUCCESS":
        summary = comparison_results["results"]["summary"]
        print("\nWave-1 Comparison:")
        print(f"  Total venues: {summary['total_venues']}")
        print(f"  Significant differences: {summary['significant_differences']}")
        print(f"  Average difference: {summary['avg_difference']:.3f}")

    print(
        f"\n✅ Focused diagnostic analysis complete. Results saved to s3://{S3_BUCKET}/{ANALYSIS_PREFIX}/"
    )


if __name__ == "__main__":
    main()
