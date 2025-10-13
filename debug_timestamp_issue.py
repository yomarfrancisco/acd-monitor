#!/usr/bin/env python3
"""
Debug Timestamp Issue - Find exact location of comparison error
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def debug_timestamp_comparison():
    """Debug the exact timestamp comparison issue"""
    print("🔍 DEBUG: Timestamp Comparison Issue")
    print("=" * 50)
    
    # Load beacon cache
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    beacons = {}
    
    # Create beacon cache (same as Step 1)
    date_str = "20250804"
    venue = "BINANCE"
    
    np.random.seed(1337 + hash(f"{date_str}_{venue}") % 1000)
    
    # Create one beacon
    hour = np.random.randint(0, 24)
    minute = np.random.randint(0, 60)
    second = np.random.randint(0, 60)
    
    t_event = pd.Timestamp(date_str, tz='UTC').replace(
        hour=hour, minute=minute, second=second
    )
    
    beacon = {
        't_event': t_event,
        'level': 115000,
        'n_trades_10s': 10,
        'n_micro_10s': 5,
        'micro_p10': 0.005
    }
    
    print(f"1) Beacon timestamp:")
    print(f"   Type: {type(beacon['t_event'])}")
    print(f"   Value: {beacon['t_event']}")
    print(f"   TZ: {beacon['t_event'].tz}")
    
    # Load parquet data
    df = pd.read_parquet("data_v6/views/BINANCE/20250804/ticks_canonical.parquet")
    print(f"\n2) Parquet timestamp column:")
    print(f"   Type: {type(df['ts'])}")
    print(f"   Dtype: {df['ts'].dtype}")
    print(f"   First value: {df['ts'].iloc[0]}")
    print(f"   First value type: {type(df['ts'].iloc[0])}")
    
    # Test the problematic comparison
    print(f"\n3) Testing comparisons:")
    
    # Test 1: Direct comparison
    try:
        result = df['ts'] >= beacon['t_event']
        print(f"   df['ts'] >= beacon['t_event']: SUCCESS")
    except Exception as e:
        print(f"   df['ts'] >= beacon['t_event']: ERROR - {e}")
    
    # Test 2: Convert beacon timestamp
    try:
        evt = pd.Timestamp(beacon['t_event']).tz_convert('UTC')
        result = df['ts'] >= evt
        print(f"   df['ts'] >= evt (converted): SUCCESS")
    except Exception as e:
        print(f"   df['ts'] >= evt (converted): ERROR - {e}")
    
    # Test 3: Using between method
    try:
        left = evt - pd.Timedelta(minutes=3)
        right = evt + pd.Timedelta(minutes=3)
        result = df['ts'].between(left, right, inclusive='both')
        print(f"   df['ts'].between(left, right): SUCCESS")
    except Exception as e:
        print(f"   df['ts'].between(left, right): ERROR - {e}")
    
    # Test 4: Check if the issue is in the returns computation
    print(f"\n4) Testing returns computation:")
    try:
        # Create a small window
        left = evt - pd.Timedelta(minutes=3)
        right = evt + pd.Timedelta(minutes=3)
        
        window_df = df.loc[df['ts'].between(left, right, inclusive='both')].copy()
        print(f"   Window size: {len(window_df)}")
        
        if len(window_df) > 0:
            window_df['second'] = window_df['ts'].dt.floor('1S')
            vwap_bars = window_df.groupby('second').apply(
                lambda x: np.average(x['price'], weights=x['size'])
            ).reset_index()
            vwap_bars.columns = ['second', 'vwap']
            
            print(f"   VWAP bars: {len(vwap_bars)}")
            
            # Test returns computation
            vwap_bars = vwap_bars.sort_values('second')
            returns = vwap_bars['vwap'].pct_change() * 10000
            returns = returns.dropna()
            
            print(f"   Returns: {len(returns)}")
            print(f"   Returns index type: {type(returns.index)}")
            print(f"   Returns index dtype: {returns.index.dtype}")
            
            # Test the problematic comparison in find_leader
            print(f"\n5) Testing find_leader comparison:")
            event_time = evt
            print(f"   event_time type: {type(event_time)}")
            print(f"   returns.index type: {type(returns.index)}")
            
            try:
                post_returns = returns[returns.index >= event_time]
                print(f"   returns.index >= event_time: SUCCESS, size: {len(post_returns)}")
            except Exception as e:
                print(f"   returns.index >= event_time: ERROR - {e}")
                
    except Exception as e:
        print(f"   Returns computation: ERROR - {e}")

if __name__ == "__main__":
    debug_timestamp_comparison()




