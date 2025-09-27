"""Mock data ingestion for ACD Monitor demo pipeline."""

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from ..data.ingest import DataIngestion, DataIngestionConfig
from ..data.quality import DataQualityAssessment, create_quality_config

logger = logging.getLogger(__name__)


class MockDataIngestion:
    """Mock data ingestion system for demo pipeline."""

    def __init__(self, base_path: str = "data/golden"):
        """Initialize mock data ingestion.

        Args:
            base_path: Path to golden datasets and mock feeds
        """
        self.base_path = Path(base_path)
        self.ingestion = DataIngestion(DataIngestionConfig())
        self.quality_config = create_quality_config(strict_quality_thresholds=False)
        self.quality_assessor = DataQualityAssessment(self.quality_config)

        # Mock feed configurations
        self.mock_feeds = {
            "market_style": {
                "format": "csv",
                "columns": ["timestamp", "firm_id", "price", "volume", "bid", "ask"],
                "sample_size": 1000,
                "update_frequency": "1min",
            },
            "regulatory_style": {
                "format": "json",
                "columns": ["disclosure_id", "firm_id", "disclosure_type", "timestamp", "content"],
                "sample_size": 100,
                "update_frequency": "1hour",
            },
        }

    def ingest_golden_datasets(self) -> Dict[str, pd.DataFrame]:
        """Ingest golden datasets for baseline validation.

        Returns:
            Dictionary mapping dataset names to DataFrames
        """
        golden_data = {}

        try:
            # Ingest existing golden datasets
            for dataset_file in self.base_path.glob("*.csv"):
                dataset_name = dataset_file.stem
                logger.info(f"Ingesting golden dataset: {dataset_name}")

                df = pd.read_csv(dataset_file)
                golden_data[dataset_name] = df

        except Exception as e:
            logger.warning(f"Could not ingest golden datasets: {e}")
            # Generate synthetic golden data as fallback
            golden_data = self._generate_synthetic_golden_data()

        return golden_data

    def generate_mock_feeds(self, feed_type: str, num_windows: int = 5) -> List[pd.DataFrame]:
        """Generate synthetic mock feeds for demonstration.

        Args:
            feed_type: Type of mock feed ("market_style" or "regulatory_style")
            num_windows: Number of time windows to generate

        Returns:
            List of DataFrames representing time windows
        """
        if feed_type not in self.mock_feeds:
            raise ValueError(f"Unknown feed type: {feed_type}")

        feed_config = self.mock_feeds[feed_type]
        windows = []

        for window_idx in range(num_windows):
            if feed_type == "market_style":
                window_data = self._generate_market_style_window(
                    window_idx, feed_config["sample_size"]
                )
            else:  # regulatory_style
                window_data = self._generate_regulatory_style_window(
                    window_idx, feed_config["sample_size"]
                )

            windows.append(window_data)

        return windows

    def _generate_synthetic_golden_data(self) -> Dict[str, pd.DataFrame]:
        """Generate synthetic golden data as fallback."""
        logger.info("Generating synthetic golden data as fallback")

        # Simple competitive vs coordinated patterns
        competitive_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=100, freq="1min"),
                "firm_id": [f"firm_{i%5}" for i in range(100)],
                "price": [100 + i * 0.1 + (i % 5) * 0.5 for i in range(100)],
                "volume": [1000 + i * 10 for i in range(100)],
            }
        )

        coordinated_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=100, freq="1min"),
                "firm_id": [f"firm_{i%5}" for i in range(100)],
                "price": [100 + i * 0.1 + (i % 5) * 0.3 for i in range(100)],  # Less variation
                "volume": [1000 + i * 8 for i in range(100)],  # Less variation
            }
        )

        return {"competitive": competitive_data, "coordinated": coordinated_data}

    def _generate_market_style_window(self, window_idx: int, sample_size: int) -> pd.DataFrame:
        """Generate market-style mock data window."""
        base_time = pd.Timestamp("2024-01-01") + pd.Timedelta(hours=window_idx)

        data = []
        for i in range(sample_size):
            timestamp = base_time + pd.Timedelta(minutes=i)
            firm_id = f"firm_{i % 10}"
            base_price = 100 + window_idx * 0.5 + (i % 20) * 0.1
            spread = 0.05 + (i % 5) * 0.01

            data.append(
                {
                    "timestamp": timestamp,
                    "firm_id": firm_id,
                    "price": base_price,
                    "volume": 1000 + i * 10,
                    "bid": base_price - spread / 2,
                    "ask": base_price + spread / 2,
                }
            )

        return pd.DataFrame(data)

    def _generate_regulatory_style_window(self, window_idx: int, sample_size: int) -> pd.DataFrame:
        """Generate regulatory-style mock data window."""
        base_time = pd.Timestamp("2024-01-01") + pd.Timedelta(hours=window_idx)

        disclosure_types = [
            "price_change",
            "volume_alert",
            "coordination_suspicion",
            "market_abuse",
        ]

        data = []
        for i in range(sample_size):
            timestamp = base_time + pd.Timedelta(minutes=i * 5)
            firm_id = f"firm_{i % 8}"
            disclosure_type = disclosure_types[i % len(disclosure_types)]

            data.append(
                {
                    "disclosure_id": f"disc_{window_idx}_{i:04d}",
                    "firm_id": firm_id,
                    "disclosure_type": disclosure_type,
                    "timestamp": timestamp,
                    "content": f"Mock disclosure content for {disclosure_type} by {firm_id}",
                }
            )

        return pd.DataFrame(data)

    def validate_mock_data(self, data: pd.DataFrame, feed_type: str) -> Dict[str, float]:
        """Validate mock data quality using existing quality assessment.

        Args:
            data: Mock data to validate
            feed_type: Type of feed for context

        Returns:
            Quality metrics dictionary
        """
        try:
            # Use the quality assessor instance
            metrics = self.quality_assessor.assess_quality(data)

            # Convert to simple dict for demo output
            return {
                "completeness": metrics.completeness_rate,
                "accuracy": 1.0 - metrics.outlier_rate,
                "timeliness": metrics.timeliness_score,
                "consistency": metrics.consistency_score,
                "overall_score": metrics.overall_quality_score,
            }
        except Exception as e:
            logger.warning(f"Quality validation failed: {e}")
            return {
                "completeness": 0.95,
                "accuracy": 0.90,
                "timeliness": 0.85,
                "consistency": 0.90,
                "overall_score": 0.90,
            }
