#!/usr/bin/env python3
"""
Phase 1 Diagnostics: Day 1 (2025-09-08) - Streaming & Memory-Safe
Process canonical tick data using streaming batches and 1-second VWAP bars
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import psutil
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from collections import defaultdict

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 450:
        print(f"HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
        return True
    return False

def process_venue_day_streaming(venue, date):
    """Process a single venue-day file using streaming batches"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Open parquet file for streaming
        parquet_file = pq.ParquetFile(file_path)
        
        # Initialize online stats
        row_count = 0
        ts_min = None
        ts_max = None
        price_min = None
        price_max = None
        
        # Initialize VWAP aggregation
        sum_pxsz = defaultdict(float)  # sum(price * size) per second
        sum_sz = defaultdict(float)    # sum(size) per second
        
        print(f"    📊 Processing {venue} {date} in streaming batches...")
        
        # Process in batches
        batch_size = 200000
        batch_count = 0
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            batch_count += 1
            
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded during batch processing"
            
            # Convert batch to pandas
            df_batch = batch.to_pandas()
            
            # Update online stats
            row_count += len(df_batch)
            
            if ts_min is None or df_batch['ts'].min() < ts_min:
                ts_min = df_batch['ts'].min()
            if ts_max is None or df_batch['ts'].max() > ts_max:
                ts_max = df_batch['ts'].max()
            
            if price_min is None or df_batch['price'].min() < price_min:
                price_min = df_batch['price'].min()
            if price_max is None or df_batch['price'].max() > price_max:
                price_max = df_batch['price'].max()
            
            # Check for data risks
            if price_min < 10000 or price_max > 300000:
                return None, f"Price outlier: {price_min:.2f} to {price_max:.2f}"
            
            if (df_batch['price'] <= 0).any() or (df_batch['size'] <= 0).any():
                return None, "Negative or zero prices/sizes detected"
            
            # Build 1-second VWAP bars
            df_batch['second'] = df_batch['ts'].dt.floor('S')
            
            for _, row in df_batch.iterrows():
                second = row['second']
                price = row['price']
                size = row['size']
                
                sum_pxsz[second] += price * size
                sum_sz[second] += size
            
            # Clean up batch
            del df_batch
            gc.collect()
            
            if batch_count % 10 == 0:
                print(f"      Processed {batch_count} batches, {row_count:,} rows")
        
        # Compute coverage
        if ts_min is None or ts_max is None:
            return None, "No valid timestamps found"
        
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
        
        expected_duration = (day_end - day_start).total_seconds()
        actual_duration = (ts_max - ts_min).total_seconds() + 1  # +1 for inclusive
        coverage_pct = min(100.0, 100 * actual_duration / expected_duration)
        
        if coverage_pct < 95:
            return None, f"Coverage too low: {coverage_pct:.1f}%"
        
        # Create VWAP bars DataFrame
        bars_data = []
        for second in sorted(sum_pxsz.keys()):
            if sum_sz[second] > 0:
                vwap = sum_pxsz[second] / sum_sz[second]
                bars_data.append({'second': second, 'vwap': vwap})
        
        bars_df = pd.DataFrame(bars_data)
        
        if len(bars_df) == 0:
            return None, "No valid VWAP bars created"
        
        result = {
            'row_count': row_count,
            'ts_min': ts_min,
            'ts_max': ts_max,
            'coverage_pct': coverage_pct,
            'price_min': price_min,
            'price_max': price_max,
            'bars_df': bars_df
        }
        
        # Clean up
        del sum_pxsz, sum_sz, bars_data
        gc.collect()
        
        return result, None
        
    except Exception as e:
        return None, f"Error processing {file_path}: {e}"

