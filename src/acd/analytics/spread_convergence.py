"""
Cross-Venue Spread Compression Analysis Module

This module detects convergence episodes where venues move toward consensus pricing,
which may reflect coordinated algorithmic behavior.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import scipy.stats as stats


@dataclass
class SpreadConvergenceResult:
    """Result container for spread convergence analysis."""

    episodes: pd.DataFrame
    leaders: Dict[str, Any]
    env_breakdown: Dict[str, Any]
    stats_results: Dict[str, Any]


class SpreadConvergenceAnalyzer:
    """
    Analyzes cross-venue spread compression episodes.

    Detects convergence episodes where venues move toward consensus pricing
    and attributes leadership to the first venue to move toward consensus.
    """

    def __init__(self, spec_version: str = "1.0.0"):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.compression_threshold = 0.10  # Bottom 10%
        self.median_threshold = 0.50  # Above median
        self.lookback_window = 10  # seconds
        self.min_duration = 3  # seconds

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

    def load_second_data(
        self, pair: str, venues: List[str], start_utc: datetime, end_utc: datetime
    ) -> pd.DataFrame:
        """
        Load second-level data for all venues.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime

        Returns:
            Combined DataFrame with all venue data
        """
        from acd.data.adapters import SecondBarsAdapter

        self.logger.info(f"Loading second data for {pair} across {len(venues)} venues")

        all_data = []
        adapter = SecondBarsAdapter(synthetic=True)

        for venue in venues:
            try:
                df = adapter.get(pair, venue, start_utc, end_utc)
                if not df.empty:
                    df["venue"] = venue
                    all_data.append(df)
                    self.logger.info(f"Loaded {len(df)} second bars for {venue}")
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

    def compute_mid_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute mid prices for each venue.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with mid prices added
        """
        df = df.copy()

        # Calculate mid prices
        df["mid"] = (df["high"] + df["low"]) / 2

        self.logger.info(f"Computed mid prices for {len(df)} records")

        return df

    def align_venues_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Align all venues by UTC second.

        Args:
            df: DataFrame with venue data

        Returns:
            Pivoted DataFrame with venues as columns
        """
        # Pivot to get venues as columns
        pivoted = (
            df.pivot_table(index="time", columns="venue", values="mid", aggfunc="first")
            .ffill()
            .bfill()
        )

        # Ensure all venues are present
        for venue in self.venues:
            if venue not in pivoted.columns:
                pivoted[venue] = pivoted.iloc[:, 0]  # Use first available venue as proxy

        # Reorder columns
        pivoted = pivoted[self.venues]

        self.logger.info(f"Aligned data: {len(pivoted)} time points, {len(pivoted.columns)} venues")

        return pivoted

    def compute_dispersion(self, mid_prices_df: pd.DataFrame) -> pd.Series:
        """
        Compute cross-venue dispersion D_t = std(mid^venue_t) in bps.

        Args:
            mid_prices_df: DataFrame with aligned mid prices

        Returns:
            Series of dispersion values
        """
        # Calculate consensus mid (median of all venues)
        consensus_mid = mid_prices_df.median(axis=1)

        # Calculate dispersion as standard deviation in basis points
        dispersion = mid_prices_df.std(axis=1) / consensus_mid * 10000  # Convert to bps

        self.logger.info(f"Computed dispersion for {len(dispersion)} time points")

        return dispersion

    def detect_compression_episodes(
        self, dispersion: pd.Series, mid_prices_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Detect compression episodes based on dispersion patterns.

        Args:
            dispersion: Series of dispersion values
            mid_prices_df: DataFrame with aligned mid prices

        Returns:
            List of compression episodes
        """
        episodes = []

        # Calculate thresholds
        p10_threshold = dispersion.quantile(self.compression_threshold)
        median_threshold = dispersion.quantile(self.median_threshold)

        self.logger.info(f"Compression threshold (p10): {p10_threshold:.2f} bps")
        self.logger.info(f"Median threshold: {median_threshold:.2f} bps")

        # Find potential compression starts
        compression_candidates = []

        for i in range(self.lookback_window, len(dispersion)):
            current_disp = dispersion.iloc[i]

            # Check if current dispersion is in bottom 10%
            if current_disp <= p10_threshold:
                # Check if dispersion was above median in prior 10s
                lookback_disp = dispersion.iloc[i - self.lookback_window : i]
                if (lookback_disp > median_threshold).any():
                    compression_candidates.append(i)

        # Process candidates to find actual episodes
        for start_idx in compression_candidates:
            # Find episode end (dispersion rises above p10)
            end_idx = start_idx
            for j in range(start_idx + 1, len(dispersion)):
                if dispersion.iloc[j] > p10_threshold:
                    end_idx = j - 1
                    break
            else:
                end_idx = len(dispersion) - 1

            # Check duration (≥3s)
            duration = end_idx - start_idx + 1
            if duration >= self.min_duration:
                # Attribute leadership
                leader = self._attribute_leadership(mid_prices_df, start_idx, end_idx)

                episode = {
                    "start_time": dispersion.index[start_idx],
                    "end_time": dispersion.index[end_idx],
                    "duration": duration,
                    "start_dispersion": dispersion.iloc[start_idx],
                    "end_dispersion": dispersion.iloc[end_idx],
                    "leader": leader,
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                }

                episodes.append(episode)

        self.logger.info(f"Detected {len(episodes)} compression episodes")

        return episodes

    def _attribute_leadership(
        self, mid_prices_df: pd.DataFrame, start_idx: int, end_idx: int
    ) -> str:
        """
        Attribute episode leadership to the first venue to move toward consensus.

        Args:
            mid_prices_df: DataFrame with aligned mid prices
            start_idx: Episode start index
            end_idx: Episode end index

        Returns:
            Venue name that led the compression
        """
        # Get consensus mid at episode start
        consensus_start = mid_prices_df.iloc[start_idx].median()

        # Look for first venue to move toward consensus in the lookback window
        lookback_start = max(0, start_idx - self.lookback_window)

        for i in range(lookback_start, start_idx):
            current_prices = mid_prices_df.iloc[i]
            consensus_current = current_prices.median()

            # Calculate distances to consensus
            distances = {}
            for venue in self.venues:
                if venue in current_prices.index:
                    distances[venue] = abs(current_prices[venue] - consensus_current)

            # Find venue that moved closest to consensus
            if distances:
                leader = min(distances, key=distances.get)
                return leader

        # Fallback: return venue with median price at start
        start_prices = mid_prices_df.iloc[start_idx]
        consensus_start = start_prices.median()

        distances = {}
        for venue in self.venues:
            if venue in start_prices.index:
                distances[venue] = abs(start_prices[venue] - consensus_start)

        if distances:
            return min(distances, key=distances.get)

        return self.venues[0]  # Fallback

    def cross_with_environments(
        self, episodes: List[Dict[str, Any]], regime_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Cross compression episodes with market environments.

        Args:
            episodes: List of compression episodes
            regime_data: Dictionary with regime assignments

        Returns:
            Cross-environment results
        """
        self.logger.info("Crossing compression episodes with market environments")

        cross_results = {}

        for env_name, env_df in regime_data.items():
            self.logger.info(f"Processing {env_name} environment")

            # Create episodes DataFrame
            episodes_df = pd.DataFrame(episodes)
            if episodes_df.empty:
                cross_results[env_name] = {}
                continue

            episodes_df["date"] = pd.to_datetime(episodes_df["start_time"]).dt.date

            # Merge with regime data
            if "regime" in env_df.columns:
                env_df["date"] = pd.to_datetime(env_df.index).date
                merged = episodes_df.merge(
                    env_df[["regime"]], left_on="date", right_index=True, how="left"
                )
                merged["regime"] = merged["regime"].fillna("unknown")
            else:
                merged = episodes_df
                merged["regime"] = "unknown"

            # Analyze by regime
            regime_results = {}
            for regime in ["low", "medium", "high"]:
                regime_episodes = merged[merged["regime"] == regime]

                if len(regime_episodes) > 0:
                    regime_results[regime] = {
                        "n_episodes": len(regime_episodes),
                        "avg_duration": regime_episodes["duration"].mean(),
                        "avg_start_disp": regime_episodes["start_dispersion"].mean(),
                        "avg_end_disp": regime_episodes["end_dispersion"].mean(),
                        "leaders": regime_episodes["leader"].value_counts().to_dict(),
                    }
                else:
                    regime_results[regime] = {
                        "n_episodes": 0,
                        "avg_duration": 0,
                        "avg_start_disp": 0,
                        "avg_end_disp": 0,
                        "leaders": {},
                    }

            cross_results[env_name] = regime_results

        return cross_results

    def compute_leadership_shares(
        self, episodes: List[Dict[str, Any]], env_breakdown: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute leadership shares by venue and environment.

        Args:
            episodes: List of compression episodes
            env_breakdown: Environment breakdown results

        Returns:
            Leadership shares dictionary
        """
        # Overall leadership shares
        overall_leaders = [ep["leader"] for ep in episodes]
        leader_counts = pd.Series(overall_leaders).value_counts()
        total_episodes = len(episodes)

        overall_shares = {}
        for venue in self.venues:
            count = leader_counts.get(venue, 0)
            overall_shares[venue] = {
                "count": int(count),
                "share": round(count / total_episodes * 100, 2) if total_episodes > 0 else 0,
            }

        # Environment-specific leadership
        env_leadership = {}
        for env_name, env_data in env_breakdown.items():
            env_leadership[env_name] = {}
            for regime, regime_data in env_data.items():
                leaders = regime_data.get("leaders", {})
                total_regime_episodes = regime_data.get("n_episodes", 0)

                regime_shares = {}
                for venue in self.venues:
                    count = leaders.get(venue, 0)
                    regime_shares[venue] = {
                        "count": int(count),
                        "share": (
                            round(count / total_regime_episodes * 100, 2)
                            if total_regime_episodes > 0
                            else 0
                        ),
                    }

                env_leadership[env_name][regime] = regime_shares

        return {"overall": overall_shares, "by_environment": env_leadership}

    def compute_statistical_tests(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute statistical tests for compression episodes.

        Args:
            episodes: List of compression episodes

        Returns:
            Statistical test results
        """
        if len(episodes) < 2:
            return {
                "permutation_test": {"p_value": 1.0, "n_permutations": 0},
                "chi2_test": {"chi2": 0.0, "p_value": 1.0, "dof": 0},
            }

        # Permutation test for episode clustering
        n_permutations = 1000
        observed_clustering = self._compute_clustering_metric(episodes)

        # Generate null distribution
        null_clustering = []
        for _ in range(n_permutations):
            # Shuffle episode times
            shuffled_episodes = episodes.copy()
            np.random.shuffle([ep["start_time"] for ep in shuffled_episodes])
            null_clustering.append(self._compute_clustering_metric(shuffled_episodes))

        # Calculate p-value
        p_value = np.mean(np.array(null_clustering) >= observed_clustering)

        # Chi-square test for leadership distribution
        leader_counts = pd.Series([ep["leader"] for ep in episodes]).value_counts()
        expected_counts = len(episodes) / len(self.venues)

        chi2_stat = 0
        for venue in self.venues:
            observed = leader_counts.get(venue, 0)
            chi2_stat += (observed - expected_counts) ** 2 / expected_counts

        chi2_p_value = 1 - stats.chi2.cdf(chi2_stat, len(self.venues) - 1)

        return {
            "permutation_test": {
                "p_value": round(p_value, 6),
                "n_permutations": n_permutations,
                "observed_clustering": round(observed_clustering, 4),
            },
            "chi2_test": {
                "chi2": round(chi2_stat, 4),
                "p_value": round(chi2_p_value, 6),
                "dof": len(self.venues) - 1,
            },
        }

    def _compute_clustering_metric(self, episodes: List[Dict[str, Any]]) -> float:
        """Compute clustering metric for episodes."""
        if len(episodes) < 2:
            return 0.0

        # Simple clustering metric: average time between consecutive episodes
        times = sorted([ep["start_time"] for ep in episodes])
        intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]

        if intervals:
            return np.mean(intervals).total_seconds()
        return 0.0

    def export_results(
        self, result: SpreadConvergenceResult, output_dir: str, start_date: str, end_date: str
    ) -> None:
        """
        Export all spread convergence results to files.

        Args:
            result: Spread convergence analysis result
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string
        """
        os.makedirs(output_dir, exist_ok=True)

        # Export episodes CSV
        episodes_path = os.path.join(output_dir, "spread_episodes.csv")
        result.episodes.to_csv(episodes_path, index=False)
        self.logger.info(f"Exported {len(result.episodes)} compression episodes")

        # Export leaders JSON
        leaders_path = os.path.join(output_dir, "spread_leaders.json")
        with open(leaders_path, "w") as f:
            json.dump(result.leaders, f, indent=2, default=str)

        # Update MANIFEST.json
        self._update_manifest(output_dir, start_date, end_date, result)

        self.logger.info(f"Exported spread convergence analysis results to {output_dir}/")

    def _update_manifest(
        self, output_dir: str, start_date: str, end_date: str, result: SpreadConvergenceResult
    ) -> None:
        """Update MANIFEST.json with spread convergence run data."""
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

        # Add spread convergence run data
        manifest_data["runs"]["spread_convergence"] = {
            "generated": datetime.now().isoformat() + "Z",
            "total_episodes": len(result.episodes),
            "min_duration": self.min_duration,
            "compression_threshold": self.compression_threshold,
            "venues": self.venues,
            "notes": "Cross-venue spread compression analysis",
        }

        # Write updated manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

    def analyze_spread_convergence(
        self,
        pair: str,
        venues: List[str],
        start_utc: datetime,
        end_utc: datetime,
        output_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
    ) -> SpreadConvergenceResult:
        """
        Run complete spread convergence analysis.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string

        Returns:
            Spread convergence analysis result
        """
        self.logger.info("Starting spread convergence analysis")

        # Load second data
        second_data = self.load_second_data(pair, venues, start_utc, end_utc)

        # Compute mid prices
        mid_prices_data = self.compute_mid_prices(second_data)

        # Align venues by time
        aligned_mid_prices = self.align_venues_by_time(mid_prices_data)

        # Compute dispersion
        dispersion = self.compute_dispersion(aligned_mid_prices)

        # Detect compression episodes
        episodes = self.detect_compression_episodes(dispersion, aligned_mid_prices)

        # Cross with environments (placeholder for now)
        cross_env_results = {}

        # Compute leadership shares
        leadership_shares = self.compute_leadership_shares(episodes, cross_env_results)

        # Compute statistical tests
        stats_results = self.compute_statistical_tests(episodes)

        # Create episodes DataFrame
        episodes_df = pd.DataFrame(episodes)

        # Log results
        episode_log = {
            "count": len(episodes),
            "medianDur": round(episodes_df["duration"].median(), 2) if len(episodes) > 0 else 0,
            "envBreakdown": cross_env_results,
        }
        print(f"[SPREAD:episodes] {json.dumps(episode_log, ensure_ascii=False)}")

        # Log leadership
        leaders_log = {"top_venues": dict(leadership_shares["overall"])}
        print(f"[SPREAD:leaders] {json.dumps(leaders_log, ensure_ascii=False)}")

        # Log statistical tests
        permute_log = stats_results["permutation_test"]
        print(f"[STATS:spread:permute] {json.dumps(permute_log, ensure_ascii=False)}")

        # Create result object
        result = SpreadConvergenceResult(
            episodes=episodes_df,
            leaders=leadership_shares,
            env_breakdown=cross_env_results,
            stats_results=stats_results,
        )

        # Export results
        self.export_results(result, output_dir, start_date, end_date)

        self.logger.info("Spread convergence analysis completed")

        return result


def create_spread_convergence_analyzer(spec_version: str = "1.0.0") -> SpreadConvergenceAnalyzer:
    """Create a spread convergence analyzer instance."""
    return SpreadConvergenceAnalyzer(spec_version=spec_version)
