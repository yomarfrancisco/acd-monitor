#!/usr/bin/env python3
"""
Compute Event Studies for Stage I1 - Wave-2
"""

import json
import os
import sys
import io
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import boto3

S3_BUCKET = "acd-monitor-snapshots"
DATE = "20251001"

s3 = boto3.client('s3')

def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response['Body'].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")

def load_canonical_data(symbol: str) -> pd.DataFrame:
    """Load canonical data for symbol."""
    symbol_mapping = {
        "BTC-USD": "btc_ticks",
        "ETH-USD": "eth_ticks"
    }
    
    if symbol not in symbol_mapping:
        raise Exception(f"Unknown symbol: {symbol}")
    
    prefix = f"canonical/{DATE}/{symbol_mapping[symbol]}/"
    
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            raise Exception(f"No data found for {symbol}")
        
        dfs = []
        for obj in response['Contents']:
            if obj['Key'].endswith('.parquet'):
                venue_df = read_parquet_s3(obj['Key'])
                dfs.append(venue_df)
        
        if not dfs:
            raise Exception(f"No parquet files found for {symbol}")
        
        return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        raise Exception(f"Failed to load canonical data for {symbol}: {e}")

def load_env_flags(symbol: str) -> pd.DataFrame:
    """Load environment flags for symbol."""
    symbol_lower = symbol.lower().replace('-', '_')
    key = f"data/derived/{symbol_lower}/env_flags_1s.parquet"
    
    try:
        return read_parquet_s3(key)
    except Exception as e:
        raise Exception(f"Failed to load environment flags for {symbol}: {e}")

def identify_events(env_flags: pd.DataFrame) -> Dict[str, List[datetime]]:
    """Identify event timestamps from environment flags."""
    events = {
        "ny_open": [],
        "session_transition": [],
        "vwap_reset": [],
        "return_2sigma_v": []
    }
    
    # Convert timestamp to datetime if needed
    if 'timestamp' in env_flags.columns:
        env_flags['timestamp'] = pd.to_datetime(env_flags['timestamp'], utc=True)
    elif 'ts' in env_flags.columns:
        env_flags['ts'] = pd.to_datetime(env_flags['ts'], utc=True)
        env_flags['timestamp'] = env_flags['ts']
    
    # NY Open events (13:30-13:45 UTC)
    if 'is_ny_open' in env_flags.columns:
        ny_events = env_flags[env_flags['is_ny_open'] == 1]['timestamp'].unique()
        events["ny_open"] = sorted(ny_events)
    
    # Session transition events
    if 'is_session_transition' in env_flags.columns:
        transition_events = env_flags[env_flags['is_session_transition'] == 1]['timestamp'].unique()
        events["session_transition"] = sorted(transition_events)
    
    # VWAP reset events (midnight jumps)
    if 'is_vwap_reset_jump_day' in env_flags.columns:
        vwap_events = env_flags[env_flags['is_vwap_reset_jump_day'] == 1]['timestamp'].unique()
        events["vwap_reset"] = sorted(vwap_events)
    
    # 2-sigma return events (per venue)
    if 'is_return_2sigma_v' in env_flags.columns:
        sigma_events = env_flags[env_flags['is_return_2sigma_v'] == 1]['timestamp'].unique()
        events["return_2sigma_v"] = sorted(sigma_events)
    
    return events

