#!/usr/bin/env python3
"""
CoinAPI 1-Second ACD Analysis

Re-run ACD analysis with 1-second granular candle data for much better precision.
"""

import json
import os
import tempfile
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr

warnings.filterwarnings("ignore")


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


def compute_1sec_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 1-second returns: r_t = ln(close_t / close_{t-1})."""
    df = df.copy()

    # Sort by timestamp to ensure proper order
    df = df.sort_values("time_period_start").reset_index(drop=True)

    # Compute log returns
    df["returns"] = np.log(df["price_close"] / df["price_close"].shift(1))

    # Remove first row (no previous price)
    df = df.dropna(subset=["returns"]).reset_index(drop=True)

    return df


def compute_1sec_correlation_matrix(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute correlation matrix for 1-second returns."""
    symbols = list(returns_data.keys())
    n_venues = len(symbols)

    if n_venues < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    # Align returns by timestamp
    aligned_data = {}
    for symbol, df in returns_data.items():
        df_sorted = df.sort_values("time_period_start")
        aligned_data[symbol] = df_sorted["returns"].values

    # Find common length (minimum length across all venues)
    min_length = min(len(returns) for returns in aligned_data.values())

    # Truncate all series to common length
    for symbol in aligned_data:
        aligned_data[symbol] = aligned_data[symbol][:min_length]

    # Compute correlation matrix
    correlation_matrix = {}

    for i, symbol1 in enumerate(symbols):
        for j, symbol2 in enumerate(symbols):
            if i < j:  # Only compute upper triangle
                x = aligned_data[symbol1]
                y = aligned_data[symbol2]

                # Pearson correlation
                pearson_corr = np.corrcoef(x, y)[0, 1]

                # Spearman correlation
                spearman_corr, _ = spearmanr(x, y)

                correlation_matrix[f"{symbol1}_vs_{symbol2}"] = {
                    "pearson": float(pearson_corr) if not np.isnan(pearson_corr) else None,
                    "spearman": float(spearman_corr) if not np.isnan(spearman_corr) else None,
                    "n_points": min_length,
                }

    return {
        "status": "success",
        "n_venues": n_venues,
        "common_length": min_length,
        "granularity": "1SEC",
        "correlations": correlation_matrix,
    }


