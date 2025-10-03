#!/usr/bin/env python3
"""
Wave-1 Variable Computation for Competitive Behavior Screening

This script computes Wave-1 variables for competitive behavior analysis:
- Returns & variance ratios
- Autocorrelation (AR(1), AR(k))
- Cross-correlation
- PCA analysis
- Rolling volatility & spread convergence

Usage:
    python analytics/wave1/compute_wave1.py --date 20251001
"""

import argparse
import hashlib
import io
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Configuration
S3_BUCKET = "acd-monitor-snapshots"
CANONICAL_PREFIX = "canonical"
ANALYSIS_PREFIX = "analysis"
WAVE1_PREFIX = "wave1"


def load_canonical_data(s3_client, date_ymd: str, symbol: str) -> pd.DataFrame:
    """Load canonical data for a specific symbol and date."""
    print(f"📊 Loading {symbol} canonical data for {date_ymd}...")

    data_frames = []

    if symbol == "BTC-USD":
        venues = ["coinbase", "kraken", "okx"]
    elif symbol == "ETH-USD":
        venues = ["coinbase", "kraken"]
    else:
        raise ValueError(f"Unsupported symbol: {symbol}")

    for venue in venues:
        try:
            # Map symbol to canonical path
            if symbol == "BTC-USD":
                symbol_path = "btc_ticks"
            elif symbol == "ETH-USD":
                symbol_path = "eth_ticks"
            else:
                raise ValueError(f"Unsupported symbol: {symbol}")

            key = f"{CANONICAL_PREFIX}/{date_ymd}/{symbol_path}/venue={venue}/part-0000.parquet"
            file_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            df = pd.read_parquet(io.BytesIO(file_obj["Body"].read()))
            data_frames.append(df)
            print(f"  {venue}: {len(df):,} records")
        except Exception as e:
            print(f"  Error loading {venue}: {e}")
            raise

    if not data_frames:
        raise ValueError(f"No data loaded for {symbol}")

    combined_df = pd.concat(data_frames, ignore_index=True)
    print(f"  Total: {len(combined_df):,} records")

    return combined_df


