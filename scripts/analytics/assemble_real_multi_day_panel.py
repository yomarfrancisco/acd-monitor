#!/usr/bin/env python3
"""
Assemble Real Multi-Day BTC-USD Panel from S3 Data
Uses authentic S3 parquet files to build extended panel for Wave-2 analysis.
"""

import boto3
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class RealMultiDayPanelAssembler:
    """Assemble real multi-day BTC-USD panel from S3 data."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.data_dir = "data/derived/btc_usd"
        self.analysis_dir = "analysis/wave2/btc_usd_extended"

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

    def assemble_multi_day_panel(self):
        """Assemble multi-day panel from real S3 data."""
        print("🔧 Assembling Real Multi-Day BTC-USD Panel")
        print("=" * 60)

        # Step 1: Get all parquet files from S3
        print("📥 Loading parquet files from S3...")
        parquet_files = self._get_all_parquet_files()

        if not parquet_files:
            print("❌ No parquet files found in S3")
            return False

        print(f"📊 Found {len(parquet_files)} parquet files")

        # Step 2: Load and process each venue's data
        print("\n🔄 Processing venue data...")
        venue_data = {}
        for venue in self.venues:
            print(f"  📊 Processing {venue}...")
            venue_files = [f for f in parquet_files if venue in f["key"]]
            if venue_files:
                venue_df = self._load_venue_data(venue, venue_files)
                if venue_df is not None and len(venue_df) > 0:
                    venue_data[venue] = venue_df
                    print(f"    ✅ {venue}: {len(venue_df)} observations")
                else:
                    print(f"    ⚠️ {venue}: No valid data")
            else:
                print(f"    ❌ {venue}: No files found")

        if not venue_data:
            print("❌ No venue data loaded")
            return False

        # Step 3: Align to 1-second grid
        print("\n🔄 Aligning to 1-second grid...")
        aligned_panel = self._align_to_1s_grid(venue_data)

        if aligned_panel is None or len(aligned_panel) == 0:
            print("❌ Alignment failed")
            return False

        print(f"✅ Aligned panel: {len(aligned_panel)} observations")
        print(f"📅 Date range: {aligned_panel.index.min()} to {aligned_panel.index.max()}")

        # Step 4: Apply data quality controls
        print("\n🔄 Applying data quality controls...")
        cleaned_panel = self._apply_quality_controls(aligned_panel)

        # Step 5: Save panel
        panel_file = f"{self.data_dir}/panel_1s_inner_real_multi_day.parquet"
        cleaned_panel.to_parquet(panel_file)
        print(f"💾 Saved panel to {panel_file}")

        # Step 6: Generate assembly report
        self._generate_assembly_report(cleaned_panel, parquet_files)

        print(f"\n✅ Multi-day panel assembly completed")
        return True

    def _get_all_parquet_files(self):
        """Get all parquet files from S3."""
        objects = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet"):
                            objects.append(
                                {
                                    "key": obj["Key"],
                                    "size": obj["Size"],
                                    "last_modified": obj["LastModified"],
                                }
                            )
        except Exception as e:
            print(f"❌ Error listing parquet files: {e}")
            return []

        return objects

    def _load_venue_data(self, venue: str, venue_files: List[Dict]) -> Optional[pd.DataFrame]:
        """Load and combine data for a specific venue."""
        venue_dfs = []

        for file_info in venue_files:
            try:
                # Download parquet file to temp location
                temp_file = f"/tmp/temp_{venue}_{file_info['key'].split('/')[-1]}"

                self.s3_client.download_file(
                    Bucket=self.bucket_name, Key=file_info["key"], Filename=temp_file
                )

                # Read parquet data
                df = pd.read_parquet(temp_file)

                if len(df) > 0:
                    # Handle timestamp column (ts_exchange)
                    if "ts_exchange" in df.columns:
                        # Convert ts_exchange to datetime
                        if df["ts_exchange"].dtype == "int64":
                            # Convert nanoseconds to datetime
                            df["ts"] = pd.to_datetime(df["ts_exchange"], unit="ns")
                        else:
                            df["ts"] = pd.to_datetime(df["ts_exchange"])
                    elif "timestamp" in df.columns:
                        df["ts"] = pd.to_datetime(df["timestamp"])
                    elif "ts" in df.columns:
                        df["ts"] = pd.to_datetime(df["ts"])
                    else:
                        print(f"    ⚠️ No timestamp column found in {file_info['key']}")
                        continue

                    # Set timestamp as index
                    df = df.set_index("ts")

                    # Ensure UTC timezone
                    if df.index.tz is None:
                        df.index = df.index.tz_localize("UTC")
                    else:
                        df.index = df.index.tz_convert("UTC")

                    # Rename columns to include venue prefix
                    column_mapping = {
                        "best_bid": f"{venue}_bid_px",
                        "best_ask": f"{venue}_ask_px",
                        "last_px": f"{venue}_mid_px",  # Use last_px as mid price proxy
                        "bid_sz": f"{venue}_bid_sz",
                        "ask_sz": f"{venue}_ask_sz",
                        "trade_sz": f"{venue}_trade_sz",
                    }

                    # Only rename columns that exist
                    existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
                    df = df.rename(columns=existing_mapping)

                    # Calculate mid price if we have bid/ask
                    if f"{venue}_bid_px" in df.columns and f"{venue}_ask_px" in df.columns:
                        df[f"{venue}_mid_px"] = (df[f"{venue}_bid_px"] + df[f"{venue}_ask_px"]) / 2

                    venue_dfs.append(df)

                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            except Exception as e:
                print(f"    ⚠️ Error loading {file_info['key']}: {e}")
                continue

        if not venue_dfs:
            return None

        # Combine all dataframes for this venue
        combined_df = pd.concat(venue_dfs, ignore_index=False)
        combined_df = combined_df.sort_index()

        # Remove duplicates
        combined_df = combined_df[~combined_df.index.duplicated(keep="last")]

        return combined_df

    def _align_to_1s_grid(self, venue_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """Align all venue data to 1-second grid."""
        print("  🔄 Aligning venues to common 1-second grid...")

        # Find common time range
        all_timestamps = []
        for venue, df in venue_data.items():
            all_timestamps.extend(df.index.tolist())

        if not all_timestamps:
            return None

        # Create 1-second grid
        start_time = min(all_timestamps)
        end_time = max(all_timestamps)

        # Round to nearest second
        start_time = start_time.floor("S")
        end_time = end_time.ceil("S")

        # Create 1-second grid
        grid = pd.date_range(start=start_time, end=end_time, freq="1S", tz="UTC")

        print(f"    📅 Grid: {len(grid)} seconds from {start_time} to {end_time}")

        # Align each venue to grid
        aligned_venues = {}
        for venue, df in venue_data.items():
            print(f"    🔄 Aligning {venue}...")

            # Resample to 1-second grid with LOCF (max gap 3 seconds)
            aligned_df = df.reindex(grid, method="ffill", limit=3)

            # Add venue prefix to columns
            venue_columns = {}
            for col in aligned_df.columns:
                if col not in ["ts", "timestamp"]:  # Skip timestamp columns
                    venue_columns[col] = f"{venue}_{col}"

            aligned_df = aligned_df.rename(columns=venue_columns)
            aligned_venues[venue] = aligned_df

        # Combine all venues
        combined_panel = pd.concat(aligned_venues.values(), axis=1)

        # Inner join to common timestamps (where all venues have data)
        # For now, we'll use outer join and handle missing data later
        print(f"    📊 Combined panel: {len(combined_panel)} observations")

        return combined_panel

    def _apply_quality_controls(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality controls."""
        print("  🔄 Applying quality controls...")

        # Remove duplicate timestamps
        panel = panel[~panel.index.duplicated(keep="last")]

        # Sort by timestamp
        panel = panel.sort_index()

        # Winsorize extreme values for price columns
        price_columns = [
            col for col in panel.columns if "mid_px" in col or "bid_px" in col or "ask_px" in col
        ]
        for col in price_columns:
            if col in panel.columns:
                # Winsorize at 1% and 99%
                lower_bound = panel[col].quantile(0.01)
                upper_bound = panel[col].quantile(0.99)
                panel[col] = panel[col].clip(lower=lower_bound, upper=upper_bound)

        # Remove rows where all price data is missing
        price_cols = [col for col in panel.columns if "mid_px" in col]
        if price_cols:
            panel = panel.dropna(subset=price_cols, how="all")

        print(f"    📊 After quality controls: {len(panel)} observations")

        return panel

    def _generate_assembly_report(self, panel: pd.DataFrame, parquet_files: List[Dict]):
        """Generate assembly report."""
        print("\n📋 Generating assembly report...")

        # Calculate statistics
        total_files = len(parquet_files)
        total_size = sum(f["size"] for f in parquet_files)

        # Venue coverage
        venue_coverage = {}
        for venue in self.venues:
            venue_cols = [col for col in panel.columns if col.startswith(f"{venue}_")]
            venue_coverage[venue] = {
                "columns": len(venue_cols),
                "has_mid_px": any("mid_px" in col for col in venue_cols),
                "has_bid_px": any("bid_px" in col for col in venue_cols),
                "has_ask_px": any("ask_px" in col for col in venue_cols),
            }

        # Date range
        date_range = {
            "start": str(panel.index.min()),
            "end": str(panel.index.max()),
            "duration_hours": (panel.index.max() - panel.index.min()).total_seconds() / 3600,
        }

        report = {
            "assembly_date": datetime.now().isoformat(),
            "total_files_processed": total_files,
            "total_size_bytes": total_size,
            "panel_observations": len(panel),
            "panel_columns": len(panel.columns),
            "date_range": date_range,
            "venue_coverage": venue_coverage,
            "data_quality": {
                "duplicate_timestamps_removed": True,
                "winsorized_extreme_values": True,
                "aligned_to_1s_grid": True,
            },
        }

        # Save report
        with open(f"{self.analysis_dir}/assembly_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Save summary
        with open(f"{self.analysis_dir}/ASSEMBLY_SUMMARY.md", "w") as f:
            f.write(f"# Real Multi-Day BTC-USD Panel Assembly Report\n\n")
            f.write(f"**Assembly Date**: {report['assembly_date']}\n")
            f.write(f"**Files Processed**: {report['total_files_processed']}\n")
            f.write(f"**Total Size**: {report['total_size_bytes']:,} bytes\n")
            f.write(f"**Panel Observations**: {report['panel_observations']:,}\n")
            f.write(f"**Panel Columns**: {report['panel_columns']}\n")
            f.write(
                f"**Date Range**: {report['date_range']['start']} to {report['date_range']['end']}\n"
            )
            f.write(f"**Duration**: {report['date_range']['duration_hours']:.1f} hours\n\n")

            f.write("## Venue Coverage\n\n")
            for venue, coverage in report["venue_coverage"].items():
                f.write(f"- **{venue}**: {coverage['columns']} columns")
                if coverage["has_mid_px"]:
                    f.write(" (mid_px ✓)")
                if coverage["has_bid_px"]:
                    f.write(" (bid_px ✓)")
                if coverage["has_ask_px"]:
                    f.write(" (ask_px ✓)")
                f.write("\n")

            f.write("\n## Data Quality Controls Applied\n\n")
            for control, applied in report["data_quality"].items():
                f.write(f"- **{control.replace('_', ' ').title()}**: {'✓' if applied else '✗'}\n")

        print(f"  ✅ Assembly report saved to {self.analysis_dir}/")


if __name__ == "__main__":
    assembler = RealMultiDayPanelAssembler()
    success = assembler.assemble_multi_day_panel()

    if success:
        print("\n🎉 Real multi-day panel assembly completed successfully!")
    else:
        print("\n❌ Panel assembly failed!")
        sys.exit(1)