def compute_temporal_alignment(binance_bars, other_bars, venue_name):
    """Compute temporal alignment between BINANCE and another venue"""
    # Merge bars on second
    merged = pd.merge(binance_bars, other_bars, on='second', suffixes=('_bin', '_other'))
    
    if len(merged) < 100:  # Need sufficient data
        return None, f"Insufficient overlapping data: {len(merged)} bars"
    
    # Compute returns
    merged['ret_bin'] = np.log(merged['vwap_bin'] / merged['vwap_bin'].shift(1))
    merged['ret_other'] = np.log(merged['vwap_other'] / merged['vwap_other'].shift(1))
    
    # Remove NaN returns
    merged = merged.dropna(subset=['ret_bin', 'ret_other'])
    
    if len(merged) < 50:
        return None, f"Insufficient return data: {len(merged)} observations"
    
    # Split by hour
    merged['hour'] = merged['second'].dt.hour
    hourly_results = []
    
    for hour in range(24):
        hour_data = merged[merged['hour'] == hour]
        if len(hour_data) < 10:  # Need minimum data per hour
            continue
        
        # Search lags -5 to +5 seconds
        best_lag = 0
        best_corr = -1
        
        for lag in range(-5, 6):
            if lag == 0:
                corr = hour_data['ret_bin'].corr(hour_data['ret_other'])
            elif lag > 0:
                # BINANCE leads
                if len(hour_data) > lag:
                    corr = hour_data['ret_bin'].iloc[:-lag].corr(hour_data['ret_other'].iloc[lag:])
                else:
                    continue
            else:
                # Other venue leads
                if len(hour_data) > abs(lag):
                    corr = hour_data['ret_bin'].iloc[abs(lag):].corr(hour_data['ret_other'].iloc[:-abs(lag)])
                else:
                    continue
            
            if not np.isnan(corr) and corr > best_corr:
                best_corr = corr
                best_lag = lag
        
        if best_corr > -1:
            hourly_results.append({
                'hour': hour,
                'lag': best_lag,
                'corr': best_corr
            })
    
    if len(hourly_results) == 0:
        return None, "No valid hourly correlations computed"
    
    # Aggregate results
    lags = [r['lag'] for r in hourly_results]
    corrs = [r['corr'] for r in hourly_results]
    
    mean_lag = np.mean(lags)
    mean_corr = np.mean(corrs)
    hours_over_1s = sum(1 for lag in lags if abs(lag) > 1)
    
    return {
        'mean_lag': mean_lag,
        'mean_corr': mean_corr,
        'hours_over_1s': hours_over_1s,
        'total_hours': len(hourly_results)
    }, None

def compute_statistical_coherence(all_bars):
    """Compute statistical coherence across all venues"""
    venues = list(all_bars.keys())
    if len(venues) < 2:
        return None, "Need at least 2 venues"
    
    # Merge all bars
    merged = all_bars['BINANCE'].copy()
    merged = merged.rename(columns={'vwap': 'vwap_bin'})
    
    for venue in venues[1:]:
        venue_bars = all_bars[venue].copy()
        venue_bars = venue_bars.rename(columns={'vwap': f'vwap_{venue.lower()}'})
        merged = pd.merge(merged, venue_bars, on='second', how='inner')
    
    if len(merged) < 100:
        return None, "Insufficient overlapping data for statistical analysis"
    
    # Compute returns for all venues
    for venue in venues:
        col_name = f'vwap_{venue.lower()}' if venue != 'BINANCE' else 'vwap_bin'
        merged[f'ret_{venue.lower()}'] = np.log(merged[col_name] / merged[col_name].shift(1))
    
    # Remove NaN returns
    ret_cols = [f'ret_{venue.lower()}' for venue in venues]
    merged = merged.dropna(subset=ret_cols)
    
    if len(merged) < 50:
        return None, "Insufficient return data for statistical analysis"
    
    # Split by hour
    merged['hour'] = merged['second'].dt.hour
    hourly_results = []
    
    for hour in range(24):
        hour_data = merged[merged['hour'] == hour]
        if len(hour_data) < 10:
            continue
        
        # Compute realized volatility per venue
        vol_by_venue = {}
        for venue in venues:
            ret_col = f'ret_{venue.lower()}'
            vol = np.sqrt(np.sum(hour_data[ret_col] ** 2))
            vol_by_venue[venue] = vol
        
        # Compute volatility ratio
        vols = list(vol_by_venue.values())
        if min(vols) > 0:
            vol_ratio = max(vols) / min(vols)
        else:
            vol_ratio = float('inf')
        
        # Compute correlations with BINANCE
        corrs_with_bin = {}
        for venue in venues[1:]:  # Skip BINANCE itself
            ret_col = f'ret_{venue.lower()}'
            corr = hour_data['ret_bin'].corr(hour_data[ret_col])
            if not np.isnan(corr):
                corrs_with_bin[venue] = corr
        
        hourly_results.append({
            'hour': hour,
            'vol_ratio': vol_ratio,
            'corrs_with_bin': corrs_with_bin,
            'vol_by_venue': vol_by_venue
        })
    
    if len(hourly_results) == 0:
        return None, "No valid hourly statistical results"
    
    # Aggregate results
    vol_ratios = [r['vol_ratio'] for r in hourly_results if r['vol_ratio'] != float('inf')]
    hours_vol_ratio_high = sum(1 for ratio in vol_ratios if ratio > 2.0)
    
    all_corrs = []
    for r in hourly_results:
        all_corrs.extend(r['corrs_with_bin'].values())
    
    hours_corr_low = sum(1 for r in hourly_results 
                        for corr in r['corrs_with_bin'].values() 
                        if corr < 0.95)
    
    return {
        'hours_vol_ratio_high': hours_vol_ratio_high,
        'hours_corr_low': hours_corr_low,
        'total_hours': len(hourly_results),
        'mean_vol_ratio': np.mean(vol_ratios) if vol_ratios else 0,
        'mean_corr': np.mean(all_corrs) if all_corrs else 0
    }, None

