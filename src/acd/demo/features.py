"""Feature engineering for ACD Monitor demo pipeline."""

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from ..data.features import DataWindowing
from ..vmm import VMMConfig, VMMOutput, run_vmm

logger = logging.getLogger(__name__)


class DemoFeatureEngineering:
    """Feature engineering for demo pipeline VMM analysis."""

    def __init__(self):
        """Initialize demo feature engineering."""
        # We don't actually need DataWindowing for the demo, so let's skip it
        self.feature_engine = None
        self.vmm_config = VMMConfig(max_iters=100, tol=1e-4, step_initial=0.01)

    def prepare_vmm_windows(self, data: pd.DataFrame, window_size: int = 50) -> List[pd.DataFrame]:
        """Transform raw data into VMM-ready windows.

        Args:
            data: Raw market data
            window_size: Number of observations per window

        Returns:
            List of windowed DataFrames
        """
        windows = []

        # Ensure data is sorted by timestamp
        if "timestamp" in data.columns:
            data = data.sort_values("timestamp").reset_index(drop=True)

        # Create rolling windows
        for start_idx in range(0, len(data), window_size):
            end_idx = min(start_idx + window_size, len(data))
            window_data = data.iloc[start_idx:end_idx].copy()

            if len(window_data) >= window_size // 2:  # Minimum window size
                # Add window metadata
                window_data["window_id"] = f"window_{start_idx//window_size:03d}"
                window_data["window_start"] = start_idx
                window_data["window_end"] = end_idx

                windows.append(window_data)

        return windows

    def extract_vmm_features(self, window_data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract features suitable for VMM analysis.

        Args:
            window_data: Windowed market data

        Returns:
            Dictionary of feature arrays
        """
        features = {}

        # Price-based features
        if "price" in window_data.columns:
            prices = window_data["price"].values
            features["price"] = prices

            # Price changes
            if len(prices) > 1:
                price_changes = np.diff(prices)
                features["price_changes"] = price_changes

                # Rolling statistics
                features["price_mean"] = np.array(
                    [np.mean(prices[: i + 1]) for i in range(len(prices))]
                )
                features["price_std"] = np.array(
                    [np.std(prices[: i + 1]) for i in range(len(prices))]
                )

        # Volume-based features
        if "volume" in window_data.columns:
            volumes = window_data["volume"].values
            features["volume"] = volumes

            if len(volumes) > 1:
                volume_changes = np.diff(volumes)
                features["volume_changes"] = volume_changes

        # Bid-ask spread features
        if "bid" in window_data.columns and "ask" in window_data.columns:
            spreads = window_data["ask"].values - window_data["bid"].values
            features["spreads"] = spreads

            if len(spreads) > 1:
                spread_changes = np.diff(spreads)
                features["spread_changes"] = spread_changes

        # Firm-specific features
        if "firm_id" in window_data.columns:
            firm_ids = window_data["firm_id"].values
            unique_firms = np.unique(firm_ids)

            # Firm concentration (Herfindahl index)
            firm_counts = np.array([np.sum(firm_ids == firm) for firm in unique_firms])
            total_obs = len(firm_ids)
            if total_obs > 0:
                concentration = np.sum((firm_counts / total_obs) ** 2)
                features["firm_concentration"] = np.full(len(window_data), concentration)

        return features

    def run_vmm_analysis(self, window_data: pd.DataFrame) -> VMMOutput:
        """Run VMM analysis on a single window.

        Args:
            window_data: Windowed market data

        Returns:
            VMM analysis results
        """
        try:
            # Debug: check input type
            logger.debug(
                f"run_vmm_analysis input: type={type(window_data)}, columns={getattr(window_data, 'columns', 'no columns')}"
            )

            # Extract features
            features = self.extract_vmm_features(window_data)

            # Prepare data matrix for VMM (firms x time)
            if "price" in features and "firm_id" in window_data.columns:
                # Reshape data for VMM: firms as rows, time as columns
                firm_data = self._reshape_for_vmm(window_data, features)

                # Run VMM
                vmm_result = run_vmm(firm_data, self.vmm_config)
                return vmm_result
            else:
                # Fallback: create dummy VMM result
                return self._create_dummy_vmm_result(window_data)

        except Exception as e:
            logger.warning(f"VMM analysis failed for window: {e}")
            return self._create_dummy_vmm_result(window_data)

    def _reshape_for_vmm(
        self, window_data: pd.DataFrame, features: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """Reshape data for VMM analysis (firms x time)."""
        if "firm_id" not in window_data.columns or "price" not in features:
            raise ValueError("Missing required columns for VMM analysis")

        # Get unique firms and sort
        firms = sorted(window_data["firm_id"].unique())
        time_points = len(window_data)

        # Create firm x time matrix
        firm_matrix = np.zeros((len(firms), time_points))

        # Create a mapping from firm_id to row index
        firm_to_row = {firm: i for i, firm in enumerate(firms)}

        # Fill the matrix by iterating through time points
        for time_idx, (_, row) in enumerate(window_data.iterrows()):
            firm = row["firm_id"]
            price = row["price"]
            row_idx = firm_to_row[firm]
            firm_matrix[row_idx, time_idx] = price

        return firm_matrix

    def _create_dummy_vmm_result(self, window_data: pd.DataFrame) -> VMMOutput:
        """Create a dummy VMM result when analysis fails."""

        # Create dummy result
        dummy_result = VMMOutput(
            regime_confidence=0.5,
            structural_stability=0.5,
            environment_quality=0.5,
            dynamic_validation_score=0.5,
            window_size=len(window_data),
            convergence_status="failed",
            iterations=0,
            elbo_final=0.0,
        )

        return dummy_result

    def prepare_evidence_data(
        self, window_data: pd.DataFrame, vmm_result: VMMOutput, quality_metrics: Dict[str, float]
    ) -> Dict:
        """Prepare data for EvidenceBundle creation.

        Args:
            window_data: Windowed market data
            vmm_result: VMM analysis results
            quality_metrics: Data quality assessment

        Returns:
            Dictionary ready for EvidenceBundle creation
        """
        evidence_data = {
            # Core identification
            "bundle_id": f"demo_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(window_data.shape)) % 10000:04d}",
            "creation_timestamp": pd.Timestamp.now().isoformat(),
            "analysis_window_start": (
                window_data["timestamp"].min().isoformat()
                if "timestamp" in window_data.columns
                else pd.Timestamp.now().isoformat()
            ),
            "analysis_window_end": (
                window_data["timestamp"].max().isoformat()
                if "timestamp" in window_data.columns
                else pd.Timestamp.now().isoformat()
            ),
            "market": "demo_market",
            # VMM outputs
            "vmm_outputs": {
                "regime_confidence": vmm_result.regime_confidence,
                "structural_stability": vmm_result.structural_stability,
                "dynamic_validation_score": vmm_result.dynamic_validation_score,
            },
            # Calibration artifacts (placeholder for demo)
            "calibration_artifacts": [
                {
                    "calibration_method": "demo_placeholder",
                    "calibration_score": 0.8,
                    "calibration_date": pd.Timestamp.now().isoformat(),
                }
            ],
            # Data quality evidence
            "data_quality": {
                "completeness_score": quality_metrics.get("completeness", 0.9),
                "accuracy_score": quality_metrics.get("accuracy", 0.9),
                "timeliness_score": quality_metrics.get("timeliness", 0.9),
                "consistency_score": quality_metrics.get("consistency", 0.9),
                "overall_quality_score": quality_metrics.get("overall", 0.9),
            },
            # Analysis configuration
            "vmm_config": {
                "max_iterations": self.vmm_config.max_iters,
                "tolerance": self.vmm_config.tol,
                "learning_rate": self.vmm_config.step_initial,
            },
            "data_sources": ["demo_market_style", "demo_regulatory_style"],
            # Validation and reproducibility
            "golden_dataset_validation": {
                "spurious_regime_rate": 0.02,  # Demo baseline
                "structural_stability_threshold": 0.6,
                "calibration_accuracy": 0.95,
            },
            "reproducibility_metrics": {
                "checksum_validation": True,
                "schema_compliance": True,
                "timestamp_accuracy": True,
            },
            # Metadata
            "analyst": "demo_pipeline",
            "version": "1.0.0",
        }

        return evidence_data
