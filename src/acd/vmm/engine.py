"""
VMM Engine
Main orchestration and public API for VMM continuous monitoring
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .profiles import VMMConfig
from .moments import MomentConditions, MomentTargets, SampleMoments
from .updates import VariationalUpdates, VariationalParams, UpdateState
from .metrics import MetricsCalibration, VMMMetrics


@dataclass
class VMMState:
    """Internal state for VMM processing"""

    current_window: pd.DataFrame
    price_columns: List[str]
    beta_dimension: int
    moment_targets: MomentTargets
    variational_params: Optional[VariationalParams] = None
    update_state: Optional[UpdateState] = None
    metrics: Optional[VMMMetrics] = None


@dataclass
class VMMOutput:
    """Public output from VMM analysis"""

    regime_confidence: float  # ∈ [0,1] - coordination-like vs competitive-like
    structural_stability: float  # ∈ [0,1] - higher = more invariant
    environment_quality: float  # ∈ [0,1] - data/context quality proxy
    dynamic_validation_score: float  # ∈ [0,1] - self-consistency + predictive checks

    # Metadata
    window_size: int
    convergence_status: str
    iterations: int
    elbo_final: float

    # Raw outputs for debugging
    variational_params: Optional[VariationalParams] = None
    moment_conditions: Optional[Dict[str, np.ndarray]] = None


class VMMEngine:
    """Main VMM engine implementing continuous monitoring"""

    def __init__(self, config: VMMConfig):
        """Initialize VMM engine with configuration"""
        self.config = config
        self.moment_calculator = MomentConditions()
        self.variational_updater = VariationalUpdates(config)
        self.metrics_calibrator = MetricsCalibration()

    def _validate_input(self, window: pd.DataFrame, price_cols: List[str]) -> None:
        """Validate input data requirements"""
        if window.empty:
            raise ValueError("Window data cannot be empty")

        if len(price_cols) < 2:
            raise ValueError("At least 2 price columns required")

        missing_cols = [col for col in price_cols if col not in window.columns]
        if missing_cols:
            raise ValueError(f"Missing price columns: {missing_cols}")

        if len(window) < self.config.min_data_points:
            raise ValueError(f"Insufficient data: {len(window)} < {self.config.min_data_points}")

    def _extract_price_data(self, window: pd.DataFrame, price_cols: List[str]) -> pd.DataFrame:
        """Extract and clean price data"""
        price_data = window[price_cols].copy()

        # Handle missing values (simple forward fill for now)
        price_data = price_data.fillna(method="ffill").fillna(method="bfill")

        # Remove rows with all NaN values
        price_data = price_data.dropna(how="all")

        return price_data

    def _compute_moment_targets(
        self, historical_data: pd.DataFrame, beta_dim: int
    ) -> MomentTargets:
        """Compute moment condition targets from historical data"""
        return self.moment_calculator.compute_moment_targets(historical_data, beta_dim)

    def _extract_beta_estimates(self, window_data: pd.DataFrame, price_cols: List[str]) -> tuple:
        """Extract beta estimates from pricing data"""
        return self.moment_calculator.extract_beta_estimates(window_data, price_cols)

    def _compute_sample_moments(
        self, current_betas: np.ndarray, lagged_betas: np.ndarray
    ) -> SampleMoments:
        """Compute sample moments from beta estimates"""
        return self.moment_calculator.compute_sample_moments(current_betas, lagged_betas)

    def _evaluate_moment_conditions(
        self, sample_moments: SampleMoments, targets: MomentTargets
    ) -> Dict[str, np.ndarray]:
        """Evaluate moment conditions"""
        return self.moment_calculator.evaluate_moment_conditions(sample_moments, targets)

    def _compute_moment_weights(
        self, sample_moments: SampleMoments, targets: MomentTargets
    ) -> np.ndarray:
        """Compute moment condition weights"""
        return self.moment_calculator.compute_moment_weights(sample_moments, targets)

    def _run_variational_optimization(
        self,
        initial_params: VariationalParams,
        moment_conditions: Dict[str, np.ndarray],
        weights: np.ndarray,
    ) -> tuple:
        """Run variational optimization loop"""
        return self.variational_updater.run_variational_optimization(
            initial_params, moment_conditions, weights
        )

    def _compute_metrics(
        self,
        variational_params: VariationalParams,
        moment_conditions: Dict[str, np.ndarray],
        update_state: UpdateState,
        window_data: pd.DataFrame,
        price_cols: List[str],
    ) -> VMMMetrics:
        """Compute all calibrated metrics"""
        return self.metrics_calibrator.compute_all_metrics(
            variational_params, moment_conditions, update_state, window_data, price_cols
        )

    def _create_output(
        self,
        metrics: VMMMetrics,
        window_size: int,
        update_state: UpdateState,
        variational_params: VariationalParams,
        moment_conditions: Dict[str, np.ndarray],
    ) -> VMMOutput:
        """Create final VMM output"""
        # Determine convergence status
        if update_state.convergence_flag:
            convergence_status = "converged"
        elif update_state.divergence_flag:
            convergence_status = "diverged"
        elif update_state.plateau_flag:
            convergence_status = "plateau"
        else:
            convergence_status = "max_iterations"

        # Get final ELBO
        elbo_final = update_state.elbo_history[-1] if update_state.elbo_history else 0.0

        return VMMOutput(
            regime_confidence=metrics.regime_confidence,
            structural_stability=metrics.structural_stability,
            environment_quality=metrics.environment_quality,
            dynamic_validation_score=metrics.dynamic_validation_score,
            window_size=window_size,
            convergence_status=convergence_status,
            iterations=update_state.iteration,
            elbo_final=elbo_final,
            variational_params=variational_params,
            moment_conditions=moment_conditions,
        )

    def run_vmm(
        self,
        window: pd.DataFrame,
        price_cols: List[str],
        historical_data: Optional[pd.DataFrame] = None,
    ) -> VMMOutput:
        """
        Main VMM analysis function

        Args:
            window: Data window for analysis
            price_cols: Column names for price series
            historical_data: Optional historical data for moment target calibration

        Returns:
            VMMOutput with all calibrated metrics
        """
        # Input validation
        self._validate_input(window, price_cols)

        # Extract and clean price data
        price_data = self._extract_price_data(window, price_cols)

        # Determine beta dimension (number of firms)
        beta_dim = len(price_cols)

        # Compute moment targets (use provided historical data or defaults)
        if historical_data is not None:
            moment_targets = self._compute_moment_targets(historical_data, beta_dim)
        else:
            # Use default targets for competitive baseline
            moment_targets = MomentTargets(
                beta_0=np.zeros(beta_dim),
                sigma_0=np.eye(beta_dim) * 0.1,
                rho_0=np.eye(beta_dim) * 0.3,
            )

        # Extract beta estimates
        current_betas, lagged_betas = self._extract_beta_estimates(price_data, price_cols)

        # Compute sample moments
        sample_moments = self._compute_sample_moments(current_betas, lagged_betas)

        # Evaluate moment conditions
        moment_conditions = self._evaluate_moment_conditions(sample_moments, moment_targets)

        # Compute moment weights
        weights = self._compute_moment_weights(sample_moments, moment_targets)

        # Initialize variational parameters
        initial_params = self.variational_updater.initialize_variational_params(beta_dim)

        # Run variational optimization
        final_params, update_state = self._run_variational_optimization(
            initial_params, moment_conditions, weights
        )

        # Compute calibrated metrics
        metrics = self._compute_metrics(
            final_params, moment_conditions, update_state, price_data, price_cols
        )

        # Create final output
        output = self._create_output(
            metrics, len(price_data), update_state, final_params, moment_conditions
        )

        return output


def run_vmm(window: pd.DataFrame, config: VMMConfig) -> VMMOutput:
    """
    Public function for running VMM analysis

    Args:
        window: Data window for analysis (must contain price columns)
        config: VMM configuration

    Returns:
        VMMOutput with all calibrated metrics
    """
    # Auto-detect price columns (assume columns ending with '_price' or containing 'price')
    price_cols = [col for col in window.columns if "price" in col.lower()]

    if not price_cols:
        # Fallback: assume first few numeric columns are prices
        numeric_cols = window.select_dtypes(include=[np.number]).columns.tolist()
        price_cols = numeric_cols[: min(3, len(numeric_cols))]

    if len(price_cols) < 2:
        raise ValueError("Could not identify sufficient price columns for VMM analysis")

    # Create engine and run analysis
    engine = VMMEngine(config)
    return engine.run_vmm(window, price_cols)
