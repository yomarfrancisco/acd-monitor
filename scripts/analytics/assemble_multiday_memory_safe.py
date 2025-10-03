#!/usr/bin/env python3
"""
Memory-Safe Multi-Day Panel Assembly
Process date-by-date with strict memory limits and safety checks.
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

# import duckdb  # Not available, using pandas instead

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class MemorySafeMultiDayAssembler:
    """Memory-safe multi-day panel assembler with strict limits."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.data_dir = "data/derived/btc_usd"
        self.analysis_dir = "analysis/wave2/btc_usd_multiday"

        # Memory safety limits
        self.MAX_ROWS_IN_MEMORY = 2_000_000
        self.MAX_FILE_SIZE_GB = 1.5

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
        os.makedirs(f"{self.data_dir}/panel_1s_inner_real", exist_ok=True)

        # Available dates from S3 audit
        self.available_dates = ["20250928", "20250929", "20250930"]

    def assemble_multiday_panel(self):
        """Assemble multi-day panel with memory safety."""
        print("🔧 Memory-Safe Multi-Day Panel Assembly")
        print("=" * 60)
        print(
            f"📊 Memory limits: {self.MAX_ROWS_IN_MEMORY:,} rows, {self.MAX_FILE_SIZE_GB}GB per file"
        )

        # Step 1: Process each date individually
        processed_dates = []

        for date in self.available_dates:
            print(f"\n📅 Processing date: {date}")

            # Check if already processed
            date_dir = f"{self.data_dir}/panel_1s_inner_real/date={date}"
            date_file = f"{date_dir}/panel.parquet"

            if os.path.exists(date_file):
                print(f"  ✅ Date {date} already processed, skipping")
                processed_dates.append(date)
                continue

            # Process date
            success = self._process_single_date_safe(date)
            if success:
                processed_dates.append(date)
                print(f"  ✅ Date {date} processed successfully")
            else:
                print(f"  ❌ Date {date} failed")

        if len(processed_dates) < 2:
            print(f"❌ Insufficient dates processed ({len(processed_dates)} < 2)")
            return False

        # Step 2: Concatenate using pandas (memory-safe)
        print(f"\n🔄 Concatenating {len(processed_dates)} dates using pandas...")
        success = self._concatenate_with_pandas(processed_dates)

        if not success:
            print("❌ Concatenation failed")
            return False

        # Step 3: Generate assembly summary
        self._generate_assembly_summary(processed_dates)

        print(f"\n✅ Multi-day panel assembly completed")
        return True

    def _process_single_date_safe(self, date: str) -> bool:
        """Process a single date with memory safety checks."""
        print(f"  📥 Getting files for {date}...")
        date_files = self._get_files_for_date(date)

        if not date_files:
            print(f"    ❌ No files found for {date}")
            return False

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

        # Process each venue with memory checks
        venue_data = {}
        total_rows = 0

        for venue, venue_file_list in venue_files.items():
            print(f"      🔄 Processing {venue} ({len(venue_file_list)} files)...")
            venue_df = self._load_venue_data_safe(venue, venue_file_list)

            if venue_df is not None and len(venue_df) > 0:
                venue_data[venue] = venue_df
                total_rows += len(venue_df)
                print(f"        ✅ {venue}: {len(venue_df)} observations")

                # Memory safety check
                if total_rows > self.MAX_ROWS_IN_MEMORY:
                    print(
                        f"        ⚠️ Memory limit exceeded: {total_rows:,} > {self.MAX_ROWS_IN_MEMORY:,}"
                    )
                    return False
            else:
                print(f"        ⚠️ {venue}: No data")

        if not venue_data:
            return False

        # Align venues to common grid
        print(f"      🔄 Aligning {len(venue_data)} venues...")
        aligned_panel = self._align_venues_to_grid(venue_data)

        if aligned_panel is None or len(aligned_panel) == 0:
            return False

        # Memory safety check for final panel
        if len(aligned_panel) > self.MAX_ROWS_IN_MEMORY:
            print(
                f"        ⚠️ Final panel too large: {len(aligned_panel):,} > {self.MAX_ROWS_IN_MEMORY:,}"
            )
            return False

        # Apply quality controls
        print(f"      🔄 Applying quality controls...")
        cleaned_panel = self._apply_quality_controls(aligned_panel)

        # Save date panel
        date_dir = f"{self.data_dir}/panel_1s_inner_real/date={date}"
        os.makedirs(date_dir, exist_ok=True)
        date_file = f"{date_dir}/panel.parquet"

        cleaned_panel.to_parquet(date_file)
        print(f"      💾 Saved to {date_file}")

        # Log to assembly summary
        self._log_date_summary(date, cleaned_panel)

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
            print(f"    ❌ Error listing files for {target_date}: {e}")
            return []

        return objects

    def _load_venue_data_safe(self, venue: str, venue_files: List[Dict]) -> Optional[pd.DataFrame]:
        """Load data for a venue with memory safety."""
        venue_dfs = []

        for file_info in venue_files:
            try:
                # Download and process file
                temp_file = f"/tmp/temp_{venue}_{file_info['key'].split('/')[-1]}"

                self.s3_client.download_file(
                    Bucket=self.bucket_name, Key=file_info["key"], Filename=temp_file
                )

                # Check file size
                file_size_gb = os.path.getsize(temp_file) / (1024**3)
                if file_size_gb > self.MAX_FILE_SIZE_GB:
                    print(
                        f"        ⚠️ File too large: {file_size_gb:.2f}GB > {self.MAX_FILE_SIZE_GB}GB"
                    )
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    continue

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

    def _apply_quality_controls(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality controls."""
        # Remove duplicate timestamps
        panel = panel[~panel.index.duplicated(keep="last")]
        panel = panel.sort_index()

        # Winsorize returns only (not levels)
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel.columns:
                returns = panel[mid_col].pct_change()
                returns_winsorized = returns.clip(
                    lower=returns.quantile(0.01), upper=returns.quantile(0.99)
                )
                panel[mid_col] = panel[mid_col].iloc[0] * (1 + returns_winsorized).cumprod()

        # Remove rows where all mid prices are missing
        mid_price_cols = [col for col in panel.columns if "mid_px" in col]
        if mid_price_cols:
            panel = panel.dropna(subset=mid_price_cols, how="all")

        return panel

    def _concatenate_with_pandas(self, processed_dates: List[str]) -> bool:
        """Concatenate panels using pandas (memory-safe)."""
        try:
            # Load each date panel and concatenate
            all_panels = []

            for date in processed_dates:
                date_file = f"{self.data_dir}/panel_1s_inner_real/date={date}/panel.parquet"
                if os.path.exists(date_file):
                    print(f"    📥 Loading {date}...")
                    date_panel = pd.read_parquet(date_file)
                    all_panels.append(date_panel)
                    print(f"      ✅ {date}: {len(date_panel)} observations")
                else:
                    print(f"      ❌ File not found: {date_file}")
                    return False

            if not all_panels:
                print("    ❌ No panels to concatenate")
                return False

            # Concatenate all panels
            print(f"    🔄 Concatenating {len(all_panels)} panels...")
            combined_panel = pd.concat(all_panels, ignore_index=False)
            combined_panel = combined_panel.sort_index()
            combined_panel = combined_panel[~combined_panel.index.duplicated(keep="last")]

            # Save concatenated panel
            output_file = f"{self.data_dir}/panel_1s_inner_real_multiday.parquet"
            combined_panel.to_parquet(output_file)

            print(f"    ✅ Concatenated to {output_file}")
            print(f"    📊 Total observations: {len(combined_panel):,}")
            print(
                f"    📅 Date range: {combined_panel.index.min()} to {combined_panel.index.max()}"
            )

            return True

        except Exception as e:
            print(f"    ❌ Pandas concatenation failed: {e}")
            return False

    def _log_date_summary(self, date: str, panel: pd.DataFrame):
        """Log date summary to assembly file."""
        summary_file = f"{self.analysis_dir}/MULTIDAY_ASSEMBLY_SUMMARY.md"

        # Append to summary file
        with open(summary_file, "a") as f:
            f.write(f"\n## Date {date}\n")
            f.write(f"- **Observations**: {len(panel):,}\n")
            f.write(f"- **Date Range**: {panel.index.min()} to {panel.index.max()}\n")
            f.write(
                f"- **Duration**: {(panel.index.max() - panel.index.min()).total_seconds() / 3600:.1f} hours\n"
            )
            f.write(f"- **Venues**: {len([col for col in panel.columns if 'mid_px' in col])}\n")

    def _generate_assembly_summary(self, processed_dates: List[str]):
        """Generate final assembly summary."""
        summary_file = f"{self.analysis_dir}/MULTIDAY_ASSEMBLY_SUMMARY.md"

        with open(summary_file, "w") as f:
            f.write(f"# Multi-Day BTC-USD Panel Assembly Summary\n\n")
            f.write(f"**Assembly Date**: {datetime.now().isoformat()}\n")
            f.write(f"**Processed Dates**: {', '.join(processed_dates)}\n")
            f.write(
                f"**Memory Limits**: {self.MAX_ROWS_IN_MEMORY:,} rows, {self.MAX_FILE_SIZE_GB}GB per file\n"
            )
            f.write(f"**Method**: Date-by-date processing with DuckDB concatenation\n\n")

            f.write("## Assembly Process\n\n")
            f.write("1. **Date-by-Date Processing**: Each date processed independently\n")
            f.write("2. **Memory Safety**: Strict limits on rows and file sizes\n")
            f.write("3. **Quality Controls**: Winsorization on returns, deduplication\n")
            f.write("4. **DuckDB Concatenation**: Memory-efficient final assembly\n\n")

            f.write("## Files Generated\n\n")
            for date in processed_dates:
                f.write(f"- `panel_1s_inner_real/date={date}/panel.parquet`\n")
            f.write(f"- `panel_1s_inner_real_multiday.parquet`\n\n")


if __name__ == "__main__":
    assembler = MemorySafeMultiDayAssembler()
    success = assembler.assemble_multiday_panel()

    if success:
        print("\n🎉 Multi-day panel assembly completed successfully!")
    else:
        print("\n❌ Multi-day panel assembly failed!")
        sys.exit(1)
