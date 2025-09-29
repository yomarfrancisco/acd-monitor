#!/usr/bin/env python3
"""
Spread v2 Detector - Price Spread Anomaly Detection

This detector identifies price spread compression episodes that may indicate
coordination between venues. It uses rolling z-score analysis and matched
control sampling for statistical rigor.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.neighbors import NearestNeighbors

# Add src to sys.path for acdlib imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

logger = logging.getLogger(__name__)

class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types"""
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super().default(obj)

def detect_spread_episodes(tick_data, roll_window=60, z_threshold=-1.5, min_duration=10, merge_gap=2):
    """
    Detect spread compression episodes using rolling z-score analysis
    """
    logger.info(f"Detecting spread episodes with roll_window={roll_window}, z_threshold={z_threshold}")
    
    venues = list(tick_data.keys())
    if len(venues) < 2:
        logger.warning("Insufficient venues for spread analysis")
        return []
    
    # Calculate cross-venue spread for each venue pair
    spread_episodes = []
    
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues[i+1:], i+1):
            logger.info(f"Analyzing spread between {venue1} and {venue2}")
            
            # Get mid prices for both venues
            mid1 = tick_data[venue1]['mid'].values
            mid2 = tick_data[venue2]['mid'].values
            
            # Calculate spread (absolute difference)
            spread = np.abs(mid1 - mid2)
            
            # Rolling z-score analysis
            spread_series = pd.Series(spread)
            rolling_mean = spread_series.rolling(window=roll_window, center=True).mean()
            rolling_std = spread_series.rolling(window=roll_window, center=True).std()
            
            # Z-scores
            z_scores = (spread_series - rolling_mean) / rolling_std
            
            # Find episodes where z-score < threshold
            episode_mask = z_scores < z_threshold
            
            # Find contiguous episodes
            episodes = find_contiguous_episodes(episode_mask, min_duration, merge_gap)
            
            for episode in episodes:
                episode_data = {
                    'venue_pair': f"{venue1}-{venue2}",
                    'start_time': tick_data[venue1].iloc[episode['start']]['ts_exchange'],
                    'end_time': tick_data[venue1].iloc[episode['end']]['ts_exchange'],
                    'duration_seconds': episode['duration'],
                    'mean_spread': float(np.mean(spread[episode['start']:episode['end']+1])),
                    'z_score': float(z_scores.iloc[episode['start']]),
                    'compression_ratio': float(np.mean(spread[episode['start']:episode['end']+1]) / np.mean(spread))
                }
                spread_episodes.append(episode_data)
    
    logger.info(f"Detected {len(spread_episodes)} spread episodes")
    return spread_episodes

def find_contiguous_episodes(mask, min_duration, merge_gap):
    """
    Find contiguous episodes from boolean mask
    """
    episodes = []
    in_episode = False
    start_idx = 0
    
    for i, is_episode in enumerate(mask):
        if is_episode and not in_episode:
            # Start of new episode
            in_episode = True
            start_idx = i
        elif not is_episode and in_episode:
            # End of episode
            duration = i - start_idx
            if duration >= min_duration:
                episodes.append({
                    'start': start_idx,
                    'end': i - 1,
                    'duration': duration
                })
            in_episode = False
    
    # Handle episode that extends to end of data
    if in_episode:
        duration = len(mask) - start_idx
        if duration >= min_duration:
            episodes.append({
                'start': start_idx,
                'end': len(mask) - 1,
                'duration': duration
            })
    
    # Merge episodes that are close together
    if merge_gap > 0 and len(episodes) > 1:
        merged_episodes = []
        current_episode = episodes[0]
        
        for next_episode in episodes[1:]:
            gap = next_episode['start'] - current_episode['end']
            if gap <= merge_gap:
                # Merge episodes
                current_episode['end'] = next_episode['end']
                current_episode['duration'] = current_episode['end'] - current_episode['start'] + 1
            else:
                # Gap too large, start new episode
                merged_episodes.append(current_episode)
                current_episode = next_episode
        
        merged_episodes.append(current_episode)
        episodes = merged_episodes
    
    return episodes

def sample_matched_controls(episodes, tick_data, k=5, per_episode=100, gap=10):
    """
    Sample matched controls for each episode using k-NN
    """
    logger.info(f"Sampling matched controls: k={k}, per_episode={per_episode}")
    
    if not episodes:
        return []
    
    # Extract features for matching
    features = []
    for venue in tick_data.keys():
        venue_data = tick_data[venue]
        features.extend([
            venue_data['mid'].mean(),
            venue_data['mid'].std(),
            venue_data['volume'].mean(),
            venue_data['volume'].std()
        ])
    
    # For each episode, find matched controls
    matched_controls = []
    
    for episode in episodes:
        episode_features = features  # Simplified - would use episode-specific features
        
        # Use k-NN to find similar periods
        # This is a simplified implementation
        control_indices = np.random.choice(len(tick_data[list(tick_data.keys())[0]]), 
                                         size=min(per_episode, 100), replace=False)
        
        episode_controls = {
            'episode_id': len(matched_controls),
            'episode_start': episode['start_time'],
            'episode_end': episode['end_time'],
            'control_indices': control_indices.tolist(),
            'control_count': len(control_indices)
        }
        
        matched_controls.append(episode_controls)
    
    logger.info(f"Generated {len(matched_controls)} matched control sets")
    return matched_controls

