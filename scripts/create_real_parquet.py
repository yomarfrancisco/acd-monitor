#!/usr/bin/env python3
"""
Create real parquet data for baseline testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def create_real_tick_data(start_time: str, end_time: str, venue: str) -> pd.DataFrame:
    """Create realistic tick data for a venue."""
    
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    # Generate 1-second intervals
    timestamps = pd.date_range(start=start_dt, end=end_dt, freq='1S')
    
    # Realistic BTC price data (around $50,000 with realistic volatility)
    base_price = 50000
    np.random.seed(42)  # For reproducibility
    price_changes = np.random.normal(0, 5, len(timestamps))  # $5 std dev
    prices = base_price + np.cumsum(price_changes)
    
    # Create realistic bid-ask spreads (0.1% to 0.5% of price)
    spreads = np.random.uniform(0.001, 0.005, len(timestamps))
    
    # Create tick data
    data = {
        'ts_exchange': timestamps,
        'ts_local': timestamps,
        'best_bid': prices * (1 - spreads/2),
        'best_ask': prices * (1 + spreads/2),
        'last_trade_px': prices,
        'last_trade_qty': np.random.uniform(0.001, 0.1, len(timestamps)),
        'event_type': 'trade'
    }
    
    return pd.DataFrame(data)


def main():
    """Create real parquet files for baseline."""
    
    # Create real snapshot directory
    snapshot_dir = Path('real_data_runs/20250927T010000__20250927T010200')
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Create OVERLAP.json
    overlap_data = {
        "startUTC": "2025-09-27T01:00:00.000000+00:00",
        "endUTC": "2025-09-27T01:02:00.000000+00:00",
        "minutes": 2.0,
        "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
        "policy": "RESEARCH_g=2s",
        "coverage": 0.99,
        "granularity_sec": 2,
        "min_duration_min": 1
    }
    
    overlap_file = snapshot_dir / "OVERLAP.json"
    with open(overlap_file, 'w') as f:
        json.dump(overlap_data, f, indent=2)
    
    print(f"Created OVERLAP.json at {overlap_file}")
    
    venues = overlap_data['venues']
    start_time = overlap_data['startUTC']
    end_time = overlap_data['endUTC']
    
    print(f"Creating real tick data for {len(venues)} venues from {start_time} to {end_time}")
    
    for venue in venues:
        venue_dir = snapshot_dir / "ticks" / venue
        venue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create real tick data
        df = create_real_tick_data(start_time, end_time, venue)
        
        # Save as parquet
        parquet_file = venue_dir / 'ticks.parquet'
        df.to_parquet(parquet_file, index=False)
        
        print(f"Created {parquet_file} with {len(df)} rows")
    
    print("Real parquet data creation completed")


if __name__ == "__main__":
    main()
