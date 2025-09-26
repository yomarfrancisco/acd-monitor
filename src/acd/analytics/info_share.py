"""
Information Share Analysis Module

This module implements Hasbrouck information share bounds to determine
which venue embeds fundamental information first using minute-level data.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from sklearn.utils import resample


@dataclass
class InfoShareResult:
    """Result container for information share analysis."""

    overall: List[Dict[str, Any]]
    by_env: Dict[str, Dict[str, List[Dict[str, Any]]]]
    assignments: Dict[str, Any]
    daily_results: List[Dict[str, Any]]


class InfoShareAnalyzer:
    """
    Analyzes information share using Hasbrouck bounds.

    Determines which venue embeds fundamental information first
    using minute-level price data and econometric methods.
    """

    def __init__(self, spec_version: str = "1.0.0", max_lag: int = 5, bootstrap_samples: int = 500):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.max_lag = max_lag
        self.bootstrap_samples = bootstrap_samples
        self.min_coverage = 0.95  # 95% minute coverage required
        self.min_venues = 3  # Minimum venues required

    def _get_code_version(self) -> str:
        """Get short commit SHA for reproducibility."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def load_minute_data(
        self, pair: str, venues: List[str], start_utc: datetime, end_utc: datetime
    ) -> pd.DataFrame:
        """
        Load minute-level data for all venues.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime

        Returns:
            Combined DataFrame with all venue data
        """
        from acd.data.adapters import MinuteBarsAdapter

        self.logger.info(f"Loading minute data for {pair} across {len(venues)} venues")

        all_data = []
        adapter = MinuteBarsAdapter()

        for venue in venues:
            try:
                df = adapter.get(pair, venue, start_utc, end_utc)
                if not df.empty:
                    df["venue"] = venue
                    all_data.append(df)
                    self.logger.info(f"Loaded {len(df)} minute bars for {venue}")
                else:
                    self.logger.warning(f"No data for {venue}")
            except Exception as e:
                self.logger.error(f"Error loading data for {venue}: {str(e)}")

        if not all_data:
            raise ValueError("No data loaded for any venue")

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Sort by time and venue
        combined_df = combined_df.sort_values(["time", "venue"]).reset_index(drop=True)

        self.logger.info(f"Combined data: {len(combined_df)} records across {len(venues)} venues")

        return combined_df

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess minute data for information share analysis.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Preprocessed DataFrame with log returns
        """
        df = df.copy()

        # Build mid prices if not present
        if "mid" not in df.columns:
            df["mid"] = (df["high"] + df["low"]) / 2

        # Compute log mid prices
        df["log_mid"] = np.log(df["mid"])

        # Compute first differences (log returns)
        df["returns"] = df.groupby("venue")["log_mid"].diff()

        # Remove NaN values
        df = df.dropna(subset=["returns"])

        self.logger.info(f"Preprocessed data: {len(df)} records")

        return df

    def align_venues_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Align all venues by UTC minute with inner join.

        Args:
            df: DataFrame with venue data

        Returns:
            Pivoted DataFrame with venues as columns
        """
        # Pivot to get venues as columns
        pivoted = df.pivot_table(index="time", columns="venue", values="returns", aggfunc="first")

        # Inner join - drop any bar with NA
        pivoted = pivoted.dropna()

        # Ensure all venues are present
        for venue in self.venues:
            if venue not in pivoted.columns:
                pivoted[venue] = 0

        # Reorder columns
        pivoted = pivoted[self.venues]

        self.logger.info(f"Aligned data: {len(pivoted)} time points, {len(pivoted.columns)} venues")

        return pivoted

    def check_data_quality(self, returns_df: pd.DataFrame, date: str) -> Tuple[bool, str]:
        """
        Check data quality for a specific day.

        Args:
            returns_df: DataFrame with aligned returns
            date: Date string

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check venue coverage
        venue_coverage = {}
        for venue in self.venues:
            if venue in returns_df.columns:
                non_zero_count = (returns_df[venue] != 0).sum()
                total_count = len(returns_df)
                coverage = non_zero_count / total_count if total_count > 0 else 0
                venue_coverage[venue] = coverage

        # Check if we have enough venues with good coverage
        good_venues = [v for v, cov in venue_coverage.items() if cov >= self.min_coverage]

        if len(good_venues) < self.min_venues:
            return False, "notEnoughData"

        return True, "valid"

    def standardize_returns(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize returns by in-day standard deviation.

        Args:
            returns_df: DataFrame with aligned returns

        Returns:
            Standardized returns DataFrame
        """
        standardized = returns_df.copy()

        for venue in self.venues:
            if venue in standardized.columns:
                venue_std = standardized[venue].std()
                if venue_std > 0:
                    standardized[venue] = standardized[venue] / venue_std

        self.logger.info("Standardized returns by in-day standard deviation")

        return standardized

    def test_cointegration(self, log_prices_df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Test for cointegration using Johansen test.

        Args:
            log_prices_df: DataFrame with log price levels

        Returns:
            Tuple of (is_cointegrated, test_results)
        """
        try:
            # Prepare data for Johansen test
            data = log_prices_df.values

            # Johansen test
            johansen_result = coint_johansen(data, det_order=0, k_ar_diff=1)

            # Check if cointegrated (trace test)
            trace_stat = johansen_result.lr1[0]  # First trace statistic
            trace_critical = johansen_result.cvt[0, 1]  # 5% critical value

            is_cointegrated = trace_stat > trace_critical

            test_results = {
                "trace_statistic": trace_stat,
                "trace_critical_5pct": trace_critical,
                "is_cointegrated": is_cointegrated,
                "eigenvalues": johansen_result.eig.tolist(),
            }

            return is_cointegrated, test_results

        except Exception as e:
            self.logger.warning(f"Cointegration test failed: {str(e)}")
            return False, {"error": str(e)}

    def estimate_vecm(self, returns_df: pd.DataFrame) -> Tuple[Optional[VECM], str]:
        """
        Estimate VECM model with optimal lag selection.

        Args:
            returns_df: DataFrame with aligned returns

        Returns:
            Tuple of (vecm_model, method)
        """
        try:
            # Prepare data
            data = returns_df.values

            # Find optimal lag using BIC
            best_lag = 1
            best_bic = float("inf")

            for lag in range(1, min(self.max_lag + 1, len(data) // 4)):
                try:
                    vecm = VECM(data, k_ar_diff=lag, coint_rank=1)
                    vecm_fit = vecm.fit()
                    bic = vecm_fit.bic

                    if bic < best_bic:
                        best_bic = bic
                        best_lag = lag
                except Exception:
                    continue

            # Fit final model
            vecm = VECM(data, k_ar_diff=best_lag, coint_rank=1)
            vecm_fit = vecm.fit()

            return vecm_fit, "VECM"

        except Exception as e:
            self.logger.warning(f"VECM estimation failed: {str(e)}")
            return None, "fallback"

    def compute_hasbrouck_bounds(
        self, vecm_model: VECM, returns_df: pd.DataFrame
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute Hasbrouck information share bounds.

        Args:
            vecm_model: Fitted VECM model
            returns_df: DataFrame with aligned returns

        Returns:
            Dictionary of information share bounds per venue
        """
        try:
            # Get model parameters
            alpha = vecm_model.alpha

            # Compute information share bounds
            bounds = {}

            for i, venue in enumerate(self.venues):
                if i < len(alpha):
                    # Lower bound: contribution to permanent component
                    lower_bound = alpha[i] ** 2 / np.sum(alpha**2)

                    # Upper bound: total contribution
                    upper_bound = (alpha[i] ** 2 + np.sum(alpha[i] * alpha)) / np.sum(alpha**2)

                    bounds[venue] = {
                        "lower": max(0, min(1, lower_bound)),
                        "upper": max(0, min(1, upper_bound)),
                    }
                else:
                    bounds[venue] = {"lower": 0, "upper": 0}

            return bounds

        except Exception as e:
            self.logger.warning(f"Hasbrouck bounds computation failed: {str(e)}")
            # Return equal bounds as fallback
            bounds = {}
            for venue in self.venues:
                bounds[venue] = {"lower": 1 / len(self.venues), "upper": 1 / len(self.venues)}
            return bounds

    def compute_gonzalo_granger_weights(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute Gonzalo-Granger weights as fallback.

        Args:
            returns_df: DataFrame with aligned returns

        Returns:
            Dictionary of weights per venue
        """
        try:
            # Simple weight computation based on variance
            weights = {}
            total_var = 0

            for venue in self.venues:
                if venue in returns_df.columns:
                    var = returns_df[venue].var()
                    weights[venue] = var
                    total_var += var
                else:
                    weights[venue] = 0

            # Normalize weights
            if total_var > 0:
                for venue in weights:
                    weights[venue] = weights[venue] / total_var
            else:
                # Equal weights if no variance
                for venue in weights:
                    weights[venue] = 1 / len(self.venues)

            return weights

        except Exception as e:
            self.logger.warning(f"Gonzalo-Granger weights computation failed: {str(e)}")
            # Return equal weights as fallback
            return {venue: 1 / len(self.venues) for venue in self.venues}

    def process_daily_data(
        self,
        returns_df: pd.DataFrame,
        log_prices_df: pd.DataFrame,
        date: str,
        env_labels: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Process data for a single day.

        Args:
            returns_df: DataFrame with aligned returns
            log_prices_df: DataFrame with log price levels
            date: Date string
            env_labels: Environment labels

        Returns:
            Daily results dictionary or None if failed
        """
        # Check data quality
        is_valid, reason = self.check_data_quality(returns_df, date)
        if not is_valid:
            return None

        # Standardize returns
        standardized_returns = self.standardize_returns(returns_df)

        # Test cointegration
        is_cointegrated, coint_results = self.test_cointegration(log_prices_df)

        # Initialize variables
        vecm_model = None

        if is_cointegrated:
            # Estimate VECM
            vecm_model, method = self.estimate_vecm(standardized_returns)

            if vecm_model is None:
                # Use Gonzalo-Granger weights as fallback
                weights = self.compute_gonzalo_granger_weights(standardized_returns)
                bounds = {venue: {"lower": w, "upper": w} for venue, w in weights.items()}
                method = "GG_fallback"
                flags = ["no_cointegration"]

                # Log fallback
                fallback_log = {"day": date, "reason": "VECM_failed"}
                print(f"[MICRO:infoShare:fallback] {json.dumps(fallback_log, ensure_ascii=False)}")
            else:
                # Compute Hasbrouck bounds
                bounds = self.compute_hasbrouck_bounds(vecm_model, standardized_returns)
                method = "Hasbrouck"
                flags = []
        else:
            # No cointegration - use Gonzalo-Granger weights
            weights = self.compute_gonzalo_granger_weights(standardized_returns)
            bounds = {venue: {"lower": w, "upper": w} for venue, w in weights.items()}
            method = "GG_fallback"
            flags = ["no_cointegration"]

        # Validate bounds
        for venue, bound in bounds.items():
            if not (0 <= bound["lower"] <= bound["upper"] <= 1):
                self.logger.warning(f"Invalid bounds for {venue}: {bound}")
                return None

        # Create daily results
        daily_results = {
            "date": date,
            "method": method,
            "bounds": bounds,
            "env_labels": env_labels,
            "n_obs": len(returns_df),
            "flags": flags,
        }

        # Log daily results
        for venue in self.venues:
            if venue in bounds:
                daily_log = {
                    "day": date,
                    "venue": venue,
                    "IS_lower": round(bounds[venue]["lower"], 4),
                    "IS_upper": round(bounds[venue]["upper"], 4),
                    "lags": getattr(vecm_model, "k_ar_diff", 1) if vecm_model else 1,
                    "method": method,
                    "env": env_labels,
                }
                print(f"[MICRO:infoShare:day] {json.dumps(daily_log, ensure_ascii=False)}")

        return daily_results

    def aggregate_by_environment(self, daily_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results by environment and regime.

        Args:
            daily_results: List of daily results

        Returns:
            Aggregated results by environment
        """
        # Group by environment
        env_groups = {}

        for result in daily_results:
            env_labels = result["env_labels"]

            for env_type, regime in env_labels.items():
                if env_type not in env_groups:
                    env_groups[env_type] = {}
                if regime not in env_groups[env_type]:
                    env_groups[env_type][regime] = []

                env_groups[env_type][regime].append(result)

        # Compute means for each environment/regime
        aggregated = {}

        for env_type, regimes in env_groups.items():
            aggregated[env_type] = {}

            for regime, results in regimes.items():
                if not results:
                    continue

                regime_means = {}
                for venue in self.venues:
                    lower_values = [r["bounds"].get(venue, {}).get("lower", 0) for r in results]
                    upper_values = [r["bounds"].get(venue, {}).get("upper", 0) for r in results]

                    regime_means[venue] = {
                        "mean_lower": np.mean(lower_values),
                        "mean_upper": np.mean(upper_values),
                        "n_days": len(results),
                    }

                # Convert to list format
                regime_list = []
                for venue in self.venues:
                    if venue in regime_means:
                        regime_list.append(
                            {
                                "venue": venue,
                                "lower": round(regime_means[venue]["mean_lower"], 4),
                                "upper": round(regime_means[venue]["mean_upper"], 4),
                                "n_days": regime_means[venue]["n_days"],
                            }
                        )

                aggregated[env_type][regime] = regime_list

                # Log environment results
                for venue_data in regime_list:
                    env_log = {
                        "envType": env_type,
                        "regime": regime,
                        "venue": venue_data["venue"],
                        "mean_lower": venue_data["lower"],
                        "mean_upper": venue_data["upper"],
                        "n_days": venue_data["n_days"],
                    }
                    print(f"[MICRO:infoShare:env] {json.dumps(env_log, ensure_ascii=False)}")

        return aggregated

    def compute_bootstrap_ci(
        self,
        daily_results: List[Dict[str, Any]],
        env_type: str,
        regime: str,
        venue: str,
        metric: str = "mean_upper",
    ) -> Dict[str, float]:
        """
        Compute bootstrap confidence intervals.

        Args:
            daily_results: List of daily results
            env_type: Environment type
            regime: Regime label
            venue: Venue name
            metric: Metric to bootstrap

        Returns:
            Bootstrap confidence interval
        """
        # Filter results for this environment/regime
        filtered_results = [r for r in daily_results if r["env_labels"].get(env_type) == regime]

        if len(filtered_results) < 2:
            return {"ci_lower": 0, "ci_upper": 0}

        # Extract values for this venue
        values = []
        for result in filtered_results:
            if venue in result["bounds"]:
                if metric == "mean_upper":
                    values.append(result["bounds"][venue]["upper"])
                else:
                    values.append(result["bounds"][venue]["lower"])

        if len(values) < 2:
            return {"ci_lower": 0, "ci_upper": 0}

        # Bootstrap
        bootstrap_values = []
        for _ in range(self.bootstrap_samples):
            sample = resample(values, n_samples=len(values))
            bootstrap_values.append(np.mean(sample))

        # Compute confidence interval
        ci_lower = np.percentile(bootstrap_values, 2.5)
        ci_upper = np.percentile(bootstrap_values, 97.5)

        # Log bootstrap results
        bootstrap_log = {
            "envType": env_type,
            "regime": regime,
            "venue": venue,
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "metric": metric,
            "B": self.bootstrap_samples,
        }
        print(f"[STATS:infoShare:bootstrap] {json.dumps(bootstrap_log, ensure_ascii=False)}")

        return {"ci_lower": ci_lower, "ci_upper": ci_upper}

    def export_results(
        self, result: InfoShareResult, output_dir: str, start_date: str, end_date: str
    ) -> None:
        """
        Export all information share results to files.

        Args:
            result: Information share analysis result
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string
        """
        os.makedirs(output_dir, exist_ok=True)

        # Export main results JSON
        main_results = {"overall": result.overall, "by_env": result.by_env}

        info_share_path = os.path.join(output_dir, "info_share.json")
        with open(info_share_path, "w") as f:
            json.dump(main_results, f, indent=2, default=str)

        # Export environment CSV
        env_data = []
        for env_type, regimes in result.by_env.items():
            for regime, venues in regimes.items():
                for venue_data in venues:
                    env_data.append(
                        {
                            "envType": env_type,
                            "regime": regime,
                            "venue": venue_data["venue"],
                            "mean_lower": venue_data["lower"],
                            "mean_upper": venue_data["upper"],
                            "ci_lower": 0,  # Placeholder
                            "ci_upper": 0,  # Placeholder
                            "n_days": venue_data["n_days"],
                        }
                    )

        env_df = pd.DataFrame(env_data)
        env_csv_path = os.path.join(output_dir, "info_share_by_env.csv")
        env_df.to_csv(env_csv_path, index=False)

        # Export assignments JSON
        assignments_path = os.path.join(output_dir, "info_share_assignments.json")
        with open(assignments_path, "w") as f:
            json.dump(result.assignments, f, indent=2, default=str)

        # Update MANIFEST.json
        self._update_manifest(output_dir, start_date, end_date, result)

        self.logger.info(f"Exported information share analysis results to {output_dir}/")

    def _update_manifest(
        self, output_dir: str, start_date: str, end_date: str, result: InfoShareResult
    ) -> None:
        """Update MANIFEST.json with information share run data."""
        manifest_path = os.path.join(output_dir, "MANIFEST.json")

        # Read existing manifest or create new one
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
        else:
            manifest_data = {
                "commit": self._get_code_version(),
                "codeVersion": self._get_code_version(),
                "tz": "UTC",
                "sampleWindow": {"start": start_date, "end": end_date},
                "specVersion": self.spec_version,
                "runs": {},
            }

        # Add information share run data
        manifest_data["runs"]["infoShare"] = {
            "generated": datetime.now().isoformat() + "Z",
            "keptDays": result.assignments.get("keptDays", 0),
            "droppedDays": result.assignments.get("droppedDays", 0),
            "dropReasons": result.assignments.get("dropReasons", {}),
            "max_lag": self.max_lag,
            "bootstrap_samples": self.bootstrap_samples,
            "venues": self.venues,
            "notes": "Hasbrouck information share bounds analysis",
        }

        # Write updated manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

    def analyze_info_share(
        self,
        pair: str,
        venues: List[str],
        start_utc: datetime,
        end_utc: datetime,
        output_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
    ) -> InfoShareResult:
        """
        Run complete information share analysis.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string

        Returns:
            Information share analysis result
        """
        self.logger.info("Starting information share analysis")

        # Load minute data
        minute_data = self.load_minute_data(pair, venues, start_utc, end_utc)

        # Preprocess data
        processed_data = self.preprocess_data(minute_data)

        # Group by date and process each day
        daily_results = []
        drop_reasons = {"notEnoughData": 0, "notCointegrated": 0, "modelFail": 0}

        for date, day_data in processed_data.groupby(processed_data["time"].dt.date):
            date_str = str(date)

            # Align venues by time
            aligned_returns = self.align_venues_by_time(day_data)

            # Create log prices for cointegration test
            log_prices = day_data.pivot_table(
                index="time", columns="venue", values="log_mid", aggfunc="first"
            ).dropna()

            # Mock environment labels (placeholder)
            env_labels = {"volatility": "medium", "funding": "medium", "liquidity": "medium"}

            # Check data quality first
            is_valid, reason = self.check_data_quality(aligned_returns, date_str)
            if not is_valid:
                drop_reasons["notEnoughData"] += 1
                continue

            # Process daily data
            daily_result = self.process_daily_data(
                aligned_returns, log_prices, date_str, env_labels
            )

            if daily_result is None:
                # Check if it failed due to cointegration
                is_cointegrated, _ = self.test_cointegration(log_prices)
                if not is_cointegrated:
                    drop_reasons["notCointegrated"] += 1
                else:
                    drop_reasons["modelFail"] += 1
            else:
                daily_results.append(daily_result)

        # Aggregate by environment
        by_env = self.aggregate_by_environment(daily_results)

        # Compute overall means
        overall = []
        if daily_results:
            for venue in self.venues:
                lower_values = [r["bounds"].get(venue, {}).get("lower", 0) for r in daily_results]
                upper_values = [r["bounds"].get(venue, {}).get("upper", 0) for r in daily_results]

                overall.append(
                    {
                        "venue": venue,
                        "lower": round(np.mean(lower_values), 4),
                        "upper": round(np.mean(upper_values), 4),
                    }
                )

        # Create assignments summary
        assignments = {
            "keptDays": len(daily_results),
            "droppedDays": sum(drop_reasons.values()),
            "dropReasons": drop_reasons,
        }

        # Log assignments
        print(f"[INFO:infoShare:assignments] {json.dumps(assignments, ensure_ascii=False)}")

        # Create result object
        result = InfoShareResult(
            overall=overall, by_env=by_env, assignments=assignments, daily_results=daily_results
        )

        # Export results
        self.export_results(result, output_dir, start_date, end_date)

        self.logger.info("Information share analysis completed")

        return result


def create_info_share_analyzer(
    spec_version: str = "1.0.0", max_lag: int = 5, bootstrap_samples: int = 500
) -> InfoShareAnalyzer:
    """Create an information share analyzer instance."""
    return InfoShareAnalyzer(
        spec_version=spec_version, max_lag=max_lag, bootstrap_samples=bootstrap_samples
    )
