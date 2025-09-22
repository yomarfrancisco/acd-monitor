"""
ATP Retrospective Case Study - Data Preparation

This module reconstructs airline price-leadership data from the ATP case
for ACD analysis. The ATP case involved coordinated fare increases by
major airlines, providing a real-world test of coordination detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")


@dataclass
class ATPConfig:
    """Configuration for ATP data preparation"""

    start_date: str = "2015-01-01"
    end_date: str = "2015-12-31"
    n_airlines: int = 4
    base_fare: float = 200.0
    coordination_strength: float = 0.8
    volatility_regime_threshold: float = 0.15
    seed: int = 42


class ATPDataGenerator:
    """Generate ATP-style airline pricing data for coordination analysis"""

    def __init__(self, config: ATPConfig = None):
        self.config = config or ATPConfig()
        np.random.seed(self.config.seed)

    def generate_atp_data(self) -> pd.DataFrame:
        """
        Generate ATP-style airline pricing data

        Returns:
            DataFrame with airline prices, environments, and coordination patterns
        """
        # Create date range
        start_date = pd.to_datetime(self.config.start_date)
        end_date = pd.to_datetime(self.config.end_date)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # Initialize data structure
        data = pd.DataFrame(index=dates)
        data["date"] = dates

        # Generate base prices for each airline
        airlines = [f"Airline_{i}" for i in range(self.config.n_airlines)]

        for airline in airlines:
            data[airline] = self._generate_airline_prices(len(dates), airline)

        # Add environment variables
        data = self._add_environment_variables(data)

        # Add coordination patterns
        data = self._add_coordination_patterns(data, airlines)

        # Add market conditions
        data = self._add_market_conditions(data)

        return data

    def _generate_airline_prices(self, n_days: int, airline: str) -> np.ndarray:
        """Generate base prices for a single airline"""
        # Base price with trend
        base_price = self.config.base_fare
        trend = np.linspace(0, 0.1, n_days)  # 10% increase over year

        # Seasonal component
        seasonal = 0.05 * np.sin(2 * np.pi * np.arange(n_days) / 365.25)

        # Random walk component
        random_walk = np.cumsum(np.random.normal(0, 0.02, n_days))

        # Combine components
        prices = base_price * (1 + trend + seasonal + random_walk)

        # Ensure positive prices
        prices = np.maximum(prices, base_price * 0.5)

        return prices

    def _add_environment_variables(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add environment variables for analysis"""
        n_days = len(data)

        # Volatility regime (high/low based on price volatility)
        price_columns = [col for col in data.columns if col.startswith("Airline_")]
        price_data = data[price_columns].values

        # Calculate rolling volatility
        window = 30  # 30-day window
        volatility = np.zeros(n_days)

        for i in range(window, n_days):
            window_prices = price_data[i - window : i]
            volatility[i] = np.std(window_prices)

        # Fill initial values
        volatility[:window] = volatility[window]

        # Create volatility regime
        data["volatility_regime"] = np.where(
            volatility > self.config.volatility_regime_threshold, "high", "low"
        )

        # Add market condition (bullish/bearish based on trend)
        price_trend = np.gradient(np.mean(price_data, axis=1))
        data["market_condition"] = np.where(price_trend > 0, "bullish", "bearish")

        # Add demand shock indicator (random events)
        demand_shocks = np.random.random(n_days) < 0.05  # 5% chance per day
        data["demand_shock"] = demand_shocks

        return data

    def _add_coordination_patterns(self, data: pd.DataFrame, airlines: List[str]) -> pd.DataFrame:
        """Add coordination patterns based on ATP case characteristics"""
        n_days = len(data)

        # Coordination periods (based on ATP case timeline)
        coordination_periods = [
            (pd.to_datetime("2015-03-01"), pd.to_datetime("2015-03-31")),  # Spring coordination
            (pd.to_datetime("2015-07-01"), pd.to_datetime("2015-07-31")),  # Summer coordination
            (pd.to_datetime("2015-11-01"), pd.to_datetime("2015-11-30")),  # Fall coordination
        ]

        # Create coordination indicator
        data["coordination_period"] = False

        for start_date, end_date in coordination_periods:
            mask = (data["date"] >= start_date) & (data["date"] <= end_date)
            data.loc[mask, "coordination_period"] = True

        # Apply coordination effects
        for airline in airlines:
            base_prices = data[airline].copy()

            # Add coordination premium during coordination periods
            coordination_mask = data["coordination_period"]
            coordination_premium = self.config.coordination_strength * 0.1  # 10% premium

            data.loc[coordination_mask, airline] = base_prices[coordination_mask] * (
                1 + coordination_premium
            )

            # Add lead-lag effects (Airline_0 leads, others follow with delay)
            if airline != "Airline_0":
                lead_airline = "Airline_0"
                lag_days = 2  # 2-day lag

                for i in range(lag_days, n_days):
                    if coordination_mask.iloc[i]:
                        # Follow the leader with some noise
                        lead_change = (
                            data[lead_airline].iloc[i] - data[lead_airline].iloc[i - lag_days]
                        ) / data[lead_airline].iloc[i - lag_days]
                        follow_change = lead_change * 0.8 + np.random.normal(
                            0, 0.01
                        )  # 80% follow with noise

                        data.iloc[i, data.columns.get_loc(airline)] = data[airline].iloc[
                            i - lag_days
                        ] * (1 + follow_change)

        return data

    def _add_market_conditions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add additional market condition variables"""
        n_days = len(data)

        # Fuel price proxy (affects all airlines)
        fuel_prices = (
            100
            + 20 * np.sin(2 * np.pi * np.arange(n_days) / 365.25)
            + np.random.normal(0, 5, n_days)
        )
        data["fuel_price_proxy"] = fuel_prices

        # Capacity utilization (affects pricing power)
        capacity_utilization = (
            0.7
            + 0.2 * np.sin(2 * np.pi * np.arange(n_days) / 365.25)
            + np.random.normal(0, 0.05, n_days)
        )
        data["capacity_utilization"] = np.clip(capacity_utilization, 0.5, 1.0)

        # Competitive intensity (number of competitors)
        data["competitive_intensity"] = np.random.choice([3, 4, 5], n_days, p=[0.2, 0.6, 0.2])

        return data


def prepare_atp_data(config: ATPConfig = None) -> pd.DataFrame:
    """
    Convenience function to prepare ATP data

    Args:
        config: ATPConfig instance

    Returns:
        DataFrame with ATP-style airline pricing data
    """
    generator = ATPDataGenerator(config)
    return generator.generate_atp_data()


if __name__ == "__main__":
    # Generate and save ATP data
    config = ATPConfig()
    atp_data = prepare_atp_data(config)

    # Save to CSV
    output_path = "cases/atp/atp_data.csv"
    atp_data.to_csv(output_path, index=False)

    print(f"ATP data generated and saved to {output_path}")
    print(f"Data shape: {atp_data.shape}")
    print(f"Date range: {atp_data['date'].min()} to {atp_data['date'].max()}")
    print(f"Coordination periods: {atp_data['coordination_period'].sum()} days")
    print(f"Airline columns: {[col for col in atp_data.columns if col.startswith('Airline_')]}")
