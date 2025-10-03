#!/usr/bin/env python3
"""
Single Date Panel Assembly
Process just one date to create a working panel.
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


class SingleDatePanelAssembler:
    """Assemble panel for a single date."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.data_dir = "data/derived/btc_usd"
        self.analysis_dir = "analysis/wave2/btc_usd_extended"

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

    def assemble_single_date_panel(self, target_date: str = "20250929"):
        """Assemble panel for a single date."""
        print(f"🔧 Single Date Panel Assembly ({target_date})")
        print("=" * 60)

        # Step 1: Get files for target date
        print(f"📥 Getting files for {target_date}...")
        date_files = self._get_files_for_date(target_date)

        if not date_files:
            print(f"❌ No files found for {target_date}")
            return False

        print(f"📊 Found {len(date_files)} files for {target_date}")

        # Step 2: Process files by venue
        venue_data = {}
        for venue in self.venues:
            print(f"\n🔄 Processing {venue}...")
            venue_files = [f for f in date_files if venue in f["key"]]
            if venue_files:
                venue_df = self._load_venue_data_single(venue, venue_files)
                if venue_df is not None and len(venue_df) > 0:
                    venue_data[venue] = venue_df
                    print(f"  ✅ {venue}: {len(venue_df)} observations")
                else:
                    print(f"  ⚠️ {venue}: No data")
            else:
                print(f"  ❌ {venue}: No files found")

        if not venue_data:
            print("❌ No venue data loaded")
            return False

        # Step 3: Align venues to common grid
        print(f"\n🔄 Aligning {len(venue_data)} venues...")
        aligned_panel = self._align_venues_to_grid(venue_data)

        if aligned_panel is None or len(aligned_panel) == 0:
            print("❌ Alignment failed")
            return False

        print(f"✅ Aligned panel: {len(aligned_panel)} observations")
        print(f"📅 Time range: {aligned_panel.index.min()} to {aligned_panel.index.max()}")

        # Step 4: Apply quality controls
        print("\n🔄 Applying quality controls...")
        cleaned_panel = self._apply_quality_controls(aligned_panel)

        # Step 5: Save panel
        panel_file = f"{self.data_dir}/panel_1s_inner_real_single_date.parquet"
        cleaned_panel.to_parquet(panel_file)
        print(f"💾 Saved panel to {panel_file}")

        # Step 6: Generate report
        self._generate_assembly_report(cleaned_panel, target_date, date_files)

        print(f"\n✅ Single date panel assembly completed")
        return True

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
            print(f"❌ Error listing files: {e}")
            return []

        return objects

    def _load_venue_data_single(
        self, venue: str, venue_files: List[Dict]
    ) -> Optional[pd.DataFrame]:
        """Load data for a venue."""
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
                print(f"    ⚠️ Error loading {file_info['key']}: {e}")
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

    def _apply_quality_controls(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality controls."""
        # Remove duplicate timestamps
        panel = panel[~panel.index.duplicated(keep="last")]
        panel = panel.sort_index()

        # Simple quality controls - remove rows where all mid prices are missing
        mid_price_cols = [col for col in panel.columns if "mid_px" in col]
        if mid_price_cols:
            panel = panel.dropna(subset=mid_price_cols, how="all")

        return panel

    def _generate_assembly_report(
        self, panel: pd.DataFrame, target_date: str, date_files: List[Dict]
    ):
        """Generate assembly report."""
        report = {
            "assembly_date": datetime.now().isoformat(),
            "target_date": target_date,
            "total_files": len(date_files),
            "panel_observations": len(panel),
            "panel_columns": len(panel.columns),
            "date_range": {
                "start": str(panel.index.min()),
                "end": str(panel.index.max()),
                "duration_hours": (panel.index.max() - panel.index.min()).total_seconds() / 3600,
            },
            "venue_coverage": {},
        }

        # Venue coverage
        for venue in self.venues:
            venue_cols = [col for col in panel.columns if col.startswith(f"{venue}_")]
            report["venue_coverage"][venue] = {
                "columns": len(venue_cols),
                "has_mid_px": any("mid_px" in col for col in venue_cols),
            }

        # Save report
        with open(f"{self.analysis_dir}/single_date_assembly_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        with open(f"{self.analysis_dir}/SINGLE_DATE_ASSEMBLY_SUMMARY.md", "w") as f:
            f.write(f"# Single Date BTC-USD Panel Assembly Report\n\n")
            f.write(f"**Assembly Date**: {report['assembly_date']}\n")
            f.write(f"**Target Date**: {report['target_date']}\n")
            f.write(f"**Files Processed**: {report['total_files']}\n")
            f.write(f"**Panel Observations**: {report['panel_observations']:,}\n")
            f.write(f"**Panel Columns**: {report['panel_columns']}\n")
            f.write(
                f"**Time Range**: {report['date_range']['start']} to {report['date_range']['end']}\n"
            )
            f.write(f"**Duration**: {report['date_range']['duration_hours']:.1f} hours\n\n")

            f.write("## Venue Coverage\n\n")
            for venue, coverage in report["venue_coverage"].items():
                f.write(f"- **{venue}**: {coverage['columns']} columns")
                if coverage["has_mid_px"]:
                    f.write(" (mid_px ✓)")
                f.write("\n")


if __name__ == "__main__":
    assembler = SingleDatePanelAssembler()
    success = assembler.assemble_single_date_panel("20250929")

    if success:
        print("\n🎉 Single date panel assembly completed successfully!")
    else:
        print("\n❌ Single date panel assembly failed!")
        sys.exit(1)
