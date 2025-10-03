#!/usr/bin/env python3
"""
ACD – 7-Day 1-Second Backfill via CoinAPI (Binance, Coinbase, Kraken)

Task 0-6: Complete 7-day backfill with provenance validation and analytics.
"""

import hashlib
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
import requests

# Task 0 - Config
COINAPI_KEY = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
API_BASE = "https://rest.coinapi.io/v1"
VENUES = ["BINANCE", "COINBASE", "KRAKEN"]
BUCKET = "acd-monitor-snapshots"


def setup_logging():
    """Setup logging configuration."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("coinapi_7day_backfill.log")],
    )
    return logging.getLogger(__name__)


def discover_symbols(logger) -> Dict[str, str]:
    """Task 0: Discover symbol mappings for each venue."""
    logger.info("🔍 Task 0: Discovering symbol mappings...")

    headers = {"X-CoinAPI-Key": COINAPI_KEY}
    symbols = {}

    for venue in VENUES:
        logger.info(f"   📊 Discovering symbols for {venue}...")

        url = f"{API_BASE}/symbols"
        params = {"filter_exchange_id": venue}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            venue_symbols = response.json()
            logger.info(f"   ✅ Found {len(venue_symbols)} symbols for {venue}")

            # Choose best symbol based on venue
            if venue == "BINANCE":
                # Prefer BTC/USDT spot
                btc_usdt = [
                    s for s in venue_symbols if s.get("symbol_id") == "BINANCE_SPOT_BTC_USDT"
                ]
                if btc_usdt:
                    symbols[venue] = btc_usdt[0]["symbol_id"]
                    logger.info(f"   ✅ Selected: {symbols[venue]}")
                else:
                    logger.error(f"   ❌ No BTC/USDT found for {venue}")
                    return {}
            elif venue == "COINBASE":
                # Prefer BTC/USD spot
                btc_usd = [
                    s for s in venue_symbols if s.get("symbol_id") == "COINBASE_SPOT_BTC_USD"
                ]
                if btc_usd:
                    symbols[venue] = btc_usd[0]["symbol_id"]
                    logger.info(f"   ✅ Selected: {symbols[venue]}")
                else:
                    logger.error(f"   ❌ No BTC/USD found for {venue}")
                    return {}
            elif venue == "KRAKEN":
                # Prefer XBT/USD spot (Kraken uses XBT)
                xbt_usd = [s for s in venue_symbols if s.get("symbol_id") == "KRAKEN_SPOT_BTC_USD"]
                if xbt_usd:
                    symbols[venue] = xbt_usd[0]["symbol_id"]
                    logger.info(f"   ✅ Selected: {symbols[venue]}")
                else:
                    logger.error(f"   ❌ No BTC/USD found for {venue}")
                    return {}

        except Exception as e:
            logger.error(f"   ❌ Error discovering symbols for {venue}: {e}")
            return {}

    logger.info(f"✅ Task 0 complete: {symbols}")
    return symbols


def get_time_window() -> Tuple[str, str]:
    """Task 1: Determine 7 full UTC days."""
    logger = setup_logging()
    logger.info("📅 Task 1: Determining 7-day time window...")

    # End at last fully completed UTC day
    now = datetime.now(timezone.utc)
    end_date = now.date() - timedelta(days=1)  # Yesterday (fully completed)
    start_date = end_date - timedelta(days=6)  # 7 days total

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    logger.info(f"   📊 Time window: {start_str} to {end_str} (7 days)")
    logger.info(f"   📊 Start: {start_str}T00:00:00Z")
    logger.info(f"   📊 End: {end_str}T23:59:59Z")

    return start_str, end_str


def fetch_venue_day_data(
    venue: str, symbol_id: str, date: str, logger
) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
    """Task 2: Fetch 1-second OHLCV candles for a single venue-day."""
    logger.info(f"   📊 Fetching {venue} {date}...")

    headers = {"X-CoinAPI-Key": COINAPI_KEY}
    time_start = f"{date}T00:00:00Z"
    time_end = f"{date}T23:59:59Z"

    url = f"{API_BASE}/ohlcv/{symbol_id}/history"
    params = {"period_id": "1SEC", "time_start": time_start, "time_end": time_end, "limit": 50000}

    all_candles = []
    retry_count = 0
    max_retries = 6

    while retry_count < max_retries:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.status_code == 200:
                candles = response.json()
                if not candles:
                    logger.warning(f"   ⚠️  No candles returned for {venue} {date}")
                    break

                all_candles.extend(candles)
                logger.info(f"   ✅ Retrieved {len(candles)} candles for {venue} {date}")

                # Check if we need to paginate
                if len(candles) == 50000:
                    # Update time_start to continue from last candle
                    last_time = candles[-1]["time_period_start"]
                    params["time_start"] = last_time
                    logger.info(f"   📄 Paginating from {last_time}...")
                    time.sleep(1.5)  # Rate limiting
                    continue
                else:
                    break

            elif response.status_code == 429 or response.status_code == 403:
                # Rate limited - exponential backoff
                backoff_time = min(2**retry_count, 60)
                logger.warning(f"   ⚠️  Rate limited, backing off {backoff_time}s...")
                time.sleep(backoff_time)
                retry_count += 1
                continue
            else:
                logger.error(f"   ❌ HTTP {response.status_code}: {response.text}")
                return False, {"error": f"HTTP {response.status_code}"}, None

        except Exception as e:
            logger.error(f"   ❌ Exception fetching {venue} {date}: {e}")
            return False, {"error": str(e)}, None

    if retry_count >= max_retries:
        logger.error(f"   ❌ Max retries exceeded for {venue} {date}")
        return False, {"error": "Max retries exceeded"}, None

    if not all_candles:
        logger.error(f"   ❌ No candles retrieved for {venue} {date}")
        return False, {"error": "No candles retrieved"}, None

    # Convert to DataFrame
    try:
        df = pd.DataFrame(all_candles)
        df["time_period_start"] = pd.to_datetime(df["time_period_start"])
        df = df.sort_values("time_period_start").reset_index(drop=True)

        # Calculate SHA256 for manifest
        data_hash = hashlib.sha256(df.to_string().encode()).hexdigest()

        manifest = {
            "symbol_id": symbol_id,
            "venue": venue,
            "date": date,
            "time_start": time_start,
            "time_end": time_end,
            "n_candles": len(df),
            "sha256": data_hash,
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"   ✅ {venue} {date}: {len(df)} candles, hash: {data_hash[:8]}...")
        return True, manifest, df

    except Exception as e:
        logger.error(f"   ❌ Error processing {venue} {date}: {e}")
        return False, {"error": f"Processing error: {e}"}, None


def validate_candle_data(df: pd.DataFrame, venue: str, date: str, logger) -> Dict[str, Any]:
    """Task 3: Provenance & quality checks for candle data."""
    logger.info(f"   🔍 Validating {venue} {date}...")

    qc_results = {
        "venue": venue,
        "date": date,
        "n_rows": int(len(df)),
        "status": "passed",
        "issues": [],
        "coverage_pct": 0.0,
        "ohlc_violations": 0,
        "price_sanity": True,
        "volume_sanity": True,
        "duplicates": 0,
    }

    if df.empty:
        qc_results["status"] = "failed"
        qc_results["issues"].append("Empty DataFrame")
        return qc_results

    # Expected 86,400 rows per day (allow 50% missing for realistic trading activity)
    expected_rows = 86400
    min_expected = int(expected_rows * 0.50)  # 50% minimum (realistic for 1-second data)

    if len(df) < min_expected:
        qc_results["status"] = "failed"
        qc_results["issues"].append(f"Insufficient coverage: {len(df)}/{expected_rows}")
        return qc_results

    qc_results["coverage_pct"] = float((len(df) / expected_rows) * 100)

    # Check monotonicity
    if not df["time_period_start"].is_monotonic_increasing:
        qc_results["status"] = "failed"
        qc_results["issues"].append("Non-monotonic timestamps")
        return qc_results

    # OHLC sanity checks
    ohlc_violations = 0
    for _, row in df.iterrows():
        if not (
            row["price_low"] <= row["price_open"] <= row["price_high"]
            and row["price_low"] <= row["price_close"] <= row["price_high"]
            and row["price_high"] >= row["price_low"]
        ):
            ohlc_violations += 1

    qc_results["ohlc_violations"] = int(ohlc_violations)
    if ohlc_violations > 0:
        qc_results["status"] = "failed"
        qc_results["issues"].append(f"OHLC violations: {ohlc_violations}")
        return qc_results

    # Price sanity: BTC price in [$10k, $1M]
    price_min = df["price_low"].min()
    price_max = df["price_high"].max()
    if price_min < 10000 or price_max > 1000000:
        qc_results["price_sanity"] = False
        qc_results["issues"].append(f"Price out of range: ${price_min:.2f} - ${price_max:.2f}")

    # Volume sanity: non-negative, flag extreme spikes
    volume_p99 = df["volume_traded"].quantile(0.99)
    extreme_volumes = (df["volume_traded"] > volume_p99 * 10).sum()
    if extreme_volumes > 0:
        qc_results["volume_sanity"] = False
        qc_results["issues"].append(f"Extreme volume spikes: {extreme_volumes}")

    # Duplicates check
    duplicates = df.duplicated().sum()
    qc_results["duplicates"] = int(duplicates)
    if duplicates > len(df) * 0.001:  # > 0.1%
        qc_results["status"] = "failed"
        qc_results["issues"].append(f"Too many duplicates: {duplicates}")
        return qc_results

    logger.info(
        f"   ✅ {venue} {date}: {qc_results['coverage_pct']:.1f}% coverage, {ohlc_violations} OHLC violations"
    )
    return qc_results


def save_venue_day_data(
    s3_client,
    venue: str,
    date: str,
    manifest: Dict[str, Any],
    df: pd.DataFrame,
    qc_results: Dict[str, Any],
):
    """Save venue-day data to S3."""
    logger = setup_logging()

    # Save parquet
    parquet_key = f"backfill/coinapi_1s/{venue.lower()}/{date}/candles_1s.parquet"
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
        df.to_parquet(tmp_file.name, index=False)
        s3_client.upload_file(tmp_file.name, BUCKET, parquet_key)
        Path(tmp_file.name).unlink()

    # Save manifest
    manifest_key = f"backfill/coinapi_1s/{venue.lower()}/{date}/manifest.json"
    s3_client.put_object(
        Bucket=BUCKET,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    # Save QC results
    qc_key = f"backfill/coinapi_1s/{venue.lower()}/{date}/qc.json"
    s3_client.put_object(
        Bucket=BUCKET,
        Key=qc_key,
        Body=json.dumps(qc_results, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    logger.info(f"   💾 Saved {venue} {date}: s3://{BUCKET}/{parquet_key}")


def build_aligned_panel(
    s3_client, start_date: str, end_date: str, symbols: Dict[str, str], logger
) -> Tuple[bool, Dict[str, Any]]:
    """Task 4: Build aligned 7-day panel."""
    logger.info("🔗 Task 4: Building aligned 7-day panel...")

    # Load all venue-day data
    all_data = {}
    panel_manifest = {
        "start_date": start_date,
        "end_date": end_date,
        "venues": {},
        "daily_overlaps": {},
        "overall_overlap": 0.0,
    }

    # Generate date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    date_range = [start_dt + timedelta(days=i) for i in range((end_dt - start_dt).days + 1)]

    for venue in VENUES:
        venue_data = {}
        for date in date_range:
            date_str = date.strftime("%Y-%m-%d")
            parquet_key = f"backfill/coinapi_1s/{venue.lower()}/{date_str}/candles_1s.parquet"

            try:
                response = s3_client.get_object(Bucket=BUCKET, Key=parquet_key)
                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
                    tmp_file.write(response["Body"].read())
                    tmp_file.flush()
                    df = pd.read_parquet(tmp_file.name)
                    Path(tmp_file.name).unlink()

                venue_data[date_str] = df
                logger.info(f"   ✅ Loaded {venue} {date_str}: {len(df)} candles")

            except Exception as e:
                logger.warning(f"   ⚠️  Could not load {venue} {date_str}: {e}")
                continue

        all_data[venue] = venue_data

    # Build daily overlaps
    daily_overlaps = {}
    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        date_data = {}

        for venue in VENUES:
            if date_str in all_data[venue]:
                date_data[venue] = all_data[venue][date_str]

        if len(date_data) >= 2:  # Need at least 2 venues
            # Inner join on timestamp
            aligned_data = None
            for venue, df in date_data.items():
                df_renamed = df.rename(
                    columns={
                        "price_open": f"{venue.lower()}_open",
                        "price_high": f"{venue.lower()}_high",
                        "price_low": f"{venue.lower()}_low",
                        "price_close": f"{venue.lower()}_close",
                        "volume_traded": f"{venue.lower()}_volume",
                    }
                )
                df_renamed = df_renamed[
                    ["time_period_start"]
                    + [col for col in df_renamed.columns if col != "time_period_start"]
                ]

                if aligned_data is None:
                    aligned_data = df_renamed
                else:
                    aligned_data = aligned_data.merge(
                        df_renamed, on="time_period_start", how="inner"
                    )

            daily_overlaps[date_str] = {
                "n_rows": len(aligned_data),
                "venues": list(date_data.keys()),
                "coverage_pct": (len(aligned_data) / 86400) * 100,
            }

            logger.info(
                f"   📊 {date_str}: {len(aligned_data)} aligned candles, {daily_overlaps[date_str]['coverage_pct']:.1f}% coverage"
            )

    # Build 7-day unified panel
    if daily_overlaps:
        # Use the day with best coverage as base
        best_day = max(daily_overlaps.keys(), key=lambda d: daily_overlaps[d]["coverage_pct"])
        logger.info(f"   🎯 Using {best_day} as base for unified panel")

        # Load and merge all days
        unified_panel = None
        for date in date_range:
            date_str = date.strftime("%Y-%m-%d")
            if date_str in daily_overlaps:
                # Load aligned data for this day
                date_data = {}
                for venue in VENUES:
                    if date_str in all_data[venue]:
                        date_data[venue] = all_data[venue][date_str]

                if len(date_data) >= 2:
                    # Build aligned data for this day
                    aligned_data = None
                    for venue, df in date_data.items():
                        df_renamed = df.rename(
                            columns={
                                "price_open": f"{venue.lower()}_open",
                                "price_high": f"{venue.lower()}_high",
                                "price_low": f"{venue.lower()}_low",
                                "price_close": f"{venue.lower()}_close",
                                "volume_traded": f"{venue.lower()}_volume",
                            }
                        )
                        df_renamed = df_renamed[
                            ["time_period_start"]
                            + [col for col in df_renamed.columns if col != "time_period_start"]
                        ]

                        if aligned_data is None:
                            aligned_data = df_renamed
                        else:
                            aligned_data = aligned_data.merge(
                                df_renamed, on="time_period_start", how="inner"
                            )

                    # Add to unified panel
                    if unified_panel is None:
                        unified_panel = aligned_data
                    else:
                        unified_panel = pd.concat([unified_panel, aligned_data], ignore_index=True)

        if unified_panel is not None:
            # Save unified panel
            panel_key = f"analysis/coinapi_1s/panel/candles_1s_panel.parquet"
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
                unified_panel.to_parquet(tmp_file.name, index=False)
                s3_client.upload_file(tmp_file.name, BUCKET, panel_key)
                Path(tmp_file.name).unlink()

            # Save panel manifest
            panel_manifest["daily_overlaps"] = daily_overlaps
            panel_manifest["overall_overlap"] = len(unified_panel) / (7 * 86400) * 100
            panel_manifest["n_rows"] = len(unified_panel)
            panel_manifest["start_time"] = unified_panel["time_period_start"].min().isoformat()
            panel_manifest["end_time"] = unified_panel["time_period_start"].max().isoformat()

            manifest_key = f"analysis/coinapi_1s/panel/panel_manifest.json"
            s3_client.put_object(
                Bucket=BUCKET,
                Key=manifest_key,
                Body=json.dumps(panel_manifest, indent=2).encode("utf-8"),
                ContentType="application/json",
            )

            logger.info(
                f"   ✅ Unified panel: {len(unified_panel)} rows, {panel_manifest['overall_overlap']:.1f}% coverage"
            )
            return True, panel_manifest
        else:
            logger.error("   ❌ Could not build unified panel")
            return False, {}
    else:
        logger.error("   ❌ No daily overlaps found")
        return False, {}


def compute_analytics(s3_client, logger) -> Dict[str, Any]:
    """Task 5: First-pass analytics on aligned panel."""
    logger.info("📊 Task 5: Computing first-pass analytics...")

    # Load unified panel
    panel_key = f"analysis/coinapi_1s/panel/candles_1s_panel.parquet"
    try:
        response = s3_client.get_object(Bucket=BUCKET, Key=panel_key)
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(response["Body"].read())
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()
    except Exception as e:
        logger.error(f"   ❌ Could not load panel: {e}")
        return {}

    logger.info(f"   📊 Panel loaded: {len(df)} rows")

    # Compute mid-prices
    for venue in VENUES:
        venue_lower = venue.lower()
        if f"{venue_lower}_open" in df.columns and f"{venue_lower}_close" in df.columns:
            df[f"{venue_lower}_mid"] = (df[f"{venue_lower}_open"] + df[f"{venue_lower}_close"]) / 2

    # Compute 1-second returns
    for venue in VENUES:
        venue_lower = venue.lower()
        if f"{venue_lower}_mid" in df.columns:
            df[f"{venue_lower}_return"] = np.log(
                df[f"{venue_lower}_mid"] / df[f"{venue_lower}_mid"].shift(1)
            )

    # Compute cross-venue spreads
    mid_cols = [f"{venue.lower()}_mid" for venue in VENUES if f"{venue.lower()}_mid" in df.columns]
    if len(mid_cols) >= 2:
        df["spread_max"] = df[mid_cols].max(axis=1) - df[mid_cols].min(axis=1)
        df["spread_pct"] = (df["spread_max"] / df[mid_cols].mean(axis=1)) * 100

    # Compute correlations
    return_cols = [
        f"{venue.lower()}_return" for venue in VENUES if f"{venue.lower()}_return" in df.columns
    ]
    correlations = {}
    if len(return_cols) >= 2:
        corr_matrix = df[return_cols].corr()
        correlations = corr_matrix.to_dict()

    # Compute lead-lag analysis
    lead_lag = {}
    if len(return_cols) >= 2:
        for i, col1 in enumerate(return_cols):
            for j, col2 in enumerate(return_cols):
                if i != j:
                    # Cross-correlation for lags -5 to +5
                    max_corr = 0
                    best_lag = 0
                    for lag in range(-5, 6):
                        if lag == 0:
                            corr = df[col1].corr(df[col2])
                        elif lag > 0:
                            corr = df[col1].corr(df[col2].shift(lag))
                        else:
                            corr = df[col1].shift(-lag).corr(df[col2])

                        if abs(corr) > abs(max_corr):
                            max_corr = corr
                            best_lag = lag

                    lead_lag[f"{col1}_vs_{col2}"] = {
                        "max_correlation": float(max_corr),
                        "best_lag": best_lag,
                    }

    # Compute volatility clustering
    volatility_clustering = {}
    for venue in VENUES:
        venue_lower = venue.lower()
        if f"{venue_lower}_return" in df.columns:
            returns = df[f"{venue_lower}_return"].dropna()
            squared_returns = returns**2

            # Autocorrelation of squared returns at lags 1-10
            autocorr = {}
            for lag in range(1, 11):
                if len(squared_returns) > lag:
                    autocorr[f"lag_{lag}"] = float(squared_returns.autocorr(lag=lag))

            volatility_clustering[venue_lower] = autocorr

    # Summary statistics
    summary = {
        "panel_stats": {
            "n_rows": len(df),
            "start_time": df["time_period_start"].min().isoformat(),
            "end_time": df["time_period_start"].max().isoformat(),
            "duration_hours": (
                df["time_period_start"].max() - df["time_period_start"].min()
            ).total_seconds()
            / 3600,
        },
        "spread_stats": {
            "mean_spread_pct": (
                float(df["spread_pct"].mean()) if "spread_pct" in df.columns else None
            ),
            "median_spread_pct": (
                float(df["spread_pct"].median()) if "spread_pct" in df.columns else None
            ),
            "p95_spread_pct": (
                float(df["spread_pct"].quantile(0.95)) if "spread_pct" in df.columns else None
            ),
        },
        "correlations": correlations,
        "lead_lag": lead_lag,
        "volatility_clustering": volatility_clustering,
    }

    # Save analytics
    analytics_key = f"analysis/coinapi_1s/summary/summary_1s.json"
    s3_client.put_object(
        Bucket=BUCKET,
        Key=analytics_key,
        Body=json.dumps(summary, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    # Generate markdown report
    md_report = f"""# ACD 7-Day 1-Second Analytics Summary

