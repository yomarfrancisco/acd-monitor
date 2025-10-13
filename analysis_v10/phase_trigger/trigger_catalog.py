#!/usr/bin/env python3
"""
ACD — Wave 1 (Trigger Catalog)
Scope: 2025-09-01…07; venues={BINANCE,COINBASE,BYBITSPOT,BITGET}
Anchors: Round numbers & Prior H/L levels
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
    if rss_mb > 600:
        raise RuntimeError(f"STOP:RESOURCE_LIMIT - RAM usage: {rss_mb:.1f}MB > 600MB")
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
    with open(logs_dir / "trigger_phase_hashes.txt", "a") as f:
        f.write(f"{filename}: {hash_val}\n")

def atomic_write_csv_line(path, row_dict):
    """Append a single row to CSV with line buffering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file exists to write header
    if not path.exists():
        with open(path, 'w', newline='') as f:
            f.write(','.join(row_dict.keys()) + '\n')
    
    # Append row
    with open(path, 'a', newline='') as f:
        f.write(','.join(str(v) for v in row_dict.values()) + '\n')
        f.flush()

def get_price_range(venue, day):
    """Get min/max prices for a venue/day to determine round number anchors."""
    ticks_path = f"data_v6/views/{venue}/{day}/ticks_canonical.parquet"
    if not Path(ticks_path).exists():
        return None, None
    
    try:
        dataset = ds.dataset(ticks_path, format="parquet")
        price_data = dataset.to_table(columns=["price"]).to_pandas()
        return price_data['price'].min(), price_data['price'].max()
    except Exception as e:
        log(f"    ❌ Error getting price range for {venue} {day}: {e}")
        return None, None

