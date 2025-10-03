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
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Add lib modules to path
sys.path.insert(0, str(Path(__file__).parent))

from lib_impact import analyze_impact_spillovers
from lib_ofi import analyze_ofi_spikes
from lib_sync import analyze_large_trade_sync

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


def run_sync_analysis(venues: List[str], date: str) -> Dict:
    """Run large trade synchronization analysis."""
    logger.info("=== Running Large Trade Synchronization Analysis (H1) ===")

    sync_results = {}

    # Load all venue data
    venue_data = {}
    for venue in venues:
        df = load_venue_data(venue, date)
        if not df.empty:
            venue_data[venue] = df

    # Analyze all pairs
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            if venue1 in venue_data and venue2 in venue_data:
                logger.info(f"Analyzing sync: {venue1} ↔ {venue2}")

                result = analyze_large_trade_sync(
                    venue_data[venue1], venue_data[venue2], venue1, venue2
                )

                pair_key = f"{venue1}_{venue2}"
                sync_results[pair_key] = result

                logger.info(
                    f"Sync result: {result['status']} - "
                    f"Correlation: {result.get('observed_correlation', 0):.3f}, "
                    f"P-value: {result.get('p_value', 1):.3f}"
                )

    return sync_results


def run_ofi_analysis(venues: List[str], date: str) -> Dict:
    """Run OFI spike analysis."""
    logger.info("=== Running OFI Spike Analysis (H2) ===")

    ofi_results = {}

    # Load all venue data
    venue_data = {}
    for venue in venues:
        df = load_venue_data(venue, date)
        if not df.empty:
            venue_data[venue] = df

    # Analyze all pairs
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i + 1 :]:
            if venue1 in venue_data and venue2 in venue_data:
                logger.info(f"Analyzing OFI: {venue1} ↔ {venue2}")

                result = analyze_ofi_spikes(venue_data[venue1], venue_data[venue2], venue1, venue2)

                pair_key = f"{venue1}_{venue2}"
                ofi_results[pair_key] = result

                logger.info(
                    f"OFI result: {result['status']} - "
                    f"Correlation: {result.get('observed_correlation', 0):.3f}, "
                    f"P-value: {result.get('p_value', 1):.3f}"
                )

    return ofi_results


def run_impact_analysis(venues: List[str], date: str) -> Dict:
    """Run impact spillovers analysis."""
    logger.info("=== Running Impact Spillovers Analysis (H3) ===")

    impact_results = {}

    # Load all venue data
    venue_data = {}
    for venue in venues:
        df = load_venue_data(venue, date)
        if not df.empty:
            venue_data[venue] = df

    # Analyze all pairs (directional)
    for venue1 in venues:
        for venue2 in venues:
            if venue1 != venue2 and venue1 in venue_data and venue2 in venue_data:
                logger.info(f"Analyzing impact: {venue1} → {venue2}")

                result = analyze_impact_spillovers(
                    venue_data[venue1], venue_data[venue2], venue1, venue2
                )

                pair_key = f"{venue1}_{venue2}"
                impact_results[pair_key] = result

                logger.info(
                    f"Impact result: {result['status']} - "
                    f"Max impact: {result.get('max_impact', 0):.6f}, "
                    f"P-value: {result.get('p_value', 1):.3f}"
                )

    return impact_results


