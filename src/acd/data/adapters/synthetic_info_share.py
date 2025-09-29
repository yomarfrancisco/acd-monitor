"""
Cointegrated synthetic data generator for information share analysis.

This module generates synthetic minute-level data with proper cointegration
relationships between venues for testing Hasbrouck information share bounds.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import json


class CointegratedSyntheticGenerator:
    """
    Generates cointegrated synthetic minute data for information share analysis.

    Creates realistic price series with:
    - Common efficient price with random walk
    - Venue-specific deviations with mean reversion
    - Lead-lag relationships with venue-specific shocks
    - Proper cointegration relationships
    """

    def __init__(self, seed: int = 42, mode: str = "vecm_cointegrated_v2"):
        self.seed = seed
        np.random.seed(seed)
        self.logger = logging.getLogger(__name__)
        self.mode = mode

        # Leader bias for shock distribution (information leadership)
        self.leader_bias = {
            "binance": 0.5,  # 50% of shocks originate from Binance
            "coinbase": 0.25,  # 25% from Coinbase
            "kraken": 0.15,  # 15% from Kraken
            "okx": 0.05,  # 5% from OKX
            "bybit": 0.05,  # 5% from Bybit
        }

        if mode == "vecm_cointegrated_v2":
            # VECM-based cointegrated parameters
            self.sigma_eff = 0.0002  # Efficient price volatility

            # Asymmetric error-correction speeds (higher = faster incorporation = higher IS)
            self.alphas = {
                "binance": 0.35,  # Fastest adjustment
                "coinbase": 0.25,  # Second fastest
                "okx": 0.18,  # Medium
                "kraken": 0.12,  # Slow
                "bybit": 0.10,  # Slowest
            }

            # AR(1) mean reversion parameters (stationary deviations)
            self.phis = {
                "binance": 0.85,  # Tight mean reversion
                "coinbase": 0.80,  # Tight mean reversion
                "okx": 0.75,  # Medium mean reversion
                "kraken": 0.70,  # Loose mean reversion
                "bybit": 0.65,  # Loose mean reversion
            }

            # Venue-specific noise (small relative to sigma_eff)
            self.venue_params = {
                "binance": {"sigma": 0.00002, "lag_seconds": 0},  # Very low noise
                "coinbase": {"sigma": 0.00003, "lag_seconds": 0},  # Low noise
                "okx": {"sigma": 0.00004, "lag_seconds": 2},  # Medium noise
                "kraken": {"sigma": 0.00005, "lag_seconds": 4},  # Higher noise
                "bybit": {"sigma": 0.00006, "lag_seconds": 6},  # Highest noise
            }
        else:
            # Original parameters for backward compatibility
            self.venue_params = {
                "binance": {
                    "alpha": 0.0,
                    "sigma": 0.00005,  # Low noise (efficient)
                    "lead_prob": 0.3,
                    "lag_seconds": 0,  # No lag (leader)
                },
                "coinbase": {
                    "alpha": 0.0001,
                    "sigma": 0.00008,  # Medium noise
                    "lead_prob": 0.25,
                    "lag_seconds": 0,  # No lag
                },
                "kraken": {
                    "alpha": -0.0001,
                    "sigma": 0.00015,  # High noise (less efficient)
                    "lead_prob": 0.2,
                    "lag_seconds": 8,  # 8 second lag
                },
                "okx": {
                    "alpha": 0.00005,
                    "sigma": 0.00012,  # High noise
                    "lead_prob": 0.15,
                    "lag_seconds": 10,  # 10 second lag
                },
                "bybit": {
                    "alpha": -0.00005,
                    "sigma": 0.00018,  # Highest noise (least efficient)
                    "lead_prob": 0.1,
                    "lag_seconds": 12,  # 12 second lag
                },
            }

        # Shock parameters
        self.shock_prob = 0.01  # 1% chance of shock per minute
        self.shock_magnitude = 0.0003  # 3 bps
        self.shock_diffusion_lag = 2  # 2-3 minute lag for diffusion

        # Log synthetic parameters
        self._log_synthetic_params()

    def _log_synthetic_params(self):
        """Log synthetic data generation parameters."""
        if self.mode == "vecm_cointegrated_v2":
            params_log = {
                "mode": self.mode,
                "alphas": self.alphas,
                "phis": self.phis,
                "sigmas": {venue: params["sigma"] for venue, params in self.venue_params.items()},
                "leader_bias": self.leader_bias,
                "lag_seconds": {
                    venue: params["lag_seconds"] for venue, params in self.venue_params.items()
                },
                "sigma_eff": self.sigma_eff,
                "shock_prob": self.shock_prob,
                "shock_magnitude": self.shock_magnitude,
            }
        else:
            params_log = {
                "mode": self.mode,
                "leader_bias": self.leader_bias,
                "noise_variances": {
                    venue: params["sigma"] for venue, params in self.venue_params.items()
                },
                "lag_seconds": {
                    venue: params["lag_seconds"] for venue, params in self.venue_params.items()
                },
                "shock_prob": self.shock_prob,
                "shock_magnitude": self.shock_magnitude,
            }
        print(f"[DATA:synthetic:params] {json.dumps(params_log, ensure_ascii=False)}")

    def generate_efficient_price(
        self, start_price: float, n_minutes: int, sigma: float = 0.0002
    ) -> np.ndarray:
        """
        Generate efficient price using random walk.

        Args:
            start_price: Starting price level
            n_minutes: Number of minutes to generate
            sigma: Volatility parameter

        Returns:
            Array of efficient prices
        """
        # Random walk: p_t = p_{t-1} + ε_t
        innovations = np.random.normal(0, sigma, n_minutes)
        prices = np.zeros(n_minutes)
        prices[0] = start_price

        for t in range(1, n_minutes):
            prices[t] = prices[t - 1] + innovations[t]

        return prices

    def generate_venue_prices(
        self, efficient_prices: np.ndarray, venue: str, shock_events: List[Dict] = None
    ) -> np.ndarray:
        """
        Generate venue-specific prices with VECM-based cointegration and asymmetric adjustment.

        Args:
            efficient_prices: Common efficient price series
            venue: Venue name
            shock_events: List of shock events with venue and time

        Returns:
            Array of venue-specific prices
        """
        # Get venue parameters and calculate duration
        _ = self.venue_params[venue]  # params not used in this context
        _ = len(efficient_prices)  # n_minutes not used in this context

        if self.mode == "vecm_cointegrated_v2":
            return self._generate_vecm_cointegrated_prices(efficient_prices, venue, shock_events)
        else:
            return self._generate_original_prices(efficient_prices, venue, shock_events)

    def _generate_vecm_cointegrated_prices(
        self, efficient_prices: np.ndarray, venue: str, shock_events: List[Dict] = None
    ) -> np.ndarray:
        """
        Generate VECM-based cointegrated prices with asymmetric adjustment speeds.
        """
        params = self.venue_params[venue]
        n_minutes = len(efficient_prices)

        # Get venue-specific parameters
        alpha = self.alphas[venue]  # Error-correction speed
        phi = self.phis[venue]  # AR(1) mean reversion
        sigma = params["sigma"]  # Venue-specific noise

        # Initialize arrays
        venue_prices = np.zeros(n_minutes)
        deviations = np.zeros(n_minutes)

        # Initialize first price
        venue_prices[0] = efficient_prices[0] + np.random.normal(0, sigma)
        deviations[0] = venue_prices[0] - efficient_prices[0]

        for t in range(1, n_minutes):
            # AR(1) mean reversion for stationary deviations
            deviations[t] = phi * deviations[t - 1] + np.random.normal(0, sigma)

            # Error-correction mechanism (asymmetric adjustment)
            error_term = venue_prices[t - 1] - efficient_prices[t - 1]
            ecm_adjustment = alpha * (-error_term)

            # Venue price = efficient price + deviation + ECM adjustment
            venue_prices[t] = efficient_prices[t] + deviations[t] + ecm_adjustment

            # Apply shocks with lagged propagation
            if shock_events:
                for shock in shock_events:
                    shock_time = shock["time"]
                    leading_venue = shock["leading_venue"]
                    magnitude = shock["magnitude"]

                    # Calculate lagged time for this venue
                    lag_minutes = params["lag_seconds"] // 60  # Convert seconds to minutes
                    lagged_time = shock_time + lag_minutes

                    # Apply shock if this venue is the leader (immediate) or follower (lagged)
                    if (leading_venue == venue and t == shock_time) or (
                        leading_venue != venue and t == lagged_time and lagged_time < n_minutes
                    ):
                        # Scale shock magnitude based on venue efficiency
                        efficiency_factor = 1.0 - (
                            sigma / self.sigma_eff
                        )  # More efficient = larger impact
                        scaled_shock = magnitude * efficiency_factor
                        venue_prices[t] += scaled_shock

        return venue_prices

    def _generate_original_prices(
        self, efficient_prices: np.ndarray, venue: str, shock_events: List[Dict] = None
    ) -> np.ndarray:
        """
        Generate original venue prices (backward compatibility).
        """
        params = self.venue_params[venue]
        n_minutes = len(efficient_prices)

        # Initialize venue-specific deviation
        deviation = np.zeros(n_minutes)
        venue_prices = np.zeros(n_minutes)

        # Mean reversion parameter
        phi = 0.95  # High persistence for cointegration

        for t in range(n_minutes):
            # Mean reversion: deviation_t = φ * deviation_{t-1} + η_t
            if t == 0:
                deviation[t] = params.get("alpha", 0.0) + np.random.normal(0, params["sigma"])
            else:
                deviation[t] = phi * deviation[t - 1] + np.random.normal(0, params["sigma"])

            # Apply shocks with lagged propagation
            if shock_events:
                for shock in shock_events:
                    shock_time = shock["time"]
                    leading_venue = shock["leading_venue"]
                    magnitude = shock["magnitude"]

                    # Calculate lagged time for this venue
                    lag_minutes = params["lag_seconds"] // 60  # Convert seconds to minutes
                    lagged_time = shock_time + lag_minutes

                    # Apply shock if this venue is the leader (immediate) or follower (lagged)
                    if (leading_venue == venue and t == shock_time) or (
                        leading_venue != venue and t == lagged_time and lagged_time < n_minutes
                    ):
                        # Scale shock magnitude based on venue efficiency
                        efficiency_factor = 1.0 - (
                            params["sigma"] / 0.0002
                        )  # More efficient = larger impact
                        scaled_shock = magnitude * efficiency_factor
                        deviation[t] += scaled_shock

            # Venue price = efficient price + deviation
            venue_prices[t] = efficient_prices[t] + deviation[t]

        return venue_prices

    def generate_shock_times(self, n_minutes: int) -> List[Dict]:
        """
        Generate random shock times with venue-specific leadership.

        Args:
            n_minutes: Total number of minutes

        Returns:
            List of shock events with venue and time
        """
        shock_events = []
        for t in range(n_minutes):
            if np.random.random() < self.shock_prob:
                # Select leading venue based on bias
                venues = list(self.leader_bias.keys())
                probs = list(self.leader_bias.values())
                leading_venue = np.random.choice(venues, p=probs)

                shock_events.append(
                    {
                        "time": t,
                        "leading_venue": leading_venue,
                        "magnitude": np.random.choice([-1, 1]) * self.shock_magnitude,
                    }
                )
        return shock_events

    def generate_ohlcv_data(
        self, venue: str, start_price: float, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """
        Generate complete OHLCV data for a venue.

        Args:
            venue: Venue name
            start_price: Starting price
            start_time: Start datetime
            end_time: End datetime

        Returns:
            DataFrame with OHLCV data
        """
        # Calculate number of minutes
        duration = end_time - start_time
        n_minutes = int(duration.total_seconds() / 60)

        # Generate efficient price
        efficient_prices = self.generate_efficient_price(start_price, n_minutes)

        # Generate shock events with venue leadership
        shock_events = self.generate_shock_times(n_minutes)

        # Generate venue-specific prices
        venue_prices = self.generate_venue_prices(efficient_prices, venue, shock_events)

        # Create OHLCV data
        timestamps = [start_time + timedelta(minutes=i) for i in range(n_minutes)]

        data = []
        for i, (timestamp, price) in enumerate(zip(timestamps, venue_prices)):
            # Generate realistic OHLCV from price
            volatility = abs(np.random.normal(0, 0.0001))
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = price * (1 + np.random.normal(0, 0.00005))
            close_price = price
            volume = np.random.lognormal(10, 1)  # Realistic volume

            data.append(
                {
                    "time": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close_price,
                    "volume": volume,
                }
            )

        df = pd.DataFrame(data)
        df["venue"] = venue

        return df

    def generate_cointegrated_data(
        self, venues: List[str], start_price: float, start_time: datetime, end_time: datetime
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate cointegrated data for all venues.

        Args:
            venues: List of venue names
            start_price: Starting price
            start_time: Start datetime
            end_time: End datetime

        Returns:
            Dictionary of DataFrames per venue
        """
        self.logger.info(f"Generating cointegrated synthetic data for {len(venues)} venues")

        venue_data = {}
        for venue in venues:
            df = self.generate_ohlcv_data(venue, start_price, start_time, end_time)
            venue_data[venue] = df

            self.logger.info(f"Generated {len(df)} minute bars for {venue}")

        return venue_data


def create_cointegrated_generator(seed: int = 42) -> CointegratedSyntheticGenerator:
    """Create a cointegrated synthetic data generator."""
    return CointegratedSyntheticGenerator(seed=seed)
