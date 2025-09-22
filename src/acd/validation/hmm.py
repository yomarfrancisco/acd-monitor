"""
HMM Regime Detection for ACD Validation Layer

This module implements Hidden Markov Model (HMM) analysis to detect
regime switching patterns in market spreads and price movements,
identifying stable coordination regimes vs competitive volatility.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy import stats
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings("ignore")


@dataclass
class HMMConfig:
    """Configuration for HMM analysis"""

    n_states: int = 3  # Number of hidden states
    window_size: int = 100  # Rolling window size
    min_observations: int = 50  # Minimum observations per state
    convergence_threshold: float = 1e-6  # Convergence threshold
    max_iterations: int = 100  # Maximum EM iterations
    random_state: int = 42  # Random seed for reproducibility


@dataclass
class HMMResult:
    """Results from HMM analysis"""

    # Core metrics
    state_sequence: np.ndarray  # Most likely state sequence
    state_probabilities: np.ndarray  # State probabilities over time
    transition_matrix: np.ndarray  # State transition probabilities
    emission_means: np.ndarray  # Mean emissions for each state
    emission_covariances: np.ndarray  # Covariance matrices for each state

    # Regime analysis
    dwell_times: Dict[int, float]  # Average dwell time per state
    state_frequencies: Dict[int, float]  # Frequency of each state
    regime_stability: float  # Overall regime stability score

    # Environment-specific results
    env_dwell_times: Dict[str, Dict[int, float]]  # env -> state -> dwell time
    env_state_frequencies: Dict[str, Dict[int, float]]  # env -> state -> frequency
    env_stability: Dict[str, float]  # env -> stability score

    # Coordination indicators
    wide_spread_regime: int  # State with widest spreads (coordination indicator)
    lockstep_regime: int  # State with highest correlation (coordination indicator)
    coordination_regime_score: float  # Score for coordination regimes

    # Statistical significance
    log_likelihood: float  # Model log-likelihood
    aic: float  # Akaike Information Criterion
    bic: float  # Bayesian Information Criterion

    # Metadata
    n_observations: int
    n_features: int
    config: HMMConfig


class HMMValidator:
    """HMM regime detection validator for coordination detection"""

    def __init__(self, config: HMMConfig = None):
        self.config = config or HMMConfig()
        self.scaler = StandardScaler()

    def analyze_hmm(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: str = None,
        seed: int = None,
    ) -> HMMResult:
        """
        Analyze regime switching patterns using HMM

        Args:
            data: DataFrame with price data and environment info
            price_columns: List of exchange price column names
            environment_column: Column name for environment partitioning
            seed: Random seed for reproducibility

        Returns:
            HMMResult with comprehensive HMM analysis
        """
        if seed is not None:
            np.random.seed(seed)

        # Extract and prepare features
        features = self._prepare_features(data, price_columns)

        # Fit HMM model
        hmm_model = self._fit_hmm_model(features)

        # Get state sequence and probabilities
        state_sequence = hmm_model.predict(features)
        state_probabilities = hmm_model.predict_proba(features)

        # Calculate regime metrics
        dwell_times = self._calculate_dwell_times(state_sequence)
        state_frequencies = self._calculate_state_frequencies(state_sequence)
        regime_stability = self._calculate_regime_stability(state_sequence, dwell_times)

        # Identify coordination regimes
        wide_spread_regime, lockstep_regime = self._identify_coordination_regimes(
            features, state_sequence, price_columns
        )
        coordination_regime_score = self._calculate_coordination_regime_score(
            state_sequence, wide_spread_regime, lockstep_regime
        )

        # Environment-specific analysis
        env_dwell_times = {}
        env_state_frequencies = {}
        env_stability = {}

        if environment_column and environment_column in data.columns:
            env_dwell_times, env_state_frequencies, env_stability = self._analyze_by_environment(
                data, features, state_sequence, environment_column
            )

        # Calculate model statistics
        log_likelihood = hmm_model.score(features)
        aic = 2 * hmm_model.n_components * (1 + features.shape[1]) - 2 * log_likelihood
        bic = (
            np.log(features.shape[0]) * hmm_model.n_components * (1 + features.shape[1])
            - 2 * log_likelihood
        )

        # Create a dummy transition matrix for GaussianMixture (since it doesn't have transitions)
        dummy_transition_matrix = (
            np.ones((self.config.n_states, self.config.n_states)) / self.config.n_states
        )

        return HMMResult(
            state_sequence=state_sequence,
            state_probabilities=state_probabilities,
            transition_matrix=dummy_transition_matrix,
            emission_means=hmm_model.means_,
            emission_covariances=hmm_model.covariances_,
            dwell_times=dwell_times,
            state_frequencies=state_frequencies,
            regime_stability=regime_stability,
            env_dwell_times=env_dwell_times,
            env_state_frequencies=env_state_frequencies,
            env_stability=env_stability,
            wide_spread_regime=wide_spread_regime,
            lockstep_regime=lockstep_regime,
            coordination_regime_score=coordination_regime_score,
            log_likelihood=log_likelihood,
            aic=aic,
            bic=bic,
            n_observations=len(features),
            n_features=features.shape[1],
            config=self.config,
        )

    def _prepare_features(self, data: pd.DataFrame, price_columns: List[str]) -> np.ndarray:
        """Prepare features for HMM analysis"""
        prices = data[price_columns].values

        # Calculate spreads between exchanges
        spreads = []
        for i in range(len(price_columns)):
            for j in range(i + 1, len(price_columns)):
                spread = np.abs(prices[:, i] - prices[:, j])
                spreads.append(spread)

        # Calculate price changes
        price_changes = np.diff(prices, axis=0)

        # Calculate volatility (rolling window)
        volatility = np.std(price_changes, axis=1)

        # Ensure all arrays have the same length
        min_length = min(len(spreads[0]) if spreads else 0, len(volatility), len(price_changes))
        if min_length == 0:
            min_length = len(prices) - 1

        # Truncate all arrays to the same length
        spreads_truncated = [spread[:min_length] for spread in spreads] if spreads else []
        volatility_truncated = volatility[:min_length]
        price_changes_truncated = price_changes[:min_length]

        # Combine features
        feature_arrays = []
        if spreads_truncated:
            feature_arrays.append(np.array(spreads_truncated).T)  # Spreads between exchanges
        feature_arrays.extend(
            [
                volatility_truncated,  # Price volatility
                np.mean(price_changes_truncated, axis=1),  # Average price change
                np.std(price_changes_truncated, axis=1),  # Price change volatility
            ]
        )

        features = np.column_stack(feature_arrays)

        # Standardize features
        features = self.scaler.fit_transform(features)

        return features

    def _fit_hmm_model(self, features: np.ndarray) -> GaussianMixture:
        """Fit HMM model using Gaussian Mixture Model"""
        hmm_model = GaussianMixture(
            n_components=self.config.n_states,
            covariance_type="full",
            max_iter=self.config.max_iterations,
            tol=self.config.convergence_threshold,
            random_state=self.config.random_state,
        )

        hmm_model.fit(features)
        return hmm_model

    def _calculate_dwell_times(self, state_sequence: np.ndarray) -> Dict[int, float]:
        """Calculate average dwell time for each state"""
        dwell_times = {}

        for state in range(self.config.n_states):
            # Find state transitions
            state_mask = state_sequence == state
            state_changes = np.diff(state_mask.astype(int))

            # Find start and end of state periods
            starts = np.where(state_changes == 1)[0] + 1
            ends = np.where(state_changes == -1)[0] + 1

            # Handle edge cases
            if state_mask[0]:  # State starts at beginning
                starts = np.concatenate([[0], starts])
            if state_mask[-1]:  # State ends at end
                ends = np.concatenate([ends, [len(state_sequence)]])

            # Calculate dwell times
            if len(starts) > 0 and len(ends) > 0:
                dwell_periods = ends - starts
                dwell_times[state] = np.mean(dwell_periods) if len(dwell_periods) > 0 else 0.0
            else:
                dwell_times[state] = 0.0

        return dwell_times

    def _calculate_state_frequencies(self, state_sequence: np.ndarray) -> Dict[int, float]:
        """Calculate frequency of each state"""
        state_frequencies = {}
        total_observations = len(state_sequence)

        for state in range(self.config.n_states):
            frequency = np.sum(state_sequence == state) / total_observations
            state_frequencies[state] = frequency

        return state_frequencies

    def _calculate_regime_stability(
        self, state_sequence: np.ndarray, dwell_times: Dict[int, float]
    ) -> float:
        """Calculate overall regime stability score"""
        # Stability is higher when:
        # 1. States have longer dwell times
        # 2. Fewer state transitions
        # 3. More concentrated state distribution

        # Calculate transition count
        transitions = np.sum(np.diff(state_sequence) != 0)
        transition_rate = transitions / len(state_sequence)

        # Calculate average dwell time
        avg_dwell_time = np.mean(list(dwell_times.values()))

        # Calculate state concentration (entropy)
        state_counts = np.bincount(state_sequence, minlength=self.config.n_states)
        state_probs = state_counts / np.sum(state_counts)
        entropy = -np.sum(state_probs * np.log2(state_probs + 1e-8))
        max_entropy = np.log2(self.config.n_states)
        concentration = 1.0 - (entropy / max_entropy)

        # Combine metrics
        stability = (
            concentration * 0.4
            + (1.0 - transition_rate) * 0.3
            + min(avg_dwell_time / 50.0, 1.0) * 0.3
        )

        return float(stability)

    def _identify_coordination_regimes(
        self, features: np.ndarray, state_sequence: np.ndarray, price_columns: List[str]
    ) -> Tuple[int, int]:
        """Identify coordination-related regimes"""
        # Find regime with widest spreads (coordination indicator)
        spread_features = features[:, : len(price_columns) * (len(price_columns) - 1) // 2]
        regime_spread_means = []

        for state in range(self.config.n_states):
            state_mask = state_sequence == state
            if np.sum(state_mask) > 0:
                regime_spread_means.append(np.mean(spread_features[state_mask]))
            else:
                regime_spread_means.append(0.0)

        wide_spread_regime = np.argmax(regime_spread_means)

        # Find regime with highest correlation (lockstep indicator)
        # This is a simplified version - in practice, you'd calculate cross-exchange correlations
        volatility_features = features[:, -2:]  # Last two features are volatility measures
        regime_volatility_means = []

        for state in range(self.config.n_states):
            state_mask = state_sequence == state
            if np.sum(state_mask) > 0:
                regime_volatility_means.append(np.mean(volatility_features[state_mask]))
            else:
                regime_volatility_means.append(0.0)

        # Lower volatility might indicate lockstep behavior
        lockstep_regime = np.argmin(regime_volatility_means)

        return wide_spread_regime, lockstep_regime

    def _calculate_coordination_regime_score(
        self, state_sequence: np.ndarray, wide_spread_regime: int, lockstep_regime: int
    ) -> float:
        """Calculate score for coordination regimes"""
        # Score based on time spent in coordination-related regimes
        total_observations = len(state_sequence)

        wide_spread_time = np.sum(state_sequence == wide_spread_regime) / total_observations
        lockstep_time = np.sum(state_sequence == lockstep_regime) / total_observations

        # Coordination score is the average time spent in coordination regimes
        coordination_score = (wide_spread_time + lockstep_time) / 2.0

        return float(coordination_score)

    def _analyze_by_environment(
        self,
        data: pd.DataFrame,
        features: np.ndarray,
        state_sequence: np.ndarray,
        environment_column: str,
    ) -> Tuple[Dict, Dict, Dict]:
        """Analyze HMM patterns by environment"""
        env_dwell_times = {}
        env_state_frequencies = {}
        env_stability = {}

        environments = data[environment_column].unique()

        for env in environments:
            env_mask = data[environment_column] == env
            env_indices = np.where(env_mask)[0]

            if len(env_indices) < self.config.min_observations:
                continue

            # Adjust indices to account for state_sequence being shorter than original data
            env_indices_adjusted = env_indices[env_indices < len(state_sequence)]
            if len(env_indices_adjusted) < self.config.min_observations:
                continue

            # Extract environment-specific state sequence
            env_state_seq = state_sequence[env_indices_adjusted]

            # Calculate environment-specific metrics
            env_dwell_times[env] = self._calculate_dwell_times(env_state_seq)
            env_state_frequencies[env] = self._calculate_state_frequencies(env_state_seq)
            env_stability[env] = self._calculate_regime_stability(
                env_state_seq, env_dwell_times[env]
            )

        return env_dwell_times, env_state_frequencies, env_stability


def analyze_hmm(
    data: pd.DataFrame,
    price_columns: List[str],
    environment_column: str = None,
    config: HMMConfig = None,
    seed: int = None,
) -> HMMResult:
    """
    Convenience function for HMM analysis

    Args:
        data: DataFrame with price data and environment info
        price_columns: List of exchange price column names
        environment_column: Column name for environment partitioning
        config: HMMConfig instance
        seed: Random seed for reproducibility

    Returns:
        HMMResult with comprehensive HMM analysis
    """
    validator = HMMValidator(config)
    return validator.analyze_hmm(data, price_columns, environment_column, seed)