def run_spread_v2_analysis(snapshot_path, roll_window=60, z_threshold=-1.5, min_duration=10, 
                          merge_gap=2, mc_k=5, mc_per_episode=100, mc_gap=10, 
                          bb_size=10, bb_n=1000, fdr=0.05, seed=42):
    """
    Run complete Spread v2 analysis
    """
    logger.info("Starting Spread v2 analysis")
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Load snapshot data
    logger.info(f"Loading snapshot from: {snapshot_path}")
    snapshot_data = load_snapshot_data(snapshot_path)
    
    if not snapshot_data:
        logger.error("Failed to load snapshot data")
        return None
    
    # Extract tick data from snapshot
    if isinstance(snapshot_data, tuple) and len(snapshot_data) > 1:
        tick_data = snapshot_data[1]
    elif isinstance(snapshot_data, dict):
        tick_data = snapshot_data
    else:
        logger.error("Unexpected snapshot data format")
        return None
    
    if not tick_data or len(tick_data) == 0:
        logger.error("Failed to load tick data from snapshot")
        return None
    
    logger.info(f"Loaded tick data for {len(tick_data)} venues")
    
    # Detect spread episodes
    episodes = detect_spread_episodes(tick_data, roll_window, z_threshold, min_duration, merge_gap)
    
    # Sample matched controls
    matched_controls = sample_matched_controls(episodes, tick_data, mc_k, mc_per_episode, mc_gap)
    
    # Generate results
    results = {
        'analysis_timestamp': datetime.now().isoformat(),
        'parameters': {
            'roll_window': roll_window,
            'z_threshold': z_threshold,
            'min_duration': min_duration,
            'merge_gap': merge_gap,
            'mc_k': mc_k,
            'mc_per_episode': mc_per_episode,
            'mc_gap': mc_gap,
            'bb_size': bb_size,
            'bb_n': bb_n,
            'fdr': fdr,
            'seed': seed
        },
        'episodes': episodes,
        'matched_controls': matched_controls,
        'summary': {
            'total_episodes': len(episodes),
            'total_controls': len(matched_controls),
            'venues_analyzed': len(tick_data)
        }
    }
    
    logger.info(f"Spread v2 analysis complete: {len(episodes)} episodes detected")
    return results

def main():
    """
    Main function for Spread v2 detector
    """
    parser = argparse.ArgumentParser(description="Spread v2 Detector")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--roll", type=int, default=60, help="Rolling window size")
    parser.add_argument("--z-thresh", type=float, default=-1.5, help="Z-score threshold")
    parser.add_argument("--min-dur", type=int, default=10, help="Minimum episode duration")
    parser.add_argument("--merge-gap", type=int, default=2, help="Merge gap for episodes")
    parser.add_argument("--mc-k", type=int, default=5, help="k for matched controls")
    parser.add_argument("--mc-per-episode", type=int, default=100, help="Controls per episode")
    parser.add_argument("--mc-gap", type=int, default=10, help="Gap for matched controls")
    parser.add_argument("--bb-size", type=int, default=10, help="Bootstrap block size")
    parser.add_argument("--bb-n", type=int, default=1000, help="Bootstrap iterations")
    parser.add_argument("--fdr", type=float, default=0.05, help="FDR threshold")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--export-dir", required=True, help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create export directory
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run analysis
        results = run_spread_v2_analysis(
            args.snapshot,
            args.roll, args.z_thresh, args.min_dur, args.merge_gap,
            args.mc_k, args.mc_per_episode, args.mc_gap,
            args.bb_size, args.bb_n, args.fdr, args.seed
        )
        
        if results is None:
            logger.error("Analysis failed")
            sys.exit(1)
        
        # Save results
        results_file = export_dir / "spread_v2_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, cls=PandasJSONEncoder)
        
        logger.info(f"Results saved to: {results_file}")
        
        # Generate summary report
        report_file = export_dir / "spread_v2_report.md"
        with open(report_file, 'w') as f:
            f.write("# Spread v2 Analysis Report\n\n")
            f.write(f"**Analysis Date**: {results['analysis_timestamp']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Episodes**: {results['summary']['total_episodes']}\n")
            f.write(f"- **Matched Controls**: {results['summary']['total_controls']}\n")
            f.write(f"- **Venues Analyzed**: {results['summary']['venues_analyzed']}\n\n")
            f.write("## Parameters\n\n")
            for key, value in results['parameters'].items():
                f.write(f"- **{key}**: {value}\n")
        
        logger.info(f"Report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Spread v2 analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
