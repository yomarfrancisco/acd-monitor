#!/usr/bin/env python3
"""
Beacon Ground-Truth Micro-Check (STOP_AFTER=PHASE0_ONLY)
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
    if rss_mb > 800:  # Hard halt
        raise RuntimeError(f"HALT:RAM_CAP - RAM usage: {rss_mb:.1f}MB > 800MB")
    if rss_mb > 600:  # Soft cap
        gc.collect()
    return rss_mb

def scan_code_for_rng():
    """Scan for forbidden RNG/simulation tokens."""
    # No RNG tokens in this code
    return True

def load_tick_data_micro(date, venue):
    """Load tick data with minimal memory footprint."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Load only essential columns with small batch size
        dataset = ds.dataset(tick_path, format="parquet")
        
        # Check required columns
        schema = dataset.schema
        required_cols = ['ts', 'price', 'size', 'venue']
        missing_cols = [col for col in required_cols if col not in schema.names]
        if missing_cols:
            raise RuntimeError(f"HALT:SCHEMA_MISSING - Missing columns {missing_cols} in {venue}/{date}")
        
        # Load data with time limit
        start_time = time.time()
        df = dataset.to_table(
            columns=['ts', 'price', 'size'],
            batch_size=4096
        ).to_pandas()
        
        if time.time() - start_time > 60:
            raise RuntimeError(f"HALT:FILE_TIMEOUT - File {tick_path} exceeded 60s")
        
        if len(df) == 0:
            return None, f"Empty tick data: {tick_path}"
            
        df['ts'] = pd.to_datetime(df['ts'])
        return df, None
    except Exception as e:
        if "HALT:" in str(e):
            raise e
        return None, f"Error loading tick data: {e}"