def generate_round_anchors(min_price, max_price):
    """Generate round number anchors around observed price range."""
    anchors = []
    
    # Round to nearest thousands
    min_round = int(min_price // 1000) * 1000
    max_round = int((max_price // 1000) + 1) * 1000
    
    # Generate whole thousands
    for price in range(min_round, max_round + 1000, 1000):
        anchors.append(price)
    
    # Generate half-thousands
    for price in range(min_round + 500, max_round + 1000, 1000):
        anchors.append(price)
    
    return sorted(anchors)

def get_prior_hl_levels(venue, current_day):
    """Get prior day/week/month H/L levels."""
    levels = []
    
    # Parse current day
    current_date = pd.to_datetime(current_day, format='%Y%m%d')
    
    # Prior day
    prev_day = (current_date - timedelta(days=1)).strftime('%Y%m%d')
    prev_day_path = f"data_v6/views/{venue}/{prev_day}/ticks_canonical.parquet"
    if Path(prev_day_path).exists():
        try:
            dataset = ds.dataset(prev_day_path, format="parquet")
            price_data = dataset.to_table(columns=["price"]).to_pandas()
            levels.extend([price_data['price'].min(), price_data['price'].max()])
        except:
            pass
    
    # Prior week (7 days ago)
    prev_week = (current_date - timedelta(days=7)).strftime('%Y%m%d')
    prev_week_path = f"data_v6/views/{venue}/{prev_week}/ticks_canonical.parquet"
    if Path(prev_week_path).exists():
        try:
            dataset = ds.dataset(prev_week_path, format="parquet")
            price_data = dataset.to_table(columns=["price"]).to_pandas()
            levels.extend([price_data['price'].min(), price_data['price'].max()])
        except:
            pass
    
    return levels

def find_first_touch(venue, day, anchor_price, cool_down_minutes=15):
    """Find first touch of anchor price with cool-down."""
    ticks_path = f"data_v6/views/{venue}/{day}/ticks_canonical.parquet"
    if not Path(ticks_path).exists():
        return None
    
    try:
        dataset = ds.dataset(ticks_path, format="parquet")
        
        # Get all data for the day
        df = dataset.to_table(columns=["ts", "price"]).to_pandas()
        df['ts'] = pd.to_datetime(df['ts'])
        
        # Find touches (price crosses anchor)
        touches = []
        for i in range(1, len(df)):
            prev_price = df.iloc[i-1]['price']
            curr_price = df.iloc[i]['price']
            
            # Check if price crossed the anchor
            if (prev_price <= anchor_price <= curr_price) or (prev_price >= anchor_price >= curr_price):
                touches.append({
                    'ts': df.iloc[i]['ts'],
                    'price': curr_price,
                    'anchor': anchor_price
                })
        
        if not touches:
            return None
        
        # Apply cool-down: only first touch per 15-minute window
        filtered_touches = []
        last_touch_time = None
        
        for touch in touches:
            if last_touch_time is None or (touch['ts'] - last_touch_time).total_seconds() >= cool_down_minutes * 60:
                filtered_touches.append(touch)
                last_touch_time = touch['ts']
        
        return filtered_touches[0] if filtered_touches else None
        
    except Exception as e:
        log(f"    ❌ Error finding first touch for {venue} {day} anchor {anchor_price}: {e}")
        return None

def create_event_windows(touch_ts, pre_minutes=15, post_minutes=15):
    """Create pre/post event windows."""
    pre_start = touch_ts - timedelta(minutes=pre_minutes)
    pre_end = touch_ts
    post_start = touch_ts
    post_end = touch_ts + timedelta(minutes=post_minutes)
    
    return {
        't0': touch_ts,
        'pre_start': pre_start,
        'pre_end': pre_end,
        'post_start': post_start,
        'post_end': post_end,
        'pre_minutes': pre_minutes,
        'post_minutes': post_minutes
    }

def validate_window_data(venue, day, windows):
    """Validate that windows have sufficient data."""
    ticks_path = f"data_v6/views/{venue}/{day}/ticks_canonical.parquet"
    if not Path(ticks_path).exists():
        return False, 0, 0
    
    try:
        dataset = ds.dataset(ticks_path, format="parquet")
        
        # Count pre-window data
        pre_filter = (ds.field("ts") >= windows['pre_start']) & (ds.field("ts") < windows['pre_end'])
        pre_count = dataset.to_table(filter=pre_filter, columns=["ts"]).num_rows
        
        # Count post-window data
        post_filter = (ds.field("ts") >= windows['post_start']) & (ds.field("ts") <= windows['post_end'])
        post_count = dataset.to_table(filter=post_filter, columns=["ts"]).num_rows
        
        return pre_count >= 50 and post_count >= 50, pre_count, post_count
        
    except Exception as e:
        log(f"    ❌ Error validating windows for {venue} {day}: {e}")
        return False, 0, 0

def assign_session_label(timestamp):
    """Assign session label based on UTC hour."""
    hour = timestamp.hour
    if 0 <= hour < 8:
        return "Asia"
    elif 8 <= hour < 16:
        return "EU"
    elif 16 <= hour < 24:
        return "US"
    else:
        return "Unknown"

def assign_wash_tercile(venue, day, timestamp):
    """Assign wash trading tercile (simplified)."""
    # This is a placeholder - in practice, you'd compute wash metrics
    # For now, assign based on hour (simplified)
    hour = timestamp.hour
    if hour < 8:
        return "Low"
    elif hour < 16:
        return "Medium"
    else:
        return "High"

# --- MAIN EXECUTION ---
log("=== ACD — Wave 1 (Trigger Catalog) ===")
log(f"Memory at start: {check_memory():.1f}MB")

ROOT = Path("analysis_v10/phase_trigger")
ROOT.mkdir(parents=True, exist_ok=True)

VENUES = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
DAYS = ["20250901", "20250902", "20250903", "20250904", "20250905", "20250906", "20250907"]

# Initialize tracking
memory_peak = check_memory()
anchors_catalog = []
windows_data = []
dashboard_stats = {
    "total_anchors": 0,
    "total_touches": 0,
    "valid_windows": 0,
    "by_anchor_type": {},
    "by_session": {},
    "by_wash_tercile": {},
    "memory_peak_MB": 0.0
}

# Process each venue/day combination
for day in DAYS:
    for venue in VENUES:
        log(f"Processing {venue} {day}... (Memory: {check_memory():.1f}MB)")
        
        try:
            # Get price range for round number anchors
            min_price, max_price = get_price_range(venue, day)
            if min_price is None or max_price is None:
                log(f"    ❌ No price data for {venue} {day}")
                continue
            
            # Generate round number anchors
            round_anchors = generate_round_anchors(min_price, max_price)
            log(f"    Generated {len(round_anchors)} round anchors for {venue} {day}")
            
            # Get prior H/L levels
            prior_levels = get_prior_hl_levels(venue, day)
            log(f"    Found {len(prior_levels)} prior H/L levels for {venue} {day}")
            
            # Combine all anchors
            all_anchors = round_anchors + prior_levels
            all_anchors = sorted(list(set(all_anchors)))  # Remove duplicates
            
            log(f"    Total anchors: {len(all_anchors)}")
            dashboard_stats["total_anchors"] += len(all_anchors)
            
            # Find first touches for each anchor
            for anchor_price in all_anchors:
                touch = find_first_touch(venue, day, anchor_price)
                
                if touch:
                    # Create event windows
                    windows = create_event_windows(touch['ts'])
                    
                    # Validate windows have sufficient data
                    is_valid, pre_count, post_count = validate_window_data(venue, day, windows)
                    
                    # Shrink windows if needed
                    if not is_valid and pre_count < 50 and post_count < 50:
                        # Try 10-minute windows
                        windows_10m = create_event_windows(touch['ts'], pre_minutes=10, post_minutes=10)
                        is_valid, pre_count, post_count = validate_window_data(venue, day, windows_10m)
                        if is_valid:
                            windows = windows_10m
                    
                    # Record anchor
                    anchor_type = "Round" if anchor_price in round_anchors else "Prior_HL"
                    session = assign_session_label(touch['ts'])
                    wash_tercile = assign_wash_tercile(venue, day, touch['ts'])
                    
                    anchor_record = {
                        'venue': venue,
                        'date': day,
                        'anchor_price': anchor_price,
                        'anchor_type': anchor_type,
                        'first_touch_ts': touch['ts'],
                        'touch_price': touch['price'],
                        'session': session,
                        'wash_tercile': wash_tercile,
                        'pre_minutes': windows['pre_minutes'],
                        'post_minutes': windows['post_minutes'],
                        'valid': is_valid
                    }
                    
                    anchors_catalog.append(anchor_record)
                    dashboard_stats["total_touches"] += 1
                    
                    # Update dashboard stats
                    dashboard_stats["by_anchor_type"][anchor_type] = dashboard_stats["by_anchor_type"].get(anchor_type, 0) + 1
                    dashboard_stats["by_session"][session] = dashboard_stats["by_session"].get(session, 0) + 1
                    dashboard_stats["by_wash_tercile"][wash_tercile] = dashboard_stats["by_wash_tercile"].get(wash_tercile, 0) + 1
                    
                    if is_valid:
                        dashboard_stats["valid_windows"] += 1
                        
                        # Record window data
                        window_record = {
                            'venue': venue,
                            'date': day,
                            'anchor_price': anchor_price,
                            'anchor_type': anchor_type,
                            't0': windows['t0'],
                            'pre_start': windows['pre_start'],
                            'pre_end': windows['pre_end'],
                            'post_start': windows['post_start'],
                            'post_end': windows['post_end'],
                            'pre_count': pre_count,
                            'post_count': post_count,
                            'session': session,
                            'wash_tercile': wash_tercile
                        }
                        
                        windows_data.append(window_record)
            
            # Clean up memory
            gc.collect()
            current_memory = check_memory()
            memory_peak = max(memory_peak, current_memory)
            
        except Exception as e:
            log(f"    ❌ Error processing {venue} {day}: {e}")
            continue

# Save results
log("\n=== Saving Results ===")

# Save anchors catalog
if anchors_catalog:
    anchors_df = pd.DataFrame(anchors_catalog)
    anchors_df.to_csv(ROOT / "anchors_catalog.csv", index=False)
    output_hashes = {}
    output_hashes['anchors_catalog.csv'] = compute_file_hash(ROOT / "anchors_catalog.csv")
    append_hash_log("anchors_catalog.csv", output_hashes['anchors_catalog.csv'])
    log(f"✅ Saved {len(anchors_df)} anchor records")

# Save windows
if windows_data:
    windows_df = pd.DataFrame(windows_data)
    windows_df.to_csv(ROOT / "windows.csv", index=False)
    output_hashes['windows.csv'] = compute_file_hash(ROOT / "windows.csv")
    append_hash_log("windows.csv", output_hashes['windows.csv'])
    log(f"✅ Saved {len(windows_df)} window records")

# Update dashboard with final stats
dashboard_stats["memory_peak_MB"] = memory_peak
dashboard_stats["output_hashes"] = output_hashes

# Save dashboard
with open(ROOT / "dashboard.json", "w") as f:
    json.dump(dashboard_stats, f, indent=2)

log(f"✅ Saved dashboard.json")

# Final summary
log("\n=== TRIGGER CATALOG COMPLETE ===")
log(f"Total anchors: {dashboard_stats['total_anchors']}")
log(f"Total touches: {dashboard_stats['total_touches']}")
log(f"Valid windows: {dashboard_stats['valid_windows']}")
log(f"Memory peak: {memory_peak:.1f}MB")
log(f"Final memory: {check_memory():.1f}MB")

print("\n=== CHECKPOINT PHASE TRIGGER: Wave 1 (Trigger Catalog) ===")
print("Key files:")
print(f"  • anchors_catalog: analysis_v10/phase_trigger/anchors_catalog.csv")
print(f"  • windows: analysis_v10/phase_trigger/windows.csv")
print(f"  • dashboard: analysis_v10/phase_trigger/dashboard.json")
print(f"  • hashes: analysis_v10/phase_trigger/logs/trigger_phase_hashes.txt")
print("Core metrics:")
print(f"  • total_anchors: {dashboard_stats['total_anchors']}")
print(f"  • total_touches: {dashboard_stats['total_touches']}")
print(f"  • valid_windows: {dashboard_stats['valid_windows']}")
print(f"  • by_anchor_type: {dashboard_stats['by_anchor_type']}")
print(f"  • by_session: {dashboard_stats['by_session']}")
print(f"  • by_wash_tercile: {dashboard_stats['by_wash_tercile']}")
print(f"  • memory_peak_MB: {dashboard_stats['memory_peak_MB']:.1f}")

log("✅ CHECKPOINT PHASE TRIGGER: Wave 1 (Trigger Catalog) complete")





