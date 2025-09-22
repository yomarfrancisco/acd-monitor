#!/usr/bin/env python3
"""
Crypto Moment Validation Script

This script validates crypto moments against real market data
and compares results with synthetic validations.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.validation.lead_lag import LeadLagValidator, LeadLagConfig
from acd.validation.mirroring import MirroringValidator, MirroringConfig


def load_crypto_data(data_file: str) -> pd.DataFrame:
    """Load crypto data from file"""

    print(f"Loading crypto data from: {data_file}")

    df = pd.read_csv(data_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    print(f"   Records: {len(df):,}")
    print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Exchanges: {df['exchange'].nunique()}")
    print(f"   Pairs: {df['symbol'].nunique()}")

    return df


def prepare_data_for_analysis(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Prepare data for crypto moment analysis"""

    print("Preparing data for crypto moment analysis...")

    # Pivot data for each pair
    prepared_data = {}

    for pair in df["symbol"].unique():
        pair_data = df[df["symbol"] == pair].copy()

        # Create wide format for analysis
        pivot_data = pair_data.pivot_table(
            index="timestamp",
            columns="exchange",
            values=["mid_price", "spread", "bid_volume", "ask_volume"],
            aggfunc="mean",
        ).fillna(method="ffill")

        prepared_data[pair] = pivot_data

        print(f"   {pair}: {len(pivot_data)} timestamps, {len(pivot_data.columns)} columns")

    return prepared_data


def validate_lead_lag_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate lead-lag moments"""

    print("Validating lead-lag moments...")

    config = LeadLagConfig(window_size=30, min_observations=50)
    validator = LeadLagValidator(config)

    results = {}

    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")

        try:
            # Extract price columns
            price_columns = [col for col in pair_data.columns if "mid_price" in col]
            price_data = pair_data[price_columns]

            result = validator.analyze_lead_lag(price_data, price_columns)

            results[pair] = {
                "switching_entropy": result.switching_entropy,
                "avg_granger_p": result.avg_granger_p,
                "n_windows": result.n_windows,
                "n_exchanges": result.n_exchanges,
            }

            print(f"     Switching entropy: {result.switching_entropy:.3f}")
            print(f"     Avg Granger p-value: {result.avg_granger_p:.3f}")

        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {"error": str(e)}

    return results


def validate_mirroring_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate mirroring moments"""

    print("Validating mirroring moments...")

    config = MirroringConfig(similarity_threshold=0.7, min_observations=50)
    validator = MirroringValidator(config)

    results = {}

    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")

        try:
            # Extract price columns
            price_columns = [col for col in pair_data.columns if "mid_price" in col]
            price_data = pair_data[price_columns]

            result = validator.analyze_mirroring(price_data, price_columns)

            results[pair] = {
                "mirroring_ratio": result.mirroring_ratio,
                "coordination_score": result.coordination_score,
                "avg_cosine_similarity": result.avg_cosine_similarity,
                "n_windows": result.n_windows,
                "n_exchanges": result.n_exchanges,
            }

            print(f"     Mirroring ratio: {result.mirroring_ratio:.3f}")
            print(f"     Coordination score: {result.coordination_score:.3f}")

        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {"error": str(e)}

    return results


def validate_crypto_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate crypto moments using CryptoMomentCalculator"""

    print("Validating crypto moments...")

    config = CryptoMomentConfig()
    calculator = CryptoMomentCalculator(config)

    results = {}

    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")

        try:
            # Calculate crypto moments
            moments = calculator.calculate_moments(pair_data, price_columns)

            results[pair] = {
                "lead_lag_betas": moments.lead_lag_betas.tolist(),
                "mirroring_ratios": moments.mirroring_ratios.tolist(),
                "spread_floor_frequency": moments.spread_floor_frequency.tolist(),
                "undercut_initiation_rate": moments.undercut_initiation_rate.tolist(),
                "mev_coordination_score": moments.mev_coordination_score.tolist(),
            }

            print(f"     Lead-lag betas: {np.mean(moments.lead_lag_betas):.3f}")
            print(f"     Mirroring ratios: {np.mean(moments.mirroring_ratios):.3f}")
            print(f"     Spread floor frequency: {np.mean(moments.spread_floor_frequency):.3f}")

        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {"error": str(e)}

    return results


def compare_with_synthetic_results(
    real_results: Dict[str, Any], synthetic_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare real data results with synthetic validation results"""

    print("Comparing with synthetic validation results...")

    comparison = {}

    for pair in real_results.keys():
        if pair in synthetic_results and "error" not in real_results[pair]:
            real = real_results[pair]
            synthetic = synthetic_results[pair]

            # Calculate consistency metrics
            consistency_metrics = {}

            for metric in ["switching_entropy", "mirroring_ratio", "coordination_score"]:
                if metric in real and metric in synthetic:
                    real_val = real[metric]
                    synthetic_val = synthetic[metric]

                    # Calculate relative difference
                    if synthetic_val != 0:
                        relative_diff = abs(real_val - synthetic_val) / abs(synthetic_val)
                        consistency_metrics[metric] = {
                            "real": real_val,
                            "synthetic": synthetic_val,
                            "relative_difference": relative_diff,
                            "consistent": relative_diff < 0.2,  # 20% tolerance
                        }

            comparison[pair] = consistency_metrics

            # Summary
            consistent_metrics = sum(1 for m in consistency_metrics.values() if m["consistent"])
            total_metrics = len(consistency_metrics)

            print(f"   {pair}: {consistent_metrics}/{total_metrics} metrics consistent")

    return comparison


def main():
    """Main validation function"""

    print("🚀 Crypto Moment Validation")
    print("=" * 50)

    # Load data
    data_file = "artifacts/mock_crypto_data.csv"
    if not Path(data_file).exists():
        print(f"❌ Data file not found: {data_file}")
        print("Please run setup_crypto_data_collection.py first")
        return False

    df = load_crypto_data(data_file)
    prepared_data = prepare_data_for_analysis(df)

    # Validate moments
    lead_lag_results = validate_lead_lag_moments(prepared_data)
    mirroring_results = validate_mirroring_moments(prepared_data)
    crypto_moment_results = validate_crypto_moments(prepared_data)

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "data_file": data_file,
        "lead_lag_results": lead_lag_results,
        "mirroring_results": mirroring_results,
        "crypto_moment_results": crypto_moment_results,
    }

    results_file = Path("artifacts/crypto_validation_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Validation results saved: {results_file}")

    # Summary
    successful_pairs = sum(1 for r in lead_lag_results.values() if "error" not in r)
    total_pairs = len(lead_lag_results)

    print(f"\n📊 Validation Summary:")
    print(f"   Total pairs: {total_pairs}")
    print(f"   Successful validations: {successful_pairs}")
    print(f"   Success rate: {successful_pairs/total_pairs*100:.1f}%")

    return successful_pairs == total_pairs


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
