#!/usr/bin/env python3
"""
Venue Excess Revenue Analysis: Calculate Δ fee revenue during coordination episodes.

This script calculates venue excess fee revenue during coordination episodes by
comparing actual fee revenue to a competitive baseline model.
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
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

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

def load_fee_schedules(bucket: str, key: str) -> Dict:
    """Load normalized fee schedules from S3."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        fee_data = json.loads(response['Body'].read())
        
        logger.info(f"Loaded fee schedules for {len(fee_data)} venues")
        return fee_data
        
    except Exception as e:
        logger.error(f"Failed to load fee schedules: {e}")
        raise

def load_micro_controls(controls_path: str) -> Dict:
    """Load microstructure controls."""
    try:
        with open(controls_path, 'r') as f:
            controls_data = json.load(f)
        
        logger.info(f"Loaded microstructure controls: {controls_data['summary']}")
        return controls_data
        
    except Exception as e:
        logger.error(f"Failed to load microstructure controls: {e}")
        raise

def load_episodes(episodes_path: str) -> List[Dict]:
    """Load coordination episodes."""
    try:
        with open(episodes_path, 'r') as f:
            episodes_data = json.load(f)
        
        if 'episodes' in episodes_data:
            episodes = episodes_data['episodes']
        else:
            episodes = episodes_data
        
        logger.info(f"Loaded {len(episodes)} episodes")
        return episodes
        
    except Exception as e:
        logger.error(f"Failed to load episodes: {e}")
        raise

def calculate_fee_revenue(venue: str, notional_traded: float, 
                         fee_schedules: Dict, tier: str = "retail") -> float:
    """Calculate fee revenue for a venue."""
    try:
        venue_fees = fee_schedules.get(venue, {})
        
        if "error" in venue_fees:
            logger.warning(f"Fee schedule error for {venue}: {venue_fees['error']}")
            return 0.0
        
        # Get fee rates
        if tier == "retail":
            taker_fee_bps = venue_fees.get("retail", {}).get("taker_bps", 0)
        else:
            taker_fee_bps = venue_fees.get("tiers", {}).get(tier, {}).get("taker_bps", 0)
        
        # Calculate fee revenue in basis points
        fee_revenue_bps = taker_fee_bps * notional_traded
        
        return fee_revenue_bps
        
    except Exception as e:
        logger.error(f"Failed to calculate fee revenue for {venue}: {e}")
        return 0.0

def build_baseline_model(micro_controls: pd.DataFrame, 
                        fee_revenue: pd.DataFrame) -> Dict:
    """Build competitive baseline model for fee revenue."""
    try:
        # Prepare features for baseline model
        features = [
            'rv_30s', 'rv_5s', 'momentum_1s', 'momentum_5s', 'momentum_30s',
            'hour', 'minute', 'second', 'day_of_week'
        ]
        
        # Create feature matrix
        X = micro_controls[features].fillna(0)
        y = fee_revenue['fee_revenue_bps']
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Fit baseline model
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # Calculate predictions
        y_pred = model.predict(X_scaled)
        
        # Calculate residuals
        residuals = y - y_pred
        
        baseline_model = {
            "model_type": "linear_regression",
            "features": features,
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(X_scaled, y)),
            "predictions": y_pred.tolist(),
            "residuals": residuals.tolist(),
            "mean_residual": float(residuals.mean()),
            "std_residual": float(residuals.std())
        }
        
        logger.info(f"Baseline model R² = {baseline_model['r_squared']:.3f}")
        return baseline_model
        
    except Exception as e:
        logger.error(f"Failed to build baseline model: {e}")
        return {"error": str(e)}

def calculate_episode_excess_revenue(episodes: List[Dict], 
                                   micro_controls: pd.DataFrame,
                                   fee_schedules: Dict,
                                   baseline_model: Dict) -> List[Dict]:
    """Calculate excess revenue for each episode."""
    episode_results = []
    
    for i, episode in enumerate(episodes):
        try:
            # Extract episode information
            if 'episode' in episode:
                episode_data = episode['episode']
            else:
                episode_data = episode
            
            start_time = pd.to_datetime(episode_data['start_time'])
            end_time = pd.to_datetime(episode_data['end_time'])
            
            # Filter controls for episode period
            episode_controls = micro_controls[
                (micro_controls['timestamp'] >= start_time) & 
                (micro_controls['timestamp'] <= end_time)
            ]
            
            if len(episode_controls) == 0:
                logger.warning(f"No controls found for episode {i}")
                continue
            
            # Calculate fee revenue for each venue during episode
            venue_revenues = {}
            for venue in episode_controls['venue'].unique():
                venue_controls = episode_controls[episode_controls['venue'] == venue]
                
                # Estimate notional traded (simplified - would need actual trade data)
                # For now, use price * volume proxy
                notional_traded = venue_controls['price'].sum() * 0.1  # Placeholder
                
                # Calculate fee revenue
                fee_revenue = calculate_fee_revenue(venue, notional_traded, fee_schedules)
                venue_revenues[venue] = fee_revenue
            
            # Calculate baseline predictions
            episode_features = episode_controls[baseline_model['features']].fillna(0)
            baseline_predictions = np.dot(episode_features, baseline_model['coefficients']) + baseline_model['intercept']
            
            # Calculate excess revenue
            actual_revenue = sum(venue_revenues.values())
            baseline_revenue = baseline_predictions.sum()
            excess_revenue = actual_revenue - baseline_revenue
            
            episode_results.append({
                "episode_index": i,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "venue_revenues": venue_revenues,
                "actual_revenue_bps": actual_revenue,
                "baseline_revenue_bps": baseline_revenue,
                "excess_revenue_bps": excess_revenue,
                "excess_revenue_pct": (excess_revenue / baseline_revenue * 100) if baseline_revenue > 0 else 0
            })
            
        except Exception as e:
            logger.error(f"Failed to process episode {i}: {e}")
            continue
    
    return episode_results