def compute_1sec_lead_lag_analysis(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute lead-lag analysis for 1-second returns with second-level precision."""
    symbols = list(returns_data.keys())
    n_venues = len(symbols)

    if n_venues < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    # Align returns by timestamp
    aligned_data = {}
    for symbol, df in returns_data.items():
        df_sorted = df.sort_values("time_period_start")
        aligned_data[symbol] = df_sorted["returns"].values

    # Find common length
    min_length = min(len(returns) for returns in aligned_data.values())

    # Truncate all series to common length
    for symbol in aligned_data:
        aligned_data[symbol] = aligned_data[symbol][:min_length]

    lead_lag_results = {}

    for i, symbol1 in enumerate(symbols):
        for j, symbol2 in enumerate(symbols):
            if i != j:  # Don't correlate with self
                x = aligned_data[symbol1]
                y = aligned_data[symbol2]

                # Compute cross-correlation at lags -10 to +10 seconds
                lags = list(range(-10, 11))
                lag_correlations = {}

                for lag in lags:
                    if lag == 0:
                        corr = np.corrcoef(x, y)[0, 1]
                    elif lag > 0:
                        if len(x) > lag:
                            corr = np.corrcoef(x[:-lag], y[lag:])[0, 1]
                        else:
                            corr = np.nan
                    else:  # lag < 0
                        if len(y) > abs(lag):
                            corr = np.corrcoef(x[abs(lag) :], y[: -abs(lag)])[0, 1]
                        else:
                            corr = np.nan

                    lag_correlations[lag] = float(corr) if not np.isnan(corr) else None

                # Find best lag
                valid_corrs = {k: v for k, v in lag_correlations.items() if v is not None}
                if valid_corrs:
                    best_lag = max(valid_corrs.keys(), key=lambda k: abs(valid_corrs[k]))
                    best_corr = valid_corrs[best_lag]

                    lead_lag_results[f"{symbol1}_vs_{symbol2}"] = {
                        "best_lag_seconds": best_lag,
                        "best_correlation": best_corr,
                        "all_lags": lag_correlations,
                        "n_points": min_length,
                    }

    return {
        "status": "success",
        "n_venues": n_venues,
        "common_length": min_length,
        "granularity": "1SEC",
        "lead_lag_pairs": lead_lag_results,
    }


def compute_1sec_spread_analysis(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute spread analysis for 1-second data."""
    symbols = list(returns_data.keys())
    n_venues = len(symbols)

    if n_venues < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    # Align price data by timestamp
    aligned_prices = {}
    for symbol, df in returns_data.items():
        df_sorted = df.sort_values("time_period_start")
        aligned_prices[symbol] = df_sorted["price_close"].values

    # Find common length
    min_length = min(len(prices) for prices in aligned_prices.values())

    # Truncate all series to common length
    for symbol in aligned_prices:
        aligned_prices[symbol] = aligned_prices[symbol][:min_length]

    # Compute pairwise spreads
    spread_results = {}

    for i, symbol1 in enumerate(symbols):
        for j, symbol2 in enumerate(symbols):
            if i < j:  # Only compute upper triangle
                prices1 = aligned_prices[symbol1]
                prices2 = aligned_prices[symbol2]

                # Compute absolute percentage spreads
                spreads_pct = np.abs(prices1 - prices2) / prices2 * 100

                spread_results[f"{symbol1}_vs_{symbol2}"] = {
                    "mean_spread_pct": float(np.mean(spreads_pct)),
                    "median_spread_pct": float(np.median(spreads_pct)),
                    "std_spread_pct": float(np.std(spreads_pct)),
                    "max_spread_pct": float(np.max(spreads_pct)),
                    "min_spread_pct": float(np.min(spreads_pct)),
                    "n_observations": len(spreads_pct),
                }

    # Overall spread statistics
    all_spreads = []
    for result in spread_results.values():
        all_spreads.extend([result["mean_spread_pct"]] * result["n_observations"])

    overall_stats = {
        "mean_spread_pct": float(np.mean(all_spreads)),
        "median_spread_pct": float(np.median(all_spreads)),
        "std_spread_pct": float(np.std(all_spreads)),
        "max_spread_pct": float(np.max(all_spreads)),
        "min_spread_pct": float(np.min(all_spreads)),
    }

    return {
        "status": "success",
        "n_venues": n_venues,
        "common_length": min_length,
        "granularity": "1SEC",
        "pairwise_spreads": spread_results,
        "overall_stats": overall_stats,
    }


def compute_1sec_volatility_co_movement(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute volatility co-movement for 1-second data with shorter windows."""
    symbols = list(returns_data.keys())
    n_venues = len(symbols)

    if n_venues < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    # Compute rolling variance for each venue with shorter windows
    rolling_vars = {}
    window_size = 30  # 30-second window for 1-second data

    for symbol, df in returns_data.items():
        df_sorted = df.sort_values("time_period_start")
        returns = df_sorted["returns"].values

        # Compute rolling variance
        rolling_var = []
        for i in range(len(returns)):
            start_idx = max(0, i - window_size + 1)
            end_idx = i + 1
            window_returns = returns[start_idx:end_idx]
            if len(window_returns) > 1:
                rolling_var.append(np.var(window_returns))
            else:
                rolling_var.append(0.0)

        rolling_vars[symbol] = np.array(rolling_var)

    # Find common length
    min_length = min(len(rv) for rv in rolling_vars.values())

    # Truncate all series to common length
    for symbol in rolling_vars:
        rolling_vars[symbol] = rolling_vars[symbol][:min_length]

    # Compute correlations between rolling variances
    vol_correlations = {}

    for i, symbol1 in enumerate(symbols):
        for j, symbol2 in enumerate(symbols):
            if i < j:  # Only compute upper triangle
                var1 = rolling_vars[symbol1]
                var2 = rolling_vars[symbol2]

                # Remove zeros and compute correlation
                valid_mask = (var1 > 0) & (var2 > 0)
                if np.sum(valid_mask) > 10:  # Need sufficient data points
                    corr = np.corrcoef(var1[valid_mask], var2[valid_mask])[0, 1]
                    vol_correlations[f"{symbol1}_vs_{symbol2}"] = {
                        "correlation": float(corr) if not np.isnan(corr) else None,
                        "n_valid_points": int(np.sum(valid_mask)),
                        "n_total_points": len(var1),
                    }
                else:
                    vol_correlations[f"{symbol1}_vs_{symbol2}"] = {
                        "correlation": None,
                        "n_valid_points": int(np.sum(valid_mask)),
                        "n_total_points": len(var1),
                    }

    return {
        "status": "success",
        "n_venues": n_venues,
        "window_size_seconds": window_size,
        "common_length": min_length,
        "granularity": "1SEC",
        "volatility_correlations": vol_correlations,
    }


def main():
    print("🔍 COINAPI 1-SECOND ACD ANALYSIS")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load 1-second candle data
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    candle_data = {}

    print("📊 Loading 1-second candle data...")
    for symbol in symbols:
        print(f"   📊 Loading {symbol}...")
        df = load_1sec_candles(s3_client, bucket, date, symbol)
        if df is not None:
            candle_data[symbol] = df
            print(f"      ✅ {len(df)} candles")
        else:
            print(f"      ❌ No data")

    if len(candle_data) < 2:
        print("❌ Insufficient data for 1-second ACD analysis")
        return

    print(f"\n✅ Loaded {len(candle_data)} venues with 1-second granularity")

    # Compute returns for each venue
    print(f"\n📊 Computing 1-second returns...")
    returns_data = {}
    for symbol, df in candle_data.items():
        returns_df = compute_1sec_returns(df)
        returns_data[symbol] = returns_df
        print(f"   {symbol}: {len(returns_df)} returns")

    # Compute ACD primitives
    results = {
        "window": {"start": "2025-09-25T00:00:00+00:00", "end": "2025-09-25T01:00:00+00:00"},
        "granularity": "1SEC",
        "venues": list(returns_data.keys()),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Correlation matrix
    print(f"\n📊 Computing 1-second correlation matrix...")
    corr_results = compute_1sec_correlation_matrix(returns_data)
    results["correlations"] = corr_results

    if corr_results["status"] == "success":
        print(
            f"   ✅ {corr_results['n_venues']} venues, {corr_results['common_length']} observations"
        )
        for pair, data in corr_results["correlations"].items():
            print(f"      {pair}: Pearson {data['pearson']:.3f}, Spearman {data['spearman']:.3f}")

    # 2. Lead-lag analysis
    print(f"\n📊 Computing 1-second lead-lag analysis...")
    lead_lag_results = compute_1sec_lead_lag_analysis(returns_data)
    results["lead_lag"] = lead_lag_results

    if lead_lag_results["status"] == "success":
        print(f"   ✅ {lead_lag_results['n_venues']} venues")
        for pair, data in lead_lag_results["lead_lag_pairs"].items():
            print(
                f"      {pair}: lag {data['best_lag_seconds']}s, corr {data['best_correlation']:.3f}"
            )

    # 3. Spread analysis
    print(f"\n📊 Computing 1-second spread analysis...")
    spread_results = compute_1sec_spread_analysis(returns_data)
    results["spreads"] = spread_results

    if spread_results["status"] == "success":
        overall = spread_results["overall_stats"]
        print(f"   ✅ Mean spread: {overall['mean_spread_pct']:.3f}%")
        print(f"   ✅ Max spread: {overall['max_spread_pct']:.3f}%")

    # 4. Volatility co-movement
    print(f"\n📊 Computing 1-second volatility co-movement...")
    vol_results = compute_1sec_volatility_co_movement(returns_data)
    results["volatility"] = vol_results

    if vol_results["status"] == "success":
        print(
            f"   ✅ {vol_results['n_venues']} venues, {vol_results['window_size_seconds']}-sec window"
        )
        for pair, data in vol_results["volatility_correlations"].items():
            if data["correlation"] is not None:
                print(f"      {pair}: {data['correlation']:.3f}")

    # Save results
    print(f"\n💾 Saving 1-second ACD results...")

    # Save individual results
    for analysis_type, data in [
        ("corr_1sec", corr_results),
        ("leadlag_1sec", lead_lag_results),
        ("spreads_1sec", spread_results),
        ("vol_co_move_1sec", vol_results),
    ]:
        if data["status"] == "success":
            key = f"analysis/coinapi/_sig_1sec/{analysis_type}.json"
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(data, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            print(f"   💾 Saved {analysis_type}: s3://{bucket}/{key}")

    # Save combined results
    combined_key = f"analysis/coinapi/_sig_1sec/combined_results_1sec.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=combined_key,
        Body=json.dumps(results, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"   💾 Saved combined results: s3://{bucket}/{combined_key}")

    print(f"\n✅ 1-SECOND ACD ANALYSIS COMPLETE")
    print("=" * 80)
    print("📁 Generated artifacts:")
    print(
        f"  - 1-second correlation matrix: s3://{bucket}/analysis/coinapi/_sig_1sec/corr_1sec.json"
    )
    print(
        f"  - 1-second lead-lag analysis: s3://{bucket}/analysis/coinapi/_sig_1sec/leadlag_1sec.json"
    )
    print(
        f"  - 1-second spread analysis: s3://{bucket}/analysis/coinapi/_sig_1sec/spreads_1sec.json"
    )
    print(
        f"  - 1-second volatility co-movement: s3://{bucket}/analysis/coinapi/_sig_1sec/vol_co_move_1sec.json"
    )
    print(f"  - Combined 1-second results: s3://{bucket}/{combined_key}")


if __name__ == "__main__":
    main()
