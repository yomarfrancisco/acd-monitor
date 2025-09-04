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

        # Generate base prices with coordinated dynamics
        base_prices = np.random.normal(100, 10, (window_size, n_firms))

        # Add invariant coordinated responses (same across all environments)
        for t in range(window_size):
            # Coordinated response: firms maintain stable relationships
            for i in range(n_firms):
                for j in range(n_firms):
                    if i != j:
                        # Fixed coordination parameter (invariant to environment)
                        coordination_param = 0.8  # Fixed across all environments
                        response = coordination_param * (base_prices[t, j] - 100) / 100
                        base_prices[t, i] += response

        # Add noise
        noise = np.random.normal(0, 1, (window_size, n_firms))
        prices = base_prices + noise

        # Create DataFrame
        df = pd.DataFrame(prices, columns=[f"firm_{i}_price" for i in range(n_firms)])
        df["timestamp"] = dates
        df.set_index("timestamp", inplace=True)

        windows.append(df)

    return windows


def save_windows(windows: List[pd.DataFrame], output_dir: str, prefix: str) -> List[Dict]:
    """
    Save windows to parquet files and return metadata

    Args:
        windows: List of DataFrames to save
        output_dir: Directory to save files
        prefix: Prefix for filenames

    Returns:
        List of metadata dictionaries
    """
    os.makedirs(output_dir, exist_ok=True)

    metadata = []

    for i, window in enumerate(windows):
        filename = f"{prefix}_window_{i:03d}.parquet"
        filepath = os.path.join(output_dir, filename)

        # Save to parquet
        window.to_parquet(filepath)

        # Compute basic stats
        stats = {
            "filename": filename,
            "window_id": i,
            "n_observations": len(window),
            "n_firms": len([col for col in window.columns if "price" in col]),
            "start_timestamp": window.index[0].isoformat(),
            "end_timestamp": window.index[-1].isoformat(),
            "price_range": {
                col: {"min": float(window[col].min()), "max": float(window[col].max())}
                for col in window.columns
                if "price" in col
            },
        }

        metadata.append(stats)

    return metadata


def create_manifest(
    competitive_metadata: List[Dict], coordinated_metadata: List[Dict], output_path: str
) -> None:
    """
    Create manifest file with dataset information

    Args:
        competitive_metadata: Metadata for competitive windows
        coordinated_metadata: Metadata for coordinated windows
        output_path: Path to save manifest
    """
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "description": "Golden datasets for VMM acceptance testing",
        "datasets": {
            "competitive": {
                "description": "Synthetic competitive data (environment-dependent betas)",
                "n_windows": len(competitive_metadata),
                "windows": competitive_metadata,
            },
            "coordinated": {
                "description": "Synthetic coordinated data (invariant betas)",
                "n_windows": len(coordinated_metadata),
                "windows": coordinated_metadata,
            },
        },
        "acceptance_criteria": {
            "spurious_regime_rate": 0.05,  # ≤ 5% on competitive golden set
            "reproducibility_drift": 0.03,  # |Δstructural_stability| ≤ 0.03
            "regime_confidence_threshold": 0.67,  # Threshold for regime detection
        },
    }

    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    """Generate golden datasets for VMM testing"""
    print("Generating golden datasets for VMM acceptance testing...")

    # Configuration
    n_windows = 50
    window_size = 100
    n_firms = 3

    # Generate competitive data
    print(f"Generating {n_windows} competitive windows...")
    competitive_windows = generate_competitive_data(
        n_windows=n_windows, window_size=window_size, n_firms=n_firms, seed=42
    )

    # Generate coordinated data
    print(f"Generating {n_windows} coordinated windows...")
    coordinated_windows = generate_coordinated_data(
        n_windows=n_windows, window_size=window_size, n_firms=n_firms, seed=42
    )

    # Save competitive data
    competitive_dir = "data/golden/competitive"
    print(f"Saving competitive data to {competitive_dir}...")
    competitive_metadata = save_windows(competitive_windows, competitive_dir, "competitive")

    # Save coordinated data
    coordinated_dir = "data/golden/coordinated"
    print(f"Saving coordinated data to {coordinated_dir}...")
    coordinated_metadata = save_windows(coordinated_windows, coordinated_dir, "coordinated")

    # Create manifest
    manifest_path = "data/golden/manifest.json"
    print(f"Creating manifest at {manifest_path}...")
    create_manifest(competitive_metadata, coordinated_metadata, manifest_path)

    print("Golden dataset generation complete!")
    print(f"Competitive windows: {len(competitive_windows)}")
    print(f"Coordinated windows: {len(coordinated_windows)}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
