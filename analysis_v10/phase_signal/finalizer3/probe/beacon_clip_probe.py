#!/usr/bin/env python3
"""
Beacon Clip Probe — Ground Truth Only (3 cases, read-only)
"""

import os, json, gc, numpy as np, pandas as pd
from pathlib import Path
import psutil
import hashlib
from datetime import datetime, timedelta
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import time
import warnings
warnings.filterwarnings('ignore')

def log(m): print(m, flush=True)

def check_memory():
    rss_mb = psutil.Process().memory_info().rss / (1024**2)
    if rss_mb > 200:  # Hard halt
        raise RuntimeError(f"HALT:RAM_CAP - RAM usage: {rss_mb:.1f}MB > 200MB")
    if rss_mb > 150:  # Soft cap
        gc.collect()
    return rss_mb

def load_proximity_summary():
    """Load the proximity-mass summary from micro-check output."""
    proximity_path = "analysis_v10/phase_signal/finalizer3/audit/microcheck/proximity_counts.csv"
    
    if not Path(proximity_path).exists():
        raise RuntimeError("HALT:FILE_MISSING - proximity_counts.csv not found")
    
    df = pd.read_csv(proximity_path)
    
    # Filter for 0.25% band and get top 3 by within_band_count
    band_025 = df[df['band_pct'] == 0.25].copy()
    if len(band_025) == 0:
        raise RuntimeError("HALT:NO_DATA - No 0.25% band data found")
    
    top_3 = band_025.nlargest(3, 'within_band_count')
    
    return top_3

def find_price_crossing_timestamp(date, venue, round_level, band_pct=0.25):
    """Find the first timestamp where price enters the band around round level."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Load tick data with time filter
        dataset = ds.dataset(tick_path, format="parquet")
        
        # Load data in small batches to find crossing
        batch_size = 10000
        price_tolerance = band_pct / 100
        
        for batch in dataset.to_batches(columns=['ts', 'price'], batch_size=batch_size):
            df_batch = batch.to_pandas()
            df_batch['ts'] = pd.to_datetime(df_batch['ts'])
            
            # Check if price is within tolerance of round level
            within_band = abs(df_batch['price'] - round_level) / round_level <= price_tolerance
            
            if within_band.any():
                # Find first occurrence
                first_crossing_idx = within_band.idxmax()
                if within_band.iloc[first_crossing_idx]:
                    return df_batch.iloc[first_crossing_idx]['ts'], None
            
            # Clean up batch
            del df_batch
            gc.collect()
        
        return None, "NO_ENTRY_FOUND"
    except Exception as e:
        return None, f"Error loading tick data: {e}"

def extract_tick_window(date, venue, ts_event, window_seconds=60):
    """Extract ±60s tick window around the event timestamp."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Define time window
        start_time = ts_event - timedelta(seconds=window_seconds)
        end_time = ts_event + timedelta(seconds=window_seconds)
        
        # Load tick data with time filter
        dataset = ds.dataset(tick_path, format="parquet")
        time_filter = (ds.field("ts") >= start_time) & (ds.field("ts") <= end_time)
        
        df = dataset.to_table(
            filter=time_filter,
            columns=['ts', 'price', 'size'],
            batch_size=8192
        ).to_pandas()
        
        if len(df) == 0:
            return None, f"Empty tick data in window: {tick_path}"
            
        df['ts'] = pd.to_datetime(df['ts'])
        df['round_level_distance'] = abs(df['price'] - round_level) / round_level * 10000  # in bps
        
        return df, None
    except Exception as e:
        return None, f"Error loading tick data: {e}"

def compute_light_metrics(tick_data, round_level):
    """Compute light metrics for the tick window."""
    if tick_data is None or len(tick_data) == 0:
        return {
            'ticks_total': 0,
            'micro_trade_count': 0,
            'max_trades_10s_window': 0,
            'rev_bps_3m': 0,
            'visible_burst': False
        }
    
    # Calculate micro-trade threshold (q15)
    micro_threshold = tick_data['size'].quantile(0.15)
    
    # Count micro trades
    micro_trades = tick_data[tick_data['size'] <= micro_threshold]
    micro_trade_count = len(micro_trades)
    
    # Find max trades in 10s window
    max_trades_10s = 0
    for i in range(len(tick_data) - 10):
        window_start = tick_data.iloc[i]['ts']
        window_end = window_start + timedelta(seconds=10)
        
        window_ticks = tick_data[
            (tick_data['ts'] >= window_start) & 
            (tick_data['ts'] <= window_end)
        ]
        
        if len(window_ticks) > max_trades_10s:
            max_trades_10s = len(window_ticks)
    
    # Calculate 3-minute reversion
    rev_bps_3m = 0
    if len(tick_data) > 0:
        # Use first and last price in the window
        price_change = (tick_data['price'].iloc[-1] - tick_data['price'].iloc[0]) / tick_data['price'].iloc[0]
        rev_bps_3m = abs(price_change) * 10000
    
    # Determine if visible burst (≥3 micro trades in 10s window)
    visible_burst = max_trades_10s >= 3
    
    return {
        'ticks_total': len(tick_data),
        'micro_trade_count': micro_trade_count,
        'max_trades_10s_window': max_trades_10s,
        'rev_bps_3m': rev_bps_3m,
        'visible_burst': visible_burst
    }

# --- MAIN EXECUTION ---
log("=== Beacon Clip Probe — Ground Truth Only ===")
log(f"Memory at start: {check_memory():.1f}MB")

# Create probe output folder
PROBE_ROOT = Path("analysis_v10/phase_signal/finalizer3/probe")
PROBE_ROOT.mkdir(parents=True, exist_ok=True)

