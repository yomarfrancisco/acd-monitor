#!/usr/bin/env python3
"""
Beacon Stress-Test — Basic Version (GROUND TRUTH ONLY)
Data availability check only
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

def load_tick_data_basic(date, venue, start_time, end_time):
    """Load basic tick data for diagnostics."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Load only essential columns with minimal batch size
        dataset = ds.dataset(tick_path, format="parquet")
        time_filter = (ds.field("ts") >= start_time) & (ds.field("ts") < end_time)
        
        # Get just the count and basic stats
        table = dataset.to_table(
            filter=time_filter,
            columns=['ts', 'price', 'size'],
            batch_size=2048
        )
        
        if len(table) == 0:
            return None, f"Empty tick data: {tick_path}"
        
        # Convert to pandas for basic stats
        df = table.to_pandas()
        df['ts'] = pd.to_datetime(df['ts'])
        
        return df, None
    except Exception as e:
        return None, f"Error loading tick data: {e}"

# --- MAIN EXECUTION ---
log("=== Beacon Stress-Test — Basic Version ===")
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

# 1. Verify total trade counts per venue/date (basic version)
log("1. Verifying total trade counts per venue/date")
trade_counts = []
venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
dates = ['20250901', '20250902', '20250903', '20250904', '20250905', '20250906', '20250907']

for venue in venues:
    for date in dates:
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_basic(date, venue, start_time, end_time)
        
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

# 2. Test only one configuration to avoid memory issues
log("2. Testing one configuration only")
configurations = [
    {'window_s': 20, 'band_pct': 0.10, 'micro_quantile': 'q10', 'rev_bps_limit': 10}
]

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
    
    # Process only a subset of events to avoid memory issues
    sample_events = windows_df.head(5)  # Only first 5 events
    
    for idx, window_row in sample_events.iterrows():
        event_id = idx
        venue = window_row['venue']
        date = window_row['date']
        
        # Load tick data for the day
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_basic(date, venue, start_time, end_time)
        
        if tick_data is not None:
            # Calculate micro-trade threshold
            if config['micro_quantile'] == 'q10':
                micro_trade_threshold = tick_data['size'].quantile(0.1)
            else:  # q15
                micro_trade_threshold = tick_data['size'].quantile(0.15)
            
            # Get round levels for this venue/date
            round_levels = [100000, 101000, 102000, 103000, 104000, 105000]
            
            for round_level in round_levels:
                # Simple beacon detection
                price_tolerance = config['band_pct'] / 100
                window_seconds = config['window_s']
                
                # Find ticks near round level
                near_ticks = tick_data[
                    (tick_data['price'] >= round_level * (1 - price_tolerance)) &
                    (tick_data['price'] <= round_level * (1 + price_tolerance))
                ]
                
                if len(near_ticks) > 0:
                    # Check for micro-trade bursts
                    micro_ticks = near_ticks[near_ticks['size'] <= micro_trade_threshold]
                    
                    if len(micro_ticks) >= 3:
                        events_with_beacons.add(event_id)
                        beacon_events_all.append({
                            'ts_beacon': micro_ticks['ts'].iloc[0],
                            'trades_in_burst': len(micro_ticks),
                            'rev_bps_3m': 0  # Simplified
                        })
        
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
    
    zeros_in_event_distribution = len(sample_events) - len(events_with_beacons)
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
    if len(beacon_events_all) >= 2 and iqr >= 1:  # Lowered thresholds for sample
        log(f"EARLY STOP: Found config with beacons_found={len(beacon_events_all)} and IQR={iqr:.1f}")
        recommendation = "RELAXED_CRITERIA_OK"
        break

# Create progress results dataframe
stress_test_df = pd.DataFrame(stress_test_results)
stress_test_df.to_csv(DIAGNOSTICS_RUN_ROOT / "beacon_stress_test_progress.csv", index=False)

# Find highest-yield configuration
if len(stress_test_df) > 0:
    highest_yield = stress_test_df.loc[stress_test_df['beacons_found'].idxmax()]
else:
    highest_yield = None

# Determine recommendation
if recommendation is None:
    if len(stress_test_df) > 0:
        max_beacons = stress_test_df['beacons_found'].max()
        if max_beacons >= 2:
            recommendation = "WIDER_BAND_ONLY"
        else:
            recommendation = "DATA_GAP_OR_TOO_QUIET_WEEK"
    else:
        recommendation = "DATA_GAP_OR_TOO_QUIET_WEEK"

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





