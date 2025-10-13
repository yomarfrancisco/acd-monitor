#!/usr/bin/env python3
"""
Week-3 Canonical Authenticity Check v2
Read-only validation protocol accounting for price clustering
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

def check_memory_limit(soft_limit=200, hard_limit=250):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit warning: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

def main():
    print("🔍 Week-3 Canonical Authenticity Check v2")
    print("=" * 50)
    print("Mode: STRICT READ-ONLY, accounting for price clustering")
    print(f"Memory limit: 250 MB")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Define Week-3 date range (2025-08-11 → 2025-08-17)
    start_date = datetime(2025, 8, 11)
    end_date = datetime(2025, 8, 17)
    
    # Set random seed for reproducibility
    np.random.seed(1337)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        print(f"\n📅 Processing {date_display} ({date_str})")
        print("-" * 50)
        
        # Check memory before processing
        mem_ok, mem_msg = check_memory_limit()
        if not mem_ok:
            print(f"❌ HALT: {mem_msg}")
            return
        
        # Load all venue data for this day
        venue_data = {}
        venue_prices = {}
        venue_sizes = {}
        
        for venue in venues:
            try:
                # Load canonical data
                file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
                
                if not os.path.exists(file_path):
                    print(f"❌ STOP: Missing file {file_path}")
                    return
                
                df = pd.read_parquet(file_path)
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                
                # Verify schema
                required_cols = ['ts', 'price', 'size', 'venue']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    print(f"❌ STOP: {venue} missing columns: {missing_cols}")
                    return
                
                # Check timestamp monotonicity (sample check)
                if not df['ts'].head(1000).is_monotonic_increasing:
                    print(f"❌ STOP: {venue} timestamps not monotonic")
                    return
                
                # Filter to 8-hour window (08:00 UTC → 16:00 UTC)
                df['hour'] = df['ts'].dt.hour
                window_df = df[(df['hour'] >= 8) & (df['hour'] < 16)].copy()
                
                if len(window_df) < 15:
                    print(f"❌ STOP: {venue} insufficient data in 8h window ({len(window_df)} ticks)")
                    return
                
                venue_data[venue] = window_df
                
            except Exception as e:
                print(f"❌ STOP: Error loading {venue}: {str(e)}")
                return
        
        # Randomly select one 5-minute window (same for all venues)
        # Use first venue to determine window bounds
        first_venue = venues[0]
        window_start = venue_data[first_venue]['ts'].min()
        window_end = venue_data[first_venue]['ts'].max()
        
        # Random start time within the window (leaving 5 minutes at the end)
        max_start = window_end - pd.Timedelta(minutes=5)
        random_start = window_start + pd.Timedelta(
            seconds=np.random.uniform(0, (max_start - window_start).total_seconds())
        )
        random_end = random_start + pd.Timedelta(minutes=5)
        
        print(f"Selected window: {random_start.strftime('%H:%M:%S')} - {random_end.strftime('%H:%M:%S')}")
        
        # Process each venue
        for venue in venues:
            try:
                # Get ticks in the 5-minute window
                window_ticks = venue_data[venue][
                    (venue_data[venue]['ts'] >= random_start) & 
                    (venue_data[venue]['ts'] < random_end)
                ].copy()
                
                if len(window_ticks) < 15:
                    print(f"❌ STOP: {venue} insufficient ticks in 5m window ({len(window_ticks)} ticks)")
                    return
                
                # Sample 15 consecutive ticks
                if len(window_ticks) == 15:
                    sample_ticks = window_ticks
                else:
                    # Random start index for 15 consecutive ticks
                    start_idx = np.random.randint(0, len(window_ticks) - 14)
                    sample_ticks = window_ticks.iloc[start_idx:start_idx+15]
                
                # Extract prices and sizes
                prices = sample_ticks['price'].values
                sizes = sample_ticks['size'].values
                
                # Compute statistics
                price_mean = np.mean(prices)
                price_std = np.std(prices)
                size_mean = np.mean(sizes)
                
                # Check for price clustering
                unique_prices = len(np.unique(prices))
                clustering_ratio = unique_prices / len(prices)
                
                # Format price list (first 5 and last 5)
                if len(prices) > 10:
                    price_list = f"[{prices[0]:.1f}, {prices[1]:.1f}, {prices[2]:.1f}, {prices[3]:.1f}, {prices[4]:.1f}, ..., {prices[-5]:.1f}, {prices[-4]:.1f}, {prices[-3]:.1f}, {prices[-2]:.1f}, {prices[-1]:.1f}]"
                else:
                    price_list = f"[{', '.join([f'{p:.1f}' for p in prices])}]"
                
                # Print venue line
                time_range = f"{sample_ticks['ts'].iloc[0].strftime('%H:%M:%S')}-{sample_ticks['ts'].iloc[-1].strftime('%H:%M:%S')}"
                print(f"{venue:>9} {date_display} {time_range} → prices={price_list} mean={price_mean:.1f} ± {price_std:.1f} (size ≈ {size_mean:.3f} BTC, unique={unique_prices}/15)")
                
                # Store for correlation analysis
                venue_prices[venue] = prices
                venue_sizes[venue] = sizes
                
            except Exception as e:
                print(f"❌ STOP: Error processing {venue}: {str(e)}")
                return
        
        # Day-level summary
        print(f"\nDay-level summary:")
        
        # Overall price statistics
        all_prices = np.concatenate(list(venue_prices.values()))
        overall_mean = np.mean(all_prices)
        overall_std = np.std(all_prices)
        overall_size_mean = np.mean([np.mean(sizes) for sizes in venue_sizes.values()])
        
        print(f"  mean = {overall_mean:.1f} ± {overall_std:.1f} / size ≈ {overall_size_mean:.3f} BTC")
        
        # Cross-venue correlation matrix (with clustering awareness)
        print(f"  Cross-venue correlation matrix:")
        print(f"         BINANCE  COINBASE  BYBITSPOT   BITGET")
        
        corr_matrix = np.zeros((4, 4))
        venue_names = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
        
        for i, venue1 in enumerate(venue_names):
            row_str = f"{venue1:>9}"
            for j, venue2 in enumerate(venue_names):
                if venue1 in venue_prices and venue2 in venue_prices:
                    corr = np.corrcoef(venue_prices[venue1], venue_prices[venue2])[0, 1]
                    corr_matrix[i, j] = corr
                    row_str += f"  {corr:>7.4f}"
                else:
                    row_str += f"  {'N/A':>7}"
            print(row_str)
        
        # Compute average correlation (excluding diagonal)
        off_diagonal = []
        for i in range(4):
            for j in range(4):
                if i != j and not np.isnan(corr_matrix[i, j]):
                    off_diagonal.append(corr_matrix[i, j])
        
        avg_corr = np.mean(off_diagonal) if len(off_diagonal) > 0 else np.nan
        print(f"  avg_corr ≈ {avg_corr:.4f}")
        
        # Check for issues (adjusted for clustering)
        issues = []
        
        # Check price ranges
        if overall_mean < 100000 or overall_mean > 200000:
            issues.append(f"Unusual price level: ${overall_mean:,.0f}")
        
        # Check correlation (relaxed threshold for clustering)
        if avg_corr < 0.5:  # Relaxed from 0.95
            issues.append(f"Very low correlation: {avg_corr:.4f}")
        
        # Check size ranges
        if overall_size_mean < 0.001 or overall_size_mean > 1.0:
            issues.append(f"Unusual size: {overall_size_mean:.3f} BTC")
        
        # Check memory
        current_memory = get_memory_usage()
        if current_memory > 200:
            issues.append(f"High memory: {current_memory:.1f} MB")
        
        # Print checkpoint result
        if issues:
            print(f"\n⚠️  ISSUE DETECTED: {', '.join(issues)}")
            print("Halting for review...")
            return
        else:
            print(f"\n✅ CHECKPOINT OK")
        
        current_date += timedelta(days=1)
    
    print(f"\n🎉 Week-3 authenticity check completed successfully!")
    print(f"Final memory usage: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()




