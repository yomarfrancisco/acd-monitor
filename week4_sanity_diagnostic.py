#!/usr/bin/env python3
"""
Week-4 Sanity Check Diagnostic
Quick verification of Δdisp = 0 results
"""

import pandas as pd
import numpy as np
import psutil
import os
import glob
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=300, hard_limit=300):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

def create_vwap_bars_streaming(df, start_time, end_time):
    """Create 1-second VWAP bars for a time window"""
    window_df = df.loc[df['ts'].between(start_time, end_time, inclusive='both')].copy()
    
    if len(window_df) == 0:
        return pd.DataFrame()
    
    window_df['second'] = window_df['ts'].dt.floor('1S')
    vwap_bars = window_df.groupby('second').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap_bars.columns = ['second', 'vwap']
    
    return vwap_bars

def main():
    print("🧪 Week-4 Sanity Check Diagnostic")
    print("=" * 50)
    print("Mode: Read-only, sample 3 venue-days per venue")
    print(f"Memory limit: 300 MB")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Check memory
    mem_ok, mem_msg = check_memory_limit()
    if not mem_ok:
        print(f"❌ HALT: {mem_msg}")
        return
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # 1️⃣ Sample beacon events and analyze
    print("1️⃣ Sampling beacon events and analyzing...")
    
    venue_results = {}
    
    for venue in venues:
        print(f"\nProcessing {venue}...")
        
        # Get all beacon files for this venue
        cache_pattern = f"data_v6/cache/beacons/week-4/{venue}_*.parquet"
        beacon_files = glob.glob(cache_pattern)
        
        if len(beacon_files) == 0:
            print(f"❌ No beacon files found for {venue}")
            continue
        
        # Pick 3 random files (or first 3 if less than 3)
        np.random.seed(1337)  # Deterministic sampling
        selected_files = np.random.choice(beacon_files, size=min(3, len(beacon_files)), replace=False)
        
        venue_stats = {
            'total_beacons': 0,
            'total_ticks': 0,
            'pre_vars': [],
            'post_vars': [],
            'mean_diffs': []
        }
        
        for beacon_file in selected_files:
            # Extract date from filename
            filename = os.path.basename(beacon_file)
            date_str = filename.split('_')[1].split('.')[0]
            date_display = f"2025-{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
            
            try:
                # Load beacon events
                beacon_df = pd.read_parquet(beacon_file)
                venue_stats['total_beacons'] += len(beacon_df)
                
                # Load canonical data
                canonical_file = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
                df = pd.read_parquet(canonical_file)
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                
                # Check tick count
                if len(df) < 10000:
                    print(f"❌ STOP: {venue} {date_display} has {len(df)} ticks, expected ≥10,000")
                    return
                
                venue_stats['total_ticks'] += len(df)
                
                # Sample 3 random beacon events from this day
                if len(beacon_df) > 0:
                    sample_events = beacon_df.sample(n=min(3, len(beacon_df)), random_state=1337)
                    
                    for _, event in sample_events.iterrows():
                        event_ts = event['event_ts']
                        
                        # Define ±3 min windows
                        pre_start = event_ts - pd.Timedelta(minutes=3)
                        pre_end = event_ts
                        post_start = event_ts
                        post_end = event_ts + pd.Timedelta(minutes=3)
                        
                        # Get pre-event data
                        pre_df = df.loc[df['ts'].between(pre_start, pre_end, inclusive='left')]
                        post_df = df.loc[df['ts'].between(post_start, post_end, inclusive='right')]
                        
                        if len(pre_df) > 0 and len(post_df) > 0:
                            # Compute price statistics
                            pre_mean = pre_df['price'].mean()
                            pre_std = pre_df['price'].std()
                            post_mean = post_df['price'].mean()
                            post_std = post_df['price'].std()
                            
                            # Check for zero variance
                            if pre_std == 0 or post_std == 0:
                                print(f"❌ STOP: {venue} {date_display} has zero price std (pre={pre_std}, post={post_std})")
                                return
                            
                            # Compute 1-sec VWAP series variance
                            pre_vwap = create_vwap_bars_streaming(pre_df, pre_start, pre_end)
                            post_vwap = create_vwap_bars_streaming(post_df, post_start, post_end)
                            
                            pre_var = pre_vwap['vwap'].var() if len(pre_vwap) > 1 else 0
                            post_var = post_vwap['vwap'].var() if len(post_vwap) > 1 else 0
                            
                            # Compute mean absolute price difference (in bps)
                            mean_diff_bps = abs(post_mean - pre_mean) / pre_mean * 10000
                            
                            venue_stats['pre_vars'].append(pre_var)
                            venue_stats['post_vars'].append(post_var)
                            venue_stats['mean_diffs'].append(mean_diff_bps)
                
            except Exception as e:
                print(f"❌ Error processing {venue} {date_display}: {str(e)}")
                return
        
        # Compute venue summary
        if len(venue_stats['pre_vars']) > 0:
            mean_ticks = venue_stats['total_ticks'] / len(selected_files)
            avg_pre_var = np.mean(venue_stats['pre_vars'])
            avg_post_var = np.mean(venue_stats['post_vars'])
            avg_mean_diff = np.mean(venue_stats['mean_diffs'])
            
            print(f"{venue} {date_display} beacons={venue_stats['total_beacons']} ticks≈{mean_ticks:.1f} pre_var={avg_pre_var:.2f} post_var={avg_post_var:.2f} meanΔ={avg_mean_diff:.2f}bps")
            
            venue_results[venue] = {
                'mean_ticks': mean_ticks,
                'pre_var': avg_pre_var,
                'post_var': avg_post_var,
                'mean_diff': avg_mean_diff
            }
    
    # 2️⃣ Cross-venue correlation analysis
    print("\n2️⃣ Cross-venue correlation analysis...")
    
    # Pick a representative day for correlation analysis
    sample_date = "20250806"  # Use 2025-08-06 as representative
    
    try:
        # Load all venue data for the sample day
        venue_data = {}
        for venue in venues:
            canonical_file = f"data_v6/views/{venue}/{sample_date}/ticks_canonical.parquet"
            df = pd.read_parquet(canonical_file)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            # Create 1-sec VWAP bars
            df['second'] = df['ts'].dt.floor('1S')
            vwap_bars = df.groupby('second').apply(
                lambda x: np.average(x['price'], weights=x['size'])
            ).reset_index()
            vwap_bars.columns = ['second', 'vwap']
            
            venue_data[venue] = vwap_bars.set_index('second')['vwap']
        
        # Compute correlation matrix
        print(f"\nCross-venue corr matrix (2025-08-06):")
        print("         BINANCE  COINBASE  BYBITSPOT   BITGET")
        
        corr_matrix = np.zeros((4, 4))
        venue_names = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
        
        for i, venue1 in enumerate(venue_names):
            row_str = f"{venue1:>9}"
            for j, venue2 in enumerate(venue_names):
                if venue1 in venue_data and venue2 in venue_data:
                    # Align by common timestamps
                    common_times = venue_data[venue1].index.intersection(venue_data[venue2].index)
                    if len(common_times) > 100:  # Need sufficient overlap
                        aligned1 = venue_data[venue1].loc[common_times]
                        aligned2 = venue_data[venue2].loc[common_times]
                        corr = np.corrcoef(aligned1.values, aligned2.values)[0, 1]
                        corr_matrix[i, j] = corr
                        row_str += f"  {corr:>7.4f}"
                    else:
                        row_str += f"  {'N/A':>7}"
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
        
        # Compute mean tick count per second (liquidity proxy)
        total_ticks = 0
        total_seconds = 0
        for venue in venues:
            canonical_file = f"data_v6/views/{venue}/{sample_date}/ticks_canonical.parquet"
            df = pd.read_parquet(canonical_file)
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            
            total_ticks += len(df)
            # Estimate seconds in day (rough)
            if len(df) > 0:
                day_seconds = (df['ts'].max() - df['ts'].min()).total_seconds()
                total_seconds += day_seconds
        
        mean_ticks_per_sec = total_ticks / total_seconds if total_seconds > 0 else 0
        
        print(f"\nMean tick count per sec (liquidity proxy): {mean_ticks_per_sec:.1f}")
        
    except Exception as e:
        print(f"❌ Error in correlation analysis: {str(e)}")
        return
    
    # 3️⃣ Summary
    print("\n3️⃣ Summary:")
    
    if venue_results:
        # Compute dispersion statistics
        all_mean_diffs = [venue_results[v]['mean_diff'] for v in venue_results.keys()]
        dispersion_mean = np.mean(all_mean_diffs)
        dispersion_std = np.std(all_mean_diffs)
        
        print(f"dispersion_mean={dispersion_mean:.2f}bps dispersion_std={dispersion_std:.2f}bps avg_corr={avg_corr:.4f}")
        
        # Interpretation
        print(f"\nInterpretation:")
        if dispersion_mean < 1.0:
            print("✅ Genuine compression: Very low dispersion indicates tight market synchronization")
        elif dispersion_mean < 5.0:
            print("✅ Real compression: Low but non-zero dispersion suggests efficient price discovery")
        else:
            print("⚠️  Higher dispersion: May indicate less synchronized markets")
        
        if avg_corr > 0.99:
            print("✅ High correlation: Venues are highly synchronized")
        elif avg_corr > 0.95:
            print("✅ Good correlation: Venues show strong synchronization")
        else:
            print("⚠️  Lower correlation: Some venue divergence detected")
    
    print(f"\nMemory usage: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()




