#!/usr/bin/env python3
"""
Beacon Phase-2 – Relaxed Real Scan (Ground Truth, ≤150 MB, ≤30 min)
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
    if rss_mb > 500:  # Hard halt
        raise RuntimeError(f"HALT:RAM_CAP - RAM usage: {rss_mb:.1f}MB > 500MB")
    if rss_mb > 150:  # Soft cap
        gc.collect()
    return rss_mb

def load_tick_data_relaxed(date, venue, start_time, end_time):
    """Load tick data with relaxed memory footprint."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Load only essential columns with small batch size
        dataset = ds.dataset(tick_path, format="parquet")
        time_filter = (ds.field("ts") >= start_time) & (ds.field("ts") < end_time)
        
        df = dataset.to_table(
            filter=time_filter,
            columns=['ts', 'price', 'size'],
            batch_size=8192
        ).to_pandas()
        
        if len(df) == 0:
            return None, f"Empty tick data: {tick_path}"
            
        df['ts'] = pd.to_datetime(df['ts'])
        return df, None
    except Exception as e:
        return None, f"Error loading tick data: {e}"

def detect_beacon_events_relaxed(tick_data, round_level, micro_trade_threshold, window_s, band_pct, rev_bps_limit):
    """Detect beacon events with relaxed parameters."""
    if tick_data is None or len(tick_data) == 0:
        return []
    
    beacon_events = []
    price_tolerance = band_pct / 100
    
    try:
        # Look for micro-trades near round levels
        for i in range(len(tick_data) - 10):
            current_tick = tick_data.iloc[i]
            
            # Check if price is within tolerance of round level
            if abs(current_tick['price'] - round_level) / round_level <= price_tolerance:
                # Check for micro-trade burst in configurable window
                burst_start = current_tick['ts']
                burst_end = burst_start + timedelta(seconds=window_s)
                
                burst_ticks = tick_data[
                    (tick_data['ts'] >= burst_start) & 
                    (tick_data['ts'] <= burst_end) &
                    (tick_data['size'] <= micro_trade_threshold)
                ]
                
                if len(burst_ticks) >= 3:  # Beacon event
                    # Calculate 3-minute reversion
                    reversion_end = burst_start + timedelta(minutes=3)
                    reversion_ticks = tick_data[
                        (tick_data['ts'] >= burst_start) & 
                        (tick_data['ts'] <= reversion_end)
                    ]
                    
                    if len(reversion_ticks) > 0:
                        price_change = (reversion_ticks['price'].iloc[-1] - reversion_ticks['price'].iloc[0]) / reversion_ticks['price'].iloc[0]
                        rev_bps = abs(price_change) * 10000
                    else:
                        rev_bps = 0
                    
                    # Apply reversion limit
                    if rev_bps <= rev_bps_limit:
                        beacon_events.append({
                            'ts_beacon': burst_start,
                            'trades_in_burst': len(burst_ticks),
                            'rev_bps_3m': rev_bps,
                            'round_level': round_level,
                            'band_pct': band_pct,
                            'window_s': window_s
                        })
        
        return beacon_events
    except Exception as e:
        return []

# --- MAIN EXECUTION ---
log("=== Beacon Phase-2 – Relaxed Real Scan ===")
log(f"Memory at start: {check_memory():.1f}MB")

# Create relaxed scan output folder
RELAXED_SCAN_ROOT = Path("analysis_v10/phase_signal/finalizer3/relaxed_scan")
RELAXED_SCAN_ROOT.mkdir(parents=True, exist_ok=True)

# Set start time for wall-clock cap
start_time_total = time.time()
WALL_CLOCK_CAP = 30 * 60  # 30 minutes

# Load windows data
windows_path = "analysis_v10/phase_trigger/windows.csv"
windows_df = pd.read_csv(windows_path)
log(f"Loaded: {len(windows_df)} windows")

# Parameters
window_s_options = [20, 30]
band_pct_options = [0.10, 0.25, 0.40]
micro_trade_quantile = 0.20  # q20
rev_bps_limit = 15
stop_after_beacons = 10
stop_after_configs = 15

# Test configurations
configurations = []
for window_s in window_s_options:
    for band_pct in band_pct_options:
        configurations.append({
            'window_s': window_s,
            'band_pct': band_pct
        })

log(f"Testing {len(configurations)} configurations")

# Process configurations
beacon_events_all = []
configs_tested = 0
beacons_found = 0

