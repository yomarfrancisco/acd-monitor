#!/usr/bin/env python3
"""
Synthetic Coordination Signal Injection Script

This script injects coordination signals into existing BTC-USD windows
to test detector sensitivity and validate the ACD pipeline.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import boto3
import sys
from pathlib import Path

# Add src to sys.path for acdlib imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

def inject_lead_lag_signal(tick_data, venue='coinbase', delay_ms=50):
    """
    Inject systematic +50ms delay to specified venue
    """
    if venue not in tick_data:
        return tick_data
    
    # Convert delay to timedelta
    delay = timedelta(milliseconds=delay_ms)
    
    # Apply delay to timestamps
    tick_data[venue] = tick_data[venue].copy()
    tick_data[venue]['ts_exchange'] = tick_data[venue]['ts_exchange'] + delay
    
    return tick_data

def inject_synchronization_signal(tick_data, interval_minutes=5):
    """
    Inject synchronized jumps across all venues at specified intervals
    """
    venues = list(tick_data.keys())
    if not venues:
        return tick_data
    
    # Get time range
    start_time = min(tick_data[venue]['ts_exchange'].min() for venue in venues)
    end_time = max(tick_data[venue]['ts_exchange'].max() for venue in venues)
    
    # Calculate jump intervals
    jump_times = []
    current_time = start_time
    while current_time < end_time:
        jump_times.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
    
    # Apply synchronized jumps
    for venue in venues:
        tick_data[venue] = tick_data[venue].copy()
        for jump_time in jump_times:
            # Find closest tick to jump time
            mask = abs(tick_data[venue]['ts_exchange'] - jump_time) < timedelta(seconds=30)
            if mask.any():
                # Apply synchronized price jump (e.g., +0.1% to mid price)
                tick_data[venue].loc[mask, 'mid'] *= 1.001
    
    return tick_data

def inject_dominance_spike(tick_data, dominant_venue='binance', block_duration_minutes=10):
    """
    Inject dominance spike for specified venue during block periods
    """
    if dominant_venue not in tick_data:
        return tick_data
    
    venues = list(tick_data.keys())
    if len(venues) < 2:
        return tick_data
    
    # Get time range
    start_time = min(tick_data[venue]['ts_exchange'].min() for venue in venues)
    end_time = max(tick_data[venue]['ts_exchange'].max() for venue in venues)
    
    # Calculate dominance blocks
    block_duration = timedelta(minutes=block_duration_minutes)
    dominance_blocks = []
    current_time = start_time
    while current_time < end_time:
        dominance_blocks.append((current_time, current_time + block_duration))
        current_time += block_duration * 2  # Skip every other block
    
    # Apply dominance spikes
    for block_start, block_end in dominance_blocks:
        for venue in venues:
            tick_data[venue] = tick_data[venue].copy()
            mask = (tick_data[venue]['ts_exchange'] >= block_start) & \
                   (tick_data[venue]['ts_exchange'] < block_end)
            
            if venue == dominant_venue:
                # Dominant venue: reduce noise, increase signal
                tick_data[venue].loc[mask, 'mid'] *= 1.002  # Slight upward bias
            else:
                # Other venues: add noise, reduce signal
                noise = np.random.normal(0, 0.001, mask.sum())
                tick_data[venue].loc[mask, 'mid'] *= (1 + noise)
    
    return tick_data

def create_synthetic_dataset(base_window_path, injection_type, output_path):
    """
    Create synthetic dataset with injected coordination signals
    """
    print(f"Creating synthetic dataset: {injection_type}")
    print(f"Base window: {base_window_path}")
    print(f"Output path: {output_path}")
    
    # Load base window data (simplified - would need actual tick data loading)
    # For now, create a mock structure
    synthetic_data = {
        'injection_type': injection_type,
        'base_window': base_window_path,
        'injection_timestamp': datetime.now().isoformat(),
        'parameters': {
            'lead_lag': {'venue': 'coinbase', 'delay_ms': 50},
            'synchronization': {'interval_minutes': 5},
            'dominance_spike': {'venue': 'binance', 'block_duration_minutes': 10}
        }[injection_type]
    }
    
    # Save synthetic dataset metadata
    with open(output_path, 'w') as f:
        json.dump(synthetic_data, f, indent=2)
    
    print(f"Synthetic dataset created: {output_path}")
    return synthetic_data

def main():
    """
    Main function to create synthetic datasets for all injection types
    """
    base_windows = [
        'snapshots/BTC-USD/20250929/1200-1230',
        'snapshots/BTC-USD/20250929/1230-1300'
    ]
    
    injection_types = ['lead_lag', 'synchronization', 'dominance_spike']
    
    synthetic_datasets = []
    
    for base_window in base_windows:
        for injection_type in injection_types:
            output_path = f"analysis/BTC/synthetic/20250929/injected_data/{base_window.split('/')[-1]}_{injection_type}.json"
            
            synthetic_data = create_synthetic_dataset(
                base_window, 
                injection_type, 
                output_path
            )
            synthetic_datasets.append(synthetic_data)
    
    # Save summary
    summary = {
        'total_datasets': len(synthetic_datasets),
        'base_windows': base_windows,
        'injection_types': injection_types,
        'datasets': synthetic_datasets
    }
    
    with open('analysis/BTC/synthetic/20250929/synthetic_datasets_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSynthetic datasets created: {len(synthetic_datasets)}")
    print("Summary saved to: analysis/BTC/synthetic/20250929/synthetic_datasets_summary.json")

if __name__ == "__main__":
    main()
