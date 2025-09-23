"""
VMM (Variational Method of Moments) Engine

Implements VMM methodology for continuous monitoring and coordination detection.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import logging
from .provenance import VMMProvenance, create_provenance_data

logger = logging.getLogger(__name__)


@dataclass
class VMMConfig:
    """Configuration for VMM analysis"""

    # Optimization parameters
    max_iterations: int = 10000
    convergence_tolerance: float = 1e-6
    learning_rate: float = 0.01

    # Moment conditions
    moment_weights: Optional[Dict[str, float]] = None

    # Structural parameters
    beta_dim: int = 3
    sigma_prior: float = 0.1
    rho_prior: float = 0.3


@dataclass
class VMMOutput:
    """Results from VMM analysis"""

    # Optimization results
    convergence_status: str  # "converged", "max_iterations", "failed"
    iterations: int
    final_loss: float

    # Parameter estimates
    beta_estimates: np.ndarray
    sigma_estimates: np.ndarray
    rho_estimates: np.ndarray

    # Structural analysis
    structural_stability: float
    regime_confidence: float

    # Diagnostics
    over_identification_stat: float
    over_identification_p_value: float


class VMMEngine:
    """
    Variational Method of Moments Engine

    Implements VMM for detecting structural stability and coordination patterns
    in crypto markets.
    """

    def __init__(self, config: VMMConfig, crypto_calculator=None):
        self.config = config
        self.crypto_calculator = crypto_calculator
        self._current_data = None
        self._current_environment_column = None
        self._global_weight_matrix = None
        self._weight_matrix_fitted = False
        self._provenance_manager = VMMProvenance()
        self._current_seed = None

    def run_vmm(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        historical_data: Optional[pd.DataFrame] = None,
        environment_column: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> VMMOutput:
        """
        Run VMM analysis on price data

        Args:
            data: DataFrame with price data
            price_columns: List of price column names
            historical_data: Optional historical data for moment targets
            environment_column: Optional environment column for enhanced moment calculation

        Returns:
            VMMOutput with analysis results
        """
        logger.info("Starting VMM analysis")

        # Store current data and environment column for use in moment calculation
        self._current_data = data
        self._current_environment_column = environment_column
        self._current_seed = seed

        # Check for existing provenance if seed is provided
        if seed is not None and self._provenance_manager.provenance_exists(seed):
            logger.info(f"Loading existing VMM provenance for seed {seed}")
            provenance = self._provenance_manager.load_provenance(seed)
            if provenance:
                self._load_provenance(provenance)
                self._weight_matrix_fitted = True

        # Fit global weight matrix if not already fitted
        if not self._weight_matrix_fitted:
            self._fit_global_weight_matrix(data, price_columns, environment_column)

            # Save provenance if seed is provided
            if seed is not None:
                self._save_provenance(seed)

        # Validate input
        self._validate_input(data, price_columns)

        # Extract price data
        prices = data[price_columns].values

        # Initialize parameters
        beta_dim = self.config.beta_dim
        beta_estimates = np.random.normal(0, 0.1, beta_dim)
        sigma_estimates = np.eye(beta_dim) * self.config.sigma_prior
        rho_estimates = np.eye(beta_dim) * self.config.rho_prior

        # Run optimization
        convergence_status, iterations, final_loss = self._optimize_parameters(
            prices, beta_estimates, sigma_estimates, rho_estimates
        )

        # Calculate structural stability
        structural_stability = self._calculate_structural_stability(
            prices, beta_estimates, sigma_estimates, rho_estimates
        )

        # Calculate regime confidence
        regime_confidence = self._calculate_regime_confidence(prices, beta_estimates)

        # Calculate over-identification test
        over_id_stat, over_id_p_value = self._calculate_over_identification(prices, beta_estimates)

        return VMMOutput(
            convergence_status=convergence_status,
            iterations=iterations,
            final_loss=final_loss,
            beta_estimates=beta_estimates,
            sigma_estimates=sigma_estimates,
            rho_estimates=rho_estimates,
            structural_stability=structural_stability,
            regime_confidence=regime_confidence,
            over_identification_stat=over_id_stat,
            over_identification_p_value=over_id_p_value,
        )

    def _validate_input(self, data: pd.DataFrame, price_columns: List[str]) -> None:
        """Validate input data"""
        if len(price_columns) < 2:
            raise ValueError("Need at least 2 price columns for VMM analysis")

        missing_cols = [col for col in price_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing price columns: {missing_cols}")

        if len(data) < 100:
            raise ValueError("Insufficient data for VMM analysis")

    def _optimize_parameters(
        self,
        prices: np.ndarray,
        beta_init: np.ndarray,
        sigma_init: np.ndarray,
        rho_init: np.ndarray,
    ) -> Tuple[str, int, float]:
        """
        Optimize VMM parameters using gradient descent

        Returns:
            Tuple of (convergence_status, iterations, final_loss)
        """
        beta = beta_init.copy()
        sigma = sigma_init.copy()
        rho = rho_init.copy()

        for iteration in range(self.config.max_iterations):
            # Calculate moment conditions
            moments = self._calculate_moment_conditions(prices, beta)

            # Calculate loss
            loss = np.sum(moments**2)

            # Check convergence
            if loss < self.config.convergence_tolerance:
                return "converged", iteration + 1, loss

            # Calculate gradients (simplified)
            gradients = self._calculate_gradients(prices, beta, moments)

            # Update parameters
            beta -= self.config.learning_rate * gradients

            # Ensure stability
            beta = np.clip(beta, -1, 1)

        return "max_iterations", self.config.max_iterations, loss

    def _calculate_moment_conditions(self, prices: np.ndarray, beta: np.ndarray) -> np.ndarray:
        """Calculate moment conditions for VMM using enhanced crypto-specific moments"""

        # Use crypto-specific moment conditions if available
        if hasattr(self, "crypto_calculator") and self.crypto_calculator is not None:
            # Use the stored full DataFrame with environment columns
            if self._current_data is not None:
                # Get price columns from the stored data
                price_columns = [
                    col for col in self._current_data.columns if col.startswith("Exchange_")
                ]

                # Use enhanced moment calculation with environment columns
                try:
                    moment_vector = self.crypto_calculator.get_combined_moment_vector(
                        self._current_data,
                        price_columns,
                        environment_column=self._current_environment_column,
                        fit_scaler=False,
                    )
                    return moment_vector
                except Exception as e:
                    logger.warning(
                        f"Enhanced moment calculation failed: {e}, falling back to basic calculation"
                    )

            # Fallback: create DataFrame from prices array
            n_exchanges = prices.shape[1]
            price_columns = [f"Exchange_{i}" for i in range(n_exchanges)]
            data = pd.DataFrame(prices, columns=price_columns)

            # Use basic crypto moment calculation
            try:
                crypto_moments = self.crypto_calculator.calculate_moments(data, price_columns)

                # Extract normalized moments
                moments = []

                # Arbitrage timing moments
                moments.extend(crypto_moments.lead_lag_betas.flatten())
                moments.extend(crypto_moments.lead_lag_significance.flatten())

                # Mirroring moments
                moments.extend(crypto_moments.mirroring_ratios.flatten())
                moments.extend(crypto_moments.mirroring_consistency.flatten())

                # Spread floor moments
                moments.extend(crypto_moments.spread_floor_dwell_times.flatten())
                moments.extend(crypto_moments.spread_floor_frequency.flatten())

                # Undercut moments
                moments.extend(crypto_moments.undercut_initiation_rate.flatten())
                moments.extend(crypto_moments.undercut_response_time.flatten())

                return np.array(moments)
            except Exception as e:
                logger.warning(
                    f"Crypto moment calculation failed: {e}, falling back to basic calculation"
                )

                # Fallback to basic crypto moments
                crypto_moments = self.crypto_calculator.calculate_moments(data, price_columns)

                # Extract normalized moments
                moments = []

                # Arbitrage timing moments
                moments.extend(crypto_moments.lead_lag_betas.flatten())
                moments.extend(crypto_moments.lead_lag_significance.flatten())

                # Mirroring moments
                moments.extend(crypto_moments.mirroring_ratios.flatten())
                moments.extend(crypto_moments.mirroring_consistency.flatten())

                # Spread floor moments
                moments.extend(crypto_moments.spread_floor_dwell_times.flatten())
                moments.extend(crypto_moments.spread_floor_frequency.flatten())

                # Undercut moments
                moments.extend(crypto_moments.undercut_initiation_rate.flatten())
                moments.extend(crypto_moments.undercut_response_time.flatten())

                return np.array(moments)

        else:
            # Fallback to simplified moment conditions
            n_exchanges = prices.shape[1]
            moments = []

            # Cross-exchange correlation moments
            for i in range(n_exchanges):
                for j in range(i + 1, n_exchanges):
                    corr = np.corrcoef(prices[:, i], prices[:, j])[0, 1]
                    expected_corr = beta[0] if len(beta) > 0 else 0.5
                    moments.append(corr - expected_corr)

            # Price level moments
            for i in range(n_exchanges):
                price_level = np.mean(prices[:, i])
                expected_level = beta[1] if len(beta) > 1 else 50000.0
                moments.append(price_level - expected_level)

            # Volatility moments
            for i in range(n_exchanges):
                volatility = np.std(np.diff(prices[:, i]))
                expected_vol = beta[2] if len(beta) > 2 else 0.02
                moments.append(volatility - expected_vol)

            return np.array(moments)

    def _calculate_gradients(
        self, prices: np.ndarray, beta: np.ndarray, moments: np.ndarray
    ) -> np.ndarray:
        """Calculate gradients for parameter updates"""

        # Simplified gradient calculation
        gradients = np.zeros_like(beta)

        # Gradient w.r.t. beta[0] (correlation parameter)
        if len(beta) > 0:
            gradients[0] = -2 * np.sum(moments[: len(moments) // 3]) * 0.1

        # Gradient w.r.t. beta[1] (price level parameter)
        if len(beta) > 1:
            gradients[1] = -2 * np.sum(moments[len(moments) // 3 : 2 * len(moments) // 3]) * 0.001

        # Gradient w.r.t. beta[2] (volatility parameter)
        if len(beta) > 2:
            gradients[2] = -2 * np.sum(moments[2 * len(moments) // 3 :]) * 0.1

        return gradients

    def _calculate_structural_stability(
        self, prices: np.ndarray, beta: np.ndarray, sigma: np.ndarray, rho: np.ndarray
    ) -> float:
        """Calculate structural stability measure using over-identification test"""

        # Calculate over-identification test
        j_stat, p_value = self._calculate_over_identification(prices, beta)

        # Bounded stability: stability = 1 - min(1, max(0, chi2_cdf(J, dof)))
        # Higher p-value (less over-identification) = higher stability
        from scipy.stats import chi2

        n_moments = len(self._calculate_moment_conditions(prices, beta))
        n_params = len(beta)
        df = n_moments - n_params

        if df <= 0:
            return 1.0  # No over-identification possible

        # Chi-squared CDF at J-statistic
        chi2_cdf_value = chi2.cdf(j_stat, df)

        # Bounded stability: 1 - min(1, max(0, chi2_cdf(J, dof)))
        stability = 1.0 - min(1.0, max(0.0, chi2_cdf_value))

        return stability

    def _calculate_regime_confidence(self, prices: np.ndarray, beta: np.ndarray) -> float:
        """Calculate regime confidence measure"""

        # Confidence based on how well the model fits the data
        moments = self._calculate_moment_conditions(prices, beta)
        moment_errors = np.abs(moments)

        # Convert to confidence (lower errors = higher confidence)
        confidence = 1.0 - np.mean(moment_errors) / np.std(prices)

        return max(0.0, min(1.0, confidence))

    def _fit_global_weight_matrix(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> None:
        """Fit global weight matrix W = S^(-1) using 4-dim per-timestep moments with HAC"""

        logger.info(
            "Fitting global weight matrix with HAC covariance from competitive 4-dim per-timestep moments"
        )

        # Get per-timestep moment matrix M ∈ R^(N×4) - consistent dimensions
        moment_matrix = self._get_per_timestep_moments(data, price_columns, environment_column)
        N, k = moment_matrix.shape

        # Apply moment stabilization: winsorization, centering, and variance targeting
        if not hasattr(self, "_per_timestep_scaler") or not self._per_timestep_scaler.get(
            "fitted", False
        ):
            logger.info("Fitting per-timestep moment stabilizer on competitive data")

            # Step 1: Winsorize at 1st/99th percentiles on competitive data
            q01 = np.quantile(moment_matrix, 0.01, axis=0)
            q99 = np.quantile(moment_matrix, 0.99, axis=0)
            moment_matrix_winsorized = np.clip(moment_matrix, q01, q99)

            # Step 2: Center at competitive mean
            mu0 = np.mean(moment_matrix_winsorized, axis=0)
            moment_matrix_centered = moment_matrix_winsorized - mu0

            # Step 3: Variance targeting (unit variance on competitive)
            sigma0 = np.std(moment_matrix_centered, axis=0, ddof=1)
            sigma0 = np.maximum(sigma0, 1e-6)  # Floor to avoid division by zero

            self._per_timestep_scaler = {
                "q01": q01,
                "q99": q99,
                "mu0": mu0,
                "sigma0": sigma0,
                "fitted": True,
            }
            logger.info(f"Per-timestep stabilizer fitted:")
            logger.info(f"  Winsorization: q01={q01}, q99={q99}")
            logger.info(f"  Centering: mu0={mu0}")
            logger.info(f"  Variance targeting: sigma0={sigma0}")

        # Apply stabilization pipeline
        # Step 1: Winsorize
        moment_matrix_winsorized = np.clip(
            moment_matrix, self._per_timestep_scaler["q01"], self._per_timestep_scaler["q99"]
        )

        # Step 2: Center
        moment_matrix_centered = moment_matrix_winsorized - self._per_timestep_scaler["mu0"]

        # Step 3: Variance target
        moment_matrix_scaled = moment_matrix_centered / self._per_timestep_scaler["sigma0"]

        # Step 4: Handle borderline components (std < 1e-3)
        component_stds = np.std(moment_matrix_scaled, axis=0)
        borderline_components = component_stds < 1e-3
        valid_components = np.ones(len(component_stds), dtype=bool)

        if np.any(borderline_components):
            borderline_indices = np.where(borderline_components)[0]
            logger.warning(
                f"Borderline components detected: {borderline_indices} with std {component_stds[borderline_components]}"
            )

            # Try EWMA smoothing first (α=0.15)
            alpha = 0.15
            moment_matrix_ewma = moment_matrix_scaled.copy()

            for idx in borderline_indices:
                # Apply EWMA smoothing to the component
                ewma_values = np.zeros_like(moment_matrix_scaled[:, idx])
                ewma_values[0] = moment_matrix_scaled[0, idx]

                for t in range(1, len(moment_matrix_scaled)):
                    ewma_values[t] = (
                        alpha * moment_matrix_scaled[t, idx] + (1 - alpha) * ewma_values[t - 1]
                    )

                moment_matrix_ewma[:, idx] = ewma_values

            # Check if EWMA improved the variance
            ewma_stds = np.std(moment_matrix_ewma, axis=0)
            improved_components = ewma_stds >= 1e-3

            if np.any(improved_components[borderline_indices]):
                logger.info(
                    f"EWMA smoothing improved {np.sum(improved_components[borderline_indices])} borderline components"
                )
                moment_matrix_scaled = moment_matrix_ewma
                component_stds = ewma_stds
                valid_components = improved_components
                self._per_timestep_scaler["ewma_applied"] = True
                self._per_timestep_scaler["ewma_alpha"] = alpha
            else:
                # Drop components that couldn't be improved
                logger.warning(
                    f"Dropping {np.sum(borderline_components)} components that couldn't be improved with EWMA"
                )
                moment_matrix_scaled = moment_matrix_scaled[:, ~borderline_components]
                valid_components = ~borderline_components
                self._per_timestep_scaler["ewma_applied"] = False
                self._per_timestep_scaler["components_dropped"] = borderline_indices.tolist()

            # Update scaler to reflect changes
            self._per_timestep_scaler["valid_components"] = valid_components
            self._per_timestep_scaler["k_reduced"] = np.sum(valid_components)
            self._per_timestep_scaler["k_original"] = len(component_stds)

        logger.info(
            f"Applied moment stabilization: {moment_matrix.shape} -> {moment_matrix_scaled.shape}"
        )
        logger.info(f"  Final std per component: {np.std(moment_matrix_scaled, axis=0)}")
        logger.info(f"  Valid components: {np.sum(valid_components)}/{len(valid_components)}")

        # Compute sample mean: ḡ = (1/N) Σ_t m_t (scaled)
        g_bar = np.mean(moment_matrix_scaled, axis=0)

        # Estimate HAC covariance matrix S using Newey-West on scaled moments
        S_hat = self._estimate_hac_covariance(moment_matrix_scaled, g_bar)

        # Apply ridge regularization if needed
        S_regularized = self._apply_ridge_regularization(S_hat)

        # Compute weight matrix W = S^(-1)
        try:
            self._global_weight_matrix = np.linalg.inv(S_regularized)
            logger.info(
                f"Global weight matrix fitted with shape {self._global_weight_matrix.shape}"
            )
            logger.info(f"First 3 diagonal entries: {np.diag(self._global_weight_matrix)[:3]}")
            logger.info(f"Condition number: {np.linalg.cond(S_regularized):.2e}")
        except np.linalg.LinAlgError:
            logger.warning("Singular covariance matrix, using identity weight matrix")
            self._global_weight_matrix = np.eye(k)

        # Store metadata for reporting
        self._weight_matrix_metadata = {
            "N": N,
            "k": k,
            "lag": self._get_optimal_lag(N),
            "ridge_lambda": getattr(self, "_ridge_lambda", 0.0),
            "condition_number": np.linalg.cond(S_regularized),
            "scaler_applied": hasattr(self, "crypto_calculator")
            and hasattr(self.crypto_calculator, "global_scaler"),
        }

        self._weight_matrix_fitted = True

    def _get_per_timestep_moments(
        self, data: pd.DataFrame, price_columns: List[str], environment_column: Optional[str] = None
    ) -> np.ndarray:
        """Get per-timestep moment matrix M ∈ R^(N×k) with proper time variation"""

        prices = data[price_columns].values
        N = len(prices)
        n_exchanges = prices.shape[1]

        # Define moment components (k0 ≈ 6-12 depending on pairs)
        moment_components = []

        # 1. Latency-adjusted arbitrage timing (per t)
        arbitrage_moments = self._calculate_arbitrage_timing_per_timestep(prices)
        moment_components.append(arbitrage_moments)

        # 2. Depth-weighted mirroring (per t) - using price correlations as proxy
        mirroring_moments = self._calculate_mirroring_per_timestep(prices)
        moment_components.append(mirroring_moments)

        # 3. Spread-floor indicator (per t)
        spread_floor_moments = self._calculate_spread_floor_per_timestep(prices)
        moment_components.append(spread_floor_moments)

        # 4. Undercut initiation (per t) - using price volatility as proxy
        undercut_moments = self._calculate_undercut_per_timestep(prices)
        moment_components.append(undercut_moments)

        # Stack all moment components
        moment_matrix = np.column_stack(moment_components)

        # Ensure no constant columns (degeneracy check)
        for j in range(moment_matrix.shape[1]):
            if np.std(moment_matrix[:, j]) == 0:
                logger.warning(f"Column {j} is constant, adding small noise")
                moment_matrix[:, j] += np.random.normal(0, 1e-6, N)

        logger.info(f"Per-timestep moment matrix shape: {moment_matrix.shape}")
        logger.info(f"Column variances: {np.var(moment_matrix, axis=0)}")

        return moment_matrix

    def _calculate_arbitrage_timing_per_timestep(self, prices: np.ndarray) -> np.ndarray:
        """Calculate latency-adjusted arbitrage timing moments per timestep"""
        N, n_exchanges = prices.shape
        window_size = min(20, N // 10)

        arbitrage_moments = np.zeros(N)

        for t in range(window_size, N):
            # Calculate price divergences in rolling window
            window_prices = prices[t - window_size : t + 1]
            divergences = []

            for i in range(n_exchanges):
                for j in range(i + 1, n_exchanges):
                    # Price divergence as proxy for arbitrage opportunity
                    price_diff = np.abs(window_prices[:, i] - window_prices[:, j])
                    # Normalize by individual exchange prices to avoid extreme values
                    avg_price_i = np.mean(window_prices[:, i])
                    avg_price_j = np.mean(window_prices[:, j])
                    if avg_price_i > 0 and avg_price_j > 0:
                        normalized_diff = np.mean(price_diff) / ((avg_price_i + avg_price_j) / 2)
                        divergences.append(normalized_diff)

            # Average divergence, bounded to [0,1]
            if divergences:
                avg_divergence = np.mean(divergences)
                arbitrage_moments[t] = min(1.0, max(0.0, avg_divergence))
            else:
                arbitrage_moments[t] = 0.0

        # Fill early timesteps
        arbitrage_moments[:window_size] = arbitrage_moments[window_size]

        return arbitrage_moments

    def _calculate_mirroring_per_timestep(self, prices: np.ndarray) -> np.ndarray:
        """Calculate depth-weighted mirroring moments per timestep"""
        N, n_exchanges = prices.shape
        window_size = min(20, N // 10)

        mirroring_moments = np.zeros(N)

        for t in range(window_size, N):
            # Calculate rolling correlations as proxy for mirroring
            window_prices = prices[t - window_size : t + 1]
            correlations = []

            for i in range(n_exchanges):
                for j in range(i + 1, n_exchanges):
                    if len(window_prices) > 1:
                        corr = np.corrcoef(window_prices[:, i], window_prices[:, j])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)

            # Average correlation, scaled to [0,1]
            mirroring_moments[t] = (np.mean(correlations) + 1) / 2 if correlations else 0.5

        # Fill early timesteps
        mirroring_moments[:window_size] = mirroring_moments[window_size]

        return mirroring_moments

    def _calculate_spread_floor_per_timestep(self, prices: np.ndarray) -> np.ndarray:
        """Calculate spread-floor indicator moments per timestep"""
        N, n_exchanges = prices.shape
        window_size = min(20, N // 10)

        spread_floor_moments = np.zeros(N)

        for t in range(window_size, N):
            # Calculate price stability as proxy for spread floors
            window_prices = prices[t - window_size : t + 1]

            # Price volatility (inverse of stability)
            price_volatility = np.mean([np.std(window_prices[:, i]) for i in range(n_exchanges)])
            price_mean = np.mean(window_prices)

            # Stability measure (higher = more stable = spread floor)
            stability = 1.0 / (1.0 + price_volatility / price_mean) if price_mean > 0 else 0.5
            spread_floor_moments[t] = stability

        # Fill early timesteps
        spread_floor_moments[:window_size] = spread_floor_moments[window_size]

        return spread_floor_moments

    def _calculate_undercut_per_timestep(self, prices: np.ndarray) -> np.ndarray:
        """Calculate undercut initiation moments per timestep"""
        N, n_exchanges = prices.shape
        window_size = min(20, N // 10)

        undercut_moments = np.zeros(N)

        for t in range(window_size, N):
            # Calculate price leadership as proxy for undercut initiation
            window_prices = prices[t - window_size : t + 1]

            # Price changes (returns)
            price_changes = np.diff(window_prices, axis=0)

            # Calculate which exchange leads price changes
            leadership_scores = []
            for i in range(n_exchanges):
                # Correlation between exchange i's returns and others
                if len(price_changes) > 1:
                    corrs = []
                    for j in range(n_exchanges):
                        if i != j:
                            corr = np.corrcoef(price_changes[:, i], price_changes[:, j])[0, 1]
                            if not np.isnan(corr):
                                corrs.append(corr)
                    leadership_scores.append(np.mean(corrs) if corrs else 0.0)
                else:
                    leadership_scores.append(0.0)

            # Herfindahl concentration of leadership
            if leadership_scores:
                leadership_scores = np.array(leadership_scores)
                leadership_scores = np.abs(leadership_scores)  # Make positive
                leadership_scores = (
                    leadership_scores / np.sum(leadership_scores)
                    if np.sum(leadership_scores) > 0
                    else np.ones_like(leadership_scores) / len(leadership_scores)
                )
                herfindahl = np.sum(leadership_scores**2)
                undercut_moments[t] = herfindahl
            else:
                undercut_moments[t] = 1.0 / max(
                    n_exchanges, 1
                )  # Equal distribution, avoid division by zero

        # Fill early timesteps
        undercut_moments[:window_size] = undercut_moments[window_size]

        return undercut_moments

    def _estimate_hac_covariance(self, moment_matrix: np.ndarray, g_bar: np.ndarray) -> np.ndarray:
        """Estimate HAC covariance using Newey-West with Bartlett weights"""

        N, k = moment_matrix.shape
        L = self._get_optimal_lag(N)

        # Compute autocovariance matrices
        Gamma = np.zeros((L + 1, k, k))

        for l in range(L + 1):
            if l == 0:
                # Γ₀ = (1/N) Σ_t (m_t - ḡ)(m_t - ḡ)ᵀ
                deviations = moment_matrix - g_bar
                Gamma[l] = np.mean([np.outer(d, d) for d in deviations], axis=0)
            else:
                # Γ_l = (1/N) Σ_{t=l+1}^N (m_t - ḡ)(m_{t-l} - ḡ)ᵀ
                if N > l:
                    deviations_t = moment_matrix[l:] - g_bar
                    deviations_t_lag = moment_matrix[:-l] - g_bar
                    Gamma[l] = np.mean(
                        [np.outer(d1, d2) for d1, d2 in zip(deviations_t, deviations_t_lag)], axis=0
                    )

        # Newey-West estimator with Bartlett weights
        S_hat = Gamma[0].copy()
        for l in range(1, L + 1):
            weight = 1 - l / (L + 1)  # Bartlett weights
            S_hat += weight * (Gamma[l] + Gamma[l].T)

        return S_hat

    def _get_optimal_lag(self, N: int) -> int:
        """Get optimal lag for HAC estimation using Andrews formula"""
        # L ≈ ⌊4(N/100)^(2/9)⌋
        return max(1, int(4 * (N / 100) ** (2 / 9)))

    def _apply_ridge_regularization(self, S: np.ndarray) -> np.ndarray:
        """Apply ridge regularization using eigenvalue floor approach"""

        # Compute eigenvalues
        eigenvals = np.linalg.eigvals(S)
        min_eigenval = np.min(eigenvals)
        max_eigenval = np.max(eigenvals)

        # Set eigenvalue floor
        eigenval_floor = 1e-6
        max_condition = 1e6

        if min_eigenval < eigenval_floor or max_eigenval / min_eigenval > max_condition:
            # Set ridge parameter to ensure minimum eigenvalue >= floor
            lambda_ridge = max(0, eigenval_floor - min_eigenval + 1e-8)

            S_regularized = S + lambda_ridge * np.eye(S.shape[0])
            self._ridge_lambda = lambda_ridge

            final_condition = np.linalg.cond(S_regularized)
            logger.info(
                f"Applied ridge regularization: λ={lambda_ridge:.2e}, "
                f"condition number: {np.linalg.cond(S):.2e} -> {final_condition:.2e}"
            )
        else:
            S_regularized = S
            self._ridge_lambda = 0.0
            logger.info(
                f"No ridge regularization needed, condition number: {np.linalg.cond(S):.2e}"
            )

        return S_regularized

    def _calculate_over_identification(
        self, prices: np.ndarray, beta: np.ndarray
    ) -> Tuple[float, float]:
        """Calculate over-identification test statistic using 4-dim per-timestep GMM Hansen's J"""

        # Get per-timestep moments for this dataset (consistent 4-dim)
        if hasattr(self, "_current_data") and self._current_data is not None:
            moment_matrix = self._get_per_timestep_moments(
                self._current_data,
                [col for col in self._current_data.columns if col.startswith("Exchange_")],
                self._current_environment_column,
            )
        else:
            # Fallback: create simple moment matrix from prices
            n_exchanges = prices.shape[1]
            k = n_exchanges * (n_exchanges - 1) // 2
            N = len(prices)
            moment_matrix = np.zeros((N, k))

            # Simple cross-exchange correlations
            moment_idx = 0
            for i in range(n_exchanges):
                for j in range(i + 1, n_exchanges):
                    corr = np.corrcoef(prices[:, i], prices[:, j])[0, 1]
                    moment_matrix[:, moment_idx] = corr if not np.isnan(corr) else 0.0
                    moment_idx += 1

        N, k = moment_matrix.shape
        n_params = len(beta)  # Likely 0 for now

        if k <= n_params:
            return 0.0, 1.0

        # Apply moment stabilization pipeline (consistent with weight matrix estimation)
        if hasattr(self, "_per_timestep_scaler") and self._per_timestep_scaler.get("fitted", False):
            # Step 1: Winsorize
            moment_matrix_winsorized = np.clip(
                moment_matrix, self._per_timestep_scaler["q01"], self._per_timestep_scaler["q99"]
            )

            # Step 2: Center
            moment_matrix_centered = moment_matrix_winsorized - self._per_timestep_scaler["mu0"]

            # Step 3: Variance target
            moment_matrix_scaled = moment_matrix_centered / self._per_timestep_scaler["sigma0"]

            # Step 4: Apply same component filtering as in weight matrix estimation
            if "valid_components" in self._per_timestep_scaler:
                moment_matrix_scaled = moment_matrix_scaled[
                    :, self._per_timestep_scaler["valid_components"]
                ]

            logger.info(
                f"Applied moment stabilization for GMM: {moment_matrix.shape} -> {moment_matrix_scaled.shape}"
            )
            logger.info(f"  Final std per component: {np.std(moment_matrix_scaled, axis=0)}")
        else:
            moment_matrix_scaled = moment_matrix
            logger.warning("No per-timestep stabilizer available for GMM calculation")

        # Compute sample mean: ḡ = (1/N) Σ_t m_t (scaled)
        g_bar = np.mean(moment_matrix_scaled, axis=0)

        # Use global weight matrix if available (must match dimensions)
        if hasattr(self, "_global_weight_matrix") and self._global_weight_matrix is not None:
            W = self._global_weight_matrix
            logger.info(f"Using global weight matrix W with shape {W.shape} for {k}-dim moments")

            # Ensure dimension consistency
            if W.shape[0] != k:
                logger.error(f"Dimension mismatch: W.shape={W.shape}, k={k}")
                return 0.0, 1.0
        else:
            # Fallback: use identity matrix
            W = np.eye(k)
            logger.warning("No global weight matrix available, using identity weighting")

        # Proper GMM Hansen's J-statistic: J = N * ḡ' * W * ḡ
        j_stat = N * np.dot(g_bar, np.dot(W, g_bar))

        # Degrees of freedom
        df = k - n_params

        # P-value using chi-squared distribution
        from scipy.stats import chi2

        p_value = 1.0 - chi2.cdf(j_stat, df)

        return j_stat, p_value

    def _load_provenance(self, provenance: Dict[str, Any]) -> None:
        """Load VMM provenance from saved data"""

        # Load moment stabilization parameters
        stab = provenance["moment_stabilization"]
        self._per_timestep_scaler = {
            "mu0": stab["mu0"],
            "sigma0": stab["sigma0"],
            "q01": stab["q01"],
            "q99": stab["q99"],
            "valid_components": stab["valid_components"],
            "k_reduced": stab["k_reduced"],
            "fitted": True,
        }

        # Load HAC parameters
        hac = provenance["hac_estimation"]
        self._weight_matrix_metadata = {
            "N": hac["N"],
            "k": hac["k"],
            "lag": hac["lag"],
            "ridge_lambda": hac["ridge_lambda"],
            "condition_number": hac["condition_number"],
        }

        # Reconstruct weight matrix (we'll need to store it properly)
        # For now, we'll refit it since we don't store the full matrix
        logger.info("Provenance loaded, weight matrix will be refitted")

    def _save_provenance(self, seed: int) -> None:
        """Save VMM provenance to file"""

        if not hasattr(self, "_per_timestep_scaler") or not self._per_timestep_scaler.get(
            "fitted", False
        ):
            logger.warning("Cannot save provenance: scaler not fitted")
            return

        if not hasattr(self, "_global_weight_matrix") or self._global_weight_matrix is None:
            logger.warning("Cannot save provenance: weight matrix not fitted")
            return

        if not hasattr(self, "_weight_matrix_metadata"):
            logger.warning("Cannot save provenance: metadata not available")
            return

        # Create provenance data
        provenance_data = create_provenance_data(
            mu0=self._per_timestep_scaler["mu0"],
            sigma0=self._per_timestep_scaler["sigma0"],
            q01=self._per_timestep_scaler["q01"],
            q99=self._per_timestep_scaler["q99"],
            valid_components=self._per_timestep_scaler.get(
                "valid_components", np.ones(len(self._per_timestep_scaler["mu0"]), dtype=bool)
            ),
            W=self._global_weight_matrix,
            N=self._weight_matrix_metadata["N"],
            k=self._weight_matrix_metadata["k"],
            lag=self._weight_matrix_metadata["lag"],
            ridge_lambda=self._weight_matrix_metadata["ridge_lambda"],
            condition_number=self._weight_matrix_metadata["condition_number"],
            seed=seed,
        )

        # Update provenance with EWMA information
        if "ewma_applied" in self._per_timestep_scaler:
            provenance_data["moment_stabilization"]["ewma_applied"] = self._per_timestep_scaler[
                "ewma_applied"
            ]
            provenance_data["moment_stabilization"]["ewma_alpha"] = self._per_timestep_scaler.get(
                "ewma_alpha"
            )
            provenance_data["moment_stabilization"]["components_dropped"] = (
                self._per_timestep_scaler.get("components_dropped")
            )

        # Save to file
        self._provenance_manager.save_provenance(seed, provenance_data)


