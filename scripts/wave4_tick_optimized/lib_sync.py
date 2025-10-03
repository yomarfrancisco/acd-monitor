"""
Large Trade Synchronization Analysis (Vectorized).
Implements H1: Large trades cluster across venues within ±50–250ms more than baseline.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def identify_large_trades(df: pd.DataFrame, percentile: float = 95.0) -> pd.DataFrame:
    """Identify large trades as top percentile by size."""
    if df.empty:
        return df

    threshold = df["base_amount"].quantile(percentile / 100)
    large_trades = df[df["base_amount"] >= threshold].copy()

    logger.info(f"Identified {len(large_trades):,} large trades (≥{threshold:.4f})")
    return large_trades


def create_sync_vectors(large_trades: pd.DataFrame, bin_size_ms: int = 50) -> np.ndarray:
    """Create binary vectors for large trade synchronization analysis."""
    if large_trades.empty:
        return np.array([])

    # Get time range
    min_bin = large_trades["bin50"].min()
    max_bin = large_trades["bin50"].max()

    # Create binary vector
    sync_vector = np.zeros(int(max_bin - min_bin + 1), dtype=int)

    for _, trade in large_trades.iterrows():
        bin_idx = int(trade["bin50"] - min_bin)
        sync_vector[bin_idx] = 1

    return sync_vector


def compute_sync_correlation(vec1: np.ndarray, vec2: np.ndarray, max_lag: int = 5) -> Dict:
    """Compute cross-correlation between sync vectors with lags."""
    if len(vec1) == 0 or len(vec2) == 0:
        return {"max_correlation": 0.0, "max_lag": 0, "lags": [], "correlations": []}

    # Ensure same length
    min_len = min(len(vec1), len(vec2))
    vec1 = vec1[:min_len]
    vec2 = vec2[:min_len]

    # Compute cross-correlation
    correlations = []
    lags = []

    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            corr = np.corrcoef(vec1, vec2)[0, 1]
        elif lag > 0:
            if len(vec1) > lag:
                corr = np.corrcoef(vec1[:-lag], vec2[lag:])[0, 1]
            else:
                corr = 0.0
        else:  # lag < 0
            if len(vec2) > abs(lag):
                corr = np.corrcoef(vec1[abs(lag) :], vec2[: -abs(lag)])[0, 1]
            else:
                corr = 0.0

        correlations.append(corr if not np.isnan(corr) else 0.0)
        lags.append(lag)

    max_idx = np.argmax(np.abs(correlations))
    max_correlation = correlations[max_idx]
    max_lag = lags[max_idx]

    return {
        "max_correlation": float(max_correlation),
        "max_lag": int(max_lag),
        "lags": lags,
        "correlations": correlations,
    }


def bootstrap_sync_baseline(vec1: np.ndarray, vec2: np.ndarray, n_bootstrap: int = 200) -> Dict:
    """Bootstrap baseline for synchronization analysis."""
    if len(vec1) == 0 or len(vec2) == 0:
        return {"mean_correlation": 0.0, "std_correlation": 0.0, "p_value": 1.0}

    # Block bootstrap (5-minute blocks)
    block_size = 6000  # 5 minutes in 50ms bins
    correlations = []

    for _ in range(n_bootstrap):
        # Resample blocks
        n_blocks1 = max(1, len(vec1) // block_size)
        n_blocks2 = max(1, len(vec2) // block_size)

        # Sample blocks with replacement
        sampled_blocks1 = np.random.choice(n_blocks1, n_blocks1, replace=True)
        sampled_blocks2 = np.random.choice(n_blocks2, n_blocks2, replace=True)

        # Reconstruct vectors
        boot_vec1 = np.concatenate(
            [vec1[i * block_size : (i + 1) * block_size] for i in sampled_blocks1]
        )
        boot_vec2 = np.concatenate(
            [vec2[i * block_size : (i + 1) * block_size] for i in sampled_blocks2]
        )

        # Compute correlation
        if len(boot_vec1) > 0 and len(boot_vec2) > 0:
            corr = np.corrcoef(
                boot_vec1[: min(len(boot_vec1), len(boot_vec2))],
                boot_vec2[: min(len(boot_vec1), len(boot_vec2))],
            )[0, 1]
            if not np.isnan(corr):
                correlations.append(corr)

    if not correlations:
        return {"mean_correlation": 0.0, "std_correlation": 0.0, "p_value": 1.0}

    mean_corr = np.mean(correlations)
    std_corr = np.std(correlations)

    return {
        "mean_correlation": float(mean_corr),
        "std_correlation": float(std_corr),
        "correlations": correlations,
    }


def analyze_large_trade_sync(
    venue1_data: pd.DataFrame, venue2_data: pd.DataFrame, venue1_name: str, venue2_name: str
) -> Dict:
    """Analyze large trade synchronization between two venues."""
    logger.info(f"Analyzing sync between {venue1_name} and {venue2_name}")

    # Identify large trades
    large_trades1 = identify_large_trades(venue1_data)
    large_trades2 = identify_large_trades(venue2_data)

    if large_trades1.empty or large_trades2.empty:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO DATA FOUND",
            "large_trades1": 0,
            "large_trades2": 0,
        }

    # Create sync vectors
    sync_vec1 = create_sync_vectors(large_trades1)
    sync_vec2 = create_sync_vectors(large_trades2)

    if len(sync_vec1) == 0 or len(sync_vec2) == 0:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO SYNC VECTORS",
            "large_trades1": len(large_trades1),
            "large_trades2": len(large_trades2),
        }

    # Compute synchronization
    sync_results = compute_sync_correlation(sync_vec1, sync_vec2)

    # Bootstrap baseline
    bootstrap_results = bootstrap_sync_baseline(sync_vec1, sync_vec2)

    # Calculate p-value
    observed_corr = sync_results["max_correlation"]
    bootstrap_corrs = bootstrap_results["correlations"]
    p_value = np.mean([abs(corr) >= abs(observed_corr) for corr in bootstrap_corrs])

    return {
        "venue1": venue1_name,
        "venue2": venue2_name,
        "status": "SUCCESS",
        "large_trades1": len(large_trades1),
        "large_trades2": len(large_trades2),
        "observed_correlation": observed_corr,
        "max_lag": sync_results["max_lag"],
        "bootstrap_mean": bootstrap_results["mean_correlation"],
        "bootstrap_std": bootstrap_results["std_correlation"],
        "sync_ratio": (
            observed_corr / bootstrap_results["mean_correlation"]
            if bootstrap_results["mean_correlation"] != 0
            else 0
        ),
        "p_value": p_value,
        "significant": p_value < 0.05,
    }
