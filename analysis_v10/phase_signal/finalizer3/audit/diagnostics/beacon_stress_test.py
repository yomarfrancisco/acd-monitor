#!/usr/bin/env python3
"""
Beacon Stress-Test (diagnostic only)
Determine whether beacon scarcity arises from data gaps or overly strict detection thresholds
"""

import os, json, gc, numpy as np, pandas as pd
from pathlib import Path
import psutil
import hashlib
from datetime import datetime, timedelta
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import warnings
warnings.filterwarnings('ignore')

def log(m): print(m, flush=True)

def check_memory():
    rss_mb = psutil.Process().memory_info().rss / (1024**2)
    if rss_mb > 350:
        raise RuntimeError(f"STOP:RESOURCE_LIMIT - RAM usage: {rss_mb:.1f}MB > 350MB")
    if rss_mb > 300:
        gc.collect()
    return rss_mb

def compute_file_hash(path):
    """Compute SHA256 hash of a file."""
    if not Path(path).exists():
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def load_tick_data_diagnostic(date, venue, start_time, end_time):
    """Load real tick data from canonical sources for diagnostics."""
    tick_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not Path(tick_path).exists():
        return None, f"Missing tick file: {tick_path}"
    
    try:
        # Load tick data with time filter
        dataset = ds.dataset(tick_path, format="parquet")
        time_filter = (ds.field("ts") >= start_time) & (ds.field("ts") < end_time)
        
        df = dataset.to_table(
            filter=time_filter,
            columns=['ts', 'price', 'size'],
            batch_size=16384
        ).to_pandas()
        
        if len(df) == 0:
            return None, f"Empty tick data: {tick_path}"
            
        df['ts'] = pd.to_datetime(df['ts'])
        return df, None
    except Exception as e:
        return None, f"Error loading tick data: {e}"

def detect_beacon_events_stress_test(tick_data, round_level, micro_trade_threshold, window_s, band_pct, rev_bps_limit):
    """Detect beacon events with configurable parameters."""
    if tick_data is None or len(tick_data) == 0:
        return []
    
    beacon_events = []
    price_tolerance = band_pct / 100  # Convert percentage to decimal
    
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
                            'rev_bps_3m': rev_bps
                        })
        
        return beacon_events
    except Exception as e:
        return []

# --- MAIN EXECUTION ---
log("=== Beacon Stress-Test (diagnostic only) ===")
log(f"Memory at start: {check_memory():.1f}MB")

# Create diagnostics output folder
DIAGNOSTICS_ROOT = Path("analysis_v10/phase_signal/finalizer3/audit/diagnostics")
DIAGNOSTICS_ROOT.mkdir(parents=True, exist_ok=True)

# Load windows data
windows_path = "analysis_v10/phase_trigger/windows.csv"
windows_df = pd.read_csv(windows_path)
log(f"Loaded: {len(windows_df)} windows")

# 1. Verify total trade counts per venue/date
log("\n=== 1. Verify total trade counts per venue/date ===")
trade_counts = []
venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
dates = ['20250901', '20250902', '20250903', '20250904', '20250905', '20250906', '20250907']

for venue in venues:
    for date in dates:
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_diagnostic(date, venue, start_time, end_time)
        
        if tick_data is not None:
            trade_counts.append({
                'venue': venue,
                'date': date,
                'total_trades': len(tick_data),
                'min_price': tick_data['price'].min(),
                'max_price': tick_data['price'].max(),
                'min_size': tick_data['size'].min(),
                'max_size': tick_data['size'].max(),
                'q10_size': tick_data['size'].quantile(0.1),
                'q15_size': tick_data['size'].quantile(0.15),
                'error': None
            })
        else:
            trade_counts.append({
                'venue': venue,
                'date': date,
                'total_trades': 0,
                'min_price': None,
                'max_price': None,
                'min_size': None,
                'max_size': None,
                'q10_size': None,
                'q15_size': None,
                'error': error
            })

trade_counts_df = pd.DataFrame(trade_counts)
trade_counts_df.to_csv(DIAGNOSTICS_ROOT / "trade_counts.csv", index=False)

# Check for missing data
missing_data = trade_counts_df[trade_counts_df['total_trades'] == 0]
if len(missing_data) > 0:
    log("HALT: MISSING_TICKS - Missing tick data detected")
    log("Missing data:")
    for _, row in missing_data.iterrows():
        log(f"  {row['venue']} {row['date']}: {row['error']}")
    exit(1)

log(f"Trade counts verified: {len(trade_counts_df)} venue/date combinations")
log(f"Total trades: {trade_counts_df['total_trades'].sum()}")

# 2. Iterate relaxed configurations
log("\n=== 2. Iterate relaxed configurations ===")
configurations = []

# Test configurations
window_s_options = [10, 20, 30]
band_pct_options = [0.05, 0.10, 0.25]
micro_quantile_options = ['q10', 'q15']
rev_bps_limit_options = [5, 10]  # X and 2X

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

# 3. For each combo, compute beacon statistics
log("\n=== 3. Compute beacon statistics for each configuration ===")
stress_test_results = []