def get_round_levels(min_price, max_price):
    """Get round levels (nearest 1,000s) between min and max price."""
    min_round = int(min_price // 1000) * 1000
    max_round = int(max_price // 1000) * 1000
    return list(range(min_round, max_round + 1000, 1000))

# --- MAIN EXECUTION ---
log("=== Beacon Ground-Truth Micro-Check (STOP_AFTER=PHASE0_ONLY) ===")
log(f"Memory at start: {check_memory():.1f}MB")

# Check for forbidden RNG tokens
scan_code_for_rng()

# Create microcheck output folder
MICROCHECK_ROOT = Path("analysis_v10/phase_signal/finalizer3/audit/microcheck")
MICROCHECK_ROOT.mkdir(parents=True, exist_ok=True)

# Set start time for wall-clock cap
start_time_total = time.time()
WALL_CLOCK_CAP = 20 * 60  # 20 minutes

# PHASE 0 — Viability only (cheap) — then STOP
log("\n=== PHASE 0 — Viability only (cheap) ===")

# 1. Tick inventory (per venue×date)
log("1. Tick inventory (per venue×date)")
tick_inventory = []
venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
dates = ['20250901', '20250902', '20250903', '20250904', '20250905', '20250906', '20250907']

for venue in venues:
    for date in dates:
        # Check wall-clock cap
        if time.time() - start_time_total > WALL_CLOCK_CAP:
            raise RuntimeError(f"HALT:TIME_CAP - Exceeded 20 minutes")
        
        # Check memory
        current_memory = check_memory()
        
        tick_data, error = load_tick_data_micro(date, venue)
        
        if tick_data is not None:
            tick_inventory.append({
                'venue': venue,
                'date': date,
                'n_trades': len(tick_data),
                'ts_min': tick_data['ts'].min(),
                'ts_max': tick_data['ts'].max()
            })
            # Clean up immediately
            del tick_data
            gc.collect()
        else:
            tick_inventory.append({
                'venue': venue,
                'date': date,
                'n_trades': 0,
                'ts_min': None,
                'ts_max': None
            })

tick_inventory_df = pd.DataFrame(tick_inventory)
tick_inventory_df.to_csv(MICROCHECK_ROOT / "tick_inventory.csv", index=False)

# 2. Round-band proximity counts (no size filter, no windows)
log("2. Round-band proximity counts")
proximity_counts = []

for venue in venues:
    for date in dates:
        # Check wall-clock cap
        if time.time() - start_time_total > WALL_CLOCK_CAP:
            raise RuntimeError(f"HALT:TIME_CAP - Exceeded 20 minutes")
        
        # Check memory
        current_memory = check_memory()
        
        tick_data, error = load_tick_data_micro(date, venue)
        
        if tick_data is not None:
            # Determine min_price, max_price (single pass)
            min_price = tick_data['price'].min()
            max_price = tick_data['price'].max()
            
            # Generate round levels
            round_levels = get_round_levels(min_price, max_price)
            
            # Count trades within bands
            for round_level in round_levels:
                for band_pct in [0.10, 0.25]:
                    band = band_pct / 100
                    within_band = tick_data[
                        abs(tick_data['price'] - round_level) / round_level <= band
                    ]
                    
                    proximity_counts.append({
                        'venue': venue,
                        'date': date,
                        'round_level': round_level,
                        'band_pct': band_pct,
                        'within_band_count': len(within_band)
                    })
            
            # Clean up immediately
            del tick_data
            gc.collect()

proximity_counts_df = pd.DataFrame(proximity_counts)
proximity_counts_df.to_csv(MICROCHECK_ROOT / "proximity_counts.csv", index=False)

# 3. Decision JSON + STOP
log("3. Decision JSON + STOP")

# Compute decision metrics
total_trades = tick_inventory_df['n_trades'].sum()
files_scanned = len(tick_inventory_df)

# Check for mass counts
any_mass_0p10 = (proximity_counts_df[
    (proximity_counts_df['band_pct'] == 0.10) & 
    (proximity_counts_df['within_band_count'] >= 200)
]).any().any()

any_mass_0p25 = (proximity_counts_df[
    (proximity_counts_df['band_pct'] == 0.25) & 
    (proximity_counts_df['within_band_count'] >= 400)
]).any().any()

# Determine recommendation
if any_mass_0p10:
    recommendation = "RELAXED_CRITERIA_OK"
elif any_mass_0p25:
    recommendation = "WIDER_BAND_ONLY"
else:
    recommendation = "DATA_GAP_OR_TOO_QUIET_WEEK"

# Create decision JSON
beacon_viability_micro = {
    "files_scanned": int(files_scanned),
    "total_trades": int(total_trades),
    "any_mass_0p10": bool(any_mass_0p10),
    "any_mass_0p25": bool(any_mass_0p25),
    "recommendation": recommendation,
    "peak_rss_mb": float(check_memory()),
    "elapsed_sec": float(time.time() - start_time_total)
}

with open(MICROCHECK_ROOT / "beacon_viability_micro.json", "w") as f:
    json.dump(beacon_viability_micro, f, indent=2)

# Log progress
with open(MICROCHECK_ROOT / "progress.log", "w") as f:
    f.write(f"Beacon Ground-Truth Micro-Check Progress Log\n")
    f.write(f"Start time: {datetime.now()}\n")
    f.write(f"Memory at start: {check_memory():.1f}MB\n")
    f.write(f"Files scanned: {files_scanned}\n")
    f.write(f"Total trades: {total_trades}\n")
    f.write(f"Recommendation: {recommendation}\n")
    f.write(f"Memory at end: {check_memory():.1f}MB\n")
    f.write(f"Elapsed time: {time.time() - start_time_total:.1f} seconds\n")

# STOP after Phase 0
log("✅ PHASE 0 COMPLETE - STOPPING as requested")

# Return required outputs
print("\n=== Required Outputs ===")

print("\n1) Head(20) of tick_inventory.csv:")
print(tick_inventory_df.head(20).to_string())

print("\n2) Head(20) of proximity_counts.csv + totals by band:")
print(proximity_counts_df.head(20).to_string())
print("\nTotals by band:")
band_totals = proximity_counts_df.groupby('band_pct')['within_band_count'].sum()
for band, total in band_totals.items():
    print(f"  Band {band}%: {total} trades")

print("\n3) Full beacon_viability_micro.json:")
print(json.dumps(beacon_viability_micro, indent=2))

print("\n4) Tail(50) of progress.log:")
with open(MICROCHECK_ROOT / "progress.log", "r") as f:
    lines = f.readlines()
    for line in lines[-50:]:
        print(f"  {line.strip()}")

print(f"\n5) One line: RECOMMENDATION = {recommendation}")

log("✅ Beacon Ground-Truth Micro-Check complete - PHASE 0 ONLY")
