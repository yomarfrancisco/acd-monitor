#!/usr/bin/env python3
"""
Wave 4 — Full Optimized Tick-Level Analysis.
Runs all three diagnostics: sync, OFI, and impact spillovers.
"""
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Add lib modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import analysis modules
from lib_impact import analyze_impact_spillovers  # noqa: E402
from lib_ofi import analyze_ofi_spikes  # noqa: E402
from lib_sync import analyze_large_trade_sync  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_venue_data(venue: str, date: str) -> pd.DataFrame:
    """Load pre-processed venue data."""
    data_file = Path(f"analysis/flatfiles_ticks/wave4/optimized/venue={venue}_date={date}.parquet")

    if not data_file.exists():
        logger.warning(f"No data found for {venue} on {date}")
        return pd.DataFrame()

    df = pd.read_parquet(data_file)
    logger.info(f"Loaded {len(df):,} bins for {venue}")
    return df


def run_full_analysis(venues: list, date: str) -> dict:
    """Run complete Wave 4 analysis."""
    logger.info("=== Wave 4 Full Analysis ===")

    start_time = time.time()
    results = {"sync": {}, "ofi": {}, "impact": {}}

    # Load venue data
    venue_data = {}
    for venue in venues:
        df = load_venue_data(venue, date)
        if not df.empty:
            venue_data[venue] = df

    # Sync analysis (pairwise)
    logger.info("Running sync analysis...")
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            if venue1 in venue_data and venue2 in venue_data:
                pair_key = f"{venue1}_{venue2}"
                result = analyze_large_trade_sync(
                    venue_data[venue1], venue_data[venue2], venue1, venue2
                )
                results["sync"][pair_key] = result

    # OFI analysis (pairwise)
    logger.info("Running OFI analysis...")
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            if venue1 in venue_data and venue2 in venue_data:
                pair_key = f"{venue1}_{venue2}"
                result = analyze_ofi_spikes(venue_data[venue1], venue_data[venue2], venue1, venue2)
                results["ofi"][pair_key] = result

    # Impact analysis (directional)
    logger.info("Running impact analysis...")
    for venue1 in venues:
        for venue2 in venues:
            if venue1 != venue2 and venue1 in venue_data and venue2 in venue_data:
                pair_key = f"{venue1}_{venue2}"
                result = analyze_impact_spillovers(
                    venue_data[venue1], venue_data[venue2], venue1, venue2
                )
                results["impact"][pair_key] = result

    elapsed = time.time() - start_time
    logger.info(f"Analysis complete in {elapsed:.1f}s")

    return results


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Wave 4 Full Analysis")
    parser.add_argument("--date", default="20250925", help="Date to analyze")
    parser.add_argument(
        "--venues", default="BINANCE,COINBASE,BYBITSPOT,BITGET", help="Comma-separated venues"
    )
    parser.add_argument("--out", default="analysis/flatfiles_ticks/wave4", help="Output directory")

    args = parser.parse_args()

    try:
        # Parse venues
        venues = [v.strip() for v in args.venues.split(",")]

        # Run analysis
        results = run_full_analysis(venues, args.date)

        # Save results
        output_dir = Path(args.out)
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_dir}")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
