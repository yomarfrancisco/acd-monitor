#!/usr/bin/env python3
"""
CoinAPI ACD Signal Analysis

Perform ACD signal analysis on the collected CoinAPI data.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd
from scipy import stats


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


def load_coinapi_data(
    s3_client, bucket: str, date: str, symbol: str, data_type: str
) -> Optional[pd.DataFrame]:
    """Load CoinAPI data from S3."""
    key = f"coinapi_bf1/{data_type}/{date}/{symbol}/part-0000.parquet"
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


def create_aligned_dataset(
    ohlcv_data: Dict[str, pd.DataFrame], start_time: str, end_time: str
) -> Dict[str, pd.DataFrame]:
    """Create aligned dataset for the specified time window."""
    start_dt = pd.to_datetime(start_time)
    end_dt = pd.to_datetime(end_time)

    aligned_data = {}

    for symbol, df in ohlcv_data.items():
        if df.empty:
            continue

        # Filter to time window
        window_data = df[
            (df["time_period_start"] >= start_dt) & (df["time_period_end"] <= end_dt)
        ].copy()

        if not window_data.empty:
            # Sort by time and create price series
            window_data = window_data.sort_values("time_period_start")
            window_data["timestamp"] = window_data["time_period_start"]
            window_data["price"] = window_data["price_close"]
            window_data["venue"] = symbol.split("_")[0].lower()

            aligned_data[symbol] = window_data[["timestamp", "price", "venue"]].copy()

    return aligned_data


def compute_acd_signals(aligned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute ACD signals from aligned data."""
    if len(aligned_data) < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    signals = {
        "status": "success",
        "n_venues": len(aligned_data),
        "time_window": {"start": None, "end": None, "duration_hours": 0},
        "price_correlations": {},
        "volatility_analysis": {},
        "spread_analysis": {},
        "leader_follower": {},
        "summary": {},
    }

    # Get time window
    all_times = []
    for df in aligned_data.values():
        all_times.extend(df["timestamp"].tolist())

    if all_times:
        signals["time_window"]["start"] = min(all_times).isoformat()
        signals["time_window"]["end"] = max(all_times).isoformat()
        signals["time_window"]["duration_hours"] = (
            max(all_times) - min(all_times)
        ).total_seconds() / 3600

    # Price correlations
    symbols = list(aligned_data.keys())
    for i, symbol1 in enumerate(symbols):
        for symbol2 in symbols[i + 1 :]:
            df1 = aligned_data[symbol1]
            df2 = aligned_data[symbol2]

            # Align by timestamp (inner join)
            merged = pd.merge(df1, df2, on="timestamp", suffixes=("_1", "_2"))

            if len(merged) > 10:  # Need sufficient data points
                corr = merged["price_1"].corr(merged["price_2"])
                signals["price_correlations"][f"{symbol1}_vs_{symbol2}"] = {
                    "correlation": float(corr) if not pd.isna(corr) else None,
                    "n_points": len(merged),
                }

    # Volatility analysis
    for symbol, df in aligned_data.items():
        if len(df) > 1:
            returns = df["price"].pct_change().dropna()
            volatility = returns.std()

            signals["volatility_analysis"][symbol] = {
                "volatility": float(volatility) if not pd.isna(volatility) else None,
                "mean_return": float(returns.mean()) if not pd.isna(returns.mean()) else None,
                "n_observations": len(returns),
            }

    # Spread analysis
    if len(aligned_data) >= 2:
        # Get common timestamps
        common_times = set(aligned_data[list(aligned_data.keys())[0]]["timestamp"])
        for df in aligned_data.values():
            common_times = common_times.intersection(set(df["timestamp"]))

        if common_times:
            # Create price matrix
            price_matrix = {}
            for symbol, df in aligned_data.items():
                df_filtered = df[df["timestamp"].isin(common_times)].sort_values("timestamp")
                price_matrix[symbol] = df_filtered["price"].values

            if len(price_matrix) >= 2:
                # Calculate spreads
                symbols_list = list(price_matrix.keys())
                spreads = []

                for i, symbol1 in enumerate(symbols_list):
                    for symbol2 in symbols_list[i + 1 :]:
                        prices1 = price_matrix[symbol1]
                        prices2 = price_matrix[symbol2]

                        if len(prices1) == len(prices2):
                            spread_pct = np.abs(prices1 - prices2) / prices2 * 100
                            spreads.extend(spread_pct)

                if spreads:
                    signals["spread_analysis"] = {
                        "mean_spread_pct": float(np.mean(spreads)),
                        "max_spread_pct": float(np.max(spreads)),
                        "std_spread_pct": float(np.std(spreads)),
                        "n_observations": len(spreads),
                    }

    # Leader-follower analysis (simplified)
    if len(aligned_data) >= 2:
        symbols_list = list(aligned_data.keys())
        for i, symbol1 in enumerate(symbols_list):
            for symbol2 in symbols_list[i + 1 :]:
                df1 = aligned_data[symbol1]
                df2 = aligned_data[symbol2]

                # Align by timestamp
                merged = pd.merge(df1, df2, on="timestamp", suffixes=("_1", "_2"))

                if len(merged) > 10:
                    # Simple lead-lag correlation
                    returns1 = merged["price_1"].pct_change().dropna()
                    returns2 = merged["price_2"].pct_change().dropna()

                    if len(returns1) == len(returns2) and len(returns1) > 5:
                        # Lag correlations
                        lag_corrs = {}
                        for lag in range(-3, 4):  # -3 to +3 lags
                            if lag == 0:
                                corr = returns1.corr(returns2)
                            elif lag > 0:
                                if len(returns1) > lag:
                                    corr = returns1[:-lag].corr(returns2[lag:])
                                else:
                                    corr = None
                            else:  # lag < 0
                                if len(returns2) > abs(lag):
                                    corr = returns1[abs(lag) :].corr(returns2[: -abs(lag)])
                                else:
                                    corr = None

                            lag_corrs[lag] = (
                                float(corr) if not pd.isna(corr) and corr is not None else None
                            )

                        # Find best lag
                        valid_corrs = {k: v for k, v in lag_corrs.items() if v is not None}
                        if valid_corrs:
                            best_lag = max(valid_corrs.keys(), key=lambda k: abs(valid_corrs[k]))
                            best_corr = valid_corrs[best_lag]

                            signals["leader_follower"][f"{symbol1}_vs_{symbol2}"] = {
                                "best_lag": best_lag,
                                "best_correlation": best_corr,
                                "all_lags": lag_corrs,
                            }

    # Summary
    signals["summary"] = {
        "n_venues": len(aligned_data),
        "time_span_hours": signals["time_window"]["duration_hours"],
        "n_correlations": len(signals["price_correlations"]),
        "n_volatility_measures": len(signals["volatility_analysis"]),
        "has_spread_analysis": bool(signals["spread_analysis"]),
        "n_leader_follower_pairs": len(signals["leader_follower"]),
    }

    return signals


