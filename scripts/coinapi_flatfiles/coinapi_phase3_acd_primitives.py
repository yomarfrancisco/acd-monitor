#!/usr/bin/env python3
"""
CoinAPI Phase 3 - Cross-venue ACD Primitives

Compute correlation matrix, lead-lag analysis, spread realism, and volatility co-movement.
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


def load_returns_data(s3_client, bucket: str, symbol: str) -> Optional[pd.DataFrame]:
    """Load returns data for a venue."""
    key = f"analysis/coinapi/_cln/returns_{symbol}.parquet"
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


def block_bootstrap_correlation(
    x: np.ndarray, y: np.ndarray, block_length: int = 5, n_bootstrap: int = 1000
) -> Dict[str, float]:
    """Compute correlation with 95% CI via block bootstrap."""
    n = len(x)
    if n < block_length * 2:
        return {"correlation": np.corrcoef(x, y)[0, 1], "ci_lower": np.nan, "ci_upper": np.nan}

    # Compute original correlation
    original_corr = np.corrcoef(x, y)[0, 1]

    # Block bootstrap
    bootstrap_corrs = []
    n_blocks = n // block_length

    for _ in range(n_bootstrap):
        # Sample blocks with replacement
        block_indices = np.random.choice(n_blocks, n_blocks, replace=True)

        # Reconstruct series
        x_boot = []
        y_boot = []

        for block_idx in block_indices:
            start_idx = block_idx * block_length
            end_idx = min(start_idx + block_length, n)
            x_boot.extend(x[start_idx:end_idx])
            y_boot.extend(y[start_idx:end_idx])

        # Compute correlation for this bootstrap sample
        if len(x_boot) > 1 and len(y_boot) > 1:
            corr = np.corrcoef(x_boot, y_boot)[0, 1]
            if not np.isnan(corr):
                bootstrap_corrs.append(corr)

    if len(bootstrap_corrs) < 10:
        return {"correlation": original_corr, "ci_lower": np.nan, "ci_upper": np.nan}

    # Compute 95% CI
    ci_lower = np.percentile(bootstrap_corrs, 2.5)
    ci_upper = np.percentile(bootstrap_corrs, 97.5)

    return {
        "correlation": float(original_corr),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "n_bootstrap": len(bootstrap_corrs),
    }


def compute_correlation_matrix(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute correlation matrix with confidence intervals."""
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

                # Pearson correlation with bootstrap CI
                pearson_result = block_bootstrap_correlation(x, y, block_length=5, n_bootstrap=1000)

                # Spearman correlation
                spearman_corr, _ = spearmanr(x, y)

                correlation_matrix[f"{symbol1}_vs_{symbol2}"] = {
                    "pearson": pearson_result,
                    "spearman": float(spearman_corr) if not np.isnan(spearman_corr) else None,
                    "n_points": min_length,
                }

    return {
        "status": "success",
        "n_venues": n_venues,
        "common_length": min_length,
        "correlations": correlation_matrix,
    }


def compute_lead_lag_analysis(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute lead-lag analysis with cross-correlation at integer minute lags."""
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

                # Compute cross-correlation at lags -3 to +3
                lags = list(range(-3, 4))
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
                        "best_lag": best_lag,
                        "best_correlation": best_corr,
                        "all_lags": lag_correlations,
                        "n_points": min_length,
                    }

    return {
        "status": "success",
        "n_venues": n_venues,
        "common_length": min_length,
        "lead_lag_pairs": lead_lag_results,
    }


def compute_spread_analysis(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute spread realism on price levels."""
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
        "pairwise_spreads": spread_results,
        "overall_stats": overall_stats,
    }


