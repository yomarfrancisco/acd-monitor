#!/usr/bin/env python3
"""
Week-4 Price Sequence Diagnostic
Read-only: Print random tick sequences for visual verification
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
    print("🔍 Week-4 Price Sequence Diagnostic")
    print("=" * 50)
    print("Mode: Read-only, random tick sequences")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    days = ['20250804', '20250806', '20250810']  # Day 1, 3, 7
    day_names = ['Day 1', 'Day 3', 'Day 7']
    
    # Set random seed for reproducibility
    np.random.seed(1337)
    
    for i, (date_str, day_name) in enumerate(zip(days, day_names)):
        date_display = f"2025-{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
        print(f"\n📅 {day_name} ({date_display})")
        print("-" * 40)
        
        for venue in venues:
            try:
                # Load canonical data
                file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
                df = pd.read_parquet(file_path)
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                
                # Define 8-hour window (08:00 UTC → 16:00 UTC)
                start_hour = 8
                end_hour = 16
                
                # Filter to 8-hour window
                df['hour'] = df['ts'].dt.hour
                window_df = df[(df['hour'] >= start_hour) & (df['hour'] < end_hour)].copy()
                
                if len(window_df) < 15:
                    print(f"{venue:>9}: Insufficient data in 8h window ({len(window_df)} ticks)")
                    continue
                
                # Randomly select a 5-minute window within the 8-hour period
                window_start = window_df['ts'].min()
                window_end = window_df['ts'].max()
                window_duration = window_end - window_start
                
                # Random start time within the window (leaving 5 minutes at the end)
                max_start = window_end - pd.Timedelta(minutes=5)
                random_start = window_start + pd.Timedelta(
                    seconds=np.random.uniform(0, (max_start - window_start).total_seconds())
                )
                random_end = random_start + pd.Timedelta(minutes=5)
                
                # Get ticks in the 5-minute window
                window_ticks = window_df[
                    (window_df['ts'] >= random_start) & 
                    (window_df['ts'] < random_end)
                ].copy()
                
                if len(window_ticks) < 15:
                    print(f"{venue:>9}: Insufficient ticks in 5m window ({len(window_ticks)} ticks)")
                    continue
                
                # Sample 15 consecutive ticks
                if len(window_ticks) == 15:
                    sample_ticks = window_ticks
                else:
                    # Random start index for 15 consecutive ticks
                    start_idx = np.random.randint(0, len(window_ticks) - 14)
                    sample_ticks = window_ticks.iloc[start_idx:start_idx+15]
                
                # Format the output
                time_str = random_start.strftime('%H:%M:%S')
                price_str = f"${sample_ticks['price'].iloc[0]:,.2f}"
                
                # Create price sequence string
                prices = sample_ticks['price'].values
                price_changes = []
                for j in range(1, len(prices)):
                    change = prices[j] - prices[j-1]
                    if change > 0:
                        price_changes.append(f"+{change:.2f}")
                    elif change < 0:
                        price_changes.append(f"{change:.2f}")
                    else:
                        price_changes.append("0.00")
                
                # Print compact line
                print(f"{venue:>9} {time_str} {price_str} → {' '.join(price_changes[:10])}...")
                
            except Exception as e:
                print(f"{venue:>9}: Error - {str(e)}")
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")
    print("\n✅ Price sequence diagnostic completed")

if __name__ == "__main__":
    main()




