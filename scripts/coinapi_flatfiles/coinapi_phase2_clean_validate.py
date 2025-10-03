#!/usr/bin/env python3
"""
CoinAPI Phase 2 - Clean & Validate Returns Data

Work only inside the chosen overlap window, compute minute returns, and validate data quality.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd


def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"Error getting S3 object {key}: {e}")
        return None


def load_overlap_window(s3_client, bucket: str) -> Dict[str, Any]:
    """Load the overlap window configuration."""
    key = "analysis/coinapi/_align/overlap_window.json"
    content = get_s3_object_content(s3_client, bucket, key)

    if content is None:
        raise ValueError("No overlap window found. Run Phase 1 first.")

    return json.loads(content.decode("utf-8"))


def load_coinapi_ohlcv(s3_client, bucket: str, date: str, symbol: str) -> Optional[pd.DataFrame]:
    """Load CoinAPI OHLCV data from S3."""
    key = f"coinapi_bf1/ohlcv/{date}/{symbol}/part-0000.parquet"
    content = get_s3_object_content(s3_client, bucket, key)

    if content is None:
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()
        return df
    except Exception as e:
        print(f"Error loading {key}: {e}")
        return None


def extract_window_data(df: pd.DataFrame, window_start: str, window_end: str) -> pd.DataFrame:
    """Extract data for the specific time window."""
    window_start_dt = pd.to_datetime(window_start, utc=True)
    window_end_dt = pd.to_datetime(window_end, utc=True)

    # Filter to window using time_period_start
    timestamps = pd.to_datetime(df["time_period_start"], utc=True)
    window_data = df[(timestamps >= window_start_dt) & (timestamps < window_end_dt)].copy()

    return window_data


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute minute returns: r_t = ln(close_t / close_{t-1})."""
    df = df.copy()

    # Sort by timestamp to ensure proper order
    df = df.sort_values("time_period_start").reset_index(drop=True)

    # Compute log returns
    df["returns"] = np.log(df["price_close"] / df["price_close"].shift(1))

    # Remove first row (no previous price)
    df = df.dropna(subset=["returns"]).reset_index(drop=True)

    return df


