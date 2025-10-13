#!/usr/bin/env python3
"""
Compute lagged and nonlinear dependence for Stage H2
"""

import json
import os
import sys
import io
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import boto3
from scipy.stats import pearsonr
from sklearn.metrics import mutual_info_score

# Import environment gates
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from CI.env_gates import check_gates

S3_BUCKET = "acd-monitor-snapshots"
DATE = "20251001"

s3 = boto3.client("s3")


def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response["Body"].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")


def load_canonical_data(symbol: str) -> pd.DataFrame:
    """Load canonical data for symbol."""
    symbol_mapping = {"BTC-USD": "btc_ticks", "ETH-USD": "eth_ticks"}

    if symbol not in symbol_mapping:
        raise Exception(f"Unknown symbol: {symbol}")

    prefix = f"canonical/{DATE}/{symbol_mapping[symbol]}/"

    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if "Contents" not in response:
            raise Exception(f"No data found for {symbol}")

        dfs = []
        for obj in response["Contents"]:
            if obj["Key"].endswith(".parquet"):
                venue_df = read_parquet_s3(obj["Key"])
                dfs.append(venue_df)

        if not dfs:
            raise Exception(f"No parquet files found for {symbol}")

        return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        raise Exception(f"Failed to load canonical data for {symbol}: {e}")


