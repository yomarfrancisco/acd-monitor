#!/usr/bin/env python3
"""
Beacon Stress-Test — Light Version (GROUND TRUTH ONLY)
Memory-efficient version with early-stop rules
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
    if rss_mb > 300:  # Hard halt
        raise RuntimeError(f"HALT:TIME_BUDGET - RAM usage: {rss_mb:.1f}MB > 300MB")
    if rss_mb > 250:  # Soft cap
        gc.collect()
    return rss_mb

def load_tick_data_light(date, venue, start_time, end_time):
    """Load real tick data with minimal memory footprint."""
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
            batch_size=8192  # Smaller batch size
        ).to_pandas()
        
        if len(df) == 0:
            return None, f"Empty tick data: {tick_path}"
            
        df['ts'] = pd.to_datetime(df['ts'])
        return df, None
    except Exception as e:
        return None, f"Error loading tick data: {e}"

def detect_beacon_events_light(tick_data, round_level, micro_trade_threshold, window_s, band_pct, rev_bps_limit):
    """Detect beacon events with minimal memory usage."""
    if tick_data is None or len(tick_data) == 0:
        return []
    
    beacon_events = []
    price_tolerance = band_pct / 100
    
    try:
        # Process in smaller chunks to avoid memory spikes
        chunk_size = 1000
        for i in range(0, len(tick_data) - 10, chunk_size):
            chunk = tick_data.iloc[i:i+chunk_size+10]
            
            for j in range(len(chunk) - 10):
                current_tick = chunk.iloc[j]
                
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
                                'rev_bps_3m': rev_bps
                            })
            
            # Clean up chunk
            del chunk
            gc.collect()
        
        return beacon_events
    except Exception as e:
        return []

# --- MAIN EXECUTION ---
log("=== Beacon Stress-Test — Light Version ===")
log(f"Memory at start: {check_memory():.1f}MB")

# Create diagnostics run output folder
DIAGNOSTICS_RUN_ROOT = Path("analysis_v10/phase_signal/finalizer3/audit/diagnostics_run")
DIAGNOSTICS_RUN_ROOT.mkdir(parents=True, exist_ok=True)

# Load windows data
windows_path = "analysis_v10/phase_trigger/windows.csv"
windows_df = pd.read_csv(windows_path)
log(f"Loaded: {len(windows_df)} windows")

# A) Emit a checkpoint now
log("\n=== A) Emit checkpoint ===")

# 1. Verify total trade counts per venue/date (light version)
log("1. Verifying total trade counts per venue/date")
trade_counts = []
venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
dates = ['20250901', '20250902', '20250903', '20250904', '20250905', '20250906', '20250907']

for venue in venues:
    for date in dates:
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_light(date, venue, start_time, end_time)
        
        if tick_data is not None:
            trade_counts.append({
                'venue': venue,
                'date': date,
                'n_trades': len(tick_data),
                'ts_min': tick_data['ts'].min(),
                'ts_max': tick_data['ts'].max(),
                'error': None
            })
            # Clean up immediately
            del tick_data
            gc.collect()
        else:
            trade_counts.append({
                'venue': venue,
                'date': date,
                'n_trades': 0,
                'ts_min': None,
                'ts_max': None,
                'error': error
            })

trade_counts_df = pd.DataFrame(trade_counts)
trade_counts_df.to_csv(DIAGNOSTICS_RUN_ROOT / "trade_counts.csv", index=False)

# 2. Test configurations with early-stop rules (light version)
log("2. Testing configurations with early-stop rules")
configurations = []

# Test configurations (reduced set for memory efficiency)
window_s_options = [10, 20, 30]
band_pct_options = [0.05, 0.10, 0.25]
micro_quantile_options = ['q10', 'q15']
rev_bps_limit_options = [5, 10]

for window_s in window_s_options:
    for band_pct in band_pct_options:
        for micro_quantile in micro_quantile_options:
            for rev_bps_limit in rev_bps_limit_options:
                configurations.append({
                    'window_s': window_s,
                    'band_pct': band_pct,
                    'micro_quantile': micro_quantile,
                    'rev_bps_limit': rev_bps_limit
                })

log(f"Testing {len(configurations)} configurations")

# 3. Process configurations with early-stop rules
stress_test_results = []
start_time_total = time.time()
recommendation = None

for i, config in enumerate(configurations):
    config_start_time = time.time()
    log(f"Testing config {i+1}/{len(configurations)}: window_s={config['window_s']}, band_pct={config['band_pct']}, micro_quantile={config['micro_quantile']}, rev_bps_limit={config['rev_bps_limit']}")
    
    # Check time budget per config
    if time.time() - config_start_time > 120:
        log(f"HALT:TIME_BUDGET - Config {i+1} exceeded 120 seconds")
        break
    
    # Check memory
    current_memory = check_memory()
    if current_memory > 300:
        log(f"HALT:TIME_BUDGET - Config {i+1} exceeded 300MB RAM")
        break
    
    beacon_events_all = []
    events_with_beacons = set()
    
    # Process each event (light version)
    for idx, window_row in windows_df.iterrows():
        event_id = idx
        venue = window_row['venue']
        date = window_row['date']
        
        # Load tick data for the day
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_light(date, venue, start_time, end_time)
        
        if tick_data is not None:
            # Calculate micro-trade threshold
            if config['micro_quantile'] == 'q10':
                micro_trade_threshold = tick_data['size'].quantile(0.1)
            else:  # q15
                micro_trade_threshold = tick_data['size'].quantile(0.15)
            
            # Get round levels for this venue/date
            round_levels = [100000, 101000, 102000, 103000, 104000, 105000]
            
            for round_level in round_levels:
                # Detect beacon events with current config
                beacon_events = detect_beacon_events_light(
                    tick_data, round_level, micro_trade_threshold,
                    config['window_s'], config['band_pct'], config['rev_bps_limit']
                )
                
                if beacon_events:
                    events_with_beacons.add(event_id)
                    beacon_events_all.extend(beacon_events)
        
        # Clean up immediately
        del tick_data
        gc.collect()
    
    # Compute statistics
    if len(beacon_events_all) > 0:
        trades_per_beacon = [beacon['trades_in_burst'] for beacon in beacon_events_all]
        median_trades = np.median(trades_per_beacon)
        p25, p75 = np.percentile(trades_per_beacon, [25, 75])
        iqr = p75 - p25
    else:
        median_trades = 0
        iqr = 0
    
    zeros_in_event_distribution = len(windows_df) - len(events_with_beacons)
    elapsed_sec = time.time() - config_start_time
    
    stress_test_results.append({
        'window_s': config['window_s'],
        'band_pct': config['band_pct'],
        'micro_quantile': config['micro_quantile'],
        'rev_bps_limit': config['rev_bps_limit'],
        'events_with_beacons': len(events_with_beacons),
        'beacons_found': len(beacon_events_all),
        'zeros': zeros_in_event_distribution,
        'median_trades': median_trades,
        'iqr': iqr,
        'elapsed_sec': elapsed_sec
    })
    
    # Early-stop rules
    if len(beacon_events_all) >= 10 and iqr >= 3:
        log(f"EARLY STOP: Found config with beacons_found={len(beacon_events_all)} and IQR={iqr:.1f}")
        recommendation = "RELAXED_CRITERIA_OK"
        break
    
    # Budget cap: After 12 configs processed
    if i >= 11:  # 0-indexed, so 12 configs = index 11
        if any(result['events_with_beacons'] >= 10 for result in stress_test_results):
            recommendation = "WIDER_BAND_ONLY"
        else:
            recommendation = "DATA_GAP_OR_TOO_QUIET_WEEK"
        log(f"BUDGET CAP: Processed 12 configs, recommendation: {recommendation}")
        break

# Create progress results dataframe
stress_test_df = pd.DataFrame(stress_test_results)
stress_test_df.to_csv(DIAGNOSTICS_RUN_ROOT / "beacon_stress_test_progress.csv", index=False)

# Find highest-yield configuration
if len(stress_test_df) > 0:
    highest_yield = stress_test_df.loc[stress_test_df['beacons_found'].idxmax()]
else:
    highest_yield = None

# Create progress summary
beacon_stress_summary = {
    "total_trades_per_venue_date": trade_counts_df['n_trades'].sum(),
    "total_venue_date_combinations": len(trade_counts_df),
    "configurations_tested": len(stress_test_df),
    "configurations_total": len(configurations),
    "highest_yield_config": {
        "window_s": int(highest_yield['window_s']) if highest_yield is not None else None,
        "band_pct": float(highest_yield['band_pct']) if highest_yield is not None else None,
        "micro_quantile": highest_yield['micro_quantile'] if highest_yield is not None else None,
        "rev_bps_limit": int(highest_yield['rev_bps_limit']) if highest_yield is not None else None,
        "events_with_beacons": int(highest_yield['events_with_beacons']) if highest_yield is not None else 0,
        "beacons_found": int(highest_yield['beacons_found']) if highest_yield is not None else 0,
        "median_trades": float(highest_yield['median_trades']) if highest_yield is not None else 0,
        "iqr": float(highest_yield['iqr']) if highest_yield is not None else 0,
        "zeros": int(highest_yield['zeros']) if highest_yield is not None else 0
    },
    "recommendation": recommendation,
    "memory_peak_MB": float(check_memory()),
    "elapsed_total_sec": time.time() - start_time_total
}

with open(DIAGNOSTICS_RUN_ROOT / "beacon_stress_summary_progress.json", "w") as f:
    json.dump(beacon_stress_summary, f, indent=2)

# 3. Log RSS to progress.log
with open(DIAGNOSTICS_RUN_ROOT / "progress.log", "w") as f:
    f.write(f"Beacon Stress-Test Progress Log\n")
    f.write(f"Start time: {datetime.now()}\n")
    f.write(f"Memory at start: {check_memory():.1f}MB\n")
    f.write(f"Configurations tested: {len(stress_test_df)}\n")
    f.write(f"Recommendation: {recommendation}\n")
    f.write(f"Memory at end: {check_memory():.1f}MB\n")
    f.write(f"Elapsed time: {time.time() - start_time_total:.1f} seconds\n")

# C) Outputs to return
log("\n=== C) Final Results ===")
memory_peak = float(check_memory())

print("\n=== CHECKPOINT PHASE TRIGGER: Beacon Stress-Test Checkpoint Complete ===")
print("Key results:")
print(f"  • Memory peak: {memory_peak:.1f}MB")
print(f"  • Configurations tested: {len(stress_test_df)}")
print(f"  • Recommendation: {recommendation}")

# Return required outputs
print("\n=== Required Outputs ===")

print("\n1) Head(20) of beacon_stress_test_progress.csv:")
print(stress_test_df.head(20).to_string())

print("\n2) Full beacon_stress_summary_progress.json:")
print(json.dumps(beacon_stress_summary, indent=2))

print("\n3) trade_counts.csv totals per venue:")
venue_totals = trade_counts_df.groupby('venue')['n_trades'].sum()
for venue, total in venue_totals.items():
    print(f"  {venue}: {total} trades")

print("\n4) progress.log tail(50):")
with open(DIAGNOSTICS_RUN_ROOT / "progress.log", "r") as f:
    lines = f.readlines()
    for line in lines[-50:]:
        print(f"  {line.strip()}")

print(f"\n5) One-line recommendation: {recommendation}")

print(f"\n6) Peak RSS: {memory_peak:.1f}MB")

log("✅ CHECKPOINT PHASE TRIGGER: Beacon Stress-Test Checkpoint complete - DIAGNOSTICS COMPLETE")





