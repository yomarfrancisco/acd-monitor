"""
Information Flow Analysis for ACD Validation Layer

This module implements transfer entropy and network analysis to detect
information flow patterns between exchanges, identifying coordinated
information sharing and network effects.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")


@dataclass
class InfoFlowConfig:
    """Configuration for information flow analysis"""

    window_size: int = 100  # Rolling window size
    n_bins: int = 5  # Number of bins for discretization
    max_lag: int = 5  # Maximum lag for transfer entropy
    significance_level: float = 0.05  # Significance level for tests
    min_observations: int = 50  # Minimum observations per window
    permutation_tests: int = 100  # Number of permutation tests


@dataclass
class InfoFlowResult:
    """Results from information flow analysis"""

    # Core metrics
    transfer_entropies: Dict[Tuple[str, str], float]  # (source, target) -> TE
    directed_correlations: Dict[Tuple[str, str], float]  # (source, target) -> correlation
    network_centrality: Dict[str, float]  # exchange -> centrality score

    # Network analysis
    out_degree_concentration: float  # Concentration of out-degrees
    eigenvector_centrality: Dict[str, float]  # exchange -> eigenvector centrality
    network_density: float  # Overall network density
    clustering_coefficient: float  # Network clustering coefficient

    # Statistical significance
    significant_te_links: List[Tuple[str, str]]  # Significant transfer entropy links
    te_p_values: Dict[Tuple[str, str], float]  # (source, target) -> p-value
    avg_transfer_entropy: float  # Average transfer entropy across all pairs

    # Environment-specific results
    env_transfer_entropies: Dict[str, Dict[Tuple[str, str], float]]  # env -> pairs -> TE
    env_centrality: Dict[str, Dict[str, float]]  # env -> exchange -> centrality
    env_network_density: Dict[str, float]  # env -> network density

    # Coordination indicators
    information_hub_score: float  # Score for information hub formation
    coordination_network_score: float  # Overall coordination network score

    # Metadata
    n_observations: int
    n_exchanges: int
    config: InfoFlowConfig


class InfoFlowValidator:
    """Information flow analysis validator for coordination detection"""

    def __init__(self, config: InfoFlowConfig = None):
        self.config = config or InfoFlowConfig()

    def analyze_infoflow(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: str = None,
        seed: int = None,
    ) -> InfoFlowResult:
        """
        Analyze information flow patterns between exchanges

        Args:
            data: DataFrame with price data and environment info
            price_columns: List of exchange price column names
            environment_column: Column name for environment partitioning
            seed: Random seed for reproducibility

        Returns:
            InfoFlowResult with comprehensive information flow analysis
        """
        if seed is not None:
            np.random.seed(seed)

        # Extract price data
        prices = data[price_columns].values
        exchanges = price_columns

        # Calculate returns
        returns = np.diff(prices, axis=0)

        # Initialize results containers
        transfer_entropies = {}
        directed_correlations = {}
        te_p_values = {}
        env_transfer_entropies = {}
        env_centrality = {}
        env_network_density = {}

        # Calculate transfer entropy between all exchange pairs
        for i in range(len(exchanges)):
            for j in range(len(exchanges)):
                if i == j:
                    continue

                source, target = exchanges[i], exchanges[j]

                # Calculate transfer entropy
                te_value = self._calculate_transfer_entropy(returns[:, i], returns[:, j])
                transfer_entropies[(source, target)] = te_value

                # Calculate directed correlation
                corr_value = self._calculate_directed_correlation(returns[:, i], returns[:, j])
                directed_correlations[(source, target)] = corr_value

                # Calculate p-value using permutation test
                p_value = self._permutation_test_te(returns[:, i], returns[:, j], te_value)
                te_p_values[(source, target)] = p_value

        # Calculate network metrics
        network_centrality = self._calculate_network_centrality(transfer_entropies, exchanges)
        out_degree_concentration = self._calculate_out_degree_concentration(
            transfer_entropies, exchanges
        )
        eigenvector_centrality = self._calculate_eigenvector_centrality(
            transfer_entropies, exchanges
        )
        network_density = self._calculate_network_density(transfer_entropies, exchanges)
        clustering_coefficient = self._calculate_clustering_coefficient(
            transfer_entropies, exchanges
        )

        # Identify significant transfer entropy links
        significant_te_links = [
            (source, target)
            for (source, target), p_val in te_p_values.items()
            if p_val < self.config.significance_level
        ]

        # Calculate average transfer entropy
        avg_transfer_entropy = (
            np.mean(list(transfer_entropies.values())) if transfer_entropies else 0.0
        )

        # Calculate coordination scores
        information_hub_score = self._calculate_information_hub_score(network_centrality, exchanges)
        coordination_network_score = self._calculate_coordination_network_score(
            transfer_entropies, network_centrality, out_degree_concentration
        )

        # Environment-specific analysis
        if environment_column and environment_column in data.columns:
            env_transfer_entropies, env_centrality, env_network_density = (
                self._analyze_by_environment(data, returns, exchanges, environment_column)
            )

        return InfoFlowResult(
            transfer_entropies=transfer_entropies,
            directed_correlations=directed_correlations,
            network_centrality=network_centrality,
            out_degree_concentration=out_degree_concentration,
            eigenvector_centrality=eigenvector_centrality,
            network_density=network_density,
            clustering_coefficient=clustering_coefficient,
            significant_te_links=significant_te_links,
            te_p_values=te_p_values,
            avg_transfer_entropy=avg_transfer_entropy,
            env_transfer_entropies=env_transfer_entropies,
            env_centrality=env_centrality,
            env_network_density=env_network_density,
            information_hub_score=information_hub_score,
            coordination_network_score=coordination_network_score,
            n_observations=len(returns),
            n_exchanges=len(exchanges),
            config=self.config,
        )

    def _calculate_transfer_entropy(self, source: np.ndarray, target: np.ndarray) -> float:
        """Calculate transfer entropy from source to target"""
        try:
            # Discretize the data
            source_disc = self._discretize_data(source)
            target_disc = self._discretize_data(target)

            # Calculate transfer entropy
            te = 0.0

            for lag in range(1, min(self.config.max_lag + 1, len(source_disc))):
                # Calculate conditional entropy
                h_target_given_past = self._conditional_entropy(
                    target_disc[lag:], target_disc[:-lag]
                )
                h_target_given_past_and_source = self._conditional_entropy(
                    target_disc[lag:], np.column_stack([target_disc[:-lag], source_disc[:-lag]])
                )

                # Transfer entropy contribution
                te += h_target_given_past - h_target_given_past_and_source

            return float(te)

        except Exception:
            return 0.0

    def _discretize_data(self, data: np.ndarray) -> np.ndarray:
        """Discretize continuous data into bins"""
        try:
            # Use quantile-based binning
            quantiles = np.linspace(0, 1, self.config.n_bins + 1)
            bin_edges = np.quantile(data, quantiles)
            bin_edges[0] = -np.inf
            bin_edges[-1] = np.inf

            # Assign bins
            discretized = np.digitize(data, bin_edges) - 1
            return discretized

        except Exception:
            return np.zeros_like(data, dtype=int)

    def _conditional_entropy(self, x: np.ndarray, y: np.ndarray) -> float:
        """Calculate conditional entropy H(X|Y)"""
        try:
            # Handle 2D y array
            if y.ndim == 1:
                y = y.reshape(-1, 1)

            # Calculate joint and marginal probabilities
            joint_probs = {}
            marginal_probs = {}

            for i in range(len(x)):
                x_val = x[i]
                y_val = tuple(y[i])

                # Joint probability
                if (x_val, y_val) in joint_probs:
                    joint_probs[(x_val, y_val)] += 1
                else:
                    joint_probs[(x_val, y_val)] = 1

                # Marginal probability
                if y_val in marginal_probs:
                    marginal_probs[y_val] += 1
                else:
                    marginal_probs[y_val] = 1

            # Normalize probabilities
            total = len(x)
            joint_probs = {k: v / total for k, v in joint_probs.items()}
            marginal_probs = {k: v / total for k, v in marginal_probs.items()}

            # Calculate conditional entropy
            ce = 0.0
            for (x_val, y_val), joint_prob in joint_probs.items():
                if joint_prob > 0 and marginal_probs[y_val] > 0:
                    ce -= joint_prob * np.log2(joint_prob / marginal_probs[y_val])

            return float(ce)

        except Exception:
            return 0.0

    def _calculate_directed_correlation(self, source: np.ndarray, target: np.ndarray) -> float:
        """Calculate directed correlation (source -> target)"""
        try:
            # Calculate correlation with lag
            max_lag = min(self.config.max_lag, len(source) // 4)
            correlations = []

            for lag in range(1, max_lag + 1):
                if len(source) > lag:
                    corr, _ = stats.pearsonr(source[:-lag], target[lag:])
                    if not np.isnan(corr):
                        correlations.append(abs(corr))

            return float(np.max(correlations)) if correlations else 0.0

        except Exception:
            return 0.0

    def _permutation_test_te(
        self, source: np.ndarray, target: np.ndarray, observed_te: float
    ) -> float:
        """Perform permutation test for transfer entropy significance"""
        try:
            # Generate permutation samples
            permuted_tes = []

            for _ in range(self.config.permutation_tests):
                # Permute source data
                permuted_source = np.random.permutation(source)

                # Calculate transfer entropy for permuted data
                permuted_te = self._calculate_transfer_entropy(permuted_source, target)
                permuted_tes.append(permuted_te)

            # Calculate p-value
            p_value = np.sum(np.array(permuted_tes) >= observed_te) / len(permuted_tes)
            return float(p_value)

        except Exception:
            return 1.0

    def _calculate_network_centrality(
        self, transfer_entropies: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> Dict[str, float]:
        """Calculate network centrality for each exchange"""
        centrality = {}

        for exchange in exchanges:
            # Calculate out-degree (information flow out)
            out_degree = sum(
                te for (source, target), te in transfer_entropies.items() if source == exchange
            )

            # Calculate in-degree (information flow in)
            in_degree = sum(
                te for (source, target), te in transfer_entropies.items() if target == exchange
            )

            # Centrality is the sum of in and out degrees
            centrality[exchange] = out_degree + in_degree

        return centrality

    def _calculate_out_degree_concentration(
        self, transfer_entropies: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> float:
        """Calculate concentration of out-degrees (Gini coefficient)"""
        out_degrees = []

        for exchange in exchanges:
            out_degree = sum(
                te for (source, target), te in transfer_entropies.items() if source == exchange
            )
            out_degrees.append(out_degree)

        if not out_degrees or np.sum(out_degrees) == 0:
            return 0.0

        # Calculate Gini coefficient
        out_degrees = np.array(out_degrees)
        sorted_degrees = np.sort(out_degrees)
        n = len(sorted_degrees)

        cumsum = np.cumsum(sorted_degrees)
        gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0.0

        return float(gini)

    def _calculate_eigenvector_centrality(
        self, transfer_entropies: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> Dict[str, float]:
        """Calculate eigenvector centrality for each exchange"""
        # Create adjacency matrix
        n = len(exchanges)
        adj_matrix = np.zeros((n, n))

        for i, source in enumerate(exchanges):
            for j, target in enumerate(exchanges):
                if (source, target) in transfer_entropies:
                    adj_matrix[i, j] = transfer_entropies[(source, target)]

        # Calculate eigenvector centrality
        try:
            eigenvalues, eigenvectors = np.linalg.eig(adj_matrix)
            max_eigenvalue_idx = np.argmax(eigenvalues)
            eigenvector_centrality = eigenvectors[:, max_eigenvalue_idx]

            # Normalize and convert to dictionary
            eigenvector_centrality = np.abs(eigenvector_centrality)
            eigenvector_centrality = eigenvector_centrality / np.sum(eigenvector_centrality)

            centrality_dict = {}
            for i, exchange in enumerate(exchanges):
                centrality_dict[exchange] = float(eigenvector_centrality[i])

            return centrality_dict

        except Exception:
            return {exchange: 0.0 for exchange in exchanges}

    def _calculate_network_density(
        self, transfer_entropies: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> float:
        """Calculate network density"""
        n = len(exchanges)
        max_possible_edges = n * (n - 1)  # Directed graph
        actual_edges = len(transfer_entropies)

        return float(actual_edges / max_possible_edges) if max_possible_edges > 0 else 0.0

    def _calculate_clustering_coefficient(
        self, transfer_entropies: Dict[Tuple[str, str], float], exchanges: List[str]
    ) -> float:
        """Calculate network clustering coefficient"""
        # This is a simplified version - in practice, you'd implement proper clustering coefficient
        # For now, we'll use the density as a proxy
        return self._calculate_network_density(transfer_entropies, exchanges)

    def _calculate_information_hub_score(
        self, network_centrality: Dict[str, float], exchanges: List[str]
    ) -> float:
        """Calculate score for information hub formation"""
        if not network_centrality:
            return 0.0

        centrality_values = list(network_centrality.values())

        # Hub score is the concentration of centrality (Gini coefficient)
        sorted_centrality = np.sort(centrality_values)
        n = len(sorted_centrality)

        if n == 0 or np.sum(sorted_centrality) == 0:
            return 0.0

        cumsum = np.cumsum(sorted_centrality)
        gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0.0

        return float(gini)

    def _calculate_coordination_network_score(
        self,
        transfer_entropies: Dict[Tuple[str, str], float],
        network_centrality: Dict[str, float],
        out_degree_concentration: float,
    ) -> float:
        """Calculate overall coordination network score"""
        # Combine multiple network metrics
        avg_te = np.mean(list(transfer_entropies.values())) if transfer_entropies else 0.0
        avg_centrality = np.mean(list(network_centrality.values())) if network_centrality else 0.0

        # Coordination score combines transfer entropy, centrality, and concentration
        coordination_score = avg_te * 0.4 + avg_centrality * 0.3 + out_degree_concentration * 0.3

        return float(coordination_score)

    def _analyze_by_environment(
        self, data: pd.DataFrame, returns: np.ndarray, exchanges: List[str], environment_column: str
    ) -> Tuple[Dict, Dict, Dict]:
        """Analyze information flow patterns by environment"""
        env_transfer_entropies = {}
        env_centrality = {}
        env_network_density = {}

        environments = data[environment_column].unique()

        for env in environments:
            env_mask = data[environment_column] == env
            env_indices = np.where(env_mask)[0]

            if len(env_indices) < self.config.min_observations:
                continue

            # Extract environment-specific returns
            # Adjust indices to account for returns being shorter than original data
            env_indices_adjusted = env_indices[env_indices < len(returns)]
            if len(env_indices_adjusted) < self.config.min_observations:
                continue
            env_returns = returns[env_indices_adjusted]

            # Calculate transfer entropies for this environment
            env_tes = {}
            for i in range(len(exchanges)):
                for j in range(len(exchanges)):
                    if i == j:
                        continue

                    source, target = exchanges[i], exchanges[j]
                    te_value = self._calculate_transfer_entropy(
                        env_returns[:, i], env_returns[:, j]
                    )
                    env_tes[(source, target)] = te_value

            env_transfer_entropies[env] = env_tes

            # Calculate environment-specific network metrics
            env_centrality[env] = self._calculate_network_centrality(env_tes, exchanges)
            env_network_density[env] = self._calculate_network_density(env_tes, exchanges)

        return env_transfer_entropies, env_centrality, env_network_density


def analyze_infoflow(
    data: pd.DataFrame,
    price_columns: List[str],
    environment_column: str = None,
    config: InfoFlowConfig = None,
    seed: int = None,
) -> InfoFlowResult:
    """
    Convenience function for information flow analysis

    Args:
        data: DataFrame with price data and environment info
        price_columns: List of exchange price column names
        environment_column: Column name for environment partitioning
        config: InfoFlowConfig instance
        seed: Random seed for reproducibility

    Returns:
        InfoFlowResult with comprehensive information flow analysis
    """
    validator = InfoFlowValidator(config)
    return validator.analyze_infoflow(data, price_columns, environment_column, seed)