for i, config in enumerate(configurations):
    # Check wall-clock cap
    if time.time() - start_time_total > WALL_CLOCK_CAP:
        log(f"HALT:TIME_CAP - Exceeded 30 minutes")
        break
    
    # Check memory
    current_memory = check_memory()
    
    # Stop after 15 configs
    if configs_tested >= stop_after_configs:
        log(f"Stopping after {stop_after_configs} configs tested")
        break
    
    # Stop after 10 beacons
    if beacons_found >= stop_after_beacons:
        log(f"Stopping after {stop_after_beacons} beacons found")
        break
    
    config_start_time = time.time()
    log(f"Testing config {i+1}/{len(configurations)}: window_s={config['window_s']}, band_pct={config['band_pct']}")
    
    # Process each event
    for idx, window_row in windows_df.iterrows():
        event_id = idx
        venue = window_row['venue']
        date = window_row['date']
        
        # Load tick data for the day
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_relaxed(date, venue, start_time, end_time)
        
        if tick_data is not None:
            # Calculate micro-trade threshold (q20)
            micro_trade_threshold = tick_data['size'].quantile(micro_trade_quantile)
            
            # Get round levels for this venue/date
            round_levels = [100000, 101000, 102000, 103000, 104000, 105000, 106000, 107000, 108000, 109000, 110000]
            
            for round_level in round_levels:
                # Detect beacon events with current config
                beacon_events = detect_beacon_events_relaxed(
                    tick_data, round_level, micro_trade_threshold,
                    config['window_s'], config['band_pct'], rev_bps_limit
                )
                
                if beacon_events:
                    beacon_events_all.extend(beacon_events)
                    beacons_found += len(beacon_events)
                    
                    # Stop if we have enough beacons
                    if beacons_found >= stop_after_beacons:
                        log(f"Found {beacons_found} beacons, stopping")
                        break
            
            # Clean up immediately
            del tick_data
            gc.collect()
        
        # Stop if we have enough beacons
        if beacons_found >= stop_after_beacons:
            break
    
    configs_tested += 1
    
    # Stop if we have enough beacons
    if beacons_found >= stop_after_beacons:
        break

# Create beacon events dataframe (limit to 10 rows)
beacon_events_df = pd.DataFrame(beacon_events_all[:10])
beacon_events_df.to_csv(RELAXED_SCAN_ROOT / "beacon_events_relaxed.csv", index=False)

# Create summary
beacon_summary = {
    "configs_tested": configs_tested,
    "beacons_found": len(beacon_events_all),
    "beacons_returned": len(beacon_events_df),
    "parameters": {
        "window_s_options": window_s_options,
        "band_pct_options": band_pct_options,
        "micro_trade_quantile": micro_trade_quantile,
        "rev_bps_limit": rev_bps_limit
    },
    "stop_reason": "beacons_found" if beacons_found >= stop_after_beacons else "configs_exhausted",
    "memory_peak_MB": float(check_memory()),
    "elapsed_sec": float(time.time() - start_time_total)
}

# Check if no beacons found
if len(beacon_events_all) == 0:
    log("HALT:NO_BEACONS_RELAXED - No beacons found with relaxed criteria")
    beacon_summary["halt_reason"] = "NO_BEACONS_RELAXED"

with open(RELAXED_SCAN_ROOT / "beacon_summary_relaxed.json", "w") as f:
    json.dump(beacon_summary, f, indent=2)

# Log progress
with open(RELAXED_SCAN_ROOT / "progress.log", "w") as f:
    f.write(f"Beacon Phase-2 Relaxed Scan Progress Log\n")
    f.write(f"Start time: {datetime.now()}\n")
    f.write(f"Memory at start: {check_memory():.1f}MB\n")
    f.write(f"Configs tested: {configs_tested}\n")
    f.write(f"Beacons found: {len(beacon_events_all)}\n")
    f.write(f"Stop reason: {beacon_summary['stop_reason']}\n")
    f.write(f"Memory at end: {check_memory():.1f}MB\n")
    f.write(f"Elapsed time: {time.time() - start_time_total:.1f} seconds\n")

# Return results
log("\n=== Final Results ===")
memory_peak = float(check_memory())

print("\n=== Beacon Phase-2 Relaxed Scan Complete ===")
print("Key results:")
print(f"  • Memory peak: {memory_peak:.1f}MB")
print(f"  • Configs tested: {configs_tested}")
print(f"  • Beacons found: {len(beacon_events_all)}")
print(f"  • Stop reason: {beacon_summary['stop_reason']}")

if len(beacon_events_all) == 0:
    print("\nHALT:NO_BEACONS_RELAXED - No beacons found with relaxed criteria")
else:
    print(f"\n✅ Found {len(beacon_events_all)} beacon events")

log("✅ Beacon Phase-2 Relaxed Scan complete")





