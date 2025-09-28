#!/usr/bin/env python3
"""
Gold Hunt Control v2: Z-score dispersion detector with matched controls

This script implements:
1. Z-score dispersion detector alongside current fixed-threshold detector
2. Matched control sampling (kNN on vol30s, volrate, t_in_window)
3. Episode vs matched controls comparison with bootstrap p-values
4. Updated Phase 5 gates with matched-control requirements
"""

import argparse
import json
import logging
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import scipy.stats as stats
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.data.cache import DataCache
from acd.analytics.spread_convergence import SpreadConvergenceAnalyzer
from acdlib.io.load_snapshot import load_snapshot_data
from _analysis_utils import inclusive_end_date, ensure_time_mid_volume, resample_second, validate_dataframe


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('gold_hunt_control_v2.log')
        ]
    )


class ZScoreDispersionDetector:
    """Z-score based dispersion detector to avoid threshold artifacts."""
    
    def __init__(self, k_window: int = 60, z_cut: float = -1.5, merge_gap: int = 2):
        """
        Initialize z-score detector.
        
        Args:
            k_window: Rolling window size for baseline (seconds)
            z_cut: Z-score threshold for episode detection
            merge_gap: Maximum gap to merge nearby episodes (seconds)
        """
        self.k_window = k_window
        self.z_cut = z_cut
        self.merge_gap = merge_gap
        self.logger = logging.getLogger(__name__)
    
    def compute_dispersion_zscore(self, dispersion: pd.Series) -> pd.Series:
        """
        Compute rolling z-score of dispersion vs baseline.
        
        Args:
            dispersion: Series of dispersion values
            
        Returns:
            Series of z-scores
        """
        # Rolling median and MAD for robust statistics
        rolling_median = dispersion.rolling(window=self.k_window, center=True).median()
        rolling_mad = dispersion.rolling(window=self.k_window, center=True).apply(
            lambda x: np.median(np.abs(x - np.median(x)))
        )
        
        # Z-score: (value - median) / MAD
        z_scores = (dispersion - rolling_median) / rolling_mad
        
        # Handle edge cases
        z_scores = z_scores.fillna(0)
        
        return z_scores
    
    def detect_episodes(self, dispersion: pd.Series, z_scores: pd.Series) -> List[Dict[str, Any]]:
        """
        Detect episodes using z-score threshold.
        
        Args:
            dispersion: Series of dispersion values
            z_scores: Series of z-scores
            
        Returns:
            List of detected episodes
        """
        episodes = []
        
        # Find regions below z_cut threshold
        below_threshold = z_scores < self.z_cut
        
        # Find episode boundaries
        episode_starts = []
        episode_ends = []
        
        in_episode = False
        start_idx = None
        
        for i, is_below in enumerate(below_threshold):
            if is_below and not in_episode:
                # Start of new episode
                in_episode = True
                start_idx = i
            elif not is_below and in_episode:
                # End of episode
                episode_ends.append(i - 1)
                in_episode = False
                if start_idx is not None:
                    episode_starts.append(start_idx)
        
        # Handle episode that extends to end
        if in_episode and start_idx is not None:
            episode_ends.append(len(below_threshold) - 1)
            episode_starts.append(start_idx)
        
        # Merge nearby episodes
        merged_episodes = self._merge_nearby_episodes(episode_starts, episode_ends)
        
        # Create episode objects
        for start_idx, end_idx in merged_episodes:
            episode = {
                'start_time': dispersion.index[start_idx],
                'end_time': dispersion.index[end_idx],
                'duration': end_idx - start_idx + 1,
                'start_dispersion': dispersion.iloc[start_idx],
                'end_dispersion': dispersion.iloc[end_idx],
                'start_zscore': z_scores.iloc[start_idx],
                'end_zscore': z_scores.iloc[end_idx],
                'min_zscore': z_scores.iloc[start_idx:end_idx+1].min(),
                'start_idx': start_idx,
                'end_idx': end_idx,
                'detector': 'zscore'
            }
            episodes.append(episode)
        
        self.logger.info(f"Z-score detector found {len(episodes)} episodes")
        return episodes
    
    def _merge_nearby_episodes(self, starts: List[int], ends: List[int]) -> List[Tuple[int, int]]:
        """Merge episodes that are within merge_gap seconds."""
        if not starts:
            return []
        
        merged = []
        current_start = starts[0]
        current_end = ends[0]
        
        for i in range(1, len(starts)):
            # Check if episodes are close enough to merge
            if starts[i] - current_end <= self.merge_gap:
                # Merge episodes
                current_end = ends[i]
            else:
                # Save current episode and start new one
                merged.append((current_start, current_end))
                current_start = starts[i]
                current_end = ends[i]
        
        # Add final episode
        merged.append((current_start, current_end))
        
        return merged


