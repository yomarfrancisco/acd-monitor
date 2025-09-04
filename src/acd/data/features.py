"""
ACD Data Features Module

Implements feature engineering and windowing for ACD analysis:
- Rolling environment labels for ICP (Institutional Coordination Patterns)
- Fixed windows for VMM (Variational Method of Moments)
- Deterministic windowing with seed control
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WindowConfig:
    """Configuration for data windowing"""

    window_size: int  # Number of data points per window
    step_size: int  # Step size between windows (overlap = window_size - step_size)
    min_data_points: int  # Minimum data points required for analysis
    window_type: str  # 'fixed' for VMM, 'rolling' for ICP
    seed: Optional[int] = None  # Random seed for deterministic behavior


@dataclass
class WindowedData:
    """Container for windowed data"""

    windows: List[pd.DataFrame]
    window_config: WindowConfig
    metadata: Dict[str, Any]

    def __len__(self) -> int:
        return len(self.windows)

    def get_window(self, index: int) -> pd.DataFrame:
        """Get window by index"""
        if 0 <= index < len(self.windows):
            return self.windows[index]
        raise IndexError(f"Window index {index} out of range")

    def get_window_metadata(self, index: int) -> Dict[str, Any]:
        """Get metadata for specific window"""
        if 0 <= index < len(self.windows):
            return self.metadata.get(f"window_{index}", {})
        raise IndexError(f"Window index {index} out of range")


class DataWindowing:
    """Main class for data windowing and feature engineering"""

    def __init__(self, config: WindowConfig):
        """Initialize windowing with configuration"""
        self.config = config

        # Set random seed for deterministic behavior
        if config.seed is not None:
            np.random.seed(config.seed)

    def create_windows(self, data: pd.DataFrame, price_columns: List[str]) -> WindowedData:
        """
        Create windows from input data

        Args:
            data: Input DataFrame with market data
            price_columns: List of price column names

        Returns:
            WindowedData object with windows and metadata
        """
        if data.empty:
            raise ValueError("Input data is empty")

        if len(data) < self.config.min_data_points:
            raise ValueError(
                f"Insufficient data: {len(data)} < {self.config.min_data_points} required"
            )

        if self.config.window_type == "fixed":
            windows = self._create_fixed_windows(data, price_columns)
        elif self.config.window_type == "rolling":
            windows = self._create_rolling_windows(data, price_columns)
        else:
            raise ValueError(f"Unknown window type: {self.config.window_type}")

        # Create metadata for each window
        metadata = self._create_window_metadata(windows, data)

        return WindowedData(windows=windows, window_config=self.config, metadata=metadata)

    def _create_fixed_windows(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> List[pd.DataFrame]:
        """Create fixed-size windows for VMM analysis"""
        windows = []
        total_points = len(data)

        # Calculate number of windows
        n_windows = max(1, (total_points - self.config.window_size) // self.config.step_size + 1)

        for i in range(n_windows):
            start_idx = i * self.config.step_size
            end_idx = start_idx + self.config.window_size

            if end_idx > total_points:
                break

            # Extract window data
            window_data = data.iloc[start_idx:end_idx].copy()

            # Ensure window has required data points
            if len(window_data) >= self.config.min_data_points:
                # Add window index for tracking
                window_data["window_index"] = i
                windows.append(window_data)

        logger.info(f"Created {len(windows)} fixed windows of size {self.config.window_size}")
        return windows

    def _create_rolling_windows(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> List[pd.DataFrame]:
        """Create rolling windows for ICP analysis"""
        windows = []
        total_points = len(data)

        # Calculate number of rolling windows
        n_windows = max(1, (total_points - self.config.window_size) // self.config.step_size + 1)

        for i in range(n_windows):
            start_idx = i * self.config.step_size
            end_idx = start_idx + self.config.window_size

            if end_idx > total_points:
                break

            # Extract window data
            window_data = data.iloc[start_idx:end_idx].copy()

            # Ensure window has required data points
            if len(window_data) >= self.config.min_data_points:
                # Add window index and rolling features
                window_data["window_index"] = i
                window_data["rolling_start"] = start_idx
                window_data["rolling_end"] = end_idx

                # Add rolling environment labels for ICP
                window_data = self._add_rolling_environment_labels(window_data, price_columns)

                windows.append(window_data)

        logger.info(f"Created {len(windows)} rolling windows of size {self.config.window_size}")
        return windows

    def _add_rolling_environment_labels(
        self, window_data: pd.DataFrame, price_columns: List[str]
    ) -> pd.DataFrame:
        """Add rolling environment labels for ICP analysis"""
        # Calculate rolling statistics for environment characterization
        for col in price_columns:
            if col in window_data.columns:
                # Rolling mean and volatility
                window_data[f"{col}_rolling_mean"] = (
                    window_data[col].rolling(window=min(10, len(window_data)), min_periods=1).mean()
                )

                window_data[f"{col}_rolling_std"] = (
                    window_data[col].rolling(window=min(10, len(window_data)), min_periods=1).std()
                )

                # Rolling momentum (price change over window)
                window_data[f"{col}_rolling_momentum"] = (
                    window_data[col] - window_data[col].iloc[0]
                ) / window_data[col].iloc[0]

        # Add cross-asset correlation features
        if len(price_columns) > 1:
            window_data = self._add_cross_asset_features(window_data, price_columns)

        return window_data

    def _add_cross_asset_features(
        self, window_data: pd.DataFrame, price_columns: List[str]
    ) -> pd.DataFrame:
        """Add cross-asset correlation and spread features"""
        # Calculate rolling correlations between assets
        for i, col1 in enumerate(price_columns):
            for j, col2 in enumerate(price_columns[i + 1 :], i + 1):
                if col1 in window_data.columns and col2 in window_data.columns:
                    # Rolling correlation
                    corr_name = f'corr_{col1.split("_")[0]}_{col2.split("_")[0]}'
                    window_data[corr_name] = (
                        window_data[col1]
                        .rolling(window=min(10, len(window_data)), min_periods=1)
                        .corr(window_data[col2])
                    )

                    # Price spread
                    spread_name = f'spread_{col1.split("_")[0]}_{col2.split("_")[0]}'
                    window_data[spread_name] = (
                        window_data[col1] - window_data[col2]
                    ) / window_data[col2]

        return window_data

    def _create_window_metadata(
        self, windows: List[pd.DataFrame], original_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Create metadata for each window"""
        metadata = {
            "total_windows": len(windows),
            "window_size": self.config.window_size,
            "step_size": self.config.step_size,
            "window_type": self.config.window_type,
            "min_data_points": self.config.min_data_points,
            "original_data_size": len(original_data),
            "created_at": datetime.now().isoformat(),
        }

        # Add metadata for each individual window
        for i, window in enumerate(windows):
            window_meta = {
                "window_index": i,
                "data_points": len(window),
                "start_timestamp": window.index[0] if len(window) > 0 else None,
                "end_timestamp": window.index[-1] if len(window) > 0 else None,
                "price_columns": [col for col in window.columns if "price" in col.lower()],
                "feature_columns": [
                    col
                    for col in window.columns
                    if "rolling" in col or "corr" in col or "spread" in col
                ],
            }

            metadata[f"window_{i}"] = window_meta

        return metadata

    def validate_windows(self, windowed_data: WindowedData) -> bool:
        """Validate that all windows meet quality requirements"""
        if not windowed_data.windows:
            return False

        for i, window in enumerate(windowed_data.windows):
            # Check minimum data points
            if len(window) < self.config.min_data_points:
                logger.warning(
                    f"Window {i} has insufficient data: "
                    f"{len(window)} < {self.config.min_data_points}"
                )
                return False

            # Check for required columns
            required_cols = ["window_index"]
            missing_cols = [col for col in required_cols if col not in window.columns]
            if missing_cols:
                logger.warning(f"Window {i} missing required columns: {missing_cols}")
                return False

        return True

    def get_window_statistics(self, windowed_data: WindowedData) -> Dict[str, Any]:
        """Get statistics about the created windows"""
        if not windowed_data.windows:
            return {}

        window_sizes = [len(window) for window in windowed_data.windows]

        stats = {
            "total_windows": len(windowed_data.windows),
            "mean_window_size": np.mean(window_sizes),
            "std_window_size": np.std(window_sizes),
            "min_window_size": min(window_sizes),
            "max_window_size": max(window_sizes),
            "window_size_consistency": np.std(window_sizes)
            < 1.0,  # All windows should be same size
            "total_data_points": sum(window_sizes),
            "data_coverage": sum(window_sizes) / windowed_data.metadata["original_data_size"],
        }

        return stats


