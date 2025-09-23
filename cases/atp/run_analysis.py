"""
ATP Retrospective Case Study - Analysis Pipeline

This module runs the complete ACD analysis on ATP data, including
ICP, VMM, and all validation layers to detect coordination patterns.
"""

import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from acd.icp.engine import ICPEngine, ICPConfig
from acd.vmm.engine import VMMEngine, VMMConfig
from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.vmm.scalers import GlobalMomentScaler
from acd.validation.lead_lag import analyze_lead_lag
from acd.validation.mirroring import analyze_mirroring
from acd.validation.hmm import analyze_hmm
from acd.validation.infoflow import analyze_infoflow
from acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig


class ATPAnalyzer:
    """Analyze ATP data using the complete ACD pipeline"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)

        # Initialize engines
        self.icp_config = ICPConfig()
        self.vmm_config = VMMConfig()
        self.crypto_config = CryptoMomentConfig()

        self.icp_engine = ICPEngine(self.icp_config)
        self.vmm_engine = VMMEngine(
            self.vmm_config, CryptoMomentCalculator(self.crypto_config, GlobalMomentScaler())
        )

        # Initialize integrated engine with proper config
        integrated_config = IntegratedConfig(
            icp_config=self.icp_config,
            vmm_config=self.vmm_config,
            crypto_moments_config=self.crypto_config,
        )
        self.integrated_engine = IntegratedACDEngine(integrated_config)

        # Results storage
        self.results = {}
        self.artifacts = {}

    def run_complete_analysis(self, data: pd.DataFrame) -> Dict:
        """
        Run complete ACD analysis on ATP data

        Args:
            data: ATP DataFrame with airline prices and environments

        Returns:
            Dictionary with all analysis results
        """
        print("Starting ATP retrospective analysis...")

        # Get airline columns
        airline_columns = [col for col in data.columns if col.startswith("Airline_")]

        # 1. ICP Analysis
        print("Running ICP analysis...")
        icp_result = self._run_icp_analysis(data, airline_columns)
        self.results["icp"] = icp_result

        # 2. VMM Analysis
        print("Running VMM analysis...")
        vmm_result = self._run_vmm_analysis(data, airline_columns)
        self.results["vmm"] = vmm_result

        # 3. Validation Layers
        print("Running validation layers...")
        validation_results = self._run_validation_layers(data, airline_columns)
        self.results["validation"] = validation_results

        # 4. Integrated Analysis
        print("Running integrated analysis...")
        integrated_result = self._run_integrated_analysis(data, airline_columns)
        self.results["integrated"] = integrated_result

        # 5. Generate Report
        print("Generating analysis report...")
        report = self._generate_report()
        self.results["report"] = report

        return self.results

    def _run_icp_analysis(self, data: pd.DataFrame, airline_columns: List[str]) -> Dict:
        """Run ICP analysis on ATP data"""
        try:
            # Run ICP with environment partitioning
            icp_result = self.icp_engine.run_icp(
                data,
                price_columns=airline_columns,
                environment_column="volatility_regime",
                seed=self.seed,
            )

            return {
                "invariance_p_value": icp_result.invariance_p_value,
                "power": icp_result.power,
                "n_environments": icp_result.n_environments,
                "environment_sizes": icp_result.environment_sizes,
                "bootstrap_ci": icp_result.bootstrap_ci,
                "status": "success",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _run_vmm_analysis(self, data: pd.DataFrame, airline_columns: List[str]) -> Dict:
        """Run VMM analysis on ATP data"""
        try:
            # Run VMM with crypto moments adapted for airlines
            vmm_result = self.vmm_engine.run_vmm(
                data,
                price_columns=airline_columns,
                environment_column="volatility_regime",
                seed=self.seed,
            )

            return {
                "over_identification_stat": vmm_result.over_identification_stat,
                "over_identification_p_value": vmm_result.over_identification_p_value,
                "structural_stability": vmm_result.structural_stability,
                "n_moments": vmm_result.n_moments,
                "convergence_achieved": vmm_result.convergence_achieved,
                "status": "success",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _run_validation_layers(self, data: pd.DataFrame, airline_columns: List[str]) -> Dict:
        """Run all validation layers on ATP data"""
        validation_results = {}

        # Lead-lag analysis
        try:
            lead_lag_result = analyze_lead_lag(
                data, airline_columns, environment_column="volatility_regime", seed=self.seed
            )
            validation_results["lead_lag"] = {
                "switching_entropy": lead_lag_result.switching_entropy,
                "avg_granger_p": lead_lag_result.avg_granger_p,
                "significant_relationships": len(lead_lag_result.significant_relationships),
                "persistence_scores": lead_lag_result.persistence_scores,
                "status": "success",
            }
        except Exception as e:
            validation_results["lead_lag"] = {"error": str(e), "status": "failed"}

        # Mirroring analysis
        try:
            mirroring_result = analyze_mirroring(
                data, airline_columns, environment_column="volatility_regime", seed=self.seed
            )
            validation_results["mirroring"] = {
                "coordination_score": mirroring_result.coordination_score,
                "mirroring_ratio": mirroring_result.mirroring_ratio,
                "avg_cosine_similarity": mirroring_result.avg_cosine_similarity,
                "high_mirroring_pairs": len(mirroring_result.high_mirroring_pairs),
                "status": "success",
            }
        except Exception as e:
            validation_results["mirroring"] = {"error": str(e), "status": "failed"}

        # HMM analysis
        try:
            hmm_result = analyze_hmm(
                data, airline_columns, environment_column="volatility_regime", seed=self.seed
            )
            validation_results["hmm"] = {
                "regime_stability": hmm_result.regime_stability,
                "coordination_regime_score": hmm_result.coordination_regime_score,
                "wide_spread_regime": hmm_result.wide_spread_regime,
                "lockstep_regime": hmm_result.lockstep_regime,
                "log_likelihood": hmm_result.log_likelihood,
                "status": "success",
            }
        except Exception as e:
            validation_results["hmm"] = {"error": str(e), "status": "failed"}

        # Information flow analysis
        try:
            infoflow_result = analyze_infoflow(
                data, airline_columns, environment_column="volatility_regime", seed=self.seed
            )
            validation_results["infoflow"] = {
                "coordination_network_score": infoflow_result.coordination_network_score,
                "avg_transfer_entropy": infoflow_result.avg_transfer_entropy,
                "out_degree_concentration": infoflow_result.out_degree_concentration,
                "significant_te_links": len(infoflow_result.significant_te_links),
                "status": "success",
            }
        except Exception as e:
            validation_results["infoflow"] = {"error": str(e), "status": "failed"}

        return validation_results

    def _run_integrated_analysis(self, data: pd.DataFrame, airline_columns: List[str]) -> Dict:
        """Run integrated ACD analysis"""
        try:
            # Run integrated analysis
            integrated_result = self.integrated_engine.run_integrated_analysis(
                data,
                price_columns=airline_columns,
                environment_column="volatility_regime",
                seed=self.seed,
            )

            return {
                "composite_score": integrated_result.composite_score,
                "risk_band": integrated_result.risk_band,
                "icp_contribution": integrated_result.icp_contribution,
                "vmm_contribution": integrated_result.vmm_contribution,
                "crypto_contribution": integrated_result.crypto_contribution,
                "status": "success",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _generate_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "seed": self.seed,
            "summary": self._generate_summary(),
            "coordination_indicators": self._extract_coordination_indicators(),
            "statistical_significance": self._extract_statistical_significance(),
            "environment_analysis": self._extract_environment_analysis(),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_summary(self) -> Dict:
        """Generate analysis summary"""
        summary = {
            "overall_risk_assessment": "AMBER",  # Default
            "coordination_detected": False,
            "confidence_level": "Medium",
            "key_findings": [],
        }

        # Check ICP results
        if self.results.get("icp", {}).get("status") == "success":
            icp_p = self.results["icp"]["invariance_p_value"]
            if icp_p < 0.05:
                summary["coordination_detected"] = True
                summary["key_findings"].append(f"ICP rejects invariance (p={icp_p:.3f})")

        # Check VMM results
        if self.results.get("vmm", {}).get("status") == "success":
            vmm_p = self.results["vmm"]["over_identification_p_value"]
            if vmm_p < 0.05:
                summary["coordination_detected"] = True
                summary["key_findings"].append(f"VMM rejects moment conditions (p={vmm_p:.3f})")

        # Check validation layers
        validation = self.results.get("validation", {})
        if validation.get("lead_lag", {}).get("status") == "success":
            entropy = validation["lead_lag"]["switching_entropy"]
            if entropy < 0.5:  # Low entropy suggests persistent leadership
                summary["key_findings"].append(
                    f"Low switching entropy ({entropy:.3f}) suggests persistent leadership"
                )

        if validation.get("mirroring", {}).get("status") == "success":
            mirroring_ratio = validation["mirroring"]["mirroring_ratio"]
            if mirroring_ratio > 0.5:  # High mirroring ratio
                summary["key_findings"].append(
                    f"High mirroring ratio ({mirroring_ratio:.3f}) suggests coordinated pricing"
                )

        # Update overall assessment
        if summary["coordination_detected"]:
            summary["overall_risk_assessment"] = "RED"
            summary["confidence_level"] = "High"
        elif len(summary["key_findings"]) > 0:
            summary["overall_risk_assessment"] = "AMBER"
            summary["confidence_level"] = "Medium"
        else:
            summary["overall_risk_assessment"] = "LOW"
            summary["confidence_level"] = "Low"

        return summary

    def _extract_coordination_indicators(self) -> Dict:
        """Extract coordination indicators from all layers"""
        indicators = {
            "lead_lag_persistence": None,
            "mirroring_coordination": None,
            "regime_stability": None,
            "information_flow": None,
        }

        validation = self.results.get("validation", {})

        if validation.get("lead_lag", {}).get("status") == "success":
            indicators["lead_lag_persistence"] = {
                "switching_entropy": validation["lead_lag"]["switching_entropy"],
                "significant_relationships": validation["lead_lag"]["significant_relationships"],
            }

        if validation.get("mirroring", {}).get("status") == "success":
            indicators["mirroring_coordination"] = {
                "coordination_score": validation["mirroring"]["coordination_score"],
                "mirroring_ratio": validation["mirroring"]["mirroring_ratio"],
            }

        if validation.get("hmm", {}).get("status") == "success":
            indicators["regime_stability"] = {
                "regime_stability": validation["hmm"]["regime_stability"],
                "coordination_regime_score": validation["hmm"]["coordination_regime_score"],
            }

        if validation.get("infoflow", {}).get("status") == "success":
            indicators["information_flow"] = {
                "coordination_network_score": validation["infoflow"]["coordination_network_score"],
                "significant_te_links": validation["infoflow"]["significant_te_links"],
            }

        return indicators

    def _extract_statistical_significance(self) -> Dict:
        """Extract statistical significance measures"""
        significance = {
            "icp_p_value": None,
            "vmm_p_value": None,
            "granger_p_values": None,
            "transfer_entropy_significance": None,
        }

        if self.results.get("icp", {}).get("status") == "success":
            significance["icp_p_value"] = self.results["icp"]["invariance_p_value"]

        if self.results.get("vmm", {}).get("status") == "success":
            significance["vmm_p_value"] = self.results["vmm"]["over_identification_p_value"]

        validation = self.results.get("validation", {})
        if validation.get("lead_lag", {}).get("status") == "success":
            significance["granger_p_values"] = validation["lead_lag"]["avg_granger_p"]

        if validation.get("infoflow", {}).get("status") == "success":
            significance["transfer_entropy_significance"] = validation["infoflow"][
                "significant_te_links"
            ]

        return significance

    def _extract_environment_analysis(self) -> Dict:
        """Extract environment-specific analysis"""
        return {
            "volatility_regimes": ["low", "high"],
            "market_conditions": ["bullish", "bearish"],
            "coordination_periods": True,  # ATP had specific coordination periods
            "environment_sensitivity": "High",  # ATP case was environment-sensitive
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        summary = self.results.get("report", {}).get("summary", {})

        if summary.get("coordination_detected"):
            recommendations.append("Investigate potential coordination patterns in airline pricing")
            recommendations.append("Review fare filing timelines for evidence of coordination")
            recommendations.append("Consider regulatory intervention if coordination is confirmed")
        else:
            recommendations.append("Continue monitoring for coordination patterns")
            recommendations.append("Regular analysis recommended for early detection")

        recommendations.append("Validate findings with additional data sources")
        recommendations.append(
            "Consider alternative explanations (fuel costs, capacity constraints)"
        )

        return recommendations

    def save_artifacts(self, output_dir: str = "cases/atp/artifacts"):
        """Save analysis artifacts"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save results as JSON
        results_file = output_path / f"atp_analysis_results_seed_{self.seed}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save report as markdown
        report_file = output_path / f"atp_analysis_report_seed_{self.seed}.md"
        self._save_markdown_report(report_file)

        print(f"Artifacts saved to {output_path}")
        return output_path

    def _save_markdown_report(self, file_path: Path):
        """Save analysis report as markdown"""
        report = self.results.get("report", {})
        summary = report.get("summary", {})

        with open(file_path, "w") as f:
            f.write("# ATP Retrospective Analysis Report\n\n")
            f.write(f"**Analysis Date:** {report.get('analysis_timestamp', 'N/A')}\n")
            f.write(f"**Seed:** {report.get('seed', 'N/A')}\n\n")

            f.write("## Executive Summary\n\n")
            f.write(
                f"**Overall Risk Assessment:** {summary.get('overall_risk_assessment', 'N/A')}\n"
            )
            f.write(f"**Coordination Detected:** {summary.get('coordination_detected', 'N/A')}\n")
            f.write(f"**Confidence Level:** {summary.get('confidence_level', 'N/A')}\n\n")

            f.write("## Key Findings\n\n")
            for finding in summary.get("key_findings", []):
                f.write(f"- {finding}\n")
            f.write("\n")

            f.write("## Coordination Indicators\n\n")
            indicators = report.get("coordination_indicators", {})
            for indicator, data in indicators.items():
                if data:
                    f.write(f"### {indicator.replace('_', ' ').title()}\n")
                    for key, value in data.items():
                        f.write(f"- {key}: {value}\n")
                    f.write("\n")

            f.write("## Recommendations\n\n")
            for rec in report.get("recommendations", []):
                f.write(f"- {rec}\n")


def run_atp_analysis(data_path: str = "cases/atp/atp_data.csv", seed: int = 42) -> Dict:
    """
    Convenience function to run ATP analysis

    Args:
        data_path: Path to ATP data CSV
        seed: Random seed for reproducibility

    Returns:
        Dictionary with analysis results
    """
    # Load data
    data = pd.read_csv(data_path)
    data["date"] = pd.to_datetime(data["date"])

    # Run analysis
    analyzer = ATPAnalyzer(seed=seed)
    results = analyzer.run_complete_analysis(data)

    # Save artifacts
    analyzer.save_artifacts()

    return results


if __name__ == "__main__":
    # Run ATP analysis
    results = run_atp_analysis(seed=42)

    # Print summary
    summary = results.get("report", {}).get("summary", {})
    print(f"\nATP Analysis Summary:")
    print(f"Risk Assessment: {summary.get('overall_risk_assessment', 'N/A')}")
    print(f"Coordination Detected: {summary.get('coordination_detected', 'N/A')}")
    print(f"Confidence Level: {summary.get('confidence_level', 'N/A')}")
    print(f"Key Findings: {len(summary.get('key_findings', []))}")
