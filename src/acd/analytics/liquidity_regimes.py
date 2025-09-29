"""
Liquidity Regime Analysis Module

This module implements liquidity regime analysis using a composite metric
combining volume, true range, and volatility-adjusted returns.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import scipy.stats as stats


@dataclass
class LiquidityRegimeResult:
    """Result container for liquidity regime analysis."""

    regime_assignments: pd.DataFrame
    liquidity_terciles: Dict[str, float]
    leadership_by_regime: List[Dict[str, Any]]
    daily_leadership: pd.DataFrame
    stats_results: Dict[str, Any]


@dataclass
class LeadershipDistribution:
    """Leadership distribution for a specific regime."""

    regime: str
    venue_leadership: Dict[str, float]
    total_days: int
    venue_rankings: List[Tuple[str, float]]
    tie_days: int


class LiquidityRegimeAnalyzer:
    """
    Analyzes liquidity regimes using composite metrics.

    The composite metric combines:
    - z-score(volumeUSD)
    - z-score(trueRange/close)
    - z-score(|return|/σ20)
    """

    def __init__(self, spec_version: str = "1.0.0"):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]

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

    def compute_liquidity_terciles(
        self, liquidity_data: pd.DataFrame
    ) -> Tuple[Dict[str, float], pd.DataFrame]:
        """
        Compute liquidity terciles and regime assignments.

        Args:
            liquidity_data: DataFrame with columns [dayUTC, venue, volumeUSD,
                                                   trueRange, close, return, sigma20]

        Returns:
            Tuple of (terciles_dict, regime_assignments_df)
        """
        # Calculate composite metric for each day
        daily_metrics = []

        for date in liquidity_data["dayUTC"].unique():
            day_data = liquidity_data[liquidity_data["dayUTC"] == date]

            # Need at least 3 venues for meaningful analysis
            if len(day_data) < 3:
                continue

            # Calculate composite metric components
            volume_z = stats.zscore(day_data["volumeUSD"])
            range_z = stats.zscore(day_data["trueRange"] / day_data["close"])
            return_z = stats.zscore(np.abs(day_data["return"]) / day_data["sigma20"])

            # Composite metric (equal weights)
            composite = volume_z + range_z + return_z

            # Use median composite as daily liquidity measure
            daily_liquidity = np.median(composite)
            daily_metrics.append({"date": pd.Timestamp(date), "liquidity": daily_liquidity})

        if not daily_metrics:
            raise ValueError("Insufficient data for liquidity analysis")

        metrics_df = pd.DataFrame(daily_metrics)
        metrics_df.set_index("date", inplace=True)

        # Calculate terciles
        q33 = metrics_df["liquidity"].quantile(0.33)
        q66 = metrics_df["liquidity"].quantile(0.66)

        terciles = {"q33": float(q33), "q66": float(q66)}

        # Assign regimes
        regime_assignments = []
        for date, row in metrics_df.iterrows():
            liquidity = row["liquidity"]
            if liquidity <= q33:
                regime = "low"
            elif liquidity <= q66:
                regime = "medium"
            else:
                regime = "high"

            regime_assignments.append({"date": date, "liquidity": liquidity, "regime": regime})

        regime_df = pd.DataFrame(regime_assignments)
        regime_df.set_index("date", inplace=True)

        return terciles, regime_df

    def compute_leadership_by_regime(
        self, regime_assignments: pd.DataFrame, leadership_data: pd.DataFrame
    ) -> Tuple[List[LeadershipDistribution], Dict[str, int]]:
        """
        Compute leadership distribution by liquidity regime using consensus-based leadership.

        Args:
            regime_assignments: DataFrame with regime assignments
            leadership_data: DataFrame with daily leadership data

        Returns:
            Tuple of (leadership_by_regime, drop_reasons)
        """
        leadership_by_regime = []
        drop_reasons = {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0}

        # Get venue columns from leadership data
        venue_columns = [
            col
            for col in leadership_data.columns
            if col not in ["dayKey", "regime", "leader", "leaderGapBps"]
        ]

        for regime in ["low", "medium", "high"]:
            regime_mask = regime_assignments["regime"] == regime
            regime_dates = regime_assignments[regime_mask].index

            if len(regime_dates) == 0:
                continue

            venue_wins = {venue: 0 for venue in venue_columns}
            tie_days = 0
            valid_days = 0

            for date in regime_dates:
                # Convert date to string format to match leadership data index
                date_str = (
                    date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
                )

                if date_str not in leadership_data.index:
                    drop_reasons["missing"] += 1
                    continue

                day_data = leadership_data.loc[date_str]
                available_venues = []
                venue_prices = {}

                for venue in venue_columns:
                    if venue in day_data and not pd.isna(day_data[venue]) and day_data[venue] > 0:
                        available_venues.append(venue)
                        venue_prices[venue] = day_data[venue]

                if len(available_venues) < 3:
                    drop_reasons["notEnoughOthers"] += 1
                    continue

                valid_days += 1

                # Calculate consensus (median of available prices)
                prices = [venue_prices[v] for v in available_venues]
                consensus = np.median(prices)

                # Find leader (closest to consensus)
                gaps = {}
                for venue in available_venues:
                    gap = abs(venue_prices[venue] - consensus)
                    gaps[venue] = gap

                min_gap = min(gaps.values())
                leaders = [v for v, gap in gaps.items() if gap == min_gap]

                if len(leaders) > 1:
                    tie_days += 1
                    win_fraction = 1.0 / len(leaders)
                    for leader in leaders:
                        venue_wins[leader] += win_fraction
                else:
                    venue_wins[leaders[0]] += 1

            # Calculate percentages
            venue_leadership = {}
            for venue in venue_columns:
                venue_leadership[venue] = (
                    (venue_wins[venue] / valid_days) * 100 if valid_days > 0 else 0
                )

            venue_rankings = sorted(venue_wins.items(), key=lambda x: x[1], reverse=True)

            leadership_by_regime.append(
                LeadershipDistribution(
                    regime=regime,
                    venue_leadership=venue_leadership,
                    total_days=valid_days,
                    venue_rankings=venue_rankings,
                    tie_days=tie_days,
                )
            )

        return leadership_by_regime, drop_reasons

    def compute_statistical_tests(
        self, regime_assignments: pd.DataFrame, leadership_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Compute statistical tests for liquidity-leadership relationship."""
        # Prepare contingency table
        regime_data = []
        venue_data = []

        for date in regime_assignments.index:
            # Convert date to string format to match leadership data index
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]

            if date_str not in leadership_data.index:
                continue

            regime = regime_assignments.loc[date, "regime"]
            day_data = leadership_data.loc[date_str]

            # Get available venues for this day
            venue_columns = [
                col
                for col in leadership_data.columns
                if col not in ["dayKey", "regime", "leader", "leaderGapBps"]
            ]
            available_venues = []
            for venue in venue_columns:
                if venue in day_data and not pd.isna(day_data[venue]) and day_data[venue] > 0:
                    available_venues.append(venue)

            if len(available_venues) < 3:
                continue

            # Calculate consensus and find leader
            prices = [day_data[v] for v in available_venues]
            consensus = np.median(prices)

            gaps = {venue: abs(day_data[venue] - consensus) for venue in available_venues}
            min_gap = min(gaps.values())
            leaders = [v for v, gap in gaps.items() if gap == min_gap]

            # Use lexicographic winner for ties
            leader = min(leaders) if leaders else available_venues[0]

            regime_data.append(regime)
            venue_data.append(leader)

        if len(regime_data) == 0:
            return {}

        # Create contingency table
        contingency_table = pd.crosstab(regime_data, venue_data)

        if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
            return {}

        # Chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

        # Cramér's V
        n = contingency_table.sum().sum()
        cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))

        # Bootstrap confidence intervals
        n_bootstrap = 1000
        bootstrap_stats = []

        for _ in range(n_bootstrap):
            sample_regime = np.random.choice(regime_data, size=len(regime_data), replace=True)
            sample_venue = np.random.choice(venue_data, size=len(venue_data), replace=True)
            sample_contingency = pd.crosstab(sample_regime, sample_venue)
            if sample_contingency.shape == contingency_table.shape:
                sample_chi2, _, _, _ = stats.chi2_contingency(sample_contingency)
                bootstrap_stats.append(sample_chi2)

        ci_lower = np.percentile(bootstrap_stats, 2.5) if bootstrap_stats else 0
        ci_upper = np.percentile(bootstrap_stats, 97.5) if bootstrap_stats else 0

        return {
            "chi2": {
                "chi2_statistic": round(chi2, 4),
                "p_value": round(p_value, 6),
                "degrees_of_freedom": int(dof),
                "expected_frequencies": expected.tolist(),
            },
            "cramers_v": {
                "cramers_v": round(cramers_v, 4),
                "interpretation": (
                    "small" if cramers_v < 0.1 else "medium" if cramers_v < 0.3 else "large"
                ),
            },
            "bootstrap_ci": {
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "n_bootstrap": n_bootstrap,
            },
        }

    def _log_terciles(self, terciles: Dict[str, float], counts: Dict[str, int]) -> None:
        """Log liquidity terciles information."""
        terciles_data = {
            "liquidity_quantiles": terciles,
            "bounds": {
                "low": {"max": terciles["q33"]},
                "medium": {"min": terciles["q33"], "max": terciles["q66"]},
                "high": {"min": terciles["q66"]},
            },
            "counts": counts,
            "coveragePct": 100.0,
        }
        self.logger.info(
            f"[ENV:liquidity:terciles] {json.dumps(terciles_data, indent=2, default=str)}"
        )

    def _log_assignments(self, regime_assignments: pd.DataFrame) -> None:
        """Log regime assignments summary."""
        kept_days = len(regime_assignments)
        dropped_days = 0  # No dropped days for liquidity analysis

        by_regime = []
        for regime in ["low", "medium", "high"]:
            count = (regime_assignments["regime"] == regime).sum()
            by_regime.append({"regime": regime, "days": int(count)})

        assignments = {
            "keptDays": int(kept_days),
            "droppedDays": int(dropped_days),
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
            "byRegime": by_regime,
        }
        self.logger.info(
            f"[ENV:liquidity:assignments] {json.dumps(assignments, indent=2, default=str)}"
        )

    def _log_leadership_summary(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log leadership summary by regime."""
        kept_days = sum(ld.total_days for ld in leadership_by_regime)

        regimes = []
        for leadership in leadership_by_regime:
            shares_pct = [
                {"venue": venue, "pct": round(pct, 2)}
                for venue, pct in leadership.venue_leadership.items()
            ]
            regimes.append(
                {
                    "regime": leadership.regime,
                    "days": leadership.total_days,
                    "sharesPct": shares_pct,
                    "isTie": leadership.tie_days > 0,
                }
            )

        summary = {
            "method": "consensus-proximity",
            "pair": "BTC-USD",
            "keptDays": kept_days,
            "regimes": regimes,
        }
        self.logger.info(
            f"[LEADER:env:liquidity:summary] {json.dumps(summary, indent=2, default=str)}"
        )

    def _log_leadership_table(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log full leadership ranking table."""
        # Aggregate across all regimes
        total_wins = {}
        total_days = 0

        for leadership in leadership_by_regime:
            total_days += leadership.total_days
            for venue, wins in leadership.venue_rankings:
                total_wins[venue] = total_wins.get(venue, 0) + wins

        table = []
        for venue, wins in sorted(total_wins.items(), key=lambda x: x[1], reverse=True):
            pct = (wins / total_days) * 100 if total_days > 0 else 0
            table.append({"venue": venue, "wins": int(wins), "pct": round(pct, 2)})

        table_data = {"keptDays": total_days, "table": table}
        self.logger.info(
            f"[LEADER:env:liquidity:table] {json.dumps(table_data, indent=2, default=str)}"
        )

    def _log_dropped_days(self, drop_reasons: Dict[str, int]) -> None:
        """Log dropped day statistics."""
        dropped_data = {"dropped": sum(drop_reasons.values()), "drop": drop_reasons}
        self.logger.info(
            f"[LEADER:env:liquidity:dropped] {json.dumps(dropped_data, indent=2, default=str)}"
        )

    def _log_ties(self, leadership_by_regime: List[LeadershipDistribution]) -> None:
        """Log tie day statistics by regime."""
        ties_data = []
        for leadership in leadership_by_regime:
            ties_data.append({"regime": leadership.regime, "tieDays": leadership.tie_days})

        ties_info = {"byRegime": ties_data}
        self.logger.info(
            f"[LEADER:env:liquidity:ties] {json.dumps(ties_info, indent=2, default=str)}"
        )

    def _log_stats(self, stats_results: Dict[str, Any]) -> None:
        """Log statistical test results."""
        for test_name, results in stats_results.items():
            self.logger.info(
                f"[STATS:env:liquidity:{test_name}] {json.dumps(results, indent=2, default=str)}"
            )

    def _log_liquidity_stats_exact(self, stats_results: Dict[str, Any]) -> None:
        """Log exact liquidity stats tags for grep."""
        if "chi2" in stats_results:
            chi2_json = json.dumps(stats_results["chi2"], ensure_ascii=False)
            print(f"[STATS:env:liquidity:chi2] {chi2_json}")
        if "cramers_v" in stats_results:
            cramers_json = json.dumps(stats_results["cramers_v"], ensure_ascii=False)
            print(f"[STATS:env:liquidity:cramers_v] {cramers_json}")
        if "bootstrap_ci" in stats_results:
            bootstrap_json = json.dumps(stats_results["bootstrap_ci"], ensure_ascii=False)
            print(f"[STATS:env:liquidity:bootstrap] {bootstrap_json}")

    def _export_results(self, results: LiquidityRegimeResult, output_dir: str = "exports") -> None:
        """Export results to machine-readable files."""
        os.makedirs(output_dir, exist_ok=True)

        # Export terciles summary
        terciles_data = {
            "liquidity_quantiles": results.liquidity_terciles,
            "bounds": {
                "low": {"max": results.liquidity_terciles["q33"]},
                "medium": {
                    "min": results.liquidity_terciles["q33"],
                    "max": results.liquidity_terciles["q66"],
                },
                "high": {"min": results.liquidity_terciles["q66"]},
            },
            "counts": {
                regime: int((results.regime_assignments["regime"] == regime).sum())
                for regime in ["low", "medium", "high"]
            },
            "coveragePct": 100.0,
        }

        with open(os.path.join(output_dir, "liquidity_terciles_summary.json"), "w") as f:
            json.dump(terciles_data, f, indent=2, default=str)

        # Export leadership by regime
        leadership_data = {
            "summary": {
                "method": "consensus-proximity",
                "pair": "BTC-USD",
                "keptDays": len(results.regime_assignments),
                "regimes": [
                    {
                        "regime": leadership.regime,
                        "days": leadership.total_days,
                        "sharesPct": [
                            {"venue": venue, "pct": round(pct, 2)}
                            for venue, pct in leadership.venue_leadership.items()
                        ],
                        "isTie": leadership.tie_days > 0,
                    }
                    for leadership in results.leadership_by_regime
                ],
            },
            "stats": results.stats_results,
        }

        with open(os.path.join(output_dir, "leadership_by_liquidity.json"), "w") as f:
            json.dump(leadership_data, f, indent=2, default=str)

        # Export daily leadership CSV
        daily_data = []
        for date, row in results.daily_leadership.iterrows():
            # Handle date formatting
            if hasattr(date, "strftime"):
                date_str = date.strftime("%Y-%m-%d")
            else:
                date_str = str(date)[:10]  # Take first 10 chars for YYYY-MM-DD

            # Get regime for this date
            regime = "unknown"
            if date in results.regime_assignments.index:
                regime = results.regime_assignments.loc[date, "regime"]

            daily_row = {
                "dayKey": date_str,
                "regime": regime,
                "leader": row.get("leader", ""),
                "leaderGapBps": row.get("leaderGapBps", 0),
            }

            # Add venue columns
            venue_columns = [
                col
                for col in results.daily_leadership.columns
                if col not in ["leader", "leaderGapBps"]
            ]
            for venue in venue_columns:
                daily_row[venue] = row.get(venue, 0)

            daily_data.append(daily_row)

        daily_df = pd.DataFrame(daily_data)
        daily_df.to_csv(os.path.join(output_dir, "leadership_by_day_liquidity.csv"), index=False)

        # Export MANIFEST.json (enriched format) - merge with existing
        kept_days = len(results.regime_assignments)
        dropped_days = 0

        # Try to read existing MANIFEST.json to preserve other run data
        manifest_path = os.path.join(output_dir, "MANIFEST.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
        else:
            # Get date range from regime assignments
            start_date = results.regime_assignments.index.min()
            end_date = results.regime_assignments.index.max()

            # Handle both datetime and string dates
            if hasattr(start_date, "strftime"):
                start_str = start_date.strftime("%Y-%m-%d")
            else:
                start_str = str(start_date)[:10]  # Take first 10 chars for YYYY-MM-DD

            if hasattr(end_date, "strftime"):
                end_str = end_date.strftime("%Y-%m-%d")
            else:
                end_str = str(end_date)[:10]  # Take first 10 chars for YYYY-MM-DD

            manifest_data = {
                "commit": self._get_code_version(),
                "codeVersion": self._get_code_version(),
                "tz": "UTC",
                "sampleWindow": {"start": start_str, "end": end_str},
                "specVersion": self.spec_version,
                "runs": {},
            }

        # Add/update liquidity run data
        manifest_data["runs"]["liquidity"] = {
            "keptDays": kept_days,
            "droppedDays": dropped_days,
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

        # Export liquidity assignments
        liquidity_assignments_data = {
            "keptDays": len(results.regime_assignments),
            "droppedDays": 0,
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
            "byRegime": [
                {
                    "regime": regime,
                    "days": int((results.regime_assignments["regime"] == regime).sum()),
                }
                for regime in ["low", "medium", "high"]
            ],
        }

        with open(os.path.join(output_dir, "liquidity_assignments.json"), "w") as f:
            json.dump(liquidity_assignments_data, f, indent=2, default=str)

        self.logger.info(f"Exported results to {output_dir}/")
        self.logger.info("  - liquidity_terciles_summary.json")
        self.logger.info("  - leadership_by_liquidity.json")
        self.logger.info("  - leadership_by_day_liquidity.csv")
        self.logger.info("  - liquidity_assignments.json")
        self.logger.info("  - MANIFEST.json")

    def analyze_liquidity_regimes(
        self, liquidity_data: pd.DataFrame, leadership_data: pd.DataFrame
    ) -> LiquidityRegimeResult:
        """
        Run complete liquidity regime analysis.

        Args:
            liquidity_data: DataFrame with liquidity metrics
            leadership_data: DataFrame with daily leadership data

        Returns:
            LiquidityRegimeResult with all analysis results
        """
        self.logger.info("Starting liquidity regime analysis with structured logging")

        # Step 1: Compute liquidity terciles
        terciles, regime_assignments = self.compute_liquidity_terciles(liquidity_data)

        # Step 2: Log terciles
        counts = regime_assignments["regime"].value_counts().to_dict()
        self._log_terciles(terciles, counts)
        self._log_assignments(regime_assignments)

        # Step 3: Compute leadership by regime
        leadership_by_regime, drop_reasons = self.compute_leadership_by_regime(
            regime_assignments, leadership_data
        )

        # Step 4: Log leadership results
        self._log_leadership_summary(leadership_by_regime)
        self._log_leadership_table(leadership_by_regime)
        self._log_dropped_days(drop_reasons)
        self._log_ties(leadership_by_regime)

        # Step 5: Compute statistical tests
        stats_results = self.compute_statistical_tests(regime_assignments, leadership_data)
        self._log_stats(stats_results)

        # Log exact tags for grep
        self._log_liquidity_stats_exact(stats_results)

        # Step 6: Create daily leadership DataFrame with computed leaders
        daily_leadership = leadership_data.copy()

        # Compute daily leaders for the daily leadership DataFrame
        for date in daily_leadership.index:
            day_data = daily_leadership.loc[date]
            available_venues = []
            venue_prices = {}

            for venue in self.venues:
                if venue in day_data and not pd.isna(day_data[venue]) and day_data[venue] > 0:
                    available_venues.append(venue)
                    venue_prices[venue] = day_data[venue]

            if len(available_venues) >= 3:
                # Calculate consensus (median of available prices)
                prices = [venue_prices[v] for v in available_venues]
                consensus = np.median(prices)

                # Find leader (closest to consensus)
                gaps = {}
                for venue in available_venues:
                    gap = abs(venue_prices[venue] - consensus)
                    gaps[venue] = gap

                min_gap = min(gaps.values())
                leaders = [v for v, gap in gaps.items() if gap == min_gap]

                # Use lexicographic winner for ties
                leader = min(leaders) if leaders else available_venues[0]
                gap_bps = (min_gap / consensus) * 10000 if consensus > 0 else 0

                daily_leadership.loc[date, "leader"] = leader
                daily_leadership.loc[date, "leaderGapBps"] = gap_bps
            else:
                daily_leadership.loc[date, "leader"] = ""
                daily_leadership.loc[date, "leaderGapBps"] = 0

        return LiquidityRegimeResult(
            regime_assignments=regime_assignments,
            liquidity_terciles=terciles,
            leadership_by_regime=leadership_by_regime,
            daily_leadership=daily_leadership,
            stats_results=stats_results,
        )


def create_liquidity_regime_analyzer(spec_version: str = "1.0.0") -> LiquidityRegimeAnalyzer:
    """Create a liquidity regime analyzer instance."""
    return LiquidityRegimeAnalyzer(spec_version=spec_version)
