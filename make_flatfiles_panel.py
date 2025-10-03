#!/usr/bin/env python3
"""
CoinAPI Flat Files → 7-Day 1-Second Panel Builder

Downloads trade data from CoinAPI Flat Files (S3-compatible API),
processes to 1-second candles, and builds aligned cross-venue panel.
"""

import os
import sys
import time
import json
import gzip
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CoinAPIFlatFilesClient:
    """Client for CoinAPI Flat Files S3-compatible API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://s3.flatfiles.coinapi.io"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def list_objects(self, prefix: str) -> List[str]:
        """List objects with given prefix"""
        url = f"{self.base_url}/bucket/?prefix={prefix}"
        headers = {"Authorization": self.api_key, "Accept": "application/xml"}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self._parse_list_response(xml_content)
                else:
                    logger.error(f"LIST failed: {response.status} - {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"LIST error: {e}")
            return []

    def _parse_list_response(self, xml_content: str) -> List[str]:
        """Parse S3 LIST response XML"""
        try:
            root = ET.fromstring(xml_content)
            keys = []
            for contents in root.findall(".//Contents"):
                key_elem = contents.find("Key")
                if key_elem is not None:
                    keys.append(key_elem.text)
            return keys
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []

    async def download_object(self, key: str, output_path: str) -> bool:
        """Download object to file"""
        url = f"{self.base_url}/bucket/{key}"
        headers = {"Authorization": self.api_key}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    with open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    return True
                else:
                    logger.error(f"Download failed for {key}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Download error for {key}: {e}")
            return False


class FlatFilesProcessor:
    """Process downloaded flat files into 1-second panel"""

    def __init__(self, data_dir: str = "data/flatfiles"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def process_trade_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Process a single trade file"""
        try:
            # Read compressed CSV
            with gzip.open(file_path, "rt") as f:
                df = pd.read_csv(f)

            # Validate required columns
            required_cols = ["time_exchange", "price", "size"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing columns: {missing_cols}")
                return None

            # Convert time_exchange to datetime
            df["time_exchange"] = pd.to_datetime(df["time_exchange"])

            # Quality checks
            if not self._validate_trade_data(df):
                return None

            return df

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None

    def _validate_trade_data(self, df: pd.DataFrame) -> bool:
        """Validate trade data quality"""
        if len(df) < 10:
            logger.warning("Too few trades")
            return False

        # Check irregularity (unique time deltas)
        df_sorted = df.sort_values("time_exchange")
        time_deltas = df_sorted["time_exchange"].diff().dropna()
        unique_deltas = time_deltas.nunique()
        if unique_deltas < 5:
            logger.warning(f"Too regular: only {unique_deltas} unique deltas")
            return False

        # Check exact duplicates
        duplicate_rows = df.duplicated().sum()
        duplicate_pct = duplicate_rows / len(df)
        if duplicate_pct > 0.05:
            logger.warning(f"Too many duplicates: {duplicate_pct:.1%}")
            return False

        # Check price variance
        price_std = df["price"].std()
        if price_std < 0.10:
            logger.warning(f"Price std too low: ${price_std:.2f}")
            return False

        return True

    def resample_to_1s(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample trades to 1-second OHLCV candles"""
        df = df.set_index("time_exchange")

        # Resample to 1-second
        ohlcv = (
            df["price"]
            .resample("1S")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        )

        volume = df["size"].resample("1S").sum()
        ohlcv["volume"] = volume

        # Calculate coverage
        total_seconds = 86400  # 24 hours
        coverage = len(ohlcv) / total_seconds

        if coverage < 0.40:
            logger.warning(f"Low coverage: {coverage:.1%}")
            return None

        return ohlcv.dropna()


def get_7_day_period() -> List[str]:
    """Get the same 7-day period used in REST analysis"""
    # Using the same period as REST: 2025-09-25 to 2025-10-01
    start_date = datetime(2025, 9, 25)
    dates = []
    for i in range(7):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime("%Y%m%d"))
    return dates


def get_venue_symbols() -> Dict[str, List[str]]:
    """Get venue to symbol mapping"""
    return {
        "E-BINANCE": ["S-BTC__002DUSDT", "S-BTC__002DUSD"],
        "E-COINBASE": ["S-BTC__002DUSD"],
        "E-KRAKEN": ["S-XBT__002DUSD", "S-BTC__002DUSD"],
    }


async def main():
    """Main execution"""
    # Get API key
    api_key = os.getenv("COINAPI_KEY")
    if not api_key:
        logger.error("COINAPI_KEY environment variable not set")
        sys.exit(1)

    # Get date range and venues
    dates = get_7_day_period()
    venues = get_venue_symbols()

    logger.info(f"Processing {len(dates)} days: {dates}")
    logger.info(f"Venues: {list(venues.keys())}")

    # Initialize processor
    processor = FlatFilesProcessor()

    # Process each day/venue combination
    all_panels = {}

    async with CoinAPIFlatFilesClient(api_key) as client:
        for date in dates:
            logger.info(f"Processing date: {date}")
            date_panels = {}

            for venue, symbols in venues.items():
                logger.info(f"  Processing venue: {venue}")
                venue_panels = []

                for symbol in symbols:
                    prefix = f"T-TRADES/D-{date}/{venue}/{symbol}"
                    logger.info(f"    Listing prefix: {prefix}")

                    # List objects
                    keys = await client.list_objects(prefix)
                    if not keys:
                        logger.warning(f"    No objects found for {prefix}")
                        continue

                    logger.info(f"    Found {len(keys)} objects")

                    # Download and process each file
                    for key in keys:
                        filename = key.split("/")[-1]
                        output_path = processor.data_dir / f"T-TRADES/D-{date}/{venue}/{filename}"
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        # Download
                        success = await client.download_object(key, str(output_path))
                        if not success:
                            continue

                        # Process
                        df = processor.process_trade_file(str(output_path))
                        if df is not None:
                            # Resample to 1s
                            ohlcv = processor.resample_to_1s(df)
                            if ohlcv is not None:
                                venue_panels.append(ohlcv)
                                logger.info(f"    Processed {filename}: {len(ohlcv)} seconds")

                        # Rate limiting
                        await asyncio.sleep(0.3)

                # Combine panels for this venue/date
                if venue_panels:
                    combined = pd.concat(venue_panels).sort_index()
                    date_panels[venue] = combined
                    logger.info(f"  {venue}: {len(combined)} seconds")

            all_panels[date] = date_panels

    # Build final 7-day panel
    logger.info("Building 7-day panel...")

    # Combine all days
    venue_data = {}
    for date, date_panels in all_panels.items():
        for venue, panel in date_panels.items():
            if venue not in venue_data:
                venue_data[venue] = []
            venue_data[venue].append(panel)

    # Concatenate and align
    final_panels = {}
    for venue, panels in venue_data.items():
        if panels:
            combined = pd.concat(panels).sort_index()
            final_panels[venue] = combined
            logger.info(f"{venue}: {len(combined)} seconds total")

    # Save results
    output_dir = Path("analysis/flatfiles_1s")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual venue panels
    for venue, panel in final_panels.items():
        venue_file = output_dir / f"panel_{venue.lower()}_7d_1s.parquet"
        panel.to_parquet(venue_file)
        logger.info(f"Saved {venue}: {venue_file}")

    # Create aligned panel (inner join on timestamps)
    if len(final_panels) >= 2:
        venues = list(final_panels.keys())
        aligned = final_panels[venues[0]]
        for venue in venues[1:]:
            aligned = aligned.join(final_panels[venue], how="inner", rsuffix=f"_{venue}")

        aligned_file = output_dir / "panel/flatfiles_panel_7d_1s.parquet"
        aligned_file.parent.mkdir(exist_ok=True)
        aligned.to_parquet(aligned_file)
        logger.info(f"Saved aligned panel: {aligned_file}")

        # Coverage report
        coverage_file = output_dir / "qc/coverage_table.md"
        coverage_file.parent.mkdir(exist_ok=True)

        with open(coverage_file, "w") as f:
            f.write("# Flat Files Coverage Report\n\n")
            f.write(f"**Date Range**: {dates[0]} to {dates[-1]}\n\n")
            f.write("## Venue Coverage\n\n")
            for venue, panel in final_panels.items():
                coverage = len(panel) / (7 * 86400)
                f.write(f"- **{venue}**: {len(panel):,} seconds ({coverage:.1%} coverage)\n")

            if "aligned" in locals():
                f.write(f"\n## Aligned Panel\n\n")
                f.write(f"- **Total seconds**: {len(aligned):,}\n")
                f.write(f"- **Coverage**: {len(aligned) / (7 * 86400):.1%}\n")

    logger.info("Flat Files processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
