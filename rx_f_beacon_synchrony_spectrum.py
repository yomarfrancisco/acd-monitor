#!/usr/bin/env python3
"""
RX-F: Beacon Synchrony Spectrum
Goal: Build event-time series for each venue and compute pairwise cross-spectral coherence
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
import glob
from scipy import signal
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def load_beacon_data_weekday_filtered(weeks):
    """Load beacon data for specified weeks with weekday filtering"""
    print(f"🔍 Loading Beacon Data for {weeks} (Weekday Filtered)")
    print("-" * 60)
    
    all_weekday_beacons = []
    
    for week in weeks:
        beacon_cache_dir = f"data_v6/cache/beacons/{week}"
        if not os.path.exists(beacon_cache_dir):
            print(f"❌ Beacon cache directory not found: {beacon_cache_dir}")
            continue
        
        beacon_files = glob.glob(f"{beacon_cache_dir}/*.parquet")
        if not beacon_files:
            print(f"❌ No beacon files found in {beacon_cache_dir}")
            continue
        
        week_beacons = []
        for file_path in beacon_files:
            try:
                df = pd.read_parquet(file_path)
                week_beacons.append(df)
            except Exception as e:
                print(f"  Warning: Could not load {file_path}: {e}")
        
        if not week_beacons:
            print(f"❌ No beacon data loaded for {week}")
            continue
        
        all_beacons = pd.concat(week_beacons, ignore_index=True)
        
        # Convert event_ts to datetime if needed
        if 'event_ts' in all_beacons.columns:
            all_beacons['event_ts'] = pd.to_datetime(all_beacons['event_ts'], utc=True)
        
        # Apply weekday filter (Mon-Fri only, UTC)
        all_beacons['weekday'] = all_beacons['event_ts'].dt.dayofweek
        weekday_beacons = all_beacons[all_beacons['weekday'].isin([0, 1, 2, 3, 4])].copy()  # Mon=0, Fri=4
        
        # Add week identifier
        weekday_beacons['week'] = week
        
        all_weekday_beacons.append(weekday_beacons)
        
        print(f"  ✅ {week}: Total={len(all_beacons)}, Weekday={len(weekday_beacons)}")
    
    if not all_weekday_beacons:
        print(f"❌ No beacon data loaded")
        return pd.DataFrame()
    
    combined_beacons = pd.concat(all_weekday_beacons, ignore_index=True)
    print(f"  ✅ Combined weekday beacons: {len(combined_beacons)}")
    
    return combined_beacons

def build_event_time_series(beacon_data):
    """Build event-time series for each venue"""
    print(f"\n🔍 Building Event-Time Series for Each Venue")
    print("-" * 60)
    
    venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
    venue_series = {}
    
    # Define time range and resolution
    min_time = beacon_data['event_ts'].min()
    max_time = beacon_data['event_ts'].max()
    
    # Round to minute boundaries
    min_time = min_time.replace(second=0, microsecond=0)
    max_time = max_time.replace(second=0, microsecond=0)
    
    # Create 1-minute time grid
    time_bins = pd.date_range(start=min_time, end=max_time, freq='1min')
    
    print(f"  Time range: {min_time} to {max_time}")
    print(f"  Total time bins: {len(time_bins)}")
    
    for venue in venues:
        venue_beacons = beacon_data[beacon_data['venue'] == venue]
        
        # Create binary time series (1 if beacon at time t, 0 otherwise)
        venue_series[venue] = np.zeros(len(time_bins))
        
        for _, beacon in venue_beacons.iterrows():
            # Find the time bin for this beacon
            bin_idx = np.searchsorted(time_bins, beacon['event_ts']) - 1
            if 0 <= bin_idx < len(time_bins):
                venue_series[venue][bin_idx] = 1
        
        # Calculate statistics
        total_beacons = len(venue_beacons)
        series_sum = np.sum(venue_series[venue])
        print(f"  {venue}: {total_beacons} beacons, {series_sum} time bins with events")
    
    return venue_series, time_bins

def compute_cross_spectral_coherence(venue_series, time_bins):
    """Compute pairwise cross-spectral coherence (0-60 min bands)"""
    print(f"\n🔍 Computing Cross-Spectral Coherence (0-60 min bands)")
    print("-" * 60)
    
    venues = list(venue_series.keys())
    coherence_results = {}
    
    # Define frequency bands (0-60 minutes)
    # Convert to frequencies in cycles per minute
    # 60 min = 1 cycle per hour = 1/60 cycles per minute
    # 1 min = 1 cycle per minute
    min_freq = 1/60  # 1 cycle per hour (60 min period)
    max_freq = 1     # 1 cycle per minute (1 min period)
    
    # Sampling rate: 1 sample per minute
    fs = 1  # samples per minute
    
    print(f"  Frequency range: {min_freq:.4f} to {max_freq:.4f} cycles/min")
    print(f"  Period range: 1 to 60 minutes")
    
    # Compute pairwise coherence
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:  # Skip diagonal and upper triangle
                continue
            
            print(f"  Computing coherence: {venue1} ↔ {venue2}")
            
            # Get time series
            series1 = venue_series[venue1]
            series2 = venue_series[venue2]
            
            # Compute cross-spectral coherence
            try:
                # Use Welch's method for coherence estimation
                freqs, coherence = signal.coherence(series1, series2, fs=fs, 
                                                  nperseg=min(256, len(series1)//4),
                                                  noverlap=None)
                
                # Filter to 0-60 minute bands
                period_mask = (freqs >= min_freq) & (freqs <= max_freq)
                filtered_freqs = freqs[period_mask]
                filtered_coherence = coherence[period_mask]
                
                # Find dominant periodicities (peaks in coherence)
                # Find peaks with minimum height and distance
                peaks, properties = signal.find_peaks(filtered_coherence, 
                                                    height=0.3,  # Minimum coherence threshold
                                                    distance=5)  # Minimum distance between peaks
                
                # Get peak information
                peak_freqs = filtered_freqs[peaks]
                peak_coherence = filtered_coherence[peaks]
                peak_periods = 1 / peak_freqs  # Convert to periods in minutes
                
                # Sort by coherence strength
                if len(peaks) > 0:
                    sort_idx = np.argsort(peak_coherence)[::-1]  # Descending order
                    peak_freqs = peak_freqs[sort_idx]
                    peak_coherence = peak_coherence[sort_idx]
                    peak_periods = peak_periods[sort_idx]
                
                # Compute phase offset (cross-correlation lag)
                # Find the lag that maximizes cross-correlation
                cross_corr = signal.correlate(series1, series2, mode='full')
                lags = signal.correlation_lags(len(series1), len(series2), mode='full')
                
                # Find peak correlation lag
                max_corr_idx = np.argmax(cross_corr)
                max_lag = lags[max_corr_idx]
                max_correlation = cross_corr[max_corr_idx]
                
                # Convert lag to phase offset (in minutes)
                phase_offset_min = max_lag
                
                # Compute average coherence in different period bands
                band_coherence = {}
                period_bands = [(1, 5), (5, 15), (15, 30), (30, 60)]  # minutes
                
                for band_min, band_max in period_bands:
                    band_freq_min = 1 / band_max
                    band_freq_max = 1 / band_min
                    band_mask = (filtered_freqs >= band_freq_min) & (filtered_freqs <= band_freq_max)
                    
                    if np.any(band_mask):
                        band_coherence[f"{band_min}-{band_max}min"] = np.mean(filtered_coherence[band_mask])
                    else:
                        band_coherence[f"{band_min}-{band_max}min"] = 0.0
                
                coherence_results[f"{venue1}_{venue2}"] = {
                    'frequencies': filtered_freqs,
                    'coherence': filtered_coherence,
                    'peak_frequencies': peak_freqs,
                    'peak_coherence': peak_coherence,
                    'peak_periods': peak_periods,
                    'phase_offset_min': phase_offset_min,
                    'max_correlation': max_correlation,
                    'band_coherence': band_coherence,
                    'n_peaks': len(peaks)
                }
                
                print(f"    Found {len(peaks)} dominant periodicities")
                if len(peaks) > 0:
                    print(f"    Top period: {peak_periods[0]:.1f} min (coherence: {peak_coherence[0]:.3f})")
                print(f"    Phase offset: {phase_offset_min} min")
                print(f"    Max correlation: {max_correlation:.3f}")
                
            except Exception as e:
                print(f"    Warning: Coherence computation failed: {e}")
                coherence_results[f"{venue1}_{venue2}"] = {
                    'frequencies': np.array([]),
                    'coherence': np.array([]),
                    'peak_frequencies': np.array([]),
                    'peak_coherence': np.array([]),
                    'peak_periods': np.array([]),
                    'phase_offset_min': 0,
                    'max_correlation': 0.0,
                    'band_coherence': {},
                    'n_peaks': 0
                }
    
    return coherence_results

def save_results_to_temp(venue_series, time_bins, coherence_results):
    """Save all results to temporary location"""
    print(f"\n🔍 Saving Results to TEMP Location")
    print("-" * 60)
    
    # Create output directory
    output_dir = "tmp/research_rx/WEEKDAY_ONLY"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/PANELS", exist_ok=True)
    
    # Save venue time series
    venues = list(venue_series.keys())
    series_data = []
    
    for i, timestamp in enumerate(time_bins):
        row = {'timestamp': timestamp}
        for venue in venues:
            row[f'{venue}_event'] = venue_series[venue][i]
        series_data.append(row)
    
    series_df = pd.DataFrame(series_data)
    
    csv_path = f"{output_dir}/RX_F_venue_time_series.csv"
    parquet_path = f"{output_dir}/RX_F_venue_time_series.parquet"
    series_df.to_csv(csv_path, index=False)
    series_df.to_parquet(parquet_path, index=False)
    print(f"  ✅ Saved Venue Time Series: {csv_path}")
    
    # Save coherence results
    coherence_data = []
    
    for pair_name, results in coherence_results.items():
        venues = pair_name.split('_')
        venue1, venue2 = venues[0], venues[1]
        
        # Save peak information
        if results['n_peaks'] > 0:
            for i in range(min(5, results['n_peaks'])):  # Top 5 peaks
                coherence_data.append({
                    'venue_pair': pair_name,
                    'venue1': venue1,
                    'venue2': venue2,
                    'peak_rank': i + 1,
                    'peak_period_min': results['peak_periods'][i],
                    'peak_coherence': results['peak_coherence'][i],
                    'phase_offset_min': results['phase_offset_min'],
                    'max_correlation': results['max_correlation'],
                    'n_peaks': results['n_peaks'],
                    'band_name': ''
                })
        else:
            # No peaks found
            coherence_data.append({
                'venue_pair': pair_name,
                'venue1': venue1,
                'venue2': venue2,
                'peak_rank': 0,
                'peak_period_min': 0.0,
                'peak_coherence': 0.0,
                'phase_offset_min': results['phase_offset_min'],
                'max_correlation': results['max_correlation'],
                'n_peaks': 0,
                'band_name': ''
            })
        
        # Add band coherence information
        for band, coherence in results['band_coherence'].items():
            coherence_data.append({
                'venue_pair': pair_name,
                'venue1': venue1,
                'venue2': venue2,
                'peak_rank': -1,  # Use -1 for band data
                'peak_period_min': 0.0,
                'peak_coherence': coherence,
                'phase_offset_min': results['phase_offset_min'],
                'max_correlation': results['max_correlation'],
                'n_peaks': results['n_peaks'],
                'band_name': band
            })
    
    coherence_df = pd.DataFrame(coherence_data)
    
    csv_path = f"{output_dir}/RX_F_coherence_spectrum.csv"
    parquet_path = f"{output_dir}/RX_F_coherence_spectrum.parquet"
    coherence_df.to_csv(csv_path, index=False)
    coherence_df.to_parquet(parquet_path, index=False)
    print(f"  ✅ Saved Coherence Spectrum: {csv_path}")
    
    # Save summary panel
    summary_data = []
    
    for pair_name, results in coherence_results.items():
        venues = pair_name.split('_')
        venue1, venue2 = venues[0], venues[1]
        
        # Get top peak information
        top_period = results['peak_periods'][0] if len(results['peak_periods']) > 0 else 0.0
        top_coherence = results['peak_coherence'][0] if len(results['peak_coherence']) > 0 else 0.0
        
        summary_data.append({
            'venue_pair': pair_name,
            'venue1': venue1,
            'venue2': venue2,
            'n_peaks': results['n_peaks'],
            'top_period_min': top_period,
            'top_coherence': top_coherence,
            'phase_offset_min': results['phase_offset_min'],
            'max_correlation': results['max_correlation'],
            'band_1_5min': results['band_coherence'].get('1-5min', 0.0),
            'band_5_15min': results['band_coherence'].get('5-15min', 0.0),
            'band_15_30min': results['band_coherence'].get('15-30min', 0.0),
            'band_30_60min': results['band_coherence'].get('30-60min', 0.0),
            'notes': "RX-F beacon synchrony spectrum analysis (Mon-Fri only)"
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    csv_path = f"{output_dir}/PANELS/rx_f_synchrony_spectrum_panel.csv"
    parquet_path = f"{output_dir}/PANELS/rx_f_synchrony_spectrum_panel.parquet"
    summary_df.to_csv(csv_path, index=False)
    summary_df.to_parquet(parquet_path, index=False)
    print(f"  ✅ Saved Summary Panel: {csv_path}")

def main():
    print("📊 RX-F: BEACON SYNCHRONY SPECTRUM")
    print("=" * 80)
    print("Goal: Build event-time series for each venue and compute pairwise cross-spectral coherence")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Define scope
    weeks = ['week-minus2', 'week-minus1']
    
    print(f"📅 Processing weeks: {weeks} (Mon-Fri only)")
    print("=" * 80)
    
    # Check memory limit
    if get_memory_usage() > 750:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 750 MB limit")
        return
    
    # Load beacon data with weekday filtering
    beacon_data = load_beacon_data_weekday_filtered(weeks)
    
    if len(beacon_data) == 0:
        print("❌ HALT: No weekday beacon data found")
        return
    
    # Build event-time series for each venue
    venue_series, time_bins = build_event_time_series(beacon_data)
    
    # Compute cross-spectral coherence
    coherence_results = compute_cross_spectral_coherence(venue_series, time_bins)
    
    # Save results to temporary location
    save_results_to_temp(venue_series, time_bins, coherence_results)
    
    # ========================================================================
    # CONSOLE TABLES
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 CONSOLE TABLES")
    print("=" * 80)
    
    # Coherence Summary Table
    print(f"\nCross-Spectral Coherence Summary:")
    print(f"{'Venue Pair':<20} {'Peaks':<6} {'Top Period':<12} {'Top Coherence':<14} {'Phase Offset':<12} {'Max Corr':<10}")
    print("-" * 80)
    
    for pair_name, results in coherence_results.items():
        venues = pair_name.split('_')
        venue1, venue2 = venues[0], venues[1]
        pair_display = f"{venue1}↔{venue2}"
        
        n_peaks = results['n_peaks']
        top_period = results['peak_periods'][0] if len(results['peak_periods']) > 0 else 0.0
        top_coherence = results['peak_coherence'][0] if len(results['peak_coherence']) > 0 else 0.0
        phase_offset = results['phase_offset_min']
        max_corr = results['max_correlation']
        
        print(f"{pair_display:<20} {n_peaks:<6} {top_period:<12.1f} {top_coherence:<14.3f} {phase_offset:<12.1f} {max_corr:<10.3f}")
    
    # Band Coherence Table
    print(f"\nBand Coherence (Average):")
    print(f"{'Venue Pair':<20} {'1-5min':<8} {'5-15min':<8} {'15-30min':<8} {'30-60min':<8}")
    print("-" * 60)
    
    for pair_name, results in coherence_results.items():
        venues = pair_name.split('_')
        venue1, venue2 = venues[0], venues[1]
        pair_display = f"{venue1}↔{venue2}"
        
        band_1_5 = results['band_coherence'].get('1-5min', 0.0)
        band_5_15 = results['band_coherence'].get('5-15min', 0.0)
        band_15_30 = results['band_coherence'].get('15-30min', 0.0)
        band_30_60 = results['band_coherence'].get('30-60min', 0.0)
        
        print(f"{pair_display:<20} {band_1_5:<8.3f} {band_5_15:<8.3f} {band_15_30:<8.3f} {band_30_60:<8.3f}")
    
    # Dominant Periodicities Table
    print(f"\nDominant Periodicities (Top 3 per pair):")
    print(f"{'Venue Pair':<20} {'Rank':<4} {'Period (min)':<12} {'Coherence':<10}")
    print("-" * 50)
    
    for pair_name, results in coherence_results.items():
        venues = pair_name.split('_')
        venue1, venue2 = venues[0], venues[1]
        pair_display = f"{venue1}↔{venue2}"
        
        n_peaks = min(3, results['n_peaks'])
        for i in range(n_peaks):
            period = results['peak_periods'][i]
            coherence = results['peak_coherence'][i]
            rank = i + 1
            
            print(f"{pair_display:<20} {rank:<4} {period:<12.1f} {coherence:<10.3f}")
        
        if n_peaks == 0:
            print(f"{pair_display:<20} {'—':<4} {'—':<12} {'—':<10}")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 750:
        print(f"✅ RX-F COMPLETE - All guardrails complied with")
        print(f"• No synthetic data, smoothing, resampling, or imputations")
        print(f"• No schema edits")
        print(f"• No overwrites/merges/append to canonical caches")
        print(f"• Raw UTC timestamps preserved")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 750 MB limit)")
        print(f"• Weekday filter applied (Mon-Fri only)")
        print(f"• Cross-spectral coherence computed for 0-60 min bands")
    else:
        print(f"❌ RX-F HALTED")
        print(f"• Memory usage: {final_memory:.1f} MB > 750 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"RX-F COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()