def generate_summary_report(sync_results: Dict, ofi_results: Dict, impact_results: Dict) -> str:
    """Generate comprehensive summary report."""

    report = "# Wave 4 — Optimized Tick-Level Coordination Diagnostics\n\n"
    report += f"**Analysis Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"**Data Source**: Raw tick data (GUID-deduped, 100k trades per venue)\n"
    report += f"**Venues**: BINANCE, COINBASE, BYBITSPOT, BITGET\n"
    report += f"**Method**: Vectorized, chunked analysis with bootstrap validation\n\n"

    # H1: Large Trade Synchronization
    report += "## H1: Large Trade Synchronization\n\n"
    report += "| Pair | Status | Correlation | P-value | Significant |\n"
    report += "|------|--------|-------------|---------|------------|\n"

    for pair, result in sync_results.items():
        status = result.get("status", "UNKNOWN")
        corr = result.get("observed_correlation", 0)
        pval = result.get("p_value", 1)
        sig = result.get("significant", False)

        report += f"| {pair} | {status} | {corr:.3f} | {pval:.3f} | {'✓' if sig else '✗'} |\n"

    # H2: OFI Spike Analysis
    report += "\n## H2: OFI Spike Co-occurrence\n\n"
    report += "| Pair | Status | Correlation | P-value | Significant |\n"
    report += "|------|--------|-------------|---------|------------|\n"

    for pair, result in ofi_results.items():
        status = result.get("status", "UNKNOWN")
        corr = result.get("observed_correlation", 0)
        pval = result.get("p_value", 1)
        sig = result.get("significant", False)

        report += f"| {pair} | {status} | {corr:.3f} | {pval:.3f} | {'✓' if sig else '✗'} |\n"

    # H3: Impact Spillovers
    report += "\n## H3: Price Impact Spillovers\n\n"
    report += "| Pair | Status | Max Impact | P-value | Significant |\n"
    report += "|------|--------|------------|---------|------------|\n"

    for pair, result in impact_results.items():
        status = result.get("status", "UNKNOWN")
        impact = result.get("max_impact", 0)
        pval = result.get("p_value", 1)
        sig = result.get("significant", False)

        report += f"| {pair} | {status} | {impact:.6f} | {pval:.3f} | {'✓' if sig else '✗'} |\n"

    # Summary Statistics
    report += "\n## Summary Statistics\n\n"

    # Count significant results
    sync_sig = sum(1 for r in sync_results.values() if r.get("significant", False))
    ofi_sig = sum(1 for r in ofi_results.values() if r.get("significant", False))
    impact_sig = sum(1 for r in impact_results.values() if r.get("significant", False))

    report += f"- **Significant Sync Pairs**: {sync_sig}/{len(sync_results)}\n"
    report += f"- **Significant OFI Pairs**: {ofi_sig}/{len(ofi_results)}\n"
    report += f"- **Significant Impact Pairs**: {impact_sig}/{len(impact_results)}\n\n"

    # Key Findings
    report += "## Key Findings\n\n"

    if sync_sig > 0:
        report += f"✅ **Coordination Signal**: {sync_sig} venue pairs show significant large trade synchronization\n"
    else:
        report += "❌ **No Coordination**: No significant large trade synchronization detected\n"

    if ofi_sig > 0:
        report += f"✅ **OFI Coordination**: {ofi_sig} venue pairs show significant OFI spike co-occurrence\n"
    else:
        report += "❌ **No OFI Coordination**: No significant OFI spike co-occurrence detected\n"

    if impact_sig > 0:
        report += f"✅ **Impact Spillovers**: {impact_sig} venue pairs show significant price impact spillovers\n"
    else:
        report += "❌ **No Impact Spillovers**: No significant price impact spillovers detected\n"

    return report


def main():
    """Main execution function."""
    logger.info("=== Wave 4 — Full Optimized Tick-Level Analysis ===")

    # Configuration
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    date = "20250925"

    start_time = time.time()

    try:
        # Run all analyses
        sync_results = run_sync_analysis(venues, date)
        ofi_results = run_ofi_analysis(venues, date)
        impact_results = run_impact_analysis(venues, date)

        # Generate summary report
        summary_report = generate_summary_report(sync_results, ofi_results, impact_results)

        # Save results
        output_dir = Path("analysis/flatfiles_ticks/wave4/optimized")

        # Save JSON results
        with open(output_dir / "sync_results.json", "w") as f:
            json.dump(sync_results, f, indent=2)

        with open(output_dir / "ofi_results.json", "w") as f:
            json.dump(ofi_results, f, indent=2)

        with open(output_dir / "impact_results.json", "w") as f:
            json.dump(impact_results, f, indent=2)

        # Save summary report
        with open(output_dir / "summary.md", "w") as f:
            f.write(summary_report)

        logger.info(f"✅ SUCCESS: Full analysis complete in {time.time() - start_time:.1f}s")
        logger.info(f"📊 Results saved to: {output_dir}")

        # Print summary
        print("\n" + "=" * 60)
        print("WAVE 4 TICK-LEVEL ANALYSIS SUMMARY")
        print("=" * 60)
        print(summary_report)

    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
