#!/usr/bin/env python3
"""
Microstructure Controls Export: Generate per-second controls for economic harm analysis.

This script exports per-second microstructure controls (spread, depth, volatility, 
imbalance, etc.) for existing BTC-USD and ETH-USD windows to support economic harm analysis.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd

# Import custom JSON encoder
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""
    
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

def load_snapshot_data(snapshot_path: str) -> Tuple[pd.DataFrame, Dict]:
    """Load snapshot data and return resampled mids and metadata."""
    try:
        # Import the snapshot loader
        sys.path.append(str(Path(__file__).parent.parent / "src"))
        from acdlib.io.load_snapshot import load_snapshot_data as load_snapshot
        
        # Load the snapshot
        overlap_data, resampled_mids = load_snapshot(snapshot_path, allow_demo=False)
        
        logger.info(f"Loaded snapshot with {len(resampled_mids)} time points")
        return resampled_mids, overlap_data
        
    except Exception as e:
        logger.error(f"Failed to load snapshot: {e}")
        raise

def calculate_microstructure_controls(resampled_mids: pd.DataFrame, 
                                    overlap_data: Dict) -> pd.DataFrame:
    """Calculate per-second microstructure controls."""
    
    controls = []
    
    for venue in resampled_mids.columns:
        venue_data = resampled_mids[venue].dropna()
        
        if len(venue_data) < 2:
            continue
        
        # Calculate controls for each second
        for i in range(len(venue_data)):
            timestamp = venue_data.index[i]
            price = venue_data.iloc[i]
            
            # Realized volatility (30-second window)
            if i >= 30:
                rv_30s = venue_data.iloc[i-30:i].pct_change().std() * np.sqrt(30)
            else:
                rv_30s = np.nan
            
            # Realized volatility (5-second window)
            if i >= 5:
                rv_5s = venue_data.iloc[i-5:i].pct_change().std() * np.sqrt(5)
            else:
                rv_5s = np.nan
            
            # Price level
            price_level = price
            
            # Time-of-day features
            hour = timestamp.hour
            minute = timestamp.minute
            second = timestamp.second
            
            # Day of week
            day_of_week = timestamp.weekday()
            
            # Market session (simplified)
            if 0 <= hour < 8:
                session = "asia"
            elif 8 <= hour < 16:
                session = "europe"
            else:
                session = "americas"
            
            # Price momentum (1-second return)
            if i > 0:
                momentum_1s = (price - venue_data.iloc[i-1]) / venue_data.iloc[i-1]
            else:
                momentum_1s = 0.0
            
            # Price momentum (5-second return)
            if i >= 5:
                momentum_5s = (price - venue_data.iloc[i-5]) / venue_data.iloc[i-5]
            else:
                momentum_5s = 0.0
            
            # Price momentum (30-second return)
            if i >= 30:
                momentum_30s = (price - venue_data.iloc[i-30]) / venue_data.iloc[i-30]
            else:
                momentum_30s = 0.0
            
            # Volatility regime (simplified)
            if rv_30s > 0.02:  # 2% threshold
                vol_regime = "high"
            elif rv_30s > 0.01:  # 1% threshold
                vol_regime = "medium"
            else:
                vol_regime = "low"
            
            controls.append({
                "timestamp": timestamp,
                "venue": venue,
                "price": price_level,
                "rv_30s": rv_30s,
                "rv_5s": rv_5s,
                "momentum_1s": momentum_1s,
                "momentum_5s": momentum_5s,
                "momentum_30s": momentum_30s,
                "hour": hour,
                "minute": minute,
                "second": second,
                "day_of_week": day_of_week,
                "session": session,
                "vol_regime": vol_regime
            })
    
    return pd.DataFrame(controls)

def calculate_cross_venue_controls(resampled_mids: pd.DataFrame) -> pd.DataFrame:
    """Calculate cross-venue microstructure controls."""
    
    cross_controls = []
    
    # Calculate cross-venue spreads
    venues = resampled_mids.columns
    for i in range(len(venues)):
        for j in range(i+1, len(venues)):
            venue1, venue2 = venues[i], venues[j]
            
            # Get common timestamps
            common_idx = resampled_mids[venue1].dropna().index.intersection(
                resampled_mids[venue2].dropna().index
            )
            
            if len(common_idx) == 0:
                continue
            
            venue1_prices = resampled_mids[venue1].loc[common_idx]
            venue2_prices = resampled_mids[venue2].loc[common_idx]
            
            # Calculate spread between venues
            spread = abs(venue1_prices - venue2_prices)
            spread_bps = (spread / venue1_prices) * 10000  # Convert to basis points
            
            for timestamp, spread_val, spread_bps_val in zip(common_idx, spread, spread_bps):
                cross_controls.append({
                    "timestamp": timestamp,
                    "venue1": venue1,
                    "venue2": venue2,
                    "spread": spread_val,
                    "spread_bps": spread_bps_val
                })
    
    return pd.DataFrame(cross_controls)

def export_micro_controls(snapshot_path: str, output_path: str) -> bool:
    """Export microstructure controls for a snapshot."""
    try:
        # Load snapshot data
        resampled_mids, overlap_data = load_snapshot_data(snapshot_path)
        
        # Calculate microstructure controls
        logger.info("Calculating microstructure controls")
        micro_controls = calculate_microstructure_controls(resampled_mids, overlap_data)
        
        # Calculate cross-venue controls
        logger.info("Calculating cross-venue controls")
        cross_controls = calculate_cross_venue_controls(resampled_mids)
        
        # Prepare output data
        output_data = {
            "snapshot_path": snapshot_path,
            "overlap_data": overlap_data,
            "micro_controls": micro_controls.to_dict('records'),
            "cross_controls": cross_controls.to_dict('records'),
            "summary": {
                "n_venues": len(resampled_mids.columns),
                "n_timestamps": len(resampled_mids),
                "n_micro_controls": len(micro_controls),
                "n_cross_controls": len(cross_controls),
                "venues": list(resampled_mids.columns)
            },
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, cls=PandasJSONEncoder, indent=2)
        
        logger.info(f"Microstructure controls exported to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export microstructure controls: {e}")
        return False

def main():
    """Main function for microstructure controls export."""
    parser = argparse.ArgumentParser(description="Export microstructure controls")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--output", required=True, help="Output path for micro_controls.json")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        # Export microstructure controls
        success = export_micro_controls(args.snapshot, args.output)
        
        if success:
            logger.info("Microstructure controls export completed successfully")
            sys.exit(0)
        else:
            logger.error("Failed to export microstructure controls")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Microstructure controls export failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
