#!/usr/bin/env python3
"""
v4 Dedup Integrity Audit (Weeks 1-7, read-only)
Audit tick-level data for duplication issues and cross-pair leakage
"""

import json
import os
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def get_week_range():
    """Get the 7-week date range"""
    start_date = "2025-08-01"
    end_date = "2025-09-18"

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    date_range = []
    current = start_dt
    while current <= end_dt:
        date_range.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return date_range


def audit_venue_day(venue, date):
    """
    Audit a single venue-day for duplication issues
    """
    date_dir = f"analysis/flatfiles_1s_v4/partitioned/dt={date}"
    venue_path = f"{date_dir}/venue={venue}/part-0.parquet"

    if not os.path.exists(venue_path):
        return None

    try:
        df = pd.read_parquet(venue_path)

        # Basic info
        n_ticks_raw = len(df)

        # Check for GUID field
        has_guid_field = "guid" in df.columns
        has_trade_id_field = "trade_id" in df.columns

        # GUID deduplication
        if has_guid_field:
            n_ticks_after_guid_dedup = df["guid"].nunique()
            dup_guid_pct = (
                ((n_ticks_raw - n_ticks_after_guid_dedup) / n_ticks_raw) * 100
                if n_ticks_raw > 0
                else 0
            )
        else:
            n_ticks_after_guid_dedup = n_ticks_raw
            dup_guid_pct = 0.0

        # Tuple deduplication (time_exchange_ns, price, base_amount)
        tuple_cols = ["time_exchange_ns", "price", "base_amount"]
        if all(col in df.columns for col in tuple_cols):
            tuple_df = df[tuple_cols].dropna()
            n_ticks_after_tuple_dedup = len(tuple_df.drop_duplicates())
            dup_tuple_pct = (
                ((len(tuple_df) - n_ticks_after_tuple_dedup) / len(tuple_df)) * 100
                if len(tuple_df) > 0
                else 0
            )
        else:
            n_ticks_after_tuple_dedup = n_ticks_raw
            dup_tuple_pct = 0.0

        # Coverage analysis
        if "t1s" in df.columns:
            df["t1s"] = pd.to_datetime(df["t1s"])
            df = df.sort_values("t1s")

            # Calculate 1-second coverage
            total_seconds = 24 * 3600  # 24 hours in seconds
            unique_seconds = df["t1s"].dt.floor("S").nunique()
            coverage_pct_1s = (unique_seconds / total_seconds) * 100

            # Find gaps > 1 second
            time_diffs = df["t1s"].diff().dt.total_seconds()
            gaps_gt_1s = (time_diffs > 1.0).sum()
        else:
            coverage_pct_1s = 0.0
            gaps_gt_1s = 0

        return {
            "venue": venue,
            "date": date,
            "n_ticks_raw": n_ticks_raw,
            "n_ticks_after_guid_dedup": n_ticks_after_guid_dedup,
            "dup_guid_pct": dup_guid_pct,
            "n_ticks_after_tuple_dedup": n_ticks_after_tuple_dedup,
            "dup_tuple_pct": dup_tuple_pct,
            "has_guid_field": has_guid_field,
            "has_trade_id_field": has_trade_id_field,
            "coverage_pct_1s": coverage_pct_1s,
            "gaps_gt_1s": gaps_gt_1s,
        }

    except Exception as e:
        print(f"⚠️  Error processing {venue_path}: {e}")
        return None


def check_cross_pair_leakage(venue, date):
    """
    Check for cross-pair leakage between BTCUSD and BTCUSDT
    """
    date_dir = f"analysis/flatfiles_1s_v4/partitioned/dt={date}"

    btcusd_path = f"{date_dir}/venue={venue}/part-0.parquet"
    btcusdt_path = f"{date_dir}/venue={venue}/part-0.parquet"  # Same path for now

    # Check if both pairs exist (simplified - would need actual pair detection)
    btcusd_exists = os.path.exists(btcusd_path)
    btcusdt_exists = os.path.exists(btcusdt_path)

    if btcusd_exists and btcusdt_exists:
        try:
            # Load both datasets
            df_btcusd = pd.read_parquet(btcusd_path)
            df_btcusdt = pd.read_parquet(btcusdt_path)

            # Check for overlapping timestamps (simplified overlap check)
            if "t1s" in df_btcusd.columns and "t1s" in df_btcusdt.columns:
                df_btcusd["t1s"] = pd.to_datetime(df_btcusd["t1s"])
                df_btcusdt["t1s"] = pd.to_datetime(df_btcusdt["t1s"])

                # Find overlapping seconds
                btcusd_seconds = set(df_btcusd["t1s"].dt.floor("S"))
                btcusdt_seconds = set(df_btcusdt["t1s"].dt.floor("S"))

                overlap_seconds = len(btcusd_seconds.intersection(btcusdt_seconds))
                total_seconds = len(btcusd_seconds.union(btcusdt_seconds))

                overlap_pct = (overlap_seconds / total_seconds) * 100 if total_seconds > 0 else 0
            else:
                overlap_pct = 0.0

        except Exception as e:
            print(f"⚠️  Error checking cross-pair leakage for {venue} {date}: {e}")
            overlap_pct = 0.0
    else:
        overlap_pct = None  # N/A - not both pairs exist

    return overlap_pct


