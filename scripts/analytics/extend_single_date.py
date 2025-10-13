#!/usr/bin/env python3
"""
Extend Single Date Panel
Add one more date to the existing single-date panel.
"""

import boto3
import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class SingleDateExtender:
    """Extend existing single-date panel with one additional date."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.data_dir = "data/derived/btc_usd"
        self.analysis_dir = "analysis/wave2/btc_usd_multiday"

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

    def extend_panel(self, target_date: str = "20250928"):
        """Extend panel with one additional date."""
        print(f"🔧 Extending Panel with Date: {target_date}")
        print("=" * 50)

        # Load existing panel
        existing_panel_file = f"{self.data_dir}/panel_1s_inner_real_single_date.parquet"
        if not os.path.exists(existing_panel_file):
            print(f"❌ Existing panel not found: {existing_panel_file}")
            return False

        print("📥 Loading existing panel...")
        existing_panel = pd.read_parquet(existing_panel_file)
        print(f"📊 Existing panel: {len(existing_panel)} observations")
        print(f"📅 Existing range: {existing_panel.index.min()} to {existing_panel.index.max()}")

        # Process new date
        print(f"\n📅 Processing new date: {target_date}")
        new_date_panel = self._process_single_date(target_date)

        if new_date_panel is None or len(new_date_panel) == 0:
            print(f"❌ No data processed for {target_date}")
            return False

        print(f"📊 New date panel: {len(new_date_panel)} observations")
        print(f"📅 New date range: {new_date_panel.index.min()} to {new_date_panel.index.max()}")

        # Combine panels
        print("\n🔄 Combining panels...")
        combined_panel = pd.concat([existing_panel, new_date_panel], ignore_index=False)
        combined_panel = combined_panel.sort_index()
        combined_panel = combined_panel[~combined_panel.index.duplicated(keep="last")]

        print(f"✅ Combined panel: {len(combined_panel)} observations")
        print(f"📅 Combined range: {combined_panel.index.min()} to {combined_panel.index.max()}")

        # Save extended panel
        extended_file = f"{self.data_dir}/panel_1s_inner_real_extended.parquet"
        combined_panel.to_parquet(extended_file)
        print(f"💾 Saved extended panel to {extended_file}")

        # Generate summary
        self._generate_extension_summary(
            existing_panel, new_date_panel, combined_panel, target_date
        )

        print(f"\n✅ Panel extension completed")
        return True

    def _process_single_date(self, target_date: str) -> Optional[pd.DataFrame]:
        """Process a single date."""
        print(f"  📥 Getting files for {target_date}...")
        date_files = self._get_files_for_date(target_date)

        if not date_files:
            print(f"    ❌ No files found for {target_date}")
            return None

        print(f"    📊 Found {len(date_files)} files for {target_date}")

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

    def _generate_extension_summary(self, existing_panel, new_panel, combined_panel, target_date):
        """Generate extension summary."""
        summary = {
            "extension_date": datetime.now().isoformat(),
            "target_date": target_date,
            "existing_observations": len(existing_panel),
            "new_observations": len(new_panel),
            "combined_observations": len(combined_panel),
            "existing_range": {
                "start": str(existing_panel.index.min()),
                "end": str(existing_panel.index.max()),
            },
            "new_range": {"start": str(new_panel.index.min()), "end": str(new_panel.index.max())},
            "combined_range": {
                "start": str(combined_panel.index.min()),
                "end": str(combined_panel.index.max()),
                "duration_hours": (
                    combined_panel.index.max() - combined_panel.index.min()
                ).total_seconds()
                / 3600,
            },
        }

        # Save summary
        with open(f"{self.analysis_dir}/EXTENSION_SUMMARY.md", "w") as f:
            f.write(f"# Panel Extension Summary\n\n")
            f.write(f"**Extension Date**: {summary['extension_date']}\n")
            f.write(f"**Target Date Added**: {summary['target_date']}\n")
            f.write(f"**Existing Observations**: {summary['existing_observations']:,}\n")
            f.write(f"**New Observations**: {summary['new_observations']:,}\n")
            f.write(f"**Combined Observations**: {summary['combined_observations']:,}\n\n")

            f.write("## Date Ranges\n\n")
            f.write(
                f"**Existing**: {summary['existing_range']['start']} to {summary['existing_range']['end']}\n"
            )
            f.write(f"**New**: {summary['new_range']['start']} to {summary['new_range']['end']}\n")
            f.write(
                f"**Combined**: {summary['combined_range']['start']} to {summary['combined_range']['end']}\n"
            )
            f.write(
                f"**Total Duration**: {summary['combined_range']['duration_hours']:.1f} hours\n\n"
            )

            f.write("## Files Generated\n\n")
            f.write("- `panel_1s_inner_real_extended.parquet`\n")


if __name__ == "__main__":
    extender = SingleDateExtender()
    success = extender.extend_panel("20250928")

    if success:
        print("\n🎉 Panel extension completed successfully!")
    else:
        print("\n❌ Panel extension failed!")
        sys.exit(1)
