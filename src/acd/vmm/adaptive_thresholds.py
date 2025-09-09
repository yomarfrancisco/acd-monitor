"""
ACD Monitor Adaptive Threshold Framework

Implements dataset-size-aware thresholds for spurious regime detection:
- Small datasets (≤200 windows): ≤2% spurious rate
- Medium datasets (201–800): ≤5%
- Large datasets (>800): ≤8%

All thresholds are configurable via profiles and applied consistently across
calibration reports and evidence bundles.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveThresholdConfig:
    """Configuration for adaptive threshold framework."""

    # Base thresholds
    small_dataset_threshold: float = 0.02  # ≤200 windows: ≤2%
    medium_dataset_threshold: float = 0.05  # 201-800 windows: ≤5%
    large_dataset_threshold: float = 0.08  # >800 windows: ≤8%

    # Dataset size boundaries
    small_dataset_max: int = 200
    medium_dataset_max: int = 800

    # Continuous scaling parameters (for smooth transitions)
    enable_continuous_scaling: bool = True
    scaling_factor: float = 0.006  # Per window increase for medium datasets

    # Validation parameters
    strict_mode: bool = True  # Fail fast on threshold violations
    log_threshold_applied: bool = True  # Log which threshold was used

    def __post_init__(self):
        """Validate configuration parameters."""
        if not (
            0
            < self.small_dataset_threshold
            < self.medium_dataset_threshold
            < self.large_dataset_threshold
            < 1
        ):
            raise ValueError("Thresholds must be strictly increasing between 0 and 1")

        if self.small_dataset_max >= self.medium_dataset_max:
            raise ValueError("Dataset size boundaries must be strictly increasing")

        if self.scaling_factor <= 0:
            raise ValueError("Scaling factor must be positive")


class AdaptiveThresholdManager:
    """Manages adaptive thresholds for spurious regime detection."""

    def __init__(self, config: Optional[AdaptiveThresholdConfig] = None):
        """Initialize threshold manager with configuration."""
        self.config = config or AdaptiveThresholdConfig()
        logger.info(f"Initialized AdaptiveThresholdManager with config: {self.config}")

    def get_threshold(self, dataset_size: int) -> float:
        """
        Get appropriate threshold for dataset size.

        Args:
            dataset_size: Number of windows in dataset

        Returns:
            Threshold value (0.0 to 1.0) for spurious regime rate
        """
        if dataset_size <= 0:
            raise ValueError(f"Dataset size must be positive, got {dataset_size}")

        if dataset_size <= self.config.small_dataset_max:
            threshold = self.config.small_dataset_threshold
            threshold_type = "small"
        elif dataset_size <= self.config.medium_dataset_max:
            if self.config.enable_continuous_scaling:
                # Continuous scaling: base + (size - small_max) * scaling_factor
                base = self.config.small_dataset_threshold
                size_factor = (
                    dataset_size - self.config.small_dataset_max
                ) * self.config.scaling_factor
                threshold = min(base + size_factor, self.config.medium_dataset_threshold)
            else:
                threshold = self.config.medium_dataset_threshold
            threshold_type = "medium"
        else:
            threshold = self.config.large_dataset_threshold
            threshold_type = "large"

        if self.config.log_threshold_applied:
            logger.info(
                f"Dataset size {dataset_size}: applying {threshold_type} threshold {threshold:.3f}"
            )

        return threshold

    def validate_spurious_rate(
        self, dataset_size: int, spurious_rate: float
    ) -> Dict[str, Union[bool, float, str]]:
        """
        Validate spurious regime rate against adaptive threshold.

        Args:
            dataset_size: Number of windows in dataset
            spurious_rate: Observed spurious regime rate (0.0 to 1.0)

        Returns:
            Validation result with pass/fail status and details
        """
        threshold = self.get_threshold(dataset_size)

        # Determine dataset category
        if dataset_size <= self.config.small_dataset_max:
            category = "small"
        elif dataset_size <= self.config.medium_dataset_max:
            category = "medium"
        else:
            category = "large"

        # Check if rate passes threshold
        passes = spurious_rate <= threshold

        result = {
            "passes": passes,
            "dataset_size": dataset_size,
            "dataset_category": category,
            "threshold_applied": threshold,
            "spurious_rate": spurious_rate,
            "margin": threshold - spurious_rate,
            "strict_mode": self.config.strict_mode,
        }

        if not passes and self.config.strict_mode:
            logger.warning(
                f"Spurious rate {spurious_rate:.3f} exceeds {category} dataset threshold {threshold:.3f} "
                f"(dataset size: {dataset_size})"
            )

        return result

    def get_threshold_profile(self) -> Dict[str, Union[float, int, str]]:
        """Get current threshold profile for documentation and export."""
        return {
            "framework_version": "1.0.0",
            "small_dataset": {
                "max_size": self.config.small_dataset_max,
                "threshold": self.config.small_dataset_threshold,
                "description": f"≤{self.config.small_dataset_max} windows: ≤{self.config.small_dataset_threshold:.1%}",
            },
            "medium_dataset": {
                "min_size": self.config.small_dataset_max + 1,
                "max_size": self.config.medium_dataset_max,
                "threshold": self.config.medium_dataset_threshold,
                "description": f"{self.config.small_dataset_max + 1}-{self.config.medium_dataset_max} windows: ≤{self.config.medium_dataset_threshold:.1%}",
            },
            "large_dataset": {
                "min_size": self.config.medium_dataset_max + 1,
                "threshold": self.config.large_dataset_threshold,
                "description": f">{self.config.medium_dataset_max} windows: ≤{self.config.large_dataset_threshold:.1%}",
            },
            "continuous_scaling": {
                "enabled": self.config.enable_continuous_scaling,
                "scaling_factor": self.config.scaling_factor,
                "description": "Smooth threshold transitions for medium datasets",
            },
            "strict_mode": self.config.strict_mode,
        }


# Default threshold profiles for common use cases
DEFAULT_PROFILES = {
    "conservative": AdaptiveThresholdConfig(
        small_dataset_threshold=0.015,  # 1.5%
        medium_dataset_threshold=0.04,  # 4%
        large_dataset_threshold=0.06,  # 6%
        strict_mode=True,
    ),
    "balanced": AdaptiveThresholdConfig(
        small_dataset_threshold=0.02,  # 2%
        medium_dataset_threshold=0.05,  # 5%
        large_dataset_threshold=0.08,  # 8%
        strict_mode=True,
    ),
    "permissive": AdaptiveThresholdConfig(
        small_dataset_threshold=0.025,  # 2.5%
        medium_dataset_threshold=0.06,  # 6%
        large_dataset_threshold=0.10,  # 10%
        strict_mode=False,
    ),
}


def get_profile(profile_name: str = "balanced") -> AdaptiveThresholdConfig:
    """Get predefined threshold profile by name."""
    if profile_name not in DEFAULT_PROFILES:
        available = ", ".join(DEFAULT_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")

    return DEFAULT_PROFILES[profile_name]