class FeatureEngineering:
    """Feature engineering utilities for ACD analysis"""

    def __init__(self, seed: Optional[int] = None):
        """Initialize feature engineering with optional seed"""
        if seed is not None:
            np.random.seed(seed)

    def extract_price_features(self, data: pd.DataFrame, price_columns: List[str]) -> pd.DataFrame:
        """Extract price-based features for analysis"""
        features = data.copy()

        for col in price_columns:
            if col in data.columns:
                # Price changes
                features[f"{col}_price_change"] = data[col].diff()
                features[f"{col}_price_change_pct"] = data[col].pct_change()

                # Volatility features
                features[f"{col}_volatility"] = data[col].rolling(window=10, min_periods=1).std()
                features[f"{col}_volatility_pct"] = features[f"{col}_volatility"] / data[col]

                # Momentum features
                features[f"{col}_momentum_5"] = data[col] / data[col].shift(5) - 1
                features[f"{col}_momentum_10"] = data[col] / data[col].shift(10) - 1

        return features

    def extract_temporal_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract temporal features from timestamp index"""
        features = data.copy()

        if isinstance(data.index, pd.DatetimeIndex):
            # Time-based features
            features["hour"] = data.index.hour
            features["day_of_week"] = data.index.dayofweek
            features["day_of_month"] = data.index.day
            features["month"] = data.index.month

            # Cyclical encoding for time features
            features["hour_sin"] = np.sin(2 * np.pi * features["hour"] / 24)
            features["hour_cos"] = np.cos(2 * np.pi * features["hour"] / 24)
            features["day_sin"] = np.sin(2 * np.pi * features["day_of_week"] / 7)
            features["day_cos"] = np.cos(2 * np.pi * features["day_of_week"] / 7)

        return features

    def extract_statistical_features(
        self, data: pd.DataFrame, price_columns: List[str], window: int = 20
    ) -> pd.DataFrame:
        """Extract statistical features for analysis"""
        features = data.copy()

        for col in price_columns:
            if col in data.columns:
                # Rolling statistics
                features[f"{col}_rolling_mean"] = (
                    data[col].rolling(window=window, min_periods=1).mean()
                )
                features[f"{col}_rolling_std"] = (
                    data[col].rolling(window=window, min_periods=1).std()
                )
                features[f"{col}_rolling_median"] = (
                    data[col].rolling(window=window, min_periods=1).median()
                )

                # Percentile features
                features[f"{col}_rolling_p25"] = (
                    data[col].rolling(window=window, min_periods=1).quantile(0.25)
                )
                features[f"{col}_rolling_p75"] = (
                    data[col].rolling(window=window, min_periods=1).quantile(0.75)
                )

                # Skewness and kurtosis
                features[f"{col}_rolling_skew"] = (
                    data[col].rolling(window=window, min_periods=1).skew()
                )
                features[f"{col}_rolling_kurt"] = (
                    data[col].rolling(window=window, min_periods=1).kurt()
                )

        return features


def create_window_config(
    window_size: int = 100,
    step_size: int = 50,
    window_type: str = "fixed",
    seed: Optional[int] = None,
) -> WindowConfig:
    """Create a standard window configuration"""
    return WindowConfig(
        window_size=window_size,
        step_size=step_size,
        min_data_points=50,
        window_type=window_type,
        seed=seed,
    )


def create_windows(
    data: pd.DataFrame, price_columns: List[str], config: Optional[WindowConfig] = None
) -> WindowedData:
    """
    Convenience function for creating windows

    Args:
        data: Input DataFrame
        price_columns: List of price column names
        config: Optional window configuration

    Returns:
        WindowedData object
    """
    if config is None:
        config = create_window_config()

    windower = DataWindowing(config)
    return windower.create_windows(data, price_columns)
