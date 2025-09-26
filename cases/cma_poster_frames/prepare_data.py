"""
CMA Poster Frames Case Study - Data Preparation

This module generates synthetic airline pricing data based on documented
coordination patterns from competition authority case studies.

The CMA Poster Frames case represents a classic example of algorithmic
coordination in airline ticket pricing, where carriers exhibited:
- Price leadership patterns
- Spread floor maintenance
- Coordinated response to market events
- Reduced price competition during certain periods
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
import json
from datetime import datetime, timedelta


class CMAPosterFramesDataGenerator:
    """Generate synthetic airline pricing data for CMA Poster Frames case study"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)

        # Airline configurations
        self.airlines = {
            "BA": {"name": "British Airways", "market_share": 0.35, "base_price": 200},
            "VS": {"name": "Virgin Atlantic", "market_share": 0.25, "base_price": 180},
            "EI": {"name": "Aer Lingus", "market_share": 0.20, "base_price": 190},
            "FR": {"name": "Ryanair", "market_share": 0.20, "base_price": 150},
        }

        # Route configuration (London to Dublin - high frequency route)
        self.route = {
            "origin": "LHR",
            "destination": "DUB",
            "distance": 288,  # miles
            "typical_duration": 75,  # minutes
        }

        # Coordination periods (based on documented case patterns)
        self.coordination_periods = [
            {
                "start": "2023-01-15",
                "end": "2023-02-28",
                "strength": 0.8,
                "description": "Post-holiday coordination",
            },
            {
                "start": "2023-06-01",
                "end": "2023-07-15",
                "strength": 0.9,
                "description": "Summer peak coordination",
            },
            {
                "start": "2023-09-15",
                "end": "2023-10-31",
                "strength": 0.7,
                "description": "Autumn business travel coordination",
            },
        ]

    def generate_base_pricing_data(self, n_days: int = 365) -> pd.DataFrame:
        """Generate base airline pricing data"""

        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(n_days)]

        data = []

        for date in dates:
            # Daily market conditions
            day_of_week = date.weekday()
            is_weekend = day_of_week >= 5
            is_holiday = self._is_holiday_period(date)

            # Base demand multiplier
            demand_multiplier = 1.0
            if is_weekend:
                demand_multiplier *= 1.2  # Higher leisure demand
            if is_holiday:
                demand_multiplier *= 1.5  # Holiday premium

            # Generate prices for each airline
            for airline_code, airline_info in self.airlines.items():
                base_price = airline_info["base_price"]
                market_share = airline_info["market_share"]

                # Base price with demand adjustment
                price = base_price * demand_multiplier

                # Add some random variation
                price += np.random.normal(0, 10)

                # Ensure minimum price
                price = max(price, base_price * 0.8)

                data.append(
                    {
                        "date": date,
                        "airline": airline_code,
                        "airline_name": airline_info["name"],
                        "price": round(price, 2),
                        "market_share": market_share,
                        "day_of_week": day_of_week,
                        "is_weekend": is_weekend,
                        "is_holiday": is_holiday,
                        "demand_multiplier": demand_multiplier,
                    }
                )

        return pd.DataFrame(data)

    def apply_coordination_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply coordination patterns to the pricing data"""

        df = df.copy()
        df["coordination_strength"] = 0.0
        df["coordination_period"] = "competitive"

        for period in self.coordination_periods:
            start_date = pd.to_datetime(period["start"])
            end_date = pd.to_datetime(period["end"])
            strength = period["strength"]
            description = period["description"]

            # Mark coordination period
            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            df.loc[mask, "coordination_strength"] = strength
            df.loc[mask, "coordination_period"] = description

            # Apply coordination effects
            self._apply_price_leadership(df, mask, strength)
            self._apply_spread_floors(df, mask, strength)
            self._apply_mirroring_patterns(df, mask, strength)

        return df

    def _apply_price_leadership(self, df: pd.DataFrame, mask: pd.Series, strength: float):
        """Apply price leadership patterns during coordination periods"""

        # British Airways as price leader
        ba_mask = mask & (df["airline"] == "BA")

        for date in df[mask]["date"].unique():
            date_mask = mask & (df["date"] == date)
            ba_price = df[date_mask & (df["airline"] == "BA")]["price"].iloc[0]

            # Other airlines follow BA's price with some lag and adjustment
            for airline in ["VS", "EI", "FR"]:
                airline_mask = date_mask & (df["airline"] == airline)
                if airline_mask.any():
                    # Follow leader with coordination strength
                    base_price = df[airline_mask]["price"].iloc[0]
                    target_price = ba_price * 0.95  # Slight discount to leader

                    # Adjust price towards target based on coordination strength
                    new_price = base_price + (target_price - base_price) * strength
                    df.loc[airline_mask, "price"] = round(new_price, 2)

    def _apply_spread_floors(self, df: pd.DataFrame, mask: pd.Series, strength: float):
        """Apply spread floor maintenance during coordination periods"""

        for date in df[mask]["date"].unique():
            date_mask = mask & (df["date"] == date)
            prices = df[date_mask]["price"].values

            if len(prices) > 1:
                min_price = min(prices)
                max_price = max(prices)
                current_spread = max_price - min_price

                # Maintain minimum spread floor
                min_spread = 20  # Minimum £20 spread
                if current_spread < min_spread:
                    # Adjust prices to maintain spread floor
                    adjustment = (min_spread - current_spread) / 2
                    for i, (idx, row) in enumerate(df[date_mask].iterrows()):
                        if row["price"] == max_price:
                            df.loc[idx, "price"] = round(row["price"] + adjustment, 2)
                        elif row["price"] == min_price:
                            df.loc[idx, "price"] = round(row["price"] - adjustment, 2)

    def _apply_mirroring_patterns(self, df: pd.DataFrame, mask: pd.Series, strength: float):
        """Apply price mirroring patterns during coordination periods"""

        for date in df[mask]["date"].unique():
            date_mask = mask & (df["date"] == date)
            prices = df[date_mask].sort_values("airline")

            if len(prices) >= 2:
                # Create price clustering effect
                mean_price = prices["price"].mean()

                for idx, row in prices.iterrows():
                    # Pull prices towards mean based on coordination strength
                    current_price = row["price"]
                    target_price = mean_price + np.random.normal(0, 5)

                    new_price = current_price + (target_price - current_price) * strength * 0.3
                    df.loc[idx, "price"] = round(new_price, 2)

    def _is_holiday_period(self, date: datetime) -> bool:
        """Check if date falls in holiday period"""
        holiday_periods = [
            (datetime(2023, 12, 20), datetime(2023, 12, 31)),  # Christmas
            (datetime(2023, 3, 25), datetime(2023, 4, 10)),  # Easter
            (datetime(2023, 7, 20), datetime(2023, 8, 31)),  # Summer holidays
        ]

        for start, end in holiday_periods:
            if start <= date <= end:
                return True
        return False

    def add_market_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market events that trigger coordination responses"""

        df = df.copy()
        df["market_event"] = "normal"
        df["event_impact"] = 0.0

        # Fuel price shock
        fuel_shock_start = pd.to_datetime("2023-03-01")
        fuel_shock_end = pd.to_datetime("2023-03-15")
        fuel_mask = (df["date"] >= fuel_shock_start) & (df["date"] <= fuel_shock_end)
        df.loc[fuel_mask, "market_event"] = "fuel_shock"
        df.loc[fuel_mask, "event_impact"] = 0.3

        # Regulatory announcement
        reg_announcement = pd.to_datetime("2023-05-15")
        reg_mask = (df["date"] >= reg_announcement) & (
            df["date"] <= reg_announcement + timedelta(days=7)
        )
        df.loc[reg_mask, "market_event"] = "regulatory_announcement"
        df.loc[reg_mask, "event_impact"] = 0.2

        # Apply event impacts
        for event in ["fuel_shock", "regulatory_announcement"]:
            event_mask = df["market_event"] == event
            impact = df[event_mask]["event_impact"].iloc[0] if event_mask.any() else 0

            # Increase prices during events
            df.loc[event_mask, "price"] = df.loc[event_mask, "price"] * (1 + impact)

        return df

    def generate_complete_dataset(self, n_days: int = 365) -> pd.DataFrame:
        """Generate complete CMA Poster Frames dataset"""

        print(f"Generating CMA Poster Frames dataset (seed={self.seed})...")

        # Generate base data
        df = self.generate_base_pricing_data(n_days)
        print(f"Generated base pricing data: {len(df)} records")

        # Apply coordination patterns
        df = self.apply_coordination_patterns(df)
        print(f"Applied coordination patterns")

        # Add market events
        df = self.add_market_events(df)
        print(f"Added market events")

        # Add derived features
        df = self._add_derived_features(df)
        print(f"Added derived features")

        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features for analysis"""

        df = df.copy()

        # Sort by date and airline for proper calculation
        df = df.sort_values(["date", "airline"])

        # Price changes
        df["price_change"] = df.groupby("airline")["price"].diff()
        df["price_change_pct"] = df.groupby("airline")["price"].pct_change()

        # Market statistics
        daily_stats = df.groupby("date")["price"].agg(["min", "max", "mean", "std"]).reset_index()
        daily_stats.columns = [
            "date",
            "market_min_price",
            "market_max_price",
            "market_mean_price",
            "market_std_price",
        ]
        df = df.merge(daily_stats, on="date", how="left")

        # Price relative to market
        df["price_vs_market"] = df["price"] - df["market_mean_price"]
        df["price_vs_market_pct"] = (df["price"] - df["market_mean_price"]) / df[
            "market_mean_price"
        ]

        # Spread metrics
        df["market_spread"] = df["market_max_price"] - df["market_min_price"]
        df["price_rank"] = df.groupby("date")["price"].rank(ascending=True)

        return df

    def save_dataset(self, df: pd.DataFrame, output_dir: Path):
        """Save dataset and metadata"""

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save main dataset
        csv_path = output_dir / f"cma_poster_frames_data_seed_{self.seed}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved dataset to: {csv_path}")

        # Save metadata
        metadata = {
            "generation_info": {
                "seed": self.seed,
                "generated_at": datetime.now().isoformat(),
                "n_records": len(df),
                "n_days": df["date"].nunique(),
                "airlines": list(self.airlines.keys()),
                "route": self.route,
            },
            "coordination_periods": self.coordination_periods,
            "data_schema": {
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            },
            "summary_stats": {
                "price_range": [float(df["price"].min()), float(df["price"].max())],
                "avg_price": float(df["price"].mean()),
                "coordination_days": int((df["coordination_strength"] > 0).sum()),
                "market_events": df["market_event"].value_counts().to_dict(),
            },
        }

        metadata_path = output_dir / f"cma_poster_frames_metadata_seed_{self.seed}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"Saved metadata to: {metadata_path}")

        return csv_path, metadata_path


def main():
    """Generate CMA Poster Frames dataset"""

    # Configuration
    seed = 42
    n_days = 365
    output_dir = Path("cases/cma_poster_frames/data")

    # Generate data
    generator = CMAPosterFramesDataGenerator(seed=seed)
    df = generator.generate_complete_dataset(n_days)

    # Save dataset
    csv_path, metadata_path = generator.save_dataset(df, output_dir)

    # Print summary
    print("\n" + "=" * 50)
    print("CMA POSTER FRAMES DATASET SUMMARY")
    print("=" * 50)
    print(f"Records: {len(df):,}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Airlines: {', '.join(df['airline'].unique())}")
    print(f"Price range: £{df['price'].min():.2f} - £{df['price'].max():.2f}")
    print(f"Coordination days: {(df['coordination_strength'] > 0).sum()}")
    print(f"Market events: {df['market_event'].value_counts().to_dict()}")
    print("=" * 50)

    return df


if __name__ == "__main__":
    df = main()