# Set start time for wall-clock cap
start_time_total = time.time()
WALL_CLOCK_CAP = 15 * 60  # 15 minutes

# A) Selection Logic
log("A) Selection Logic - Loading proximity-mass summary")
try:
    top_3_selections = load_proximity_summary()
    log(f"Selected top 3 venue×date×round combinations:")
    for i, row in top_3_selections.iterrows():
        log(f"  {i+1}. {row['venue']} {row['date']} {row['round_level']} ({row['within_band_count']} trades)")
except Exception as e:
    raise RuntimeError(f"HALT:SELECTION_FAILED - {e}")

# B) Extraction Logic
log("B) Extraction Logic - Processing each selection")
probe_results = []

for i, (_, selection) in enumerate(top_3_selections.iterrows()):
    # Check wall-clock cap
    if time.time() - start_time_total > WALL_CLOCK_CAP:
        raise RuntimeError("HALT:TIME_CAP - Exceeded 15 minutes")
    
    # Check memory
    current_memory = check_memory()
    
    venue = selection['venue']
    date = selection['date']
    round_level = selection['round_level']
    
    log(f"Processing clip {i+1}: {venue} {date} {round_level}")
    
    # Find price crossing timestamp
    ts_event, error = find_price_crossing_timestamp(date, venue, round_level)
    
    if ts_event is None:
        log(f"  No crossing found: {error}")
        # Create empty result
        probe_results.append({
            'venue': venue,
            'date': date,
            'round_level': round_level,
            'ts_event_found': None,
            'ticks_total': 0,
            'micro_trade_count': 0,
            'max_trades_10s_window': 0,
            'rev_bps_3m': 0,
            'visible_burst': False,
            'peak_rss_MB': float(check_memory()),
            'error': error
        })
        
        # Create empty CSV
        empty_df = pd.DataFrame(columns=['ts', 'price', 'size', 'venue', 'round_level_distance'])
        empty_df.to_csv(PROBE_ROOT / f"probe_clip_{i+1}.csv", index=False)
        continue
    
    log(f"  Found crossing at: {ts_event}")
    
    # Extract tick window
    tick_data, error = extract_tick_window(date, venue, ts_event)
    
    if tick_data is None:
        log(f"  Error extracting window: {error}")
        # Create empty result
        probe_results.append({
            'venue': venue,
            'date': date,
            'round_level': round_level,
            'ts_event_found': str(ts_event),
            'ticks_total': 0,
            'micro_trade_count': 0,
            'max_trades_10s_window': 0,
            'rev_bps_3m': 0,
            'visible_burst': False,
            'peak_rss_MB': float(check_memory()),
            'error': error
        })
        
        # Create empty CSV
        empty_df = pd.DataFrame(columns=['ts', 'price', 'size', 'venue', 'round_level_distance'])
        empty_df.to_csv(PROBE_ROOT / f"probe_clip_{i+1}.csv", index=False)
        continue
    
    # Compute light metrics
    metrics = compute_light_metrics(tick_data, round_level)
    
    # Save tick data to CSV
    tick_data['venue'] = venue
    tick_data.to_csv(PROBE_ROOT / f"probe_clip_{i+1}.csv", index=False)
    
    # Store results
    probe_results.append({
        'venue': venue,
        'date': date,
        'round_level': round_level,
        'ts_event_found': str(ts_event),
        'ticks_total': metrics['ticks_total'],
        'micro_trade_count': metrics['micro_trade_count'],
        'max_trades_10s_window': metrics['max_trades_10s_window'],
        'rev_bps_3m': metrics['rev_bps_3m'],
        'visible_burst': metrics['visible_burst'],
        'peak_rss_MB': float(check_memory())
    })
    
    log(f"  Metrics: {metrics['ticks_total']} ticks, {metrics['micro_trade_count']} micro trades, {metrics['max_trades_10s_window']} max in 10s, burst: {metrics['visible_burst']}")
    
    # Clean up
    del tick_data
    gc.collect()

# C) Outputs
log("C) Outputs - Writing probe_summary.json")
probe_summary = {
    "clips": probe_results,
    "total_clips": len(probe_results),
    "visible_bursts_found": sum(1 for r in probe_results if r['visible_burst']),
    "peak_rss_MB": float(check_memory()),
    "elapsed_sec": float(time.time() - start_time_total)
}

with open(PROBE_ROOT / "probe_summary.json", "w") as f:
    json.dump(probe_summary, f, indent=2)

# D) Return to Me
log("D) Return to Me")
memory_peak = float(check_memory())
elapsed_time = time.time() - start_time_total

print("\n=== Beacon Clip Probe Complete ===")
print(f"Memory peak: {memory_peak:.1f}MB")
print(f"Runtime: {elapsed_time:.1f} seconds")

print("\n1) Full probe_summary.json:")
print(json.dumps(probe_summary, indent=2))

print("\n2) Head -10 of each probe_clip_*.csv:")
for i in range(1, 4):
    clip_path = PROBE_ROOT / f"probe_clip_{i}.csv"
    if clip_path.exists():
        df = pd.read_csv(clip_path)
        print(f"\nprobe_clip_{i}.csv:")
        print(df.head(10).to_string())
    else:
        print(f"\nprobe_clip_{i}.csv: File not found")

print(f"\n3) Peak RSS memory: {memory_peak:.1f}MB")
print(f"4) Runtime: {elapsed_time:.1f} seconds")

visible_bursts_found = sum(1 for r in probe_results if r['visible_burst'])
print(f"\n5) Visible bursts observed: {visible_bursts_found} out of {len(probe_results)} clips")

log("✅ Beacon Clip Probe complete - Ground Truth Only")
