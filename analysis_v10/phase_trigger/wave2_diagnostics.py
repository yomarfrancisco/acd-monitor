#!/usr/bin/env python3
"""
Wave 2: Diagnostics Only
Check data availability and provide summary without full processing.
"""

import os, json, gc, numpy as np, pandas as pd
from pathlib import Path
import psutil
import hashlib
from datetime import datetime, timedelta
import pyarrow.dataset as ds
import pyarrow.parquet as pq

def log(m): print(m, flush=True)

def check_memory():
    rss_mb = psutil.Process().memory_info().rss / (1024**2)
    return rss_mb

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

# --- MAIN EXECUTION ---
log("=== Wave 2: Diagnostics Only ===")
log(f"Memory at start: {check_memory():.1f}MB")

ROOT = Path("analysis_v10/phase_trigger")
ROOT.mkdir(parents=True, exist_ok=True)

# Load windows data
windows_df = pd.read_csv(ROOT / "windows.csv")
log(f"Loaded {len(windows_df)} event windows")

# Check data availability
days = windows_df['date'].unique()
venues = windows_df['venue'].unique()

log(f"Days: {sorted(days)}")
log(f"Venues: {sorted(venues)}")

# Check aligned data availability
aligned_data_status = {}
for day in days:
    aligned_path = f"analysis_v7/icp_{day}_5s/aligned_5s.parquet"
    exists = Path(aligned_path).exists()
    aligned_data_status[day] = exists
    log(f"Aligned data for {day}: {'✅' if exists else '❌'}")

# Sample a few events to check data structure
log("\n=== Sample Event Analysis ===")
sample_events = windows_df.head(3)

for idx, event in sample_events.iterrows():
    log(f"Event {idx}: {event['venue']} {event['date']} {event['anchor_type']}")
    
    # Check if aligned data exists
    aligned_path = f"analysis_v7/icp_{event['date']}_5s/aligned_5s.parquet"
    if Path(aligned_path).exists():
        try:
            # Load just the schema
            dataset = ds.dataset(aligned_path, format="parquet")
            schema = dataset.schema
            log(f"  Schema: {list(schema.names)}")
            
            # Check row count
            row_count = dataset.count_rows()
            log(f"  Row count: {row_count:,}")
            
            # Check memory usage for a small sample
            sample_df = dataset.to_table(columns=['ts', 'venue_i', 'venue_j']).slice(0, 1000).to_pandas()
            log(f"  Sample memory: {sample_df.memory_usage(deep=True).sum() / 1024**2:.1f}MB for 1000 rows")
            
        except Exception as e:
            log(f"  ❌ Error reading aligned data: {e}")
    else:
        log(f"  ❌ Aligned data missing: {aligned_path}")

# Create diagnostic dashboard
dashboard = {
    "N_events": int(len(windows_df)),
    "days_available": int(len([d for d in days if aligned_data_status.get(d, False)])),
    "total_days": int(len(days)),
    "venues": [str(v) for v in venues],
    "data_availability": {str(k): v for k, v in aligned_data_status.items()},
    "memory_peak_MB": float(check_memory()),
    "diagnostic_only": True,
    "recommendation": "Data available but memory constraints prevent full processing. Consider processing in smaller batches or using streaming approaches."
}

# Save dashboard
with open(ROOT / "dashboard.json", "w") as f:
    json.dump(dashboard, f, indent=2)

# Compute and save hashes
output_hashes = {}
output_hashes['dashboard.json'] = compute_file_hash(ROOT / "dashboard.json")

for filename, hash_val in output_hashes.items():
    append_hash_log(filename, hash_val)

# Final summary
log("\n=== Wave 2 Diagnostics Complete ===")
log(f"Total events: {len(windows_df)}")
log(f"Days with data: {dashboard['days_available']}/{dashboard['total_days']}")
log(f"Memory peak: {dashboard['memory_peak_MB']:.1f}MB")
log(f"Final memory: {check_memory():.1f}MB")

print("\n=== CHECKPOINT PHASE TRIGGER: Wave 2 (Diagnostics Only) ===")
print("Key files:")
print(f"  • dashboard: analysis_v10/phase_trigger/dashboard.json")
print(f"  • hashes: analysis_v10/phase_trigger/logs/wave2_hashes.txt")
print("Core metrics:")
print(f"  • N_events: {dashboard['N_events']}")
print(f"  • days_available: {dashboard['days_available']}")
print(f"  • total_days: {dashboard['total_days']}")
print(f"  • memory_peak_MB: {dashboard['memory_peak_MB']:.1f}")
print(f"  • recommendation: {dashboard['recommendation']}")

log("❌ CHECKPOINT PHASE TRIGGER: Wave 2 complete - DIAGNOSTICS ONLY")
log("Memory constraints prevent full processing. Consider alternative approaches.")
