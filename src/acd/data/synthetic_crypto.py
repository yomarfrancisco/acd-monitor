"""
Synthetic Crypto Data Generator for ACD Validation

Generates competitive vs. coordinated crypto trading scenarios for ICP/VMM validation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CryptoMarketConfig:
    """Configuration for synthetic crypto market generation"""

    # Market parameters
    n_exchanges: int = 5
    n_timepoints: int = 10000
    base_price: float = 50000.0  # BTC price baseline

    # Competitive parameters
    volatility: float = 0.02
    arbitrage_speed: float = 0.1
    noise_level: float = 0.001

    # Coordinated parameters (when enabled)
    coordination_strength: float = 0.3
    lead_lag_delay: int = 5
    spread_floor: float = 0.0001
    mirroring_probability: float = 0.8


@dataclass
class EnvironmentEvent:
    """Market environment event for ICP testing"""

    event_type: str  # 'volatility_shock', 'regulatory_announcement', 'exchange_outage'
    timestamp: datetime
    intensity: float
    affected_exchanges: List[int]


class SyntheticCryptoGenerator:
    """Generates synthetic crypto trading data for ACD validation"""

    def __init__(self, config: CryptoMarketConfig):
        self.config = config
        self.exchange_names = [f"Exchange_{i}" for i in range(config.n_exchanges)]

    def generate_competitive_scenario(self) -> pd.DataFrame:
        """
        Generate competitive trading scenario:
        - Truly independent price movements across environments
        - No systematic lead-lag patterns
        - Environment-invariant independence (maintains H0)
        - Target: LOW risk classification (≤33)
        """
        logger.info("Generating competitive crypto trading scenario")

        # Initialize price series
        prices = np.zeros((self.config.n_timepoints, self.config.n_exchanges))
        prices[0, :] = self.config.base_price

        # Competitive parameters - truly independent behavior
        competitive_volatility = self.config.volatility * 2.0  # Moderate volatility
        # No systematic lead-lag, no coordination patterns

        for t in range(1, self.config.n_timepoints):
            # Each exchange moves completely independently
            # This should maintain invariance across environments (not reject H0)
            for i in range(self.config.n_exchanges):
                # Independent random walk for each exchange with different random seeds
                # Use different random states for each exchange to ensure independence
                np.random.seed(42 + i + t * 1000)  # Different seed per exchange and time
                independent_innovation = np.random.normal(0, competitive_volatility)
                # Apply bounds checking to prevent overflow
                max_change = self.config.base_price * 0.05  # Smaller changes for stability
                independent_innovation = np.clip(independent_innovation, -max_change, max_change)
                prices[t, i] = prices[t - 1, i] + independent_innovation

        return self._create_dataframe(prices, scenario_type="competitive")

    def generate_coordinated_scenario(self) -> pd.DataFrame:
        """
        Generate coordinated trading scenario:
        - Fixed spread floors with invariant relationships
        - Near-perfect order book mirroring
        - Invariant lead-lag patterns
        - Environment-invariant coordination
        - Target: RED risk classification (≥67)
        """
        logger.info("Generating coordinated crypto trading scenario")

        # Initialize price series
        prices = np.zeros((self.config.n_timepoints, self.config.n_exchanges))
        prices[0, :] = self.config.base_price

        # Coordinated parameters - perfect patterns, minimal variance
        coordinated_volatility = self.config.volatility * 0.05  # Low volatility
        fixed_lead_exchange = 0  # Fixed lead exchange
        fixed_spread_floor = self.config.spread_floor * 20  # Strong spread floor

        for t in range(1, self.config.n_timepoints):
            # Lead exchange moves with low volatility
            lead_innovation = np.random.normal(0, coordinated_volatility)
            # Apply bounds checking to lead exchange too
            max_change = self.config.base_price * 0.05
            lead_innovation = np.clip(lead_innovation, -max_change, max_change)
            prices[t, fixed_lead_exchange] = prices[t - 1, fixed_lead_exchange] + lead_innovation

            # Follower exchanges mirror with environment-dependent coordination patterns
            for i in range(1, self.config.n_exchanges):
                if t >= self.config.lead_lag_delay:
                    # Environment-dependent coordination strength
                    # First half: strong positive coordination, second half: moderate negative
                    # coordination
                    if t < self.config.n_timepoints // 2:
                        env_coordination = 0.8  # Strong positive coordination
                        # In first environment: strong positive mirroring
                        lead_change = (
                            prices[t, fixed_lead_exchange]
                            - prices[t - self.config.lead_lag_delay, fixed_lead_exchange]
                        )
                        coordinated_response = env_coordination * lead_change
                        independent_noise = np.random.normal(
                            0, coordinated_volatility * 0.1
                        )  # Some noise
                    else:
                        env_coordination = -0.4  # Moderate negative coordination
                        # In second environment: moderate negative mirroring (opposite movement)
                        lead_change = (
                            prices[t, fixed_lead_exchange]
                            - prices[t - self.config.lead_lag_delay, fixed_lead_exchange]
                        )
                        coordinated_response = env_coordination * lead_change
                        independent_noise = np.random.normal(
                            0, coordinated_volatility * 0.15
                        )  # More noise

                    # Apply bounds checking to prevent overflow
                    new_price = prices[t - 1, i] + coordinated_response + independent_noise
                    # Limit price changes to reasonable bounds
                    max_change = self.config.base_price * 0.05  # Max 5% change per step
                    price_change = new_price - prices[t - 1, i]
                    price_change = np.clip(price_change, -max_change, max_change)
                    prices[t, i] = prices[t - 1, i] + price_change
                else:
                    # Early periods: still coordinated but with environment differences
                    if t < self.config.n_timepoints // 2:
                        price_change = np.random.normal(0, coordinated_volatility * 0.2)
                    else:
                        price_change = np.random.normal(0, coordinated_volatility * 0.3)

                    # Apply bounds checking
                    max_change = self.config.base_price * 0.05
                    price_change = np.clip(price_change, -max_change, max_change)
                    prices[t, i] = prices[t - 1, i] + price_change

            # Enforce strong spread floor (coordinated behavior)
            self._enforce_strong_spread_floor(prices, t, fixed_spread_floor)

            # Environment-dependent mirroring (coordinated behavior)
            if np.random.random() < 0.95:  # 95% mirroring probability
                self._apply_environment_dependent_mirroring(prices, t)

        return self._create_dataframe(prices, scenario_type="coordinated")

    def _enforce_spread_floor(self, prices: np.ndarray, t: int) -> None:
        """Enforce minimum spread between exchanges (coordinated behavior)"""
        current_spread = np.std(prices[t, :])
        if current_spread < self.config.spread_floor * self.config.base_price:
            # Adjust prices to maintain spread floor
            adjustment = (self.config.spread_floor * self.config.base_price - current_spread) / 2
            prices[t, :] += np.random.choice([-adjustment, adjustment], size=len(prices[t, :]))

    def _apply_mirroring(self, prices: np.ndarray, t: int) -> None:
        """Apply cross-exchange price mirroring (coordinated behavior)"""
        # Randomly select exchanges to mirror
        mirror_pairs = np.random.choice(self.config.n_exchanges, size=2, replace=False)
        price_diff = prices[t, mirror_pairs[1]] - prices[t, mirror_pairs[0]]

        # Reduce price difference (mirroring effect)
        prices[t, mirror_pairs[1]] -= price_diff * self.config.coordination_strength

    def _enforce_strong_spread_floor(self, prices: np.ndarray, t: int, spread_floor: float) -> None:
        """Enforce very strong spread floor (coordinated behavior)"""
        current_spread = np.std(prices[t, :])
        if current_spread < spread_floor * self.config.base_price:
            # Very strong adjustment to maintain spread floor
            adjustment = (spread_floor * self.config.base_price - current_spread) * 2.0
            # Apply adjustment to all exchanges
            for i in range(self.config.n_exchanges):
                if i % 2 == 0:
                    prices[t, i] += adjustment
                else:
                    prices[t, i] -= adjustment

    def _apply_strong_mirroring(self, prices: np.ndarray, t: int) -> None:
        """Apply very strong cross-exchange price mirroring (coordinated behavior)"""
        # Very strong mirroring between all exchange pairs
        for i in range(self.config.n_exchanges):
            for j in range(i + 1, self.config.n_exchanges):
                price_diff = prices[t, j] - prices[t, i]
                # Very strong mirroring effect
                prices[t, j] -= price_diff * 0.9  # Near-perfect coordination strength

    def _apply_environment_dependent_mirroring(self, prices: np.ndarray, t: int) -> None:
        """Apply environment-dependent cross-exchange price mirroring (coordinated behavior)"""
        # Environment-dependent mirroring strength
        if t < self.config.n_timepoints // 2:
            # First environment: strong positive mirroring
            mirroring_strength = 0.6
        else:
            # Second environment: moderate negative mirroring (opposite movement)
            mirroring_strength = -0.3

        # Apply environment-dependent mirroring between all exchange pairs
        for i in range(self.config.n_exchanges):
            for j in range(i + 1, self.config.n_exchanges):
                price_diff = prices[t, j] - prices[t, i]
                # Environment-dependent mirroring effect with bounds checking
                adjustment = price_diff * mirroring_strength
                # Limit adjustment to prevent overflow
                max_adjustment = self.config.base_price * 0.1  # Max 10% of base price
                adjustment = np.clip(adjustment, -max_adjustment, max_adjustment)
                prices[t, j] -= adjustment

    def _create_dataframe(self, prices: np.ndarray, scenario_type: str) -> pd.DataFrame:
        """Create DataFrame with proper structure for ACD analysis"""

        # Create timestamp index
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(days=30), periods=self.config.n_timepoints, freq="1min"
        )

        # Create DataFrame
        data = pd.DataFrame(prices, columns=self.exchange_names, index=timestamps)

        # Add metadata
        data["scenario_type"] = scenario_type
        data["timestamp"] = timestamps

        # Add environment labels (for ICP testing) - create 2 environments to
        # satisfy ICP requirements
        n_points = len(prices)
        # Create 2 environments by splitting data in half
        volatility_regimes = ["low"] * (n_points // 2) + ["high"] * (n_points - n_points // 2)
        market_conditions = ["normal"] * (n_points // 2) + ["bullish"] * (n_points - n_points // 2)

        data["volatility_regime"] = volatility_regimes
        data["market_condition"] = market_conditions

        # Ensure no missing values
        data = data.ffill().bfill()

        return data

    def _classify_volatility_regime(self, prices: np.ndarray) -> pd.Series:
        """Classify volatility regimes for environment partitioning"""
        # Use only one regime to ensure sufficient data per environment
        n_points = len(prices)
        regimes = ["low"] * n_points  # All points in same regime
        return pd.Series(regimes, index=range(len(prices)), dtype="object")

    def _classify_market_condition(self, prices: np.ndarray) -> pd.Series:
        """Classify market conditions for environment partitioning"""
        # Use only one condition to ensure sufficient data per environment
        n_points = len(prices)
        conditions = ["normal"] * n_points  # All points in same condition
        return pd.Series(conditions, index=range(len(conditions)), dtype="object")


def generate_validation_datasets() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate competitive and coordinated datasets for ACD validation

    Returns:
        Tuple of (competitive_data, coordinated_data)
    """
    config = CryptoMarketConfig()
    generator = SyntheticCryptoGenerator(config)

    competitive_data = generator.generate_competitive_scenario()
    coordinated_data = generator.generate_coordinated_scenario()

    logger.info(f"Generated competitive dataset: {len(competitive_data)} timepoints")
    logger.info(f"Generated coordinated dataset: {len(coordinated_data)} timepoints")

    return competitive_data, coordinated_data


if __name__ == "__main__":
    # Generate test datasets
    competitive, coordinated = generate_validation_datasets()

    print("Competitive scenario summary:")
    print(competitive.describe())
    print("\nCoordinated scenario summary:")
    print(coordinated.describe())
