#!/usr/bin/env python3
"""
Debug Beacon Processing - Investigate why event processing fails
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def debug_beacon_processing():
    """Debug why beacon processing fails to find data"""
    print("🔍 Debug Beacon Processing Issue")
    print("=" * 50)
    
    # Load data for 2025-08-04 BINANCE
    date_str = "20250804"
    venue = "BINANCE"
    file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
    
    df = pd.read_parquet(file_path)
    df['ts'] = pd.to_datetime(df['ts'], utc=True)
    
    print(f"Data loaded: {len(df):,} rows")
    print(f"Time range: {df['ts'].min()} to {df['ts'].max()}")
    
    # Test the beacon detection logic
    print("\nTesting beacon detection logic...")
    
    # Compute micro threshold
    micro_p10 = df['size'].quantile(0.10)
    print(f"Micro threshold (10th percentile): {micro_p10:.6f}")
    
    # Define round levels
    round_levels = list(range(110000, 121000, 1000))
    print(f"Round levels: {round_levels[:5]}...{round_levels[-5:]}")
    
    # Create 1-second VWAP bars
    df['second'] = df['ts'].dt.floor('1S')
    vwap_bars = df.groupby('second').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap_bars.columns = ['second', 'vwap']
    
    print(f"VWAP bars created: {len(vwap_bars)} bars")
    print(f"VWAP range: ${vwap_bars['vwap'].min():,.2f} to ${vwap_bars['vwap'].max():,.2f}")
    
    # Find round-eligible seconds
    band_pct = 0.001  # 0.10%
    round_eligible = set()
    
    for _, row in vwap_bars.iterrows():
        vwap = row['vwap']
        second = row['second']
        
        for level in round_levels:
            distance = abs(vwap - level) / level
            if distance <= band_pct:
                round_eligible.add(second)
                break
    
    print(f"Round-eligible seconds: {len(round_eligible)}")
    
    # Test a specific beacon time
    beacon_time = "2025-08-04 00:56:26.150000+00:00"
    beacon_ts = pd.Timestamp(beacon_time)
    
    print(f"\nTesting beacon time: {beacon_ts}")
    
    # Check if this time is in the data
    print(f"Beacon time in data range: {df['ts'].min() <= beacon_ts <= df['ts'].max()}")
    
    # Check data around this time
    start_time = beacon_ts - pd.Timedelta(seconds=15)
    end_time = beacon_ts + pd.Timedelta(seconds=15)
    
    window_data = df.loc[df['ts'].between(start_time, end_time, inclusive='both')]
    print(f"Data in ±15s window: {len(window_data)} rows")
    
    if len(window_data) > 0:
        print(f"Window range: {window_data['ts'].min()} to {window_data['ts'].max()}")
        print(f"Price range: ${window_data['price'].min():,.2f} to ${window_data['price'].max():,.2f}")
        
        # Test the event processing logic
        print("\nTesting event processing logic...")
        
        # 3-minute window
        left_3 = beacon_ts - pd.Timedelta(minutes=3)
        right_3 = beacon_ts + pd.Timedelta(minutes=3)
        
        print(f"3-minute window: {left_3} to {right_3}")
        
        # Create VWAP bars for this window
        window_df = df.loc[df['ts'].between(left_3, right_3, inclusive='both')].copy()
        print(f"Data in 3-minute window: {len(window_df)} rows")
        
        if len(window_df) > 0:
            window_df['second'] = window_df['ts'].dt.floor('1S')
            vwap_bars_window = window_df.groupby('second').apply(
                lambda x: np.average(x['price'], weights=x['size'])
            ).reset_index()
            vwap_bars_window.columns = ['second', 'vwap']
            
            print(f"VWAP bars in window: {len(vwap_bars_window)}")
            
            # Test coverage calculation
            expected_seconds = int((right_3 - left_3).total_seconds())
            actual_seconds = len(vwap_bars_window)
            coverage = (actual_seconds / expected_seconds) * 100 if expected_seconds > 0 else 0
            
            print(f"Expected seconds: {expected_seconds}")
            print(f"Actual seconds: {actual_seconds}")
            print(f"Coverage: {coverage:.1f}%")
            
            if coverage >= 60:
                print("✅ Coverage check passed")
            else:
                print("❌ Coverage check failed")
        else:
            print("❌ No data in 3-minute window")
    else:
        print("❌ No data in ±15s window")
    
    # Test the beacon detection window logic
    print("\nTesting beacon detection window logic...")
    
    # Sort by timestamp
    df_sorted = df.sort_values('ts').reset_index(drop=True)
    
    # Find the beacon time in the sorted data
    beacon_idx = df_sorted[df_sorted['ts'] == beacon_ts].index
    if len(beacon_idx) > 0:
        print(f"Beacon time found at index: {beacon_idx[0]}")
        
        # Test 10-second window around beacon
        window_size = timedelta(seconds=10)
        window_start = beacon_ts
        window_end = beacon_ts + window_size
        
        window_trades = df_sorted[
            (df_sorted['ts'] >= window_start) & 
            (df_sorted['ts'] < window_end)
        ]
        
        print(f"Trades in 10s window: {len(window_trades)}")
        
        if len(window_trades) > 0:
            # Count micro trades
            micro_trades = window_trades[window_trades['size'] <= micro_p10]
            n_micro = len(micro_trades)
            
            print(f"Micro trades in window: {n_micro}")
            print(f"Micro threshold: {micro_p10:.6f}")
            
            # Check if window has round-eligible seconds
            window_seconds = pd.date_range(
                start=window_start.floor('1S'),
                end=window_end.floor('1S'),
                freq='1S'
            )
            
            has_round_eligible = any(sec in round_eligible for sec in window_seconds)
            print(f"Has round-eligible seconds: {has_round_eligible}")
            
            if n_micro >= 3 and has_round_eligible:
                print("✅ Beacon conditions met")
            else:
                print("❌ Beacon conditions not met")
        else:
            print("❌ No trades in 10s window")
    else:
        print("❌ Beacon time not found in sorted data")

if __name__ == "__main__":
    debug_beacon_processing()




