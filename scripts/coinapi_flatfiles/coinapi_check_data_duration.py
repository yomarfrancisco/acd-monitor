#!/usr/bin/env python3
"""
CoinAPI Check Data Duration

Check the exact duration of the time period captured in our 1-second data.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
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


def load_1sec_candles(s3_client, bucket: str, date: str, symbol: str) -> Optional[pd.DataFrame]:
    """Load 1-second candle data from S3."""
    key = f"coinapi_bf1/ohlcv_1sec/{date}/{symbol}/part-0000.parquet"
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


def analyze_data_duration(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Analyze the duration and coverage of the data."""
    if df.empty:
        return {"status": "empty", "message": "No data"}

    # Get time range
    start_time = df["time_period_start"].min()
    end_time = df["time_period_start"].max()
    duration = (end_time - start_time).total_seconds()

    # Calculate expected vs actual
    n_candles = len(df)
    expected_candles = duration + 1  # +1 because we include both start and end

    # Check for gaps
    time_diffs = df["time_period_start"].diff().dt.total_seconds().dropna()
    gaps = time_diffs[time_diffs > 1.1]  # More than 1.1 seconds (allowing for small rounding)

    # Coverage analysis
    coverage_pct = (n_candles / expected_candles) * 100 if expected_candles > 0 else 0

    return {
        "status": "success",
        "symbol": symbol,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "duration_minutes": duration / 60,
        "duration_hours": duration / 3600,
        "n_candles": n_candles,
        "expected_candles": expected_candles,
        "coverage_pct": coverage_pct,
        "n_gaps": len(gaps),
        "gap_details": {
            "n_gaps": len(gaps),
            "total_gap_seconds": float(gaps.sum()) if len(gaps) > 0 else 0,
            "largest_gap_seconds": float(gaps.max()) if len(gaps) > 0 else 0,
        },
        "time_intervals": {
            "mean_interval_seconds": float(time_diffs.mean()),
            "std_interval_seconds": float(time_diffs.std()),
            "min_interval_seconds": float(time_diffs.min()),
            "max_interval_seconds": float(time_diffs.max()),
        },
    }


def main():
    print("🔍 COINAPI DATA DURATION ANALYSIS")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load and analyze 1-second data
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]

    print("📊 Analyzing 1-second candle data duration...")

    all_analysis = {}
    overall_start = None
    overall_end = None

    for symbol in symbols:
        print(f"\n📊 Analyzing {symbol}...")

        df = load_1sec_candles(s3_client, bucket, date, symbol)
        if df is None:
            print(f"   ❌ No data")
            continue

        analysis = analyze_data_duration(df, symbol)
        all_analysis[symbol] = analysis

        if analysis["status"] == "success":
            print(
                f"   ✅ Duration: {analysis['duration_hours']:.2f} hours ({analysis['duration_minutes']:.1f} minutes)"
            )
            print(f"   📊 Time range: {analysis['start_time']} to {analysis['end_time']}")
            print(
                f"   📊 Candles: {analysis['n_candles']} (expected: {analysis['expected_candles']:.0f})"
            )
            print(f"   📊 Coverage: {analysis['coverage_pct']:.1f}%")
            print(f"   📊 Gaps: {analysis['n_gaps']} gaps")

            if analysis["n_gaps"] > 0:
                print(
                    f"   ⚠️  Largest gap: {analysis['gap_details']['largest_gap_seconds']:.1f} seconds"
                )

            # Track overall time range
            start_time = pd.to_datetime(analysis["start_time"])
            end_time = pd.to_datetime(analysis["end_time"])

            if overall_start is None or start_time < overall_start:
                overall_start = start_time
            if overall_end is None or end_time > overall_end:
                overall_end = end_time

    # Overall analysis
    if overall_start and overall_end:
        overall_duration = (overall_end - overall_start).total_seconds()
        print(f"\n📊 OVERALL DATA DURATION")
        print("=" * 80)
        print(f"Overall start: {overall_start.isoformat()}")
        print(f"Overall end: {overall_end.isoformat()}")
        print(
            f"Total duration: {overall_duration/3600:.2f} hours ({overall_duration/60:.1f} minutes)"
        )
        print(f"Total duration: {overall_duration:.0f} seconds")

        # Check if it's exactly 1 hour
        if abs(overall_duration - 3600) < 60:  # Within 1 minute of 1 hour
            print(f"✅ Data covers approximately 1 hour (3600 seconds)")
        elif abs(overall_duration - 3600) < 300:  # Within 5 minutes of 1 hour
            print(f"⚠️  Data covers close to 1 hour ({overall_duration:.0f} seconds)")
        else:
            print(
                f"📊 Data covers {overall_duration:.0f} seconds ({overall_duration/3600:.2f} hours)"
            )

    # Summary by venue
    print(f"\n📊 VENUE SUMMARY")
    print("=" * 80)
    for symbol, analysis in all_analysis.items():
        if analysis["status"] == "success":
            print(f"{symbol}:")
            print(
                f"   Duration: {analysis['duration_hours']:.2f}h ({analysis['duration_seconds']:.0f}s)"
            )
            print(f"   Candles: {analysis['n_candles']} ({analysis['coverage_pct']:.1f}% coverage)")
            print(f"   Gaps: {analysis['n_gaps']}")

    # Save analysis
    analysis_data = {
        "overall": {
            "start_time": overall_start.isoformat() if overall_start else None,
            "end_time": overall_end.isoformat() if overall_end else None,
            "duration_seconds": overall_duration if overall_start and overall_end else None,
            "duration_hours": overall_duration / 3600 if overall_start and overall_end else None,
        },
        "venues": all_analysis,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    s3_client.put_object(
        Bucket=bucket,
        Key=f"analysis/coinapi/_sig_1sec/duration_analysis.json",
        Body=json.dumps(analysis_data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    print(
        f"\n💾 Saved duration analysis: s3://{bucket}/analysis/coinapi/_sig_1sec/duration_analysis.json"
    )


if __name__ == "__main__":
    main()
