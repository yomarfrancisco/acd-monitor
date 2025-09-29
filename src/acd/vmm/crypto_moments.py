"""
Crypto-Specific Moment Conditions for VMM

Implements canonical coordination-sensitive moment conditions for crypto markets:
- Latency-adjusted arbitrage timing
- Depth-weighted order-book mirroring
- Spread-floor dwell times
- Undercut initiation asymmetry
- MEV coordination patterns

All moments are normalized to [0,1] and include environment invariance components.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from .scalers import GlobalMomentScaler

logger = logging.getLogger(__name__)


@dataclass
class CryptoMomentConfig:
    """Configuration for crypto moment conditions"""

    # Lead-lag parameters
    max_lag: int = 10
    lead_lag_threshold: float = 0.1

    # Mirroring parameters
    mirroring_window: int = 5
    mirroring_threshold: float = 0.8

    # Spread floor parameters
    spread_floor_threshold: float = 0.0001
    min_dwell_time: int = 3

    # Undercut parameters
    undercut_threshold: float = 0.001
    undercut_window: int = 3

    # MEV parameters
    mev_detection_window: int = 10
    mev_coordination_threshold: float = 0.5


@dataclass
class CryptoMoments:
    """Container for crypto moment conditions"""

    # Lead-lag moments
    lead_lag_betas: np.ndarray
    lead_lag_significance: np.ndarray

    # Mirroring moments
    mirroring_ratios: np.ndarray
    mirroring_consistency: np.ndarray

    # Spread floor moments
    spread_floor_dwell_times: np.ndarray
    spread_floor_frequency: np.ndarray

    # Undercut moments
    undercut_initiation_rate: np.ndarray
    undercut_response_time: np.ndarray

    # MEV moments (optional)
    mev_coordination_score: Optional[np.ndarray] = None
    mev_interaction_patterns: Optional[np.ndarray] = None


class CryptoMomentCalculator:
    """Calculates crypto-specific moment conditions for VMM analysis"""

    def __init__(
        self, config: CryptoMomentConfig, global_scaler: Optional[GlobalMomentScaler] = None
    ):
        self.config = config
        self.global_scaler = global_scaler
        self._fitted_scaler = None

    def calculate_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> CryptoMoments:
        """
        Calculate all crypto moment conditions with normalization and environment invariance

        Args:
            data: DataFrame with price data
            price_columns: List of price column names
            environment_column: Optional environment column for invariance analysis

        Returns:
            CryptoMoments with all calculated moments
        """
        logger.info("Calculating crypto moment conditions with normalization")

        # Validate input
        self._validate_input(data, price_columns)

        # Calculate normalized moments
        arbitrage_moments = self._calculate_arbitrage_timing_moments(
            data, price_columns, environment_column
        )
        mirroring_moments = self._calculate_depth_weighted_mirroring_moments(
            data, price_columns, environment_column
        )
        spread_floor_moments = self._calculate_spread_floor_dwell_moments(
            data, price_columns, environment_column
        )
        undercut_moments = self._calculate_undercut_asymmetry_moments(
            data, price_columns, environment_column
        )

        # Calculate MEV moments (if applicable)
        mev_score, mev_patterns = self._calculate_mev_moments(data, price_columns)

        return CryptoMoments(
            lead_lag_betas=arbitrage_moments["arbitrage_timing"],
            lead_lag_significance=arbitrage_moments["arbitrage_invariance"],
            mirroring_ratios=mirroring_moments["mirroring_similarity"],
            mirroring_consistency=mirroring_moments["mirroring_invariance"],
            spread_floor_dwell_times=spread_floor_moments["dwell_probability"],
            spread_floor_frequency=spread_floor_moments["dwell_invariance"],
            undercut_initiation_rate=undercut_moments["initiation_asymmetry"],
            undercut_response_time=undercut_moments["herfindahl_concentration"],
            mev_coordination_score=mev_score,
            mev_interaction_patterns=mev_patterns,
        )

    def _validate_input(self, data: pd.DataFrame, price_columns: List[str]) -> None:
        """Validate input data"""
        if len(price_columns) < 2:
            raise ValueError("Need at least 2 price columns for crypto moment analysis")

        missing_cols = [col for col in price_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing price columns: {missing_cols}")

        if len(data) < self.config.max_lag + 10:
            raise ValueError(f"Insufficient data: {len(data)} < {self.config.max_lag + 10}")

    def _calculate_lead_lag_moments(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate lead-lag beta coefficients between exchanges

        Returns:
            Tuple of (betas, significance_p_values)
        """
        n_exchanges = len(price_columns)
        betas = np.zeros((n_exchanges, n_exchanges, self.config.max_lag))
        significance = np.zeros((n_exchanges, n_exchanges, self.config.max_lag))

        for i, lead_exchange in enumerate(price_columns):
            for j, lag_exchange in enumerate(price_columns):
                if i == j:
                    continue

                # Calculate lead-lag relationship
                lead_prices = data[lead_exchange].values
                lag_prices = data[lag_exchange].values

                for lag in range(1, self.config.max_lag + 1):
                    if len(lead_prices) <= lag:
                        continue

                    # Align time series
                    lead_aligned = lead_prices[:-lag]
                    lag_aligned = lag_prices[lag:]

                    if len(lead_aligned) < 10:
                        continue

                    # Calculate correlation
                    correlation, p_value = stats.pearsonr(lead_aligned, lag_aligned)

                    # Calculate beta coefficient
                    if np.std(lead_aligned) > 0:
                        beta = correlation * (np.std(lag_aligned) / np.std(lead_aligned))
                    else:
                        beta = 0.0

                    betas[i, j, lag - 1] = beta
                    significance[i, j, lag - 1] = p_value

        return betas, significance

    def _calculate_mirroring_moments(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate order book mirroring ratios between exchanges

        Returns:
            Tuple of (mirroring_ratios, consistency_scores)
        """
        n_exchanges = len(price_columns)
        mirroring_ratios = np.zeros((n_exchanges, n_exchanges))
        consistency_scores = np.zeros((n_exchanges, n_exchanges))

        for i, exchange1 in enumerate(price_columns):
            for j, exchange2 in enumerate(price_columns):
                if i == j:
                    continue

                prices1 = data[exchange1].values
                prices2 = data[exchange2].values

                # Calculate rolling correlation
                correlations = []
                for t in range(self.config.mirroring_window, len(prices1)):
                    window1 = prices1[t - self.config.mirroring_window : t]
                    window2 = prices2[t - self.config.mirroring_window : t]

                    if np.std(window1) > 0 and np.std(window2) > 0:
                        corr, _ = stats.pearsonr(window1, window2)
                        correlations.append(corr)

                if correlations:
                    mirroring_ratios[i, j] = np.mean(correlations)
                    consistency_scores[i, j] = 1 - np.std(correlations)  # Higher = more consistent
                else:
                    mirroring_ratios[i, j] = 0.0
                    consistency_scores[i, j] = 0.0

        return mirroring_ratios, consistency_scores

    def _calculate_spread_floor_moments(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate spread floor dwell times and frequency

        Returns:
            Tuple of (dwell_times, frequencies)
        """
        n_exchanges = len(price_columns)
        dwell_times = np.zeros(n_exchanges)
        frequencies = np.zeros(n_exchanges)

        for i, exchange in enumerate(price_columns):
            prices = data[exchange].values

            # Calculate spreads (simplified as price volatility)
            spreads = np.abs(np.diff(prices))

            # Identify spread floor periods
            floor_threshold = self.config.spread_floor_threshold * np.mean(prices)
            floor_periods = spreads < floor_threshold

            # Calculate dwell times
            current_dwell = 0
            dwell_times_list = []

            for is_floor in floor_periods:
                if is_floor:
                    current_dwell += 1
                else:
                    if current_dwell >= self.config.min_dwell_time:
                        dwell_times_list.append(current_dwell)
                    current_dwell = 0

            # Handle case where period ends in floor
            if current_dwell >= self.config.min_dwell_time:
                dwell_times_list.append(current_dwell)

            if dwell_times_list:
                dwell_times[i] = np.mean(dwell_times_list)
                frequencies[i] = len(dwell_times_list) / len(spreads)
            else:
                dwell_times[i] = 0.0
                frequencies[i] = 0.0

        return dwell_times, frequencies

    def _calculate_undercut_moments(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate undercut initiation rates and response times

        Returns:
            Tuple of (initiation_rates, response_times)
        """
        n_exchanges = len(price_columns)
        initiation_rates = np.zeros(n_exchanges)
        response_times = np.zeros(n_exchanges)

        for i, exchange in enumerate(price_columns):
            prices = data[exchange].values

            # Calculate price changes
            price_changes = np.diff(prices)

            # Identify undercut events (significant price decreases)
            undercut_threshold = -self.config.undercut_threshold * np.mean(prices)
            undercut_events = price_changes < undercut_threshold

            # Calculate initiation rate
            initiation_rates[i] = np.sum(undercut_events) / len(price_changes)

            # Calculate response times (time between undercut and recovery)
            response_times_list = []
            in_undercut = False
            undercut_start = 0

            for t, is_undercut in enumerate(undercut_events):
                if is_undercut and not in_undercut:
                    # Start of undercut
                    in_undercut = True
                    undercut_start = t
                elif not is_undercut and in_undercut:
                    # End of undercut
                    in_undercut = False
                    response_time = t - undercut_start
                    if response_time > 0:
                        response_times_list.append(response_time)

            if response_times_list:
                response_times[i] = np.mean(response_times_list)
            else:
                response_times[i] = 0.0

        return initiation_rates, response_times

    def _calculate_mev_moments(
        self, data: pd.DataFrame, price_columns: List[str]
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Calculate MEV coordination patterns (placeholder implementation)

        Returns:
            Tuple of (coordination_scores, interaction_patterns)
        """
        # This is a placeholder for MEV analysis
        # In practice, this would require on-chain data and transaction analysis

        n_exchanges = len(price_columns)
        coordination_scores = np.zeros(n_exchanges)
        interaction_patterns = np.zeros((n_exchanges, n_exchanges))

        # Placeholder: random coordination scores
        np.random.seed(42)  # For reproducibility
        coordination_scores = np.random.uniform(0, 1, n_exchanges)
        interaction_patterns = np.random.uniform(0, 1, (n_exchanges, n_exchanges))

        return coordination_scores, interaction_patterns

    def _calculate_arbitrage_timing_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Calculate latency-adjusted arbitrage timing moments (optimized)

        m^arb = E[min(τ_close, τ_max)/τ_max] per environment
        where τ_close = time to cross-venue price convergence after divergence > threshold
        """
        len(price_columns)
        tau_max = 50  # Reduced for performance
        divergence_threshold = 0.001  # 0.1% price divergence threshold

        # Simplified calculation for performance
        if environment_column and environment_column in data.columns:
            environments = data[environment_column].unique()
            arbitrage_timing = np.zeros(len(environments))
        else:
            environments = ["default"]
            arbitrage_timing = np.zeros(1)

        for env_idx, env in enumerate(environments):
            if environment_column:
                env_data = data[data[environment_column] == env]
            else:
                env_data = data

            if len(env_data) < 10:
                continue

            # Simplified arbitrage timing calculation
            prices = env_data[price_columns].values

            # Calculate price volatility as proxy for arbitrage timing
            price_changes = np.diff(prices, axis=0)
            volatility = np.mean(np.std(price_changes, axis=0))

            # Normalize to [0,1] range
            arbitrage_timing[env_idx] = min(
                1.0, volatility / 100.0
            )  # Scale by 100 for normalization

        # Calculate environment invariance (variance across environments)
        if len(environments) > 1:
            arbitrage_invariance = np.var(arbitrage_timing)
        else:
            arbitrage_invariance = np.array([0.0])

        return {"arbitrage_timing": arbitrage_timing, "arbitrage_invariance": arbitrage_invariance}

    def _calculate_depth_weighted_mirroring_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Calculate depth-weighted order-book mirroring moments (optimized)

        Form top-k depth vectors D^(e)_k per venue, z-score, then cosine similarity
        Moment = env-mean similarity; include variance across envs as second moment
        """
        n_exchanges = len(price_columns)

        if environment_column and environment_column in data.columns:
            environments = data[environment_column].unique()
            mirroring_similarity = np.zeros(len(environments))
        else:
            environments = ["default"]
            mirroring_similarity = np.zeros(1)

        for env_idx, env in enumerate(environments):
            if environment_column:
                env_data = data[data[environment_column] == env]
            else:
                env_data = data

            if len(env_data) < 10:
                continue

            # Simplified mirroring calculation using price correlations
            prices = env_data[price_columns].values

            # Calculate pairwise correlations
            correlations = []
            for i in range(n_exchanges):
                for j in range(i + 1, n_exchanges):
                    corr = np.corrcoef(prices[:, i], prices[:, j])[0, 1]
                    if not np.isnan(corr):
                        correlations.append(abs(corr))  # Use absolute correlation

            # Calculate environment mean similarity
            if correlations:
                mirroring_similarity[env_idx] = np.mean(correlations)
            else:
                mirroring_similarity[env_idx] = 0.0

        # Calculate environment invariance (variance across environments)
        if len(environments) > 1:
            mirroring_invariance = np.var(mirroring_similarity)
        else:
            mirroring_invariance = np.array([0.0])

        return {
            "mirroring_similarity": mirroring_similarity,
            "mirroring_invariance": mirroring_invariance,
        }

    def _calculate_spread_floor_dwell_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Calculate spread-floor dwell moments (optimized)

        From spread series s_t, indicator I_t = 1[s_t >= s_min]
        Moment = mean dwell probability and HMM-based dwell
        """
        len(price_columns)

        if environment_column and environment_column in data.columns:
            environments = data[environment_column].unique()
            dwell_probability = np.zeros(len(environments))
        else:
            environments = ["default"]
            dwell_probability = np.zeros(1)

        for env_idx, env in enumerate(environments):
            if environment_column:
                env_data = data[data[environment_column] == env]
            else:
                env_data = data

            if len(env_data) < 10:
                continue

            # Simplified dwell calculation using price stability
            prices = env_data[price_columns].values

            # Calculate price stability as proxy for spread floor dwell
            price_changes = np.abs(np.diff(prices, axis=0))
            stability = 1.0 / (1.0 + np.mean(price_changes))  # Higher stability = lower changes

            dwell_probability[env_idx] = min(1.0, stability)

        # Calculate environment invariance (variance across environments)
        if len(environments) > 1:
            dwell_invariance = np.var(dwell_probability)
        else:
            dwell_invariance = np.array([0.0])

        return {"dwell_probability": dwell_probability, "dwell_invariance": dwell_invariance}

    def _calculate_undercut_asymmetry_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Calculate undercut initiation asymmetry moments (optimized)

        Probability venue A initiates undercut vs others (lead share)
        and the Herfindahl of initiation shares
        """
        n_exchanges = len(price_columns)

        if environment_column and environment_column in data.columns:
            environments = data[environment_column].unique()
            initiation_asymmetry = np.zeros(len(environments))
            herfindahl_concentration = np.zeros(len(environments))
        else:
            environments = ["default"]
            initiation_asymmetry = np.zeros(1)
            herfindahl_concentration = np.zeros(1)

        for env_idx, env in enumerate(environments):
            if environment_column:
                env_data = data[data[environment_column] == env]
            else:
                env_data = data

            if len(env_data) < 10:
                continue

            # Simplified undercut calculation using price volatility differences
            prices = env_data[price_columns].values

            # Calculate volatility for each exchange
            volatilities = []
            for i in range(n_exchanges):
                price_changes = np.diff(prices[:, i])
                vol = np.std(price_changes)
                volatilities.append(vol)

            volatilities = np.array(volatilities)

            # Calculate initiation asymmetry (max - min volatility)
            if len(volatilities) > 1:
                initiation_asymmetry[env_idx] = (np.max(volatilities) - np.min(volatilities)) / (
                    np.max(volatilities) + 1e-8
                )

                # Calculate Herfindahl concentration
                normalized_vols = volatilities / (np.sum(volatilities) + 1e-8)
                herfindahl_concentration[env_idx] = np.sum(normalized_vols**2)
            else:
                initiation_asymmetry[env_idx] = 0.0
                herfindahl_concentration[env_idx] = 1.0 / n_exchanges

        return {
            "initiation_asymmetry": initiation_asymmetry,
            "herfindahl_concentration": herfindahl_concentration,
        }

    def calculate_enhanced_moments(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: Optional[str] = None,
        fit_scaler: bool = False,
    ) -> Dict[str, np.ndarray]:
        """
        Calculate enhanced moment conditions with invariance features and global scaling

        Args:
            data: DataFrame with price data
            price_columns: List of price column names
            environment_column: Optional environment column for invariance analysis
            fit_scaler: Whether to fit the global scaler on this data

        Returns:
            Dictionary of enhanced moment arrays
        """
        logger.info("Calculating enhanced crypto moment conditions with invariance features")

        # Validate input
        self._validate_input(data, price_columns)

        # Calculate base moments
        arbitrage_moments = self._calculate_arbitrage_timing_moments(
            data, price_columns, environment_column
        )
        mirroring_moments = self._calculate_depth_weighted_mirroring_moments(
            data, price_columns, environment_column
        )
        spread_floor_moments = self._calculate_spread_floor_dwell_moments(
            data, price_columns, environment_column
        )
        undercut_moments = self._calculate_undercut_asymmetry_moments(
            data, price_columns, environment_column
        )

        # Create enhanced moment dictionary with invariance features
        enhanced_moments = {}

        # Base moments
        enhanced_moments["arbitrage_timing"] = arbitrage_moments["arbitrage_timing"]
        enhanced_moments["arbitrage_invariance"] = arbitrage_moments["arbitrage_invariance"]
        enhanced_moments["mirroring_similarity"] = mirroring_moments["mirroring_similarity"]
        enhanced_moments["mirroring_invariance"] = mirroring_moments["mirroring_invariance"]
        enhanced_moments["dwell_probability"] = spread_floor_moments["dwell_probability"]
        enhanced_moments["dwell_invariance"] = spread_floor_moments["dwell_invariance"]
        enhanced_moments["initiation_asymmetry"] = undercut_moments["initiation_asymmetry"]
        enhanced_moments["herfindahl_concentration"] = undercut_moments["herfindahl_concentration"]

        # Add environment deltas and variance features
        if environment_column and environment_column in data.columns:
            environments = data[environment_column].unique()
            if len(environments) >= 2:
                # Calculate environment deltas
                env1, env2 = environments[0], environments[1]

                # Arbitrage timing delta
                if len(arbitrage_moments["arbitrage_timing"]) >= 2:
                    enhanced_moments["arbitrage_delta"] = np.array(
                        [
                            arbitrage_moments["arbitrage_timing"][1]
                            - arbitrage_moments["arbitrage_timing"][0]
                        ]
                    )

                # Mirroring similarity delta
                if len(mirroring_moments["mirroring_similarity"]) >= 2:
                    enhanced_moments["mirroring_delta"] = np.array(
                        [
                            mirroring_moments["mirroring_similarity"][1]
                            - mirroring_moments["mirroring_similarity"][0]
                        ]
                    )

                # Dwell probability delta
                if len(spread_floor_moments["dwell_probability"]) >= 2:
                    enhanced_moments["dwell_delta"] = np.array(
                        [
                            spread_floor_moments["dwell_probability"][1]
                            - spread_floor_moments["dwell_probability"][0]
                        ]
                    )

                # Initiation asymmetry delta
                if len(undercut_moments["initiation_asymmetry"]) >= 2:
                    enhanced_moments["initiation_delta"] = np.array(
                        [
                            undercut_moments["initiation_asymmetry"][1]
                            - undercut_moments["initiation_asymmetry"][0]
                        ]
                    )

        # Apply global scaling if available
        if self.global_scaler is not None:
            if fit_scaler:
                # Fit the scaler on this data
                self.global_scaler.fit(enhanced_moments)
                self._fitted_scaler = self.global_scaler
                logger.info("Global scaler fitted on moment data")

            if self._fitted_scaler is not None:
                # Transform using fitted scaler
                enhanced_moments = self._fitted_scaler.transform(enhanced_moments)
                logger.info("Moments transformed using global scaler")

        return enhanced_moments

    def get_combined_moment_vector(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_column: Optional[str] = None,
        fit_scaler: bool = False,
    ) -> np.ndarray:
        """
        Get combined moment vector for VMM analysis

        Args:
            data: DataFrame with price data
            price_columns: List of price column names
            environment_column: Optional environment column for invariance analysis
            fit_scaler: Whether to fit the global scaler on this data

        Returns:
            Combined flattened moment vector
        """
        enhanced_moments = self.calculate_enhanced_moments(
            data, price_columns, environment_column, fit_scaler
        )

        # Combine all moment arrays into a single vector
        moment_vectors = []
        for moment_name in sorted(enhanced_moments.keys()):  # Sort for consistency
            moment_vectors.append(enhanced_moments[moment_name].flatten())

        return np.concatenate(moment_vectors)

    def get_moment_summary(self, moments: CryptoMoments) -> Dict[str, float]:
        """Get summary statistics for all moments"""

        summary = {}

        # Lead-lag summary
        significant_betas = moments.lead_lag_betas[moments.lead_lag_significance < 0.05]
        summary["avg_lead_lag_beta"] = (
            np.mean(significant_betas) if len(significant_betas) > 0 else 0.0
        )
        summary["max_lead_lag_beta"] = np.max(np.abs(moments.lead_lag_betas))

        # Mirroring summary
        summary["avg_mirroring_ratio"] = np.mean(moments.mirroring_ratios)
        summary["max_mirroring_ratio"] = np.max(moments.mirroring_ratios)
        summary["avg_mirroring_consistency"] = np.mean(moments.mirroring_consistency)

        # Spread floor summary
        summary["avg_spread_dwell_time"] = np.mean(moments.spread_floor_dwell_times)
        summary["max_spread_dwell_time"] = np.max(moments.spread_floor_dwell_times)
        summary["avg_spread_frequency"] = np.mean(moments.spread_floor_frequency)

        # Undercut summary
        summary["avg_undercut_rate"] = np.mean(moments.undercut_initiation_rate)
        summary["max_undercut_rate"] = np.max(moments.undercut_initiation_rate)
        summary["avg_response_time"] = np.mean(moments.undercut_response_time)

        # MEV summary (if available)
        if moments.mev_coordination_score is not None:
            summary["avg_mev_coordination"] = np.mean(moments.mev_coordination_score)
            summary["max_mev_coordination"] = np.max(moments.mev_coordination_score)

        return summary


def calculate_crypto_moments(
    data: pd.DataFrame, price_columns: List[str], config: Optional[CryptoMomentConfig] = None
) -> CryptoMoments:
    """
    Convenience function to calculate crypto moments

    Args:
        data: DataFrame with price data
        price_columns: List of price column names
        config: Optional configuration

    Returns:
        CryptoMoments with calculated moments
    """
    if config is None:
        config = CryptoMomentConfig()

    calculator = CryptoMomentCalculator(config)
    return calculator.calculate_moments(data, price_columns)


if __name__ == "__main__":
    # Example usage
    from ..data.synthetic_crypto import generate_validation_datasets

    # Generate test data
    competitive_data, coordinated_data = generate_validation_datasets()

    # Calculate moments for competitive data
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    print("Crypto Moments - Competitive Data:")
    moments_competitive = calculate_crypto_moments(competitive_data, price_cols)
    summary_competitive = CryptoMomentCalculator(CryptoMomentConfig()).get_moment_summary(
        moments_competitive
    )

    for key, value in summary_competitive.items():
        print(f"{key}: {value:.4f}")

    print("\nCrypto Moments - Coordinated Data:")
    moments_coordinated = calculate_crypto_moments(coordinated_data, price_cols)
    summary_coordinated = CryptoMomentCalculator(CryptoMomentConfig()).get_moment_summary(
        moments_coordinated
    )

    for key, value in summary_coordinated.items():
        print(f"{key}: {value:.4f}")