def prepare_midprices(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare midprices from best_bid/best_ask or use last_px as proxy."""
    print("🔧 Preparing midprices...")

    # Create midprice from best_bid/best_ask when available
    df["mid_px"] = np.where(
        (df["best_bid"].notna()) & (df["best_ask"].notna()),
        (df["best_bid"] + df["best_ask"]) / 2.0,
        df["last_px"],  # Fallback to last_px
    )

    # Convert timestamp to datetime
    df["ts_exchange"] = pd.to_datetime(df["ts_exchange_ms"], unit="ms", utc=True)

    # Sort by venue and timestamp
    df = df.sort_values(["venue", "ts_exchange"]).reset_index(drop=True)

    print(f"  Midprices prepared: {len(df):,} records")
    return df


def compute_returns_variance_ratios(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute 1s returns and variance ratios (VR 1s vs 5s) per venue."""
    print(f"📈 Computing returns and variance ratios for {symbol}...")

    results = []

    for venue in df["venue"].unique():
        venue_data = df[df["venue"] == venue].copy()
        venue_data = venue_data.sort_values("ts_exchange").reset_index(drop=True)

        # Compute 1s returns
        venue_data["returns_1s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(1))

        # Compute 5s returns (every 5th observation)
        venue_data["returns_5s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(5))

        # Remove NaN values
        venue_data = venue_data.dropna(subset=["returns_1s", "returns_5s"])

        if len(venue_data) > 0:
            # Variance ratios
            var_1s = venue_data["returns_1s"].var()
            var_5s = venue_data["returns_5s"].var()
            vr_ratio = var_1s / var_5s if var_5s > 0 else np.nan

            results.append(
                {
                    "symbol": symbol,
                    "venue": venue,
                    "n_obs": len(venue_data),
                    "var_1s": var_1s,
                    "var_5s": var_5s,
                    "vr_ratio": vr_ratio,
                    "mean_return_1s": venue_data["returns_1s"].mean(),
                    "mean_return_5s": venue_data["returns_5s"].mean(),
                    "std_return_1s": venue_data["returns_1s"].std(),
                    "std_return_5s": venue_data["returns_5s"].std(),
                }
            )

    result_df = pd.DataFrame(results)
    print(f"  Computed for {len(result_df)} venues")
    return result_df


def compute_autocorrelation(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute AR(1) and AR(k) autocorrelation per venue."""
    print(f"🔄 Computing autocorrelation for {symbol}...")

    results = []

    for venue in df["venue"].unique():
        venue_data = df[df["venue"] == venue].copy()
        venue_data = venue_data.sort_values("ts_exchange").reset_index(drop=True)

        # Compute 1s returns
        venue_data["returns_1s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(1))
        venue_data = venue_data.dropna(subset=["returns_1s"])

        if len(venue_data) > 10:  # Need sufficient data
            returns = venue_data["returns_1s"].values

            # AR(1)
            ar1_coef = np.corrcoef(returns[:-1], returns[1:])[0, 1] if len(returns) > 1 else np.nan

            # AR(k) for k in {2, 3, 5}
            ar_coefs = {}
            for k in [2, 3, 5]:
                if len(returns) > k:
                    ar_coefs[f"ar{k}_coef"] = np.corrcoef(returns[:-k], returns[k:])[0, 1]
                else:
                    ar_coefs[f"ar{k}_coef"] = np.nan

            results.append(
                {
                    "symbol": symbol,
                    "venue": venue,
                    "n_obs": len(venue_data),
                    "ar1_coef": ar1_coef,
                    **ar_coefs,
                }
            )

    result_df = pd.DataFrame(results)
    print(f"  Computed for {len(result_df)} venues")
    return result_df


def compute_cross_correlation(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute pairwise venue cross-correlation of returns."""
    print(f"🔗 Computing cross-correlation for {symbol}...")

    results = []
    venues = df["venue"].unique()

    # Prepare returns for each venue
    venue_returns = {}
    for venue in venues:
        venue_data = df[df["venue"] == venue].copy()
        venue_data = venue_data.sort_values("ts_exchange").reset_index(drop=True)
        venue_data["returns_1s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(1))
        venue_data = venue_data.dropna(subset=["returns_1s", "ts_exchange"])

        if len(venue_data) > 0:
            venue_returns[venue] = venue_data[["ts_exchange", "returns_1s"]].copy()

    # Compute pairwise correlations
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            if venue1 in venue_returns and venue2 in venue_returns:
                # Align timestamps (nearest neighbor)
                merged = pd.merge_asof(
                    venue_returns[venue1].sort_values("ts_exchange"),
                    venue_returns[venue2].sort_values("ts_exchange"),
                    on="ts_exchange",
                    direction="nearest",
                    tolerance=pd.Timedelta(seconds=5),
                )

                if len(merged) > 10:
                    corr = merged["returns_1s_x"].corr(merged["returns_1s_y"])
                    results.append(
                        {
                            "symbol": symbol,
                            "venue1": venue1,
                            "venue2": venue2,
                            "n_aligned": len(merged),
                            "cross_corr": corr,
                        }
                    )

    result_df = pd.DataFrame(results)
    print(f"  Computed {len(result_df)} pairwise correlations")
    return result_df


def compute_pca_analysis(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute PCA analysis on standardized returns."""
    print(f"📊 Computing PCA analysis for {symbol}...")

    # Prepare standardized returns matrix
    venue_returns = {}
    venues = df["venue"].unique()

    for venue in venues:
        venue_data = df[df["venue"] == venue].copy()
        venue_data = venue_data.sort_values("ts_exchange").reset_index(drop=True)
        venue_data["returns_1s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(1))
        venue_data = venue_data.dropna(subset=["returns_1s", "ts_exchange"])

        if len(venue_data) > 0:
            venue_returns[venue] = venue_data[["ts_exchange", "returns_1s"]].copy()

    if len(venue_returns) < 2:
        print(f"  Insufficient venues for PCA: {len(venue_returns)}")
        return create_pca_placeholder(symbol, venues, len(venue_returns), "insufficient_venues")

    # Align all venues to common timestamps
    common_ts = None
    for venue, data in venue_returns.items():
        if common_ts is None:
            common_ts = set(data["ts_exchange"])
        else:
            common_ts = common_ts.intersection(set(data["ts_exchange"]))

    MIN_COMMON = 120  # Minimum common timestamps required
    if len(common_ts) < MIN_COMMON:
        print(f"  Insufficient common timestamps: {len(common_ts)} < {MIN_COMMON}")
        return create_pca_placeholder(
            symbol, venues, len(common_ts), "insufficient_common_timestamps"
        )

    # Create aligned returns matrix
    aligned_data = []
    for venue in venues:
        if venue in venue_returns:
            venue_data = venue_returns[venue]
            venue_data = venue_data[venue_data["ts_exchange"].isin(common_ts)]
            venue_data = venue_data.sort_values("ts_exchange")
            aligned_data.append(venue_data["returns_1s"].values)

    if len(aligned_data) < 2:
        print(f"  Insufficient aligned data: {len(aligned_data)}")
        return create_pca_placeholder(symbol, venues, len(common_ts), "insufficient_aligned_data")

    # Stack returns matrix
    returns_matrix = np.column_stack(aligned_data)

    # Standardize
    returns_matrix = (returns_matrix - returns_matrix.mean(axis=0)) / returns_matrix.std(axis=0)

    # PCA
    from sklearn.decomposition import PCA

    pca = PCA()
    pca.fit(returns_matrix)

    # Results
    results = []
    for i, venue in enumerate(venues):
        if i < len(venues):
            results.append(
                {
                    "symbol": symbol,
                    "venue": venue,
                    "n_obs": len(common_ts),
                    "explained_variance_ratio": (
                        pca.explained_variance_ratio_[i]
                        if i < len(pca.explained_variance_ratio_)
                        else 0
                    ),
                    "component_1": pca.components_[0][i] if len(pca.components_) > 0 else 0,
                    "component_2": pca.components_[1][i] if len(pca.components_) > 1 else 0,
                    "component_3": pca.components_[2][i] if len(pca.components_) > 2 else 0,
                }
            )

    result_df = pd.DataFrame(results)
    print(f"  PCA computed for {len(result_df)} venues")
    print(f"  Explained variance (top 3): {pca.explained_variance_ratio_[:3]}")
    return result_df


def create_pca_placeholder(symbol: str, venues: list, n_common: int, reason: str) -> pd.DataFrame:
    """Create PCA placeholder artifact when PCA is skipped."""
    print(f"  Creating PCA placeholder: {reason}")

    placeholder_data = {
        "symbol": [symbol],
        "venues": [venues],
        "n_common": [n_common],
        "window_sec": [60],  # 60-second window
        "status": ["skipped"],
        "reason": [reason],
        "ts_created_utc": [datetime.now(timezone.utc).isoformat()],
        "explained_var_ratio": [None],
        "n_components": [None],
    }

    return pd.DataFrame(placeholder_data)


def compute_rolling_volatility(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute 60s rolling volatility and spread convergence."""
    print(f"📊 Computing rolling volatility for {symbol}...")

    results = []

    for venue in df["venue"].unique():
        venue_data = df[df["venue"] == venue].copy()
        venue_data = venue_data.sort_values("ts_exchange").reset_index(drop=True)

        # Compute 1s returns
        venue_data["returns_1s"] = np.log(venue_data["mid_px"] / venue_data["mid_px"].shift(1))
        venue_data = venue_data.dropna(subset=["returns_1s"])

        if len(venue_data) > 60:  # Need sufficient data for 60s rolling
            # 60s rolling volatility
            venue_data["rolling_vol_60s"] = (
                venue_data["returns_1s"].rolling(window=60, min_periods=30).std()
            )

            # Spread convergence (if bid/ask available)
            if "best_bid" in venue_data.columns and "best_ask" in venue_data.columns:
                venue_data["spread"] = venue_data["best_ask"] - venue_data["best_bid"]
                venue_data["spread_pct"] = venue_data["spread"] / venue_data["mid_px"] * 100
                venue_data["rolling_spread_60s"] = (
                    venue_data["spread_pct"].rolling(window=60, min_periods=30).mean()
                )
            else:
                venue_data["rolling_spread_60s"] = np.nan

            # Summary statistics
            vol_stats = venue_data["rolling_vol_60s"].dropna()
            spread_stats = venue_data["rolling_spread_60s"].dropna()

            results.append(
                {
                    "symbol": symbol,
                    "venue": venue,
                    "n_obs": len(venue_data),
                    "mean_vol_60s": vol_stats.mean(),
                    "std_vol_60s": vol_stats.std(),
                    "min_vol_60s": vol_stats.min(),
                    "max_vol_60s": vol_stats.max(),
                    "mean_spread_60s": spread_stats.mean() if len(spread_stats) > 0 else np.nan,
                    "std_spread_60s": spread_stats.std() if len(spread_stats) > 0 else np.nan,
                }
            )

    result_df = pd.DataFrame(results)
    print(f"  Computed for {len(result_df)} venues")
    return result_df


def save_results(s3_client, date_ymd: str, symbol: str, results: Dict[str, pd.DataFrame]):
    """Save Wave-1 results to S3."""
    print(f"💾 Saving {symbol} Wave-1 results...")

    symbol_lower = symbol.lower().replace("-", "_")

    for result_type, df in results.items():
        if len(df) > 0:
            # Convert to Parquet
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0)

            # Save to S3
            s3_key = (
                f"{ANALYSIS_PREFIX}/{date_ymd}/{WAVE1_PREFIX}/{symbol_lower}/{result_type}.parquet"
            )
            try:
                s3_client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=parquet_buffer.getvalue())
                print(f"  ✅ Successfully saved s3://{S3_BUCKET}/{s3_key}")
            except Exception as e:
                print(
                    f"  ❌ ERROR: Failed to save s3://{S3_BUCKET}/{s3_key}. Reason: {e}",
                    file=sys.stderr,
                )
                raise

            print(f"  Saved {result_type}.parquet ({len(df)} rows)")
        else:
            print(f"  Skipped {result_type}.parquet (empty)")


def create_manifest(s3_client, date_ymd: str, all_results: Dict[str, Dict[str, pd.DataFrame]]):
    """Create manifest with checksums and counts."""
    print("📋 Creating manifest...")

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "F",
        "date": date_ymd,
        "wave1_analysis": True,
        "symbols": list(all_results.keys()),
        "artifacts": {},
    }

    for symbol, results in all_results.items():
        symbol_lower = symbol.lower().replace("-", "_")
        manifest["artifacts"][symbol] = {}

        for result_type, df in results.items():
            if len(df) > 0:
                # Compute hash
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False)
                parquet_buffer.seek(0)
                content = parquet_buffer.getvalue()
                sha256_hash = hashlib.sha256(content).hexdigest()

                # Special handling for PCA status
                pca_info = {}
                if result_type == "pca":
                    if "status" in df.columns and df["status"].iloc[0] == "skipped":
                        pca_info = {
                            "status": "skipped",
                            "n_common": (
                                int(df["n_common"].iloc[0]) if "n_common" in df.columns else 0
                            ),
                            "reason": (
                                str(df["reason"].iloc[0]) if "reason" in df.columns else "unknown"
                            ),
                        }
                    else:
                        pca_info = {
                            "status": "ok",
                            "n_common": int(df["n_obs"].iloc[0]) if "n_obs" in df.columns else 0,
                            "n_components": (
                                int(len(df["explained_variance_ratio"].dropna()))
                                if "explained_variance_ratio" in df.columns
                                else 0
                            ),
                            "explained_var_ratio": (
                                [float(x) for x in df["explained_variance_ratio"].dropna().tolist()]
                                if "explained_variance_ratio" in df.columns
                                else []
                            ),
                        }

                manifest["artifacts"][symbol][result_type] = {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "sha256": sha256_hash,
                    "venues": df["venue"].unique().tolist() if "venue" in df.columns else [],
                    "non_null_ts": (
                        df["ts_exchange_ms"].notna().sum() if "ts_exchange_ms" in df.columns else 0
                    ),
                    "non_null_px": df["last_px"].notna().sum() if "last_px" in df.columns else 0,
                    **pca_info,
                }

    # Save manifest
    manifest_json = json.dumps(manifest, indent=2)
    manifest_key = f"{ANALYSIS_PREFIX}/{date_ymd}/{WAVE1_PREFIX}/_checks/manifest.json"
    try:
        s3_client.put_object(Bucket=S3_BUCKET, Key=manifest_key, Body=manifest_json)
        print(f"  ✅ Successfully saved manifest s3://{S3_BUCKET}/{manifest_key}")
    except Exception as e:
        print(
            f"  ❌ ERROR: Failed to save manifest s3://{S3_BUCKET}/{manifest_key}. Reason: {e}",
            file=sys.stderr,
        )
        raise

    print("  Manifest saved")


def main():
    parser = argparse.ArgumentParser(
        description="Compute Wave-1 variables for competitive behavior analysis"
    )
    parser.add_argument("--date", required=True, help="Date in YYYYMMDD format (e.g., 20251001)")
    args = parser.parse_args()

    print(f"🔍 Computing Wave-1 variables for {args.date}")

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Process each symbol
    all_results = {}
    symbols = ["BTC-USD", "ETH-USD"]

    for symbol in symbols:
        print(f"\n📊 Processing {symbol}...")

        try:
            # Load canonical data
            df = load_canonical_data(s3_client, args.date, symbol)
            print(f"  📊 Loaded {len(df)} rows for {symbol}")

            if len(df) == 0:
                print(f"  ⚠️ No data available for {symbol} - skipping")
                continue

            # Prepare midprices
            df = prepare_midprices(df)

            # Compute Wave-1 variables
            results = {
                "variance_ratios": compute_returns_variance_ratios(df, symbol),
                "autocorr": compute_autocorrelation(df, symbol),
                "xcorr": compute_cross_correlation(df, symbol),
                "pca": compute_pca_analysis(df, symbol),
                "rolling": compute_rolling_volatility(df, symbol),
            }

            # Save results
            save_results(s3_client, args.date, symbol, results)
            all_results[symbol] = results

        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            raise

    # Create manifest
    create_manifest(s3_client, args.date, all_results)

    print("\n✅ Wave-1 variable computation completed successfully")
    print("📊 All variables computed and saved to S3")
    print("🎯 Ready for competitive behavior analysis")


if __name__ == "__main__":
    main()
