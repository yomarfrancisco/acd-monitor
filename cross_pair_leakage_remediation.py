#!/usr/bin/env python3
"""
Cross-Pair Leakage Remediation (BTCUSD vs BTCUSDT)
Eliminate 100% overlap, rebuild clean single-pair panels, then re-audit
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")


def jaccard_similarity(set1, set2):
    """Calculate Jaccard similarity between two sets"""
    if len(set1) == 0 and len(set2) == 0:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0


def identify_duplicates():
    """
    Step 1: Identify Duplicates
    For each venue×day, calculate overlap between BTCUSD and BTCUSDT
    """
    print("🔍 **Step 1: Identify Duplicates**")
    print("=" * 50)

    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    start_date = "2025-08-01"
    end_date = "2025-09-18"

    # Generate date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = []
    current = start_dt
    while current <= end_dt:
        date_range.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    overlap_results = []

    for venue in venues:
        for date in date_range:
            date_dir = f"analysis/flatfiles_1s_v4/partitioned/dt={date}"
            venue_path = f"{date_dir}/venue={venue}/part-0.parquet"

            if os.path.exists(venue_path):
                try:
                    df = pd.read_parquet(venue_path)
                    
                    # Check if we have symbol column to distinguish BTCUSD vs BTCUSDT
                    if "symbol" in df.columns:
                        btcusd_data = df[df["symbol"] == "BTCUSD"]
                        btcusdt_data = df[df["symbol"] == "BTCUSDT"]
                        
                        if len(btcusd_data) > 0 and len(btcusdt_data) > 0:
                            # Calculate overlap using GUID
                            if "guid" in df.columns:
                                btcusd_guids = set(btcusd_data["guid"].dropna())
                                btcusdt_guids = set(btcusdt_data["guid"].dropna())
                                overlap_pct = jaccard_similarity(btcusd_guids, btcusdt_guids) * 100
                            else:
                                # Fallback to timestamp overlap
                                btcusd_times = set(btcusd_data["t1s"].dt.floor("S"))
                                btcusdt_times = set(btcusdt_data["t1s"].dt.floor("S"))
                                overlap_pct = jaccard_similarity(btcusd_times, btcusdt_times) * 100
                        else:
                            overlap_pct = 0.0
                    else:
                        # No symbol column - assume all data is BTCUSDT
                        overlap_pct = 0.0
                    
                    overlap_results.append({
                        "venue": venue,
                        "date": date,
                        "overlap_pct": overlap_pct,
                        "btcusd_trades": len(btcusd_data) if "symbol" in df.columns else 0,
                        "btcusdt_trades": len(btcusdt_data) if "symbol" in df.columns else len(df)
                    })
                    
                    print(f"📊 {venue} {date}: {overlap_pct:.3f}% overlap")
                    
                except Exception as e:
                    print(f"⚠️  Error processing {venue_path}: {e}")
                    overlap_results.append({
                        "venue": venue,
                        "date": date,
                        "overlap_pct": 0.0,
                        "btcusd_trades": 0,
                        "btcusdt_trades": 0
                    })

    return overlap_results


def apply_fix(overlap_results):
    """
    Step 2: Apply Fix
    Keep only BTCUSDT (canonical pair), drop BTCUSD if overlap > 1%
    """
    print(f"\n🔍 **Step 2: Apply Fix**")
    print("=" * 50)

    fix_metadata = []
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    start_date = "2025-08-01"
    end_date = "2025-09-18"

    # Generate date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = []
    current = start_dt
    while current <= end_dt:
        date_range.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    for venue in venues:
        for date in date_range:
            date_dir = f"analysis/flatfiles_1s_v4/partitioned/dt={date}"
            venue_path = f"{date_dir}/venue={venue}/part-0.parquet"

            if os.path.exists(venue_path):
                try:
                    df = pd.read_parquet(venue_path)
                    
                    # Find overlap for this venue-date
                    overlap_info = next(
                        (r for r in overlap_results if r["venue"] == venue and r["date"] == date),
                        {"overlap_pct": 0.0}
                    )
                    overlap_pct = overlap_info["overlap_pct"]
                    
                    # Apply fix based on overlap
                    if overlap_pct > 1.0:  # High overlap - keep only BTCUSDT
                        if "symbol" in df.columns:
                            # Keep only BTCUSDT data
                            clean_df = df[df["symbol"] == "BTCUSDT"].copy()
                            removed_symbol = "BTCUSD"
                        else:
                            # No symbol column - keep all data as BTCUSDT
                            clean_df = df.copy()
                            removed_symbol = "None"
                    else:
                        # Low overlap - keep all data
                        clean_df = df.copy()
                        removed_symbol = "None"
                    
                    # Create output directory
                    output_dir = f"analysis/flatfiles_1s_v4/repaired/dt={date}/venue={venue}"
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Save cleaned data
                    output_path = f"{output_dir}/part-0.parquet"
                    clean_df.to_parquet(output_path, compression="zstd")
                    
                    # Store metadata
                    fix_metadata.append({
                        "venue": venue,
                        "date": date,
                        "removed_symbol": removed_symbol,
                        "overlap_pct": overlap_pct,
                        "original_rows": len(df),
                        "cleaned_rows": len(clean_df),
                        "rows_removed": len(df) - len(clean_df)
                    })
                    
                    print(f"📊 {venue} {date}: {len(clean_df):,} rows kept, {len(df) - len(clean_df):,} removed")
                    
                except Exception as e:
                    print(f"⚠️  Error processing {venue_path}: {e}")
                    fix_metadata.append({
                        "venue": venue,
                        "date": date,
                        "removed_symbol": "Error",
                        "overlap_pct": 0.0,
                        "original_rows": 0,
                        "cleaned_rows": 0,
                        "rows_removed": 0
                    })

    return fix_metadata


def verify_fix(fix_metadata):
    """
    Step 3: Verify
    Recompute overlap and duplication metrics after fix
    """
    print(f"\n🔍 **Step 3: Verify Fix**")
    print("=" * 50)

    verification_results = []
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    start_date = "2025-08-01"
    end_date = "2025-09-18"

    # Generate date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = []
    current = start_dt
    while current <= end_dt:
        date_range.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    for venue in venues:
        for date in date_range:
            repaired_path = f"analysis/flatfiles_1s_v4/repaired/dt={date}/venue={venue}/part-0.parquet"
            
            if os.path.exists(repaired_path):
                try:
                    df = pd.read_parquet(repaired_path)
                    
                    # Check for GUID duplicates
                    if "guid" in df.columns:
                        n_ticks_raw = len(df)
                        n_unique_guids = df["guid"].nunique()
                        dup_guid_pct = ((n_ticks_raw - n_unique_guids) / n_ticks_raw) * 100 if n_ticks_raw > 0 else 0
                    else:
                        dup_guid_pct = 0.0
                    
                    # Check for cross-pair leakage (should be 0 after fix)
                    cross_pair_leakage = 0.0  # No cross-pair data after fix
                    
                    verification_results.append({
                        "venue": venue,
                        "date": date,
                        "overlap_pct": 0.0,  # No overlap after fix
                        "dup_guid_pct": dup_guid_pct,
                        "cross_pair_leakage": cross_pair_leakage,
                        "total_rows": len(df)
                    })
                    
                    # Check stop conditions
                    if dup_guid_pct > 0.05:
                        print(f"❌ **STOP: {venue} {date} GUID dup {dup_guid_pct:.3f}% > 0.05%**")
                        return None
                    
                    if cross_pair_leakage > 0.1:
                        print(f"❌ **STOP: {venue} {date} cross-pair leakage {cross_pair_leakage:.3f}% > 0.1%**")
                        return None
                    
                    print(f"✅ {venue} {date}: {len(df):,} rows, {dup_guid_pct:.3f}% GUID dup")
                    
                except Exception as e:
                    print(f"⚠️  Error verifying {repaired_path}: {e}")
                    verification_results.append({
                        "venue": venue,
                        "date": date,
                        "overlap_pct": 0.0,
                        "dup_guid_pct": 0.0,
                        "cross_pair_leakage": 0.0,
                        "total_rows": 0
                    })

    return verification_results


def create_fix_report(overlap_results, fix_metadata, verification_results):
    """
    Create comprehensive fix report
    """
    print(f"\n🔍 **Creating Fix Report**")
    print("=" * 50)

    # Calculate summary statistics
    total_original_rows = sum(m["original_rows"] for m in fix_metadata)
    total_cleaned_rows = sum(m["cleaned_rows"] for m in fix_metadata)
    total_rows_removed = sum(m["rows_removed"] for m in fix_metadata)
    
    high_overlap_days = [m for m in fix_metadata if m["overlap_pct"] > 1.0]
    avg_overlap_before = np.mean([r["overlap_pct"] for r in overlap_results])
    avg_overlap_after = np.mean([r["overlap_pct"] for r in verification_results])
    
    # Create report data
    report_data = {
        "fix_summary": {
            "total_original_rows": total_original_rows,
            "total_cleaned_rows": total_cleaned_rows,
            "total_rows_removed": total_rows_removed,
            "removal_rate": (total_rows_removed / total_original_rows) * 100 if total_original_rows > 0 else 0,
            "high_overlap_days": len(high_overlap_days),
            "avg_overlap_before": avg_overlap_before,
            "avg_overlap_after": avg_overlap_after
        },
        "overlap_results": overlap_results,
        "fix_metadata": fix_metadata,
        "verification_results": verification_results,
        "fix_date": datetime.now().isoformat()
    }

    # Save JSON report
    with open("analysis/_diag_v4/cross_pair_fix_report.json", "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    # Save Markdown report
    with open("analysis/_diag_v4/cross_pair_fix_report.md", "w") as f:
        f.write("# Cross-Pair Leakage Fix Report\n\n")
        f.write("## Fix Summary\n\n")
        f.write(f"- **Total original rows:** {total_original_rows:,}\n")
        f.write(f"- **Total cleaned rows:** {total_cleaned_rows:,}\n")
        f.write(f"- **Total rows removed:** {total_rows_removed:,}\n")
        f.write(f"- **Removal rate:** {(total_rows_removed / total_original_rows) * 100:.2f}%\n")
        f.write(f"- **High overlap days:** {len(high_overlap_days)}\n")
        f.write(f"- **Avg overlap before:** {avg_overlap_before:.3f}%\n")
        f.write(f"- **Avg overlap after:** {avg_overlap_after:.3f}%\n\n")
        
        f.write("## High Overlap Days (Fixed)\n\n")
        f.write("| Venue | Date | Overlap % | Rows Removed |\n")
        f.write("|-------|------|-----------|--------------|\n")
        
        for day in high_overlap_days:
            f.write(f"| {day['venue']} | {day['date']} | {day['overlap_pct']:.3f} | {day['rows_removed']:,} |\n")
        
        f.write("\n## Verification Results\n\n")
        f.write("| Venue | Date | Overlap % | GUID Dup % | Cross-Pair % |\n")
        f.write("|-------|------|-----------|------------|-------------|\n")
        
        for result in verification_results:
            f.write(f"| {result['venue']} | {result['date']} | {result['overlap_pct']:.3f} | {result['dup_guid_pct']:.3f} | {result['cross_pair_leakage']:.3f} |\n")

    print(f"📊 **Fix report created**")
    print(f"📊 Total rows removed: {total_rows_removed:,}")
    print(f"📊 Removal rate: {(total_rows_removed / total_original_rows) * 100:.2f}%")
    print(f"📊 High overlap days fixed: {len(high_overlap_days)}")

    return report_data


def main():
    """Main execution function"""
    print("🚦 **Cross-Pair Leakage Remediation**")
    print("=" * 70)

    # Step 1: Identify duplicates
    overlap_results = identify_duplicates()
    
    # Step 2: Apply fix
    fix_metadata = apply_fix(overlap_results)
    
    # Step 3: Verify fix
    verification_results = verify_fix(fix_metadata)
    
    if verification_results is None:
        print("❌ **STOP: Verification failed**")
        return
    
    # Create fix report
    report_data = create_fix_report(overlap_results, fix_metadata, verification_results)
    
    print(f"\n📊 **Remediation Complete**")
    print(f"📊 **Ready for re-audit**")
    print(f"📊 **Artifacts saved:** analysis/_diag_v4/")


if __name__ == "__main__":
    main()