def run_day1_diagnostics():
    """Run diagnostics for Day 1 (2025-09-08)"""
    print("🧾 Phase 1 Diagnostics: Day 1 (2025-09-08)")
    print("=" * 60)
    
    date = "20250908"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Process each venue
    all_results = {}
    all_bars = {}
    
    for venue in venues:
        print(f"\n🔍 Processing {venue}...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded before processing {venue}")
            return False
        
        result, error = process_venue_day_streaming(venue, date)
        
        if error:
            print(f"    ❌ {error}")
            print(f"❌ HALT — Issue detected. Summary below.")
            print(f"Failed venue: {venue} {date}")
            print(f"Error: {error}")
            return False
        
        all_results[venue] = result
        all_bars[venue] = result['bars_df']
        
        print(f"    ✅ {result['row_count']:,} rows, {result['coverage_pct']:.1f}% coverage")
        print(f"    📊 Created {len(result['bars_df']):,} VWAP bars")
        
        # Clean up
        gc.collect()
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after processing {venue}")
            return False
    
    # Checkpoint 1: Structural Consistency
    print(f"\n📊 Checkpoint 1 — Structural Consistency:")
    structural_ok = True
    
    for venue in venues:
        result = all_results[venue]
        print(f"  {venue}  rows={result['row_count']:,} coverage={result['coverage_pct']:.1f}%  price={result['price_min']:.0f}→{result['price_max']:.0f}")
        
        if result['coverage_pct'] < 95:
            print(f"❌ HALT: {venue} coverage too low: {result['coverage_pct']:.1f}%")
            structural_ok = False
    
    if not structural_ok:
        return False
    
    # Checkpoint 2: Temporal Alignment
    print(f"\n🧭 Checkpoint 2 — Temporal Alignment:")
    temporal_ok = True
    
    binance_bars = all_bars['BINANCE']
    
    for venue in venues[1:]:  # Skip BINANCE
        print(f"  Computing {venue} alignment...")
        
        result, error = compute_temporal_alignment(binance_bars, all_bars[venue], venue)
        
        if error:
            print(f"    ❌ {error}")
            temporal_ok = False
            continue
        
        print(f"  {venue}  mean_lag={result['mean_lag']:.1f}s  hours>|1s|={result['hours_over_1s']}/{result['total_hours']}  meanρ={result['mean_corr']:.3f}")
        
        if result['hours_over_1s'] > 5:
            print(f"❌ HALT: {venue} has {result['hours_over_1s']} hours with |lag| > 1s")
            temporal_ok = False
    
    if not temporal_ok:
        return False
    
    # Checkpoint 3: Statistical Coherence
    print(f"\n📈 Checkpoint 3 — Statistical Coherence:")
    
    result, error = compute_statistical_coherence(all_bars)
    
    if error:
        print(f"    ❌ {error}")
        print(f"❌ HALT: Statistical coherence check failed")
        return False
    
    print(f"  hours σRatio>2.0: {result['hours_vol_ratio_high']}")
    print(f"  hours ρ<0.95: {result['hours_corr_low']}")
    
    if result['hours_vol_ratio_high'] > 3:
        print(f"❌ HALT: {result['hours_vol_ratio_high']} hours with σRatio > 2.0")
        return False
    
    if result['hours_corr_low'] > 5:
        print(f"❌ HALT: {result['hours_corr_low']} hours with ρ < 0.95")
        return False
    
    # Daily Summary
    print(f"\n📊 Daily Summary:")
    print(f"Date: {date[:4]}-{date[4:6]}-{date[6:8]}")
    print(f"Structural:")
    for venue in venues:
        result = all_results[venue]
        print(f"  {venue}  rows={result['row_count']:,} coverage={result['coverage_pct']:.1f}%  price={result['price_min']:.0f}→{result['price_max']:.0f}")
    
    print(f"Temporal (BINANCE→X best lag in seconds, mean hourly):")
    for venue in venues[1:]:
        result, _ = compute_temporal_alignment(binance_bars, all_bars[venue], venue)
        if result:
            print(f"  {venue}  mean_lag={result['mean_lag']:.1f}s  hours>|1s|={result['hours_over_1s']}/{result['total_hours']}  meanρ={result['mean_corr']:.3f}")
    
    print(f"Statistical:")
    print(f"  hours σRatio>2.0: {result['hours_vol_ratio_high']}")
    print(f"  hours ρ<0.95: {result['hours_corr_low']}")
    
    print(f"Status: PASS")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_day1_diagnostics()
    
    if success:
        print(f"\n🎉 Day 1 diagnostics passed. Ready for Day 2.")
        print(f"Please confirm: ✅ Proceed")
    else:
        print(f"\n❌ Day 1 diagnostics failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