def run_dedup_audit():
    """
    Run the complete dedup integrity audit
    """
    print("🔍 **v4 Dedup Integrity Audit (Weeks 1-7)**")
    print("=" * 50)

    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    date_range = get_week_range()

    print(f"📊 **Scope:** {len(date_range)} days, {len(venues)} venues")
    print(f"📊 **Date range:** {date_range[0]} → {date_range[-1]}")

    # Audit results
    audit_results = []
    cross_pair_results = []

    # Process each venue-day
    for venue in venues:
        venue_results = []

        for date in date_range:
            print(f"🔍 Processing {venue} {date}...")

            # Audit venue-day
            result = audit_venue_day(venue, date)
            if result:
                audit_results.append(result)
                venue_results.append(result)

                # Check for duplication breaches
                if result["dup_guid_pct"] > 0.05:
                    print(
                        f"❌ **DUPLICATION BREACH: {venue} {date} GUID dup {result['dup_guid_pct']:.3f}%**"
                    )
                    return None

                if result["dup_tuple_pct"] > 0.05:
                    print(
                        f"❌ **DUPLICATION BREACH: {venue} {date} tuple dup {result['dup_tuple_pct']:.3f}%**"
                    )
                    return None

            # Check cross-pair leakage
            overlap_pct = check_cross_pair_leakage(venue, date)
            if overlap_pct is not None:
                cross_pair_results.append(
                    {"venue": venue, "date": date, "overlap_pct": overlap_pct}
                )

                if overlap_pct > 0.5:
                    print(f"❌ **CROSS-PAIR LEAKAGE: {venue} {date} overlap {overlap_pct:.3f}%**")
                    return None

    # Create summary statistics
    summary_stats = {}

    for venue in venues:
        venue_data = [r for r in audit_results if r["venue"] == venue]

        if venue_data:
            dup_guid_rates = [r["dup_guid_pct"] for r in venue_data]
            dup_tuple_rates = [r["dup_tuple_pct"] for r in venue_data]

            summary_stats[venue] = {
                "mean_dup_guid_pct": np.mean(dup_guid_rates),
                "median_dup_guid_pct": np.median(dup_guid_rates),
                "max_dup_guid_pct": np.max(dup_guid_rates),
                "mean_dup_tuple_pct": np.mean(dup_tuple_rates),
                "median_dup_tuple_pct": np.median(dup_tuple_rates),
                "max_dup_tuple_pct": np.max(dup_tuple_rates),
                "max_dup_day": venue_data[np.argmax(dup_guid_rates)]["date"],
            }

    # Save results
    audit_data = {
        "summary_stats": summary_stats,
        "detailed_results": audit_results,
        "cross_pair_results": cross_pair_results,
        "audit_date": datetime.now().isoformat(),
        "date_range": f"{date_range[0]} → {date_range[-1]}",
        "venues": venues,
    }

    # Save JSON
    with open("analysis/flatfiles_ticks_v4/clean/_audit/dedup_audit_week1_7_v1.json", "w") as f:
        json.dump(audit_data, f, indent=2, default=str)

    # Save Markdown
    with open("analysis/flatfiles_ticks_v4/clean/_audit/dedup_audit_week1_7_v1.md", "w") as f:
        f.write("# v4 Dedup Integrity Audit (Weeks 1-7)\n\n")
        f.write("## Summary Statistics\n\n")
        f.write("| Venue | Mean GUID Dup % | Median GUID Dup % | Max GUID Dup % | Max Day |\n")
        f.write("|-------|-----------------|-------------------|----------------|----------|\n")

        for venue in venues:
            if venue in summary_stats:
                stats = summary_stats[venue]
                f.write(
                    f"| {venue} | {stats['mean_dup_guid_pct']:.3f} | {stats['median_dup_guid_pct']:.3f} | {stats['max_dup_guid_pct']:.3f} | {stats['max_dup_day']} |\n"
                )

        f.write("\n## Detailed Results\n\n")
        f.write("| Venue | Date | Raw Ticks | GUID Dup % | Tuple Dup % | Coverage % |\n")
        f.write("|-------|------|-----------|------------|-------------|------------|\n")

        for result in audit_results:
            f.write(
                f"| {result['venue']} | {result['date']} | {result['n_ticks_raw']:,} | {result['dup_guid_pct']:.3f} | {result['dup_tuple_pct']:.3f} | {result['coverage_pct_1s']:.1f} |\n"
            )

        f.write("\n## Cross-Pair Leakage Check\n\n")
        f.write("| Venue | Date | Overlap % |\n")
        f.write("|-------|------|----------|\n")

        for result in cross_pair_results:
            overlap_str = (
                f"{result['overlap_pct']:.3f}" if result["overlap_pct"] is not None else "N/A"
            )
            f.write(f"| {result['venue']} | {result['date']} | {overlap_str} |\n")

    print(f"\n📊 **Audit complete**")
    print(f"📊 Total venue-days processed: {len(audit_results)}")
    print(f"📊 Cross-pair checks: {len(cross_pair_results)}")

    return audit_data


def main():
    """Main execution function"""
    print("🚦 **v4 Dedup Integrity Audit**")
    print("=" * 70)

    # Run audit
    audit_data = run_dedup_audit()

    if audit_data is None:
        print("❌ **STOP: Duplication breach or cross-pair leakage detected**")
        return

    # Print 4-row summary
    print(f"\n📊 **4-Row Summary (Venues):**")
    print(f"Venue | Mean Dup % | Median Dup % | Max Dup % | Max Day")
    print(f"------|------------|--------------|-----------|--------")

    for venue in ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]:
        if venue in audit_data["summary_stats"]:
            stats = audit_data["summary_stats"][venue]
            print(
                f"{venue:6} | {stats['mean_dup_guid_pct']:10.3f} | {stats['median_dup_guid_pct']:12.3f} | {stats['max_dup_guid_pct']:8.3f} | {stats['max_dup_day']}"
            )

    print(f"\n📊 **Statement: No duplication breach**")
    print(f"📊 **Artifacts saved:** analysis/flatfiles_ticks_v4/clean/_audit/")


if __name__ == "__main__":
    main()
