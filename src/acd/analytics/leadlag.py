"""
Lead-Lag Matrix Analysis Module

This module analyzes lead-lag relationships between venues at high frequency
to detect coordination patterns and information flow.
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
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


@dataclass
class LeadLagResult:
    """Result container for lead-lag analysis."""

    edges: Dict[str, List[Dict[str, Any]]]
    leader_ranks: Dict[str, List[Dict[str, Any]]]
    cross_env_results: Dict[str, Any]
    stats_results: Dict[str, Any]


class LeadLagMatrixAnalyzer:
    """
    Analyzes lead-lag relationships between venues at multiple horizons.

    Computes Granger-style predictability and builds leader rankings
    to identify information flow patterns.
    """

    def __init__(self, spec_version: str = "1.0.0"):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.horizons = ["1s", "5s", "30s"]
        self.environments = ["volatility", "funding", "liquidity"]

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

    def compute_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute log returns for each venue.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with returns added
        """
        df = df.copy()

        # Calculate mid prices
        df["mid"] = (df["high"] + df["low"]) / 2

        # Compute log returns
        df["log_mid"] = np.log(df["mid"])
        df["returns"] = df.groupby("venue")["log_mid"].diff()

        # Remove NaN values
        df = df.dropna(subset=["returns"])

        self.logger.info(f"Computed returns for {len(df)} records")

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
        pivoted = df.pivot_table(
            index="time", columns="venue", values="returns", aggfunc="first"
        ).fillna(0)

        # Ensure all venues are present
        for venue in self.venues:
            if venue not in pivoted.columns:
                pivoted[venue] = 0

        # Reorder columns
        pivoted = pivoted[self.venues]

        self.logger.info(f"Aligned data: {len(pivoted)} time points, {len(pivoted.columns)} venues")

        return pivoted

    def compute_leadlag_score(
        self, returns_df: pd.DataFrame, src_venue: str, dst_venue: str, horizon: str
    ) -> Dict[str, Any]:
        """
        Compute lead-lag score between two venues.

        Args:
            returns_df: DataFrame with aligned returns
            src_venue: Source venue (leader)
            dst_venue: Destination venue (follower)
            horizon: Time horizon ('1s', '5s', '30s')

        Returns:
            Dictionary with lead-lag metrics
        """
        # Get horizon in seconds
        horizon_seconds = {"1s": 1, "5s": 5, "30s": 30}[horizon]

        # Extract return series
        src_returns = returns_df[src_venue].values
        dst_returns = returns_df[dst_venue].values

        # Remove any remaining NaN values
        valid_mask = ~(np.isnan(src_returns) | np.isnan(dst_returns))
        src_returns = src_returns[valid_mask]
        dst_returns = dst_returns[valid_mask]

        if len(src_returns) < horizon_seconds + 1:
            return {
                "src": src_venue,
                "dst": dst_venue,
                "score": 0.0,
                "p_value": 1.0,
                "t_stat": 0.0,
                "r_squared": 0.0,
                "n_obs": len(src_returns),
                "valid": False,
            }

        # Create lagged features
        X = []
        y = []

        for i in range(horizon_seconds, len(src_returns)):
            # Use lagged source returns as features
            features = src_returns[i - horizon_seconds : i]
            target = dst_returns[i]

            X.append(features)
            y.append(target)

        X = np.array(X)
        y = np.array(y)

        if len(X) == 0:
            return {
                "src": src_venue,
                "dst": dst_venue,
                "score": 0.0,
                "p_value": 1.0,
                "t_stat": 0.0,
                "r_squared": 0.0,
                "n_obs": len(src_returns),
                "valid": False,
            }

        # Fit linear regression
        try:
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)

            # Calculate R-squared
            r_squared = r2_score(y, y_pred)

            # Calculate t-statistic for the coefficient
            residuals = y - y_pred
            mse = np.mean(residuals**2)

            if mse > 0:
                # Simplified t-statistic calculation
                t_stat = np.sqrt(r_squared * len(y) / (1 - r_squared)) if r_squared < 1 else 0
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), len(y) - 2))
            else:
                t_stat = 0
                p_value = 1.0

            # Lead-lag score (absolute t-statistic)
            score = abs(t_stat)

            return {
                "src": src_venue,
                "dst": dst_venue,
                "score": round(score, 4),
                "p_value": round(p_value, 6),
                "t_stat": round(t_stat, 4),
                "r_squared": round(r_squared, 4),
                "n_obs": len(y),
                "valid": True,
            }

        except Exception as e:
            self.logger.warning(f"Error computing lead-lag for {src_venue}->{dst_venue}: {str(e)}")
            return {
                "src": src_venue,
                "dst": dst_venue,
                "score": 0.0,
                "p_value": 1.0,
                "t_stat": 0.0,
                "r_squared": 0.0,
                "n_obs": len(src_returns),
                "valid": False,
            }

    def compute_leadlag_matrix(
        self, returns_df: pd.DataFrame, horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Compute lead-lag matrix for all venue pairs.

        Args:
            returns_df: DataFrame with aligned returns
            horizon: Time horizon

        Returns:
            List of edge dictionaries
        """
        edges = []

        for src_venue in self.venues:
            for dst_venue in self.venues:
                if src_venue != dst_venue:
                    edge = self.compute_leadlag_score(returns_df, src_venue, dst_venue, horizon)
                    edges.append(edge)

        # Filter significant edges (p < 0.05)
        significant_edges = [e for e in edges if e["valid"] and e["p_value"] < 0.05]

        self.logger.info(
            f"Horizon {horizon}: {len(significant_edges)} significant edges "
            f"out of {len(edges)} total"
        )

        return edges

    def compute_leader_rank(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compute leader ranking based on net outflow.

        Args:
            edges: List of edge dictionaries

        Returns:
            List of venue rankings
        """
        # Calculate net outflow for each venue
        venue_stats = {}

        for venue in self.venues:
            venue_stats[venue] = {
                "out_degree": 0,
                "in_degree": 0,
                "net_outflow": 0,
                "total_score": 0.0,
            }

        # Count edges
        for edge in edges:
            if edge["valid"] and edge["p_value"] < 0.05:
                src = edge["src"]
                dst = edge["dst"]
                score = edge["score"]

                venue_stats[src]["out_degree"] += 1
                venue_stats[src]["total_score"] += score
                venue_stats[dst]["in_degree"] += 1

        # Calculate net outflow
        for venue in self.venues:
            stats = venue_stats[venue]
            stats["net_outflow"] = stats["out_degree"] - stats["in_degree"]

        # Sort by net outflow (descending)
        rankings = []
        for venue in self.venues:
            stats = venue_stats[venue]
            rankings.append(
                {
                    "venue": venue,
                    "out_degree": stats["out_degree"],
                    "in_degree": stats["in_degree"],
                    "net_outflow": stats["net_outflow"],
                    "total_score": round(stats["total_score"], 4),
                }
            )

        rankings.sort(key=lambda x: x["net_outflow"], reverse=True)

        return rankings

    def cross_with_environments(
        self, returns_df: pd.DataFrame, regime_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Cross lead-lag analysis with market environments.

        Args:
            returns_df: DataFrame with aligned returns
            regime_data: Dictionary with regime assignments

        Returns:
            Cross-environment results
        """
        self.logger.info("Crossing lead-lag analysis with market environments")

        cross_results = {}

        for env_name, env_df in regime_data.items():
            self.logger.info(f"Processing {env_name} environment")

            # Join returns with regime data
            returns_with_regime = returns_df.copy()
            returns_with_regime["date"] = returns_with_regime.index.date

            # Merge with regime data
            if "regime" in env_df.columns:
                env_df["date"] = pd.to_datetime(env_df.index).date
                merged = returns_with_regime.merge(
                    env_df[["regime"]], left_on="date", right_index=True, how="left"
                )
                merged["regime"] = merged["regime"].fillna("unknown")
            else:
                merged = returns_with_regime
                merged["regime"] = "unknown"

            # Analyze by regime
            regime_results = {}
            for regime in ["low", "medium", "high"]:
                regime_mask = merged["regime"] == regime
                regime_returns = merged[regime_mask]

                if len(regime_returns) > 100:  # Minimum sample size
                    # Compute lead-lag for this regime
                    regime_edges = []
                    for src_venue in self.venues:
                        for dst_venue in self.venues:
                            if src_venue != dst_venue:
                                edge = self.compute_leadlag_score(
                                    regime_returns[self.venues], src_venue, dst_venue, "1s"
                                )
                                regime_edges.append(edge)

                    regime_results[regime] = {
                        "edges": regime_edges,
                        "n_obs": len(regime_returns),
                        "significant_edges": len(
                            [e for e in regime_edges if e["valid"] and e["p_value"] < 0.05]
                        ),
                    }
                else:
                    regime_results[regime] = {
                        "edges": [],
                        "n_obs": len(regime_returns),
                        "significant_edges": 0,
                    }

            cross_results[env_name] = regime_results

        return cross_results

    def compute_statistical_tests(
        self, edges_by_horizon: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Compute statistical tests for lead-lag relationships.

        Args:
            edges_by_horizon: Dictionary of edges by horizon

        Returns:
            Statistical test results
        """
        stats_results = {}

        for horizon, edges in edges_by_horizon.items():
            # Extract significant edges
            significant_edges = [e for e in edges if e["valid"] and e["p_value"] < 0.05]

            if len(significant_edges) > 0:
                # Chi-square test for independence
                # Create contingency table: venue x venue
                contingency = np.zeros((len(self.venues), len(self.venues)))
                venue_to_idx = {v: i for i, v in enumerate(self.venues)}

                for edge in significant_edges:
                    src_idx = venue_to_idx[edge["src"]]
                    dst_idx = venue_to_idx[edge["dst"]]
                    contingency[src_idx, dst_idx] += 1

                # Chi-square test (with error handling for zero expected frequencies)
                try:
                    chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
                except ValueError as e:
                    if "zero element" in str(e):
                        # Handle zero expected frequencies
                        chi2, p_value, dof = 0.0, 1.0, 0
                    else:
                        raise

                stats_results[horizon] = {
                    "chi2": round(chi2, 4),
                    "p_value": round(p_value, 6),
                    "dof": int(dof),
                    "n_significant": len(significant_edges),
                    "n_total": len(edges),
                }

                # Log single-line JSON
                chi2_result = {
                    "chi2_statistic": round(chi2, 4),
                    "p_value": round(p_value, 6),
                    "degrees_of_freedom": int(dof),
                }
                print(f"[STATS:leadlag:chi2] {json.dumps(chi2_result, ensure_ascii=False)}")
            else:
                stats_results[horizon] = {
                    "chi2": 0.0,
                    "p_value": 1.0,
                    "dof": 0,
                    "n_significant": 0,
                    "n_total": len(edges),
                }

        return stats_results

    def export_results(
        self, result: LeadLagResult, output_dir: str, start_date: str, end_date: str
    ) -> None:
        """
        Export all lead-lag results to files.

        Args:
            result: Lead-lag analysis result
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string
        """
        os.makedirs(output_dir, exist_ok=True)

        # Export edges by horizon
        for horizon, edges in result.edges.items():
            edges_path = os.path.join(output_dir, f"leadlag_edges_h={horizon}.csv")
            edges_df = pd.DataFrame(edges)
            edges_df.to_csv(edges_path, index=False)
            self.logger.info(f"Exported {len(edges)} edges for horizon {horizon}")

        # Export leader rankings
        ranks_path = os.path.join(output_dir, "leadlag_ranks.csv")
        all_ranks = []
        for horizon, ranks in result.leader_ranks.items():
            for rank in ranks:
                rank["horizon"] = horizon
                all_ranks.append(rank)

        ranks_df = pd.DataFrame(all_ranks)
        ranks_df.to_csv(ranks_path, index=False)
        self.logger.info(f"Exported leader rankings for {len(result.leader_ranks)} horizons")

        # Export cross-environment results
        cross_env_path = os.path.join(output_dir, "leadlag_by_env.json")
        with open(cross_env_path, "w") as f:
            json.dump(result.cross_env_results, f, indent=2, default=str)

        # Update MANIFEST.json
        self._update_manifest(output_dir, start_date, end_date, result)

        self.logger.info(f"Exported lead-lag analysis results to {output_dir}/")

    def _update_manifest(
        self, output_dir: str, start_date: str, end_date: str, result: LeadLagResult
    ) -> None:
        """Update MANIFEST.json with lead-lag run data."""
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

        # Add lead-lag run data
        total_edges = sum(len(edges) for edges in result.edges.values())
        significant_edges = sum(
            len([e for e in edges if e["valid"] and e["p_value"] < 0.05])
            for edges in result.edges.values()
        )

        manifest_data["runs"]["leadlag"] = {
            "generated": datetime.now().isoformat() + "Z",
            "horizons": list(result.edges.keys()),
            "total_edges": total_edges,
            "significant_edges": significant_edges,
            "venues": self.venues,
            "notes": "Lead-lag analysis across multiple horizons",
        }

        # Write updated manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

    def analyze_leadlag(
        self,
        pair: str,
        venues: List[str],
        start_utc: datetime,
        end_utc: datetime,
        output_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
    ) -> LeadLagResult:
        """
        Run complete lead-lag analysis.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string

        Returns:
            Lead-lag analysis result
        """
        self.logger.info("Starting lead-lag matrix analysis")

        # Load second data
        second_data = self.load_second_data(pair, venues, start_utc, end_utc)

        # Compute returns
        returns_data = self.compute_returns(second_data)

        # Align venues by time
        aligned_returns = self.align_venues_by_time(returns_data)

        # Compute lead-lag matrices for each horizon
        edges_by_horizon = {}
        leader_ranks_by_horizon = {}

        for horizon in self.horizons:
            self.logger.info(f"Computing lead-lag matrix for horizon {horizon}")

            # Compute edges
            edges = self.compute_leadlag_matrix(aligned_returns, horizon)
            edges_by_horizon[horizon] = edges

            # Compute leader rankings
            ranks = self.compute_leader_rank(edges)
            leader_ranks_by_horizon[horizon] = ranks

            # Log results
            significant_edges = [e for e in edges if e["valid"] and e["p_value"] < 0.05]
            log_data = {"edges": significant_edges, "leaderRank": ranks}
            print(f"[LEADLAG:h={horizon}] {json.dumps(log_data, ensure_ascii=False)}")

        # Cross with environments (placeholder for now)
        cross_env_results = {}

        # Compute statistical tests
        stats_results = self.compute_statistical_tests(edges_by_horizon)

        # Create result object
        result = LeadLagResult(
            edges=edges_by_horizon,
            leader_ranks=leader_ranks_by_horizon,
            cross_env_results=cross_env_results,
            stats_results=stats_results,
        )

        # Export results
        self.export_results(result, output_dir, start_date, end_date)

        self.logger.info("Lead-lag matrix analysis completed")

        return result


def create_leadlag_analyzer(spec_version: str = "1.0.0") -> LeadLagMatrixAnalyzer:
    """Create a lead-lag matrix analyzer instance."""
    return LeadLagMatrixAnalyzer(spec_version=spec_version)
