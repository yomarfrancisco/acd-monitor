#!/usr/bin/env python3
"""
Simple Real Data Analysis: Basic S3 Data Validation
====================================================

This script performs basic validation of real S3 snapshots data
to confirm record counts and coverage before full analysis.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import boto3
import numpy as np
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleRealDataAnalysis:
    """Basic validation of real S3 snapshots data."""

    def __init__(self, output_dir: str = "data/derived/btc_usd_real"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # S3 configuration
        self.bucket_name = "acd-monitor-snapshots"
        self.s3_prefix = "snapshots/BTC-USD/"

        # Initialize S3 client
        self.s3_client = boto3.client("s3")

    def get_s3_coverage(self) -> Dict[str, Any]:
        """Get S3 data coverage statistics."""
        logger.info("Analyzing S3 data coverage...")

        try:
            # List all objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=self.s3_prefix, MaxKeys=1000
            )

            objects = response.get("Contents", [])

            # Analyze coverage
            coverage = {
                "total_objects": len(objects),
                "total_size_mb": sum(obj["Size"] for obj in objects) / (1024 * 1024),
                "date_coverage": set(),
                "venue_coverage": set(),
                "window_coverage": set(),
                "parquet_files": 0,
            }

            for obj in objects:
                key = obj["Key"]

                # Count parquet files
                if key.endswith(".parquet"):
                    coverage["parquet_files"] += 1

                # Extract date, window, venue from path
                # Format: snapshots/BTC-USD/20250928/0200-0230/ticks/venue/part-0000.parquet
                parts = key.split("/")
                if len(parts) >= 6:
                    date = parts[2]
                    window = parts[3]
                    venue = parts[5]

                    coverage["date_coverage"].add(date)
                    coverage["venue_coverage"].add(venue)
                    coverage["window_coverage"].add(window)

            # Convert sets to lists for JSON serialization
            coverage["date_coverage"] = sorted(list(coverage["date_coverage"]))
            coverage["venue_coverage"] = sorted(list(coverage["venue_coverage"]))
            coverage["window_coverage"] = sorted(list(coverage["window_coverage"]))

            logger.info(
                f"✅ S3 coverage analysis complete: {coverage['parquet_files']} parquet files"
            )
            return coverage

        except Exception as e:
            logger.error(f"❌ Failed to analyze S3 coverage: {e}")
            return {}

    def analyze_sample_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single sample file."""
        logger.info(f"Analyzing sample file: {file_path}")

        try:
            # Read parquet file
            df = pd.read_parquet(file_path)

            analysis = {
                "file_path": file_path,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "venue": df["venue"].iloc[0] if "venue" in df.columns else None,
                "min_timestamp": (
                    int(df["ts_exchange"].min()) if "ts_exchange" in df.columns else None
                ),
                "max_timestamp": (
                    int(df["ts_exchange"].max()) if "ts_exchange" in df.columns else None
                ),
                "missing_data": df.isnull().sum().to_dict(),
                "unique_venues": df["venue"].nunique() if "venue" in df.columns else 0,
            }

            logger.info(f"✅ Sample file analyzed: {len(df)} rows")
            return analysis

        except Exception as e:
            logger.error(f"❌ Failed to analyze {file_path}: {e}")
            return {}

    def create_simple_aligned_panel(self, sample_files: List[str]) -> pd.DataFrame:
        """Create simple aligned panel from sample files."""
        logger.info("Creating simple aligned panel...")

        all_data = []

        for file_path in sample_files:
            try:
                df = pd.read_parquet(file_path)
                all_data.append(df)
            except Exception as e:
                logger.error(f"❌ Failed to read {file_path}: {e}")

        if not all_data:
            logger.error("❌ No data to align")
            return pd.DataFrame()

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Convert timestamp to datetime
        combined_df["timestamp"] = pd.to_datetime(combined_df["ts_exchange"], unit="ms")

        # Create simple aligned panel
        aligned_data = []

        # Group by timestamp and create venue-specific columns
        for timestamp, group in combined_df.groupby("timestamp"):
            row = {"timestamp": timestamp}

            for _, venue_data in group.iterrows():
                venue = venue_data["venue"]
                row[f"mid_{venue}"] = (venue_data["best_bid"] + venue_data["best_ask"]) / 2
                row[f"bid_{venue}"] = venue_data["best_bid"]
                row[f"ask_{venue}"] = venue_data["best_ask"]

            aligned_data.append(row)

        aligned_df = pd.DataFrame(aligned_data)
        aligned_df = aligned_df.set_index("timestamp")
        aligned_df = aligned_df.sort_index()

        logger.info(f"✅ Simple aligned panel created: {len(aligned_df)} observations")
        return aligned_df

    def run_simple_analysis(self) -> bool:
        """Run simple real data analysis."""
        logger.info("Starting simple real data analysis...")

        try:
            # Get S3 coverage
            coverage = self.get_s3_coverage()
            if not coverage:
                logger.error("❌ Failed to get S3 coverage")
                return False

            # Analyze sample files
            sample_files = [
                "data/derived/btc_usd_real/sample_0_binance.parquet",
                "data/derived/btc_usd_real/sample_1_coinbase.parquet",
                "data/derived/btc_usd_real/sample_2_binance.parquet",
                "data/derived/btc_usd_real/sample_3_bybit.parquet",
                "data/derived/btc_usd_real/sample_4_coinbase.parquet",
            ]

            sample_analysis = []
            for file_path in sample_files:
                if Path(file_path).exists():
                    analysis = self.analyze_sample_file(file_path)
                    sample_analysis.append(analysis)

            # Create simple aligned panel
            aligned_df = self.create_simple_aligned_panel(sample_files)

            # Save results
            results = {
                "s3_coverage": coverage,
                "sample_analysis": sample_analysis,
                "aligned_panel_summary": {
                    "total_observations": len(aligned_df),
                    "date_range": {
                        "start": (
                            aligned_df.index.min().isoformat() if not aligned_df.empty else None
                        ),
                        "end": aligned_df.index.max().isoformat() if not aligned_df.empty else None,
                    },
                    "venues": (
                        [col for col in aligned_df.columns if col.startswith("mid_")]
                        if not aligned_df.empty
                        else []
                    ),
                },
            }

            # Save results
            with open(self.output_dir / "simple_analysis_results.json", "w") as f:
                json.dump(results, f, indent=2, default=str)

            # Save aligned panel
            if not aligned_df.empty:
                aligned_df.to_parquet(self.output_dir / "simple_aligned_panel.parquet")

            logger.info("✅ Simple real data analysis completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Simple real data analysis failed: {e}")
            return False


def main():
    """Main execution function."""
    analysis = SimpleRealDataAnalysis()
    success = analysis.run_simple_analysis()

    if success:
        print("\n🎉 Simple real data analysis complete!")
        print("✅ S3 coverage analyzed")
        print("✅ Sample files analyzed")
        print("✅ Simple aligned panel created")
    else:
        print("\n❌ Simple real data analysis failed")
        print("❌ Check logs for details")


if __name__ == "__main__":
    main()