def compute_volatility_co_movement(returns_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute correlation of rolling 5-minute realized variance."""
    symbols = list(returns_data.keys())
    n_venues = len(symbols)

    if n_venues < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 venues"}

    # Compute rolling variance for each venue
    rolling_vars = {}
    window_size = 5  # 5-minute window

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
                if np.sum(valid_mask) > 5:  # Need sufficient data points
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
        "window_size": window_size,
        "common_length": min_length,
        "volatility_correlations": vol_correlations,
    }


def generate_summary_markdown(results: Dict[str, Any]) -> str:
    """Generate markdown summary of ACD analysis."""
    summary = f"""# CoinAPI ACD Analysis Summary

## Analysis Overview
- **Data Source**: CoinAPI REST OHLCV (1-minute aggregated candles)
- **Time Window**: {results.get('window', {}).get('start', 'N/A')} to {results.get('window', {}).get('end', 'N/A')}
- **Venues**: {', '.join(results.get('venues', []))}
- **Analysis Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Key Findings

### Correlation Analysis
"""

    if "correlations" in results:
        corr_data = results["correlations"]
        summary += f"- **Venues**: {corr_data.get('n_venues', 'N/A')}\n"
        summary += f"- **Common Length**: {corr_data.get('common_length', 'N/A')} observations\n\n"

        for pair, data in corr_data.get("correlations", {}).items():
            pearson = data.get("pearson", {})
            summary += f"**{pair}**:\n"
            summary += f"- Pearson: {pearson.get('correlation', 'N/A'):.3f} (CI: {pearson.get('ci_lower', 'N/A'):.3f} - {pearson.get('ci_upper', 'N/A'):.3f})\n"
            summary += f"- Spearman: {data.get('spearman', 'N/A'):.3f}\n\n"

    if "lead_lag" in results:
        lead_lag_data = results["lead_lag"]
        summary += "### Lead-Lag Analysis\n"
        for pair, data in lead_lag_data.get("lead_lag_pairs", {}).items():
            summary += f"**{pair}**:\n"
            summary += f"- Best lag: {data.get('best_lag', 'N/A')} minutes\n"
            summary += f"- Best correlation: {data.get('best_correlation', 'N/A'):.3f}\n\n"

    if "spreads" in results:
        spread_data = results["spreads"]
        summary += "### Spread Analysis\n"
        overall = spread_data.get("overall_stats", {})
        summary += f"- Mean spread: {overall.get('mean_spread_pct', 'N/A'):.3f}%\n"
        summary += f"- Max spread: {overall.get('max_spread_pct', 'N/A'):.3f}%\n\n"

    if "volatility" in results:
        vol_data = results["volatility"]
        summary += "### Volatility Co-movement\n"
        for pair, data in vol_data.get("volatility_correlations", {}).items():
            summary += f"**{pair}**: {data.get('correlation', 'N/A'):.3f}\n"

    summary += """
## Important Caveats
- **Data Type**: This analysis uses OHLCV minute data (aggregated), not raw trade ticks
- **Regular Intervals**: 1-minute candles have regular timing by design
- **Correlation Interpretation**: High correlations on returns may indicate market efficiency rather than coordination
- **Lead-Lag**: Small lags (±1-2 minutes) are expected in efficient markets

## Methodology Notes
- Returns computed as log returns: r_t = ln(close_t / close_{t-1})
- Correlations computed with 95% confidence intervals via block bootstrap
- Lead-lag analysis uses cross-correlation at integer minute lags
- Spread analysis computed on price levels (not returns)
- Volatility co-movement uses rolling 5-minute realized variance
"""

    return summary


def main():
    print("🔍 COINAPI PHASE 3 - CROSS-VENUE ACD PRIMITIVES")
    print("=" * 80)

    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")

    s3_client = boto3.client("s3")

    # Load returns data
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    returns_data = {}

    print("📊 Loading returns data...")
    for symbol in symbols:
        print(f"   📊 Loading {symbol}...")
        df = load_returns_data(s3_client, bucket, symbol)
        if df is not None:
            returns_data[symbol] = df
            print(f"      ✅ {len(df)} returns")
        else:
            print(f"      ❌ No data")

    if len(returns_data) < 2:
        print("❌ Insufficient data for ACD analysis")
        return

    print(f"\n✅ Loaded {len(returns_data)} venues: {', '.join(returns_data.keys())}")

    # Compute ACD primitives
    results = {
        "window": {"start": "2025-09-25T00:00:00+00:00", "end": "2025-09-25T01:00:00+00:00"},
        "venues": list(returns_data.keys()),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Correlation matrix
    print(f"\n📊 Computing correlation matrix...")
    corr_results = compute_correlation_matrix(returns_data)
    results["correlations"] = corr_results

    if corr_results["status"] == "success":
        print(
            f"   ✅ {corr_results['n_venues']} venues, {corr_results['common_length']} observations"
        )
        for pair, data in corr_results["correlations"].items():
            pearson = data["pearson"]
            print(
                f"      {pair}: {pearson['correlation']:.3f} (CI: {pearson['ci_lower']:.3f}-{pearson['ci_upper']:.3f})"
            )

    # 2. Lead-lag analysis
    print(f"\n📊 Computing lead-lag analysis...")
    lead_lag_results = compute_lead_lag_analysis(returns_data)
    results["lead_lag"] = lead_lag_results

    if lead_lag_results["status"] == "success":
        print(f"   ✅ {lead_lag_results['n_venues']} venues")
        for pair, data in lead_lag_results["lead_lag_pairs"].items():
            print(f"      {pair}: lag {data['best_lag']}, corr {data['best_correlation']:.3f}")

    # 3. Spread analysis
    print(f"\n📊 Computing spread analysis...")
    spread_results = compute_spread_analysis(returns_data)
    results["spreads"] = spread_results

    if spread_results["status"] == "success":
        overall = spread_results["overall_stats"]
        print(f"   ✅ Mean spread: {overall['mean_spread_pct']:.3f}%")
        print(f"   ✅ Max spread: {overall['max_spread_pct']:.3f}%")

    # 4. Volatility co-movement
    print(f"\n📊 Computing volatility co-movement...")
    vol_results = compute_volatility_co_movement(returns_data)
    results["volatility"] = vol_results

    if vol_results["status"] == "success":
        print(f"   ✅ {vol_results['n_venues']} venues, {vol_results['window_size']}-min window")
        for pair, data in vol_results["volatility_correlations"].items():
            if data["correlation"] is not None:
                print(f"      {pair}: {data['correlation']:.3f}")

    # Save results
    print(f"\n💾 Saving results...")

    # Save individual results
    for analysis_type, data in [
        ("corr", corr_results),
        ("leadlag", lead_lag_results),
        ("spreads", spread_results),
        ("vol_co_move", vol_results),
    ]:
        if data["status"] == "success":
            key = f"analysis/coinapi/_sig/{analysis_type}.json"
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(data, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            print(f"   💾 Saved {analysis_type}: s3://{bucket}/{key}")

    # Save combined results
    combined_key = f"analysis/coinapi/_sig/combined_results.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=combined_key,
        Body=json.dumps(results, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"   💾 Saved combined results: s3://{bucket}/{combined_key}")

    # Generate and save markdown summary
    summary_md = generate_summary_markdown(results)
    summary_key = f"analysis/coinapi/_sig/summary.md"
    s3_client.put_object(
        Bucket=bucket, Key=summary_key, Body=summary_md.encode("utf-8"), ContentType="text/markdown"
    )
    print(f"   💾 Saved summary: s3://{bucket}/{summary_key}")

    print(f"\n✅ PHASE 3 COMPLETE")
    print("=" * 80)
    print("📁 Generated artifacts:")
    print(f"  - Correlation matrix: s3://{bucket}/analysis/coinapi/_sig/corr.json")
    print(f"  - Lead-lag analysis: s3://{bucket}/analysis/coinapi/_sig/leadlag.json")
    print(f"  - Spread analysis: s3://{bucket}/analysis/coinapi/_sig/spreads.json")
    print(f"  - Volatility co-movement: s3://{bucket}/analysis/coinapi/_sig/vol_co_move.json")
    print(f"  - Combined results: s3://{bucket}/{combined_key}")
    print(f"  - Summary report: s3://{bucket}/{summary_key}")


if __name__ == "__main__":
    main()
