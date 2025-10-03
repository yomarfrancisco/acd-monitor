#!/usr/bin/env python3
"""
Assemble Multi-Day BTC Panel from S3

Mission: Build multi-day raw BTC windows from S3 → write single wide panel.
"""

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


class MultiDayPanelAssembler:
    """Assemble multi-day BTC panel from S3."""

    def __init__(self):
        self.s3_bucket = "acd-monitor-snapshots"
        self.s3_prefix = "snapshots/BTC-USD/"
        self.tmp_dir = "data/tmp/btc_usd"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        # Create tmp directory
        os.makedirs(self.tmp_dir, exist_ok=True)
        os.makedirs(f"{self.tmp_dir}/raw_7d_by_venue", exist_ok=True)

        # Initialize S3 client
        self.s3_client = boto3.client("s3")

    def assemble_multi_day_panel(self):
        """Assemble multi-day panel from S3."""
        print(f"🔧 Assembling Multi-Day BTC Panel")
        print("=" * 50)

        # Get last 7 calendar days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        print(f"📅 Date range: {start_date} to {end_date}")

        # Find available windows
        available_windows = self._find_available_windows(start_date, end_date)

        if not available_windows:
            print("❌ No available windows found")
            return

        print(f"📊 Found {len(available_windows)} windows")

        # Process each venue
        for venue in self.venues:
            print(f"\n🏢 Processing {venue}...")
            venue_data = self._process_venue_windows(venue, available_windows)

            if venue_data is not None and len(venue_data) > 0:
                # Save venue data
                venue_file = f"{self.tmp_dir}/raw_7d_by_venue/{venue}_7d.parquet"
                venue_data.to_parquet(venue_file)
                print(f"  ✅ Saved {len(venue_data)} observations to {venue_file}")
            else:
                print(f"  ⚠️ No data for {venue}")

        # Create assembly manifest
        self._create_assembly_manifest(available_windows)

        print(f"✅ Multi-day panel assembly completed")
        print(f"📁 Results saved to {self.tmp_dir}")

    def _find_available_windows(self, start_date, end_date):
        """Find available windows in S3."""
        available_windows = []

        try:
            # List objects in S3
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=self.s3_prefix)

            if "Contents" not in response:
                print("❌ No objects found in S3")
                return available_windows

            # Parse window timestamps
            for obj in response["Contents"]:
                key = obj["Key"]

                # Handle both YYYYMMDD/HHMM-HHMM/ and YYYY-MM-DD/HHMM-HHMM/ formats
                if "/ticks/" in key:
                    # Extract date and time from path
                    path_parts = key.split("/")
                    if len(path_parts) >= 3:
                        date_part = path_parts[2]  # Should be YYYYMMDD or YYYY-MM-DD
                        time_part = path_parts[3] if len(path_parts) > 3 else None

                        if time_part and "-" in time_part:
                            # Parse YYYY-MM-DD format
                            try:
                                window_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                                if start_date <= window_date <= end_date:
                                    available_windows.append(
                                        {
                                            "date": window_date,
                                            "time": time_part,
                                            "key": key,
                                            "size": obj["Size"],
                                        }
                                    )
                            except ValueError:
                                continue
                        elif time_part and len(time_part) == 9:  # HHMM-HHMM format
                            # Parse YYYYMMDD format
                            try:
                                window_date = datetime.strptime(date_part, "%Y%m%d").date()
                                if start_date <= window_date <= end_date:
                                    available_windows.append(
                                        {
                                            "date": window_date,
                                            "time": time_part,
                                            "key": key,
                                            "size": obj["Size"],
                                        }
                                    )
                            except ValueError:
                                continue

            # Sort by date and time
            available_windows.sort(key=lambda x: (x["date"], x["time"]))

        except Exception as e:
            print(f"❌ Error listing S3 objects: {e}")
            return available_windows

        return available_windows

    def _process_venue_windows(self, venue: str, available_windows: List[Dict]):
        """Process windows for a specific venue."""
        venue_data_list = []

        for window in available_windows:
            try:
                # Construct S3 key for venue ticks
                venue_key = window["key"].replace("/ticks/", f"/ticks/{venue}/")

                # Check if venue file exists
                try:
                    self.s3_client.head_object(Bucket=self.s3_bucket, Key=venue_key)
                except:
                    # Try alternative path format
                    venue_key = venue_key.replace(
                        f"/ticks/{venue}/", f"/ticks/{venue}/part-0000.parquet"
                    )
                    try:
                        self.s3_client.head_object(Bucket=self.s3_bucket, Key=venue_key)
                    except:
                        continue

                # Download and process venue data
                venue_data = self._download_and_process_venue_data(venue_key, venue)

                if venue_data is not None and len(venue_data) > 0:
                    venue_data_list.append(venue_data)
                    print(f"    ✅ {window['date']} {window['time']}: {len(venue_data)} obs")
                else:
                    print(f"    ⚠️ {window['date']} {window['time']}: No data")

            except Exception as e:
                print(f"    ❌ Error processing {window['date']} {window['time']}: {e}")
                continue

        if venue_data_list:
            # Concatenate all venue data
            combined_data = pd.concat(venue_data_list, ignore_index=True)

            # Remove exact duplicates by (venue, ts_exchange, mid)
            combined_data = combined_data.drop_duplicates(subset=["venue", "ts_exchange", "mid"])

            return combined_data
        else:
            return None

    def _download_and_process_venue_data(self, s3_key: str, venue: str):
        """Download and process venue data from S3."""
        try:
            # Download from S3
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            data = pd.read_parquet(response["Body"])

            # Enforce canonical fields
            required_fields = ["best_bid", "best_ask", "mid", "ts_exchange"]

            if not all(field in data.columns for field in required_fields):
                print(f"    ⚠️ Missing required fields in {s3_key}")
                return None

            # Add venue identifier
            data["venue"] = venue

            # Ensure proper data types
            data["ts_exchange"] = pd.to_datetime(data["ts_exchange"])
            data["best_bid"] = pd.to_numeric(data["best_bid"], errors="coerce")
            data["best_ask"] = pd.to_numeric(data["best_ask"], errors="coerce")
            data["mid"] = pd.to_numeric(data["mid"], errors="coerce")

            # Drop rows with invalid data
            data = data.dropna(subset=["ts_exchange", "mid"])

            return data

        except Exception as e:
            print(f"    ❌ Error downloading {s3_key}: {e}")
            return None

    def _create_assembly_manifest(self, available_windows: List[Dict]):
        """Create assembly manifest."""
        manifest = f"""# Multi-Day BTC Panel Assembly Manifest

## Overview
Successfully assembled multi-day BTC panel from S3 snapshots.

**Assembly Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Date Range**: {available_windows[0]['date'] if available_windows else 'N/A'} to {available_windows[-1]['date'] if available_windows else 'N/A'}
**Total Windows**: {len(available_windows)}

## Available Windows
"""

        for window in available_windows:
            manifest += f"- {window['date']} {window['time']}: {window['size']} bytes\n"

        manifest += f"""
## Venue Data Files
- `{self.tmp_dir}/raw_7d_by_venue/binance_7d.parquet`
- `{self.tmp_dir}/raw_7d_by_venue/coinbase_7d.parquet`
- `{self.tmp_dir}/raw_7d_by_venue/kraken_7d.parquet`
- `{self.tmp_dir}/raw_7d_by_venue/okx_7d.parquet`
- `{self.tmp_dir}/raw_7d_by_venue/bybit_7d.parquet`

## Next Steps
1. Align to 1-second grid (inner join + LOCF fill within 3s)
2. Regenerate environment flags & market structure
3. Prepare Wave-2 variables
4. Run Wave-2 tests on extended sample

---
*Generated by Multi-Day Panel Assembly*
"""

        # Create output directory
        os.makedirs("analysis/wave2/btc_usd_extended", exist_ok=True)

        with open("analysis/wave2/btc_usd_extended/ASSEMBLY.md", "w") as f:
            f.write(manifest)


def main():
    """Main function."""
    assembler = MultiDayPanelAssembler()
    assembler.assemble_multi_day_panel()


if __name__ == "__main__":
    main()
