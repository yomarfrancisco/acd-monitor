#!/usr/bin/env python3
"""
Extract Last 10 Rows Per Venue for Week -4 (2025-08-04 to 2025-08-10)
"""

import pandas as pd
from datetime import datetime, timedelta

def extract_last_10_rows():
    """Extract last 10 rows per venue for each day in Week -4"""
    print("📊 Last 10 Rows Per Venue - Week -4 (2025-08-04 to 2025-08-10)")
    print("=" * 80)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        print(f"\n📅 {date_display} ({date_str})")
        print("-" * 60)
        
        for venue in venues:
            file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
            try:
                # Read the parquet file
                df = pd.read_parquet(file_path)
                
                # Get last 10 rows
                last_10 = df.tail(10)
                
                print(f"\n{venue}:")
                print(f"  Total rows: {len(df):,}")
                print(f"  Time range: {df['ts'].min()} to {df['ts'].max()}")
                print(f"  Price range: ${df['price'].min():,.2f} to ${df['price'].max():,.2f}")
                print(f"  Last 10 rows:")
                
                # Display last 10 rows in a clean format
                for idx, row in last_10.iterrows():
                    timestamp = row['ts'].strftime('%H:%M:%S.%f')[:-3]  # Remove last 3 digits of microseconds
                    price = f"${row['price']:,.2f}"
                    size = f"{row['size']:.6f}"
                    print(f"    {timestamp} | {price:>12} | {size:>12} | {row['venue']}")
                
            except Exception as e:
                print(f"\n{venue}: ERROR - {str(e)}")
        
        current_date += timedelta(days=1)

if __name__ == "__main__":
    extract_last_10_rows()




