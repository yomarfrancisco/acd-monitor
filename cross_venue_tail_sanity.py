#!/usr/bin/env python3
"""
Cross-Venue Tail Sanity Check (2025-09-18 23:59:00–23:59:59 UTC)
Analyze price consistency across venues in the final minute of trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import warnings

warnings.filterwarnings("ignore")


def load_venue_data(venue, date):
    """Load venue data for the specified date"""
    file_path = f"analysis/flatfiles_1s_v4/partitioned/dt={date}/venue={venue}/part-0.parquet"
    
    try:
        df = pd.read_parquet(file_path)
        df["t1s"] = pd.to_datetime(df["t1s"])
        df = df.sort_values("t1s")
        return df
    except Exception as e:
        print(f"⚠️  Error loading {venue} data: {e}")
        return pd.DataFrame()


def build_joined_table(date, target_minute="23:59"):
    """
    Build a joined table at 1-second resolution for all venues
    """
    print(f"🔍 **Building Cross-Venue Joined Table for {date} {target_minute}**")
    print("=" * 70)
    
    venues = ["BINANCE", "COINBASE", "BITGET", "BYBITSPOT"]
    venue_data = {}
    
    # Load data for each venue
    for venue in venues:
        df = load_venue_data(venue, date)
        if not df.empty:
            # Filter to target minute
            df["time_str"] = df["t1s"].dt.strftime("%H:%M")
            minute_data = df[df["time_str"] == target_minute].copy()
            
            if not minute_data.empty:
                minute_data = minute_data.set_index("t1s")
                venue_data[venue] = minute_data
                print(f"✅ {venue}: {len(minute_data)} seconds")
            else:
                print(f"⚠️  {venue}: No data for {target_minute}")
        else:
            print(f"❌ {venue}: No data file found")
    
    if len(venue_data) < 3:
        print(f"❌ **STOP: Only {len(venue_data)} venues have data (need ≥3)**")
        return None
    
    # Build joined table
    print(f"\n📊 **Building joined table with {len(venue_data)} venues**")
    
    # Start with the first venue
    first_venue = list(venue_data.keys())[0]
    joined_df = venue_data[first_venue][["close"]].copy()
    joined_df.columns = [f"{first_venue}_close"]
    
    # Join other venues
    for venue in list(venue_data.keys())[1:]:
        venue_close = venue_data[venue][["close"]].copy()
        venue_close.columns = [f"{venue}_close"]
        joined_df = joined_df.join(venue_close, how="inner")
    
    # Add per-second analysis
    close_cols = [col for col in joined_df.columns if col.endswith("_close")]
    joined_df["max_price"] = joined_df[close_cols].max(axis=1)
    joined_df["min_price"] = joined_df[close_cols].min(axis=1)
    joined_df["price_spread_usd"] = joined_df["max_price"] - joined_df["min_price"]
    joined_df["price_spread_bps"] = (joined_df["price_spread_usd"] / joined_df[close_cols].mean(axis=1)) * 10000
    
    return joined_df, venue_data


def analyze_spreads(joined_df):
    """
    Analyze price spreads and coverage
    """
    print(f"\n📊 **Spread Analysis**")
    print("=" * 50)
    
    # Per-second analysis
    median_spread_bps = joined_df["price_spread_bps"].median()
    p95_spread_bps = joined_df["price_spread_bps"].quantile(0.95)
    max_spread_bps = joined_df["price_spread_bps"].max()
    
    print(f"📊 **Median spread:** {median_spread_bps:.2f} bps")
    print(f"📊 **95th percentile spread:** {p95_spread_bps:.2f} bps")
    print(f"📊 **Max spread:** {max_spread_bps:.2f} bps")
    
    # Coverage analysis
    close_cols = [col for col in joined_df.columns if col.endswith("_close")]
    coverage = {}
    for col in close_cols:
        venue = col.replace("_close", "")
        non_null_count = joined_df[col].notna().sum()
        coverage[venue] = non_null_count
    
    print(f"\n📊 **Per-venue second counts:**")
    for venue, count in coverage.items():
        print(f"   {venue}: {count} seconds")
    
    return {
        "median_spread_bps": median_spread_bps,
        "p95_spread_bps": p95_spread_bps,
        "max_spread_bps": max_spread_bps,
        "coverage": coverage
    }


def check_usdt_basis(joined_df):
    """
    Check USD vs USDT basis if applicable
    """
    print(f"\n📊 **USD vs USDT Basis Check**")
    print("=" * 50)
    
    # Check if we have both USD and USDT venues
    close_cols = [col for col in joined_df.columns if col.endswith("_close")]
    
    # Assume BINANCE is USDT, others are USD
    usdt_cols = [col for col in close_cols if "BINANCE" in col]
    usd_cols = [col for col in close_cols if "BINANCE" not in col]
    
    if usdt_cols and usd_cols:
        # Calculate USDT basis
        usdt_median = joined_df[usdt_cols].mean(axis=1)
        usd_median = joined_df[usd_cols].mean(axis=1)
        
        # USDT basis in bps
        usdt_basis_bps = ((usdt_median - usd_median) / usd_median) * 10000
        median_basis_bps = usdt_basis_bps.median()
        
        print(f"📊 **USDT basis (median):** {median_basis_bps:.2f} bps")
        print(f"📊 **USDT basis (95th percentile):** {usdt_basis_bps.quantile(0.95):.2f} bps")
        
        return {
            "usdt_basis_bps": median_basis_bps,
            "usdt_basis_p95": usdt_basis_bps.quantile(0.95)
        }
    else:
        print("📊 **No USD/USDT basis to check**")
        return None


def integrity_checks(joined_df, target_minute="23:59"):
    """
    Perform integrity checks
    """
    print(f"\n📊 **Integrity Checks**")
    print("=" * 50)
    
    issues = []
    
    # Check for $0 or NaN prices
    close_cols = [col for col in joined_df.columns if col.endswith("_close")]
    for col in close_cols:
        zero_prices = (joined_df[col] == 0).sum()
        nan_prices = joined_df[col].isna().sum()
        
        if zero_prices > 0:
            issues.append(f"{col}: {zero_prices} zero prices")
        if nan_prices > 0:
            issues.append(f"{col}: {nan_prices} NaN prices")
    
    # Check UTC bounds
    time_bounds = joined_df.index.min(), joined_df.index.max()
    expected_start = pd.Timestamp(f"2025-09-18 {target_minute}:00", tz="UTC")
    expected_end = pd.Timestamp(f"2025-09-18 {target_minute}:59", tz="UTC")
    
    # Convert time_bounds to UTC if needed
    if time_bounds[0].tz is None:
        time_bounds = (time_bounds[0].tz_localize("UTC"), time_bounds[1].tz_localize("UTC"))
    elif time_bounds[0].tz != expected_start.tz:
        time_bounds = (time_bounds[0].tz_convert("UTC"), time_bounds[1].tz_convert("UTC"))
    
    if time_bounds[0] < expected_start or time_bounds[1] > expected_end:
        issues.append(f"Time bounds outside expected range: {time_bounds}")
    
    if issues:
        print("⚠️  **Issues found:**")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("✅ **No integrity issues found**")
    
    return issues


def main():
    """Main execution function"""
    print("🚦 **Cross-Venue Tail Sanity Check**")
    print("=" * 70)
    
    date = "2025-09-18"
    target_minute = "23:59"
    
    # Build joined table
    result = build_joined_table(date, target_minute)
    if result is None:
        return
    
    joined_df, venue_data = result
    
    # Analyze spreads
    spread_analysis = analyze_spreads(joined_df)
    
    # Check USDT basis
    basis_analysis = check_usdt_basis(joined_df)
    
    # Integrity checks
    integrity_issues = integrity_checks(joined_df, target_minute)
    
    # Display 10-row tail
    print(f"\n📊 **10-Row Tail Joined Table (Last 10 seconds)**")
    print("=" * 80)
    
    tail_df = joined_df.tail(10).copy()
    display_cols = [col for col in tail_df.columns if col.endswith("_close")] + ["price_spread_bps"]
    print(tail_df[display_cols].round(2).to_string())
    
    # Summary
    print(f"\n📊 **Summary**")
    print("=" * 50)
    print(f"📊 **Median spread:** {spread_analysis['median_spread_bps']:.2f} bps")
    print(f"📊 **95th percentile spread:** {spread_analysis['p95_spread_bps']:.2f} bps")
    print(f"📊 **Per-venue second counts:** {spread_analysis['coverage']}")
    
    if basis_analysis:
        print(f"📊 **USDT basis:** {basis_analysis['usdt_basis_bps']:.2f} bps")
        print(f"📊 **Spreads consistent with USD↔USDT basis:** {'Yes' if abs(spread_analysis['median_spread_bps'] - basis_analysis['usdt_basis_bps']) < 10 else 'No'}")
    else:
        print(f"📊 **Spreads consistent with USD↔USDT basis:** N/A")
    
    # Stop condition check
    if spread_analysis['median_spread_bps'] > 30:
        if basis_analysis and abs(spread_analysis['median_spread_bps'] - basis_analysis['usdt_basis_bps']) < 10:
            print(f"✅ **Spreads > 30 bps but explained by USDT basis**")
        else:
            print(f"❌ **STOP: Spreads > 30 bps and cannot be explained by basis**")
            return
    
    print(f"\n✅ **Cross-venue tail sanity check complete**")


if __name__ == "__main__":
    main()
