#!/usr/bin/env python3
"""
Consumer Cost Uplift Analysis: Calculate welfare loss during coordination episodes.

This script calculates consumer cost uplift during coordination episodes by
comparing execution costs to a competitive baseline with proper controls.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        elif hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return super().default(obj)


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def load_micro_controls(controls_path: str) -> Dict:
    """Load microstructure controls."""
    try:
        with open(controls_path, "r") as f:
            controls_data = json.load(f)

        logger.info(f"Loaded microstructure controls: {controls_data['summary']}")
        return controls_data

    except Exception as e:
        logger.error(f"Failed to load microstructure controls: {e}")
        raise


def load_episodes(episodes_path: str) -> List[Dict]:
    """Load coordination episodes."""
    try:
        with open(episodes_path, "r") as f:
            episodes_data = json.load(f)

        if "episodes" in episodes_data:
            episodes = episodes_data["episodes"]
        else:
            episodes = episodes_data

        logger.info(f"Loaded {len(episodes)} episodes")
        return episodes

    except Exception as e:
        logger.error(f"Failed to load episodes: {e}")
        raise


def calculate_execution_cost(
    price: float, spread_bps: float, taker_fee_bps: float, slippage_bps: float = 0.0
) -> float:
    """Calculate execution cost for a retail trade."""
    # Half spread (market impact)
    half_spread_bps = spread_bps / 2

    # Total execution cost in basis points
    total_cost_bps = half_spread_bps + slippage_bps + taker_fee_bps

    return total_cost_bps


def estimate_spread_from_controls(micro_controls: pd.DataFrame) -> pd.DataFrame:
    """Estimate spreads from microstructure controls."""
    # This is a simplified approach - in practice, you'd need actual bid/ask data
    # For now, we'll estimate spreads based on volatility and momentum

    spreads = []

    for _, row in micro_controls.iterrows():
        # Estimate spread based on volatility and momentum
        base_spread_bps = 5.0  # 5 bps base spread

        # Volatility component
        vol_component = row["rv_30s"] * 1000 if not pd.isna(row["rv_30s"]) else 0

        # Momentum component (higher momentum = wider spreads)
        momentum_component = (
            abs(row["momentum_1s"]) * 1000 if not pd.isna(row["momentum_1s"]) else 0
        )

        # Time-of-day component (wider spreads during off-hours)
        if row["session"] == "asia":
            time_component = 2.0
        elif row["session"] == "europe":
            time_component = 1.0
        else:
            time_component = 1.5

        # Estimated spread
        estimated_spread_bps = base_spread_bps + vol_component + momentum_component + time_component

        spreads.append(
            {
                "timestamp": row["timestamp"],
                "venue": row["venue"],
                "spread_bps": estimated_spread_bps,
            }
        )

    return pd.DataFrame(spreads)


def build_consumer_cost_baseline(
    micro_controls: pd.DataFrame, execution_costs: pd.DataFrame
) -> Dict:
    """Build competitive baseline model for consumer execution costs."""
    try:
        # Prepare features for baseline model
        features = [
            "rv_30s",
            "rv_5s",
            "momentum_1s",
            "momentum_5s",
            "momentum_30s",
            "hour",
            "minute",
            "second",
            "day_of_week",
        ]

        # Create feature matrix
        X = micro_controls[features].fillna(0)
        y = execution_costs["execution_cost_bps"]

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
            "std_residual": float(residuals.std()),
        }

        logger.info(f"Consumer cost baseline model R² = {baseline_model['r_squared']:.3f}")
        return baseline_model

    except Exception as e:
        logger.error(f"Failed to build consumer cost baseline model: {e}")
        return {"error": str(e)}


def calculate_episode_cost_uplift(
    episodes: List[Dict],
    micro_controls: pd.DataFrame,
    execution_costs: pd.DataFrame,
    baseline_model: Dict,
) -> List[Dict]:
    """Calculate consumer cost uplift for each episode."""
    episode_results = []

    for i, episode in enumerate(episodes):
        try:
            # Extract episode information
            if "episode" in episode:
                episode_data = episode["episode"]
            else:
                episode_data = episode

            start_time = pd.to_datetime(episode_data["start_time"])
            end_time = pd.to_datetime(episode_data["end_time"])

            # Filter controls and costs for episode period
            episode_controls = micro_controls[
                (micro_controls["timestamp"] >= start_time)
                & (micro_controls["timestamp"] <= end_time)
            ]

            episode_costs = execution_costs[
                (execution_costs["timestamp"] >= start_time)
                & (execution_costs["timestamp"] <= end_time)
            ]

            if len(episode_controls) == 0 or len(episode_costs) == 0:
                logger.warning(f"No controls or costs found for episode {i}")
                continue

            # Calculate baseline predictions
            episode_features = episode_controls[baseline_model["features"]].fillna(0)
            baseline_predictions = (
                np.dot(episode_features, baseline_model["coefficients"])
                + baseline_model["intercept"]
            )

            # Calculate actual vs baseline costs
            actual_costs = episode_costs["execution_cost_bps"].values
            baseline_costs = baseline_predictions

            # Calculate uplift
            cost_uplift = actual_costs - baseline_costs
            mean_uplift = np.mean(cost_uplift)
            total_uplift = np.sum(cost_uplift)

            # Calculate welfare loss (simplified)
            # Welfare loss = uplift * notional traded
            notional_traded = episode_costs["price"].sum() * 0.1  # Placeholder
            welfare_loss = mean_uplift * notional_traded / 10000  # Convert bps to dollars

            episode_results.append(
                {
                    "episode_index": i,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                    "actual_cost_bps": float(np.mean(actual_costs)),
                    "baseline_cost_bps": float(np.mean(baseline_costs)),
                    "cost_uplift_bps": float(mean_uplift),
                    "total_uplift_bps": float(total_uplift),
                    "welfare_loss_usd": float(welfare_loss),
                    "n_timestamps": len(episode_costs),
                }
            )

        except Exception as e:
            logger.error(f"Failed to process episode {i}: {e}")
            continue

    return episode_results


def run_consumer_cost_uplift_analysis(
    snapshot_path: str, episodes_path: str, micro_controls_path: str, output_path: str
) -> bool:
    """Run consumer cost uplift analysis."""
    try:
        # Load data
        logger.info("Loading microstructure controls")
        micro_controls_data = load_micro_controls(micro_controls_path)
        micro_controls = pd.DataFrame(micro_controls_data["micro_controls"])

        logger.info("Loading episodes")
        episodes = load_episodes(episodes_path)

        # Estimate spreads and execution costs
        logger.info("Estimating spreads and execution costs")
        spreads = estimate_spread_from_controls(micro_controls)

        # Calculate execution costs
        execution_costs = []
        for _, row in micro_controls.iterrows():
            venue_spread = spreads[spreads["venue"] == row["venue"]]
            if len(venue_spread) > 0:
                spread_bps = venue_spread.iloc[0]["spread_bps"]
            else:
                spread_bps = 5.0  # Default spread

            # Taker fee (simplified - would need actual fee schedules)
            taker_fee_bps = 10.0  # 10 bps default

            # Calculate execution cost
            execution_cost = calculate_execution_cost(row["price"], spread_bps, taker_fee_bps)

            execution_costs.append(
                {
                    "timestamp": row["timestamp"],
                    "venue": row["venue"],
                    "price": row["price"],
                    "spread_bps": spread_bps,
                    "taker_fee_bps": taker_fee_bps,
                    "execution_cost_bps": execution_cost,
                }
            )

        execution_costs_df = pd.DataFrame(execution_costs)

        # Build baseline model
        logger.info("Building consumer cost baseline model")
        baseline_model = build_consumer_cost_baseline(micro_controls, execution_costs_df)

        if "error" in baseline_model:
            logger.error(f"Baseline model failed: {baseline_model['error']}")
            return False

        # Calculate episode cost uplift
        logger.info("Calculating episode cost uplift")
        episode_results = calculate_episode_cost_uplift(
            episodes, micro_controls, execution_costs_df, baseline_model
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
                "total_cost_uplift_bps": sum(ep["total_uplift_bps"] for ep in episode_results),
                "mean_cost_uplift_bps": np.mean([ep["cost_uplift_bps"] for ep in episode_results]),
                "std_cost_uplift_bps": np.std([ep["cost_uplift_bps"] for ep in episode_results]),
                "total_welfare_loss_usd": sum(ep["welfare_loss_usd"] for ep in episode_results),
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        # Write output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(output_data, f, cls=PandasJSONEncoder, indent=2)

        logger.info(f"Consumer cost uplift analysis completed: {output_file}")
        return True

    except Exception as e:
        logger.error(f"Consumer cost uplift analysis failed: {e}")
        return False


def main():
    """Main function for consumer cost uplift analysis."""
    parser = argparse.ArgumentParser(description="Calculate consumer cost uplift")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--episodes", required=True, help="Path to episodes JSON")
    parser.add_argument("--micro-controls", required=True, help="Path to micro_controls.json")
    parser.add_argument("--output", required=True, help="Output path for analysis results")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Run analysis
        success = run_consumer_cost_uplift_analysis(
            args.snapshot, args.episodes, args.micro_controls, args.output
        )

        if success:
            logger.info("Consumer cost uplift analysis completed successfully")
            sys.exit(0)
        else:
            logger.error("Failed to complete consumer cost uplift analysis")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Consumer cost uplift analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