def compute_event_metrics(canonical_df: pd.DataFrame, env_flags_df: pd.DataFrame, 
                         event_time: datetime, event_type: str, venue: str) -> Dict[str, Any]:
    """Compute metrics for a single event."""
    
    # Filter to venue first (more efficient)
    venue_canonical = canonical_df[canonical_df['venue'] == venue].copy()
    venue_env = env_flags_df[env_flags_df['venue'] == venue].copy()
    
    if len(venue_canonical) == 0:
        return {"status": "no_data", "reason": "No canonical data for venue"}
    
    # Convert timestamps only for the filtered data
    if 'timestamp' in venue_canonical.columns:
        venue_canonical['timestamp'] = pd.to_datetime(venue_canonical['timestamp'], utc=True)
    elif 'ts_exchange_ms' in venue_canonical.columns:
        venue_canonical['timestamp'] = pd.to_datetime(venue_canonical['ts_exchange_ms'], unit='ms', utc=True)
    
    if 'timestamp' in venue_env.columns:
        venue_env['timestamp'] = pd.to_datetime(venue_env['timestamp'], utc=True)
    elif 'ts' in venue_env.columns:
        venue_env['ts'] = pd.to_datetime(venue_env['ts'], utc=True)
        venue_env['timestamp'] = venue_env['ts']
    
    # Sort by timestamp for efficient filtering
    venue_canonical = venue_canonical.sort_values('timestamp')
    
    # Define windows (15 minutes = 900 seconds)
    pre_start = event_time - timedelta(minutes=15)
    pre_end = event_time
    post_start = event_time
    post_end = event_time + timedelta(minutes=15)
    
    # Get pre-event data (use boolean indexing for efficiency)
    pre_mask = (venue_canonical['timestamp'] >= pre_start) & (venue_canonical['timestamp'] < pre_end)
    pre_data = venue_canonical[pre_mask].copy()
    
    # Get post-event data
    post_mask = (venue_canonical['timestamp'] >= post_start) & (venue_canonical['timestamp'] < post_end)
    post_data = venue_canonical[post_mask].copy()
    
    if len(pre_data) < 5 or len(post_data) < 5:
        return {"status": "insufficient_data", "reason": "Insufficient pre/post data"}
    
    # Compute mid prices and returns
    pre_data['mid_price'] = (pre_data['best_bid'] + pre_data['best_ask']) / 2.0
    post_data['mid_price'] = (post_data['best_bid'] + post_data['best_ask']) / 2.0
    
    pre_data['returns'] = pre_data['mid_price'].pct_change()
    post_data['returns'] = post_data['mid_price'].pct_change()
    
    # Compute spreads
    pre_data['spread'] = pre_data['best_ask'] - pre_data['best_bid']
    post_data['spread'] = post_data['best_ask'] - post_data['best_bid']
    
    # CAR calculations
    pre_returns = pre_data['returns'].dropna()
    post_returns = post_data['returns'].dropna()
    
    if len(pre_returns) == 0 or len(post_returns) == 0:
        return {"status": "no_returns", "reason": "No valid returns data"}
    
    # CAR 0-60s (first minute)
    post_60s = post_data[post_data['timestamp'] <= event_time + timedelta(seconds=60)]
    car_60s = post_60s['returns'].sum() if len(post_60s) > 0 else 0
    
    # CAR 0-300s (5 minutes)
    post_300s = post_data[post_data['timestamp'] <= event_time + timedelta(seconds=300)]
    car_300s = post_300s['returns'].sum() if len(post_300s) > 0 else 0
    
    # Spread change
    avg_spread_pre = pre_data['spread'].mean()
    avg_spread_post = post_data['spread'].mean()
    d_spread = avg_spread_post - avg_spread_pre
    
    # Volatility change
    vol_pre = pre_returns.std()
    vol_post = post_returns.std()
    d_vol = vol_post / vol_pre if vol_pre > 0 else np.nan
    
    # Hit ratio (sign of first 60s return)
    first_minute_returns = post_60s['returns'].dropna()
    if len(first_minute_returns) > 0:
        hit_60s = (first_minute_returns > 0).mean()
    else:
        hit_60s = np.nan
    
    # Missing data percentage
    total_expected = 30 * 60  # 30 minutes in seconds
    actual_obs = len(pre_data) + len(post_data)
    missing_pct = max(0, (total_expected - actual_obs) / total_expected * 100)
    
    return {
        "status": "success",
        "car_60s": car_60s,
        "car_300s": car_300s,
        "d_spread": d_spread,
        "d_vol": d_vol,
        "hit_60s": hit_60s,
        "missing_pct": missing_pct,
        "n_pre": len(pre_data),
        "n_post": len(post_data)
    }