def main():
    print("🔍 COINAPI ACD SIGNAL ANALYSIS")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load OHLCV data
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    ohlcv_data = {}

    print(f"📅 Loading data for date: {date}")

    for symbol in symbols:
        print(f"📊 Loading {symbol}...")
        df = load_coinapi_data(s3_client, bucket, date, symbol, "ohlcv")
        if df is not None:
            ohlcv_data[symbol] = df
            print(f"   ✅ {len(df)} records")
        else:
            print(f"   ❌ No data")

    if len(ohlcv_data) < 2:
        print("❌ Insufficient data for ACD analysis")
        return

    # Use the best 1-hour window (first hour of data)
    print(f"\n🔍 Creating aligned dataset...")

    # Find common time range
    all_starts = [df["time_period_start"].min() for df in ohlcv_data.values()]
    all_ends = [df["time_period_end"].max() for df in ohlcv_data.values()]

    common_start = max(all_starts)
    common_end = min(all_ends)

    # Use first hour of common data
    window_start = common_start
    window_end = common_start + timedelta(hours=1)

    if window_end > common_end:
        window_end = common_end

    print(f"   🎯 Window: {window_start.isoformat()} to {window_end.isoformat()}")

    # Create aligned dataset
    aligned_data = create_aligned_dataset(
        ohlcv_data, window_start.isoformat(), window_end.isoformat()
    )

    print(f"   ✅ Aligned {len(aligned_data)} venues")
    for symbol, df in aligned_data.items():
        print(f"      - {symbol}: {len(df)} records")

    # Compute ACD signals
    print(f"\n🔍 Computing ACD signals...")
    signals = compute_acd_signals(aligned_data)

    if signals["status"] == "success":
        print(f"   ✅ Analysis complete")
        print(f"   📊 Time span: {signals['time_window']['duration_hours']:.1f} hours")
        print(f"   📊 Correlations: {signals['summary']['n_correlations']}")
        print(f"   📊 Volatility measures: {signals['summary']['n_volatility_measures']}")
        print(f"   📊 Leader-follower pairs: {signals['summary']['n_leader_follower_pairs']}")

        # Print key findings
        if signals["price_correlations"]:
            print(f"\n📊 PRICE CORRELATIONS:")
            for pair, data in signals["price_correlations"].items():
                if data["correlation"] is not None:
                    print(f"   {pair}: {data['correlation']:.3f} ({data['n_points']} points)")

        if signals["spread_analysis"]:
            spread = signals["spread_analysis"]
            print(f"\n📊 SPREAD ANALYSIS:")
            print(f"   Mean spread: {spread['mean_spread_pct']:.3f}%")
            print(f"   Max spread: {spread['max_spread_pct']:.3f}%")
            print(f"   Std spread: {spread['std_spread_pct']:.3f}%")

        if signals["leader_follower"]:
            print(f"\n📊 LEADER-FOLLOWER ANALYSIS:")
            for pair, data in signals["leader_follower"].items():
                print(f"   {pair}: lag {data['best_lag']}, corr {data['best_correlation']:.3f}")
    else:
        print(f"   ❌ Analysis failed: {signals.get('message', 'Unknown error')}")

    # Save results
    results = {
        "date": date,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "aligned_data_summary": {
            symbol: {"n_records": len(df), "venue": df["venue"].iloc[0] if not df.empty else None}
            for symbol, df in aligned_data.items()
        },
        "signals": signals,
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"coinapi_bf1/analysis/{date}/acd_signals.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"\n💾 Saved results to s3://{bucket}/{results_key}")


if __name__ == "__main__":
    main()
