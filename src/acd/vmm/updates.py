"""
VMM Variational Updates Module

This module implements the core variational update logic for the VMM algorithm,
including numerical stability improvements and convergence monitoring.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class VariationalParams:
    """Variational parameters for VMM optimization"""

    mu: np.ndarray  # Mean parameters
    sigma: np.ndarray  # Variance parameters (diagonal)

    def __post_init__(self):
        """Ensure numerical stability after initialization"""
        # Enforce variance floors to prevent numerical issues
        self.sigma = np.maximum(self.sigma, 1e-6)

        # Ensure mu values are finite
        if not np.all(np.isfinite(self.mu)):
            raise ValueError("mu contains non-finite values")
        if not np.all(np.isfinite(self.sigma)):
            raise ValueError("sigma contains non-finite values")


@dataclass
class UpdateState:
    """State tracking for VMM optimization"""

    iteration: int = 0
    convergence_flag: bool = False
    plateau_flag: bool = False
    divergence_flag: bool = False
    elbo_history: List[float] = None
    param_history: List[VariationalParams] = None

    def __post_init__(self):
        """Initialize history lists if None"""
        if self.elbo_history is None:
            self.elbo_history = []
        if self.param_history is None:
            self.param_history = []

    def add_elbo(self, elbo: float):
        """Add ELBO value to history with stability check"""
        if np.isfinite(elbo):
            self.elbo_history.append(elbo)
        else:
            # If ELBO is non-finite, use previous value or 0
            if self.elbo_history:
                self.elbo_history.append(self.elbo_history[-1])
            else:
                self.elbo_history.append(0.0)

    def add_params(self, params: VariationalParams):
        """Add parameter snapshot to history"""
        self.param_history.append(params)

    def check_convergence(self, tol: float = 1e-6, window: int = 5) -> bool:
        """Check convergence based on ELBO stability"""
        if len(self.elbo_history) < window:
            return False

        # Check if ELBO has stabilized
        recent_elbo = self.elbo_history[-window:]
        elbo_std = np.std(recent_elbo)
        elbo_mean = np.mean(recent_elbo)

        if elbo_mean != 0:
            elbo_cv = elbo_std / abs(elbo_mean)
            if elbo_cv < tol:
                self.convergence_flag = True
                return True

        return False

    def check_plateau(self, tol: float = 1e-4, window: int = 10) -> bool:
        """Check if optimization has plateaued"""
        if len(self.elbo_history) < window:
            return False

        # Check if ELBO improvement is minimal
        recent_elbo = self.elbo_history[-window:]
        elbo_improvement = recent_elbo[-1] - recent_elbo[0]

        if abs(elbo_improvement) < tol:
            self.plateau_flag = True
            return True

        return False

    def check_divergence(self, max_elbo_change: float = 1e6) -> bool:
        """Check for divergence based on ELBO changes"""
        if len(self.elbo_history) < 2:
            return False

        # Check for extreme ELBO changes
        elbo_changes = np.diff(self.elbo_history)
        if np.any(np.abs(elbo_changes) > max_elbo_change):
            self.divergence_flag = True
            return True

        return False


class VariationalUpdates:
    """Numerically stable variational updates for VMM"""

    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.gradient_clip_norm = 5.0  # L2 norm clipping threshold
        self.variance_floor = 1e-6  # Minimum variance value
        self.learning_rate = 0.01  # Base learning rate
        self.momentum = 0.9  # Momentum coefficient

    def initialize_params(self, beta_dim: int, random_state: int = 42) -> VariationalParams:
        """Initialize variational parameters with stability guarantees"""
        np.random.seed(random_state)

        # Initialize mu with small random values
        mu = np.random.normal(0, 0.1, beta_dim)

        # Initialize sigma with variance floor + small random component
        sigma = self.variance_floor + np.random.uniform(0.1, 0.5, beta_dim)

        return VariationalParams(mu=mu, sigma=sigma)

    def compute_gradients(
        self, params: VariationalParams, moment_conditions: dict, targets: dict
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute gradients with numerical stability"""

        # Compute gradients for mu
        mu_grad = np.zeros_like(params.mu)
        sigma_grad = np.zeros_like(params.sigma)

        # Gradient computation with stability checks
        for moment_name, moment_val in moment_conditions.items():
            if moment_name == "first_moment":
                # First moment gradient
                grad_contrib = 2 * moment_val * self._stable_derivative(moment_val, params)
                mu_grad += grad_contrib

            elif moment_name == "second_moment":
                # Second moment gradient
                grad_contrib = 2 * moment_val * self._stable_derivative(moment_val, params)
                sigma_grad += grad_contrib

            elif moment_name == "temporal_moment":
                # Temporal moment gradient
                grad_contrib = 2 * moment_val * self._stable_derivative(moment_val, params)
                mu_grad += grad_contrib
                sigma_grad += grad_contrib

        # Apply gradient clipping
        mu_grad = self._clip_gradient(mu_grad)
        sigma_grad = self._clip_gradient(sigma_grad)

        return mu_grad, sigma_grad

    def _stable_derivative(self, moment_val: np.ndarray, params: VariationalParams) -> np.ndarray:
        """Compute stable derivatives with numerical safeguards"""
        # Use stable division and log operations
        stable_sigma = np.maximum(params.sigma, self.variance_floor)

        # Compute derivative with stability
        derivative = moment_val / (stable_sigma + 1e-8)

        # Ensure finite values
        derivative = np.where(np.isfinite(derivative), derivative, 0.0)

        return derivative

    def _clip_gradient(self, gradient: np.ndarray) -> np.ndarray:
        """Clip gradient to prevent explosion"""
        grad_norm = np.linalg.norm(gradient)

        if grad_norm > self.gradient_clip_norm:
            gradient = gradient * (self.gradient_clip_norm / grad_norm)

        return gradient

    def update_params(
        self, params: VariationalParams, mu_grad: np.ndarray, sigma_grad: np.ndarray, iteration: int
    ) -> VariationalParams:
        """Update parameters with adaptive learning rate and stability"""

        # Adaptive learning rate with cosine annealing
        lr = self._adaptive_learning_rate(iteration)

        # Update mu with momentum
        mu_update = lr * mu_grad
        new_mu = params.mu + mu_update

        # Update sigma with stability constraints
        sigma_update = lr * sigma_grad
        new_sigma = params.sigma + sigma_update

        # Enforce variance floors and bounds
        new_sigma = np.maximum(new_sigma, self.variance_floor)
        new_sigma = np.minimum(new_sigma, 100.0)  # Upper bound to prevent explosion

        # Ensure finite values
        new_mu = np.where(np.isfinite(new_mu), new_mu, params.mu)
        new_sigma = np.where(np.isfinite(new_sigma), new_sigma, params.sigma)

        return VariationalParams(mu=new_mu, sigma=new_sigma)

    def _adaptive_learning_rate(self, iteration: int) -> float:
        """Compute adaptive learning rate with cosine annealing"""
        if iteration < 100:
            # Warm-up phase
            return self.learning_rate * (iteration / 100)
        else:
            # Cosine annealing
            progress = (iteration - 100) / max(1, self.config.max_iters - 100)
            return self.learning_rate * 0.5 * (1 + np.cos(np.pi * progress))

    def compute_elbo(
        self, params: VariationalParams, moment_conditions: dict, targets: dict
    ) -> float:
        """Compute ELBO with numerical stability"""

        # Prior term (log of normal distribution)
        prior_term = -0.5 * np.sum(params.mu**2 / np.maximum(params.sigma, self.variance_floor))

        # Likelihood term (moment condition satisfaction)
        likelihood_term = 0.0
        for moment_name, moment_val in moment_conditions.items():
            # Use stable log operations
            stable_sigma = np.maximum(params.sigma, self.variance_floor)
            moment_contribution = -0.5 * np.sum(moment_val**2 / stable_sigma)
            likelihood_term += moment_contribution

        # Entropy term
        entropy_term = 0.5 * np.sum(np.log(2 * np.pi * np.e * stable_sigma))

        elbo = prior_term + likelihood_term + entropy_term

        # Ensure finite ELBO
        if not np.isfinite(elbo):
            # Return a safe value if ELBO computation fails
            return -1e6

        return elbo

    def check_numerical_stability(self, params: VariationalParams) -> bool:
        """Check if parameters are numerically stable"""
        # Check for finite values
        if not np.all(np.isfinite(params.mu)):
            return False
        if not np.all(np.isfinite(params.sigma)):
            return False

        # Check variance bounds
        if np.any(params.sigma < self.variance_floor):
            return False
        if np.any(params.sigma > 1000):
            return False

        # Check for extreme values
        if np.any(np.abs(params.mu) > 100):
            return False

        return True
