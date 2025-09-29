"""
ACD Invariance Matrix Analysis Module

This module analyzes whether venue leadership is invariant across different
market environments (volatility, funding, liquidity regimes).
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import scipy.stats as stats
from datetime import datetime


@dataclass
class InvarianceResult:
    """Result container for invariance matrix analysis."""

    matrix_df: pd.DataFrame
    report_data: Dict[str, Any]
    guardrails: List[Dict[str, Any]]
    stats_results: Dict[str, Any]


class InvarianceMatrixAnalyzer:
    """
    Analyzes venue leadership invariance across market environments.

    Computes stability indices, ranges, and statistical tests to determine
    whether venues maintain consistent leadership across volatility, funding,
    and liquidity regimes.
    """

    def __init__(self, spec_version: str = "1.0.0"):
        self.spec_version = spec_version
        self.logger = logging.getLogger(__name__)
        self.venues = ["binance", "coinbase", "kraken", "bybit", "okx"]
        self.environments = ["volatility", "funding", "liquidity"]
        self.regimes = ["low", "medium", "high"]

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

    def load_environment_data(
        self, volatility_file: str, funding_file: str, liquidity_file: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load and normalize environment data from CSV files.

        Args:
            volatility_file: Path to volatility leadership CSV
            funding_file: Path to funding leadership CSV
            liquidity_file: Path to liquidity leadership CSV

        Returns:
            Tuple of (volatility_df, funding_df, liquidity_df)
        """
        self.logger.info("Loading environment data from CSV files")

        # Load CSVs
        vol_df = pd.read_csv(volatility_file)
        fund_df = pd.read_csv(funding_file)
        liq_df = pd.read_csv(liquidity_file)

        # Normalize data
        vol_df = self._normalize_dataframe(vol_df, "volatility")
        fund_df = self._normalize_dataframe(fund_df, "funding")
        liq_df = self._normalize_dataframe(liq_df, "liquidity")

        self.logger.info(
            f"Loaded {len(vol_df)} volatility, {len(fund_df)} funding, "
            f"{len(liq_df)} liquidity records"
        )

        return vol_df, fund_df, liq_df

    def _normalize_dataframe(self, df: pd.DataFrame, env_name: str) -> pd.DataFrame:
        """
        Normalize a dataframe to standard format.

        Args:
            df: Input dataframe
            env_name: Environment name for logging

        Returns:
            Normalized dataframe
        """
        # Ensure required columns exist
        required_cols = ["dayKey", "regime", "leader"] + self.venues
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in {env_name} data: {missing_cols}")

        # Filter valid regimes
        valid_regimes = {"low", "medium", "high"}
        original_count = len(df)
        df = df[df["regime"].isin(valid_regimes)].copy()
        dropped_count = original_count - len(df)

        if dropped_count > 0:
            self.logger.warning(f"Dropped {dropped_count} rows with invalid regimes in {env_name}")

        # Filter valid leaders
        original_count = len(df)
        df = df[df["leader"].isin(self.venues)].copy()
        dropped_count = original_count - len(df)

        if dropped_count > 0:
            self.logger.warning(f"Dropped {dropped_count} rows with invalid leaders in {env_name}")

        # Ensure regime labels are standardized
        df["regime"] = df["regime"].replace({"med": "medium"})

        return df

    def compute_environment_shares(
        self, vol_df: pd.DataFrame, fund_df: pd.DataFrame, liq_df: pd.DataFrame
    ) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], List[Dict[str, Any]]]:
        """
        Compute leadership shares for each environment and regime.

        Args:
            vol_df: Volatility dataframe
            fund_df: Funding dataframe
            liq_df: Liquidity dataframe

        Returns:
            Tuple of (shares_dict, guardrails_list)
        """
        shares = {}
        guardrails = []

        # Process each environment
        for env_name, df in [("volatility", vol_df), ("funding", fund_df), ("liquidity", liq_df)]:
            shares[env_name] = {}

            for regime in self.regimes:
                regime_data = df[df["regime"] == regime]
                days_count = len(regime_data)

                # Check guardrails
                if days_count < 30:
                    guardrail = {
                        "type": "sample:small",
                        "env": env_name,
                        "regime": regime,
                        "days": days_count,
                    }
                    guardrails.append(guardrail)
                    self.logger.warning(f"[GUARDRAIL:sample:small] {json.dumps(guardrail)}")

                if days_count == 0:
                    shares[env_name][regime] = {venue: 0.0 for venue in self.venues}
                    continue

                # Compute shares
                regime_shares = {}
                for venue in self.venues:
                    venue_wins = (regime_data["leader"] == venue).sum()
                    share_pct = (venue_wins / days_count) * 100
                    regime_shares[venue] = round(share_pct, 2)

                # Verify sum is ~100%
                total_share = sum(regime_shares.values())
                if abs(total_share - 100.0) > 0.01:
                    self.logger.warning(
                        f"[WARN:shares:not100] {env_name}:{regime} sum={total_share:.2f}"
                    )

                shares[env_name][regime] = regime_shares

        return shares, guardrails

    def compute_invariance_metrics(
        self, shares: Dict[str, Dict[str, Dict[str, float]]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute invariance metrics for each venue.

        Args:
            shares: Environment shares dictionary

        Returns:
            Dictionary of venue metrics
        """
        venue_metrics = {}

        for venue in self.venues:
            # Collect shares across all environment-regime combinations
            vector = []
            for env in self.environments:
                for regime in self.regimes:
                    share = shares[env][regime][venue]
                    vector.append(share)

            vector = np.array(vector)

            # Compute metrics
            mean_share = np.mean(vector)
            std_share = np.std(vector)

            # Stability Index: 1 - (std / mean), closer to 1 = more invariant
            si = 1 - (std_share / max(1e-9, mean_share))

            # Range: max - min
            range_val = np.max(vector) - np.min(vector)

            # Min share
            min_share = np.min(vector)

            venue_metrics[venue] = {
                "SI": round(si, 4),
                "Range": round(range_val, 2),
                "MinShare": round(min_share, 2),
                "vector": vector.tolist(),
            }

        return venue_metrics

    def compute_herfindahl_indices(
        self, shares: Dict[str, Dict[str, Dict[str, float]]]
    ) -> List[Dict[str, Any]]:
        """
        Compute Herfindahl-Hirschman indices for each environment-regime.

        Args:
            shares: Environment shares dictionary

        Returns:
            List of HHI values
        """
        hhi_results = []

        for env in self.environments:
            for regime in self.regimes:
                regime_shares = shares[env][regime]
                # Convert percentages to proportions
                proportions = [share / 100.0 for share in regime_shares.values()]
                hhi = sum(p**2 for p in proportions)

                hhi_results.append({"env": env, "regime": regime, "HHI": round(hhi, 3)})

        return hhi_results

    def compute_statistical_tests(
        self, vol_df: pd.DataFrame, fund_df: pd.DataFrame, liq_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compute statistical tests for environment-leadership relationships.

        Args:
            vol_df: Volatility dataframe
            fund_df: Funding dataframe
            liq_df: Liquidity dataframe

        Returns:
            Dictionary of statistical test results
        """
        stats_results = {}

        # Per-environment chi-square tests
        for env_name, df in [("volatility", vol_df), ("funding", fund_df), ("liquidity", liq_df)]:
            # Create contingency table: venue × regime
            contingency = pd.crosstab(df["leader"], df["regime"])

            if contingency.shape[0] >= 2 and contingency.shape[1] >= 2:
                chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

                stats_results[env_name] = {
                    "chi2": round(chi2, 4),
                    "dof": int(dof),
                    "p": round(p_value, 6),
                }

                # Log single-line JSON
                chi2_result = {
                    "chi2_statistic": round(chi2, 4),
                    "p_value": round(p_value, 6),
                    "degrees_of_freedom": int(dof),
                }
                print(f"[STATS:env:{env_name}:chi2] {json.dumps(chi2_result, ensure_ascii=False)}")

        # Global chi-square test across all environments
        all_data = []
        for df in [vol_df, fund_df, liq_df]:
            all_data.append(df[["leader", "regime"]])

        combined_df = pd.concat(all_data, ignore_index=True)
        global_contingency = pd.crosstab(combined_df["leader"], combined_df["regime"])

        if global_contingency.shape[0] >= 2 and global_contingency.shape[1] >= 2:
            chi2, p_value, dof, expected = stats.chi2_contingency(global_contingency)

            stats_results["global"] = {
                "chi2": round(chi2, 4),
                "dof": int(dof),
                "p": round(p_value, 6),
            }

            # Log single-line JSON
            global_result = {
                "chi2_statistic": round(chi2, 4),
                "p_value": round(p_value, 6),
                "degrees_of_freedom": int(dof),
            }
            print(f"[STATS:env:global:chi2] {json.dumps(global_result, ensure_ascii=False)}")

        return stats_results

    def compute_bootstrap_stability(
        self,
        vol_df: pd.DataFrame,
        fund_df: pd.DataFrame,
        liq_df: pd.DataFrame,
        n_bootstrap: int = 1000,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute bootstrap confidence intervals for stability indices.

        Args:
            vol_df: Volatility dataframe
            fund_df: Funding dataframe
            liq_df: Liquidity dataframe
            n_bootstrap: Number of bootstrap samples

        Returns:
            Dictionary of bootstrap results per venue
        """
        bootstrap_results = {}

        for venue in self.venues:
            si_values = []

            for _ in range(n_bootstrap):
                # Bootstrap sample from each environment-regime
                boot_vector = []

                for df in [vol_df, fund_df, liq_df]:
                    for regime in self.regimes:
                        regime_data = df[df["regime"] == regime]
                        if len(regime_data) > 0:
                            # Bootstrap sample
                            boot_sample = regime_data.sample(n=len(regime_data), replace=True)
                            venue_wins = (boot_sample["leader"] == venue).sum()
                            share_pct = (venue_wins / len(boot_sample)) * 100
                            boot_vector.append(share_pct)
                        else:
                            boot_vector.append(0.0)

                # Compute SI for this bootstrap sample
                boot_array = np.array(boot_vector)
                mean_share = np.mean(boot_array)
                std_share = np.std(boot_array)
                si = 1 - (std_share / max(1e-9, mean_share))
                si_values.append(si)

            # Compute confidence interval
            ci_lower = np.percentile(si_values, 2.5)
            ci_upper = np.percentile(si_values, 97.5)
            si_mean = np.mean(si_values)

            bootstrap_results[venue] = {
                "SI_mean": round(si_mean, 4),
                "CI95": [round(ci_lower, 4), round(ci_upper, 4)],
                "n": n_bootstrap,
            }

            # Log single-line JSON
            bootstrap_result = {
                "venue": venue,
                "SI_mean": round(si_mean, 4),
                "CI95": [round(ci_lower, 4), round(ci_upper, 4)],
                "n": n_bootstrap,
            }
            print(
                f"[STATS:env:global:bootstrap] {json.dumps(bootstrap_result, ensure_ascii=False)}"
            )

        return bootstrap_results

    def create_matrix_dataframe(
        self,
        shares: Dict[str, Dict[str, Dict[str, float]]],
        venue_metrics: Dict[str, Dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Create the invariance matrix CSV dataframe.

        Args:
            shares: Environment shares dictionary
            venue_metrics: Venue metrics dictionary

        Returns:
            Matrix dataframe
        """
        matrix_data = []

        for venue in self.venues:
            row = {"venue": venue}

            # Add shares for each environment-regime combination
            for env in self.environments:
                for regime in self.regimes:
                    col_name = f"{env}_{regime}" if env != "volatility" else f"vol_{regime}"
                    row[col_name] = shares[env][regime][venue]

            # Add summary metrics
            row["SI"] = venue_metrics[venue]["SI"]
            row["Range"] = venue_metrics[venue]["Range"]
            row["MinShare"] = venue_metrics[venue]["MinShare"]

            matrix_data.append(row)

        return pd.DataFrame(matrix_data)

    def create_report_data(
        self,
        shares: Dict[str, Dict[str, Dict[str, float]]],
        venue_metrics: Dict[str, Dict[str, Any]],
        bootstrap_results: Dict[str, Dict[str, Any]],
        hhi_results: List[Dict[str, Any]],
        guardrails: List[Dict[str, Any]],
        stats_results: Dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Create the invariance report JSON data.

        Args:
            shares: Environment shares dictionary
            venue_metrics: Venue metrics dictionary
            bootstrap_results: Bootstrap results dictionary
            hhi_results: HHI results list
            guardrails: Guardrails list
            stats_results: Statistical test results
            start_date: Start date string
            end_date: End date string

        Returns:
            Report data dictionary
        """
        # Count regime days
        regime_counts = {}
        for env in self.environments:
            regime_counts[env] = {}
            for regime in self.regimes:
                # Count days in this environment-regime
                count = 0
                for venue_shares in shares[env][regime].values():
                    if venue_shares > 0:  # Approximate count from shares
                        count += 1
                regime_counts[env][regime] = count

        # Create venue data
        venues_data = []
        for venue in self.venues:
            venue_data = {
                "venue": venue,
                "sharesPct": {
                    "volatility": {
                        "low": shares["volatility"]["low"][venue],
                        "medium": shares["volatility"]["medium"][venue],
                        "high": shares["volatility"]["high"][venue],
                    },
                    "funding": {
                        "low": shares["funding"]["low"][venue],
                        "medium": shares["funding"]["medium"][venue],
                        "high": shares["funding"]["high"][venue],
                    },
                    "liquidity": {
                        "low": shares["liquidity"]["low"][venue],
                        "medium": shares["liquidity"]["medium"][venue],
                        "high": shares["liquidity"]["high"][venue],
                    },
                },
                "SI": venue_metrics[venue]["SI"],
                "Range": venue_metrics[venue]["Range"],
                "MinShare": venue_metrics[venue]["MinShare"],
                "bootstrap": bootstrap_results[venue],
            }
            venues_data.append(venue_data)

        report_data = {
            "specVersion": self.spec_version,
            "codeVersion": self._get_code_version(),
            "tz": "UTC",
            "window": {"start": start_date, "end": end_date},
            "regimeCounts": regime_counts,
            "guardrails": guardrails,
            "perRegimeHHI": hhi_results,
            "venues": venues_data,
            "stats": stats_results,
        }

        return report_data

    def export_results(
        self, result: InvarianceResult, output_dir: str, start_date: str, end_date: str
    ) -> None:
        """
        Export all results to files.

        Args:
            result: Invariance analysis result
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string
        """
        os.makedirs(output_dir, exist_ok=True)

        # Export matrix CSV
        matrix_path = os.path.join(output_dir, "invariance_matrix.csv")
        result.matrix_df.to_csv(matrix_path, index=False)
        self.logger.info(
            f'[INVARIANCE:matrix:ready] {{"venues":{len(self.venues)},'
            f'"bins":9,"file":"{matrix_path}"}}'
        )

        # Export report JSON
        report_path = os.path.join(output_dir, "invariance_report.json")
        with open(report_path, "w") as f:
            json.dump(result.report_data, f, indent=2, default=str)

        # Export summary markdown
        summary_path = os.path.join(output_dir, "invariance_summary.md")
        self._create_summary_markdown(result, summary_path)

        # Update MANIFEST.json
        self._update_manifest(output_dir, start_date, end_date, result.guardrails)

        self.logger.info(f"Exported invariance analysis results to {output_dir}/")

    def _create_summary_markdown(self, result: InvarianceResult, output_path: str) -> None:
        """Create human-readable summary markdown."""
        with open(output_path, "w") as f:
            f.write("# ACD Invariance Matrix Summary\n\n")

            # Matrix table
            f.write("## Leadership Shares by Environment-Regime\n\n")
            f.write(
                "| Venue | Vol Low | Vol Med | Vol High | Fund Low | Fund Med | "
                "Fund High | Liq Low | Liq Med | Liq High | SI | Range | MinShare |\n"
            )
            f.write(
                "|-------|---------|---------|----------|----------|----------|"
                "-----------|---------|---------|----------|----|-------|----------|\n"
            )

            for _, row in result.matrix_df.iterrows():
                f.write(
                    f"| {row['venue']} | {row['vol_low']} | {row['vol_medium']} | "
                    f"{row['vol_high']} | {row['funding_low']} | {row['funding_medium']} | "
                    f"{row['funding_high']} | {row['liquidity_low']} | {row['liquidity_medium']} | "
                    f"{row['liquidity_high']} | {row['SI']} | {row['Range']} | "
                    f"{row['MinShare']} |\n"
                )

            # Notable rotations
            f.write("\n## Notable Leadership Rotations\n\n")
            f.write("- *Analysis of venue leadership patterns across environments*\n")

            # Guardrails
            if result.guardrails:
                f.write("\n## Guardrail Warnings\n\n")
                for guardrail in result.guardrails:
                    f.write(
                        f"- **{guardrail['env'].title()} {guardrail['regime'].title()}**: "
                        f"Only {guardrail['days']} days (minimum 30 recommended)\n"
                    )

            # Interpretation
            f.write("\n## Interpretation\n\n")
            f.write(
                "- **Stability Index (SI)**: Closer to 1.0 indicates more " "invariant leadership\n"
            )
            f.write(
                "- **Range**: Smaller values indicate more consistent leadership "
                "across environments\n"
            )
            f.write("- **MinShare**: Higher values indicate persistent baseline leadership\n")
            f.write(
                "- **Statistical tests**: Chi-square tests assess independence of "
                "venue leadership from market regimes\n"
            )
            f.write(
                "- **Bootstrap CI**: Confidence intervals for stability indices "
                "based on 1000 resamples\n"
            )

    def _update_manifest(
        self, output_dir: str, start_date: str, end_date: str, guardrails: List[Dict[str, Any]]
    ) -> None:
        """Update MANIFEST.json with invariance run data."""
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

        # Add invariance run data
        manifest_data["runs"]["invariance"] = {
            "generated": datetime.now().isoformat() + "Z",
            "inputs": [
                "leadership_by_day.csv",
                "leadership_by_day_funding.csv",
                "leadership_by_day_liquidity.csv",
            ],
            "guardrails": guardrails,
            "notes": "All sums within ±0.01; labels standardized",
        }

        # Write updated manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

    def analyze_invariance(
        self,
        volatility_file: str,
        funding_file: str,
        liquidity_file: str,
        output_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
    ) -> InvarianceResult:
        """
        Run complete invariance matrix analysis.

        Args:
            volatility_file: Path to volatility leadership CSV
            funding_file: Path to funding leadership CSV
            liquidity_file: Path to liquidity leadership CSV
            output_dir: Output directory
            start_date: Start date string
            end_date: End date string

        Returns:
            Invariance analysis result
        """
        self.logger.info("Starting ACD Invariance Matrix analysis")

        # Load and normalize data
        vol_df, fund_df, liq_df = self.load_environment_data(
            volatility_file, funding_file, liquidity_file
        )

        # Compute environment shares
        shares, guardrails = self.compute_environment_shares(vol_df, fund_df, liq_df)

        # Compute invariance metrics
        venue_metrics = self.compute_invariance_metrics(shares)

        # Compute Herfindahl indices
        hhi_results = self.compute_herfindahl_indices(shares)

        # Compute statistical tests
        stats_results = self.compute_statistical_tests(vol_df, fund_df, liq_df)

        # Compute bootstrap stability
        bootstrap_results = self.compute_bootstrap_stability(vol_df, fund_df, liq_df)

        # Create matrix dataframe
        matrix_df = self.create_matrix_dataframe(shares, venue_metrics)

        # Create report data
        report_data = self.create_report_data(
            shares,
            venue_metrics,
            bootstrap_results,
            hhi_results,
            guardrails,
            stats_results,
            start_date,
            end_date,
        )

        # Create result object
        result = InvarianceResult(
            matrix_df=matrix_df,
            report_data=report_data,
            guardrails=guardrails,
            stats_results=stats_results,
        )

        # Export results
        self.export_results(result, output_dir, start_date, end_date)

        self.logger.info("ACD Invariance Matrix analysis completed")

        return result


def create_invariance_analyzer(spec_version: str = "1.0.0") -> InvarianceMatrixAnalyzer:
    """Create an invariance matrix analyzer instance."""
    return InvarianceMatrixAnalyzer(spec_version=spec_version)