def validate_venue_data(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Validate data quality for a single venue."""
    if df.empty:
        return {"venue": venue, "status": "empty", "message": "No data in window"}

    n_bars = len(df)
    n_returns = len(df.dropna(subset=["returns"]))

    # Check for missing data
    missing_returns = df["returns"].isna().sum()
    missing_pct = missing_returns / n_bars if n_bars > 0 else 1.0

    # Check for constant prices (zero variance)
    price_std = df["price_close"].std()
    is_constant = price_std == 0 or np.isnan(price_std)

    # Check returns variance
    returns_std = df["returns"].std()
    is_zero_variance = returns_std == 0 or np.isnan(returns_std)

    # Check for duplicate timestamps
    timestamp_duplicates = df["time_period_start"].duplicated().sum()
    duplicate_pct = timestamp_duplicates / n_bars if n_bars > 0 else 0

    # Check timestamp alignment (should be 1-minute intervals)
    if len(df) > 1:
        time_diffs = df["time_period_start"].diff().dt.total_seconds().dropna()
        expected_interval = 60  # 1 minute in seconds
        interval_errors = abs(time_diffs - expected_interval).sum()
        alignment_score = 1 - (interval_errors / (len(time_diffs) * expected_interval))
    else:
        alignment_score = 1.0

    # Quality assessment
    quality_issues = []
    if missing_pct > 0.05:  # More than 5% missing
        quality_issues.append(f"High missing data: {missing_pct:.1%}")
    if is_constant:
        quality_issues.append("Constant prices detected")
    if is_zero_variance:
        quality_issues.append("Zero returns variance")
    if duplicate_pct > 0.01:  # More than 1% duplicates
        quality_issues.append(f"Duplicate timestamps: {duplicate_pct:.1%}")
    if alignment_score < 0.95:  # Less than 95% alignment
        quality_issues.append(f"Poor timestamp alignment: {alignment_score:.3f}")

    # Overall quality
    if len(quality_issues) == 0:
        quality_status = "good"
    elif len(quality_issues) <= 2:
        quality_status = "acceptable"
    else:
        quality_status = "poor"

    return {
        "venue": venue,
        "status": "success",
        "n_bars": n_bars,
        "n_returns": n_returns,
        "missing_pct": float(missing_pct),
        "is_constant": bool(is_constant),
        "is_zero_variance": bool(is_zero_variance),
        "duplicate_pct": float(duplicate_pct),
        "alignment_score": float(alignment_score),
        "quality_issues": quality_issues,
        "quality_status": quality_status,
        "price_stats": {
            "mean": float(df["price_close"].mean()),
            "std": float(df["price_close"].std()),
            "min": float(df["price_close"].min()),
            "max": float(df["price_close"].max()),
        },
        "returns_stats": {
            "mean": float(df["returns"].mean()),
            "std": float(df["returns"].std()),
            "min": float(df["returns"].min()),
            "max": float(df["returns"].max()),
        },
    }


def main():
    print("🔍 COINAPI PHASE 2 - CLEAN & VALIDATE RETURNS DATA")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load overlap window configuration
    print("📊 Loading overlap window configuration...")
    try:
        overlap_config = load_overlap_window(s3_client, bucket)
        if overlap_config["status"] != "success":
            print(f"❌ Overlap window not found: {overlap_config['message']}")
            return

        best_window = overlap_config["best_window"]
        window_start = best_window["start"]
        window_end = best_window["end"]
        print(f"   ✅ Window: {window_start} to {window_end}")
        print(f"   📊 Size: {best_window['window_size_minutes']} minutes")
        print(f"   📊 Venues: {best_window['total_venues']}")

    except Exception as e:
        print(f"❌ Error loading overlap window: {e}")
        return

    # Load and process data for each venue
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    venue_data = {}
    quality_reports = {}

    print(f"\n📊 Processing venue data...")
    for symbol in symbols:
        print(f"   📊 Processing {symbol}...")

        # Load OHLCV data
        df = load_coinapi_ohlcv(s3_client, bucket, date, symbol)
        if df is None:
            print(f"      ❌ No data")
            continue

        # Extract window data
        window_df = extract_window_data(df, window_start, window_end)
        if window_df.empty:
            print(f"      ❌ No data in window")
            continue

        # Compute returns
        returns_df = compute_returns(window_df)
        venue_data[symbol] = returns_df

        # Validate data quality
        quality_report = validate_venue_data(returns_df, symbol)
        quality_reports[symbol] = quality_report

        print(f"      ✅ {quality_report['n_bars']} bars, {quality_report['n_returns']} returns")
        print(f"      📊 Quality: {quality_report['quality_status']}")
        if quality_report["quality_issues"]:
            print(f"      ⚠️  Issues: {', '.join(quality_report['quality_issues'])}")

    # Check if we have sufficient venues
    valid_venues = [
        symbol
        for symbol, report in quality_reports.items()
        if report["status"] == "success" and report["quality_status"] in ["good", "acceptable"]
    ]

    if len(valid_venues) < 2:
        print(f"\n❌ Insufficient valid venues: {len(valid_venues)} (need ≥2)")
        print("   📊 Quality summary:")
        for symbol, report in quality_reports.items():
            print(f"      {symbol}: {report['quality_status']} - {report.get('message', '')}")
        return

    print(f"\n✅ Valid venues: {len(valid_venues)} ({', '.join(valid_venues)})")

    # Save quality report
    quality_report_data = {
        "window": {
            "start": window_start,
            "end": window_end,
            "size_minutes": best_window["window_size_minutes"],
        },
        "venues": quality_reports,
        "valid_venues": valid_venues,
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    quality_key = f"analysis/coinapi/_cln/quality_report.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=quality_key,
        Body=json.dumps(quality_report_data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"   💾 Saved quality report: s3://{bucket}/{quality_key}")

    # Save returns data for each venue
    print(f"\n📊 Saving returns data...")
    for symbol in valid_venues:
        returns_df = venue_data[symbol]

        # Save returns parquet
        returns_key = f"analysis/coinapi/_cln/returns_{symbol}.parquet"
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            returns_df.to_parquet(tmp_file.name, index=False)
            s3_client.upload_file(tmp_file.name, bucket, returns_key)
            Path(tmp_file.name).unlink()

        print(f"   💾 Saved {symbol} returns: s3://{bucket}/{returns_key}")

    print(f"\n✅ PHASE 2 COMPLETE")
    print("=" * 80)
    print("📁 Generated artifacts:")
    print(f"  - Quality report: s3://{bucket}/{quality_key}")
    print(f"  - Returns data: s3://{bucket}/analysis/coinapi/_cln/returns_*.parquet")

    # Print summary
    print(f"\n📊 QUALITY SUMMARY:")
    for symbol, report in quality_reports.items():
        if report["status"] == "success":
            print(f"   {symbol}: {report['quality_status']} ({report['n_returns']} returns)")
            if report["quality_issues"]:
                print(f"      Issues: {', '.join(report['quality_issues'])}")


if __name__ == "__main__":
    main()
