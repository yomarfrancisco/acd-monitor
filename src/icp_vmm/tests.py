#!/usr/bin/env python3
"""
Precondition Tests for ICP-VMM Analysis

Validates data quality and stationarity requirements.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats  # noqa: F401
from statsmodels.tsa.stattools import adfuller, kpss

logger = logging.getLogger(__name__)


class PreconditionTester:
    """Validates data quality and stationarity for ICP-VMM analysis."""

    def __init__(self, min_coverage: float = 0.95, min_venues: int = 3):
        self.min_coverage = min_coverage
        self.min_venues = min_venues

    def test_coverage(self, venue_data: Dict[str, pd.DataFrame]) -> Tuple[bool, Dict[str, float]]:
        """
        Test data coverage per venue.

        Args:
            venue_data: Dict of venue DataFrames

        Returns:
            Tuple of (passes, coverage_rates)
        """
        coverage_rates = {}
        passes = True

        for venue, data in venue_data.items():
            if len(data) == 0:
                coverage_rates[venue] = 0.0
                passes = False
                continue

            # Calculate coverage as non-null percentage
            coverage = data.notna().mean().mean()
            coverage_rates[venue] = coverage

            if coverage < self.min_coverage:
                passes = False
                logger.warning(f"Venue {venue}: coverage {coverage:.3f} < {self.min_coverage}")

        return passes, coverage_rates

    def test_venue_count(self, venue_data: Dict[str, pd.DataFrame]) -> Tuple[bool, int]:
        """
        Test minimum venue count.

        Args:
            venue_data: Dict of venue DataFrames

        Returns:
            Tuple of (passes, venue_count)
        """
        venue_count = len([v for v in venue_data.values() if len(v) > 0])
        passes = venue_count >= self.min_venues

        if not passes:
            logger.warning(f"Insufficient venues: {venue_count} < {self.min_venues}")

        return passes, venue_count

    def test_stationarity(self, returns: pd.Series, test_type: str = "adf") -> Tuple[bool, Dict]:
        """
        Test stationarity of returns series.

        Args:
            returns: Returns series
            test_type: 'adf' or 'kpss'

        Returns:
            Tuple of (is_stationary, test_results)
        """
        if len(returns) < 10:
            return False, {"error": "insufficient_data"}

        try:
            if test_type == "adf":
                # Augmented Dickey-Fuller test
                (
                    adf_stat,
                    adf_pvalue,
                    adf_usedlag,
                    adf_nobs,
                    adf_critical,
                    adf_icbest,
                ) = adfuller(returns.dropna())

                is_stationary = adf_pvalue < 0.05
                test_results = {
                    "test": "adf",
                    "statistic": adf_stat,
                    "pvalue": adf_pvalue,
                    "critical_values": adf_critical,
                    "is_stationary": is_stationary,
                }

            elif test_type == "kpss":
                # KPSS test
                kpss_stat, kpss_pvalue, kpss_lags, kpss_critical = kpss(returns.dropna())

                is_stationary = kpss_pvalue > 0.05
                test_results = {
                    "test": "kpss",
                    "statistic": kpss_stat,
                    "pvalue": kpss_pvalue,
                    "critical_values": kpss_critical,
                    "is_stationary": is_stationary,
                }
            else:
                raise ValueError(f"Unknown test type: {test_type}")

        except Exception as e:
            logger.warning(f"Stationarity test failed: {e}")
            return False, {"error": str(e)}

        return is_stationary, test_results

    def test_clock_skew(self, venue_data: Dict[str, pd.DataFrame]) -> Tuple[bool, Dict[str, float]]:
        """
        Test clock skew between venues.

        Args:
            venue_data: Dict of venue DataFrames

        Returns:
            Tuple of (passes, skew_measures)
        """
        skew_measures = {}
        passes = True

        if len(venue_data) < 2:
            return True, skew_measures

        # Get timestamps for each venue
        venue_timestamps = {}
        for venue, data in venue_data.items():
            if "ts_exchange" in data.columns and len(data) > 0:
                venue_timestamps[venue] = data["ts_exchange"]

        if len(venue_timestamps) < 2:
            return True, skew_measures

        # Calculate pairwise skew
        venues = list(venue_timestamps.keys())
        for i, venue1 in enumerate(venues):
            for venue2 in venues[i + 1 :]:
                ts1 = venue_timestamps[venue1]
                ts2 = venue_timestamps[venue2]

                # Find common time range
                min_ts = max(ts1.min(), ts2.min())
                max_ts = min(ts1.max(), ts2.max())

                if min_ts >= max_ts:
                    skew_measures[f"{venue1}_{venue2}"] = float("inf")
                    passes = False
                    continue

                # Calculate median time difference
                ts1_filtered = ts1[(ts1 >= min_ts) & (ts1 <= max_ts)]
                ts2_filtered = ts2[(ts2 >= min_ts) & (ts2 <= max_ts)]

                if len(ts1_filtered) == 0 or len(ts2_filtered) == 0:
                    skew_measures[f"{venue1}_{venue2}"] = float("inf")
                    passes = False
                    continue

                # Calculate skew as median absolute difference
                time_diff = np.abs(ts1_filtered.median() - ts2_filtered.median())
                skew_measures[f"{venue1}_{venue2}"] = time_diff.total_seconds()

                # Check if skew is too large (e.g., > 1 minute)
                if time_diff.total_seconds() > 60:
                    passes = False

        return passes, skew_measures

    def test_environment_balance(
        self, env_counts: Dict[str, Dict[str, int]], min_obs_per_env: int = 5
    ) -> Tuple[bool, List[str]]:
        """
        Test environment balance for sufficient observations.

        Args:
            env_counts: Environment counts dict
            min_obs_per_env: Minimum observations per environment

        Returns:
            Tuple of (passes, warnings)
        """
        warnings = []
        passes = True

        for env_type, env_counts_dict in env_counts.items():
            total_obs = sum(env_counts_dict.values())
            min_obs = min(env_counts_dict.values()) if env_counts_dict else 0

            if total_obs < min_obs_per_env * 2:
                warnings.append(f"{env_type}: insufficient total observations ({total_obs})")
                passes = False
            elif min_obs < min_obs_per_env:
                warnings.append(f"{env_type}: some bins have < {min_obs_per_env} obs")
                passes = False

        return passes, warnings

    def run_all_tests(
        self, venue_data: Dict[str, pd.DataFrame], env_counts: Dict[str, Dict[str, int]]
    ) -> Dict:
        """
        Run all precondition tests.

        Args:
            venue_data: Dict of venue DataFrames
            env_counts: Environment counts dict

        Returns:
            Test results dict
        """
        results = {
            "coverage": {"passes": False, "rates": {}},
            "venue_count": {"passes": False, "count": 0},
            "stationarity": {"passes": False, "results": {}},
            "clock_skew": {"passes": False, "measures": {}},
            "environment_balance": {"passes": False, "warnings": []},
            "overall": {"passes": False, "status": "INSUFFICIENT"},
        }

        # Test coverage
        coverage_passes, coverage_rates = self.test_coverage(venue_data)
        results["coverage"] = {"passes": coverage_passes, "rates": coverage_rates}

        # Test venue count
        venue_count_passes, venue_count = self.test_venue_count(venue_data)
        results["venue_count"] = {"passes": venue_count_passes, "count": venue_count}

        # Test stationarity for each venue
        stationarity_passes = True
        stationarity_results = {}

        for venue, data in venue_data.items():
            if "last_px" in data.columns and len(data) > 1:
                # Construct returns
                returns = data["last_px"].pct_change().dropna()
                if len(returns) > 10:
                    is_stationary, test_results = self.test_stationarity(returns)
                    stationarity_results[venue] = test_results
                    if not is_stationary:
                        stationarity_passes = False

        results["stationarity"] = {
            "passes": stationarity_passes,
            "results": stationarity_results,
        }

        # Test clock skew
        clock_skew_passes, skew_measures = self.test_clock_skew(venue_data)
        results["clock_skew"] = {"passes": clock_skew_passes, "measures": skew_measures}

        # Test environment balance
        env_balance_passes, env_warnings = self.test_environment_balance(env_counts)
        results["environment_balance"] = {
            "passes": env_balance_passes,
            "warnings": env_warnings,
        }

        # Overall assessment
        overall_passes = (
            coverage_passes
            and venue_count_passes
            and stationarity_passes
            and clock_skew_passes
            and env_balance_passes
        )

        results["overall"] = {
            "passes": overall_passes,
            "status": "SUFFICIENT" if overall_passes else "INSUFFICIENT",
        }

        return results
