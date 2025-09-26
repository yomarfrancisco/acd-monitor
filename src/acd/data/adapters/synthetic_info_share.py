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


class CointegratedSyntheticGenerator:
    """
    Generates cointegrated synthetic minute data for information share analysis.

    Creates realistic price series with:
    - Common efficient price with random walk
    - Venue-specific deviations with mean reversion
    - Lead-lag relationships with venue-specific shocks
    - Proper cointegration relationships
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
        self.logger = logging.getLogger(__name__)

        # Venue-specific parameters
        self.venue_params = {
            "binance": {"alpha": 0.0, "sigma": 0.0001, "lead_prob": 0.3},
            "coinbase": {"alpha": 0.0001, "sigma": 0.00008, "lead_prob": 0.25},
            "kraken": {"alpha": -0.0001, "sigma": 0.00012, "lead_prob": 0.2},
            "okx": {"alpha": 0.00005, "sigma": 0.00009, "lead_prob": 0.15},
            "bybit": {"alpha": -0.00005, "sigma": 0.00011, "lead_prob": 0.1},
        }

        # Shock parameters
        self.shock_prob = 0.01  # 1% chance of shock per minute
        self.shock_magnitude = 0.0003  # 3 bps
        self.shock_diffusion_lag = 2  # 2-3 minute lag for diffusion

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
        self, efficient_prices: np.ndarray, venue: str, shock_times: List[int] = None
    ) -> np.ndarray:
        """
        Generate venue-specific prices with mean reversion and shocks.

        Args:
            efficient_prices: Common efficient price series
            venue: Venue name
            shock_times: List of shock times (minutes)

        Returns:
            Array of venue-specific prices
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
                deviation[t] = params["alpha"] + np.random.normal(0, params["sigma"])
            else:
                deviation[t] = phi * deviation[t - 1] + np.random.normal(0, params["sigma"])

            # Add shock if this is a shock time
            if shock_times and t in shock_times:
                # Lead venue gets immediate shock
                if np.random.random() < params["lead_prob"]:
                    shock = np.random.choice([-1, 1]) * self.shock_magnitude
                    deviation[t] += shock

            # Venue price = efficient price + deviation
            venue_prices[t] = efficient_prices[t] + deviation[t]

        return venue_prices

    def generate_shock_times(self, n_minutes: int) -> List[int]:
        """
        Generate random shock times.

        Args:
            n_minutes: Total number of minutes

        Returns:
            List of shock times
        """
        shock_times = []
        for t in range(n_minutes):
            if np.random.random() < self.shock_prob:
                shock_times.append(t)
        return shock_times

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

        # Generate shock times
        shock_times = self.generate_shock_times(n_minutes)

        # Generate venue-specific prices
        venue_prices = self.generate_venue_prices(efficient_prices, venue, shock_times)

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
