#!/usr/bin/env python3
"""
CoinAPI Phase 1 - Build common 1-hour window

From OHLCV minute data, compute intersection and choose latest continuous 60-minute overlap.
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


def find_overlap_window(ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Find the best overlapping time window across venues."""
    if len(ohlcv_data) < 2:
        return {"status": "insufficient_venues", "message": "Need at least 2 venues"}

    # Get time ranges for each venue
    venue_ranges = {}
    for symbol, df in ohlcv_data.items():
        if df.empty:
            continue

        # Use time_period_start as the primary timestamp
        timestamps = pd.to_datetime(df["time_period_start"], utc=True)
        venue_ranges[symbol] = {
            "start": timestamps.min(),
            "end": timestamps.max(),
            "n_bars": len(df),
        }

    if len(venue_ranges) < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues with data"}

    # Find intersection
    common_start = max(tr["start"] for tr in venue_ranges.values())
    common_end = min(tr["end"] for tr in venue_ranges.values())

    if common_start >= common_end:
        return {"status": "no_overlap", "message": "No time overlap between venues"}

    # Try different window sizes: 60min, 30min, 15min
    window_sizes = [60, 30, 15]
    best_window = None

    for window_minutes in window_sizes:
        print(f"   🔍 Testing {window_minutes}-minute windows...")

        # Slide window through the common time range
        current_start = common_start
        window_duration = timedelta(minutes=window_minutes)

        while current_start + window_duration <= common_end:
            current_end = current_start + window_duration

            # Check coverage for each venue in this window
            window_coverage = {}
            total_venues = 0

            for symbol, df in ohlcv_data.items():
                if df.empty:
                    continue

                # Filter to window
                timestamps = pd.to_datetime(df["time_period_start"], utc=True)
                window_data = df[(timestamps >= current_start) & (timestamps < current_end)]

                n_bars = len(window_data)
                coverage_pct = n_bars / window_minutes if window_minutes > 0 else 0

                window_coverage[symbol] = {
                    "n_bars": n_bars,
                    "coverage_pct": coverage_pct,
                    "meets_threshold": n_bars >= (window_minutes * 0.97),  # 97% threshold
                }

                if n_bars > 0:
                    total_venues += 1

            # Check if this window meets criteria
            meets_criteria = total_venues >= 2 and all(  # At least 2 venues
                venue["meets_threshold"]
                for venue in window_coverage.values()
                if venue["n_bars"] > 0
            )

            if meets_criteria:
                window_info = {
                    "window_size_minutes": window_minutes,
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                    "duration_hours": window_minutes / 60,
                    "total_venues": total_venues,
                    "coverage": window_coverage,
                    "quality_score": sum(
                        venue["coverage_pct"] for venue in window_coverage.values()
                    )
                    / total_venues,
                }

                if (
                    best_window is None
                    or window_info["quality_score"] > best_window["quality_score"]
                ):
                    best_window = window_info
                    print(
                        f"      ✅ Found {window_minutes}-min window: {current_start.isoformat()} to {current_end.isoformat()}"
                    )
                    print(
                        f"         Quality: {window_info['quality_score']:.3f}, Venues: {total_venues}"
                    )

            # Move to next window (slide by 15 minutes)
            current_start += timedelta(minutes=15)

        if best_window:
            break  # Found a good window, no need to try smaller sizes

    if best_window is None:
        return {
            "status": "no_suitable_window",
            "message": "No suitable overlapping window found",
            "venue_ranges": venue_ranges,
            "common_start": common_start.isoformat(),
            "common_end": common_end.isoformat(),
        }

    # Convert venue_ranges to serializable format
    venue_ranges_serializable = {}
    for symbol, tr in venue_ranges.items():
        venue_ranges_serializable[symbol] = {
            "start": tr["start"].isoformat(),
            "end": tr["end"].isoformat(),
            "n_bars": tr["n_bars"],
        }

    return {
        "status": "success",
        "best_window": best_window,
        "venue_ranges": venue_ranges_serializable,
        "common_start": common_start.isoformat(),
        "common_end": common_end.isoformat(),
    }


def main():
    print("🔍 COINAPI PHASE 1 - BUILD COMMON 1-HOUR WINDOW")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load OHLCV data for all venues
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    ohlcv_data = {}

    print("📊 Loading OHLCV data...")
    for symbol in symbols:
        print(f"   📊 Loading {symbol}...")
        df = load_coinapi_ohlcv(s3_client, bucket, date, symbol)
        if df is not None:
            ohlcv_data[symbol] = df
            print(f"      ✅ {len(df)} bars")
        else:
            print(f"      ❌ No data")

    if len(ohlcv_data) < 2:
        print("❌ Insufficient data for overlap analysis")
        return

    print(f"\n🔍 Finding overlap window...")
    overlap_result = find_overlap_window(ohlcv_data)

    if overlap_result["status"] == "success":
        best_window = overlap_result["best_window"]
        print(f"   ✅ Found {best_window['window_size_minutes']}-minute window")
        print(f"   🎯 Time: {best_window['start']} to {best_window['end']}")
        print(f"   📊 Venues: {best_window['total_venues']}")
        print(f"   📊 Quality: {best_window['quality_score']:.3f}")

        print(f"\n   📊 Coverage details:")
        for symbol, coverage in best_window["coverage"].items():
            print(
                f"      {symbol}: {coverage['n_bars']} bars ({coverage['coverage_pct']:.1%} coverage)"
            )

        # Save overlap window results
        output_key = f"analysis/coinapi/_align/overlap_window.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=json.dumps(overlap_result, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"\n   💾 Saved overlap window: s3://{bucket}/{output_key}")

    else:
        print(f"   ❌ {overlap_result['message']}")
        if "venue_ranges" in overlap_result:
            print(f"   📊 Venue time ranges:")
            for symbol, tr in overlap_result["venue_ranges"].items():
                print(
                    f"      {symbol}: {tr['start'].isoformat()} to {tr['end'].isoformat()} ({tr['n_bars']} bars)"
                )

        # Save failure report
        output_key = f"analysis/coinapi/_align/overlap_window_failed.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=json.dumps(overlap_result, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"\n   💾 Saved failure report: s3://{bucket}/{output_key}")
        return

    print(f"\n✅ PHASE 1 COMPLETE")
    print("=" * 80)
    print("📁 Generated artifacts:")
    print(f"  - Overlap window: s3://{bucket}/analysis/coinapi/_align/overlap_window.json")


if __name__ == "__main__":
    main()
