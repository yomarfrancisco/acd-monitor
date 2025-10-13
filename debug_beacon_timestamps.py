#!/usr/bin/env python3
"""
Debug Beacon Timestamps - Check if beacon times are within data range
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def debug_beacon_timestamps():
    """Debug beacon timestamps vs actual data range"""
    print("🔍 Debug Beacon Timestamps vs Data Range")
    print("=" * 50)
    
    # Check data range for 2025-08-04
    date_str = "20250804"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
        try:
            df = pd.read_parquet(file_path)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            print(f"\n{venue}:")
            print(f"  Data range: {df['ts'].min()} to {df['ts'].max()}")
            print(f"  Total rows: {len(df):,}")
            
            # Check if beacon times are within range
            beacon_times = [
                "2025-08-04 00:56:26.150000+00:00",
                "2025-08-04 00:54:11.697355+00:00", 
                "2025-08-04 00:57:14.121000+00:00"
            ]
            
            for beacon_time in beacon_times:
                beacon_ts = pd.Timestamp(beacon_time)
                if venue == 'BINANCE' and beacon_time == "2025-08-04 00:56:26.150000+00:00":
                    print(f"  Beacon {beacon_ts}: {'IN RANGE' if df['ts'].min() <= beacon_ts <= df['ts'].max() else 'OUT OF RANGE'}")
                    
                    # Check data around this time
                    start_time = beacon_ts - pd.Timedelta(seconds=15)
                    end_time = beacon_ts + pd.Timedelta(seconds=15)
                    
                    window_data = df.loc[df['ts'].between(start_time, end_time, inclusive='both')]
                    print(f"    Data in ±15s window: {len(window_data)} rows")
                    
                    if len(window_data) > 0:
                        print(f"    Window range: {window_data['ts'].min()} to {window_data['ts'].max()}")
                        print(f"    Price range: ${window_data['price'].min():,.2f} to ${window_data['price'].max():,.2f}")
                    else:
                        print(f"    No data in window")
                        
        except Exception as e:
            print(f"{venue}: ERROR - {str(e)}")

if __name__ == "__main__":
    debug_beacon_timestamps()




