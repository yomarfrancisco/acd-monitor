#!/usr/bin/env python3
"""
Memory-Safe Multi-Day Panel Assembly
Process one date at a time to avoid memory issues.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class MemorySafeMultiDayAssembler:
    """Memory-safe multi-day panel assembler."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.data_dir = "data/derived/btc_usd"
        self.analysis_dir = "analysis/wave2/btc_usd_multiday"

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

        # Available dates from S3 audit
        self.available_dates = ["20250928", "20250929", "20250930"]

    def assemble_multiday_panel(self):
        """Assemble multi-day panel date by date."""
        print("🔧 Memory-Safe Multi-Day Panel Assembly")
        print("=" * 60)

        # Step 1: Process each date individually
        processed_dates = []
        all_panels = []

        for date in self.available_dates:
            print(f"\n📅 Processing date: {date}")
            date_panel = self._process_single_date(date)

            if date_panel is not None and len(date_panel) > 0:
                # Save individual date panel
                date_file = f"{self.data_dir}/panel_1s_inner_real_{date}.parquet"
                date_panel.to_parquet(date_file)
                processed_dates.append(date)
                all_panels.append(date_panel)

                print(f"  ✅ {date}: {len(date_panel)} observations saved to {date_file}")

                # Generate day summary
                self._generate_day_summary(date, date_panel)
            else:
                print(f"  ⚠️ {date}: No data processed")

        if not processed_dates:
            print("❌ No dates processed successfully")
            return False

        # Step 2: Concatenate all panels
        print(f"\n🔄 Concatenating {len(processed_dates)} date panels...")
        multi_day_panel = self._concatenate_panels(all_panels, processed_dates)

        if multi_day_panel is None:
            print("❌ Panel concatenation failed")
            return False

        # Step 3: Save multi-day panel
        multi_day_file = f"{self.data_dir}/panel_1s_inner_real_multiday.parquet"
        multi_day_panel.to_parquet(multi_day_file)

        print(f"✅ Multi-day panel: {len(multi_day_panel)} observations")
        print(f"📅 Date range: {multi_day_panel.index.min()} to {multi_day_panel.index.max()}")
        print(f"💾 Saved to {multi_day_file}")

        # Step 4: Generate assembly summary
        self._generate_assembly_summary(multi_day_panel, processed_dates)

        print(f"\n✅ Multi-day panel assembly completed")
        return True

    def _process_single_date(self, date: str) -> Optional[pd.DataFrame]:
        """Process a single date (memory-safe)."""
        print(f"  📥 Getting files for {date}...")
        date_files = self._get_files_for_date(date)

        if not date_files:
            print(f"    ❌ No files found for {date}")
            return None

        print(f"    📊 Found {len(date_files)} files for {date}")

        # Group files by venue
        venue_files = {}
        for file_info in date_files:
            key = file_info["key"]
            for venue in self.venues:
                if venue in key:
                    if venue not in venue_files:
                        venue_files[venue] = []
                    venue_files[venue].append(file_info)
                    break

        print(f"    📊 Found files for {len(venue_files)} venues")

        # Process each venue
        venue_data = {}
        for venue, venue_file_list in venue_files.items():
            print(f"      🔄 Processing {venue} ({len(venue_file_list)} files)...")
            venue_df = self._load_venue_data_single(venue, venue_file_list)
            if venue_df is not None and len(venue_df) > 0:
                venue_data[venue] = venue_df
                print(f"        ✅ {venue}: {len(venue_df)} observations")
            else:
                print(f"        ⚠️ {venue}: No data")

        if not venue_data:
            return None

        # Align venues to common grid
        print(f"      🔄 Aligning {len(venue_data)} venues...")
        aligned_panel = self._align_venues_to_grid(venue_data)

        return aligned_panel

    def _get_files_for_date(self, target_date: str):
        """Get files for a specific date."""
        objects = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet") and target_date in obj["Key"]:
                            objects.append({"key": obj["Key"], "size": obj["Size"]})
        except Exception as e:
            print(f"    ❌ Error listing files for {target_date}: {e}")
            return []

        return objects

    def _load_venue_data_single(
        self, venue: str, venue_files: List[Dict]
    ) -> Optional[pd.DataFrame]:
        """Load data for a venue (single date)."""
        venue_dfs = []

        for file_info in venue_files:
            try:
                # Download and process file
                temp_file = f"/tmp/temp_{venue}_{file_info['key'].split('/')[-1]}"

                self.s3_client.download_file(
                    Bucket=self.bucket_name, Key=file_info["key"], Filename=temp_file
                )

                df = pd.read_parquet(temp_file)

                if len(df) > 0:
                    # Process timestamp
                    if "ts_exchange" in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df["ts_exchange"]):
                            df["ts"] = df["ts_exchange"]
                        else:
                            df["ts"] = pd.to_datetime(df["ts_exchange"], unit="ns")
                    else:
                        continue

                    df = df.set_index("ts")

                    # Ensure UTC timezone
                    if df.index.tz is None:
                        df.index = df.index.tz_localize("UTC")
                    else:
                        df.index = df.index.tz_convert("UTC")

                    # Keep only essential columns and rename
                    essential_columns = [
                        "best_bid",
                        "best_ask",
                        "last_px",
                        "bid_sz",
                        "ask_sz",
                        "trade_sz",
                    ]
                    available_columns = [col for col in essential_columns if col in df.columns]
                    df = df[available_columns]

                    # Rename columns
                    column_mapping = {
                        "best_bid": f"{venue}_bid_px",
                        "best_ask": f"{venue}_ask_px",
                        "last_px": f"{venue}_last_px",
                        "bid_sz": f"{venue}_bid_sz",
                        "ask_sz": f"{venue}_ask_sz",
                        "trade_sz": f"{venue}_trade_sz",
                    }

                    existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
                    df = df.rename(columns=existing_mapping)

                    # Calculate mid price
                    if f"{venue}_bid_px" in df.columns and f"{venue}_ask_px" in df.columns:
                        df[f"{venue}_mid_px"] = (df[f"{venue}_bid_px"] + df[f"{venue}_ask_px"]) / 2
                    elif f"{venue}_last_px" in df.columns:
                        df[f"{venue}_mid_px"] = df[f"{venue}_last_px"]

                    venue_dfs.append(df)

                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            except Exception as e:
                print(f"        ⚠️ Error loading {file_info['key']}: {e}")
                continue

        if not venue_dfs:
            return None

        # Combine and dedupe
        combined_df = pd.concat(venue_dfs, ignore_index=False)
        combined_df = combined_df.sort_index()
        combined_df = combined_df[~combined_df.index.duplicated(keep="last")]

        return combined_df

    def _align_venues_to_grid(self, venue_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """Align venues to common 1-second grid."""
        # Find common time range
        all_timestamps = []
        for df in venue_data.values():
            all_timestamps.extend(df.index.tolist())

        if not all_timestamps:
            return None

        start_time = min(all_timestamps).floor("S")
        end_time = max(all_timestamps).ceil("S")

        # Create 1-second grid
        grid = pd.date_range(start=start_time, end=end_time, freq="1S", tz="UTC")

        # Align each venue
        aligned_venues = {}
        for venue, df in venue_data.items():
            aligned_df = df.reindex(grid, method="ffill", limit=3)
            aligned_venues[venue] = aligned_df

        # Combine all venues
        combined_panel = pd.concat(aligned_venues.values(), axis=1)

        return combined_panel

    def _concatenate_panels(
        self, all_panels: List[pd.DataFrame], processed_dates: List[str]
    ) -> Optional[pd.DataFrame]:
        """Concatenate all date panels into multi-day panel."""
        if not all_panels:
            return None

        # Concatenate all panels
        multi_day_panel = pd.concat(all_panels, ignore_index=False)
        multi_day_panel = multi_day_panel.sort_index()
        multi_day_panel = multi_day_panel[~multi_day_panel.index.duplicated(keep="last")]

        return multi_day_panel

    def _generate_day_summary(self, date: str, panel: pd.DataFrame):
        """Generate summary for a single day."""
        summary = {
            "date": date,
            "observations": len(panel),
            "date_range": {
                "start": str(panel.index.min()),
                "end": str(panel.index.max()),
                "duration_hours": (panel.index.max() - panel.index.min()).total_seconds() / 3600,
            },
            "venue_coverage": {},
            "columns": len(panel.columns),
        }

        # Venue coverage
        for venue in self.venues:
            venue_cols = [col for col in panel.columns if col.startswith(f"{venue}_")]
            summary["venue_coverage"][venue] = {
                "columns": len(venue_cols),
                "has_mid_px": any("mid_px" in col for col in venue_cols),
            }

        # Save day summary
        with open(f"{self.analysis_dir}/DAY_{date}_SUMMARY.md", "w") as f:
            f.write(f"# Day {date} Assembly Summary\n\n")
            f.write(f"**Date**: {date}\n")
            f.write(f"**Observations**: {summary['observations']:,}\n")
            f.write(f"**Columns**: {summary['columns']}\n")
            f.write(
                f"**Time Range**: {summary['date_range']['start']} to {summary['date_range']['end']}\n"
            )
            f.write(f"**Duration**: {summary['date_range']['duration_hours']:.1f} hours\n\n")

            f.write("## Venue Coverage\n\n")
            for venue, coverage in summary["venue_coverage"].items():
                f.write(f"- **{venue}**: {coverage['columns']} columns")
                if coverage["has_mid_px"]:
                    f.write(" (mid_px ✓)")
                f.write("\n")

    def _generate_assembly_summary(self, multi_day_panel: pd.DataFrame, processed_dates: List[str]):
        """Generate multi-day assembly summary."""
        summary = {
            "assembly_date": datetime.now().isoformat(),
            "processed_dates": processed_dates,
            "total_observations": len(multi_day_panel),
            "total_columns": len(multi_day_panel.columns),
            "date_range": {
                "start": str(multi_day_panel.index.min()),
                "end": str(multi_day_panel.index.max()),
                "duration_hours": (
                    multi_day_panel.index.max() - multi_day_panel.index.min()
                ).total_seconds()
                / 3600,
            },
            "venue_coverage": {},
        }

        # Venue coverage
        for venue in self.venues:
            venue_cols = [col for col in multi_day_panel.columns if col.startswith(f"{venue}_")]
            summary["venue_coverage"][venue] = {
                "columns": len(venue_cols),
                "has_mid_px": any("mid_px" in col for col in venue_cols),
            }

        # Save summary
        with open(f"{self.analysis_dir}/MULTIDAY_ASSEMBLY_SUMMARY.md", "w") as f:
            f.write(f"# Multi-Day BTC-USD Panel Assembly Summary\n\n")
            f.write(f"**Assembly Date**: {summary['assembly_date']}\n")
            f.write(f"**Processed Dates**: {', '.join(summary['processed_dates'])}\n")
            f.write(f"**Total Observations**: {summary['total_observations']:,}\n")
            f.write(f"**Total Columns**: {summary['total_columns']}\n")
            f.write(
                f"**Date Range**: {summary['date_range']['start']} to {summary['date_range']['end']}\n"
            )
            f.write(f"**Duration**: {summary['date_range']['duration_hours']:.1f} hours\n\n")

            f.write("## Venue Coverage\n\n")
            for venue, coverage in summary["venue_coverage"].items():
                f.write(f"- **{venue}**: {coverage['columns']} columns")
                if coverage["has_mid_px"]:
                    f.write(" (mid_px ✓)")
                f.write("\n")

            f.write("\n## Files Generated\n\n")
            for date in summary["processed_dates"]:
                f.write(f"- `panel_1s_inner_real_{date}.parquet`\n")
            f.write(f"- `panel_1s_inner_real_multiday.parquet`\n")


if __name__ == "__main__":
    assembler = MemorySafeMultiDayAssembler()
    success = assembler.assemble_multiday_panel()

    if success:
        print("\n🎉 Multi-day panel assembly completed successfully!")
    else:
        print("\n❌ Multi-day panel assembly failed!")
        sys.exit(1)
