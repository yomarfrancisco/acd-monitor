#!/usr/bin/env python3
"""
Generate Golden Datasets for VMM Testing
Creates synthetic competitive and coordinated datasets for acceptance testing
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd


def generate_competitive_data(
    n_windows: int = 50, window_size: int = 100, n_firms: int = 3, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic competitive data where betas vary with environment

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of competing firms
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames, each representing a window
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base prices with competitive dynamics
        base_prices = np.random.normal(100, 10, (window_size, n_firms))

        # Add environment-dependent competitive responses
        for t in range(window_size):
            # Simulate different competitive environments
            if t < window_size // 3:
                # High competition period
                competitive_factor = 1.5
            elif t < 2 * window_size // 3:
                # Medium competition period
                competitive_factor = 1.0
            else:
                # Low competition period
                competitive_factor = 0.5

            # Firms respond competitively to each other
            for i in range(n_firms):
                for j in range(n_firms):
                    if i != j:
                        # Competitive response: firm i responds to firm j's price
                        response = np.random.normal(0, 2) * competitive_factor
                        base_prices[t, i] += response * (base_prices[t, j] - 100) / 100

        # Add noise
        noise = np.random.normal(0, 1, (window_size, n_firms))
        prices = base_prices + noise

        # Create DataFrame
        df = pd.DataFrame(prices, columns=[f"firm_{i}_price" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_coordinated_data(
    n_windows: int = 50, window_size: int = 100, n_firms: int = 3, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic coordinated data where betas remain invariant

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of coordinating firms
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames, each representing a window
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base prices with coordination
        base_prices = np.random.normal(100, 10, (window_size, n_firms))

        # Add coordinated behavior
        for t in range(window_size):
            # Common market factor affecting all firms
            market_factor = np.random.normal(0, 3)

            # Firms move together in response to market factor
            for i in range(n_firms):
                base_prices[t, i] += market_factor * 0.8

        # Add noise
        noise = np.random.normal(0, 1, (window_size, n_firms))
        prices = base_prices + noise

        # Create DataFrame
        df = pd.DataFrame(prices, columns=[f"firm_{i}_price" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_leader_follower_data(
    n_windows: int = 25, window_size: int = 100, n_firms: int = 3, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic data with leader-follower coordination dynamics.

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of firms (first firm is leader)
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames with leader-follower dynamics
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base prices
        base_prices = np.random.normal(100, 10, (window_size, n_firms))

        # Leader-follower dynamics
        for t in range(window_size):
            # Leader makes independent moves
            if t > 0:
                leader_move = np.random.normal(0, 2)
                base_prices[t, 0] += leader_move

            # Followers react to leader with delay
            for i in range(1, n_firms):
                if t >= 2:  # 2-period delay for followers
                    # Followers copy leader's move with some variation
                    follower_response = base_prices[t - 2, 0] - base_prices[t - 3, 0]
                    base_prices[t, i] += follower_response * 0.7 + np.random.normal(0, 0.5)

        # Add noise
        noise = np.random.normal(0, 1, (window_size, n_firms))
        prices = base_prices + noise

        # Create DataFrame
        df = pd.DataFrame(prices, columns=[f"firm_{i}_price" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_staggered_reaction_data(
    n_windows: int = 25, window_size: int = 100, n_firms: int = 3, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic data with staggered reaction coordination.

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of firms
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames with staggered reaction dynamics
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base prices
        base_prices = np.random.normal(100, 10, (window_size, n_firms))

        # Staggered reaction dynamics
        for t in range(window_size):
            # Common market shock at specific times
            if t % 20 == 0:  # Every 20 periods
                market_shock = np.random.normal(0, 5)

                # Firms react in sequence with different delays
                for i in range(n_firms):
                    delay = i * 3  # Firm i reacts after i*3 periods
                    if t + delay < window_size:
                        base_prices[t + delay, i] += market_shock * (0.8 - i * 0.1)

        # Add noise
        noise = np.random.normal(0, 1, (window_size, n_firms))
        prices = base_prices + noise

        # Create DataFrame
        df = pd.DataFrame(prices, columns=[f"firm_{i}_price" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_cds_spread_data(
    n_windows: int = 20, window_size: int = 100, n_firms: int = 3, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic CDS spread data based on real-world patterns.

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of firms
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames with CDS spread dynamics
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base CDS spreads (in basis points)
        base_spreads = np.random.normal(150, 50, (window_size, n_firms))

        # Add market-wide credit risk factors
        for t in range(window_size):
            # Market-wide credit cycle
            credit_cycle = 20 * np.sin(2 * np.pi * t / window_size)

            # Systemic risk factor
            systemic_risk = np.random.normal(0, 10)

            # Apply to all firms
            for i in range(n_firms):
                base_spreads[t, i] += credit_cycle + systemic_risk

        # Add noise
        noise = np.random.normal(0, 5, (window_size, n_firms))
        spreads = base_spreads + noise

        # Ensure positive spreads
        spreads = np.maximum(spreads, 10)

        # Create DataFrame
        df = pd.DataFrame(spreads, columns=[f"firm_{i}_cds" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_sa_bank_competition_data(
    n_windows: int = 20, window_size: int = 100, n_firms: int = 4, seed: int = 42
) -> List[pd.DataFrame]:
    """
    Generate synthetic South African bank competition data.

    Args:
        n_windows: Number of data windows to generate
        window_size: Number of observations per window
        n_firms: Number of banks
        seed: Random seed for reproducibility

    Returns:
        List of DataFrames with SA bank competition dynamics
    """
    np.random.seed(seed)

    windows = []

    for window_idx in range(n_windows):
        # Create time index
        start_date = datetime(2024, 1, 1) + timedelta(days=window_idx * 7)
        dates = [start_date + timedelta(hours=i) for i in range(window_size)]

        # Generate base lending rates
        base_rates = np.random.normal(8.5, 1.0, (window_size, n_firms))

        # Add competitive dynamics
        for t in range(window_size):
            # Market leader (first bank) sets rate
            if t > 0:
                market_condition = np.random.normal(0, 0.2)
                base_rates[t, 0] += market_condition

            # Other banks follow with slight variations
            for i in range(1, n_firms):
                if t > 0:
                    # Follow leader with competitive pressure
                    leader_change = base_rates[t, 0] - base_rates[t - 1, 0]
                    competitive_adjustment = leader_change * 0.8 + np.random.normal(0, 0.1)
                    base_rates[t, i] += competitive_adjustment

        # Add noise
        noise = np.random.normal(0, 0.1, (window_size, n_firms))
        rates = base_rates + noise

        # Create DataFrame
        df = pd.DataFrame(rates, columns=[f"bank_{i}_rate" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def generate_enhanced_golden_datasets(seed: int = 42) -> Dict[str, List[pd.DataFrame]]:
    """
    Generate enhanced golden datasets with multiple coordination mechanisms.

    Args:
        seed: Random seed for reproducibility

    Returns:
        Dictionary containing all dataset types
    """
    datasets = {}

    # Original competitive and coordinated datasets
    datasets["competitive"] = generate_competitive_data(seed=seed)
    datasets["coordinated"] = generate_coordinated_data(seed=seed)

    # New coordination mechanism datasets
    datasets["leader_follower"] = generate_leader_follower_data(seed=seed)
    datasets["staggered_reaction"] = generate_staggered_reaction_data(seed=seed)

    # Real-world reference datasets
    datasets["cds_spreads"] = generate_cds_spread_data(seed=seed)
    datasets["sa_bank_competition"] = generate_sa_bank_competition_data(seed=seed)

    return datasets


def save_golden_datasets(
    datasets: Dict[str, List[pd.DataFrame]], output_dir: str = "golden_datasets"
) -> None:
    """
    Save golden datasets to disk.

    Args:
        datasets: Dictionary of datasets to save
        output_dir: Output directory for datasets
    """
    os.makedirs(output_dir, exist_ok=True)

    for dataset_type, windows in datasets.items():
        dataset_dir = os.path.join(output_dir, dataset_type)
        os.makedirs(dataset_dir, exist_ok=True)

        for i, window in enumerate(windows):
            filename = f"{dataset_type}_window_{i:03d}.csv"
            filepath = os.path.join(dataset_dir, filename)
            window.to_csv(filepath)

        print(f"Saved {len(windows)} {dataset_type} windows to {dataset_dir}/")


def generate_validation_metrics(datasets: Dict[str, List[pd.DataFrame]]) -> Dict[str, float]:
    """
    Generate validation metrics for golden datasets.

    Args:
        datasets: Dictionary of datasets

    Returns:
        Dictionary of validation metrics
    """
    metrics = {}

    for dataset_type, windows in datasets.items():
        # Calculate basic statistics
        all_prices = []
        for window in windows:
            price_cols = [
                col for col in window.columns if "price" in col or "cds" in col or "rate" in col
            ]
            all_prices.extend(window[price_cols].values.flatten())

        metrics[f"{dataset_type}_mean"] = np.mean(all_prices)
        metrics[f"{dataset_type}_std"] = np.std(all_prices)
        metrics[f"{dataset_type}_count"] = len(windows)

    return metrics


if __name__ == "__main__":
    # Generate enhanced golden datasets
    print("Generating enhanced golden datasets...")
    datasets = generate_enhanced_golden_datasets(seed=42)

    # Save datasets
    save_golden_datasets(datasets)

    # Generate validation metrics
    metrics = generate_validation_metrics(datasets)

    # Save metrics
    with open("golden_datasets/validation_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Generated {sum(len(windows) for windows in datasets.values())} total windows")
    print("Validation metrics saved to golden_datasets/validation_metrics.json")