class MatchedControlSampler:
    """Sample matched controls for episodes using kNN."""
    
    def __init__(self, n_controls: int = 100, random_state: int = 42):
        """
        Initialize matched control sampler.
        
        Args:
            n_controls: Number of controls to sample per episode
            random_state: Random seed for reproducibility
        """
        self.n_controls = n_controls
        self.random_state = random_state
        self.logger = logging.getLogger(__name__)
        
        # Set random seed for reproducibility
        np.random.seed(random_state)
    
    def extract_features(self, mid_prices_df: pd.DataFrame, volume_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Extract features for matching: vol30s, volrate, t_in_window.
        
        Args:
            mid_prices_df: DataFrame with mid prices
            volume_df: DataFrame with volume data (optional)
            
        Returns:
            DataFrame with features for each time point
        """
        features = []
        
        for i in range(len(mid_prices_df)):
            # Time in window (0 to 1)
            t_in_window = i / len(mid_prices_df)
            
            # Realized volatility (last 30s)
            vol30s = self._compute_realized_volatility(mid_prices_df, i, window=30)
            
            # Volume rate (if available)
            if volume_df is not None and i < len(volume_df):
                volrate = volume_df.iloc[i].sum() if not volume_df.iloc[i].isna().all() else 0
            else:
                volrate = 0
            
            features.append({
                'time_idx': i,
                't_in_window': t_in_window,
                'vol30s': vol30s,
                'volrate': volrate
            })
        
        return pd.DataFrame(features)
    
    def _compute_realized_volatility(self, prices_df: pd.DataFrame, idx: int, window: int = 30) -> float:
        """Compute realized volatility over rolling window."""
        start_idx = max(0, idx - window)
        window_prices = prices_df.iloc[start_idx:idx+1]
        
        if len(window_prices) < 2:
            return 0.0
        
        # Compute returns
        returns = window_prices.pct_change().dropna()
        
        if len(returns) < 2:
            return 0.0
        
        # Realized volatility (annualized)
        rv = returns.var() * 252 * 24 * 3600  # Assuming 1-second data
        rv_value = rv if isinstance(rv, (int, float)) else rv.iloc[0] if len(rv) > 0 else 0.0
        return np.sqrt(rv_value) if not np.isnan(rv_value) else 0.0
    
    def sample_controls(self, episode_features: pd.Series, all_features: pd.DataFrame, 
                      episode_start: int, episode_end: int) -> List[int]:
        """
        Sample matched controls for an episode.
        
        Args:
            episode_features: Features of the episode
            all_features: All available features
            episode_start: Start index of episode
            episode_end: End index of episode
            
        Returns:
            List of control indices
        """
        # Exclude episode region and nearby regions
        exclude_buffer = 10  # seconds
        exclude_start = max(0, episode_start - exclude_buffer)
        exclude_end = min(len(all_features), episode_end + exclude_buffer)
        
        # Create mask for valid control regions
        valid_mask = np.ones(len(all_features), dtype=bool)
        valid_mask[exclude_start:exclude_end] = False
        
        if not valid_mask.any():
            self.logger.warning("No valid control regions found")
            return []
        
        # Get valid features
        valid_features = all_features[valid_mask]
        valid_indices = all_features.index[valid_mask]
        
        # Standardize features for kNN
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(valid_features[['t_in_window', 'vol30s', 'volrate']])
        episode_scaled = scaler.transform([episode_features[['t_in_window', 'vol30s', 'volrate']].values])
        
        # Find nearest neighbors
        n_neighbors = min(self.n_controls, len(valid_features))
        nn = NearestNeighbors(n_neighbors=n_neighbors)
        nn.fit(features_scaled)
        
        distances, indices = nn.kneighbors(episode_scaled)
        
        # Return control indices
        control_indices = [valid_indices[i] for i in indices[0]]
        
        self.logger.info(f"Sampled {len(control_indices)} matched controls for episode")
        return control_indices


class EpisodeControlAnalyzer:
    """Analyze episodes vs matched controls."""
    
    def __init__(self, n_bootstrap: int = 1000, block_size: int = 10, random_state: int = 42):
        """
        Initialize episode-control analyzer.
        
        Args:
            n_bootstrap: Number of bootstrap samples
            block_size: Block size for block bootstrap (seconds)
            random_state: Random seed for reproducibility
        """
        self.n_bootstrap = n_bootstrap
        self.block_size = block_size
        self.random_state = random_state
        self.logger = logging.getLogger(__name__)
        
        # Set random seed for reproducibility
        np.random.seed(random_state)
    
    def compare_episode_controls(self, episode_data: pd.DataFrame, control_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Compare episode vs matched controls.
        
        Args:
            episode_data: Episode data
            control_data: Matched control data
            
        Returns:
            Comparison results
        """
        results = {}
        
        # Extract metrics
        episode_metrics = self._extract_metrics(episode_data)
        control_metrics = self._extract_metrics(control_data)
        
        # Compare dispersion z-scores
        episode_z = episode_metrics['dispersion_zscore']
        control_z = control_metrics['dispersion_zscore']
        
        # Effect size (Cohen's d)
        pooled_std = np.sqrt(((len(episode_z) - 1) * episode_z.std()**2 + 
                             (len(control_z) - 1) * control_z.std()**2) / 
                            (len(episode_z) + len(control_z) - 2))
        cohens_d = (episode_z.mean() - control_z.mean()) / pooled_std
        
        # Bootstrap p-value
        p_value = self._bootstrap_test(episode_z, control_z)
        
        # AUC below threshold
        threshold = -1.5
        episode_auc = (episode_z < threshold).sum() / len(episode_z)
        control_auc = (control_z < threshold).sum() / len(control_z)
        
        results = {
            'episode_z_mean': episode_z.mean(),
            'control_z_mean': control_z.mean(),
            'delta_z': episode_z.mean() - control_z.mean(),
            'cohens_d': cohens_d,
            'p_value': p_value,
            'episode_auc': episode_auc,
            'control_auc': control_auc,
            'delta_auc': episode_auc - control_auc,
            'n_episode': len(episode_z),
            'n_control': len(control_z)
        }
        
        return results
    
    def _extract_metrics(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Extract metrics from data."""
        return {
            'dispersion_zscore': data.get('dispersion_zscore', pd.Series()),
            'volume_rate': data.get('volume_rate', pd.Series()),
            'realized_vol': data.get('realized_vol', pd.Series())
        }
    
    def _bootstrap_test(self, episode_data: pd.Series, control_data: pd.Series) -> float:
        """Perform block bootstrap test."""
        # Combine data
        combined = pd.concat([episode_data, control_data])
        labels = np.concatenate([np.ones(len(episode_data)), np.zeros(len(control_data))])
        
        # Original difference
        original_diff = episode_data.mean() - control_data.mean()
        
        # Bootstrap samples
        bootstrap_diffs = []
        
        for _ in range(self.n_bootstrap):
            # Block bootstrap
            bootstrap_sample = self._block_bootstrap(combined, labels)
            
            # Calculate difference
            episode_boot = bootstrap_sample[bootstrap_sample == 1]
            control_boot = bootstrap_sample[bootstrap_sample == 0]
            
            if len(episode_boot) > 0 and len(control_boot) > 0:
                diff = episode_boot.mean() - control_boot.mean()
                bootstrap_diffs.append(diff)
        
        # P-value (two-tailed)
        bootstrap_diffs = np.array(bootstrap_diffs)
        p_value = 2 * min(
            np.mean(bootstrap_diffs >= original_diff),
            np.mean(bootstrap_diffs <= original_diff)
        )
        
        return p_value
    
    def _block_bootstrap(self, data: pd.Series, labels: np.ndarray) -> np.ndarray:
        """Perform block bootstrap sampling."""
        n_blocks = len(data) // self.block_size
        bootstrap_labels = []
        
        for _ in range(n_blocks):
            # Random block start
            start_idx = np.random.randint(0, len(data) - self.block_size + 1)
            block_labels = labels[start_idx:start_idx + self.block_size]
            bootstrap_labels.extend(block_labels)
        
        return np.array(bootstrap_labels[:len(data)])


def run_control_v2_analysis(
    snapshot_dir: str,
    export_dir: str,
    detector: str = "zscore",
    n_controls: int = 100,
    z_cut: float = -1.5,
    roll_window: int = 60,
    merge_gap: int = 2,
    min_duration: int = 10,
    mc_features: str = "vol30s,volrate,t_in_window",
    mc_k: int = 5,
    mc_gap: int = 10,
    bb_size: int = 10,
    bb_n: int = 1000,
    seed: int = 42,
    allow_demo: bool = False,
    verbose: bool = False
) -> None:
    """
    Run control v2 analysis with z-score detector and matched controls.
    
    Args:
        snapshot_dir: Directory containing snapshot data
        export_dir: Export directory for results
        n_controls: Number of matched controls per episode
        z_cut: Z-score threshold for episode detection
        verbose: Verbose logging
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting Gold Hunt Control v2 analysis")
    
    # Load snapshot data
    snapshot_path = Path(snapshot_dir)
    overlap_file = snapshot_path / "OVERLAP.json"
    
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found in {snapshot_dir}")
        return
    
    # Load snapshot data using the proper function
    overlap_data, resampled_mids = load_snapshot_data(str(overlap_file), allow_demo=allow_demo)
    
    if resampled_mids.empty:
        logger.error("No tick data loaded from snapshot")
        return
    
    # Convert to the format expected by the analyzer
    tick_data = {}
    for venue in overlap_data['venues']:
        if venue in resampled_mids.columns:
            tick_data[venue] = resampled_mids[[venue]].reset_index()
            tick_data[venue].columns = ['time', 'mid']
    
    if len(tick_data) < 3:
        logger.error(f"Insufficient venues: {len(tick_data)}")
        return
    
    # Build aligned price data
    venues = list(tick_data.keys())
    base_venue = venues[0]
    base_df = tick_data[base_venue].copy()
    base_df = base_df.set_index('time')
    
    for venue in venues[1:]:
        venue_df = tick_data[venue].copy()
        venue_df = venue_df.set_index('time')
        base_df = base_df.join(venue_df, how='inner', rsuffix=f'_{venue}')
    
    base_df = base_df.dropna()
    
    # Compute dispersion
    analyzer = SpreadConvergenceAnalyzer()
    dispersion = analyzer.compute_dispersion(base_df)
    
    # Initialize detector based on type
    if detector == "zscore":
        zscore_detector = ZScoreDispersionDetector(
            k_window=roll_window, 
            z_cut=z_cut, 
            merge_gap=merge_gap
        )
        z_scores = zscore_detector.compute_dispersion_zscore(dispersion)
        zscore_episodes = zscore_detector.detect_episodes(dispersion, z_scores)
        episodes = zscore_episodes
    else:  # percentile detector (original)
        episodes = analyzer.detect_compression_episodes(dispersion, base_df)
        z_scores = None
    
    # Original detector for comparison
    original_episodes = analyzer.detect_compression_episodes(dispersion, base_df)
    
    logger.info(f"Selected detector ({detector}): {len(episodes)} episodes")
    logger.info(f"Original detector: {len(original_episodes)} episodes")
    
    # Matched control analysis
    if episodes:
        # Extract features
        sampler = MatchedControlSampler(n_controls=n_controls, random_state=seed)
        all_features = sampler.extract_features(base_df)
        
        # Analyze each episode
        episode_results = []
        
        for episode in episodes:
            # Get episode features
            episode_start = episode['start_idx']
            episode_end = episode['end_idx']
            episode_features = all_features.iloc[episode_start]
            
            # Sample matched controls
            control_indices = sampler.sample_controls(
                episode_features, all_features, episode_start, episode_end
            )
            
            if not control_indices:
                continue
            
            # Extract episode and control data
            episode_data = base_df.iloc[episode_start:episode_end+1].copy()
            episode_data['dispersion_zscore'] = z_scores.iloc[episode_start:episode_end+1]
            
            control_data_list = []
            for control_idx in control_indices:
                control_start = max(0, control_idx - (episode_end - episode_start))
                control_end = min(len(base_df), control_idx + (episode_end - episode_start) + 1)
                control_data = base_df.iloc[control_start:control_end].copy()
                control_data['dispersion_zscore'] = z_scores.iloc[control_start:control_end]
                control_data_list.append(control_data)
            
            if not control_data_list:
                continue
            
            control_data = pd.concat(control_data_list, ignore_index=True)
            
            # Compare episode vs controls
            analyzer_episode = EpisodeControlAnalyzer(
                n_bootstrap=bb_n, 
                block_size=bb_size, 
                random_state=seed
            )
            comparison = analyzer_episode.compare_episode_controls(episode_data, control_data)
            
            episode_result = {
                'episode': episode,
                'comparison': comparison,
                'n_controls': len(control_indices)
            }
            episode_results.append(episode_result)
        
        # Generate summary report
        generate_control_v2_report(episode_results, export_dir, detector, allow_demo)
        
        # Check updated Phase 5 gates
        check_updated_gates(episode_results, export_dir, allow_demo)
    
    logger.info("Control v2 analysis completed")


def generate_control_v2_report(episode_results: List[Dict], export_dir: str, 
                              detector: str = "zscore", allow_demo: bool = False) -> None:
    """Generate episode vs matched controls summary report."""
    logger = logging.getLogger(__name__)
    
    # Aggregate results
    all_delta_z = [r['comparison']['delta_z'] for r in episode_results]
    all_cohens_d = [r['comparison']['cohens_d'] for r in episode_results]
    all_p_values = [r['comparison']['p_value'] for r in episode_results]
    all_delta_auc = [r['comparison']['delta_auc'] for r in episode_results]
    
    # Add provenance tagging
    provenance = "DEMO" if allow_demo else "REAL"
    regulatory_grade = not allow_demo
    
    summary = {
        'n_episodes': len(episode_results),
        'delta_z_mean': np.mean(all_delta_z),
        'delta_z_std': np.std(all_delta_z),
        'cohens_d_mean': np.mean(all_cohens_d),
        'cohens_d_std': np.std(all_cohens_d),
        'p_value_mean': np.mean(all_p_values),
        'p_value_median': np.median(all_p_values),
        'delta_auc_mean': np.mean(all_delta_auc),
        'episodes': episode_results,
        'provenance': provenance,
        'regulatory_grade': regulatory_grade,
        'detector_type': detector
    }
    
    # Save results
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    
    with open(export_path / 'control_v2_results.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Generate markdown report
    report = generate_markdown_report(summary)
    with open(export_path / 'control_v2_report.md', 'w') as f:
        f.write(report)
    
    logger.info(f"Control v2 report saved to {export_dir}")


def generate_markdown_report(summary: Dict) -> str:
    """Generate markdown report for control v2 results."""
    report = []
    
    report.append("# Gold Hunt Control v2: Episode vs Matched Controls")
    report.append("")
    report.append(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Episodes Analyzed**: {summary['n_episodes']}")
    report.append("")
    
    report.append("## Summary Statistics")
    report.append("")
    report.append(f"- **Mean Δz**: {summary['delta_z_mean']:.3f} ± {summary['delta_z_std']:.3f}")
    report.append(f"- **Mean Cohen's d**: {summary['cohens_d_mean']:.3f} ± {summary['cohens_d_std']:.3f}")
    report.append(f"- **Mean p-value**: {summary['p_value_mean']:.3f}")
    report.append(f"- **Median p-value**: {summary['p_value_median']:.3f}")
    report.append(f"- **Mean ΔAUC**: {summary['delta_auc_mean']:.3f}")
    report.append("")
    
    report.append("## Episode Details")
    report.append("")
    
    for i, episode_result in enumerate(summary['episodes']):
        episode = episode_result['episode']
        comparison = episode_result['comparison']
        
        report.append(f"### Episode {i+1}")
        report.append("")
        report.append(f"- **Duration**: {episode['duration']} seconds")
        report.append(f"- **Start Time**: {episode['start_time']}")
        report.append(f"- **End Time**: {episode['end_time']}")
        report.append(f"- **Min Z-score**: {episode['min_zscore']:.3f}")
        report.append("")
        report.append("**Comparison vs Matched Controls:**")
        report.append(f"- **Δz**: {comparison['delta_z']:.3f}")
        report.append(f"- **Cohen's d**: {comparison['cohens_d']:.3f}")
        report.append(f"- **p-value**: {comparison['p_value']:.3f}")
        report.append(f"- **ΔAUC**: {comparison['delta_auc']:.3f}")
        report.append("")
    
    return "\n".join(report)


def check_updated_gates(episode_results: List[Dict], export_dir: str, allow_demo: bool = False) -> None:
    """Check updated Phase 5 gates with matched control requirements."""
    logger = logging.getLogger(__name__)
    
    # Skip gates for demo data
    if allow_demo:
        logger.info("Skipping Phase 5 gates for demo data")
        gate_results = {
            'gates': {'gate1_episode_control': False, 'gate2_leadlag': False, 'gate3_infoshare': False},
            'reason': 'Demo data - gates only apply to real data',
            'significant_episodes': 0,
            'total_episodes': len(episode_results)
        }
        
        export_path = Path(export_dir)
        with open(export_path / 'updated_gates.json', 'w') as f:
            json.dump(gate_results, f, indent=2, default=str)
        return
    
    gates = {
        'gate1_episode_control': False,
        'gate2_leadlag': False,  # Placeholder - would need leadlag results
        'gate3_infoshare': False  # Placeholder - would need infoshare results
    }
    
    # Gate 1: Episode vs matched controls
    significant_episodes = []
    for episode_result in episode_results:
        comparison = episode_result['comparison']
        
        # Check if episode meets gate criteria
        if (comparison['delta_z'] <= -0.75 and 
            comparison['p_value'] < 0.10 and
            episode_result['episode']['duration'] >= 10):
            significant_episodes.append(episode_result)
    
    gates['gate1_episode_control'] = len(significant_episodes) >= 1
    
    # Save gate results
    gate_results = {
        'gates': gates,
        'significant_episodes': len(significant_episodes),
        'total_episodes': len(episode_results),
        'gate1_criteria': {
            'delta_z_threshold': -0.75,
            'p_value_threshold': 0.10,
            'min_duration': 10
        }
    }
    
    export_path = Path(export_dir)
    with open(export_path / 'updated_gates.json', 'w') as f:
        json.dump(gate_results, f, indent=2, default=str)
    
    logger.info(f"Gate 1 (Episode vs Controls): {'PASS' if gates['gate1_episode_control'] else 'FAIL'}")
    logger.info(f"Significant episodes: {len(significant_episodes)}/{len(episode_results)}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Gold Hunt Control v2 Analysis")
    parser.add_argument("--snapshot-dir", required=True, help="Snapshot directory")
    parser.add_argument("--export-dir", required=True, help="Export directory")
    parser.add_argument("--detector", choices=["percentile", "zscore"], default="percentile", 
                       help="Detector type (default: percentile for backward compatibility)")
    parser.add_argument("--n-controls", type=int, default=100, help="Number of matched controls")
    parser.add_argument("--z-cut", type=float, default=-1.5, help="Z-score threshold")
    parser.add_argument("--roll", type=int, default=60, help="Rolling window size (seconds)")
    parser.add_argument("--merge-gap", type=int, default=2, help="Merge gap tolerance (seconds)")
    parser.add_argument("--min-dur", type=int, default=10, help="Minimum episode duration (seconds)")
    parser.add_argument("--mc-features", default="vol30s,volrate,t_in_window", 
                       help="Matched control features (comma-separated)")
    parser.add_argument("--mc-k", type=int, default=5, help="kNN parameter")
    parser.add_argument("--mc-gap", type=int, default=10, help="Control exclusion gap (seconds)")
    parser.add_argument("--bb-size", type=int, default=10, help="Block bootstrap size (seconds)")
    parser.add_argument("--bb-n", type=int, default=1000, help="Number of bootstrap samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--allow-demo", action="store_true", help="Allow demo/synthetic data")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    run_control_v2_analysis(
        snapshot_dir=args.snapshot_dir,
        export_dir=args.export_dir,
        detector=args.detector,
        n_controls=args.n_controls,
        z_cut=args.z_cut,
        roll_window=args.roll,
        merge_gap=args.merge_gap,
        min_duration=args.min_dur,
        mc_features=args.mc_features,
        mc_k=args.mc_k,
        mc_gap=args.mc_gap,
        bb_size=args.bb_size,
        bb_n=args.bb_n,
        seed=args.seed,
        allow_demo=args.allow_demo,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
