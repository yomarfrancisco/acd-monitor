#!/usr/bin/env python3
"""
Coinbase BTC-USD Anomaly Quality Control Analysis

Investigates data integrity issues that might explain the Coinbase variance ratio anomaly
observed in Wave-1 tests (VR 1.5-18.4 vs 0.3-0.4 for other venues).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")

s3 = boto3.client("s3")


class CoinbaseAnomalyQC:
    """Quality control analysis for Coinbase BTC-USD anomaly."""

    def __init__(self, symbol: str, start_date: str, end_date: str):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = f"analysis/wave1/{symbol.replace('-', '_').lower()}/coinbase_qc"
        self.results = {}

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

    def run_qc_analysis(self):
        """Run comprehensive QC analysis on Coinbase data."""
        print(f"🔍 Coinbase QC Analysis for {self.symbol}")
        print("=" * 50)

        # Load Coinbase data
        coinbase_data = self._load_coinbase_data()
        if coinbase_data.empty:
            print("❌ No Coinbase data found")
            return

        print(f"📊 Loaded {len(coinbase_data)} Coinbase ticks")

        # Run QC checks
        self._check_timestamps(coinbase_data)
        self._check_duplicates(coinbase_data)
        self._check_staleness_burstiness(coinbase_data)
        self._check_spread_sanity(coinbase_data)
        self._check_schema_conformity(coinbase_data)

        # Generate summary report
        self._generate_summary_report()

        print(f"✅ QC analysis complete")
        print(f"📁 Results saved to {self.output_dir}")

    def _load_coinbase_data(self) -> pd.DataFrame:
        """Load Coinbase data for the specified date range."""
        print("📥 Loading Coinbase data...")

        # Get windows for the date range
        windows = self._get_windows_for_date_range()

        coinbase_data = []
        for window in windows:
            try:
                # Try both parquet naming conventions
                parquet_key = f"{window}/ticks/coinbase/part-00000.parquet"
                try:
                    s3.head_object(Bucket=BUCKET, Key=parquet_key)
                except:
                    parquet_key = f"{window}/ticks/coinbase/part-0000.parquet"

                parquet_uri = f"s3://{BUCKET}/{parquet_key}"
                df = pd.read_parquet(parquet_uri, storage_options={"anon": False})

                if not df.empty:
                    # Ensure canonical schema
                    df = self._standardize_schema(df)
                    coinbase_data.append(df)

            except Exception as e:
                print(f"  Warning: Could not load {window}: {e}")
                continue

        if coinbase_data:
            combined_df = pd.concat(coinbase_data, ignore_index=True)
            combined_df = combined_df.sort_values("ts_exchange").reset_index(drop=True)
            return combined_df
        else:
            return pd.DataFrame()

    def _get_windows_for_date_range(self) -> List[str]:
        """Get window paths for the specified date range."""
        try:
            response = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{PREFIX}/{self.symbol}/")

            windows = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith("OVERLAP.json"):
                    window = obj["Key"].replace("/OVERLAP.json", "")
                    windows.append(window)

            return windows[:10]  # Limit to recent windows

        except Exception as e:
            print(f"Error getting windows: {e}")
            return []

    def _standardize_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure canonical schema alignment."""
        # Ensure required columns exist
        required_cols = ["ts_exchange", "best_bid", "best_ask", "last_px"]

        for col in required_cols:
            if col not in df.columns:
                if col == "ts_exchange" and "timestamp" in df.columns:
                    df[col] = df["timestamp"]
                elif col in ["best_bid", "best_ask"] and "price" in df.columns:
                    df[col] = df["price"]
                elif col == "last_px" and "price" in df.columns:
                    df[col] = df["price"]
                else:
                    df[col] = np.nan

        # Ensure timestamp is datetime and timezone-aware
        if "ts_exchange" in df.columns:
            df["ts_exchange"] = pd.to_datetime(df["ts_exchange"])
            if df["ts_exchange"].dt.tz is None:
                df["ts_exchange"] = df["ts_exchange"].dt.tz_localize("UTC")
            else:
                df["ts_exchange"] = df["ts_exchange"].dt.tz_convert("UTC")

        # Calculate mid price and spread
        if "best_bid" in df.columns and "best_ask" in df.columns:
            df["mid_px"] = (df["best_bid"] + df["best_ask"]) / 2
            df["spread"] = df["best_ask"] - df["best_bid"]
            df["spread_bps"] = (df["spread"] / df["mid_px"]) * 10000

        return df

    def _check_timestamps(self, df: pd.DataFrame):
        """Check timestamp integrity."""
        print("\n🕐 Timestamp Analysis")

        # Normalize timestamps
        df["ts_exchange"] = pd.to_datetime(df["ts_exchange"])
        if df["ts_exchange"].dt.tz is None:
            df["ts_exchange"] = df["ts_exchange"].dt.tz_localize("UTC")
        else:
            df["ts_exchange"] = df["ts_exchange"].dt.tz_convert("UTC")

        # Inter-arrival times
        df_sorted = df.sort_values("ts_exchange")
        df_sorted["inter_arrival"] = df_sorted["ts_exchange"].diff().dt.total_seconds()

        # Timestamp statistics
        timestamp_stats = {
            "total_ticks": len(df),
            "time_span_hours": (df["ts_exchange"].max() - df["ts_exchange"].min()).total_seconds()
            / 3600,
            "mean_inter_arrival_ms": df_sorted["inter_arrival"].mean() * 1000,
            "median_inter_arrival_ms": df_sorted["inter_arrival"].median() * 1000,
            "std_inter_arrival_ms": df_sorted["inter_arrival"].std() * 1000,
            "min_inter_arrival_ms": df_sorted["inter_arrival"].min() * 1000,
            "max_inter_arrival_ms": df_sorted["inter_arrival"].max() * 1000,
            "duplicate_timestamps": df["ts_exchange"].duplicated().sum(),
            "non_monotonic": (df_sorted["ts_exchange"].diff() < pd.Timedelta(0)).sum(),
        }

        # Inter-arrival distribution plot
        plt.figure(figsize=(12, 8))

        plt.subplot(2, 2, 1)
        plt.hist(df_sorted["inter_arrival"].dropna(), bins=50, alpha=0.7, edgecolor="black")
        plt.title("Inter-Arrival Time Distribution")
        plt.xlabel("Seconds")
        plt.ylabel("Frequency")
        plt.yscale("log")

        plt.subplot(2, 2, 2)
        plt.plot(df_sorted["ts_exchange"], df_sorted["inter_arrival"])
        plt.title("Inter-Arrival Times Over Time")
        plt.xlabel("Time")
        plt.ylabel("Inter-Arrival (seconds)")
        plt.xticks(rotation=45)

        plt.subplot(2, 2, 3)
        df_sorted["inter_arrival"].rolling(1000).mean().plot()
        plt.title("Rolling Mean Inter-Arrival Time")
        plt.xlabel("Tick Index")
        plt.ylabel("Mean Inter-Arrival (seconds)")

        plt.subplot(2, 2, 4)
        plt.boxplot(df_sorted["inter_arrival"].dropna())
        plt.title("Inter-Arrival Time Box Plot")
        plt.ylabel("Seconds")

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/timestamp_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        self.results["timestamps"] = timestamp_stats
        print(f"  ✅ Timestamp analysis complete")
        print(f"    Mean inter-arrival: {timestamp_stats['mean_inter_arrival_ms']:.1f}ms")
        print(f"    Duplicates: {timestamp_stats['duplicate_timestamps']}")
        print(f"    Non-monotonic: {timestamp_stats['non_monotonic']}")

    def _check_duplicates(self, df: pd.DataFrame):
        """Check for duplicate records."""
        print("\n🔄 Duplicate Analysis")

        # Before deduplication
        before_count = len(df)
        before_duplicates = df.duplicated().sum()

        # Deduplication rule: (ts_exchange, last_px, last_sz)
        dedup_cols = ["ts_exchange", "last_px", "last_sz"]
        available_cols = [col for col in dedup_cols if col in df.columns]

        if len(available_cols) >= 2:
            df_dedup = df.drop_duplicates(subset=available_cols, keep="first")
            after_count = len(df_dedup)
            after_duplicates = df_dedup.duplicated().sum()
        else:
            df_dedup = df
            after_count = before_count
            after_duplicates = before_duplicates

        duplicate_stats = {
            "before_count": before_count,
            "before_duplicates": before_duplicates,
            "before_duplicate_rate": before_duplicates / before_count if before_count > 0 else 0,
            "after_count": after_count,
            "after_duplicates": after_duplicates,
            "after_duplicate_rate": after_duplicates / after_count if after_count > 0 else 0,
            "dedup_removed": before_count - after_count,
            "dedup_rate": (before_count - after_count) / before_count if before_count > 0 else 0,
        }

        # Duplicate analysis plot
        plt.figure(figsize=(10, 6))

        plt.subplot(1, 2, 1)
        duplicate_counts = [
            duplicate_stats["before_duplicates"],
            duplicate_stats["after_duplicates"],
        ]
        plt.bar(
            ["Before Dedup", "After Dedup"], duplicate_counts, color=["red", "green"], alpha=0.7
        )
        plt.title("Duplicate Records")
        plt.ylabel("Count")

        plt.subplot(1, 2, 2)
        duplicate_rates = [
            duplicate_stats["before_duplicate_rate"],
            duplicate_stats["after_duplicate_rate"],
        ]
        plt.bar(["Before Dedup", "After Dedup"], duplicate_rates, color=["red", "green"], alpha=0.7)
        plt.title("Duplicate Rate")
        plt.ylabel("Rate")

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/duplicate_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        self.results["duplicates"] = duplicate_stats
        print(f"  ✅ Duplicate analysis complete")
        print(
            f"    Before: {duplicate_stats['before_duplicates']} duplicates ({duplicate_stats['before_duplicate_rate']:.1%})"
        )
        print(
            f"    After: {duplicate_stats['after_duplicates']} duplicates ({duplicate_stats['after_duplicate_rate']:.1%})"
        )
        print(
            f"    Removed: {duplicate_stats['dedup_removed']} records ({duplicate_stats['dedup_rate']:.1%})"
        )

    def _check_staleness_burstiness(self, df: pd.DataFrame):
        """Check for staleness and burstiness patterns."""
        print("\n⏱️ Staleness & Burstiness Analysis")

        # Sort by timestamp
        df_sorted = df.sort_values("ts_exchange")

        # Create time grid (1-second intervals)
        start_time = df_sorted["ts_exchange"].min()
        end_time = df_sorted["ts_exchange"].max()
        time_grid = pd.date_range(start=start_time, end=end_time, freq="1S", tz="UTC")

        # Count updates per second
        df_sorted["second"] = df_sorted["ts_exchange"].dt.floor("1S")
        updates_per_second = df_sorted.groupby("second").size()

        # Merge with time grid
        time_grid_df = pd.DataFrame({"second": time_grid})
        updates_df = pd.merge(
            time_grid_df, updates_per_second.reset_index(), on="second", how="left"
        )
        updates_df["updates"] = updates_df[0].fillna(0)

        # Staleness analysis
        zero_update_seconds = (updates_df["updates"] == 0).sum()
        total_seconds = len(updates_df)
        staleness_rate = zero_update_seconds / total_seconds

        # Longest stale stretch
        updates_df["is_stale"] = updates_df["updates"] == 0
        stale_stretches = []
        current_stretch = 0
        for is_stale in updates_df["is_stale"]:
            if is_stale:
                current_stretch += 1
            else:
                if current_stretch > 0:
                    stale_stretches.append(current_stretch)
                current_stretch = 0
        if current_stretch > 0:
            stale_stretches.append(current_stretch)

        longest_stale = max(stale_stretches) if stale_stretches else 0

        # Price change analysis
        df_sorted["price_change"] = df_sorted["mid_px"].diff().abs()
        price_change_stats = {
            "mean_price_change": df_sorted["price_change"].mean(),
            "median_price_change": df_sorted["price_change"].median(),
            "std_price_change": df_sorted["price_change"].std(),
            "max_price_change": df_sorted["price_change"].max(),
            "outlier_threshold": df_sorted["price_change"].quantile(0.999),
            "outlier_count": (
                df_sorted["price_change"] > df_sorted["price_change"].quantile(0.999)
            ).sum(),
        }

        staleness_stats = {
            "total_seconds": total_seconds,
            "zero_update_seconds": zero_update_seconds,
            "staleness_rate": staleness_rate,
            "longest_stale_seconds": longest_stale,
            "mean_updates_per_second": updates_df["updates"].mean(),
            "max_updates_per_second": updates_df["updates"].max(),
            "price_change_stats": price_change_stats,
        }

        # Staleness plots
        plt.figure(figsize=(15, 10))

        plt.subplot(2, 3, 1)
        updates_df["updates"].hist(bins=50, alpha=0.7, edgecolor="black")
        plt.title("Updates per Second Distribution")
        plt.xlabel("Updates")
        plt.ylabel("Frequency")

        plt.subplot(2, 3, 2)
        updates_df.set_index("second")["updates"].plot()
        plt.title("Updates per Second Over Time")
        plt.xlabel("Time")
        plt.ylabel("Updates")
        plt.xticks(rotation=45)

        plt.subplot(2, 3, 3)
        plt.bar(
            ["Zero Updates", "Non-Zero Updates"],
            [zero_update_seconds, total_seconds - zero_update_seconds],
        )
        plt.title("Staleness Summary")
        plt.ylabel("Seconds")

        plt.subplot(2, 3, 4)
        df_sorted["price_change"].hist(bins=50, alpha=0.7, edgecolor="black")
        plt.title("Price Change Distribution")
        plt.xlabel("Absolute Price Change")
        plt.ylabel("Frequency")
        plt.yscale("log")

        plt.subplot(2, 3, 5)
        df_sorted["price_change"].rolling(1000).mean().plot()
        plt.title("Rolling Mean Price Change")
        plt.xlabel("Tick Index")
        plt.ylabel("Mean Price Change")

        plt.subplot(2, 3, 6)
        plt.boxplot(df_sorted["price_change"].dropna())
        plt.title("Price Change Box Plot")
        plt.ylabel("Absolute Price Change")

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/staleness_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        self.results["staleness"] = staleness_stats
        print(f"  ✅ Staleness analysis complete")
        print(f"    Staleness rate: {staleness_rate:.1%}")
        print(f"    Longest stale stretch: {longest_stale} seconds")
        print(f"    Mean updates/second: {staleness_stats['mean_updates_per_second']:.1f}")

    def _check_spread_sanity(self, df: pd.DataFrame):
        """Check spread sanity and quality."""
        print("\n📏 Spread Sanity Analysis")

        if "spread" not in df.columns or "mid_px" not in df.columns:
            print("  ❌ Spread data not available")
            return

        # Calculate spreads
        df["spread"] = df["best_ask"] - df["best_bid"]
        df["spread_bps"] = (df["spread"] / df["mid_px"]) * 10000

        # Spread statistics
        spread_stats = {
            "total_observations": len(df),
            "negative_spreads": (df["spread"] < 0).sum(),
            "negative_spread_rate": (df["spread"] < 0).sum() / len(df),
            "zero_spreads": (df["spread"] == 0).sum(),
            "zero_spread_rate": (df["spread"] == 0).sum() / len(df),
            "mean_spread": df["spread"].mean(),
            "median_spread": df["spread"].median(),
            "std_spread": df["spread"].std(),
            "mean_spread_bps": df["spread_bps"].mean(),
            "median_spread_bps": df["spread_bps"].median(),
            "implausibly_small": (df["spread_bps"] < 0.1).sum(),
            "implausibly_large": (df["spread_bps"] > 1000).sum(),
        }

        # Rolling spread analysis
        df_sorted = df.sort_values("ts_exchange")
        df_sorted = df_sorted.set_index("ts_exchange")
        df_sorted["rolling_spread_1s"] = df_sorted["spread"].rolling("1S").mean()
        df_sorted["rolling_spread_5s"] = df_sorted["spread"].rolling("5S").mean()

        # Spread plots
        plt.figure(figsize=(15, 10))

        plt.subplot(2, 3, 1)
        df["spread"].hist(bins=50, alpha=0.7, edgecolor="black")
        plt.title("Spread Distribution")
        plt.xlabel("Spread")
        plt.ylabel("Frequency")

        plt.subplot(2, 3, 2)
        df["spread_bps"].hist(bins=50, alpha=0.7, edgecolor="black")
        plt.title("Spread (bps) Distribution")
        plt.xlabel("Spread (bps)")
        plt.ylabel("Frequency")

        plt.subplot(2, 3, 3)
        df_sorted["spread"].plot(alpha=0.7)
        plt.title("Spread Over Time")
        plt.xlabel("Time")
        plt.ylabel("Spread")
        plt.xticks(rotation=45)

        plt.subplot(2, 3, 4)
        df_sorted["rolling_spread_1s"].plot()
        plt.title("Rolling 1s Mean Spread")
        plt.xlabel("Time")
        plt.ylabel("Spread")
        plt.xticks(rotation=45)

        plt.subplot(2, 3, 5)
        df_sorted["rolling_spread_5s"].plot()
        plt.title("Rolling 5s Mean Spread")
        plt.xlabel("Time")
        plt.ylabel("Spread")
        plt.xticks(rotation=45)

        plt.subplot(2, 3, 6)
        plt.scatter(df["mid_px"], df["spread"], alpha=0.5)
        plt.title("Spread vs Mid Price")
        plt.xlabel("Mid Price")
        plt.ylabel("Spread")

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/spread_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        self.results["spread"] = spread_stats
        print(f"  ✅ Spread analysis complete")
        print(f"    Negative spreads: {spread_stats['negative_spread_rate']:.1%}")
        print(f"    Mean spread: {spread_stats['mean_spread']:.4f}")
        print(f"    Mean spread (bps): {spread_stats['mean_spread_bps']:.1f}")

    def _check_schema_conformity(self, df: pd.DataFrame):
        """Check schema conformity."""
        print("\n📋 Schema Conformity Analysis")

        # Expected canonical columns
        canonical_cols = [
            "ts_exchange",
            "best_bid",
            "best_ask",
            "last_px",
            "last_sz",
            "mid_px",
            "spread",
            "spread_bps",
        ]

        # Check column presence
        present_cols = [col for col in canonical_cols if col in df.columns]
        missing_cols = [col for col in canonical_cols if col not in df.columns]

        # Data types
        dtypes = df.dtypes.to_dict()

        # Sample data quality
        sample_stats = {
            "total_rows": len(df),
            "non_null_ts": df["ts_exchange"].notna().sum() if "ts_exchange" in df.columns else 0,
            "non_null_mid": df["mid_px"].notna().sum() if "mid_px" in df.columns else 0,
            "non_null_spread": df["spread"].notna().sum() if "spread" in df.columns else 0,
        }

        schema_stats = {
            "canonical_columns_present": present_cols,
            "canonical_columns_missing": missing_cols,
            "total_columns": len(df.columns),
            "data_types": dtypes,
            "sample_stats": sample_stats,
        }

        self.results["schema"] = schema_stats
        print(f"  ✅ Schema analysis complete")
        print(f"    Present: {len(present_cols)}/{len(canonical_cols)} canonical columns")
        print(f"    Missing: {missing_cols}")
        print(f"    Total columns: {len(df.columns)}")

    def _generate_summary_report(self):
        """Generate comprehensive summary report."""
        report = f"""# Coinbase BTC-USD Anomaly QC Report

## Overview
Quality control analysis of Coinbase data to investigate variance ratio anomaly
observed in Wave-1 tests (VR 1.5-18.4 vs 0.3-0.4 for other venues).

**Analysis Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Symbol**: {self.symbol}
**Date Range**: {self.start_date} to {self.end_date}

## Key Findings

### Timestamp Analysis
- **Total Ticks**: {self.results.get('timestamps', {}).get('total_ticks', 'N/A')}
- **Time Span**: {self.results.get('timestamps', {}).get('time_span_hours', 'N/A'):.1f} hours
- **Mean Inter-Arrival**: {self.results.get('timestamps', {}).get('mean_inter_arrival_ms', 'N/A'):.1f}ms
- **Duplicate Timestamps**: {self.results.get('timestamps', {}).get('duplicate_timestamps', 'N/A')}
- **Non-Monotonic**: {self.results.get('timestamps', {}).get('non_monotonic', 'N/A')}

### Duplicate Analysis
- **Before Dedup**: {self.results.get('duplicates', {}).get('before_duplicates', 'N/A')} duplicates ({self.results.get('duplicates', {}).get('before_duplicate_rate', 0):.1%})
- **After Dedup**: {self.results.get('duplicates', {}).get('after_duplicates', 'N/A')} duplicates ({self.results.get('duplicates', {}).get('after_duplicate_rate', 0):.1%})
- **Records Removed**: {self.results.get('duplicates', {}).get('dedup_removed', 'N/A')} ({self.results.get('duplicates', {}).get('dedup_rate', 0):.1%})

### Staleness & Burstiness
- **Staleness Rate**: {self.results.get('staleness', {}).get('staleness_rate', 0):.1%}
- **Longest Stale Stretch**: {self.results.get('staleness', {}).get('longest_stale_seconds', 'N/A')} seconds
- **Mean Updates/Second**: {self.results.get('staleness', {}).get('mean_updates_per_second', 'N/A'):.1f}

### Spread Analysis
- **Negative Spreads**: {self.results.get('spread', {}).get('negative_spread_rate', 0):.1%}
- **Mean Spread**: {self.results.get('spread', {}).get('mean_spread', 'N/A')}
- **Mean Spread (bps)**: {self.results.get('spread', {}).get('mean_spread_bps', 'N/A'):.1f}

### Schema Conformity
- **Canonical Columns Present**: {len(self.results.get('schema', {}).get('canonical_columns_present', []))}
- **Missing Columns**: {self.results.get('schema', {}).get('canonical_columns_missing', [])}

## Plots Generated
- `timestamp_analysis.png` - Inter-arrival time analysis
- `duplicate_analysis.png` - Duplicate record analysis  
- `staleness_analysis.png` - Staleness and burstiness patterns
- `spread_analysis.png` - Spread quality and distribution

## Conclusion
{self._generate_conclusion()}

## Files
- `coinbase_qc_summary.csv` - Summary metrics
- `coinbase_qc_report.md` - This report
- Various PNG plots for visual analysis
"""

        with open(f"{self.output_dir}/coinbase_qc_report.md", "w") as f:
            f.write(report)

        # Save summary CSV
        summary_data = {}
        for category, stats in self.results.items():
            for key, value in stats.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        summary_data[f"{category}_{subkey}"] = subvalue
                else:
                    summary_data[f"{category}_{key}"] = value

        summary_df = pd.DataFrame([summary_data])
        summary_df.to_csv(f"{self.output_dir}/coinbase_qc_summary.csv", index=False)

    def _generate_conclusion(self) -> str:
        """Generate conclusion based on QC results."""
        conclusions = []

        # Check for data quality issues
        duplicate_rate = self.results.get("duplicates", {}).get("before_duplicate_rate", 0)
        if duplicate_rate > 0.1:
            conclusions.append(
                f"⚠️ High duplicate rate ({duplicate_rate:.1%}) may affect variance calculations"
            )

        staleness_rate = self.results.get("staleness", {}).get("staleness_rate", 0)
        if staleness_rate > 0.1:
            conclusions.append(
                f"⚠️ High staleness rate ({staleness_rate:.1%}) may create artificial patterns"
            )

        negative_spread_rate = self.results.get("spread", {}).get("negative_spread_rate", 0)
        if negative_spread_rate > 0.01:
            conclusions.append(
                f"⚠️ Negative spreads ({negative_spread_rate:.1%}) indicate data quality issues"
            )

        if not conclusions:
            conclusions.append("✅ No major data quality issues detected")
            conclusions.append(
                "🔍 Coinbase anomaly may be genuine - requires deeper econometric analysis"
            )
        else:
            conclusions.append(
                "🔧 Data quality issues detected - may explain variance ratio anomaly"
            )

        return "\n".join(conclusions)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Coinbase BTC-USD Anomaly QC Analysis")
    parser.add_argument("--symbol", default="BTC-USD", help="Symbol to analyze")
    parser.add_argument("--start", default="2025-09-29", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-09-30", help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Initialize QC analyzer
    qc = CoinbaseAnomalyQC(args.symbol, args.start, args.end)

    # Run QC analysis
    qc.run_qc_analysis()


if __name__ == "__main__":
    main()
