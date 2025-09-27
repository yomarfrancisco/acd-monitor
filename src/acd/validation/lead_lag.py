"""
Lead-Lag Causality Detection for ACD Validation Layer

This module implements rolling lead-lag betas and Granger causality tests
to detect price leadership patterns between exchanges.
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests

warnings.filterwarnings("ignore")


@dataclass
class LeadLagConfig:
    """Configuration for lead-lag analysis"""

    window_size: int = 100
    min_lag: int = 1
    max_lag: int = 5
    significance_level: float = 0.05
    min_observations: int = 50
    persistence_threshold: float = 0.6  # Minimum fraction of windows with same leader


@dataclass
class LeadLagResult:
    """Results from lead-lag analysis"""

    # Core metrics
    lead_lag_betas: Dict[Tuple[str, str], float]  # (leader, follower) -> beta
    granger_p_values: Dict[Tuple[str, str], float]  # (leader, follower) -> p-value
    persistence_scores: Dict[str, float]  # exchange -> persistence score
    switching_entropy: float  # Overall entropy of leadership switching

    # Statistical significance
    significant_relationships: List[Tuple[str, str]]  # Significant lead-lag pairs
    avg_granger_p: float  # Average p-value across all pairs

    # Environment-specific results
    env_persistence: Dict[str, Dict[str, float]]  # env -> exchange -> persistence
    env_entropy: Dict[str, float]  # env -> switching entropy

    # Metadata
    n_windows: int
    n_exchanges: int
    config: LeadLagConfig


class LeadLagValidator:
    """Lead-lag causality validator for coordination detection"""

    def __init__(self, config: LeadLagConfig = None):
        self.config = config or LeadLagConfig()

    def analyze_lead_lag(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: str = None,
        seed: int = None,
    ) -> LeadLagResult:
        """
        Analyze lead-lag relationships between exchanges

        Args:
            data: DataFrame with price data and environment info
            price_columns: List of exchange price column names
            environment_column: Column name for environment partitioning
            seed: Random seed for reproducibility

        Returns:
            LeadLagResult with comprehensive lead-lag analysis
        """
        if seed is not None:
            np.random.seed(seed)

        # Extract price data
        prices = data[price_columns].values
        exchanges = price_columns

        # Calculate returns
        returns = np.diff(prices, axis=0)

        # Initialize results containers
        persistence_scores = {ex: 0.0 for ex in exchanges}
        env_persistence = {}
        env_entropy = {}

        # Calculate rolling lead-lag betas
        rolling_betas = self._calculate_rolling_betas(returns, exchanges)

        # Calculate Granger causality tests
        granger_results = self._calculate_granger_tests(returns, exchanges)

        # Calculate persistence scores
        persistence_scores = self._calculate_persistence_scores(rolling_betas, exchanges)

        # Calculate switching entropy
        switching_entropy = self._calculate_switching_entropy(rolling_betas, exchanges)

        # Environment-specific analysis
        if environment_column and environment_column in data.columns:
            env_persistence, env_entropy = self._analyze_by_environment(
                data, returns, exchanges, environment_column
            )

        # Identify significant relationships
        significant_relationships = [
            (leader, follower)
            for (leader, follower), p_val in granger_results.items()
            if p_val < self.config.significance_level
        ]

        # Calculate average Granger p-value
        avg_granger_p = np.mean(list(granger_results.values())) if granger_results else 1.0

        return LeadLagResult(
            lead_lag_betas=rolling_betas,
            granger_p_values=granger_results,
            persistence_scores=persistence_scores,
            switching_entropy=switching_entropy,
            significant_relationships=significant_relationships,
            avg_granger_p=avg_granger_p,
            env_persistence=env_persistence,
            env_entropy=env_entropy,
            n_windows=len(returns) - self.config.window_size + 1,
            n_exchanges=len(exchanges),
            config=self.config,
        )

    def _calculate_rolling_betas(
        self, returns: np.ndarray, exchanges: List[str]
    ) -> Dict[Tuple[str, str], float]:
        """Calculate rolling lead-lag betas between all exchange pairs"""
        betas = {}
        n_obs, n_exchanges = returns.shape

        for i in range(n_exchanges):
            for j in range(n_exchanges):
                if i == j:
                    continue

                leader, follower = exchanges[i], exchanges[j]

                # Calculate rolling beta using OLS
                rolling_beta = self._rolling_ols_beta(
                    returns[:, i], returns[:, j], self.config.window_size
                )

                # Average beta across all windows
                avg_beta = np.nanmean(rolling_beta)
                betas[(leader, follower)] = avg_beta

        return betas

    def _rolling_ols_beta(self, x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
        """Calculate rolling OLS beta coefficient"""
        n = len(x)
        betas = np.full(n - window + 1, np.nan)

        for i in range(n - window + 1):
            x_window = x[i : i + window]
            y_window = y[i : i + window]

            # Skip if insufficient data or no variation
            if len(x_window) < self.config.min_observations or np.std(x_window) < 1e-8:
                continue

            try:
                # OLS regression: y = alpha + beta * x
                X = np.column_stack([np.ones(len(x_window)), x_window])
                beta = np.linalg.lstsq(X, y_window, rcond=None)[0][1]
                betas[i] = beta
            except np.linalg.LinAlgError:
                continue

        return betas

    def _calculate_granger_tests(
        self, returns: np.ndarray, exchanges: List[str]
    ) -> Dict[Tuple[str, str], float]:
        """Calculate Granger causality tests between exchange pairs"""
        granger_results = {}
        n_obs, n_exchanges = returns.shape

        for i in range(n_exchanges):
            for j in range(n_exchanges):
                if i == j:
                    continue

                leader, follower = exchanges[i], exchanges[j]

                try:
                    # Prepare data for Granger test
                    data = np.column_stack([returns[:, j], returns[:, i]])  # [follower, leader]

                    # Skip if insufficient data
                    if len(data) < self.config.min_observations:
                        granger_results[(leader, follower)] = 1.0
                        continue

                    # Perform Granger causality test
                    gc_result = grangercausalitytests(
                        data, maxlag=self.config.max_lag, verbose=False
                    )

                    # Extract p-value for the optimal lag
                    best_lag = min(self.config.max_lag, len(data) // 4)
                    if best_lag in gc_result:
                        p_value = gc_result[best_lag][0]["ssr_ftest"][1]  # F-test p-value
                        granger_results[(leader, follower)] = p_value
                    else:
                        granger_results[(leader, follower)] = 1.0

                except Exception:
                    granger_results[(leader, follower)] = 1.0

        return granger_results

    def _calculate_persistence_scores(
        self, rolling_betas: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> Dict[str, float]:
        """Calculate persistence scores for each exchange"""
        persistence_scores = {}

        for exchange in exchanges:
            # Count how many times this exchange leads others
            lead_count = 0
            total_pairs = 0

            for (leader, follower), beta in rolling_betas.items():
                if leader == exchange:
                    total_pairs += 1
                    if beta > 0.1:  # Positive beta indicates leadership
                        lead_count += 1

            # Calculate persistence score
            persistence_scores[exchange] = lead_count / max(total_pairs, 1)

        return persistence_scores

    def _calculate_switching_entropy(
        self, rolling_betas: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> float:
        """Calculate switching entropy of leadership patterns"""
        # This is a simplified version - in practice, you'd track leadership over time
        # For now, we'll calculate entropy based on the distribution of leadership

        leader_counts = {ex: 0 for ex in exchanges}
        total_relationships = 0

        for (leader, follower), beta in rolling_betas.items():
            if beta > 0.1:  # Positive beta indicates leadership
                leader_counts[leader] += 1
                total_relationships += 1

        if total_relationships == 0:
            return 0.0

        # Calculate entropy
        probabilities = [count / total_relationships for count in leader_counts.values()]
        entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in probabilities)

        # Normalize by maximum possible entropy
        max_entropy = np.log2(len(exchanges))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        return normalized_entropy

    def _analyze_by_environment(
        self, data: pd.DataFrame, returns: np.ndarray, exchanges: List[str], environment_column: str
    ) -> Tuple[Dict, Dict]:
        """Analyze lead-lag patterns by environment"""
        env_persistence = {}
        env_entropy = {}

        environments = data[environment_column].unique()

        for env in environments:
            env_mask = data[environment_column] == env
            env_returns = returns[env_mask[1:]]  # Adjust for returns lag

            if len(env_returns) < self.config.min_observations:
                continue

            # Calculate rolling betas for this environment
            env_betas = self._calculate_rolling_betas(env_returns, exchanges)

            # Calculate persistence scores for this environment
            env_persistence[env] = self._calculate_persistence_scores(env_betas, exchanges)

            # Calculate switching entropy for this environment
            env_entropy[env] = self._calculate_switching_entropy(env_betas, exchanges)

        return env_persistence, env_entropy


def analyze_lead_lag(
    data: pd.DataFrame,
    price_columns: List[str],
    environment_column: str = None,
    config: LeadLagConfig = None,
    seed: int = None,
) -> LeadLagResult:
    """
    Convenience function for lead-lag analysis

    Args:
        data: DataFrame with price data and environment info
        price_columns: List of exchange price column names
        environment_column: Column name for environment partitioning
        config: LeadLagConfig instance
        seed: Random seed for reproducibility

    Returns:
        LeadLagResult with comprehensive lead-lag analysis
    """
    validator = LeadLagValidator(config)
    return validator.analyze_lead_lag(data, price_columns, environment_column, seed)
