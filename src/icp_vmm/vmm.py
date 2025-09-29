#!/usr/bin/env python3
"""
Variance-Movement Mapping (VMM) Core

Implements Johansen cointegration, VECM, and information share analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from statsmodels.tsa.vector_ar.var_model import VAR

# from statsmodels.tsa.vector_ar.impulse_response import irf  # noqa: F401
import logging

logger = logging.getLogger(__name__)


class VMMAnalyzer:
    """Variance-Movement Mapping analyzer for cointegration and information shares."""

    def __init__(self, max_lags: int = 5, significance_level: float = 0.05):
        self.max_lags = max_lags
        self.significance_level = significance_level

    def test_cointegration(self, price_data: pd.DataFrame) -> Dict:
        """
        Test for cointegration using Johansen test.

        Args:
            price_data: DataFrame with price series for each venue

        Returns:
            Cointegration test results
        """
        try:
            # Prepare data for Johansen test
            if len(price_data) < 10:
                return {"cointegrated": False, "error": "insufficient_data"}

            # Run Johansen test
            johansen_result = coint_johansen(price_data.values, det_order=0, k_ar_diff=1)

            # Extract results
            trace_stats = johansen_result.lr1
            trace_critical = johansen_result.cvt
            eigen_stats = johansen_result.lr2
            eigen_critical = johansen_result.cve

            # Determine cointegration rank
            cointegrated = False
            rank = 0

            for i, (trace_stat, trace_crit) in enumerate(zip(trace_stats, trace_critical[:, 0])):
                if trace_stat > trace_crit:
                    rank = i + 1
                    cointegrated = True
                else:
                    break

            results = {
                "cointegrated": cointegrated,
                "rank": rank,
                "trace_stats": trace_stats.tolist(),
                "trace_critical": trace_critical.tolist(),
                "eigen_stats": eigen_stats.tolist(),
                "eigen_critical": eigen_critical.tolist(),
                "venues": price_data.columns.tolist(),
            }

        except Exception as e:
            logger.warning(f"Cointegration test failed: {e}")
            results = {"cointegrated": False, "error": str(e)}

        return results

    def estimate_vecm(self, price_data: pd.DataFrame, rank: int) -> Dict:
        """
        Estimate VECM model.

        Args:
            price_data: DataFrame with price series
            rank: Cointegration rank

        Returns:
            VECM estimation results
        """
        try:
            if rank == 0:
                return {"error": "no_cointegration", "mode": "VAR_FEVD"}

            # Estimate VECM
            vecm = VECM(price_data, k_ar_diff=1, coint_rank=rank)
            vecm_result = vecm.fit()

            # Extract coefficients
            alpha = vecm_result.alpha
            beta = vecm_result.beta
            gamma = vecm_result.gamma

            results = {
                "alpha": alpha.tolist(),
                "beta": beta.tolist(),
                "gamma": gamma.tolist(),
                "venues": price_data.columns.tolist(),
                "mode": "VECM",
            }

        except Exception as e:
            logger.warning(f"VECM estimation failed: {e}")
            results = {"error": str(e), "mode": "VAR_FEVD"}

        return results

    def estimate_var_fevd(self, returns_data: pd.DataFrame) -> Dict:
        """
        Estimate VAR model and FEVD as fallback.

        Args:
            returns_data: DataFrame with returns series

        Returns:
            VAR FEVD results
        """
        try:
            if len(returns_data) < 10:
                return {"error": "insufficient_data", "mode": "VAR_FEVD"}

            # Estimate VAR
            var_model = VAR(returns_data)
            var_result = var_model.fit(maxlags=self.max_lags, ic="aic")

            # Calculate FEVD
            fevd = var_result.fevd(periods=10)
            fevd_table = fevd.summary()

            # Extract information shares (diagonal of FEVD)
            info_shares = {}
            for i, venue in enumerate(returns_data.columns):
                info_shares[venue] = float(fevd_table.iloc[i, i])

            results = {
                "info_shares": info_shares,
                "fevd_table": fevd_table.values.tolist(),
                "venues": returns_data.columns.tolist(),
                "mode": "VAR_FEVD",
            }

        except Exception as e:
            logger.warning(f"VAR FEVD estimation failed: {e}")
            results = {"error": str(e), "mode": "VAR_FEVD"}

        return results

    def calculate_hasbrouck_bounds(
        self, price_data: pd.DataFrame, vecm_result: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate Hasbrouck information share bounds.

        Args:
            price_data: DataFrame with price series
            vecm_result: VECM results (if available)

        Returns:
            Information share bounds
        """
        try:
            if vecm_result and "error" not in vecm_result:
                # Use VECM results for bounds calculation
                alpha = np.array(vecm_result["alpha"])  # noqa: F841
                beta = np.array(vecm_result["beta"])  # noqa: F841

                # Calculate information share bounds
                # This is a simplified implementation
                venues = vecm_result["venues"]
                n_venues = len(venues)

                # For now, return equal shares as placeholder
                # Full implementation would use the VECM parameters
                info_shares = {venue: 1.0 / n_venues for venue in venues}
                bounds = {venue: [0.0, 1.0] for venue in venues}

            else:
                # Fallback to simple variance-based shares
                price_vars = price_data.var()
                total_var = price_vars.sum()
                info_shares = (price_vars / total_var).to_dict()
                bounds = {venue: [0.0, 1.0] for venue in price_data.columns}

            results = {
                "info_shares": info_shares,
                "bounds": bounds,
                "venues": list(info_shares.keys()),
            }

        except Exception as e:
            logger.warning(f"Hasbrouck bounds calculation failed: {e}")
            results = {"error": str(e)}

        return results

    def analyze_vmm(self, venue_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Perform complete VMM analysis.

        Args:
            venue_data: Dict of venue DataFrames with price data

        Returns:
            VMM analysis results
        """
        results = {
            "mode": "INSUFFICIENT",
            "cointegration": {},
            "vecm": {},
            "var_fevd": {},
            "info_shares": {},
            "venues": list(venue_data.keys()),
        }

        try:
            # Prepare price data
            price_data = pd.DataFrame()
            returns_data = pd.DataFrame()

            for venue, data in venue_data.items():
                if "last_px" in data.columns and len(data) > 1:
                    price_data[venue] = data["last_px"]
                    returns_data[venue] = data["last_px"].pct_change().dropna()

            if len(price_data) < 10 or len(price_data.columns) < 2:
                results["error"] = "insufficient_data"
                return results

            # Test cointegration
            coint_results = self.test_cointegration(price_data)
            results["cointegration"] = coint_results

            if coint_results.get("cointegrated", False):
                # Estimate VECM
                rank = coint_results.get("rank", 0)
                vecm_results = self.estimate_vecm(price_data, rank)
                results["vecm"] = vecm_results

                if "error" not in vecm_results:
                    # Calculate Hasbrouck bounds
                    info_share_results = self.calculate_hasbrouck_bounds(price_data, vecm_results)
                    results["info_shares"] = info_share_results
                    results["mode"] = "VECM"
                else:
                    # Fallback to VAR FEVD
                    var_fevd_results = self.estimate_var_fevd(returns_data)
                    results["var_fevd"] = var_fevd_results
                    results["mode"] = "VAR_FEVD"
            else:
                # No cointegration, use VAR FEVD
                var_fevd_results = self.estimate_var_fevd(returns_data)
                results["var_fevd"] = var_fevd_results
                results["mode"] = "VAR_FEVD"

        except Exception as e:
            logger.error(f"VMM analysis failed: {e}")
            results["error"] = str(e)
            results["mode"] = "ERROR"

        return results
