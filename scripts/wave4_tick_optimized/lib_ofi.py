"""
OFI (Order Flow Imbalance) Spike Analysis (Vectorized).
Implements H2: OFI spikes co-occur across venues within ±250ms above baseline.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_ofi(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Order Flow Imbalance from tick data."""
    if df.empty:
        return df

    # Method 1: Use taker_side if available
    if "taker_side" in df.columns:
        signed_volumes = np.where(df["taker_side"] == "BUY", df["base_amount"], -df["base_amount"])
        df["ofi"] = signed_volumes
    else:
        # Method 2: Use price change proxy
        price_changes = df["price"].diff()
        df["ofi"] = np.sign(price_changes) * df["base_amount"]

    return df


def aggregate_ofi_by_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate OFI by 100ms bins for spike analysis."""
    if df.empty:
        return df

    # Group by 100ms bins and sum OFI
    ofi_bins = (
        df.groupby("bin100")
        .agg({"ofi": "sum", "time_exchange": "last", "price": "last"})
        .reset_index()
    )

    return ofi_bins


def identify_ofi_spikes(ofi_bins: pd.DataFrame, percentile: float = 99.0) -> pd.DataFrame:
    """Identify OFI spikes as top percentile of absolute OFI."""
    if ofi_bins.empty:
        return ofi_bins

    threshold = ofi_bins["ofi"].abs().quantile(percentile / 100)
    spikes = ofi_bins[ofi_bins["ofi"].abs() >= threshold].copy()

    logger.info(f"Identified {len(spikes):,} OFI spikes (≥{threshold:.4f})")
    return spikes


def create_spike_vectors(spikes: pd.DataFrame) -> np.ndarray:
    """Create binary vectors for OFI spike analysis."""
    if spikes.empty:
        return np.array([])

    # Get time range
    min_bin = spikes["bin100"].min()
    max_bin = spikes["bin100"].max()

    # Create binary vector
    spike_vector = np.zeros(int(max_bin - min_bin + 1), dtype=int)

    for _, spike in spikes.iterrows():
        bin_idx = int(spike["bin100"] - min_bin)
        spike_vector[bin_idx] = 1

    return spike_vector


def compute_spike_correlation(vec1: np.ndarray, vec2: np.ndarray, max_lag: int = 10) -> Dict:
    """Compute cross-correlation between spike vectors with lags."""
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


def bootstrap_spike_baseline(vec1: np.ndarray, vec2: np.ndarray, n_bootstrap: int = 200) -> Dict:
    """Bootstrap baseline for OFI spike analysis."""
    if len(vec1) == 0 or len(vec2) == 0:
        return {"mean_correlation": 0.0, "std_correlation": 0.0, "p_value": 1.0}

    # Block bootstrap (5-minute blocks)
    block_size = 3000  # 5 minutes in 100ms bins
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


def analyze_ofi_spikes(
    venue1_data: pd.DataFrame, venue2_data: pd.DataFrame, venue1_name: str, venue2_name: str
) -> Dict:
    """Analyze OFI spike co-occurrence between two venues."""
    logger.info(f"Analyzing OFI spikes between {venue1_name} and {venue2_name}")

    # Calculate OFI
    ofi_data1 = calculate_ofi(venue1_data)
    ofi_data2 = calculate_ofi(venue2_data)

    if ofi_data1.empty or ofi_data2.empty:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO DATA FOUND",
            "ofi_bins1": 0,
            "ofi_bins2": 0,
        }

    # Aggregate by bins
    ofi_bins1 = aggregate_ofi_by_bins(ofi_data1)
    ofi_bins2 = aggregate_ofi_by_bins(ofi_data2)

    if ofi_bins1.empty or ofi_bins2.empty:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO OFI BINS",
            "ofi_bins1": len(ofi_bins1),
            "ofi_bins2": len(ofi_bins2),
        }

    # Identify spikes
    spikes1 = identify_ofi_spikes(ofi_bins1)
    spikes2 = identify_ofi_spikes(ofi_bins2)

    if spikes1.empty or spikes2.empty:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO SPIKES",
            "spikes1": len(spikes1),
            "spikes2": len(spikes2),
        }

    # Create spike vectors
    spike_vec1 = create_spike_vectors(spikes1)
    spike_vec2 = create_spike_vectors(spikes2)

    if len(spike_vec1) == 0 or len(spike_vec2) == 0:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO SPIKE VECTORS",
            "spikes1": len(spikes1),
            "spikes2": len(spikes2),
        }

    # Compute spike correlation
    spike_results = compute_spike_correlation(spike_vec1, spike_vec2)

    # Bootstrap baseline
    bootstrap_results = bootstrap_spike_baseline(spike_vec1, spike_vec2)

    # Calculate p-value
    observed_corr = spike_results["max_correlation"]
    bootstrap_corrs = bootstrap_results["correlations"]
    p_value = np.mean([abs(corr) >= abs(observed_corr) for corr in bootstrap_corrs])

    return {
        "venue1": venue1_name,
        "venue2": venue2_name,
        "status": "SUCCESS",
        "ofi_bins1": len(ofi_bins1),
        "ofi_bins2": len(ofi_bins2),
        "spikes1": len(spikes1),
        "spikes2": len(spikes2),
        "observed_correlation": observed_corr,
        "max_lag": spike_results["max_lag"],
        "bootstrap_mean": bootstrap_results["mean_correlation"],
        "bootstrap_std": bootstrap_results["std_correlation"],
        "spike_ratio": (
            observed_corr / bootstrap_results["mean_correlation"]
            if bootstrap_results["mean_correlation"] != 0
            else 0
        ),
        "p_value": p_value,
        "significant": p_value < 0.05,
    }