def compute_lagged_correlations(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute lagged correlations between venue pairs."""
    print(f"  📊 Computing lagged correlations for {symbol}...")

    # Convert timestamp
    ts_col = "ts_verified" if "ts_verified" in df.columns else "ts_exchange_ms"
    if ts_col == "ts_exchange_ms":
        df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df[ts_col], utc=True)

    # Compute mid price and returns
    df["mid_price"] = (df["best_bid"] + df["best_ask"]) / 2.0
    df["returns"] = df.groupby("venue")["mid_price"].pct_change()

    # Get venue pairs
    venues = df["venue"].unique()
    venue_pairs = [(v1, v2) for v1 in venues for v2 in venues if v1 < v2]

    results = []
    lags = [-30, -10, -5, 0, 5, 10, 30]  # seconds

    for venue1, venue2 in venue_pairs:
        print(f"    📈 Processing pair: {venue1}-{venue2}")

        # Get data for both venues
        v1_data = df[df["venue"] == venue1].sort_values("timestamp")
        v2_data = df[df["venue"] == venue2].sort_values("timestamp")

        if len(v1_data) == 0 or len(v2_data) == 0:
            continue

        # Align timestamps (nearest within 1 second)
        v1_data["timestamp_rounded"] = v1_data["timestamp"].dt.floor("S")
        v2_data["timestamp_rounded"] = v2_data["timestamp"].dt.floor("S")

        # Get aligned data
        aligned_data = pd.merge(
            v1_data[["timestamp_rounded", "returns"]].rename(columns={"returns": "returns_v1"}),
            v2_data[["timestamp_rounded", "returns"]].rename(columns={"returns": "returns_v2"}),
            on="timestamp_rounded",
            how="inner",
        )

        if len(aligned_data) < 10:
            continue

        # Compute correlations for each lag
        for lag in lags:
            try:
                if lag == 0:
                    # No lag
                    v1_clean = aligned_data["returns_v1"].dropna()
                    v2_clean = aligned_data["returns_v2"].dropna()
                elif lag > 0:
                    # Positive lag: v2 leads v1
                    v1_shifted = aligned_data["returns_v1"].shift(lag)
                    v1_clean = v1_shifted.dropna()
                    v2_clean = aligned_data["returns_v2"].dropna()
                else:
                    # Negative lag: v1 leads v2
                    v2_shifted = aligned_data["returns_v2"].shift(-lag)
                    v1_clean = aligned_data["returns_v1"].dropna()
                    v2_clean = v2_shifted.dropna()

                # Align lengths
                min_len = min(len(v1_clean), len(v2_clean))
                if min_len < 10:
                    continue

                v1_aligned = v1_clean.iloc[:min_len]
                v2_aligned = v2_clean.iloc[:min_len]

                rho, p_value = pearsonr(v1_aligned, v2_aligned)

            except Exception as e:
                print(f"    ⚠️ Correlation failed for lag {lag}: {e}")
                continue

            if not np.isnan(rho):
                results.append(
                    {
                        "symbol": symbol,
                        "venue1": venue1,
                        "venue2": venue2,
                        "lag_s": lag,
                        "rho": rho,
                        "n_aligned": len(aligned_data),
                        "window": DATE,
                    }
                )

    return pd.DataFrame(results)


def compute_mutual_information(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Compute mutual information between venue pairs."""
    print(f"  📊 Computing mutual information for {symbol}...")

    # Convert timestamp
    ts_col = "ts_verified" if "ts_verified" in df.columns else "ts_exchange_ms"
    if ts_col == "ts_exchange_ms":
        df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df[ts_col], utc=True)

    # Compute mid price and returns
    df["mid_price"] = (df["best_bid"] + df["best_ask"]) / 2.0
    df["returns"] = df.groupby("venue")["mid_price"].pct_change()

    # Get venue pairs
    venues = df["venue"].unique()
    venue_pairs = [(v1, v2) for v1 in venues for v2 in venues if v1 < v2]

    results = []

    for venue1, venue2 in venue_pairs:
        print(f"    📈 Processing pair: {venue1}-{venue2}")

        # Get data for both venues
        v1_data = df[df["venue"] == venue1].sort_values("timestamp")
        v2_data = df[df["venue"] == venue2].sort_values("timestamp")

        if len(v1_data) == 0 or len(v2_data) == 0:
            continue

        # Align timestamps
        v1_data["timestamp_rounded"] = v1_data["timestamp"].dt.floor("S")
        v2_data["timestamp_rounded"] = v2_data["timestamp"].dt.floor("S")

        # Get aligned data
        aligned_data = pd.merge(
            v1_data[["timestamp_rounded", "returns"]].rename(columns={"returns": "returns_v1"}),
            v2_data[["timestamp_rounded", "returns"]].rename(columns={"returns": "returns_v2"}),
            on="timestamp_rounded",
            how="inner",
        )

        if len(aligned_data) < 10:
            continue

        # Compute mutual information
        try:
            # Discretize returns for MI calculation
            returns_v1 = aligned_data["returns_v1"].dropna()
            returns_v2 = aligned_data["returns_v2"].dropna()

            if len(returns_v1) < 10 or len(returns_v2) < 10:
                continue

            # Align lengths
            min_len = min(len(returns_v1), len(returns_v2))
            returns_v1_aligned = returns_v1.iloc[:min_len]
            returns_v2_aligned = returns_v2.iloc[:min_len]

            if min_len < 10:
                continue

            # Use quantile-based discretization
            v1_bins = pd.qcut(returns_v1_aligned, q=5, duplicates="drop", labels=False)
            v2_bins = pd.qcut(returns_v2_aligned, q=5, duplicates="drop", labels=False)

            # Remove any NaN values
            valid_mask = ~(np.isnan(v1_bins) | np.isnan(v2_bins))
            v1_bins = v1_bins[valid_mask]
            v2_bins = v2_bins[valid_mask]

            if len(v1_bins) < 10:
                continue

            mi = mutual_info_score(v1_bins, v2_bins)

            results.append(
                {
                    "symbol": symbol,
                    "venue1": venue1,
                    "venue2": venue2,
                    "metric": "mutual_information",
                    "value": mi,
                    "n_aligned": len(aligned_data),
                }
            )

        except Exception as e:
            print(f"    ⚠️ MI calculation failed for {venue1}-{venue2}: {e}")
            continue

    return pd.DataFrame(results)


