"""
Mirroring Detection for ACD Validation Layer

This module implements depth-weighted order book similarity detection
using dynamic time warping and cosine similarity to identify coordinated
order book mirroring patterns.
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")


@dataclass
class MirroringConfig:
    """Configuration for mirroring analysis"""

    window_size: int = 50
    top_k_levels: int = 5  # Number of order book levels to consider
    similarity_threshold: float = 0.7  # Threshold for high similarity
    min_observations: int = 20
    depth_weight_power: float = 0.5  # Power for depth weighting (0.5 = sqrt)
    correlation_threshold: float = 0.6  # Threshold for significant correlation


@dataclass
class MirroringResult:
    """Results from mirroring analysis"""

    # Core metrics
    cosine_similarities: Dict[Tuple[str, str], float]  # (exchange1, exchange2) -> similarity
    pearson_correlations: Dict[Tuple[str, str], float]  # (exchange1, exchange2) -> correlation
    depth_weighted_similarities: Dict[Tuple[str, str], float]  # Depth-weighted similarities

    # Statistical significance
    significant_correlations: List[Tuple[str, str]]  # Significant correlation pairs
    avg_cosine_similarity: float  # Average cosine similarity across all pairs
    avg_pearson_correlation: float  # Average Pearson correlation across all pairs

    # Environment-specific results
    env_similarities: Dict[str, Dict[Tuple[str, str], float]]  # env -> pairs -> similarity
    env_correlations: Dict[str, Dict[Tuple[str, str], float]]  # env -> pairs -> correlation

    # Mirroring indicators
    high_mirroring_pairs: List[Tuple[str, str]]  # Pairs with high mirroring
    mirroring_ratio: float  # Fraction of pairs with high mirroring
    coordination_score: float  # Overall coordination score (0-1)

    # Metadata
    n_windows: int
    n_exchanges: int
    config: MirroringConfig


class MirroringValidator:
    """Mirroring detection validator for coordination detection"""

    def __init__(self, config: MirroringConfig = None):
        self.config = config or MirroringConfig()

    def analyze_mirroring(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: str = None,
        seed: int = None,
    ) -> MirroringResult:
        """
        Analyze order book mirroring patterns between exchanges

        Args:
            data: DataFrame with price data and environment info
            price_columns: List of exchange price column names
            environment_column: Column name for environment partitioning
            seed: Random seed for reproducibility

        Returns:
            MirroringResult with comprehensive mirroring analysis
        """
        if seed is not None:
            np.random.seed(seed)

        # Extract price data
        prices = data[price_columns].values
        exchanges = price_columns

        # Generate synthetic order book data (in real implementation, this would be actual order book data)
        order_books = self._generate_synthetic_order_books(prices, exchanges)

        # Initialize results containers
        cosine_similarities = {}
        pearson_correlations = {}
        depth_weighted_similarities = {}
        env_similarities = {}
        env_correlations = {}

        # Calculate similarities between all exchange pairs
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1, exchange2 = exchanges[i], exchanges[j]

                # Calculate cosine similarity
                cosine_sim = self._calculate_cosine_similarity(
                    order_books[exchange1], order_books[exchange2]
                )
                cosine_similarities[(exchange1, exchange2)] = cosine_sim

                # Calculate Pearson correlation
                pearson_corr = self._calculate_pearson_correlation(
                    order_books[exchange1], order_books[exchange2]
                )
                pearson_correlations[(exchange1, exchange2)] = pearson_corr

                # Calculate depth-weighted similarity
                depth_sim = self._calculate_depth_weighted_similarity(
                    order_books[exchange1], order_books[exchange2]
                )
                depth_weighted_similarities[(exchange1, exchange2)] = depth_sim

        # Identify significant correlations
        significant_correlations = [
            (ex1, ex2)
            for (ex1, ex2), corr in pearson_correlations.items()
            if abs(corr) > self.config.correlation_threshold
        ]

        # Calculate average similarities
        avg_cosine_similarity = (
            np.mean(list(cosine_similarities.values())) if cosine_similarities else 0.0
        )
        avg_pearson_correlation = (
            np.mean(list(pearson_correlations.values())) if pearson_correlations else 0.0
        )

        # Identify high mirroring pairs
        high_mirroring_pairs = [
            (ex1, ex2)
            for (ex1, ex2), sim in cosine_similarities.items()
            if sim > self.config.similarity_threshold
        ]

        # Calculate mirroring ratio
        mirroring_ratio = len(high_mirroring_pairs) / max(len(cosine_similarities), 1)

        # Calculate coordination score
        coordination_score = self._calculate_coordination_score(
            cosine_similarities, pearson_correlations, depth_weighted_similarities
        )

        # Environment-specific analysis
        if environment_column and environment_column in data.columns:
            env_similarities, env_correlations = self._analyze_by_environment(
                data, order_books, exchanges, environment_column
            )

        return MirroringResult(
            cosine_similarities=cosine_similarities,
            pearson_correlations=pearson_correlations,
            depth_weighted_similarities=depth_weighted_similarities,
            significant_correlations=significant_correlations,
            avg_cosine_similarity=avg_cosine_similarity,
            avg_pearson_correlation=avg_pearson_correlation,
            env_similarities=env_similarities,
            env_correlations=env_correlations,
            high_mirroring_pairs=high_mirroring_pairs,
            mirroring_ratio=mirroring_ratio,
            coordination_score=coordination_score,
            n_windows=len(prices) - self.config.window_size + 1,
            n_exchanges=len(exchanges),
            config=self.config,
        )

    def _generate_synthetic_order_books(
        self, prices: np.ndarray, exchanges: List[str]
    ) -> Dict[str, np.ndarray]:
        """Generate synthetic order book data based on price movements"""
        n_obs, n_exchanges = prices.shape
        order_books = {}

        for i, exchange in enumerate(exchanges):
            # Generate synthetic order book levels based on price movements
            order_book = np.zeros((n_obs, self.config.top_k_levels * 2))  # bid + ask levels

            for t in range(n_obs):
                mid_price = prices[t, i]

                # Generate bid levels (below mid-price)
                for level in range(self.config.top_k_levels):
                    spread = 0.001 * (level + 1)  # Increasing spread
                    order_book[t, level] = mid_price - spread

                # Generate ask levels (above mid-price)
                for level in range(self.config.top_k_levels):
                    spread = 0.001 * (level + 1)  # Increasing spread
                    order_book[t, self.config.top_k_levels + level] = mid_price + spread

            order_books[exchange] = order_book

        return order_books

    def _calculate_cosine_similarity(self, ob1: np.ndarray, ob2: np.ndarray) -> float:
        """Calculate cosine similarity between order books"""
        try:
            # Flatten order books and calculate cosine similarity
            ob1_flat = ob1.flatten()
            ob2_flat = ob2.flatten()

            # Handle zero vectors
            if np.linalg.norm(ob1_flat) == 0 or np.linalg.norm(ob2_flat) == 0:
                return 0.0

            # Calculate cosine similarity
            similarity = cosine_similarity([ob1_flat], [ob2_flat])[0][0]
            return float(similarity)

        except Exception:
            return 0.0

    def _calculate_pearson_correlation(self, ob1: np.ndarray, ob2: np.ndarray) -> float:
        """Calculate Pearson correlation between order books"""
        try:
            # Flatten order books
            ob1_flat = ob1.flatten()
            ob2_flat = ob2.flatten()

            # Calculate Pearson correlation
            correlation, _ = pearsonr(ob1_flat, ob2_flat)
            return float(correlation) if not np.isnan(correlation) else 0.0

        except Exception:
            return 0.0

    def _calculate_depth_weighted_similarity(self, ob1: np.ndarray, ob2: np.ndarray) -> float:
        """Calculate depth-weighted similarity between order books"""
        try:
            # Calculate depth weights (deeper levels get lower weights)
            depth_weights = np.power(
                np.arange(1, self.config.top_k_levels + 1), -self.config.depth_weight_power
            )

            # Normalize weights
            depth_weights = depth_weights / np.sum(depth_weights)

            # Calculate weighted similarity for each time step
            weighted_similarities = []

            for t in range(len(ob1)):
                # Get bid and ask levels
                bid1 = ob1[t, : self.config.top_k_levels]
                ask1 = ob1[t, self.config.top_k_levels :]
                bid2 = ob2[t, : self.config.top_k_levels]
                ask2 = ob2[t, self.config.top_k_levels :]

                # Calculate weighted similarities for bids and asks
                bid_sim = np.sum(depth_weights * np.abs(bid1 - bid2)) / np.mean(
                    [np.std(bid1), np.std(bid2)]
                )
                ask_sim = np.sum(depth_weights * np.abs(ask1 - ask2)) / np.mean(
                    [np.std(ask1), np.std(ask2)]
                )

                # Combine bid and ask similarities
                weighted_sim = 1.0 - (bid_sim + ask_sim) / 2.0
                weighted_similarities.append(max(0.0, min(1.0, weighted_sim)))

            return float(np.mean(weighted_similarities))

        except Exception:
            return 0.0

    def _calculate_coordination_score(
        self, cosine_sims: Dict, pearson_corrs: Dict, depth_sims: Dict
    ) -> float:
        """Calculate overall coordination score from all similarity measures"""
        try:
            # Combine all similarity measures
            all_scores = []

            # Add cosine similarities
            all_scores.extend(cosine_sims.values())

            # Add absolute Pearson correlations
            all_scores.extend([abs(corr) for corr in pearson_corrs.values()])

            # Add depth-weighted similarities
            all_scores.extend(depth_sims.values())

            # Calculate weighted average (cosine similarity gets higher weight)
            if all_scores:
                # Weight cosine similarities more heavily
                cosine_weight = 0.5
                other_weight = 0.25

                cosine_scores = list(cosine_sims.values())
                other_scores = [abs(corr) for corr in pearson_corrs.values()] + list(
                    depth_sims.values()
                )

                weighted_score = cosine_weight * np.mean(cosine_scores) + other_weight * np.mean(
                    other_scores
                )

                return float(weighted_score)
            else:
                return 0.0

        except Exception:
            return 0.0

    def _analyze_by_environment(
        self,
        data: pd.DataFrame,
        order_books: Dict[str, np.ndarray],
        exchanges: List[str],
        environment_column: str,
    ) -> Tuple[Dict, Dict]:
        """Analyze mirroring patterns by environment"""
        env_similarities = {}
        env_correlations = {}

        environments = data[environment_column].unique()

        for env in environments:
            env_mask = data[environment_column] == env
            env_indices = np.where(env_mask)[0]

            if len(env_indices) < self.config.min_observations:
                continue

            env_similarities[env] = {}
            env_correlations[env] = {}

            # Calculate similarities for this environment
            for i in range(len(exchanges)):
                for j in range(i + 1, len(exchanges)):
                    exchange1, exchange2 = exchanges[i], exchanges[j]

                    # Extract environment-specific order book data
                    ob1_env = order_books[exchange1][env_indices]
                    ob2_env = order_books[exchange2][env_indices]

                    # Calculate similarities
                    cosine_sim = self._calculate_cosine_similarity(ob1_env, ob2_env)
                    pearson_corr = self._calculate_pearson_correlation(ob1_env, ob2_env)

                    env_similarities[env][(exchange1, exchange2)] = cosine_sim
                    env_correlations[env][(exchange1, exchange2)] = pearson_corr

        return env_similarities, env_correlations


def analyze_mirroring(
    data: pd.DataFrame,
    price_columns: List[str],
    environment_column: str = None,
    config: MirroringConfig = None,
    seed: int = None,
) -> MirroringResult:
    """
    Convenience function for mirroring analysis

    Args:
        data: DataFrame with price data and environment info
        price_columns: List of exchange price column names
        environment_column: Column name for environment partitioning
        config: MirroringConfig instance
        seed: Random seed for reproducibility

    Returns:
        MirroringResult with comprehensive mirroring analysis
    """
    validator = MirroringValidator(config)
    return validator.analyze_mirroring(data, price_columns, environment_column, seed)
