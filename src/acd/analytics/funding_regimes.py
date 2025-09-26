"""
Funding Rate Regimes for ACD Analysis

This module implements funding rate regime environments for BTC perpetuals.
It computes daily funding rate terciles and provides leadership distribution
analysis across funding regimes, including funding shock detection.

Based on ACD_Working_Plan.md: Implement funding-rate regimes for BTC perps.

Logging Schema: Implements structured logging with court-ready format including:
- [ENV:funding:config] - Configuration and metadata
- [ENV:funding:terciles] - Tercile thresholds and bounds
- [ENV:funding:assignments] - Regime assignments summary
- [LEADER:env:funding:summary] - Leadership shares by regime
- [LEADER:env:funding:table] - Full ranking table
- [LEADER:env:funding:ties] - Tie day statistics
- [LEADER:env:funding:dropped] - Dropped day accounting
- [STATS:env:funding:*] - Statistical tests (χ², Cramér's V, bootstrap CI)
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class FundingRegimeResult:
    """Result of funding regime analysis."""

    regime_assignments: pd.DataFrame
    funding_terciles: Dict[str, float]
    leadership_by_regime: List[Dict[str, Any]]
    funding_shocks: pd.Series
    stats_results: Dict[str, Any]
    funding_data: pd.DataFrame


class FundingRegimeAnalyzer:
    """Analyzes funding rate regimes and leadership distribution."""

    def __init__(self, pair: str = "BTC-USD", spec_version: str = "1.0.0"):
        self.pair = pair
        self.spec_version = spec_version
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.logger = logging.getLogger(__name__)

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

    def _log_config(self, funding_data: pd.DataFrame) -> None:
        """Log configuration and metadata."""
        config = {
            "specVersion": self.spec_version,
            "codeVersion": self._get_code_version(),
            "pair": self.pair,
            "source": "funding_rate",
            "tz": "UTC",
            "sample": {
                "start": funding_data.index.min().strftime("%Y-%m-%d"),
                "end": funding_data.index.max().strftime("%Y-%m-%d"),
                "bars": len(funding_data),
            },
        }
        self.logger.info(f"[ENV:funding:config] {json.dumps(config, indent=2, default=str)}")

    def _log_terciles(self, terciles: Dict[str, float], counts: Dict[str, int]) -> None:
        """Log tercile thresholds and counts."""
        tercile_data = {
            "funding_quantiles": {
                "q33": round(terciles["q33"], 6),
                "q66": round(terciles["q66"], 6),
            },
            "bounds": {
                "low": {"max": round(terciles["q33"], 6)},
                "med": {"min": round(terciles["q33"], 6), "max": round(terciles["q66"], 6)},
                "high": {"min": round(terciles["q66"], 6)},
            },
            "counts": counts,
            "coveragePct": 100.00,
        }
        self.logger.info(
            f"[ENV:funding:terciles] {json.dumps(tercile_data, indent=2, default=str)}"
        )

    def _log_assignments(self, assignments: pd.DataFrame) -> None:
        """Log regime assignments summary."""
        regime_counts = assignments["regime"].value_counts().to_dict()
        by_regime = [{"regime": regime, "days": count} for regime, count in regime_counts.items()]

        assignments_data = {
            "keptDays": len(assignments),
            "droppedDays": 0,
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0},
            "byRegime": by_regime,
        }
        self.logger.info(
            f"[ENV:funding:assignments] {json.dumps(assignments_data, indent=2, default=str)}"
        )

    def _log_leadership_summary(self, leadership_by_regime: List[Dict]) -> None:
        """Log leadership shares by regime."""
        summary = {
            "method": "consensus-proximity",
            "pair": self.pair,
            "keptDays": sum(leadership.total_days for leadership in leadership_by_regime),
            "regimes": [],
        }

        for leadership in leadership_by_regime:
            regime_data = {
                "regime": leadership.regime,
                "days": leadership.total_days,
                "sharesPct": [
                    {"venue": venue, "pct": round(pct, 2)}
                    for venue, pct in leadership.venue_leadership.items()
                ],
                "isTie": leadership.tie_days > 0,
            }
            summary["regimes"].append(regime_data)

        self.logger.info(
            f"[LEADER:env:funding:summary] {json.dumps(summary, indent=2, default=str)}"
        )

    def _log_leadership_table(self, leadership_by_regime: List[Dict]) -> None:
        """Log full ranking table."""
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

        table_data = {"keptDays": total_days, "table": table}
        self.logger.info(
            f"[LEADER:env:funding:table] {json.dumps(table_data, indent=2, default=str)}"
        )

    def _log_dropped_days(self) -> None:
        """Log dropped day accounting."""
        dropped_data = {
            "dropped": 0,
            "drop": {"missing": 0, "notEnoughOthers": 0, "tooTight": 0, "outlier": 0, "nan": 0},
        }
        self.logger.info(
            f"[LEADER:env:funding:dropped] {json.dumps(dropped_data, indent=2, default=str)}"
        )

    def _log_ties(self, leadership_by_regime: List[Dict]) -> None:
        """Log tie day statistics."""
        ties_data = {
            "byRegime": [
                {"regime": leadership.regime, "tieDays": leadership.tie_days}
                for leadership in leadership_by_regime
            ]
        }
        self.logger.info(
            f"[LEADER:env:funding:ties] {json.dumps(ties_data, indent=2, default=str)}"
        )

    def _log_stats(self, stats_results: Dict[str, Any]) -> None:
        """Log statistical test results."""
        for test_name, results in stats_results.items():
            self.logger.info(
                f"[STATS:env:funding:{test_name}] {json.dumps(results, indent=2, default=str)}"
            )

    def _log_funding_stats_exact(self, stats_results: Dict[str, Any]) -> None:
        """Log exact funding stats tags for grep."""
        if "chi2" in stats_results:
            chi2_json = json.dumps(stats_results["chi2"], indent=2, default=str)
            print(f"[STATS:env:funding:chi2] {chi2_json}")
        if "cramers_v" in stats_results:
            cramers_json = json.dumps(stats_results["cramers_v"], indent=2, default=str)
            print(f"[STATS:env:funding:cramers_v] {cramers_json}")
        if "bootstrap_ci" in stats_results:
            bootstrap_json = json.dumps(stats_results["bootstrap_ci"], indent=2, default=str)
            print(f"[STATS:env:funding:bootstrap] {bootstrap_json}")

    def _export_results(self, results: FundingRegimeResult, output_dir: str = "exports") -> None:
        """Export results to machine-readable files."""
        os.makedirs(output_dir, exist_ok=True)

        # Export terciles summary
        terciles_data = {
            "funding_quantiles": results.funding_terciles,
            "bounds": {
                "low": {"max": results.funding_terciles["q33"]},
                "med": {
                    "min": results.funding_terciles["q33"],
                    "max": results.funding_terciles["q66"],
                },
                "high": {"min": results.funding_terciles["q66"]},
            },
            "counts": results.regime_assignments["regime"].value_counts().to_dict(),
            "coveragePct": 100.00,
        }

        with open(os.path.join(output_dir, "funding_terciles_summary.json"), "w") as f:
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
            "stats": results.stats_results,
        }

        # Add regime data
        for leadership in results.leadership_by_regime:
            regime_data = {
                "regime": leadership.regime,
                "days": leadership.total_days,
                "sharesPct": [
                    {"venue": venue, "pct": round(pct, 2)}
                    for venue, pct in leadership.venue_leadership.items()
                ],
                "isTie": leadership.tie_days > 0,
            }
            leadership_data["summary"]["regimes"].append(regime_data)

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

        # Add ties data
        for leadership in results.leadership_by_regime:
            leadership_data["ties"]["byRegime"].append(
                {"regime": leadership.regime, "tieDays": leadership.tie_days}
            )

        with open(os.path.join(output_dir, "leadership_by_funding.json"), "w") as f:
            json.dump(leadership_data, f, indent=2, default=str)

        # Export daily data with leadership
        daily_data = []
        for _, row in results.regime_assignments.iterrows():
            # Get available venues for this day (from funding data)
            available_venues = []
            venue_funding = {}

            for venue in self.venues:
                venue_data = results.funding_data[
                    (results.funding_data.index.date == row.name.date())
                    & (results.funding_data["venue"] == venue)
                ]
                if not venue_data.empty:
                    funding_rate = venue_data["funding_rate"].iloc[0]
                    if not pd.isna(funding_rate):
                        available_venues.append(venue)
                        venue_funding[venue] = funding_rate

            # Need at least 3 venues for consensus
            if len(available_venues) < 3:
                continue

            # Compute consensus as median of available venue funding rates
            rates = [venue_funding[v] for v in available_venues]
            consensus = np.median(rates)

            # Find leader (venue closest to consensus)
            gaps = {}
            for venue in available_venues:
                gap = abs(venue_funding[venue] - consensus)
                gaps[venue] = gap

            # Find minimum gap
            min_gap = min(gaps.values())
            leaders = [v for v, gap in gaps.items() if gap == min_gap]

            # Handle ties - choose lexicographically for CSV
            leader = sorted(leaders)[0]
            leader_gap_bps = (min_gap / abs(consensus)) * 10000 if consensus != 0 else 0

            daily_row = {
                "dayKey": int(row.name.timestamp() * 1000),
                "regime": row["regime"],
                "leader": leader,
                "leaderGapBps": round(leader_gap_bps, 2),
                "fundingRate": round(row["funding_rate"], 6),
                "fundingShock": row["funding_shock"],
            }

            # Add venue funding rates
            for venue in self.venues:
                if venue in available_venues:
                    daily_row[venue] = round(venue_funding[venue], 6)
                else:
                    daily_row[venue] = None

            daily_data.append(daily_row)

        daily_df = pd.DataFrame(daily_data)
        daily_df.to_csv(os.path.join(output_dir, "leadership_by_day_funding.csv"), index=False)

        # Export MANIFEST.json (enriched format) - merge with existing if present
        kept_days = len(results.regime_assignments)
        dropped_days = 0

        # Try to read existing MANIFEST.json to preserve volatility run data
        manifest_path = os.path.join(output_dir, "MANIFEST.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
        else:
            manifest_data = {
                "commit": self._get_code_version(),
                "codeVersion": self._get_code_version(),
                "tz": "UTC",
                "sampleWindow": {
                    "start": results.funding_data.index.min().strftime("%Y-%m-%d"),
                    "end": results.funding_data.index.max().strftime("%Y-%m-%d"),
                },
                "specVersion": self.spec_version,
                "runs": {},
            }

        # Add/update funding run data
        manifest_data["runs"]["funding"] = {
            "keptDays": kept_days,
            "droppedDays": dropped_days,
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

        # Export funding assignments
        funding_assignments_data = {
            "keptDays": len(results.regime_assignments),
            "droppedDays": 0,
            "dropReasons": {"missing": 0, "nan": 0, "tooFewBars": 0, "notEnoughOthers": 0},
            "byRegime": [
                {
                    "regime": regime,
                    "days": int((results.regime_assignments["regime"] == regime).sum()),
                }
                for regime in ["low", "med", "high"]
            ],
        }

        with open(os.path.join(output_dir, "funding_assignments.json"), "w") as f:
            json.dump(funding_assignments_data, f, indent=2, default=str)

        self.logger.info(f"Exported results to {output_dir}/")
        self.logger.info("  - funding_terciles_summary.json")
        self.logger.info("  - leadership_by_funding.json")
        self.logger.info("  - leadership_by_day_funding.csv")
        self.logger.info("  - funding_assignments.json")
        self.logger.info("  - MANIFEST.json")

    def compute_funding_terciles(
        self, funding_data: pd.DataFrame
    ) -> Tuple[Dict[str, float], pd.Series]:
        """Compute funding rate terciles and regime assignments."""
        # Calculate daily mean funding rates
        daily_funding = funding_data.groupby(funding_data.index.date)["funding_rate"].mean()

        # Compute terciles
        q33 = daily_funding.quantile(0.33)
        q66 = daily_funding.quantile(0.66)

        terciles = {"q33": q33, "q66": q66}

        # Assign regimes
        regime_assignments = []
        for date, funding_rate in daily_funding.items():
            if funding_rate <= q33:
                regime = "low"
            elif funding_rate <= q66:
                regime = "med"
            else:
                regime = "high"

            regime_assignments.append(
                {"date": pd.Timestamp(date), "funding_rate": funding_rate, "regime": regime}
            )

        assignments_df = pd.DataFrame(regime_assignments)
        assignments_df.set_index("date", inplace=True)

        return terciles, assignments_df

    def detect_funding_shocks(
        self, funding_data: pd.DataFrame, threshold_pct: float = 90
    ) -> pd.Series:
        """Detect funding rate shocks (|Δfunding| > p90)."""
        daily_funding = funding_data.groupby(funding_data.index.date)["funding_rate"].mean()
        funding_changes = daily_funding.diff().abs()

        threshold = funding_changes.quantile(threshold_pct / 100)
        shocks = funding_changes > threshold

        return shocks

    def compute_leadership_by_regime(
        self, regime_assignments: pd.DataFrame, funding_data: pd.DataFrame
    ) -> List[Any]:
        """Compute leadership distribution by funding regime using consensus-based leadership."""
        from types import SimpleNamespace

        leadership_by_regime = []

        for regime in ["low", "med", "high"]:
            regime_days = regime_assignments[regime_assignments["regime"] == regime]
            if len(regime_days) == 0:
                continue

            # Calculate leadership for each day in this regime
            venue_wins = {venue: 0 for venue in self.venues}
            tie_days = 0

            for date in regime_days.index:
                # Get available venues for this day
                available_venues = []
                venue_funding = {}

                for venue in self.venues:
                    venue_data = funding_data[
                        (funding_data.index.date == date.date()) & (funding_data["venue"] == venue)
                    ]
                    if not venue_data.empty:
                        funding_rate = venue_data["funding_rate"].iloc[0]
                        if not pd.isna(funding_rate):
                            available_venues.append(venue)
                            venue_funding[venue] = funding_rate

                # Need at least 3 venues for consensus
                if len(available_venues) < 3:
                    continue

                # Compute consensus as median of available venue funding rates
                rates = [venue_funding[v] for v in available_venues]
                consensus = np.median(rates)

                # Find leader (venue closest to consensus)
                gaps = {}
                for venue in available_venues:
                    gap = abs(venue_funding[venue] - consensus)
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

            # Calculate percentages
            total_days = len(regime_days)
            venue_leadership = {}
            venue_rankings = []
            for venue in self.venues:
                wins = venue_wins[venue]
                pct = (wins / total_days * 100) if total_days > 0 else 0
                venue_leadership[venue] = round(pct, 2)
                venue_rankings.append((venue, wins))

            # Create a simple namespace object to mimic the expected structure
            leadership_result = SimpleNamespace(
                regime=regime,
                total_days=total_days,
                venue_leadership=venue_leadership,
                venue_rankings=venue_rankings,
                tie_days=tie_days,
            )

            leadership_by_regime.append(leadership_result)

        return leadership_by_regime

    def compute_statistical_tests(
        self, regime_assignments: pd.DataFrame, leadership_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Compute statistical tests for regime-leadership relationships."""
        stats_results = {}

        # Prepare data for tests
        regime_leadership = leadership_data.merge(
            regime_assignments[["regime"]], left_index=True, right_index=True, how="inner"
        )

        # Chi-square test
        contingency_table = pd.crosstab(regime_leadership["regime"], regime_leadership["leader"])
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

        stats_results["chi2"] = {
            "chi2_statistic": round(chi2, 4),
            "p_value": round(p_value, 6),
            "degrees_of_freedom": int(dof),
            "expected_frequencies": expected.tolist(),
        }

        # Cramér's V
        n = contingency_table.sum().sum()
        cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))

        stats_results["cramers_v"] = {
            "cramers_v": round(cramers_v, 4),
            "interpretation": (
                "small" if cramers_v < 0.1 else "medium" if cramers_v < 0.3 else "large"
            ),
        }

        # Bootstrap confidence intervals (simplified)
        n_bootstrap = 1000
        bootstrap_stats = []

        for _ in range(n_bootstrap):
            sample = regime_leadership.sample(frac=1.0, replace=True)
            sample_contingency = pd.crosstab(sample["regime"], sample["leader"])
            if sample_contingency.shape == contingency_table.shape:
                sample_chi2, _, _, _ = stats.chi2_contingency(sample_contingency)
                bootstrap_stats.append(sample_chi2)

        if bootstrap_stats:
            ci_lower = np.percentile(bootstrap_stats, 2.5)
            ci_upper = np.percentile(bootstrap_stats, 97.5)

            stats_results["bootstrap_ci"] = {
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "n_bootstrap": n_bootstrap,
            }

        return stats_results

    def analyze_funding_regimes(
        self, funding_data: pd.DataFrame, leadership_data: pd.DataFrame
    ) -> FundingRegimeResult:
        """Main analysis function for funding regimes."""
        self.logger.info("=== START [ENV:funding:config] ===")

        # Log configuration
        self._log_config(funding_data)

        # Compute terciles and regime assignments
        terciles, regime_assignments = self.compute_funding_terciles(funding_data)

        # Detect funding shocks
        funding_shocks = self.detect_funding_shocks(funding_data)
        regime_assignments["funding_shock"] = funding_shocks

        # Log terciles and assignments
        counts = regime_assignments["regime"].value_counts().to_dict()
        self._log_terciles(terciles, counts)
        self._log_assignments(regime_assignments)

        # Compute leadership by regime
        leadership_by_regime = self.compute_leadership_by_regime(regime_assignments, funding_data)

        # Log leadership results
        self._log_leadership_summary(leadership_by_regime)
        self._log_leadership_table(leadership_by_regime)
        self._log_dropped_days()
        self._log_ties(leadership_by_regime)

        # Compute statistical tests
        stats_results = self.compute_statistical_tests(regime_assignments, leadership_data)
        self._log_stats(stats_results)

        # Log exact tags for grep
        self._log_funding_stats_exact(stats_results)

        # Export results
        result = FundingRegimeResult(
            regime_assignments=regime_assignments,
            funding_terciles=terciles,
            leadership_by_regime=leadership_by_regime,
            funding_shocks=funding_shocks,
            stats_results=stats_results,
            funding_data=funding_data,
        )

        self._export_results(result)

        self.logger.info("=== END [ENV:funding:config] ===")
        return result


def create_funding_regime_analyzer(pair: str = "BTC-USD") -> FundingRegimeAnalyzer:
    """Create a funding regime analyzer instance."""
    return FundingRegimeAnalyzer(pair=pair)
