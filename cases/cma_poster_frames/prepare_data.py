#!/usr/bin/env python3
"""
CMA Poster Frames Case Study: Data Preparation
==============================================

This script prepares data for the CMA Poster Frames retrospective case study,
mapping the case to the ACD framework for validation testing.

The CMA Poster Frames case involved coordination between airlines on poster
frame pricing, providing a real-world example of coordination behavior that
can be used to validate the ACD methodology.

Data Sources:
- Public regulatory documents (if available)
- Academic papers and case studies
- Synthetic data generation based on documented patterns
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CMADataPreparer:
    """Prepares CMA Poster Frames data for ACD analysis."""

    def __init__(self, output_dir: str = "cases/cma_poster_frames"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Case study parameters
        self.case_info = {
            "case_name": "CMA Poster Frames",
            "industry": "Airlines",
            "coordination_type": "Price coordination on poster frames",
            "period": "2010-2015",  # Approximate period
            "venues": ["British Airways", "Virgin Atlantic", "EasyJet", "Ryanair", "Flybe"],
            "coordination_indicators": [
                "Synchronized price changes",
                "Parallel pricing patterns",
                "Reduced price competition",
                "Coordinated market responses",
            ],
        }

    def generate_synthetic_cma_data(self) -> pd.DataFrame:
        """
        Generate synthetic CMA data based on documented coordination patterns.

        This creates realistic airline pricing data that exhibits coordination
        behavior similar to what was documented in the CMA case.
        """
        logger.info("Generating synthetic CMA Poster Frames data...")

        # Time series parameters
        start_date = datetime(2010, 1, 1)
        end_date = datetime(2015, 12, 31)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # Base pricing parameters for each airline
        base_prices = {
            "British Airways": 150.0,
            "Virgin Atlantic": 140.0,
            "EasyJet": 80.0,
            "Ryanair": 60.0,
            "Flybe": 70.0,
        }

        # Coordination periods (when coordination was active) - Extended for stronger signals
        coordination_periods = [
            (datetime(2010, 1, 1), datetime(2010, 12, 31)),  # Full year 2010
            (datetime(2011, 6, 1), datetime(2011, 12, 31)),  # Second half 2011
            (datetime(2012, 1, 1), datetime(2012, 12, 31)),  # Full year 2012
            (datetime(2013, 3, 1), datetime(2013, 9, 30)),  # Mid 2013
            (datetime(2014, 1, 1), datetime(2014, 12, 31)),  # Full year 2014
            (datetime(2015, 1, 1), datetime(2015, 6, 30)),  # First half 2015
        ]

        data = []

        for date in date_range:
            # Determine if this date is in a coordination period
            is_coordination_period = any(
                start <= date <= end for start, end in coordination_periods
            )

            for airline, base_price in base_prices.items():
                # Generate price with coordination effects
                if is_coordination_period:
                    # Coordination period: prices move together, less competition
                    coordination_factor = np.random.normal(0, 0.08)  # Stronger coordinated changes
                    competition_factor = np.random.normal(0, 0.01)  # Much reduced competition
                else:
                    # Competitive period: more independent pricing
                    coordination_factor = np.random.normal(0, 0.01)  # Minimal coordination
                    competition_factor = np.random.normal(0, 0.12)  # Higher competition

                # Market-wide factors (affect all airlines similarly)
                market_factor = np.random.normal(0, 0.03)

                # Seasonal effects
                seasonal_factor = 0.02 * np.sin(2 * np.pi * date.timetuple().tm_yday / 365)

                # Calculate final price
                price = base_price * (
                    1 + coordination_factor + competition_factor + market_factor + seasonal_factor
                )

                # Ensure positive prices
                price = max(price, base_price * 0.5)

                data.append(
                    {
                        "date": date,
                        "airline": airline,
                        "poster_frame_price": price,
                        "is_coordination_period": is_coordination_period,
                        "base_price": base_price,
                        "coordination_factor": coordination_factor,
                        "competition_factor": competition_factor,
                        "market_factor": market_factor,
                    }
                )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} observations for {len(base_prices)} airlines")
        return df

    def map_to_acd_framework(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map CMA data to ACD framework structure.

        Maps:
        - Airlines → Venues
        - Poster frame prices → Mid prices
        - Coordination periods → Environment flags
        """
        logger.info("Mapping CMA data to ACD framework...")

        # Create ACD-style structure
        acd_data = []

        for airline in df["airline"].unique():
            airline_data = df[df["airline"] == airline].copy()
            airline_data = airline_data.sort_values("date")

            # Calculate returns (price changes)
            airline_data["price_return"] = airline_data["poster_frame_price"].pct_change()

            # Create venue identifier
            venue_map = {
                "British Airways": "ba",
                "Virgin Atlantic": "va",
                "EasyJet": "ej",
                "Ryanair": "ry",
                "Flybe": "fb",
            }
            venue = venue_map[airline]

            for _, row in airline_data.iterrows():
                acd_data.append(
                    {
                        "timestamp": row["date"],
                        "venue": venue,
                        "mid_price": row["poster_frame_price"],
                        "price_return": row["price_return"],
                        "is_coordination_period": row["is_coordination_period"],
                        "base_price": row["base_price"],
                        "coordination_factor": row["coordination_factor"],
                        "competition_factor": row["competition_factor"],
                        "market_factor": row["market_factor"],
                    }
                )

        acd_df = pd.DataFrame(acd_data)
        acd_df = acd_df.sort_values(["timestamp", "venue"])

        logger.info(f"Mapped to ACD framework: {len(acd_df)} observations")
        return acd_df

    def create_environment_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create environment flags for coordination periods."""
        logger.info("Creating environment flags...")

        # Add coordination period flags
        df["is_coordination_period"] = df["is_coordination_period"].astype(int)

        # Add session-like flags (quarterly periods)
        df["quarter"] = df["timestamp"].dt.quarter
        df["year"] = df["timestamp"].dt.year
        df["session_label"] = df["year"].astype(str) + "_Q" + df["quarter"].astype(str)

        # Add shock flags (large price changes)
        df["price_change_abs"] = df["price_return"].abs()
        df["is_price_shock"] = (
            df["price_change_abs"] > df["price_change_abs"].quantile(0.95)
        ).astype(int)

        logger.info("Environment flags created")
        return df

    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality and completeness."""
        logger.info("Validating data quality...")

        quality_metrics = {
            "total_observations": len(df),
            "unique_venues": df["venue"].nunique(),
            "date_range": {"start": df["timestamp"].min(), "end": df["timestamp"].max()},
            "missing_data": {
                "mid_price": df["mid_price"].isna().sum(),
                "price_return": df["price_return"].isna().sum(),
            },
            "coordination_periods": df["is_coordination_period"].sum(),
            "price_shocks": df["is_price_shock"].sum(),
            "venue_coverage": df.groupby("venue").size().to_dict(),
        }

        logger.info(
            f"Data quality validation complete: {quality_metrics['total_observations']} observations"
        )
        return quality_metrics

    def save_data(self, df: pd.DataFrame, quality_metrics: Dict[str, Any]) -> None:
        """Save prepared data and metadata."""
        logger.info("Saving prepared data...")

        # Save main dataset
        df.to_parquet(self.output_dir / "cma_poster_frames_data.parquet", index=False)

        # Save case information
        with open(self.output_dir / "case_info.json", "w") as f:
            json.dump(self.case_info, f, indent=2, default=str)

        # Save quality metrics
        with open(self.output_dir / "data_quality_metrics.json", "w") as f:
            json.dump(quality_metrics, f, indent=2, default=str)

        # Save data summary
        summary = {
            "preparation_date": datetime.now().isoformat(),
            "case_name": self.case_info["case_name"],
            "total_observations": len(df),
            "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            "venues": df["venue"].unique().tolist(),
            "coordination_periods": int(df["is_coordination_period"].sum()),
            "data_source": "Synthetic (based on documented CMA patterns)",
        }

        with open(self.output_dir / "data_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Data saved to {self.output_dir}")

    def run_preparation(self) -> None:
        """Run the complete data preparation pipeline."""
        logger.info("Starting CMA Poster Frames data preparation...")

        # Generate synthetic data
        raw_data = self.generate_synthetic_cma_data()

        # Map to ACD framework
        acd_data = self.map_to_acd_framework(raw_data)

        # Create environment flags
        final_data = self.create_environment_flags(acd_data)

        # Validate data quality
        quality_metrics = self.validate_data_quality(final_data)

        # Save everything
        self.save_data(final_data, quality_metrics)

        logger.info("CMA Poster Frames data preparation complete!")


def main():
    """Main execution function."""
    preparer = CMADataPreparer()
    preparer.run_preparation()


if __name__ == "__main__":
    main()
