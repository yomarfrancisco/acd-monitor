"""
Synchronous Move Detection Module

This module detects abnormal simultaneity in venue price movements
to identify potential coordinated algorithmic behavior.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SyncMoveResult:
    """Result container for synchronous move analysis."""

    events: pd.DataFrame
    summary: Dict[str, Any]
    env_breakdown: Dict[str, Any]
    config: Dict[str, Any]


class SynchronousMoveDetector:
    """
    Detects synchronous price movements across venues.

    Identifies abnormal simultaneity by comparing observed coincidences
    to expected values under independence assumptions.
    """

    def __init__(self, spec_version: str = "1.0.0"):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.dt_windows = [1, 2]  # seconds
        self.theta_pct = 90  # percentile threshold

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

    def compute_jump_thresholds(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute jump thresholds (θ) for each venue.

        Args:
            returns_df: DataFrame with aligned returns

        Returns:
            Dictionary of thresholds by venue
        """
        thresholds = {}

        for venue in self.venues:
            if venue in returns_df.columns:
                venue_returns = returns_df[venue].dropna()
                if len(venue_returns) > 0:
                    # Compute 90th percentile of absolute returns
                    threshold = np.percentile(np.abs(venue_returns), self.theta_pct)
                    thresholds[venue] = threshold
                else:
                    thresholds[venue] = 0.0
            else:
                thresholds[venue] = 0.0

        self.logger.info(f"Computed jump thresholds: {thresholds}")

        return thresholds

    def detect_jumps(self, returns_df: pd.DataFrame, thresholds: Dict[str, float]) -> pd.DataFrame:
        """
        Detect jumps for each venue based on thresholds.

        Args:
            returns_df: DataFrame with aligned returns
            thresholds: Dictionary of thresholds by venue

        Returns:
            DataFrame with jump flags and signs
        """
        jump_df = returns_df.copy()

        for venue in self.venues:
            if venue in jump_df.columns:
                # Flag jumps where |r_t| > θ
                jump_df[f"{venue}_jump"] = np.abs(jump_df[venue]) > thresholds[venue]
                jump_df[f"{venue}_sign"] = np.sign(jump_df[venue])
            else:
                jump_df[f"{venue}_jump"] = False
                jump_df[f"{venue}_sign"] = 0

        self.logger.info(f"Detected jumps for {len(jump_df)} time points")

        return jump_df

    def detect_coincidence_events(
        self, jump_df: pd.DataFrame, dt_window: int
    ) -> List[Dict[str, Any]]:
        """
        Detect coincidence events within time window.

        Args:
            jump_df: DataFrame with jump flags
            dt_window: Time window in seconds

        Returns:
            List of coincidence events
        """
        events = []

        for i, (timestamp, row) in enumerate(jump_df.iterrows()):
            # Get venues that jumped at this time
            jumping_venues = []
            for venue in self.venues:
                if row[f"{venue}_jump"]:
                    jumping_venues.append(
                        {"venue": venue, "sign": row[f"{venue}_sign"], "return": row[venue]}
                    )

            if len(jumping_venues) >= 3:
                # Check for same sign
                signs = [v["sign"] for v in jumping_venues]
                if len(set(signs)) == 1:  # All same sign
                    # Look for additional venues within dt_window
                    window_venues = set(v["venue"] for v in jumping_venues)

                    # Check future timestamps within window
                    for j in range(i + 1, min(i + dt_window + 1, len(jump_df))):
                        if j < len(jump_df):
                            future_row = jump_df.iloc[j]
                            for venue in self.venues:
                                if (
                                    future_row[f"{venue}_jump"]
                                    and future_row[f"{venue}_sign"] == signs[0]
                                    and venue not in window_venues
                                ):
                                    window_venues.add(venue)

                    if len(window_venues) >= 3:
                        events.append(
                            {
                                "time": timestamp,
                                "venues": list(window_venues),
                                "sign": signs[0],
                                "n_venues": len(window_venues),
                                "dt_window": dt_window,
                                "returns": {
                                    venue: jump_df.loc[timestamp, venue] for venue in window_venues
                                },
                            }
                        )

        self.logger.info(f"Detected {len(events)} coincidence events for dt={dt_window}s")

        return events

    def compute_expected_coincidences(
        self, jump_df: pd.DataFrame, dt_window: int, n_bootstrap: int = 1000
    ) -> Tuple[float, float]:
        """
        Compute expected coincidences under independence.

        Args:
            jump_df: DataFrame with jump flags
            dt_window: Time window in seconds
            n_bootstrap: Number of bootstrap samples

        Returns:
            Tuple of (expected_coincidences, p_value)
        """
        # Extract jump probabilities for each venue
        jump_probs = {}
        for venue in self.venues:
            if f"{venue}_jump" in jump_df.columns:
                jump_probs[venue] = jump_df[f"{venue}_jump"].mean()
            else:
                jump_probs[venue] = 0.0

        # Bootstrap simulation
        bootstrap_coincidences = []

        for _ in range(n_bootstrap):
            # Simulate independent jumps
            simulated_jumps = {}
            for venue in self.venues:
                prob = jump_probs[venue]
                simulated_jumps[venue] = np.random.binomial(1, prob, len(jump_df))

            # Count coincidences in simulation
            sim_coincidences = 0
            for i in range(len(jump_df)):
                # Count venues jumping at this time
                jumping_venues = [v for v in self.venues if simulated_jumps[v][i]]

                if len(jumping_venues) >= 3:
                    # Check for same sign (simplified - assume random signs)
                    signs = np.random.choice([-1, 1], len(jumping_venues))
                    if len(set(signs)) == 1:  # All same sign
                        # Check window
                        window_venues = set(jumping_venues)
                        for j in range(i + 1, min(i + dt_window + 1, len(jump_df))):
                            if j < len(jump_df):
                                future_jumping = [v for v in self.venues if simulated_jumps[v][j]]
                                for venue in future_jumping:
                                    if venue not in window_venues:
                                        window_venues.add(venue)

                        if len(window_venues) >= 3:
                            sim_coincidences += 1

            bootstrap_coincidences.append(sim_coincidences)

        expected_coincidences = np.mean(bootstrap_coincidences)
        p_value = np.mean(
            np.array(bootstrap_coincidences)
            >= len(self.detect_coincidence_events(jump_df, dt_window))
        )

        return expected_coincidences, p_value

    def cross_with_environments(
        self, events: List[Dict[str, Any]], regime_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Cross synchronous events with market environments.

        Args:
            events: List of coincidence events
            regime_data: Dictionary with regime assignments

        Returns:
            Cross-environment results
        """
        self.logger.info("Crossing synchronous events with market environments")

        cross_results = {}

        for env_name, env_df in regime_data.items():
            self.logger.info(f"Processing {env_name} environment")

            # Create events DataFrame
            events_df = pd.DataFrame(events)
            if events_df.empty:
                cross_results[env_name] = {}
                continue

            events_df["date"] = pd.to_datetime(events_df["time"]).dt.date

            # Merge with regime data
            if "regime" in env_df.columns:
                env_df["date"] = pd.to_datetime(env_df.index).date
                merged = events_df.merge(
                    env_df[["regime"]], left_on="date", right_index=True, how="left"
                )
                merged["regime"] = merged["regime"].fillna("unknown")
            else:
                merged = events_df
                merged["regime"] = "unknown"

            # Analyze by regime
            regime_results = {}
            for regime in ["low", "medium", "high"]:
                regime_events = merged[merged["regime"] == regime]

                if len(regime_events) > 0:
                    regime_results[regime] = {
                        "n_events": len(regime_events),
                        "avg_venues": regime_events["n_venues"].mean(),
                        "venues_distribution": regime_events["n_venues"].value_counts().to_dict(),
                    }
                else:
                    regime_results[regime] = {
                        "n_events": 0,
                        "avg_venues": 0,
                        "venues_distribution": {},
                    }

            cross_results[env_name] = regime_results

        return cross_results

    def export_results(
        self, result: SyncMoveResult, output_dir: str, start_date: str, end_date: str
    ) -> None:
        """
        Export all synchronous move results to files.

        Args:
            result: Synchronous move analysis result
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string
        """
        os.makedirs(output_dir, exist_ok=True)

        # Export events CSV
        events_path = os.path.join(output_dir, "sync_events.csv")
        result.events.to_csv(events_path, index=False)
        self.logger.info(f"Exported {len(result.events)} synchronous events")

        # Export summary JSON
        summary_path = os.path.join(output_dir, "sync_summary.json")
        with open(summary_path, "w") as f:
            json.dump(result.summary, f, indent=2, default=str)

        # Update MANIFEST.json
        self._update_manifest(output_dir, start_date, end_date, result)

        self.logger.info(f"Exported synchronous move analysis results to {output_dir}/")

    def _update_manifest(
        self, output_dir: str, start_date: str, end_date: str, result: SyncMoveResult
    ) -> None:
        """Update MANIFEST.json with sync move run data."""
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

        # Add sync move run data
        manifest_data["runs"]["sync_moves"] = {
            "generated": datetime.now().isoformat() + "Z",
            "config": result.config,
            "total_events": len(result.events),
            "dt_windows": self.dt_windows,
            "venues": self.venues,
            "notes": "Synchronous move detection across multiple time windows",
        }

        # Write updated manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

    def analyze_sync_moves(
        self,
        pair: str,
        venues: List[str],
        start_utc: datetime,
        end_utc: datetime,
        output_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
    ) -> SyncMoveResult:
        """
        Run complete synchronous move analysis.

        Args:
            pair: Trading pair
            venues: List of venues
            start_utc: Start datetime
            end_utc: End datetime
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string

        Returns:
            Synchronous move analysis result
        """
        self.logger.info("Starting synchronous move detection")

        # Log configuration
        config = {"theta_pct": self.theta_pct, "dt": self.dt_windows, "venues": venues}
        print(f"[SYNC:config] {json.dumps(config, ensure_ascii=False)}")

        # Load second data
        second_data = self.load_second_data(pair, venues, start_utc, end_utc)

        # Compute returns
        returns_data = self.compute_returns(second_data)

        # Align venues by time
        aligned_returns = self.align_venues_by_time(returns_data)

        # Compute jump thresholds
        thresholds = self.compute_jump_thresholds(aligned_returns)

        # Detect jumps
        jump_df = self.detect_jumps(aligned_returns, thresholds)

        # Detect coincidence events for each time window
        all_events = []
        summary_results = {}

        for dt_window in self.dt_windows:
            self.logger.info(f"Detecting coincidence events for dt={dt_window}s")

            # Detect events
            events = self.detect_coincidence_events(jump_df, dt_window)
            all_events.extend(events)

            # Compute expected coincidences
            expected, p_value = self.compute_expected_coincidences(jump_df, dt_window)

            # Calculate lift
            observed = len(events)
            lift = observed / expected if expected > 0 else 0

            summary_results[f"dt_{dt_window}s"] = {
                "observed": observed,
                "expected": round(expected, 4),
                "lift": round(lift, 4),
                "p_value": round(p_value, 6),
            }

            # Log summary
            summary_log = {
                "dt": dt_window,
                "observed": observed,
                "expected": round(expected, 4),
                "lift": round(lift, 4),
                "p_value": round(p_value, 6),
            }
            print(f"[SYNC:summary] {json.dumps(summary_log, ensure_ascii=False)}")

        # Cross with environments (placeholder for now)
        cross_env_results = {}

        # Create events DataFrame
        events_df = pd.DataFrame(all_events)

        # Create result object
        result = SyncMoveResult(
            events=events_df,
            summary=summary_results,
            env_breakdown=cross_env_results,
            config=config,
        )

        # Export results
        self.export_results(result, output_dir, start_date, end_date)

        self.logger.info("Synchronous move detection completed")

        return result


def create_sync_move_detector(spec_version: str = "1.0.0") -> SynchronousMoveDetector:
    """Create a synchronous move detector instance."""
    return SynchronousMoveDetector(spec_version=spec_version)
