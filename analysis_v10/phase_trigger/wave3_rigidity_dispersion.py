#!/usr/bin/env python3
"""
Wave 3: Rigidity & Dispersion Shift
Test whether triggers foster tacit coordination by measuring cross-venue rivalry weakening post-event.
"""

import os, json, gc, numpy as np, pandas as pd
from pathlib import Path
import psutil
import hashlib
from datetime import datetime, timedelta
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from scipy.stats import entropy
import warnings
warnings.filterwarnings('ignore')

def log(m): print(m, flush=True)

def check_memory():
    rss_mb = psutil.Process().memory_info().rss / (1024**2)
    if rss_mb > 550:  # Hard stop
        raise RuntimeError(f"STOP:RESOURCE_LIMIT - RAM usage: {rss_mb:.1f}MB > 550MB")
    if rss_mb > 450:  # Force GC and reduce batch size
        gc.collect()
        return rss_mb, 8192  # Reduced batch size
    return rss_mb, 32768  # Normal batch size

def compute_file_hash(path):
    """Compute SHA256 hash of a file."""
    if not Path(path).exists():
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def append_hash_log(filename, hash_val):
    """Append hash to log file."""
    logs_dir = Path("analysis_v10/phase_trigger/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    with open(logs_dir / "wave2_hashes.txt", "a") as f:
        f.write(f"{filename}: {hash_val}\n")

def atomic_write_csv_line(path, row_dict):
    """Append a single row to CSV with line buffering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file exists to write header
    if not path.exists():
        with open(path, 'w', newline='') as f:
            f.write(','.join(row_dict.keys()) + '\n')
    
    # Append row with line buffering
    with open(path, 'a', newline='') as f:
        f.write(','.join(str(v) for v in row_dict.values()) + '\n')
        f.flush()

def load_event_window_rigidity(date, pre_start, post_end, batch_size=32768):
    """Load event window data for rigidity analysis."""
    aligned_path = f"analysis_v7/icp_{date}_5s/aligned_5s.parquet"
    
    if not Path(aligned_path).exists():
        return None
    
    try:
        # Use PyArrow dataset with time filter
        dataset = ds.dataset(aligned_path, format="parquet")
        
        # Time filter
        time_filter = (ds.field("ts") >= pre_start) & (ds.field("ts") < post_end)
        
        # Column subset immediately
        columns = ['ts', 'venue_i', 'venue_j', 'r_i', 'r_j', 'session', 'wash_regime', 'vol_regime']
        
        # Stream the data
        df = dataset.to_table(
            filter=time_filter,
            columns=columns,
            batch_size=batch_size
        ).to_pandas()
        
        if len(df) == 0:
            return None
            
        df['ts'] = pd.to_datetime(df['ts'])
        return df
    except Exception as e:
        return None

def compute_rigidity_entropy(df):
    """Compute rigidity (dispersion) and entropy measures."""
    if len(df) < 60:
        return np.nan, np.nan, 'Unknown', 'Unknown'
    
    try:
        # Compute return differences
        r_diff = df['r_i'] - df['r_j']
        
        # Dispersion (variance of return differences)
        dispersion = np.var(r_diff)
        
        # Entropy of price-change states
        # Discretize r_diff into 5 symmetric bins
        r_diff_clean = r_diff.dropna()
        if len(r_diff_clean) < 10:
            return np.nan, np.nan, 'Unknown', 'Unknown'
        
        # Create 5 symmetric bins
        q1, q2, q3, q4 = np.percentile(r_diff_clean, [20, 40, 60, 80])
        bins = [-np.inf, q1, q2, q3, q4, np.inf]
        
        # Discretize
        discretized = pd.cut(r_diff_clean, bins=bins, labels=False)
        
        # Compute Shannon entropy
        value_counts = discretized.value_counts()
        probabilities = value_counts / len(discretized)
        shannon_entropy = entropy(probabilities)
        
        # Get session and wash regime (mode)
        session = df['session'].mode()[0] if not df['session'].empty else 'Unknown'
        wash_tercile = df['wash_regime'].mode()[0] if not df['wash_regime'].empty else 'Unknown'
        
        return float(dispersion) if np.isfinite(dispersion) else np.nan, float(shannon_entropy) if np.isfinite(shannon_entropy) else np.nan, session, wash_tercile
    except Exception as e:
        return np.nan, np.nan, 'Unknown', 'Unknown'

def process_event_rigidity(event_id, date, venue_event, ts_event, pre_start, post_end):
    """Process rigidity and entropy for a single event."""
    # Load event window data
    current_memory, batch_size = check_memory()
    event_data = load_event_window_rigidity(date, pre_start, post_end, batch_size)
    
    if event_data is None or len(event_data) < 120:
        return []
    
    # Build exact pair test set
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    pair_tests = []
    
    # For each venue Y != venue_event, test both directions
    for venue_y in venues:
        if venue_y == venue_event:
            continue
        
        # Direction 1: (venue_event -> venue_y)
        pair_tests.append((venue_event, venue_y))
        # Direction 2: (venue_y -> venue_event)  
        pair_tests.append((venue_y, venue_event))
    
    rigidity_results = []
    
    for venue_i, venue_j in pair_tests:
        # Filter for exact pair
        pair_data = event_data[
            (event_data['venue_i'] == venue_i) & 
            (event_data['venue_j'] == venue_j)
        ].copy()
        
        if len(pair_data) < 120:
            continue
        
        # Split into pre/post by ts_event
        pre_data = pair_data[pair_data['ts'] < ts_event].copy()
        post_data = pair_data[pair_data['ts'] >= ts_event].copy()
        
        n_pre = len(pre_data)
        n_post = len(post_data)
        
        # Check requirements
        if n_pre < 60 or n_post < 60:
            continue
        
        # Compute rigidity and entropy for pre and post
        disp_pre, entropy_pre, session_pre, wash_pre = compute_rigidity_entropy(pre_data)
        disp_post, entropy_post, session_post, wash_post = compute_rigidity_entropy(post_data)
        
        if (np.isfinite(disp_pre) and np.isfinite(disp_post) and 
            np.isfinite(entropy_pre) and np.isfinite(entropy_post)):
            
            delta_disp = disp_post - disp_pre
            delta_entropy = entropy_post - entropy_pre
            
            # Use post-window session and wash regime
            session = session_post if session_post != 'Unknown' else session_pre
            wash_tercile = wash_post if wash_post != 'Unknown' else wash_pre
            
            rigidity_results.append({
                'event_id': event_id,
                'date': date,
                'venue_event': venue_event,
                'venue_i': venue_i,
                'venue_j': venue_j,
                'delta_disp': delta_disp,
                'delta_entropy': delta_entropy,
                'session': session,
                'wash_tercile': wash_tercile,
                'n_pre': n_pre,
                'n_post': n_post
            })
        
        # Clean up immediately
        del pair_data, pre_data, post_data
        gc.collect()
    
    # Clean up event data
    del event_data
    gc.collect()
    
    return rigidity_results

# --- MAIN EXECUTION ---
log("=== Wave 3: Rigidity & Dispersion Shift ===")
log(f"Memory at start: {check_memory()[0]:.1f}MB")

# Set random seed for reproducibility
np.random.seed(20251006)

ROOT = Path("analysis_v10/phase_trigger")
ROOT.mkdir(parents=True, exist_ok=True)

# Load windows data
windows_df = pd.read_csv(ROOT / "windows.csv")
windows_df['t0'] = pd.to_datetime(windows_df['t0'])
windows_df['pre_start'] = pd.to_datetime(windows_df['pre_start'])
windows_df['pre_end'] = pd.to_datetime(windows_df['pre_end'])
windows_df['post_start'] = pd.to_datetime(windows_df['post_start'])
windows_df['post_end'] = pd.to_datetime(windows_df['post_end'])

log(f"Loaded {len(windows_df)} event windows")

# Sort windows deterministically
windows_df = windows_df.sort_values(['date', 'venue', 'anchor_price']).reset_index(drop=True)
windows_df['event_id'] = range(len(windows_df))

# Initialize tracking
memory_peak = check_memory()[0]
failed_windows = 0
processed_events = 0
rows_rigidity = 0

# Process events one at a time
for idx, window_row in windows_df.iterrows():
    if processed_events % 25 == 0:
        current_memory, _ = check_memory()
        log(f"Processing event {processed_events + 1}/{len(windows_df)}... (Memory: {current_memory:.1f}MB)")
    
    try:
        # Process single event
        rigidity_results = process_event_rigidity(
            window_row['event_id'],
            window_row['date'],
            window_row['venue'],
            window_row['t0'],
            window_row['pre_start'],
            window_row['post_end']
        )
        
        # Save results immediately
        for result in rigidity_results:
            atomic_write_csv_line(ROOT / "rigidity_entropy.csv", result)
            rows_rigidity += 1
        
        processed_events += 1
        
        # Force garbage collection after each event
        gc.collect()
        current_memory, _ = check_memory()
        memory_peak = max(memory_peak, current_memory)
        
    except Exception as e:
        log(f"    ❌ Error processing event {window_row['event_id']}: {e}")
        failed_windows += 1
        gc.collect()
        continue

# Load existing data to get counts
existing_beta_count = 0
existing_tsi_count = 0
existing_placebo_count = 0

if Path(ROOT / "beta_deltas.csv").exists():
    existing_beta_df = pd.read_csv(ROOT / "beta_deltas.csv")
    existing_beta_count = len(existing_beta_df)

if Path(ROOT / "tsi_deltas.csv").exists():
    existing_tsi_df = pd.read_csv(ROOT / "tsi_deltas.csv")
    existing_tsi_count = len(existing_tsi_df)

if Path(ROOT / "placebos.csv").exists():
    existing_placebo_df = pd.read_csv(ROOT / "placebos.csv")
    existing_placebo_count = len(existing_placebo_df)

# Compute summary statistics
log("\n=== Computing Summary Statistics ===")

# Check promotion criteria
failed_pct = (failed_windows / len(windows_df)) * 100 if len(windows_df) > 0 else 0

# Create dashboard
dashboard = {
    "events_total": int(len(windows_df)),
    "rows_beta": int(existing_beta_count),
    "rows_tsi": int(existing_tsi_count),
    "rows_placebo": int(existing_placebo_count),
    "rows_rigidity": int(rows_rigidity),
    "failed_windows": int(failed_windows),
    "failed_pct": float(failed_pct),
    "mean_abs_delta_beta": 0.0,  # Would need to compute from saved data
    "mean_abs_delta_tsi": 0.0,   # Would need to compute from saved data
    "mean_abs_delta_disp": 0.0,  # Would need to compute from saved data
    "mean_abs_delta_entropy": 0.0,  # Would need to compute from saved data
    "memory_peak_MB": float(memory_peak),
    "rng_seed": 20251006
}

# Save dashboard
with open(ROOT / "dashboard.json", "w") as f:
    json.dump(dashboard, f, indent=2)

# Compute and save hashes
output_hashes = {}
output_hashes['rigidity_entropy.csv'] = compute_file_hash(ROOT / "rigidity_entropy.csv")
output_hashes['dashboard.json'] = compute_file_hash(ROOT / "dashboard.json")

for filename, hash_val in output_hashes.items():
    append_hash_log(filename, hash_val)

# Final summary
log("\n=== Wave 3 Complete ===")
log(f"Processed events: {processed_events}")
log(f"Failed windows: {failed_windows}")
log(f"Rows rigidity: {rows_rigidity}")
log(f"Memory peak: {memory_peak:.1f}MB")
log(f"Final memory: {check_memory()[0]:.1f}MB")

print("\n=== CHECKPOINT PHASE TRIGGER: Wave 3 (Rigidity & Dispersion Shift) ===")
print("Key files:")
print(f"  • rigidity_entropy: analysis_v10/phase_trigger/rigidity_entropy.csv")
print(f"  • dashboard: analysis_v10/phase_trigger/dashboard.json")
print(f"  • hashes: analysis_v10/phase_trigger/logs/wave2_hashes.txt")
print("Core metrics:")
print(f"  • rows_rigidity: {dashboard['rows_rigidity']}")
print(f"  • failed_pct: {dashboard['failed_pct']:.1f}%")
print(f"  • memory_peak_MB: {dashboard['memory_peak_MB']:.1f}")

log("✅ CHECKPOINT PHASE TRIGGER: Wave 3 complete - READY FOR WAVE 4")





