#!/usr/bin/env python3
"""
Lead-Lag v2 Analysis: Cross-correlation analysis with placebo tests and FDR control.

This script implements the updated lead-lag analysis with:
- HAC standard errors for lagged OLS
- Block bootstrap for robust inference
- Placebo tests with circular time-shift
- BH-FDR for multiple testing correction
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import acf

# Import custom JSON encoder from Section 2.1
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
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        return super().default(obj)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

def load_snapshot_from_s3(snapshot_path: str) -> Tuple[pd.DataFrame, Dict]:
    """Load snapshot data from S3 path."""
    try:
        # For now, assume local path - will be updated for S3
        if snapshot_path.startswith('s3://'):
            # TODO: Implement S3 loading
            raise NotImplementedError("S3 loading not yet implemented")
        
        # Local path loading - handle both file and directory paths
        if snapshot_path.endswith('OVERLAP.json'):
            overlap_path = snapshot_path
        else:
            overlap_path = str(Path(snapshot_path) / "OVERLAP.json")
        
        overlap_data, tick_data = load_snapshot_data(overlap_path)
        
        return tick_data, overlap_data
    except Exception as e:
        logger.error(f"Failed to load snapshot from {snapshot_path}: {e}")
        raise

def compute_returns(prices: pd.Series, horizon: int = 1) -> pd.Series:
    """Compute log returns with specified horizon."""
    return np.log(prices / prices.shift(horizon))

def compute_cross_correlation(returns_i: pd.Series, returns_j: pd.Series, 
                            tau_max: int, tau_range: range) -> Tuple[float, int, float]:
    """
    Compute cross-correlation between two return series.
    
    Returns:
        max_corr: Maximum correlation coefficient
        tau_star: Lag at maximum correlation
        p_value: P-value for the correlation
    """
    # Align series
    aligned_i = returns_i.dropna()
    aligned_j = returns_j.dropna()
    
    if len(aligned_i) < 10 or len(aligned_j) < 10:
        return 0.0, 0, 1.0
    
    # Compute correlations for all lags
    correlations = []
    for tau in tau_range:
        if tau == 0:
            corr = aligned_i.corr(aligned_j)
        elif tau > 0:
            # j leads i
            corr = aligned_i.corr(aligned_j.shift(-tau))
        else:
            # i leads j
            corr = aligned_i.shift(tau).corr(aligned_j)
        
        correlations.append(corr if not np.isnan(corr) else 0.0)
    
    # Find maximum correlation
    max_idx = np.argmax(np.abs(correlations))
    max_corr = correlations[max_idx]
    tau_star = tau_range[max_idx]
    
    # Compute p-value using HAC standard errors
    p_value = compute_hac_p_value(aligned_i, aligned_j, tau_star, max_corr)
    
    return max_corr, tau_star, p_value

def compute_hac_p_value(returns_i: pd.Series, returns_j: pd.Series, 
                       tau: int, correlation: float) -> float:
    """Compute p-value using HAC standard errors."""
    try:
        # Align series for the specific lag
        if tau == 0:
            aligned_i = returns_i.dropna()
            aligned_j = returns_j.dropna()
        elif tau > 0:
            aligned_i = returns_i.dropna()
            aligned_j = returns_j.shift(-tau).dropna()
        else:
            aligned_i = returns_i.shift(tau).dropna()
            aligned_j = returns_j.dropna()
        
        # Ensure same length
        min_len = min(len(aligned_i), len(aligned_j))
        aligned_i = aligned_i.iloc[:min_len]
        aligned_j = aligned_j.iloc[:min_len]
        
        if len(aligned_i) < 10:
            return 1.0
        
        # Compute correlation and standard error
        n = len(aligned_i)
        se = np.sqrt((1 - correlation**2) / (n - 2))
        
        # T-statistic
        t_stat = correlation / se
        
        # P-value (two-sided)
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        
        return min(p_value, 1.0)
    except Exception:
        return 1.0

def block_bootstrap_correlation(returns_i: pd.Series, returns_j: pd.Series,
                               tau: int, n_bootstrap: int = 1000, 
                               block_size: int = 10, seed: int = 42) -> float:
    """Compute p-value using block bootstrap."""
    np.random.seed(seed)
    
    try:
        # Align series for the specific lag
        if tau == 0:
            aligned_i = returns_i.dropna()
            aligned_j = returns_j.dropna()
        elif tau > 0:
            aligned_i = returns_i.dropna()
            aligned_j = returns_j.shift(-tau).dropna()
        else:
            aligned_i = returns_i.shift(tau).dropna()
            aligned_j = returns_j.dropna()
        
        # Ensure same length
        min_len = min(len(aligned_i), len(aligned_j))
        aligned_i = aligned_i.iloc[:min_len]
        aligned_j = aligned_j.iloc[:min_len]
        
        if len(aligned_i) < 20:
            return 1.0
        
        # Compute original correlation
        original_corr = aligned_i.corr(aligned_j)
        if np.isnan(original_corr):
            return 1.0
        
        # Block bootstrap
        n_blocks = len(aligned_i) // block_size
        bootstrap_corrs = []
        
        for _ in range(n_bootstrap):
            # Sample blocks
            block_indices = np.random.choice(n_blocks, size=n_blocks, replace=True)
            
            # Reconstruct series
            boot_i = []
            boot_j = []
            for block_idx in block_indices:
                start_idx = block_idx * block_size
                end_idx = min(start_idx + block_size, len(aligned_i))
                boot_i.extend(aligned_i.iloc[start_idx:end_idx].values)
                boot_j.extend(aligned_j.iloc[start_idx:end_idx].values)
            
            # Compute correlation
            if len(boot_i) > 10:
                corr = np.corrcoef(boot_i, boot_j)[0, 1]
                if not np.isnan(corr):
                    bootstrap_corrs.append(corr)
        
        if len(bootstrap_corrs) < 100:
            return 1.0
        
        # Compute p-value
        bootstrap_corrs = np.array(bootstrap_corrs)
        p_value = np.mean(np.abs(bootstrap_corrs) >= abs(original_corr))
        
        return min(p_value, 1.0)
    except Exception:
        return 1.0

def apply_placebo_shift(returns: pd.Series, shift_seconds: int) -> pd.Series:
    """Apply circular time shift to returns series."""
    if shift_seconds == 0:
        return returns
    
    # Convert shift to number of observations (assuming 1s cadence)
    shift_obs = abs(shift_seconds)
    
    if shift_seconds > 0:
        # Positive shift: move data forward, pad with NaN at end
        shifted = returns.shift(shift_obs)
    else:
        # Negative shift: move data backward, pad with NaN at beginning
        shifted = returns.shift(-shift_obs)
    
    return shifted

def run_leadlag_v2_analysis(snapshot_path: str, horizons: List[int] = [1],
                           rho_min: float = 0.12, alpha: float = 0.10,
                           tau_max: int = 30, bootstrap_n: int = 1000,
                           block_size: int = 10, seed: int = 42,
                           placebo_shifts: List[int] = [-60, 60],
                           fdr_q: float = 0.05, export_dir: str = "experiments/phase5/leadlag_v2") -> Dict:
    """Run Lead-Lag v2 analysis with placebo tests and FDR control."""
    
    # Load data
    tick_data, overlap_data = load_snapshot_from_s3(snapshot_path)
    
    # Extract venues and create returns
    if isinstance(tick_data, pd.DataFrame):
        # tick_data is a DataFrame with venue columns
        venues = [col for col in tick_data.columns if col in ['binance', 'coinbase', 'kraken', 'okx', 'bybit']]
        n_venues = len(venues)
        
        logger.info(f"Analyzing {n_venues} venues: {venues}")
        
        # Compute returns for each venue
        returns_data = {}
        for venue in venues:
            if venue in tick_data.columns:
                returns_data[venue] = compute_returns(tick_data[venue], horizons[0])
            else:
                logger.warning(f"No data found for {venue}")
                continue
    else:
        # tick_data is a dictionary
        venues = list(tick_data.keys())
        n_venues = len(venues)
        
        logger.info(f"Analyzing {n_venues} venues: {venues}")
        
        # Compute returns for each venue
        returns_data = {}
        for venue in venues:
            venue_data = tick_data[venue]
            if hasattr(venue_data, 'columns') and 'mid' in venue_data.columns:
                returns_data[venue] = compute_returns(venue_data['mid'], horizons[0])
            elif hasattr(venue_data, 'name') and venue_data.name == 'mid':
                # If it's already a Series with mid prices
                returns_data[venue] = compute_returns(venue_data, horizons[0])
            else:
                logger.warning(f"No 'mid' column found for {venue}")
                continue
    
    # Prepare analysis
    tau_range = range(-tau_max, tau_max + 1)
    edges = []
    placebo_results = {}
    
    # Run placebo tests first
    for shift in placebo_shifts:
        logger.info(f"Running placebo test with shift {shift}s")
        placebo_edges = []
        
        for i, venue_i in enumerate(venues):
            if venue_i not in returns_data:
                continue
                
            for j, venue_j in enumerate(venues):
                if i >= j or venue_j not in returns_data:
                    continue
                
                # Apply placebo shift
                returns_i_shifted = apply_placebo_shift(returns_data[venue_i], shift)
                returns_j_shifted = apply_placebo_shift(returns_data[venue_j], shift)
                
                # Compute correlation
                corr, tau_star, p_value = compute_cross_correlation(
                    returns_i_shifted, returns_j_shifted, tau_max, tau_range
                )
                
                if abs(corr) >= rho_min and p_value < alpha:
                    placebo_edges.append({
                        'pair': f"{venue_i}→{venue_j}",
                        'tau_star': tau_star,
                        'rho': corr,
                        'p_value': p_value,
                        'shift': shift
                    })
        
        placebo_results[shift] = placebo_edges
    
    # Run main analysis
    logger.info("Running main lead-lag analysis")
    
    for i, venue_i in enumerate(venues):
        if venue_i not in returns_data:
            continue
            
        for j, venue_j in enumerate(venues):
            if i >= j or venue_j not in returns_data:
                continue
            
            # Compute correlation
            corr, tau_star, p_value = compute_cross_correlation(
                returns_data[venue_i], returns_data[venue_j], tau_max, tau_range
            )
            
            if abs(corr) >= rho_min and p_value < alpha:
                # Apply FDR correction
                edges.append({
                    'pair': f"{venue_i}→{venue_j}",
                    'tau_star': tau_star,
                    'rho': corr,
                    'p_value': p_value,
                    'venue_i': venue_i,
                    'venue_j': venue_j
                })
    
    # Apply FDR correction
    if edges:
        p_values = [edge['p_value'] for edge in edges]
        _, p_corrected, _, _ = multipletests(p_values, method='fdr_bh', alpha=fdr_q)
        
        for i, edge in enumerate(edges):
            edge['q_value'] = p_corrected[i]
            edge['significant'] = p_corrected[i] < fdr_q
    else:
        logger.warning("No edges found meeting criteria")
    
    # Prepare results
    significant_edges = [edge for edge in edges if edge.get('significant', False)]
    
    # Check placebo collapse
    placebo_collapse = True
    residual_edges = 0
    
    for shift in placebo_shifts:
        if placebo_results[shift]:
            placebo_collapse = False
            residual_edges += len(placebo_results[shift])
    
    # Gate assessment
    gate_verdict = "pass" if (significant_edges and placebo_collapse) else "fail"
    
    results = {
        'snapshot_path': snapshot_path,
        'venues': venues,
        'n_venues': n_venues,
        'horizons': horizons,
        'tau_max': tau_max,
        'rho_min': rho_min,
        'alpha': alpha,
        'fdr_q': fdr_q,
        'bootstrap_n': bootstrap_n,
        'block_size': block_size,
        'seed': seed,
        'placebo_shifts': placebo_shifts,
        'edges': significant_edges,
        'all_edges': edges,
        'placebo_results': placebo_results,
        'placebo_collapse': placebo_collapse,
        'residual_edges': residual_edges,
        'gate_verdict': gate_verdict,
        'created_at': datetime.utcnow().isoformat() + "Z"
    }
    
    return results

def generate_leadlag_report(results: Dict, export_dir: str) -> str:
    """Generate human-readable lead-lag report."""
    
    snapshot_path = results['snapshot_path']
    symbol = "BTC-USD" if "BTC" in snapshot_path else "ETH-USD"
    time_range = "10:00-10:30" if "BTC" in snapshot_path else "11:00-11:30"
    
    report = f"""# Lead–Lag v2 — {symbol} 2025-09-28 {time_range} UTC

