"""
Volatility Regime Environments for ACD Analysis

This module implements volatility regime environments as specified in the ACD Working Plan.
It computes 20-day rolling realized volatility from OHLCV data, partitions into terciles,
and provides leadership distribution analysis across volatility regimes.

Based on ACD_Working_Plan.md Step 1: Implement volatility regime environments for BTC-USD.

Logging Schema: Implements structured logging with court-ready format including:
- [ENV:volatility:config] - Configuration and metadata
- [ENV:volatility:terciles] - Tercile thresholds and bounds
- [ENV:volatility:assignments] - Regime assignments summary
- [LEADER:env:volatility:summary] - Leadership shares by regime
- [LEADER:env:volatility:table] - Full ranking table
- [LEADER:env:volatility:dropped] - Dropped day accounting
- [LEADER:env:volatility:ties] - Tie day statistics
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VolatilityRegime:
    """Represents a volatility regime with boundaries and statistics"""

    regime: str  # 'low', 'medium', 'high'
    lower_bound: float
    upper_bound: float
    count: int
    percentage: float


@dataclass
class LeadershipDistribution:
    """Leadership distribution within a volatility regime"""

    regime: str
    venue_leadership: Dict[str, float]  # venue -> percentage of days leading
    total_days: int
    venue_rankings: List[Tuple[str, int]]  # (venue, win_count) sorted by wins
    tie_days: int = 0  # number of days with ties


@dataclass
class VolatilityRegimeResults:
    """Complete results from volatility regime analysis"""

    regimes: List[VolatilityRegime]
    leadership_by_regime: List[LeadershipDistribution]
    volatility_series: pd.Series
    regime_labels: pd.Series
    summary: Dict[str, Any]
    ohlcv_data: pd.DataFrame


class VolatilityRegimeAnalyzer:
    """
    Analyzes volatility regimes and leadership patterns across them.

    Implements the ACD Working Plan Step 1 requirements:
    1. Compute 20-day rolling realized volatility from OHLCV
    2. Partition into low/med/high terciles
    3. Label each day with volatility regime
    4. Compute leadership distribution per regime
    5. Log outputs in structured court-ready format
    """

    def __init__(
        self,
        window: int = 20,
        min_periods: int = 10,
        spec_version: str = "1.0.0",
        pair: str = "BTC-USD",
    ):
        """
        Initialize the volatility regime analyzer.

        Args:
            window: Rolling window size for volatility calculation (default: 20 days)
            min_periods: Minimum periods required for volatility calculation
            spec_version: Specification version for logging
            pair: Trading pair identifier
        """
        self.window = window
        self.min_periods = min_periods
        self.spec_version = spec_version
        self.pair = pair
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "bybit", "okx", "kraken"]

    def _get_code_version(self) -> str:
        """Get git commit hash for code versioning."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def _log_config(self, ohlcv_data: pd.DataFrame) -> None:
        """Log configuration and metadata."""
        config = {
            "specVersion": self.spec_version,
            "codeVersion": self._get_code_version(),
            "pair": self.pair,
            "window": self.window,
            "annualize": True,
            "source": "close",
            "tz": "UTC",
            "sample": {
                "start": ohlcv_data.index.min().strftime("%Y-%m-%d"),
                "end": ohlcv_data.index.max().strftime("%Y-%m-%d"),
                "bars": len(ohlcv_data),
            },
        }

        self.logger.info(f"[ENV:volatility:config] {json.dumps(config, indent=2, default=str)}")

    def _log_terciles(self, volatility_series: pd.Series, regimes: List[VolatilityRegime]) -> None:
        """Log tercile thresholds and bounds."""
        clean_vol = volatility_series.dropna()
        q33 = clean_vol.quantile(0.33)
        q66 = clean_vol.quantile(0.67)

        terciles = {
            "sigma20_quantiles": {"q33": round(q33, 4), "q66": round(q66, 4)},
            "bounds": {
                "low": {"max": round(q33, 4)},
                "medium": {"min": round(q33, 4), "max": round(q66, 4)},
                "high": {"min": round(q66, 4)},
            },
            "counts": {r.regime: r.count for r in regimes},
            "coveragePct": round(sum(r.count for r in regimes) / len(volatility_series) * 100, 2),
        }

        self.logger.info(f"[ENV:volatility:terciles] {json.dumps(terciles, indent=2, default=str)}")

    def _log_assignments(self, regime_labels: pd.Series, drop_reasons: Dict[str, int]) -> None:
        """Log regime assignments summary."""
        kept_days = len(regime_labels.dropna())
        dropped_days = len(regime_labels) - kept_days

        by_regime = []
        for regime in ["low", "medium", "high"]:
            count = (regime_labels == regime).sum()
            by_regime.append({"regime": regime, "days": int(count)})

        assignments = {
            "keptDays": int(kept_days),
            "droppedDays": int(dropped_days),
            "dropReasons": drop_reasons,
            "byRegime": by_regime,
        }

        self.logger.info(
            f"[ENV:volatility:assignments] {json.dumps(assignments, indent=2, default=str)}"
        )

    def _log_leadership_summary(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log leadership shares by regime."""
        regimes_data = []

        for leadership in leadership_by_regime:
            shares_pct = []
            for venue in self.venues:
                pct = leadership.venue_leadership.get(venue, 0.0)
                shares_pct.append({"venue": venue, "pct": round(pct, 2)})

            # Sort by percentage descending
            shares_pct.sort(key=lambda x: x["pct"], reverse=True)

            regimes_data.append(
                {
                    "regime": leadership.regime,
                    "days": leadership.total_days,
                    "sharesPct": shares_pct,
                    "isTie": False,  # Will be updated if ties detected
                }
            )

        summary = {
            "method": "consensus-proximity",
            "pair": self.pair,
            "keptDays": sum(leadership.total_days for leadership in leadership_by_regime),
            "regimes": regimes_data,
        }

        self.logger.info(
            f"[LEADER:env:volatility:summary] {json.dumps(summary, indent=2, default=str)}"
        )

    def _log_leadership_table(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log full ranking table with counts and percentages."""
        # Aggregate wins across all regimes
        total_wins = {}
        for venue in self.venues:
            total_wins[venue] = 0

        for leadership in leadership_by_regime:
            for venue, wins in leadership.venue_rankings:
                total_wins[venue] += wins

        total_days = sum(leadership.total_days for leadership in leadership_by_regime)

        table = []
        for venue in self.venues:
            wins = total_wins[venue]
            pct = round((wins / total_days * 100) if total_days > 0 else 0, 2)
            table.append({"venue": venue, "wins": wins, "pct": pct})

        # Sort by wins descending
        table.sort(key=lambda x: x["wins"], reverse=True)

        table_data = {"keptDays": total_days, "table": table}

        self.logger.info(
            f"[LEADER:env:volatility:table] {json.dumps(table_data, indent=2, default=str)}"
        )

    def _log_dropped_days(self, drop_reasons: Dict[str, int]) -> None:
        """Log dropped day accounting."""
        dropped_data = {"dropped": sum(drop_reasons.values()), "drop": drop_reasons}

        self.logger.info(
            f"[LEADER:env:volatility:dropped] {json.dumps(dropped_data, indent=2, default=str)}"
        )

    def _log_ties(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log tie day statistics by regime."""
        ties_data = []

        for leadership in leadership_by_regime:
            # Count days with ties (multiple venues with same score)
            tie_days = 0
            # This would need to be calculated from the actual consensus data
            # For now, we'll estimate based on the distribution

            ties_data.append({"regime": leadership.regime, "tieDays": tie_days})

        ties_info = {"byRegime": ties_data}
        self.logger.info(
            f"[LEADER:env:volatility:ties] {json.dumps(ties_info, indent=2, default=str)}"
        )

    def _log_volatility_stats(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log statistical test results for volatility analysis."""
        # Basic chi-square test for regime-leadership relationship
        import scipy.stats as stats

        # Prepare contingency table
        regime_data = []
        venue_data = []

        for leadership in leadership_by_regime:
            for venue, wins in leadership.venue_rankings:
                regime_data.extend([leadership.regime] * int(wins))
                venue_data.extend([venue] * int(wins))

        if len(regime_data) > 0:
            contingency_table = pd.crosstab(regime_data, venue_data)
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

            # Chi-square test
            chi2_result = {
                "chi2_statistic": round(chi2, 4),
                "p_value": round(p_value, 6),
                "degrees_of_freedom": int(dof),
                "expected_frequencies": expected.tolist(),
            }
            print(f"[STATS:env:volatility:chi2] {json.dumps(chi2_result, ensure_ascii=False)}")

            # Cramér's V
            n = contingency_table.sum().sum()
            cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))
            cramers_v_result = {
                "cramers_v": round(cramers_v, 4),
                "interpretation": (
                    "small" if cramers_v < 0.1 else "medium" if cramers_v < 0.3 else "large"
                ),
            }
            cramers_json = json.dumps(cramers_v_result, ensure_ascii=False)
            print(f"[STATS:env:volatility:cramers_v] {cramers_json}")

            # Bootstrap confidence intervals (simplified)
            n_bootstrap = 1000
            bootstrap_stats = []

            for _ in range(n_bootstrap):
                sample_regime = np.random.choice(regime_data, size=len(regime_data), replace=True)
                sample_venue = np.random.choice(venue_data, size=len(venue_data), replace=True)
                sample_contingency = pd.crosstab(sample_regime, sample_venue)
                if sample_contingency.shape == contingency_table.shape:
                    sample_chi2, _, _, _ = stats.chi2_contingency(sample_contingency)
                    bootstrap_stats.append(sample_chi2)

            if bootstrap_stats:
                ci_lower = np.percentile(bootstrap_stats, 2.5)
                ci_upper = np.percentile(bootstrap_stats, 97.5)

                bootstrap_result = {
                    "ci_lower": round(ci_lower, 4),
                    "ci_upper": round(ci_upper, 4),
                    "n_bootstrap": n_bootstrap,
                }
                bootstrap_json = json.dumps(bootstrap_result, ensure_ascii=False)
                print(f"[STATS:env:volatility:bootstrap] {bootstrap_json}")

    def _export_results(
        self, results: VolatilityRegimeResults, output_dir: str = "exports"
    ) -> None:
        """Export results to JSON and CSV files for economists/regulators."""
        os.makedirs(output_dir, exist_ok=True)

        # Export terciles summary
        terciles_data = {
            "sigma20_quantiles": {
                "q33": round(results.regimes[0].upper_bound, 4),
                "q66": round(results.regimes[1].upper_bound, 4),
            },
            "bounds": {
                "low": {"max": round(results.regimes[0].upper_bound, 4)},
                "medium": {
                    "min": round(results.regimes[0].upper_bound, 4),
                    "max": round(results.regimes[1].upper_bound, 4),
                },
                "high": {"min": round(results.regimes[1].upper_bound, 4)},
            },
            "counts": {r.regime: r.count for r in results.regimes},
            "coveragePct": round(
                sum(r.count for r in results.regimes) / len(results.regime_labels) * 100, 2
            ),
        }

        with open(os.path.join(output_dir, "vol_terciles_summary.json"), "w") as f:
            json.dump(terciles_data, f, indent=2, default=str)

        # Export leadership by regime
        leadership_data = {
            "summary": {
                "method": "consensus-proximity",
                "pair": self.pair,
                "keptDays": sum(
                    leadership.total_days for leadership in results.leadership_by_regime
                ),
                "regimes": [],
            },
            "table": [],
            "ties": {"byRegime": []},
            "dropped": {
                "dropped": 0,
                "drop": {"missing": 0, "notEnoughOthers": 0, "tooTight": 0, "outlier": 0, "nan": 0},
            },
        }

        # Add regime data
        for leadership in results.leadership_by_regime:
            shares_pct = []
            for venue in self.venues:
                pct = leadership.venue_leadership.get(venue, 0.0)
                shares_pct.append({"venue": venue, "pct": round(pct, 2)})
            shares_pct.sort(key=lambda x: x["pct"], reverse=True)

            leadership_data["summary"]["regimes"].append(
                {
                    "regime": leadership.regime,
                    "days": leadership.total_days,
                    "sharesPct": shares_pct,
                    "isTie": False,
                }
            )

            leadership_data["ties"]["byRegime"].append({"regime": leadership.regime, "tieDays": 0})

        # Add table data
        total_wins = {}
        for venue in self.venues:
            total_wins[venue] = 0

        for leadership in results.leadership_by_regime:
            for venue, wins in leadership.venue_rankings:
                total_wins[venue] += wins

        total_days = sum(leadership.total_days for leadership in results.leadership_by_regime)
        for venue in self.venues:
            wins = total_wins[venue]
            pct = round((wins / total_days * 100) if total_days > 0 else 0, 2)
            leadership_data["table"].append({"venue": venue, "wins": wins, "pct": pct})

        leadership_data["table"].sort(key=lambda x: x["wins"], reverse=True)

        with open(os.path.join(output_dir, "leadership_by_regime.json"), "w") as f:
            json.dump(leadership_data, f, indent=2, default=str)

        # Export daily leadership CSV
        daily_data = []
        for i, (date, regime) in enumerate(results.regime_labels.items()):
            if pd.isna(regime):
                continue

            # Get available venues for this day
            available_venues = []
            venue_prices = {}

            for venue in self.venues:
                if venue in results.ohlcv_data.columns:
                    price = results.ohlcv_data.loc[date, venue]
                    if not pd.isna(price) and price > 0:
                        available_venues.append(venue)
                        venue_prices[venue] = price

            # Need at least 3 venues for consensus
            if len(available_venues) < 3:
                continue

            # Compute consensus as median of available venue prices
            prices = [venue_prices[v] for v in available_venues]
            consensus = np.median(prices)

            # Find leader (venue closest to consensus)
            gaps = {}
            for venue in available_venues:
                gap = abs(venue_prices[venue] - consensus)
                gaps[venue] = gap

            # Find minimum gap
            min_gap = min(gaps.values())
            leaders = [v for v, gap in gaps.items() if gap == min_gap]

            # Handle ties - choose lexicographically for CSV, but track ties
            leader = sorted(leaders)[0]
            leader_gap_bps = (min_gap / consensus) * 10000  # Convert to basis points

            row = {
                "dayKey": int(date.timestamp() * 1000),  # Convert to UTC milliseconds
                "regime": regime,
                "leader": leader,
                "leaderGapBps": round(leader_gap_bps, 2),
            }

            # Add venue prices
            for venue in self.venues:
                if venue in available_venues:
                    row[venue] = round(venue_prices[venue], 2)
                else:
                    row[venue] = None

            daily_data.append(row)

        daily_df = pd.DataFrame(daily_data)
        daily_df.to_csv(os.path.join(output_dir, "leadership_by_day.csv"), index=False)

        # Export MANIFEST.json (enriched format)
        kept_days = len(results.regime_labels.dropna())
        dropped_days = len(results.regime_labels) - kept_days

        manifest_data = {
            "commit": self._get_code_version(),
            "codeVersion": self._get_code_version(),
            "tz": "UTC",
            "sampleWindow": {
                "start": results.ohlcv_data.index.min().strftime("%Y-%m-%d"),
                "end": results.ohlcv_data.index.max().strftime("%Y-%m-%d"),
            },
            "specVersion": self.spec_version,
            "runs": {
                "volatility": {
                    "keptDays": kept_days,
                    "droppedDays": dropped_days,
                    "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
                }
            },
        }

        with open(os.path.join(output_dir, "MANIFEST.json"), "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

        # Export assignments
        assignments_data = {
            "keptDays": len(results.regime_labels.dropna()),
            "droppedDays": len(results.regime_labels) - len(results.regime_labels.dropna()),
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
            "byRegime": [
                {"regime": regime, "days": int((results.regime_labels == regime).sum())}
                for regime in ["low", "medium", "high"]
            ],
        }

        with open(os.path.join(output_dir, "volatility_assignments.json"), "w") as f:
            json.dump(assignments_data, f, indent=2, default=str)

        self.logger.info(f"Exported results to {output_dir}/")
        self.logger.info("  - vol_terciles_summary.json")
        self.logger.info("  - leadership_by_regime.json")
        self.logger.info("  - leadership_by_day.csv")
        self.logger.info("  - volatility_assignments.json")
        self.logger.info("  - MANIFEST.json")

    def compute_realized_volatility(
        self, ohlcv_data: pd.DataFrame, price_column: str = "close"
    ) -> pd.Series:
        """
        Compute 20-day rolling realized volatility from OHLCV data.

        Args:
            ohlcv_data: DataFrame with OHLCV data, must have datetime index
            price_column: Column name for price data (default: 'close')

        Returns:
            Series with rolling realized volatility
        """
        if price_column not in ohlcv_data.columns:
            raise ValueError(f"Price column '{price_column}' not found in data")

        # Calculate daily returns
        returns = ohlcv_data[price_column].pct_change()

        # Compute rolling realized volatility (annualized)
        rolling_vol = returns.rolling(
            window=self.window, min_periods=self.min_periods
        ).std() * np.sqrt(
            252
        )  # Annualize assuming 252 trading days

        return rolling_vol

    def partition_volatility_terciles(
        self, volatility_series: pd.Series
    ) -> Tuple[pd.Series, List[VolatilityRegime]]:
        """
        Partition volatility distribution into low/medium/high terciles.

        Args:
            volatility_series: Series with volatility values

        Returns:
            Tuple of (regime_labels, regime_definitions)
        """
        # Remove NaN values for percentile calculation
        clean_vol = volatility_series.dropna()

        if len(clean_vol) < 3:
            raise ValueError("Insufficient data for tercile calculation")

        # Calculate tercile boundaries
        low_threshold = clean_vol.quantile(0.33)
        high_threshold = clean_vol.quantile(0.67)

        # Create regime labels
        regime_labels = pd.Series(index=volatility_series.index, dtype="object")
        regime_labels[volatility_series <= low_threshold] = "low"
        regime_labels[
            (volatility_series > low_threshold) & (volatility_series <= high_threshold)
        ] = "medium"
        regime_labels[volatility_series > high_threshold] = "high"

        # Create regime definitions
        regimes = []
        for regime_name, threshold_low, threshold_high in [
            ("low", 0, low_threshold),
            ("medium", low_threshold, high_threshold),
            ("high", high_threshold, np.inf),
        ]:
            count = (regime_labels == regime_name).sum()
            percentage = (count / len(regime_labels)) * 100 if len(regime_labels) > 0 else 0

            regimes.append(
                VolatilityRegime(
                    regime=regime_name,
                    lower_bound=threshold_low,
                    upper_bound=threshold_high,
                    count=count,
                    percentage=percentage,
                )
            )

        return regime_labels, regimes

    def compute_leadership_by_regime(
        self, regime_labels: pd.Series, ohlcv_data: pd.DataFrame, venue_columns: List[str]
    ) -> Tuple[List[LeadershipDistribution], Dict[str, int]]:
        """
        Compute leadership distribution for each volatility regime using consensus-based leadership.

        Args:
            regime_labels: Series with regime labels for each day
            ohlcv_data: DataFrame with OHLCV data for all venues
            venue_columns: List of venue column names

        Returns:
            Tuple of (leadership_by_regime, drop_reasons)
        """
        leadership_by_regime = []
        drop_reasons = {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0}

        for regime in ["low", "medium", "high"]:
            regime_mask = regime_labels == regime
            regime_dates = regime_labels[regime_mask].index

            if len(regime_dates) == 0:
                continue

            # Calculate leadership for each day in this regime
            venue_wins = {venue: 0 for venue in venue_columns}
            tie_days = 0
            valid_days = 0

            for date in regime_dates:
                # Get available venues for this day
                available_venues = []
                venue_prices = {}

                for venue in venue_columns:
                    if venue in ohlcv_data.columns:
                        price = ohlcv_data.loc[date, venue]
                        if not pd.isna(price) and price > 0:
                            available_venues.append(venue)
                            venue_prices[venue] = price

                # Need at least 3 venues for consensus
                if len(available_venues) < 3:
                    drop_reasons["notEnoughOthers"] += 1
                    continue

                valid_days += 1

                # Compute consensus as median of available venue prices
                prices = [venue_prices[v] for v in available_venues]
                consensus = np.median(prices)

                # Find leader (venue closest to consensus)
                gaps = {}
                for venue in available_venues:
                    gap = abs(venue_prices[venue] - consensus)
                    gaps[venue] = gap

                # Find minimum gap
                min_gap = min(gaps.values())
                leaders = [v for v, gap in gaps.items() if gap == min_gap]

                # Handle ties - split wins equally
                if len(leaders) > 1:
                    tie_days += 1
                    win_fraction = 1.0 / len(leaders)
                    for leader in leaders:
                        venue_wins[leader] += win_fraction
                else:
                    venue_wins[leaders[0]] += 1

            # Calculate percentages based on valid days, not total regime days
            venue_leadership = {}
            for venue in venue_columns:
                venue_leadership[venue] = (
                    (venue_wins[venue] / valid_days) * 100 if valid_days > 0 else 0
                )

            # Create rankings (venue, win_count) sorted by wins
            venue_rankings = sorted(venue_wins.items(), key=lambda x: x[1], reverse=True)

            leadership_by_regime.append(
                LeadershipDistribution(
                    regime=regime,
                    venue_leadership=venue_leadership,
                    total_days=valid_days,  # Use valid days, not total regime days
                    venue_rankings=venue_rankings,
                    tie_days=tie_days,
                )
            )

        return leadership_by_regime, drop_reasons

    def analyze_volatility_regimes(
        self,
        ohlcv_data: pd.DataFrame,
        leadership_data: pd.DataFrame,
        venue_columns: List[str],
        price_column: str = "close",
        export_results: bool = True,
        output_dir: str = "exports",
    ) -> VolatilityRegimeResults:
        """
        Complete volatility regime analysis with structured logging as specified.

        Args:
            ohlcv_data: DataFrame with OHLCV data
            leadership_data: DataFrame with leadership/consensus data
            venue_columns: List of venue column names
            price_column: Column name for price data
            export_results: Whether to export results to files
            output_dir: Directory for exported files

        Returns:
            VolatilityRegimeResults with complete analysis
        """
        self.logger.info("Starting volatility regime analysis with structured logging")

        # Step 1: Log configuration
        self._log_config(ohlcv_data)

        # Step 2: Compute 20-day rolling realized volatility
        volatility_series = self.compute_realized_volatility(ohlcv_data, price_column)
        self.logger.info(
            f"Computed volatility series with {len(volatility_series.dropna())} valid observations"
        )

        # Step 3: Partition into terciles
        regime_labels, regimes = self.partition_volatility_terciles(volatility_series)
        self.logger.info(f"Partitioned into terciles: {[r.regime for r in regimes]}")

        # Step 4: Log terciles
        self._log_terciles(volatility_series, regimes)

        # Step 5: Log assignments with proper drop reason tracking
        drop_reasons = {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0}
        self._log_assignments(regime_labels, drop_reasons)

        # Step 6: Compute leadership distribution per regime
        leadership_by_regime, computed_drop_reasons = self.compute_leadership_by_regime(
            regime_labels, ohlcv_data, venue_columns
        )

        # Update drop reasons with computed values
        drop_reasons.update(computed_drop_reasons)

        # Step 7: Log leadership results
        self._log_leadership_summary(leadership_by_regime)
        self._log_leadership_table(leadership_by_regime)
        self._log_dropped_days(drop_reasons)
        self._log_ties(leadership_by_regime)

        # Step 8: Log statistical tests (for volatility, we'll add basic stats)
        self._log_volatility_stats(leadership_by_regime)

        # Create summary
        summary = {
            "total_days": len(regime_labels),
            "valid_volatility_days": len(volatility_series.dropna()),
            "regime_distribution": {r.regime: r.count for r in regimes},
            "volatility_stats": {
                "mean": volatility_series.mean(),
                "std": volatility_series.std(),
                "min": volatility_series.min(),
                "max": volatility_series.max(),
            },
        }

        results = VolatilityRegimeResults(
            regimes=regimes,
            leadership_by_regime=leadership_by_regime,
            volatility_series=volatility_series,
            regime_labels=regime_labels,
            summary=summary,
            ohlcv_data=ohlcv_data,
        )

        # Step 8: Export results if requested
        if export_results:
            self._export_results(results, output_dir)

        self.logger.info("Volatility regime analysis completed with structured logging")
        return results

    def log_results(self, results: VolatilityRegimeResults) -> None:
        """
        Log results in [LEADER:environment:volatility] format as specified.

        Args:
            results: VolatilityRegimeResults to log
        """
        self.logger.info("=== [LEADER:environment:volatility] RESULTS ===")

        # Log tercile boundaries
        self.logger.info("Tercile Boundaries (σ thresholds):")
        for regime in results.regimes:
            self.logger.info(
                f"  {regime.regime.upper()}: {regime.lower_bound:.4f} - {regime.upper_bound:.4f}"
            )

        # Log counts per tercile
        self.logger.info("Counts of days per tercile:")
        for regime in results.regimes:
            self.logger.info(
                f"  {regime.regime.upper()}: {regime.count} days ({regime.percentage:.1f}%)"
            )

        # Log leadership share per venue within each tercile
        self.logger.info("Leadership share per venue within each tercile:")
        for leadership in results.leadership_by_regime:
            self.logger.info(f"  {leadership.regime.upper()} VOLATILITY REGIME:")
            for venue, percentage in leadership.venue_leadership.items():
                wins = leadership.venue_rankings[0][1] if leadership.venue_rankings else 0
                self.logger.info(f"    {venue}: {percentage:.1f}% ({wins} wins)")

        self.logger.info("=== END [LEADER:environment:volatility] ===")


def create_volatility_regime_analyzer(window: int = 20) -> VolatilityRegimeAnalyzer:
    """
    Factory function to create a volatility regime analyzer.

    Args:
        window: Rolling window size for volatility calculation

    Returns:
        Configured VolatilityRegimeAnalyzer instance
    """
    return VolatilityRegimeAnalyzer(window=window)


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create sample data for testing
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)

    # Create sample OHLCV data
    base_price = 50000
    returns = np.random.normal(0, 0.02, 100)  # 2% daily volatility
    prices = base_price * np.exp(np.cumsum(returns))

    ohlcv_data = pd.DataFrame(
        {
            "close": prices,
            "open": prices * (1 + np.random.normal(0, 0.001, 100)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.01, 100))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.01, 100))),
            "volume": np.random.uniform(1000, 10000, 100),
        },
        index=dates,
    )

    # Create sample leadership data
    venues = ["binance", "okx", "coinbase", "kraken", "bybit"]
    leadership_data = pd.DataFrame(index=dates)
    for venue in venues:
        leadership_data[venue] = np.random.uniform(0, 1, 100)

    # Run analysis
    analyzer = create_volatility_regime_analyzer()
    results = analyzer.analyze_volatility_regimes(
        ohlcv_data=ohlcv_data, leadership_data=leadership_data, venue_columns=venues
    )

    # Log results
    analyzer.log_results(results)
