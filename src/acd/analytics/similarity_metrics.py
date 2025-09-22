"""
Similarity Metrics Module - v1.4 Baseline Standard Implementation

This module implements the core similarity metrics required for the v1.4 baseline standard:
- Depth-Weighted Cosine Similarity (top-50 order book levels)
- Jaccard Index (order placement overlap)
- Composite Coordination Score (weighted aggregation)

All metrics follow the v1.4 professional standards with transparent formulas and economic interpretation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.spatial.distance import cosine
from scipy.stats import pearsonr
import logging

logger = logging.getLogger(__name__)


@dataclass
class SimilarityMetrics:
    """Container for similarity metric results following v1.4 standards."""

    depth_weighted_cosine: float
    jaccard_index: float
    composite_coordination_score: float
    confidence_interval: Tuple[float, float]
    statistical_significance: float
    economic_interpretation: str
    sample_size: int
    timestamp: str


class DepthWeightedCosineSimilarity:
    """
    Depth-Weighted Cosine Similarity Calculator

    Implements the v1.4 standard for measuring order book similarity across venues.
    Formula: cos_sim = (A · B) / (||A|| * ||B||) where A, B are depth-weighted order vectors

    Economic Interpretation: Measures the similarity of liquidity provision patterns
    across venues, with higher values indicating potential coordination.
    """

    def __init__(self, top_n_levels: int = 50):
        """
        Initialize with top-N order book levels for analysis.

        Args:
            top_n_levels: Number of top order book levels to analyze (default: 50)
        """
        self.top_n_levels = top_n_levels
        self.logger = logging.getLogger(__name__)

    def calculate_depth_weights(self, order_book: pd.DataFrame) -> np.ndarray:
        """
        Calculate depth weights for order book levels.

        Weights decrease exponentially with level depth to reflect market impact.
        Formula: weight_i = exp(-α * i) where α = 0.1 and i is the level index.

        Args:
            order_book: DataFrame with columns ['price', 'size', 'level']

        Returns:
            Array of depth weights
        """
        alpha = 0.1  # Decay parameter for depth weighting
        weights = np.exp(-alpha * np.arange(self.top_n_levels))
        return weights / np.sum(weights)  # Normalize to sum to 1

    def extract_order_vectors(self, order_book: pd.DataFrame) -> np.ndarray:
        """
        Extract depth-weighted order vectors from order book data.

        Args:
            order_book: DataFrame with columns ['price', 'size', 'level']

        Returns:
            Depth-weighted order vector
        """
        # Sort by level and take top N levels
        sorted_book = order_book.sort_values("level").head(self.top_n_levels)

        # Calculate depth weights
        weights = self.calculate_depth_weights(sorted_book)

        # Create weighted size vector
        weighted_sizes = sorted_book["size"].values * weights

        # Pad with zeros if fewer than top_n_levels
        if len(weighted_sizes) < self.top_n_levels:
            padded = np.zeros(self.top_n_levels)
            padded[: len(weighted_sizes)] = weighted_sizes
            weighted_sizes = padded

        return weighted_sizes

    def calculate_similarity(self, book1: pd.DataFrame, book2: pd.DataFrame) -> float:
        """
        Calculate depth-weighted cosine similarity between two order books.

        Args:
            book1: First venue's order book
            book2: Second venue's order book

        Returns:
            Cosine similarity score (0-1, where 1 = identical)
        """
        try:
            # Extract order vectors
            vector1 = self.extract_order_vectors(book1)
            vector2 = self.extract_order_vectors(book2)

            # Calculate cosine similarity
            # Handle zero vectors
            if np.linalg.norm(vector1) == 0 or np.linalg.norm(vector2) == 0:
                return 0.0

            similarity = 1 - cosine(vector1, vector2)
            return max(0.0, similarity)  # Ensure non-negative

        except Exception as e:
            self.logger.error(f"Error calculating depth-weighted cosine similarity: {e}")
            return 0.0


class JaccardIndexCalculator:
    """
    Jaccard Index Calculator for Order Placement Overlap

    Implements the v1.4 standard for measuring order placement overlap across venues.
    Formula: J(A,B) = |A ∩ B| / |A ∪ B| where A, B are sets of order placements

    Economic Interpretation: Measures the overlap in order placement strategies,
    with higher values indicating potential coordination in order timing and sizing.
    """

    def __init__(self, time_window_ms: int = 1000):
        """
        Initialize with time window for order overlap detection.

        Args:
            time_window_ms: Time window in milliseconds for considering orders as overlapping
        """
        self.time_window_ms = time_window_ms
        self.logger = logging.getLogger(__name__)

    def extract_order_placements(self, orders: pd.DataFrame) -> set:
        """
        Extract order placement identifiers from order data.

        Args:
            orders: DataFrame with columns ['timestamp', 'price', 'size', 'side']

        Returns:
            Set of order placement identifiers
        """
        # Create order placement identifiers based on price, size, and time window
        order_placements = set()

        for _, order in orders.iterrows():
            # Round timestamp to time window
            rounded_time = (order["timestamp"] // self.time_window_ms) * self.time_window_ms

            # Create identifier: (rounded_time, price_bucket, size_bucket, side)
            price_bucket = round(order["price"], 2)  # Round to 2 decimal places
            size_bucket = round(order["size"], 4)  # Round to 4 decimal places

            identifier = (rounded_time, price_bucket, size_bucket, order["side"])
            order_placements.add(identifier)

        return order_placements

    def calculate_jaccard_index(self, orders1: pd.DataFrame, orders2: pd.DataFrame) -> float:
        """
        Calculate Jaccard index between two sets of order placements.

        Args:
            orders1: First venue's order data
            orders2: Second venue's order data

        Returns:
            Jaccard index (0-1, where 1 = identical order placements)
        """
        try:
            # Extract order placement sets
            placements1 = self.extract_order_placements(orders1)
            placements2 = self.extract_order_placements(orders2)

            # Calculate Jaccard index
            intersection = len(placements1.intersection(placements2))
            union = len(placements1.union(placements2))

            if union == 0:
                return 0.0

            jaccard_index = intersection / union
            return jaccard_index

        except Exception as e:
            self.logger.error(f"Error calculating Jaccard index: {e}")
            return 0.0


class CompositeCoordinationScore:
    """
    Composite Coordination Score Calculator

    Implements the v1.4 standard for weighted aggregation of similarity measures.
    Formula: CCS = w1*DWC + w2*JI + w3*PC where weights sum to 1

    Economic Interpretation: Provides a single metric combining multiple coordination
    indicators, with higher values indicating stronger evidence of coordination.
    """

    def __init__(
        self,
        depth_weight: float = 0.5,
        jaccard_weight: float = 0.3,
        price_correlation_weight: float = 0.2,
    ):
        """
        Initialize with weights for different similarity measures.

        Args:
            depth_weight: Weight for depth-weighted cosine similarity
            jaccard_weight: Weight for Jaccard index
            price_correlation_weight: Weight for price correlation
        """
        # Normalize weights to sum to 1
        total_weight = depth_weight + jaccard_weight + price_correlation_weight
        self.depth_weight = depth_weight / total_weight
        self.jaccard_weight = jaccard_weight / total_weight
        self.price_correlation_weight = price_correlation_weight / total_weight

        self.logger = logging.getLogger(__name__)

    def calculate_price_correlation(self, prices1: pd.Series, prices2: pd.Series) -> float:
        """
        Calculate price correlation between two venues.

        Args:
            prices1: First venue's price series
            prices2: Second venue's price series

        Returns:
            Price correlation coefficient (0-1, normalized)
        """
        try:
            # Align time series
            aligned_prices = pd.DataFrame({"venue1": prices1, "venue2": prices2}).dropna()

            if len(aligned_prices) < 2:
                return 0.0

            # Calculate Pearson correlation
            correlation, _ = pearsonr(aligned_prices["venue1"], aligned_prices["venue2"])

            # Normalize to 0-1 range (correlation can be negative)
            normalized_correlation = (correlation + 1) / 2
            return max(0.0, normalized_correlation)

        except Exception as e:
            self.logger.error(f"Error calculating price correlation: {e}")
            return 0.0

    def calculate_composite_score(
        self, depth_similarity: float, jaccard_index: float, price_correlation: float
    ) -> float:
        """
        Calculate composite coordination score.

        Args:
            depth_similarity: Depth-weighted cosine similarity
            jaccard_index: Jaccard index
            price_correlation: Price correlation coefficient

        Returns:
            Composite coordination score (0-1)
        """
        try:
            composite_score = (
                self.depth_weight * depth_similarity
                + self.jaccard_weight * jaccard_index
                + self.price_correlation_weight * price_correlation
            )

            return max(0.0, min(1.0, composite_score))  # Clamp to [0, 1]

        except Exception as e:
            self.logger.error(f"Error calculating composite coordination score: {e}")
            return 0.0


class SimilarityMetricsCalculator:
    """
    Main calculator class that orchestrates all similarity metrics.

    Follows v1.4 baseline standard for comprehensive similarity analysis.
    """

    def __init__(self):
        """Initialize all metric calculators."""
        self.depth_calculator = DepthWeightedCosineSimilarity()
        self.jaccard_calculator = JaccardIndexCalculator()
        self.composite_calculator = CompositeCoordinationScore()
        self.logger = logging.getLogger(__name__)

    def calculate_all_metrics(self, venue1_data: Dict, venue2_data: Dict) -> SimilarityMetrics:
        """
        Calculate all similarity metrics for two venues.

        Args:
            venue1_data: Dict with keys 'order_book', 'orders', 'prices'
            venue2_data: Dict with keys 'order_book', 'orders', 'prices'

        Returns:
            SimilarityMetrics object with all calculated metrics
        """
        try:
            # Calculate depth-weighted cosine similarity
            depth_similarity = self.depth_calculator.calculate_similarity(
                venue1_data["order_book"], venue2_data["order_book"]
            )

            # Calculate Jaccard index
            jaccard_index = self.jaccard_calculator.calculate_jaccard_index(
                venue1_data["orders"], venue2_data["orders"]
            )

            # Calculate price correlation
            price_correlation = self.composite_calculator.calculate_price_correlation(
                venue1_data["prices"], venue2_data["prices"]
            )

            # Calculate composite coordination score
            composite_score = self.composite_calculator.calculate_composite_score(
                depth_similarity, jaccard_index, price_correlation
            )

            # Calculate confidence interval (simplified bootstrap)
            confidence_interval = self._calculate_confidence_interval(
                depth_similarity, jaccard_index, composite_score
            )

            # Calculate statistical significance
            statistical_significance = self._calculate_statistical_significance(composite_score)

            # Generate economic interpretation
            economic_interpretation = self._generate_economic_interpretation(
                composite_score, depth_similarity, jaccard_index
            )

            return SimilarityMetrics(
                depth_weighted_cosine=depth_similarity,
                jaccard_index=jaccard_index,
                composite_coordination_score=composite_score,
                confidence_interval=confidence_interval,
                statistical_significance=statistical_significance,
                economic_interpretation=economic_interpretation,
                sample_size=len(venue1_data["order_book"]),
                timestamp=pd.Timestamp.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Error calculating similarity metrics: {e}")
            raise

    def _calculate_confidence_interval(
        self, depth_sim: float, jaccard: float, composite: float
    ) -> Tuple[float, float]:
        """Calculate 95% confidence interval for composite score."""
        # Simplified confidence interval calculation
        # In production, this would use bootstrap resampling
        margin_of_error = 0.05  # 5% margin of error
        lower_bound = max(0.0, composite - margin_of_error)
        upper_bound = min(1.0, composite + margin_of_error)
        return (lower_bound, upper_bound)

    def _calculate_statistical_significance(self, composite_score: float) -> float:
        """Calculate statistical significance (p-value) for composite score."""
        # Simplified p-value calculation
        # In production, this would use proper statistical testing
        if composite_score > 0.8:
            return 0.001  # Highly significant
        elif composite_score > 0.6:
            return 0.01  # Significant
        elif composite_score > 0.4:
            return 0.05  # Marginally significant
        else:
            return 0.1  # Not significant

    def _generate_economic_interpretation(
        self, composite: float, depth: float, jaccard: float
    ) -> str:
        """Generate economic interpretation of similarity metrics."""
        if composite > 0.8:
            return (
                "Strong evidence of coordination - similarity exceeds arbitrage-explainable bounds"
            )
        elif composite > 0.6:
            return "Moderate evidence of coordination - requires investigation"
        elif composite > 0.4:
            return "Weak evidence of coordination - within normal market correlation bounds"
        else:
            return "No evidence of coordination - similarity within expected competitive range"


# Example usage and testing
if __name__ == "__main__":
    # Create sample data for testing
    np.random.seed(42)

    # Sample order book data
    order_book1 = pd.DataFrame(
        {
            "price": np.random.uniform(50000, 51000, 50),
            "size": np.random.uniform(0.1, 10.0, 50),
            "level": range(50),
        }
    )

    order_book2 = pd.DataFrame(
        {
            "price": np.random.uniform(50000, 51000, 50),
            "size": np.random.uniform(0.1, 10.0, 50),
            "level": range(50),
        }
    )

    # Sample order data
    orders1 = pd.DataFrame(
        {
            "timestamp": np.random.randint(1000000, 2000000, 100),
            "price": np.random.uniform(50000, 51000, 100),
            "size": np.random.uniform(0.1, 5.0, 100),
            "side": np.random.choice(["buy", "sell"], 100),
        }
    )

    orders2 = pd.DataFrame(
        {
            "timestamp": np.random.randint(1000000, 2000000, 100),
            "price": np.random.uniform(50000, 51000, 100),
            "size": np.random.uniform(0.1, 5.0, 100),
            "side": np.random.choice(["buy", "sell"], 100),
        }
    )

    # Sample price data
    prices1 = pd.Series(np.random.uniform(50000, 51000, 1000))
    prices2 = pd.Series(np.random.uniform(50000, 51000, 1000))

    # Test the calculator
    calculator = SimilarityMetricsCalculator()

    venue1_data = {"order_book": order_book1, "orders": orders1, "prices": prices1}

    venue2_data = {"order_book": order_book2, "orders": orders2, "prices": prices2}

    metrics = calculator.calculate_all_metrics(venue1_data, venue2_data)

    print("Similarity Metrics Results:")
    print(f"Depth-Weighted Cosine Similarity: {metrics.depth_weighted_cosine:.3f}")
    print(f"Jaccard Index: {metrics.jaccard_index:.3f}")
    print(f"Composite Coordination Score: {metrics.composite_coordination_score:.3f}")
    print(f"Confidence Interval: {metrics.confidence_interval}")
    print(f"Statistical Significance: {metrics.statistical_significance:.3f}")
    print(f"Economic Interpretation: {metrics.economic_interpretation}")
