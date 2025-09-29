#!/usr/bin/env python3
"""
Create mock parquet data for baseline testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def create_mock_tick_data(start_time: str, end_time: str, venue: str) -> pd.DataFrame:
    """Create mock tick data for a venue."""
    
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    # Generate 1-second intervals
    timestamps = pd.date_range(start=start_dt, end=end_dt, freq='1S')
    
    # Mock price data (around $50,000 for BTC)
    base_price = 50000
    price_noise = np.random.normal(0, 10, len(timestamps))
    prices = base_price + price_noise
    
    # Create tick data
    data = {
        'ts_exchange': timestamps,
        'ts_local': timestamps,
        'best_bid': prices - np.random.uniform(0.5, 2.0, len(timestamps)),
        'best_ask': prices + np.random.uniform(0.5, 2.0, len(timestamps)),
        'last_trade_px': prices,
        'last_trade_qty': np.random.uniform(0.001, 0.1, len(timestamps)),
        'event_type': 'trade'
    }
    
    return pd.DataFrame(data)


def main():
    """Create mock parquet files for baseline."""
    
    # Load overlap data
    with open('baselines/2s/OVERLAP.json', 'r') as f:
        overlap_data = json.load(f)
    
    venues = overlap_data['venues']
    start_time = overlap_data['start']
    end_time = overlap_data['end']
    
    print(f"Creating mock data for {len(venues)} venues from {start_time} to {end_time}")
    
    for venue in venues:
        venue_dir = Path(f'baselines/2s/ticks/{venue}')
        venue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock tick data
        df = create_mock_tick_data(start_time, end_time, venue)
        
        # Save as parquet
        parquet_file = venue_dir / 'ticks.parquet'
        df.to_parquet(parquet_file, index=False)
        
        print(f"Created {parquet_file} with {len(df)} rows")
    
    print("Mock parquet data creation completed")


if __name__ == "__main__":
    main()
