#!/usr/bin/env python3
"""
Week-3 Debug Authenticity Check
Focused diagnostic to understand data patterns
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def main():
    print("🔍 Week-3 Debug Authenticity Check")
    print("=" * 50)
    print("Mode: Focused diagnostic for 2025-08-11")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    date_str = '20250811'
    date_display = '2025-08-11'
    
    # Set random seed for reproducibility
    np.random.seed(1337)
    
    print(f"📅 Analyzing {date_display} ({date_str})")
    print("-" * 50)
    
    # Load and analyze each venue
    for venue in venues:
        try:
            # Load canonical data
            file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
            
            if not os.path.exists(file_path):
                print(f"❌ Missing file: {file_path}")
                continue
            
            df = pd.read_parquet(file_path)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            print(f"\n{venue}:")
            print(f"  Total rows: {len(df):,}")
            print(f"  Time range: {df['ts'].min()} to {df['ts'].max()}")
            print(f"  Price range: ${df['price'].min():,.2f} to ${df['price'].max():,.2f}")
            print(f"  Size range: {df['size'].min():.6f} to {df['size'].max():.6f} BTC")
            
            # Check for price clustering
            unique_prices = df['price'].nunique()
            print(f"  Unique prices: {unique_prices:,} (clustering ratio: {unique_prices/len(df):.4f})")
            
            # Sample some price sequences
            print(f"  Sample price sequences:")
            
            # Get 3 different time windows
            for i, hour in enumerate([8, 12, 15]):
                hour_data = df[df['ts'].dt.hour == hour]
                if len(hour_data) > 0:
                    # Take first 10 ticks from this hour
                    sample = hour_data.head(10)
                    prices = sample['price'].values
                    times = sample['ts'].dt.strftime('%H:%M:%S').values
                    
                    print(f"    Hour {hour:02d}:00 - {times[0]} to {times[-1]}")
                    print(f"      Prices: {prices[:5]} ... {prices[-3:]}")
                    print(f"      Changes: {np.diff(prices[:5])} ... {np.diff(prices[-3:])}")
            
            # Check for constant prices (potential data quality issue)
            constant_price_ratio = (df['price'].value_counts().max() / len(df))
            if constant_price_ratio > 0.1:
                print(f"  ⚠️  High constant price ratio: {constant_price_ratio:.3f}")
            
            # Memory check
            current_memory = get_memory_usage()
            if current_memory > 200:
                print(f"  ⚠️  High memory usage: {current_memory:.1f} MB")
            
        except Exception as e:
            print(f"❌ Error analyzing {venue}: {str(e)}")
    
    print(f"\nFinal memory usage: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()