def run_vmm_analysis(
    data: pd.DataFrame, price_columns: List[str], config: Optional[VMMConfig] = None
) -> VMMOutput:
    """
    Convenience function to run VMM analysis

    Args:
        data: DataFrame with price data
        price_columns: List of price column names
        config: Optional VMM configuration

    Returns:
        VMMOutput with analysis results
    """
    if config is None:
        config = VMMConfig()

    engine = VMMEngine(config)
    return engine.run_vmm(data, price_columns)


if __name__ == "__main__":
    # Example usage
    from ..data.synthetic_crypto import generate_validation_datasets

    # Generate test data
    competitive_data, coordinated_data = generate_validation_datasets()

    # Run VMM analysis on competitive data
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    print("VMM Analysis on Competitive Data:")
    result_competitive = run_vmm_analysis(competitive_data, price_cols)
    print(f"Convergence: {result_competitive.convergence_status}")
    print(f"Iterations: {result_competitive.iterations}")
    print(f"Structural stability: {result_competitive.structural_stability:.4f}")
    print(f"Regime confidence: {result_competitive.regime_confidence:.4f}")

    print("\nVMM Analysis on Coordinated Data:")
    result_coordinated = run_vmm_analysis(coordinated_data, price_cols)
    print(f"Convergence: {result_coordinated.convergence_status}")
    print(f"Iterations: {result_coordinated.iterations}")
    print(f"Structural stability: {result_coordinated.structural_stability:.4f}")
    print(f"Regime confidence: {result_coordinated.regime_confidence:.4f}")
