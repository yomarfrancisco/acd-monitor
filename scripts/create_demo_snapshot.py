#!/usr/bin/env python3
"""
Create a demo snapshot with synthetic tick data for control v2 analysis.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys


def create_synthetic_tick_data(
    start_time: str, end_time: str, venue: str, base_price: float = 45000.0
) -> pd.DataFrame:
    """Create synthetic tick data for a venue."""
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    # Generate 1-second intervals
    timestamps = pd.date_range(start=start_dt, end=end_dt, freq="1S")

    # Generate price data with some coordination episodes
    np.random.seed(42)  # For reproducibility

    # Base price with random walk
    prices = [base_price]
    for i in range(1, len(timestamps)):
        # Random walk with some episodes of coordination
        if 100 <= i <= 110:  # Episode 1: 10 seconds of coordination
            # All venues move together
            change = np.random.normal(0, 0.5)
        elif 200 <= i <= 215:  # Episode 2: 15 seconds of coordination
            change = np.random.normal(0, 0.3)
        elif 300 <= i <= 310:  # Episode 3: 10 seconds of coordination
            change = np.random.normal(0, 0.4)
        else:
            # Normal random walk
            change = np.random.normal(0, 1.0)

        new_price = prices[-1] + change
        prices.append(new_price)

    # Create tick data
    data = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        # Add some bid-ask spread
        spread = np.random.uniform(0.5, 2.0)
        bid = price - spread / 2
        ask = price + spread / 2

        data.append(
            {
                "exchange": venue,
                "pair": "BTC-USD",
                "ts_exchange": ts,  # Use pandas Timestamp directly
                "ts_local": ts,
                "best_bid": bid,
                "best_ask": ask,
                "mid": price,
                "last_trade_px": price + np.random.normal(0, 0.1),
                "last_trade_qty": np.random.uniform(0.001, 0.1),
                "event_type": "ticker",
            }
        )

    return pd.DataFrame(data)


def create_demo_snapshot():
    """Create a demo snapshot with synthetic data."""
    # Create snapshot directory
    snapshot_dir = Path("experiments/gold_hunt_v1/demo_snapshot")
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Create OVERLAP.json
    overlap_data = {
        "startUTC": "2025-09-27T01:00:00.000000+00:00",
        "endUTC": "2025-09-27T01:10:00.000000+00:00",  # 10 minutes
        "minutes": 10.0,
        "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
        "policy": "DEMO_1s",
        "coverage": 1.0,
        "granularity_sec": 1,
        "min_duration_min": 10,
        "all_venues": True,
        "stitch": False,
        "mode": "DEMO",
        "granularity": "1s",
    }

    with open(snapshot_dir / "OVERLAP.json", "w") as f:
        json.dump(overlap_data, f, indent=2)

    # Create tick data for each venue
    venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
    base_prices = [45000, 45010, 44990, 45005, 44995]  # Slightly different base prices

    for venue, base_price in zip(venues, base_prices):
        # Create venue directory
        venue_dir = snapshot_dir / "ticks" / venue / "BTC-USD" / "1s" / "2025-09-27" / "01"
        venue_dir.mkdir(parents=True, exist_ok=True)

        # Generate tick data
        tick_data = create_synthetic_tick_data(
            "2025-09-27T01:00:00+00:00", "2025-09-27T01:10:00+00:00", venue, base_price
        )

        # Save as parquet
        tick_data.to_parquet(venue_dir / "ticks_00.parquet", index=False)

    print(f"Created demo snapshot in {snapshot_dir}")
    return str(snapshot_dir)


if __name__ == "__main__":
    snapshot_path = create_demo_snapshot()
    print(f"Demo snapshot created at: {snapshot_path}")