def compute_events_for_symbol(symbol: str) -> pd.DataFrame:
    """Compute event studies for a symbol."""
    print(f"📊 Computing event studies for {symbol}...")
    
    # Load data
    canonical_df = load_canonical_data(symbol)
    env_flags_df = load_env_flags(symbol)
    
    print(f"  ✅ Loaded {len(canonical_df)} canonical records")
    print(f"  ✅ Loaded {len(env_flags_df)} environment flags")
    
    # Identify events
    events = identify_events(env_flags_df)
    print(f"  📅 Events identified:")
    for event_type, timestamps in events.items():
        print(f"    {event_type}: {len(timestamps)} events")
    
    # Get venues
    venues = canonical_df['venue'].unique()
    print(f"  🏢 Venues: {list(venues)}")
    
    # Limit events to prevent memory issues (take first 50 events per type)
    for event_type in events:
        if len(events[event_type]) > 50:
            events[event_type] = events[event_type][:50]
            print(f"    ⚠️ Limited {event_type} to first 50 events")
    
    # Compute metrics for each venue and event type
    results = []
    total_combinations = len(venues) * len([et for et in events.values() if len(et) > 0])
    processed = 0
    
    for venue in venues:
        print(f"  📈 Processing venue: {venue}")
        
        for event_type, event_times in events.items():
            if len(event_times) == 0:
                continue
            
            print(f"    📊 {event_type}: {len(event_times)} events")
            
            # Compute metrics for each event (limit to first 20 for efficiency)
            venue_events = []
            max_events = min(20, len(event_times))
            
            for i, event_time in enumerate(event_times[:max_events]):
                if i % 5 == 0:  # Progress tracking
                    print(f"      Processing event {i+1}/{max_events}")
                
                metrics = compute_event_metrics(
                    canonical_df, env_flags_df, event_time, event_type, venue
                )
                
                if metrics["status"] == "success":
                    venue_events.append({
                        "event_time": event_time,
                        "metrics": metrics
                    })
            
            # Check if we have enough events
            n_events = len(venue_events)
            n_used = len([e for e in venue_events if e["metrics"]["status"] == "success"])
            
            if n_used < 5:
                print(f"    ⚠️ Insufficient samples: {n_used}/5 required")
                results.append({
                    "symbol": symbol,
                    "venue": venue,
                    "event_type": event_type,
                    "n_events": n_events,
                    "n_used": n_used,
                    "car_60s": np.nan,
                    "car_300s": np.nan,
                    "d_spread": np.nan,
                    "d_vol": np.nan,
                    "hit_60s": np.nan,
                    "status": "insufficient_sample"
                })
                continue
            
            # Aggregate metrics
            successful_events = [e for e in venue_events if e["metrics"]["status"] == "success"]
            
            if len(successful_events) == 0:
                continue
            
            # Calculate averages
            avg_car_60s = np.mean([e["metrics"]["car_60s"] for e in successful_events])
            avg_car_300s = np.mean([e["metrics"]["car_300s"] for e in successful_events])
            avg_d_spread = np.mean([e["metrics"]["d_spread"] for e in successful_events])
            avg_d_vol = np.mean([e["metrics"]["d_vol"] for e in successful_events])
            avg_hit_60s = np.mean([e["metrics"]["hit_60s"] for e in successful_events])
            
            results.append({
                "symbol": symbol,
                "venue": venue,
                "event_type": event_type,
                "n_events": n_events,
                "n_used": n_used,
                "car_60s": avg_car_60s,
                "car_300s": avg_car_300s,
                "d_spread": avg_d_spread,
                "d_vol": avg_d_vol,
                "hit_60s": avg_hit_60s,
                "status": "success"
            })
            
            print(f"    ✅ {event_type}: {n_used} events processed")
        
        processed += 1
        print(f"  📊 Progress: {processed}/{len(venues)} venues completed")
    
    return pd.DataFrame(results)

def save_events(symbol: str, events_df: pd.DataFrame) -> Dict[str, Any]:
    """Save event studies results."""
    symbol_lower = symbol.lower().replace('-', '_')
    key = f"analysis/{DATE}/wave2/events/{symbol_lower}/events.parquet"
    
    # Check if file exists
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        print(f"  ⚠️ File exists: {key} - reusing")
        return {"status": "reused", "key": key}
    except:
        pass
    
    # Save parquet file
    parquet_buffer = io.BytesIO()
    events_df.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=parquet_buffer.getvalue()
    )
    
    print(f"  ✅ Saved: {key}")
    
    # Create manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "rows": len(events_df),
        "columns": list(events_df.columns),
        "checksum": hashlib.sha256(parquet_buffer.getvalue()).hexdigest(),
        "event_stats": {
            "total_venue_event_combinations": len(events_df),
            "successful_combinations": len(events_df[events_df['status'] == 'success']),
            "insufficient_sample": len(events_df[events_df['status'] == 'insufficient_sample']),
            "venues": list(events_df['venue'].unique()),
            "event_types": list(events_df['event_type'].unique())
        }
    }
    
    # Save manifest
    manifest_key = f"analysis/{DATE}/wave2/events/{symbol_lower}/_checks/manifest.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2)
    )
    
    return manifest

def main():
    """Main function."""
    print("🔍 Computing Event Studies for Stage I1...")
    
    symbols = ["BTC-USD", "ETH-USD"]
    results = {}
    
    for symbol in symbols:
        try:
            print(f"\n📊 Processing {symbol}...")
            
            # Check if ETH alignment is sufficient
            if symbol == "ETH-USD":
                # For now, proceed with ETH (exploratory)
                print(f"  📊 {symbol}: exploratory mode")
            
            events_df = compute_events_for_symbol(symbol)
            manifest = save_events(symbol, events_df)
            results[symbol] = manifest
            
        except Exception as e:
            print(f"  ❌ Failed {symbol}: {e}")
            results[symbol] = {"status": "failed", "error": str(e)}
    
    # Print summary
    print(f"\n📊 Event Studies Summary:")
    for symbol, result in results.items():
        if result.get("status") == "reused":
            print(f"  {symbol}: REUSED")
        elif result.get("status") == "failed":
            print(f"  {symbol}: FAILED - {result.get('error')}")
        else:
            stats = result.get("event_stats", {})
            print(f"  {symbol}: {stats.get('successful_combinations', 0)} successful combinations")

if __name__ == "__main__":
    main()