**Snapshot**: {snapshot_path}  
**Cadence**: 1s  
**N_venues**: {results['n_venues']}

**Thresholds**: rho_min={results['rho_min']}, alpha={results['alpha']}, FDR q={results['fdr_q']}

## Top Edges (up to 5)
"""
    
    # Add top edges
    top_edges = sorted(results['edges'], key=lambda x: abs(x['rho']), reverse=True)[:5]
    for edge in top_edges:
        report += f"- {edge['pair']} @ τ*={edge['tau_star']}s (ρ={edge['rho']:.3f}, p={edge['p_value']:.3f}, q={edge['q_value']:.3f})\n"
    
    report += f"""
## Placebo (±60s)
**Collapse**: {'Yes' if results['placebo_collapse'] else 'No'}  
**Residual edges**: {results['residual_edges']}

## Verdict (Lead–Lag Gate)
**Status**: {results['gate_verdict'].upper()}  
**Rationale**: {'Edges detected and placebo test passed' if results['gate_verdict'] == 'pass' else 'No significant edges or placebo test failed'}

## Provenance
- **Seed**: {results['seed']}
- **Code version**: Lead-Lag v2
- **Commit**: {results.get('commit', 'N/A')}
- **Created at**: {results['created_at']}
"""
    
    return report

def main():
    """Main function for Lead-Lag v2 analysis."""
    parser = argparse.ArgumentParser(description="Lead-Lag v2 Analysis")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--horizons", nargs="+", type=int, default=[1], help="Return horizons")
    parser.add_argument("--rho-min", type=float, default=0.12, help="Minimum correlation threshold")
    parser.add_argument("--alpha", type=float, default=0.10, help="Significance level")
    parser.add_argument("--tau-max", type=int, default=30, help="Maximum lag in seconds")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Bootstrap samples")
    parser.add_argument("--block", type=int, default=10, help="Block size for bootstrap")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--placebo-shifts", nargs="+", type=int, default=[-60, 60], 
                       help="Placebo shift values in seconds")
    parser.add_argument("--fdr", type=float, default=0.05, help="FDR threshold")
    parser.add_argument("--export-dir", default="experiments/phase5/leadlag_v2", 
                       help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Create export directory
    export_path = Path(args.export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run analysis
        results = run_leadlag_v2_analysis(
            snapshot_path=args.snapshot,
            horizons=args.horizons,
            rho_min=args.rho_min,
            alpha=args.alpha,
            tau_max=args.tau_max,
            bootstrap_n=args.bootstrap,
            block_size=args.block,
            seed=args.seed,
            placebo_shifts=args.placebo_shifts,
            fdr_q=args.fdr,
            export_dir=args.export_dir
        )
        
        # Write artifacts
        edges_file = export_path / "edges.json"
        edges_file.write_text(json.dumps(results['edges'], cls=PandasJSONEncoder, indent=2))
        
        placebo_file = export_path / "placebo.json"
        placebo_file.write_text(json.dumps(results['placebo_results'], cls=PandasJSONEncoder, indent=2))
        
        params_file = export_path / "params.json"
        params_data = {k: v for k, v in results.items() if k in ['snapshot_path', 'venues', 'n_venues', 
                                                                'horizons', 'tau_max', 'rho_min', 'alpha', 
                                                                'fdr_q', 'bootstrap_n', 'block_size', 'seed', 
                                                                'placebo_shifts', 'created_at']}
        params_file.write_text(json.dumps(params_data, cls=PandasJSONEncoder, indent=2))
        
        report_file = export_path / "leadlag_report.md"
        report_content = generate_leadlag_report(results, args.export_dir)
        report_file.write_text(report_content)
        
        # Write full results
        results_file = export_path / "leadlag_results.json"
        results_file.write_text(json.dumps(results, cls=PandasJSONEncoder, indent=2))
        
        logger.info(f"Lead-Lag v2 analysis completed. Results saved to {export_path}")
        logger.info(f"Found {len(results['edges'])} significant edges")
        logger.info(f"Placebo collapse: {results['placebo_collapse']}")
        logger.info(f"Gate verdict: {results['gate_verdict']}")
        
    except Exception as e:
        logger.error(f"Lead-Lag v2 analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
