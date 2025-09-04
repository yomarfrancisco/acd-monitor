"""
VMM Moment Conditions
Computes sample moments and targets per window for variational inference
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass
class MomentTargets:
    """Target values for moment conditions"""

    beta_0: np.ndarray  # First moment target
    sigma_0: np.ndarray  # Second moment target (variance)
    rho_0: np.ndarray  # Temporal cross-moment target


@dataclass
class SampleMoments:
    """Sample moments computed from data window"""

    beta_t: np.ndarray  # Current beta estimates
    beta_t_1: np.ndarray  # Lagged beta estimates
    sample_mean: np.ndarray
    sample_var: np.ndarray
    sample_cov: np.ndarray


class MomentConditions:
    """Implements moment conditions for VMM as per Brief 55+ and Product Spec"""

    def __init__(self):
        """Initialize moment conditions calculator"""

    def compute_moment_targets(self, historical_data: pd.DataFrame, beta_dim: int) -> MomentTargets:
        """
        Compute target values for moment conditions from historical data

        Args:
            historical_data: Historical pricing data for calibration
            beta_dim: Dimension of beta parameter vector

        Returns:
            MomentTargets with calibrated target values
        """
        # For now, use simple empirical targets
        # In production, these would be calibrated from historical competitive periods

        beta_0 = np.zeros(beta_dim)  # Competitive baseline: no systematic bias
        sigma_0 = np.eye(beta_dim) * 0.1  # Moderate variation expected
        rho_0 = np.eye(beta_dim) * 0.3  # Some temporal persistence

        return MomentTargets(beta_0=beta_0, sigma_0=sigma_0, rho_0=rho_0)

    def extract_beta_estimates(
        self, window_data: pd.DataFrame, price_cols: list
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract beta estimates from pricing data window

        Args:
            window_data: Data window for analysis
            price_cols: Column names for price series

        Returns:
            Tuple of (current_betas, lagged_betas)
        """
        if len(window_data) < 2:
            raise ValueError("Window must contain at least 2 observations")

        # Simple approach: use price differences as beta proxies
        # In production, this would use proper econometric estimation

        prices = window_data[price_cols].values
        n_firms = len(price_cols)

        # Compute price changes (simplified beta estimation)
        price_changes = np.diff(prices, axis=0)

        # For now, use simple correlation-based betas
        betas = np.zeros((len(price_changes), n_firms))

        for i in range(n_firms):
            for j in range(n_firms):
                if i != j:
                    # Simple correlation as beta proxy
                    corr = np.corrcoef(price_changes[:, i], price_changes[:, j])[0, 1]
                    if not np.isnan(corr):
                        betas[:, i] += corr * price_changes[:, j]

        # Current and lagged betas
        current_betas = betas[1:]  # Skip first observation
        lagged_betas = betas[:-1]  # Lag by one period

        return current_betas, lagged_betas

    def compute_sample_moments(
        self, current_betas: np.ndarray, lagged_betas: np.ndarray
    ) -> SampleMoments:
        """
        Compute sample moments from beta estimates

        Args:
            current_betas: Current period beta estimates
            lagged_betas: Previous period beta estimates

        Returns:
            SampleMoments with computed statistics
        """
        if len(current_betas) != len(lagged_betas):
            raise ValueError("Current and lagged betas must have same length")

        # Sample moments
        sample_mean = np.mean(current_betas, axis=0)
        sample_var = np.var(current_betas, axis=0)

        # Temporal cross-moment (covariance between current and lagged)
        sample_cov = np.zeros_like(sample_var)
        for i in range(current_betas.shape[1]):
            valid_mask = ~(np.isnan(current_betas[:, i]) | np.isnan(lagged_betas[:, i]))
            if np.sum(valid_mask) > 1:
                sample_cov[i] = np.cov(current_betas[valid_mask, i], lagged_betas[valid_mask, i])[
                    0, 1
                ]

        return SampleMoments(
            beta_t=current_betas,
            beta_t_1=lagged_betas,
            sample_mean=sample_mean,
            sample_var=sample_var,
            sample_cov=sample_cov,
        )

    def evaluate_moment_conditions(
        self, sample_moments: SampleMoments, targets: MomentTargets
    ) -> Dict[str, np.ndarray]:
        """
        Evaluate moment conditions: g(θ) = 0

        Args:
            sample_moments: Computed sample moments
            targets: Target values for moment conditions

        Returns:
            Dictionary of moment condition evaluations
        """
        # First moment condition: E[β_t] = β_0
        g1 = sample_moments.sample_mean - targets.beta_0

        # Second moment condition: Var[β_t] = Σ_0
        g2 = sample_moments.sample_var - np.diag(targets.sigma_0)

        # Temporal cross-moment: Cov[β_t, β_{t-1}] = ρ_0
        g3 = sample_moments.sample_cov - np.diag(targets.rho_0)

        return {"first_moment": g1, "second_moment": g2, "temporal_moment": g3}

    def compute_moment_weights(
        self, sample_moments: SampleMoments, targets: MomentTargets
    ) -> np.ndarray:
        """
        Compute optimal weights for moment conditions

        Args:
            sample_moments: Sample moments
            targets: Moment condition targets

        Returns:
            Weight matrix for moment conditions
        """
        # Simple approach: identity weights
        # In production, this would use optimal GMM weighting

        n_moments = 3  # First, second, temporal
        n_params = len(targets.beta_0)

        # Identity weight matrix (can be enhanced with optimal weighting)
        weights = np.eye(n_moments * n_params)

        return weights
