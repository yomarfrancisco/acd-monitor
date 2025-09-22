"""
Global Scalers for VMM Moment Normalization

Implements global scalers that can be fit once and reused across datasets
to prevent normalization from collapsing differences between competitive and coordinated scenarios.
"""

import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GlobalMinMaxScaler:
    """Global Min-Max scaler that fits once and applies consistently"""

    def __init__(self):
        self.min_val: Optional[float] = None
        self.max_val: Optional[float] = None
        self.fitted: bool = False

    def fit(self, data: np.ndarray) -> "GlobalMinMaxScaler":
        """Fit the scaler on the provided data"""
        self.min_val = np.min(data)
        self.max_val = np.max(data)
        self.fitted = True

        logger.info(f"GlobalMinMaxScaler fitted: min={self.min_val:.6f}, max={self.max_val:.6f}")
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Transform data using fitted parameters"""
        if not self.fitted:
            raise ValueError("Scaler must be fitted before transform")

        if self.max_val == self.min_val:
            return np.zeros_like(data)

        return (data - self.min_val) / (self.max_val - self.min_val)

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """Fit and transform in one step"""
        return self.fit(data).transform(data)

    def get_params(self) -> Dict[str, float]:
        """Get scaler parameters"""
        return {"min_val": self.min_val, "max_val": self.max_val, "fitted": self.fitted}


class GlobalZScaler:
    """Global Z-score scaler that fits once and applies consistently"""

    def __init__(self):
        self.mean_val: Optional[float] = None
        self.std_val: Optional[float] = None
        self.fitted: bool = False

    def fit(self, data: np.ndarray) -> "GlobalZScaler":
        """Fit the scaler on the provided data"""
        self.mean_val = np.mean(data)
        self.std_val = np.std(data)
        self.fitted = True

        logger.info(f"GlobalZScaler fitted: mean={self.mean_val:.6f}, std={self.std_val:.6f}")
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Transform data using fitted parameters"""
        if not self.fitted:
            raise ValueError("Scaler must be fitted before transform")

        if self.std_val == 0:
            return np.zeros_like(data)

        return (data - self.mean_val) / self.std_val

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """Fit and transform in one step"""
        return self.fit(data).transform(data)

    def get_params(self) -> Dict[str, float]:
        """Get scaler parameters"""
        return {"mean_val": self.mean_val, "std_val": self.std_val, "fitted": self.fitted}


class GlobalRobustScaler:
    """Global robust scaler using median and IQR"""

    def __init__(self):
        self.median_val: Optional[float] = None
        self.iqr_val: Optional[float] = None
        self.fitted: bool = False

    def fit(self, data: np.ndarray) -> "GlobalRobustScaler":
        """Fit the scaler on the provided data"""
        self.median_val = np.median(data)
        q75, q25 = np.percentile(data, [75, 25])
        self.iqr_val = q75 - q25
        self.fitted = True

        logger.info(
            f"GlobalRobustScaler fitted: median={self.median_val:.6f}, iqr={self.iqr_val:.6f}"
        )
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Transform data using fitted parameters"""
        if not self.fitted:
            raise ValueError("Scaler must be fitted before transform")

        if self.iqr_val == 0:
            return np.zeros_like(data)

        return (data - self.median_val) / self.iqr_val

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """Fit and transform in one step"""
        return self.fit(data).transform(data)

    def get_params(self) -> Dict[str, float]:
        """Get scaler parameters"""
        return {"median_val": self.median_val, "iqr_val": self.iqr_val, "fitted": self.fitted}


class GlobalMomentScaler:
    """Global scaler specifically designed for VMM moment conditions"""

    def __init__(self, method: str = "minmax"):
        """
        Initialize global moment scaler

        Args:
            method: Scaling method ('minmax', 'zscore', 'robust')
        """
        self.method = method
        self.scalers: Dict[str, any] = {}
        self.fitted: bool = False

    def fit(self, moment_data: Dict[str, np.ndarray]) -> "GlobalMomentScaler":
        """
        Fit scalers on moment data

        Args:
            moment_data: Dictionary of moment arrays by name
        """
        for moment_name, moment_array in moment_data.items():
            if self.method == "minmax":
                self.scalers[moment_name] = GlobalMinMaxScaler().fit(moment_array)
            elif self.method == "zscore":
                self.scalers[moment_name] = GlobalZScaler().fit(moment_array)
            elif self.method == "robust":
                self.scalers[moment_name] = GlobalRobustScaler().fit(moment_array)
            else:
                raise ValueError(f"Unknown scaling method: {self.method}")

        self.fitted = True
        logger.info(
            f"GlobalMomentScaler fitted with {self.method} method for {len(moment_data)} moment types"
        )
        return self

    def transform(self, moment_data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Transform moment data using fitted scalers

        Args:
            moment_data: Dictionary of moment arrays by name

        Returns:
            Dictionary of scaled moment arrays
        """
        if not self.fitted:
            raise ValueError("Scaler must be fitted before transform")

        scaled_data = {}
        for moment_name, moment_array in moment_data.items():
            if moment_name in self.scalers:
                scaled_data[moment_name] = self.scalers[moment_name].transform(moment_array)
            else:
                logger.warning(f"No scaler found for moment type: {moment_name}")
                scaled_data[moment_name] = moment_array

        return scaled_data

    def fit_transform(self, moment_data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Fit and transform in one step"""
        return self.fit(moment_data).transform(moment_data)

    def get_params(self) -> Dict[str, Dict[str, float]]:
        """Get all scaler parameters"""
        params = {}
        for moment_name, scaler in self.scalers.items():
            params[moment_name] = scaler.get_params()
        return params

    def get_combined_moment_vector(self, moment_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Get combined moment vector from scaled moment data

        Args:
            moment_data: Dictionary of moment arrays by name

        Returns:
            Combined flattened moment vector
        """
        scaled_data = self.transform(moment_data)

        # Combine all moment arrays into a single vector
        moment_vectors = []
        for moment_name in sorted(scaled_data.keys()):  # Sort for consistency
            moment_vectors.append(scaled_data[moment_name].flatten())

        return np.concatenate(moment_vectors)