def save_results(symbol: str, lagged_df: pd.DataFrame, mi_df: pd.DataFrame) -> Dict[str, Any]:
    """Save results and create manifest."""
    symbol_lower = symbol.lower().replace("-", "_")

    # Save lagged correlations
    lagged_key = f"analysis/{DATE}/wave1_h2/{symbol_lower}_lagged_xcorr.parquet"
    lagged_buffer = io.BytesIO()
    lagged_df.to_parquet(lagged_buffer, index=False)
    lagged_buffer.seek(0)

    s3.put_object(Bucket=S3_BUCKET, Key=lagged_key, Body=lagged_buffer.getvalue())

    # Save mutual information (only if not empty)
    mi_key = f"analysis/{DATE}/wave1_h2/{symbol_lower}_mutual_info.parquet"
    if len(mi_df) > 0:
        mi_buffer = io.BytesIO()
        mi_df.to_parquet(mi_buffer, index=False)
        mi_buffer.seek(0)

        s3.put_object(Bucket=S3_BUCKET, Key=mi_key, Body=mi_buffer.getvalue())
    else:
        # Create empty DataFrame with correct schema
        empty_mi = pd.DataFrame(
            columns=["symbol", "venue1", "venue2", "metric", "value", "n_aligned"]
        )
        mi_buffer = io.BytesIO()
        empty_mi.to_parquet(mi_buffer, index=False)
        mi_buffer.seek(0)

        s3.put_object(Bucket=S3_BUCKET, Key=mi_key, Body=mi_buffer.getvalue())

    # Create manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "lagged_correlations": {
            "rows": len(lagged_df),
            "columns": list(lagged_df.columns) if len(lagged_df) > 0 else [],
            "checksum": hashlib.sha256(lagged_buffer.getvalue()).hexdigest(),
        },
        "mutual_information": {
            "rows": len(mi_df),
            "columns": list(mi_df.columns) if len(mi_df) > 0 else [],
            "checksum": hashlib.sha256(mi_buffer.getvalue()).hexdigest(),
        },
        "coverage_stats": {
            "venue_pairs": (
                len(lagged_df.groupby(["venue1", "venue2"])) if len(lagged_df) > 0 else 0
            ),
            "lags_tested": len(lagged_df["lag_s"].unique()) if len(lagged_df) > 0 else 0,
        },
    }

    # Save manifest
    manifest_key = f"analysis/{DATE}/wave1_h2/_checks/manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=manifest_key, Body=json.dumps(manifest, indent=2))

    return manifest


def main():
    """Main function."""
    print("🔍 Computing lagged and nonlinear dependence for Stage H2...")

    # Check gates
    gates = check_gates()
    if gates["ALLOW_OVERWRITE"]:
        print("⚠️ ALLOW_OVERWRITE=true - proceeding with potential overwrites")
    else:
        print("🔒 ALLOW_OVERWRITE=false - no overwrites allowed")

    symbols = ["BTC-USD", "ETH-USD"]
    results = {}

    for symbol in symbols:
        try:
            print(f"\n📊 Processing {symbol}...")

            # Load canonical data
            df = load_canonical_data(symbol)
            print(f"  ✅ Loaded {len(df)} records")

            # Compute lagged correlations
            lagged_df = compute_lagged_correlations(df, symbol)
            print(f"  ✅ Lagged correlations: {len(lagged_df)} pairs")

            # Compute mutual information
            mi_df = compute_mutual_information(df, symbol)
            print(f"  ✅ Mutual information: {len(mi_df)} pairs")

            # Save results
            try:
                manifest = save_results(symbol, lagged_df, mi_df)
                results[symbol] = manifest
            except Exception as e:
                print(f"  ❌ Save failed for {symbol}: {e}")
                results[symbol] = {"status": "failed", "error": f"Save failed: {e}"}

        except Exception as e:
            print(f"  ❌ Failed {symbol}: {e}")
            results[symbol] = {"status": "failed", "error": str(e)}

    # Print summary
    print(f"\n📊 Lagged & Nonlinear Dependence Summary:")
    for symbol, result in results.items():
        if result.get("status") == "failed":
            print(f"  {symbol}: FAILED - {result.get('error')}")
        else:
            lagged = result.get("lagged_correlations", {})
            mi = result.get("mutual_information", {})
            print(f"  {symbol}: Lagged={lagged.get('rows', 0)} rows, MI={mi.get('rows', 0)} rows")


if __name__ == "__main__":
    main()
