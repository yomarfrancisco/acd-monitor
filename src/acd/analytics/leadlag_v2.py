"""
Lead-Lag Analysis v2 - Research-Grade Module

Implements proper lead-lag analysis with:
- Log-returns instead of price levels
- Cross-correlation and lagged regression estimators
- HAC significance testing with bootstrap
- Multiple horizon support
"""

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class LeadLagV2Engine:
    """Research-grade lead-lag analysis engine."""

    def __init__(self, min_obs: int = 300, block_size: int = 10, bootstrap_reps: int = 1000):
        """
        Initialize lead-lag v2 engine.

        Args:
            min_obs: Minimum observations required for analysis
            block_size: Block size for circular bootstrap (seconds)
            bootstrap_reps: Number of bootstrap replications
        """
        self.min_obs = min_obs
        self.block_size = block_size
        self.bootstrap_reps = bootstrap_reps

    def prepare_data(self, data: Dict[str, pd.DataFrame], freq: str = "1S") -> pd.DataFrame:
        """
        Prepare aligned panel data with log-returns.

        Args:
            data: Dictionary of venue dataframes with 'mid' column
            freq: Resampling frequency

        Returns:
            Aligned panel with log-returns
        """
        logger.info(f"[LLV2:prep] Preparing data at {freq} frequency")

        # Resample and align all venues
        aligned_data = {}
        for venue, df in data.items():
            # Set datetime index if needed
            if not isinstance(df.index, pd.DatetimeIndex):
                if "ts_exchange" in df.columns:
                    df = df.set_index("ts_exchange")
                elif "ts_local" in df.columns:
                    df = df.set_index("ts_local")
                else:
                    logger.warning(f"[LLV2:skip] No datetime column for {venue}")
                    continue

            # Calculate mid price if not present
            if "mid" in df.columns:
                mid_series = df["mid"]
            elif "best_bid" in df.columns and "best_ask" in df.columns:
                # Calculate mid = (best_bid + best_ask) / 2
                mid_series = (df["best_bid"] + df["best_ask"]) / 2
                logger.info(f"[LLV2:mid] Calculated mid price for {venue}")
            elif "last_trade_px" in df.columns:
                # Fallback to last trade price
                mid_series = df["last_trade_px"]
                logger.warning(f"[LLV2:mid] Using last_trade_px as mid for {venue}")
            else:
                logger.warning(f"[LLV2:skip] No price data for {venue}")
                continue

            # Resample to target frequency
            resampled = mid_series.resample(freq).last().dropna()
            if len(resampled) < 10:
                logger.warning(
                    f"[LLV2:skip] Insufficient data for {venue}: " f"{len(resampled)} points"
                )
                continue

            aligned_data[venue] = resampled

        if len(aligned_data) < 2:
            logger.error("[LLV2:skip] Less than 2 venues with sufficient data")
            return pd.DataFrame()

        # Create aligned panel
        panel = pd.DataFrame(aligned_data)
        panel = panel.dropna()

        if len(panel) < self.min_obs:
            logger.warning(
                f"[LLV2:skip] Insufficient aligned data: " f"{len(panel)} < {self.min_obs}"
            )
            return pd.DataFrame()

        # Compute log-returns
        returns = panel.pct_change().dropna()
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

        logger.info(
            f"[LLV2:prep] Prepared panel: {len(returns)} observations, "
            f"{len(returns.columns)} venues"
        )
        return returns

    def cross_correlation_estimator(
        self, returns1: pd.Series, returns2: pd.Series, horizons: List[int]
    ) -> Dict:
        """
        Cross-correlation estimator for lead-lag analysis.

        Args:
            returns1: First venue's returns
            returns2: Second venue's returns
            horizons: List of horizons to test

        Returns:
            Dictionary with results for each horizon
        """
        results = {}

        for horizon in horizons:
            # Calculate cross-correlation for this horizon
            max_lag = horizon

            # Align series
            common_index = returns1.index.intersection(returns2.index)
            r1 = returns1.loc[common_index]
            r2 = returns2.loc[common_index]

            if len(r1) < max_lag * 2:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Calculate cross-correlation
            correlations = []
            lags = []

            for lag in range(-max_lag, max_lag + 1):
                if lag < 0:
                    # r1 leads r2
                    r1_shifted = r1.shift(lag)
                    r2_aligned = r2

                    # Align on common index
                    common_idx = r1_shifted.index.intersection(r2_aligned.index)
                    r1_aligned = r1_shifted.loc[common_idx]
                    r2_aligned = r2_aligned.loc[common_idx]
                else:
                    # r2 leads r1
                    r1_aligned = r1
                    r2_shifted = r2.shift(-lag)

                    # Align on common index
                    common_idx = r1_aligned.index.intersection(r2_shifted.index)
                    r1_aligned = r1_aligned.loc[common_idx]
                    r2_aligned = r2_shifted.loc[common_idx]

                # Calculate correlation on aligned data
                if len(r1_aligned) > 10 and len(r2_aligned) > 10:
                    # Drop NaN values
                    valid_mask = r1_aligned.notna() & r2_aligned.notna()
                    if valid_mask.sum() > 10:
                        r1_valid = r1_aligned[valid_mask]
                        r2_valid = r2_aligned[valid_mask]
                        corr = r1_valid.corr(r2_valid)
                        if not pd.isna(corr):
                            correlations.append(corr)
                            lags.append(lag)

            if not correlations:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Find peak correlation
            max_corr_idx = np.argmax(np.abs(correlations))
            peak_correlation = correlations[max_corr_idx]
            peak_lag = lags[max_corr_idx]

            # Bootstrap significance test
            p_value = self._bootstrap_significance(r1, r2, peak_correlation, peak_lag)

            results[f"{horizon}s"] = {
                "score": peak_correlation,
                "lag": peak_lag,
                "p": p_value,
            }

        return results

    def lagged_regression_estimator(
        self, returns1: pd.Series, returns2: pd.Series, horizons: List[int]
    ) -> Dict:
        """
        Lagged regression estimator with HAC standard errors.

        Args:
            returns1: First venue's returns
            returns2: Second venue's returns
            horizons: List of horizons to test

        Returns:
            Dictionary with results for each horizon
        """
        results = {}

        for horizon in horizons:
            # Align series
            common_index = returns1.index.intersection(returns2.index)
            r1 = returns1.loc[common_index]
            r2 = returns2.loc[common_index]

            if len(r1) < horizon * 2:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Create lagged features
            X = []
            y = []

            for lag in range(1, horizon + 1):
                r2_lagged = r2.shift(lag)

                # Align on common index
                common_idx = r1.index.intersection(r2_lagged.index)
                r1_aligned = r1.loc[common_idx]
                r2_aligned = r2_lagged.loc[common_idx]

                # Drop NaN values
                valid_mask = r1_aligned.notna() & r2_aligned.notna()

                if valid_mask.sum() > 10:
                    X.append(r2_aligned[valid_mask].values)
                    y.append(r1_aligned[valid_mask].values)

            if not X:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Find common length for all arrays
            min_length = min(len(arr) for arr in X + y)
            if min_length < 10:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Truncate all arrays to common length
            X_truncated = [arr[:min_length] for arr in X]
            y_truncated = y[0][:min_length]  # Use first valid y

            # Stack features
            X = np.column_stack(X_truncated)

            if len(X) < 10:
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}
                continue

            # Fit regression with HAC standard errors
            try:
                model = OLS(y_truncated, X).fit(
                    cov_type="HAC", cov_kwds={"maxlags": self.block_size}
                )

                # Find best lag by |t-statistic|
                t_stats = model.tvalues
                best_lag_idx = np.argmax(np.abs(t_stats))
                best_coef = model.params[best_lag_idx]
                best_p_value = model.pvalues[best_lag_idx]

                results[f"{horizon}s"] = {
                    "score": best_coef,
                    "lag": best_lag_idx + 1,
                    "p": best_p_value,
                }

            except Exception as e:
                logger.warning(f"[LLV2:lagreg] Regression failed: {e}")
                results[f"{horizon}s"] = {"score": 0.0, "lag": 0, "p": 1.0}

        return results

    def _bootstrap_significance(
        self, r1: pd.Series, r2: pd.Series, observed_corr: float, observed_lag: int
    ) -> float:
        """
        Calculate bootstrap significance for cross-correlation.

        Args:
            r1: First returns series
            r2: Second returns series
            observed_corr: Observed correlation
            observed_lag: Observed lag

        Returns:
            P-value from bootstrap
        """
        # Circular block bootstrap
        n_blocks = len(r1) // self.block_size
        if n_blocks < 2:
            return 1.0

        bootstrap_corrs = []

        for _ in range(self.bootstrap_reps):
            # Sample blocks with replacement
            block_indices = np.random.choice(n_blocks, n_blocks, replace=True)

            # Reconstruct series
            r1_boot = []
            r2_boot = []

            for block_idx in block_indices:
                start_idx = block_idx * self.block_size
                end_idx = min(start_idx + self.block_size, len(r1))

                r1_boot.extend(r1.iloc[start_idx:end_idx].values)
                r2_boot.extend(r2.iloc[start_idx:end_idx].values)

            if len(r1_boot) < 10:
                continue

            # Calculate correlation at observed lag
            r1_boot = pd.Series(r1_boot)
            r2_boot = pd.Series(r2_boot)

            if observed_lag < 0:
                r1_shifted = r1_boot.shift(observed_lag)
                r2_aligned = r2_boot

                # Align on common index
                common_idx = r1_shifted.index.intersection(r2_aligned.index)
                r1_aligned = r1_shifted.loc[common_idx]
                r2_aligned = r2_aligned.loc[common_idx]
            else:
                r1_aligned = r1_boot
                r2_shifted = r2_boot.shift(-observed_lag)

                # Align on common index
                common_idx = r1_aligned.index.intersection(r2_shifted.index)
                r1_aligned = r1_aligned.loc[common_idx]
                r2_aligned = r2_shifted.loc[common_idx]

            # Calculate correlation on aligned data
            if len(r1_aligned) > 5 and len(r2_aligned) > 5:
                # Drop NaN values
                valid_mask = r1_aligned.notna() & r2_aligned.notna()
                if valid_mask.sum() > 5:
                    r1_valid = r1_aligned[valid_mask]
                    r2_valid = r2_aligned[valid_mask]
                    corr = r1_valid.corr(r2_valid)
                    if not pd.isna(corr):
                        bootstrap_corrs.append(corr)

        if not bootstrap_corrs:
            return 1.0

        # Calculate p-value
        bootstrap_corrs = np.array(bootstrap_corrs)
        p_value = np.mean(np.abs(bootstrap_corrs) >= np.abs(observed_corr))

        return p_value

    def analyze_pair(
        self,
        returns1: pd.Series,
        returns2: pd.Series,
        horizons: List[int],
        methods: List[str],
    ) -> Dict:
        """
        Analyze lead-lag relationship between two venues.

        Args:
            returns1: First venue's returns
            returns2: Second venue's returns
            horizons: List of horizons to test
            methods: List of methods to use

        Returns:
            Dictionary with analysis results
        """
        results = {}

        for method in methods:
            if method == "xcorr":
                method_results = self.cross_correlation_estimator(returns1, returns2, horizons)
            elif method == "lagreg":
                method_results = self.lagged_regression_estimator(returns1, returns2, horizons)
            else:
                logger.warning(f"[LLV2:skip] Unknown method: {method}")
                continue

            results[method] = method_results

        return results

    def run_analysis(
        self,
        data: Dict[str, pd.DataFrame],
        pairs: List[Tuple[str, str]],
        horizons: List[int],
        methods: List[str],
        freq: str = "1S",
    ) -> Dict:
        """
        Run lead-lag analysis on specified pairs.

        Args:
            data: Dictionary of venue dataframes
            pairs: List of (venue1, venue2) pairs to analyze
            horizons: List of horizons to test
            methods: List of methods to use
            freq: Resampling frequency

        Returns:
            Dictionary with analysis results
        """
        logger.info("[LLV2:start] Starting lead-lag v2 analysis")
        logger.info(f"[LLV2:config] Pairs: {pairs}, Horizons: {horizons}, " f"Methods: {methods}")

        # Prepare data
        returns_panel = self.prepare_data(data, freq)
        if returns_panel.empty:
            logger.error("[LLV2:skip] No valid data for analysis")
            return {}

        # Analyze each pair
        results = {
            "analysis": "lead_lag_v2",
            "window": {
                "start": returns_panel.index[0].isoformat(),
                "end": returns_panel.index[-1].isoformat(),
                "freq": freq,
            },
            "horizons": horizons,
            "methods": methods,
            "edges": [],
        }

        for venue1, venue2 in pairs:
            if venue1 not in returns_panel.columns or venue2 not in returns_panel.columns:
                logger.warning(f"[LLV2:skip] Missing data for {venue1}-{venue2}")
                continue

            logger.info(f"[LLV2:pair] Analyzing {venue1} -> {venue2}")

            # Analyze pair
            pair_results = self.analyze_pair(
                returns_panel[venue1], returns_panel[venue2], horizons, methods
            )

            # Find best result across methods and horizons
            best_score = 0.0
            best_lag = 0
            best_p = 1.0

            for method, method_results in pair_results.items():
                for horizon_str, horizon_results in method_results.items():
                    score = abs(horizon_results["score"])
                    if score > best_score:
                        best_score = score
                        best_lag = horizon_results["lag"]
                        best_p = horizon_results["p"]

            # Create edge
            edge = {
                "from": venue1,
                "to": venue2,
                "best_lag_s": best_lag,
                "score": best_score,
                "p": best_p,
                "per_horizon": {},
                "status": "real",
            }

            # Add per-horizon results
            for method, method_results in pair_results.items():
                for horizon_str, horizon_results in method_results.items():
                    edge["per_horizon"][f"{method}_{horizon_str}"] = {
                        "score": horizon_results["score"],
                        "lag": horizon_results["lag"],
                        "p": horizon_results["p"],
                    }

            results["edges"].append(edge)
            logger.info(
                f"[LLV2:result] {venue1}->{venue2}: score={best_score:.3f}, "
                f"lag={best_lag}, p={best_p:.3f}"
            )

        logger.info(f"[LLV2:complete] Analysis complete: {len(results['edges'])} edges")
        return results