## Panel Statistics
- **Rows**: {summary['panel_stats']['n_rows']:,}
- **Duration**: {summary['panel_stats']['duration_hours']:.1f} hours
- **Start**: {summary['panel_stats']['start_time']}
- **End**: {summary['panel_stats']['end_time']}

## Spread Statistics
- **Mean Spread**: {summary['spread_stats']['mean_spread_pct']:.3f}%
- **Median Spread**: {summary['spread_stats']['median_spread_pct']:.3f}%
- **P95 Spread**: {summary['spread_stats']['p95_spread_pct']:.3f}%

## Cross-Venue Correlations
"""

    for venue1 in VENUES:
        for venue2 in VENUES:
            if venue1 != venue2:
                col1 = f"{venue1.lower()}_return"
                col2 = f"{venue2.lower()}_return"
                if col1 in correlations and col2 in correlations[col1]:
                    corr = correlations[col1][col2]
                    md_report += f"- **{venue1} vs {venue2}**: {corr:.4f}\n"

    md_report += "\n## Lead-Lag Analysis\n"
    for pair, stats in lead_lag.items():
        md_report += f"- **{pair}**: Max correlation {stats['max_correlation']:.4f} at lag {stats['best_lag']}\n"

    md_report += "\n## Volatility Clustering\n"
    for venue, autocorr in volatility_clustering.items():
        md_report += f"- **{venue.upper()}**: "
        for lag, corr in autocorr.items():
            md_report += f"{lag}={corr:.3f} "
        md_report += "\n"

    # Save markdown report
    md_key = f"analysis/coinapi_1s/summary/summary_1s.md"
    s3_client.put_object(
        Bucket=BUCKET, Key=md_key, Body=md_report.encode("utf-8"), ContentType="text/markdown"
    )

    logger.info(f"   ✅ Analytics saved: s3://{BUCKET}/{analytics_key}")
    return summary


def main():
    """Main execution function."""
    logger = setup_logging()
    s3_client = boto3.client("s3")

    logger.info("🚀 Starting ACD 7-Day 1-Second Backfill")
    logger.info("=" * 80)

    # Task 0: Discover symbols
    symbols = discover_symbols(logger)
    if not symbols:
        logger.error("❌ Task 0 failed: Could not discover symbols")
        return

    # Task 1: Get time window
    start_date, end_date = get_time_window()

    # Task 2 & 3: Fetch and validate data
    logger.info("📊 Task 2-3: Fetching and validating data...")

    run_log = {
        "start_timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "time_window": {"start": start_date, "end": end_date},
        "venues": {},
        "successes": 0,
        "failures": 0,
    }

    for venue in VENUES:
        venue_log = {"days": {}}
        venue_successes = 0
        venue_failures = 0

        for date in pd.date_range(start_date, end_date):
            date_str = date.strftime("%Y-%m-%d")

            success, manifest, df = fetch_venue_day_data(venue, symbols[venue], date_str, logger)

            if success and df is not None:
                qc_results = validate_candle_data(df, venue, date_str, logger)

                if qc_results["status"] == "passed":
                    save_venue_day_data(s3_client, venue, date_str, manifest, df, qc_results)
                    venue_successes += 1
                    venue_log["days"][date_str] = {"status": "success", "n_candles": len(df)}
                else:
                    venue_failures += 1
                    venue_log["days"][date_str] = {
                        "status": "failed",
                        "issues": qc_results["issues"],
                    }
            else:
                venue_failures += 1
                venue_log["days"][date_str] = {
                    "status": "failed",
                    "error": manifest.get("error", "Unknown error"),
                }

        run_log["venues"][venue] = venue_log
        run_log["successes"] += venue_successes
        run_log["failures"] += venue_failures

        logger.info(f"   📊 {venue}: {venue_successes} successes, {venue_failures} failures")

    # Task 4: Build aligned panel
    panel_success, panel_manifest = build_aligned_panel(
        s3_client, start_date, end_date, symbols, logger
    )

    if panel_success:
        run_log["panel_status"] = "success"
        run_log["panel_manifest"] = panel_manifest
    else:
        run_log["panel_status"] = "failed"

    # Task 5: Compute analytics
    if panel_success:
        analytics = compute_analytics(s3_client, logger)
        run_log["analytics"] = analytics

    # Task 6: Save run log
    run_log["end_timestamp"] = datetime.now(timezone.utc).isoformat()

    run_log_key = f"analysis/coinapi_1s/run_log.json"
    s3_client.put_object(
        Bucket=BUCKET,
        Key=run_log_key,
        Body=json.dumps(run_log, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    logger.info("✅ ACD 7-Day 1-Second Backfill Complete")
    logger.info(f"   📊 Successes: {run_log['successes']}")
    logger.info(f"   📊 Failures: {run_log['failures']}")
    logger.info(f"   📊 Panel: {'Success' if panel_success else 'Failed'}")
    logger.info(f"   💾 Run log: s3://{BUCKET}/{run_log_key}")


if __name__ == "__main__":
    main()
