#!/usr/bin/env python3
"""
Compute environment flags for Stage H2
"""

import json
import os
import sys
import io
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import boto3

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
    # Map symbol to the correct canonical path
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


def compute_session_label(timestamp: pd.Timestamp) -> str:
    """Compute session label based on UTC hour."""
    hour = timestamp.hour
    if 0 <= hour < 8:
        return "asia"
    elif 8 <= hour < 13:
        return "europe"
    elif 13 <= hour < 20:
        return "us"
    else:  # 20 <= hour < 24
        return "pacific"


def is_session_transition(timestamp: pd.Timestamp) -> bool:
    """Check if timestamp is within ±5m of session transitions."""
    hour = timestamp.hour
    minute = timestamp.minute

    transition_times = [0, 8, 13, 20]  # UTC hours

    for trans_hour in transition_times:
        if hour == trans_hour and minute <= 5:
            return True
        elif hour == (trans_hour - 1) and minute >= 55:
            return True

    return False


def is_ny_open(timestamp: pd.Timestamp) -> bool:
    """Check if timestamp is during NY open (13:30-13:45 UTC)."""
    return timestamp.hour == 13 and 30 <= timestamp.minute <= 45


def compute_venue_flags(df: pd.DataFrame, venue: str) -> pd.DataFrame:
    """Compute venue-specific flags."""
    venue_df = df[df["venue"] == venue].copy()

    if len(venue_df) == 0:
        return pd.DataFrame()

    # Sort by timestamp
    ts_col = "ts_verified" if "ts_verified" in venue_df.columns else "ts_exchange_ms"
    venue_df = venue_df.sort_values(ts_col)

    # Convert timestamp to datetime
    if ts_col == "ts_exchange_ms":
        venue_df["timestamp"] = pd.to_datetime(venue_df[ts_col], unit="ms", utc=True)
    else:
        venue_df["timestamp"] = pd.to_datetime(venue_df[ts_col], utc=True)

    # Compute mid price
    venue_df["mid_v"] = (venue_df["best_bid"] + venue_df["best_ask"]) / 2.0

    # Compute returns
    venue_df["r_v"] = venue_df["mid_v"].pct_change()

    # Rolling volatility (1800s window, min 900s)
    venue_df["sigma_v"] = venue_df["r_v"].rolling(window=1800, min_periods=900).std()

    # 2-sigma return flag
    venue_df["is_return_2sigma_v"] = (np.abs(venue_df["r_v"]) > 2 * venue_df["sigma_v"]).astype(int)

    # Daily VWAP (reset at 00:00)
    venue_df["date"] = venue_df["timestamp"].dt.date
    venue_df["vwap_v"] = (
        venue_df.groupby("date")
        .apply(lambda x: np.average(x["mid_v"], weights=x.get("trade_sz", 1)))
        .reset_index(level=0, drop=True)
    )

    # VWAP fallback flag (if sizes missing)
    venue_df["vwap_fallback_v"] = (
        venue_df["trade_sz"].isna() | (venue_df["trade_sz"] == 0)
    ).astype(int)

    # VWAP deviation (2-sigma)
    venue_df["mid_vwap_diff"] = np.abs(venue_df["mid_v"] - venue_df["vwap_v"])
    venue_df["mid_vwap_std"] = venue_df["mid_vwap_diff"].rolling(window=1800, min_periods=900).std()
    venue_df["is_vwap_dev_2sigma_v"] = (
        venue_df["mid_vwap_diff"] > 2 * venue_df["mid_vwap_std"]
    ).astype(int)

    # Daily VWAP reset jump flag
    def compute_vwap_reset_jump(group):
        if len(group) > 1:
            first_vwap = group.iloc[0]
            last_vwap = group.iloc[-1]
            return first_vwap - last_vwap
        return 0

    venue_df["vwap_reset_jump"] = venue_df.groupby("date")["vwap_v"].transform(
        compute_vwap_reset_jump
    )
    venue_df["is_vwap_reset_jump_day"] = (venue_df["vwap_reset_jump"] != 0).astype(int)

    return venue_df


def compute_env_flags(symbol: str) -> pd.DataFrame:
    """Compute environment flags for a symbol."""
    print(f"📊 Computing environment flags for {symbol}...")

    # Load canonical data
    df = load_canonical_data(symbol)
    print(f"  ✅ Loaded {len(df)} records")

    # Convert timestamp to datetime
    ts_col = "ts_verified" if "ts_verified" in df.columns else "ts_exchange_ms"
    if ts_col == "ts_exchange_ms":
        df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df[ts_col], utc=True)

    # Compute global flags
    df["session_label"] = df["timestamp"].apply(compute_session_label)
    df["is_session_transition"] = df["timestamp"].apply(is_session_transition)
    df["is_ny_open"] = df["timestamp"].apply(is_ny_open)

    # Compute venue-specific flags
    venue_flags = []
    for venue in df["venue"].unique():
        venue_df = compute_venue_flags(df, venue)
        if len(venue_df) > 0:
            venue_flags.append(venue_df)

    if not venue_flags:
        raise Exception(f"No venue data available for {symbol}")

    # Combine all venue flags
    result_df = pd.concat(venue_flags, ignore_index=True)

    # Add coverage mask (venues present per second)
    result_df["coverage_mask"] = result_df.groupby("timestamp")["venue"].transform("count")

    print(f"  ✅ Computed flags for {len(result_df)} records")
    return result_df


def save_env_flags(symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
    """Save environment flags and create manifest."""
    symbol_lower = symbol.lower().replace("-", "_")
    key = f"data/derived/{symbol_lower}/env_flags_1s.parquet"

    # Check if file exists
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        print(f"  ⚠️ File exists: {key} - reusing")
        return {"status": "reused", "key": key}
    except:
        pass

    # Save parquet file
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)

    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=parquet_buffer.getvalue())

    print(f"  ✅ Saved: {key}")

    # Create manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "rows": len(df),
        "columns": list(df.columns),
        "checksum": hashlib.sha256(parquet_buffer.getvalue()).hexdigest(),
        "coverage_stats": {
            "total_seconds": df["timestamp"].nunique(),
            "venues_present": df["venue"].nunique(),
            "avg_coverage": df["coverage_mask"].mean(),
        },
    }

    # Save manifest
    manifest_key = f"data/derived/{symbol_lower}/_checks/manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=manifest_key, Body=json.dumps(manifest, indent=2))

    return manifest


def main():
    """Main function."""
    print("🔍 Computing environment flags for Stage H2...")

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
            # Check if ETH panel exists and is aligned
            if symbol == "ETH-USD":
                # For now, assume ETH panel exists (exploratory)
                print(f"  📊 ETH-USD: exploratory mode")

            df = compute_env_flags(symbol)
            manifest = save_env_flags(symbol, df)
            results[symbol] = manifest

        except Exception as e:
            print(f"  ❌ Failed {symbol}: {e}")
            results[symbol] = {"status": "failed", "error": str(e)}

    # Print summary
    print(f"\n📊 Environment Flags Summary:")
    for symbol, result in results.items():
        if result.get("status") == "reused":
            print(f"  {symbol}: REUSED")
        elif result.get("status") == "failed":
            print(f"  {symbol}: FAILED - {result.get('error')}")
        else:
            print(f"  {symbol}: COMPUTED - {result.get('rows', 0)} rows")


if __name__ == "__main__":
    main()