def run_venue_excess_revenue_analysis(snapshot_path: str, 
                                    episodes_path: str,
                                    micro_controls_path: str,
                                    fee_schedules_bucket: str,
                                    fee_schedules_key: str,
                                    output_path: str) -> bool:
    """Run venue excess revenue analysis."""
    try:
        # Load data
        logger.info("Loading fee schedules")
        fee_schedules = load_fee_schedules(fee_schedules_bucket, fee_schedules_key)
        
        logger.info("Loading microstructure controls")
        micro_controls_data = load_micro_controls(micro_controls_path)
        micro_controls = pd.DataFrame(micro_controls_data['micro_controls'])
        
        logger.info("Loading episodes")
        episodes = load_episodes(episodes_path)
        
        # Calculate fee revenue for all timestamps
        logger.info("Calculating fee revenue for all timestamps")
        fee_revenue_data = []
        for _, row in micro_controls.iterrows():
            venue = row['venue']
            notional_traded = row['price'] * 0.1  # Placeholder - would need actual trade data
            
            fee_revenue = calculate_fee_revenue(venue, notional_traded, fee_schedules)
            
            fee_revenue_data.append({
                'timestamp': row['timestamp'],
                'venue': venue,
                'fee_revenue_bps': fee_revenue
            })
        
        fee_revenue_df = pd.DataFrame(fee_revenue_data)
        
        # Build baseline model
        logger.info("Building competitive baseline model")
        baseline_model = build_baseline_model(micro_controls, fee_revenue_df)
        
        if "error" in baseline_model:
            logger.error(f"Baseline model failed: {baseline_model['error']}")
            return False
        
        # Calculate episode excess revenue
        logger.info("Calculating episode excess revenue")
        episode_results = calculate_episode_excess_revenue(
            episodes, micro_controls, fee_schedules, baseline_model
        )
        
        # Prepare output
        output_data = {
            "snapshot_path": snapshot_path,
            "episodes_path": episodes_path,
            "micro_controls_path": micro_controls_path,
            "baseline_model": baseline_model,
            "episode_results": episode_results,
            "summary": {
                "n_episodes": len(episode_results),
                "total_excess_revenue_bps": sum(ep['excess_revenue_bps'] for ep in episode_results),
                "mean_excess_revenue_bps": np.mean([ep['excess_revenue_bps'] for ep in episode_results]),
                "std_excess_revenue_bps": np.std([ep['excess_revenue_bps'] for ep in episode_results])
            },
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Write output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, cls=PandasJSONEncoder, indent=2)
        
        logger.info(f"Venue excess revenue analysis completed: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Venue excess revenue analysis failed: {e}")
        return False

def main():
    """Main function for venue excess revenue analysis."""
    parser = argparse.ArgumentParser(description="Calculate venue excess revenue")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--episodes", required=True, help="Path to episodes JSON")
    parser.add_argument("--micro-controls", required=True, help="Path to micro_controls.json")
    parser.add_argument("--fee-bucket", default="acd-monitor-snapshots", help="S3 bucket for fee schedules")
    parser.add_argument("--fee-key", default="fee_schedules/normalized_fees.json", help="S3 key for fee schedules")
    parser.add_argument("--output", required=True, help="Output path for analysis results")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        # Run analysis
        success = run_venue_excess_revenue_analysis(
            args.snapshot, args.episodes, args.micro_controls,
            args.fee_bucket, args.fee_key, args.output
        )
        
        if success:
            logger.info("Venue excess revenue analysis completed successfully")
            sys.exit(0)
        else:
            logger.error("Failed to complete venue excess revenue analysis")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Venue excess revenue analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
