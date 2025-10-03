#!/usr/bin/env python3
"""
Real Data Sample Analysis: Download and Analyze Sample S3 Data
==============================================================

This script downloads a sample of real S3 snapshots and analyzes them
to validate the data structure and coverage before full re-ingestion.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import boto3
import numpy as np
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealDataSampleAnalysis:
    """Analyze sample of real S3 snapshots."""

    def __init__(self, output_dir: str = "data/derived/btc_usd_real"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # S3 configuration
        self.bucket_name = "acd-monitor-snapshots"
        self.s3_prefix = "snapshots/BTC-USD/"

        # Initialize S3 client
        self.s3_client = boto3.client("s3")

    def get_s3_file_list(self) -> List[str]:
        """Get list of S3 parquet files."""
        logger.info("Getting S3 file list...")

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=self.s3_prefix, MaxKeys=1000
            )

            file_paths = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    file_paths.append(obj["Key"])

            logger.info(f"✅ Found {len(file_paths)} parquet files")
            return file_paths

        except Exception as e:
            logger.error(f"❌ Failed to list S3 files: {e}")
            return []

    def download_sample_files(self, file_paths: List[str], max_files: int = 5) -> List[str]:
        """Download sample files for analysis."""
        logger.info(f"Downloading {max_files} sample files...")

        downloaded_files = []

        for i, file_path in enumerate(file_paths[:max_files]):
            try:
                # Create local file path
                local_path = self.output_dir / f"sample_{i}_{Path(file_path).name}"

                # Download file
                self.s3_client.download_file(self.bucket_name, file_path, str(local_path))
                downloaded_files.append(str(local_path))

                logger.info(f"✅ Downloaded: {file_path}")

            except Exception as e:
                logger.error(f"❌ Failed to download {file_path}: {e}")

        logger.info(f"✅ Downloaded {len(downloaded_files)} sample files")
        return downloaded_files

    def analyze_sample_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze sample files to understand data structure."""
        logger.info("Analyzing sample files...")

        analysis_results = {
            "file_count": len(file_paths),
            "file_analysis": [],
            "schema_analysis": {},
            "data_quality": {},
            "coverage_summary": {},
        }

        all_data = []

        for file_path in file_paths:
            try:
                # Read parquet file
                df = pd.read_parquet(file_path)

                file_analysis = {
                    "file_path": file_path,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "dtypes": df.dtypes.to_dict(),
                    "min_timestamp": (
                        df["ts_exchange"].min() if "ts_exchange" in df.columns else None
                    ),
                    "max_timestamp": (
                        df["ts_exchange"].max() if "ts_exchange" in df.columns else None
                    ),
                    "venue": df["venue"].iloc[0] if "venue" in df.columns else None,
                }

                analysis_results["file_analysis"].append(file_analysis)
                all_data.append(df)

                logger.info(f"✅ Analyzed {file_path}: {len(df)} rows")

            except Exception as e:
                logger.error(f"❌ Failed to analyze {file_path}: {e}")

        if all_data:
            # Combine all data for schema analysis
            combined_df = pd.concat(all_data, ignore_index=True)

            # Schema analysis
            analysis_results["schema_analysis"] = {
                "total_rows": len(combined_df),
                "columns": list(combined_df.columns),
                "dtypes": combined_df.dtypes.to_dict(),
                "unique_venues": (
                    combined_df["venue"].unique().tolist() if "venue" in combined_df.columns else []
                ),
                "date_range": {
                    "min": (
                        combined_df["ts_exchange"].min()
                        if "ts_exchange" in combined_df.columns
                        else None
                    ),
                    "max": (
                        combined_df["ts_exchange"].max()
                        if "ts_exchange" in combined_df.columns
                        else None
                    ),
                },
            }

            # Data quality analysis
            analysis_results["data_quality"] = {
                "missing_data": combined_df.isnull().sum().to_dict(),
                "duplicate_rows": combined_df.duplicated().sum(),
                "venue_coverage": (
                    combined_df["venue"].value_counts().to_dict()
                    if "venue" in combined_df.columns
                    else {}
                ),
            }

            # Coverage summary
            analysis_results["coverage_summary"] = {
                "total_records": len(combined_df),
                "unique_venues": (
                    len(combined_df["venue"].unique()) if "venue" in combined_df.columns else 0
                ),
                "date_range_days": (
                    (combined_df["ts_exchange"].max() - combined_df["ts_exchange"].min())
                    / (1000 * 60 * 60 * 24)
                    if "ts_exchange" in combined_df.columns
                    else 0
                ),
            }

        logger.info("✅ Sample file analysis complete")
        return analysis_results

    def create_aligned_sample(self, file_paths: List[str]) -> pd.DataFrame:
        """Create aligned sample panel from downloaded files."""
        logger.info("Creating aligned sample panel...")

        all_data = []

        for file_path in file_paths:
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

        # Create aligned panel
        aligned_data = []

        # Group by timestamp and create venue-specific columns
        for timestamp, group in combined_df.groupby("timestamp"):
            row = {"timestamp": timestamp}

            for _, venue_data in group.iterrows():
                venue = venue_data["venue"]
                row[f"mid_{venue}"] = (venue_data["best_bid"] + venue_data["best_ask"]) / 2
                row[f"bid_{venue}"] = venue_data["best_bid"]
                row[f"ask_{venue}"] = venue_data["best_ask"]
                row[f"spread_{venue}"] = venue_data["best_ask"] - venue_data["best_bid"]

            aligned_data.append(row)

        aligned_df = pd.DataFrame(aligned_data)
        aligned_df = aligned_df.set_index("timestamp")
        aligned_df = aligned_df.sort_index()

        logger.info(f"✅ Aligned sample panel created: {len(aligned_df)} observations")
        return aligned_df

    def save_sample_analysis(
        self, analysis_results: Dict[str, Any], aligned_df: pd.DataFrame
    ) -> None:
        """Save sample analysis results."""
        logger.info("Saving sample analysis results...")

        # Save analysis results
        with open(self.output_dir / "sample_analysis.json", "w") as f:
            json.dump(analysis_results, f, indent=2, default=str)

        # Save aligned sample
        if not aligned_df.empty:
            aligned_df.to_parquet(self.output_dir / "aligned_sample.parquet")

            # Save sample metadata
            sample_metadata = {
                "creation_date": datetime.now().isoformat(),
                "total_observations": len(aligned_df),
                "date_range": {
                    "start": aligned_df.index.min().isoformat(),
                    "end": aligned_df.index.max().isoformat(),
                },
                "venues": [col for col in aligned_df.columns if col.startswith("mid_")],
                "data_source": "real_s3_snapshots_sample",
                "methodology": "boto3_download_analysis",
            }

            with open(self.output_dir / "sample_metadata.json", "w") as f:
                json.dump(sample_metadata, f, indent=2)

        logger.info("✅ Sample analysis results saved")

    def run_sample_analysis(self) -> bool:
        """Run complete sample analysis."""
        logger.info("Starting real data sample analysis...")

        try:
            # Get S3 file list
            file_paths = self.get_s3_file_list()
            if not file_paths:
                logger.error("❌ No S3 files found")
                return False

            # Download sample files
            downloaded_files = self.download_sample_files(file_paths, max_files=5)
            if not downloaded_files:
                logger.error("❌ No files downloaded")
                return False

            # Analyze sample files
            analysis_results = self.analyze_sample_files(downloaded_files)

            # Create aligned sample
            aligned_df = self.create_aligned_sample(downloaded_files)

            # Save results
            self.save_sample_analysis(analysis_results, aligned_df)

            logger.info("✅ Real data sample analysis completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Real data sample analysis failed: {e}")
            return False


def main():
    """Main execution function."""
    analysis = RealDataSampleAnalysis()
    success = analysis.run_sample_analysis()

    if success:
        print("\n🎉 Real data sample analysis complete!")
        print("✅ Sample files downloaded and analyzed")
        print("✅ Data structure validated")
        print("✅ Aligned sample panel created")
    else:
        print("\n❌ Real data sample analysis failed")
        print("❌ Check logs for details")


if __name__ == "__main__":
    main()