for config in configurations:
    log(f"Testing config: window_s={config['window_s']}, band_pct={config['band_pct']}, micro_quantile={config['micro_quantile']}, rev_bps_limit={config['rev_bps_limit']}")
    
    beacon_events_all = []
    events_with_beacons = set()
    
    # Process each event
    for idx, window_row in windows_df.iterrows():
        event_id = idx
        venue = window_row['venue']
        date = window_row['date']
        
        # Load tick data for the day
        start_time = pd.to_datetime(f"{date} 00:00:00")
        end_time = pd.to_datetime(f"{date} 23:59:59")
        
        tick_data, error = load_tick_data_diagnostic(date, venue, start_time, end_time)
        
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
                beacon_events = detect_beacon_events_stress_test(
                    tick_data, round_level, micro_trade_threshold,
                    config['window_s'], config['band_pct'], config['rev_bps_limit']
                )
                
                if beacon_events:
                    events_with_beacons.add(event_id)
                    beacon_events_all.extend(beacon_events)
        
        # Clean up
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
    
    stress_test_results.append({
        'window_s': config['window_s'],
        'band_pct': config['band_pct'],
        'micro_quantile': config['micro_quantile'],
        'rev_bps_limit': config['rev_bps_limit'],
        'events_with_beacons': len(events_with_beacons),
        'total_beacon_events': len(beacon_events_all),
        'median_trades_per_beacon': median_trades,
        'iqr': iqr,
        'zeros_in_event_distribution': zeros_in_event_distribution
    })

# Create stress test results dataframe
stress_test_df = pd.DataFrame(stress_test_results)
stress_test_df.to_csv(DIAGNOSTICS_ROOT / "beacon_stress_test.csv", index=False)

# 4. Find highest-yield configuration
log("\n=== 4. Find highest-yield configuration ===")
highest_yield = stress_test_df.loc[stress_test_df['events_with_beacons'].idxmax()]

# Get top 3 configs by beacon yield
top_3_configs = stress_test_df.nlargest(3, 'events_with_beacons')

# Create summary
beacon_stress_summary = {
    "total_trades_per_venue_date": trade_counts_df['total_trades'].sum(),
    "total_venue_date_combinations": len(trade_counts_df),
    "configurations_tested": len(configurations),
    "highest_yield_config": {
        "window_s": int(highest_yield['window_s']),
        "band_pct": float(highest_yield['band_pct']),
        "micro_quantile": highest_yield['micro_quantile'],
        "rev_bps_limit": int(highest_yield['rev_bps_limit']),
        "events_with_beacons": int(highest_yield['events_with_beacons']),
        "total_beacon_events": int(highest_yield['total_beacon_events']),
        "median_trades_per_beacon": float(highest_yield['median_trades_per_beacon']),
        "iqr": float(highest_yield['iqr']),
        "zeros_in_event_distribution": int(highest_yield['zeros_in_event_distribution'])
    },
    "top_3_configs": [
        {
            "rank": i+1,
            "window_s": int(row['window_s']),
            "band_pct": float(row['band_pct']),
            "micro_quantile": row['micro_quantile'],
            "rev_bps_limit": int(row['rev_bps_limit']),
            "events_with_beacons": int(row['events_with_beacons']),
            "total_beacon_events": int(row['total_beacon_events']),
            "median_trades_per_beacon": float(row['median_trades_per_beacon']),
            "iqr": float(row['iqr']),
            "zeros_in_event_distribution": int(row['zeros_in_event_distribution'])
        }
        for i, (_, row) in enumerate(top_3_configs.iterrows())
    ],
    "memory_peak_MB": float(check_memory())
}

with open(DIAGNOSTICS_ROOT / "beacon_stress_summary.json", "w") as f:
    json.dump(beacon_stress_summary, f, indent=2)

# 5. Final results
log("\n=== 5. Final Results ===")
memory_peak = float(check_memory())

print("\n=== CHECKPOINT PHASE TRIGGER: Beacon Stress-Test Complete ===")
print("Key results:")
print(f"  • Memory peak: {memory_peak:.1f}MB")
print(f"  • Total trades: {trade_counts_df['total_trades'].sum()}")
print(f"  • Configurations tested: {len(configurations)}")
print(f"  • Highest yield: {highest_yield['events_with_beacons']} events with beacons")

# Return required outputs
print("\n=== Required Outputs ===")

print("\n1) Total trades per venue/date:")
for _, row in trade_counts_df.iterrows():
    print(f"  {row['venue']} {row['date']}: {row['total_trades']} trades")

print("\n2) Top 3 configs by beacon yield:")
for i, (_, row) in enumerate(top_3_configs.iterrows()):
    print(f"  #{i+1}: window_s={row['window_s']}, band_pct={row['band_pct']}, micro_quantile={row['micro_quantile']}, rev_bps_limit={row['rev_bps_limit']}")
    print(f"       events_with_beacons={row['events_with_beacons']}, total_beacon_events={row['total_beacon_events']}, iqr={row['iqr']:.1f}")

print("\n3) Recommendation:")
if highest_yield['events_with_beacons'] == 0:
    print("  INVESTIGATE DATA GAP - No beacons found with any configuration")
elif highest_yield['events_with_beacons'] < 10:
    print("  RELAX - Very few beacons found, consider relaxing thresholds")
else:
    print("  RETAIN - Sufficient beacons found with current configuration")

print(f"\n4) Peak RSS: {memory_peak:.1f}MB")

log("✅ CHECKPOINT PHASE TRIGGER: Beacon Stress-Test complete - DIAGNOSTICS COMPLETE")





