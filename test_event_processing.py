#!/usr/bin/env python3
"""
Test Event Processing - Debug the specific issue
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_vwap_bars_streaming(df, start_time, end_time):
    """Create 1-second VWAP bars for a time window (streaming)"""
    # Filter to time window using pandas between logic
    window_df = df.loc[df['ts'].between(start_time, end_time, inclusive='both')].copy()
    
    if len(window_df) == 0:
        return pd.DataFrame()
    
    # Create 1-second bins
    window_df['second'] = window_df['ts'].dt.floor('1S')
    
    # Compute VWAP for each second
    vwap_bars = window_df.groupby('second').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap_bars.columns = ['second', 'vwap']
    
    return vwap_bars

def compute_coverage(vwap_bars, start_time, end_time):
    """Compute coverage percentage for a time window"""
    expected_seconds = int((end_time - start_time).total_seconds())
    actual_seconds = len(vwap_bars)
    return (actual_seconds / expected_seconds) * 100 if expected_seconds > 0 else 0

def test_event_processing():
    """Test the event processing logic directly"""
    print("🔍 Test Event Processing Logic")
    print("=" * 50)
    
    # Load data for 2025-08-04 BINANCE
    date_str = "20250804"
    venue = "BINANCE"
    file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
    
    df = pd.read_parquet(file_path)
    df['ts'] = pd.to_datetime(df['ts'], utc=True)
    
    print(f"Data loaded: {len(df):,} rows")
    
    # Test beacon time
    beacon_time = "2025-08-04 00:56:26.150000+00:00"
    evt = pd.Timestamp(beacon_time).tz_convert('UTC')
    
    print(f"Testing beacon time: {evt}")
    
    # Test 3-minute window
    left_3 = evt - pd.Timedelta(minutes=3)
    right_3 = evt + pd.Timedelta(minutes=3)
    
    print(f"3-minute window: {left_3} to {right_3}")
    
    # Test VWAP bars creation
    vwap_pre = create_vwap_bars_streaming(df, left_3, evt)
    vwap_post = create_vwap_bars_streaming(df, evt, right_3)
    
    print(f"Pre-event VWAP bars: {len(vwap_pre)}")
    print(f"Post-event VWAP bars: {len(vwap_post)}")
    
    # Test coverage calculation
    pre_coverage = compute_coverage(vwap_pre, left_3, evt)
    post_coverage = compute_coverage(vwap_post, evt, right_3)
    
    print(f"Pre-event coverage: {pre_coverage:.1f}%")
    print(f"Post-event coverage: {post_coverage:.1f}%")
    
    # Test the coverage threshold
    if pre_coverage >= 60 and post_coverage >= 60:
        print("✅ Coverage check passed")
    else:
        print("❌ Coverage check failed")
    
    # Test with all venues
    print("\nTesting with all venues...")
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    all_venues_data = {}
    
    for v in venues:
        file_path = f"data_v6/views/{v}/{date_str}/ticks_canonical.parquet"
        try:
            df_venue = pd.read_parquet(file_path)
            df_venue['ts'] = pd.to_datetime(df_venue['ts'], utc=True)
            all_venues_data[v] = df_venue
            print(f"  {v}: {len(df_venue):,} rows")
        except Exception as e:
            print(f"  {v}: ERROR - {str(e)}")
            return
    
    # Test coverage for all venues
    pre_returns = {}
    post_returns = {}
    
    for v in all_venues_data.keys():
        vwap_pre = create_vwap_bars_streaming(all_venues_data[v], left_3, evt)
        vwap_post = create_vwap_bars_streaming(all_venues_data[v], evt, right_3)
        
        pre_coverage = compute_coverage(vwap_pre, left_3, evt)
        post_coverage = compute_coverage(vwap_post, evt, right_3)
        
        print(f"  {v}: pre_coverage={pre_coverage:.1f}%, post_coverage={post_coverage:.1f}%")
        
        if pre_coverage >= 60 and post_coverage >= 60:
            print(f"    ✅ {v} passed coverage check")
            # For now, just mark as passed without computing returns
            pre_returns[v] = True
            post_returns[v] = True
        else:
            print(f"    ❌ {v} failed coverage check")
    
    # Check if we have enough venues
    print(f"\nVenues with good coverage: {len(pre_returns)}")
    
    if len(pre_returns) >= 3 and len(post_returns) >= 3:
        print("✅ Sufficient venues for analysis")
    else:
        print("❌ Insufficient venues for analysis")

if __name__ == "__main__":
    test_event_processing()




