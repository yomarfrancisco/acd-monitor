#!/usr/bin/env python3
"""
Debug script to check synthetic data generation
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd
import numpy as np

from acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig


def debug_data():
    """Debug synthetic data generation"""

    print("Debugging synthetic data generation...")

    config = CryptoMarketConfig(n_timepoints=100, n_exchanges=3)
    generator = SyntheticCryptoGenerator(config)

    competitive_data = generator.generate_competitive_scenario()

    print(f"Data shape: {competitive_data.shape}")
    print(f"Columns: {list(competitive_data.columns)}")
    print(f"Data types: {competitive_data.dtypes}")
    print(f"Missing values: {competitive_data.isnull().sum()}")

    # Check specific columns
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]
    print(f"Price columns: {price_cols}")

    for col in price_cols:
        print(f"{col}: {competitive_data[col].isnull().sum()} missing values")

    # Check environment columns
    env_cols = ["scenario_type", "volatility_regime", "market_condition"]
    for col in env_cols:
        if col in competitive_data.columns:
            print(f"{col}: {competitive_data[col].isnull().sum()} missing values")
            print(f"{col} unique values: {competitive_data[col].unique()}")

    # Check for any remaining missing values
    total_missing = competitive_data.isnull().sum().sum()
    print(f"Total missing values: {total_missing}")

    if total_missing > 0:
        print("Missing value locations:")
        print(competitive_data.isnull().sum())


if __name__ == "__main__":
    debug_data()
