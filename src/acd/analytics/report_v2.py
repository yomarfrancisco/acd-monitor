"""
ACD Reporting v2 - Attribution Tables and Provenance-Tracked Outputs

This module provides enhanced reporting capabilities with:
- Risk attribution tables showing driver breakdowns
- Provenance-tracked outputs (JSON + PDF)
- Regulatory-ready bundle generation
- Audit trails with cryptographic signatures
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..icp.engine import ICPResult
from ..validation.hmm import HMMResult
from ..validation.infoflow import InfoFlowResult
from ..validation.lead_lag import LeadLagResult
from ..validation.mirroring import MirroringResult
from ..vmm.crypto_moments import CryptoMoments
from ..vmm.engine import VMMOutput
from .integrated_engine import IntegratedResult

logger = logging.getLogger(__name__)


@dataclass
class AttributionTable:
    """Risk attribution table showing driver breakdowns"""

    # Overall risk metrics
    total_risk_score: float
    risk_band: str  # LOW, AMBER, RED
    confidence_level: float

    # Component contributions
    icp_contribution: float
    vmm_contribution: float
    crypto_moments_contribution: float
    validation_contribution: float

    # Driver breakdown
    lead_lag_driver: float
    mirroring_driver: float
    regime_driver: float
    infoflow_driver: float

    # Statistical significance
    icp_p_value: float
    vmm_p_value: Optional[float]
    lead_lag_significance: float
    mirroring_significance: float

    # Data quality factors
    data_completeness: float
    data_consistency: float
    sample_size_adequacy: float


@dataclass
class ProvenanceInfo:
    """Provenance tracking information"""

    # Analysis metadata
    analysis_id: str
    timestamp: datetime
    version: str
    seed: Optional[int]

    # Data sources
    data_file_paths: List[str]
    config_files: List[str]

    # Analysis components
    icp_config: Dict[str, Any]
    vmm_config: Dict[str, Any]
    validation_configs: Dict[str, Dict[str, Any]]

    # Results provenance
    result_file_paths: Dict[str, str]
    intermediate_artifacts: List[str]

    # Cryptographic signature
    content_hash: str
    signature: str


@dataclass
class RegulatoryBundle:
    """Regulatory-ready analysis bundle"""

    # Executive summary
    executive_summary: str
    key_findings: List[str]
    risk_assessment: str
    recommendations: List[str]

    # Technical details
    methodology: str
    attribution_table: AttributionTable
    statistical_results: Dict[str, Any]

    # Evidence
    charts_and_graphs: List[str]  # File paths to charts
    data_tables: Dict[str, pd.DataFrame]
    alternative_explanations: List[str]

    # Audit trail
    provenance: ProvenanceInfo
    audit_trail: List[str]

    # Metadata
    bundle_id: str
    created_at: datetime
    expires_at: Optional[datetime]


class ReportV2Generator:
    """
    Enhanced reporting generator with attribution tables and provenance tracking
    """

    def __init__(self, output_dir: str = "artifacts/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Version tracking
        self.version = "2.0.0"

    def generate_attribution_table(
        self,
        integrated_result: IntegratedResult,
        validation_results: Dict[str, Any],
        data_quality_metrics: Dict[str, float],
    ) -> AttributionTable:
        """
        Generate risk attribution table showing driver breakdowns

        Args:
            integrated_result: Results from integrated analysis
            validation_results: Results from validation layers
            data_quality_metrics: Data quality assessment metrics

        Returns:
            AttributionTable with comprehensive risk attribution
        """

        # Extract component contributions
        icp_contribution = self._calculate_icp_contribution(integrated_result.icp_result)
        vmm_contribution = self._calculate_vmm_contribution(integrated_result.vmm_result)
        crypto_contribution = self._calculate_crypto_contribution(integrated_result.crypto_moments)
        validation_contribution = self._calculate_validation_contribution(validation_results)

        # Calculate driver breakdowns
        lead_lag_driver = self._calculate_lead_lag_driver(validation_results.get("lead_lag"))
        mirroring_driver = self._calculate_mirroring_driver(validation_results.get("mirroring"))
        regime_driver = self._calculate_regime_driver(validation_results.get("hmm"))
        infoflow_driver = self._calculate_infoflow_driver(validation_results.get("infoflow"))

        # Statistical significance
        icp_p_value = integrated_result.icp_result.p_value
        vmm_p_value = getattr(integrated_result.vmm_result, "over_identification_p_value", None)
        lead_lag_significance = self._calculate_lead_lag_significance(
            validation_results.get("lead_lag")
        )
        mirroring_significance = self._calculate_mirroring_significance(
            validation_results.get("mirroring")
        )

        return AttributionTable(
            total_risk_score=integrated_result.composite_risk_score,
            risk_band=integrated_result.risk_classification,
            confidence_level=integrated_result.confidence_level,
            icp_contribution=icp_contribution,
            vmm_contribution=vmm_contribution,
            crypto_moments_contribution=crypto_contribution,
            validation_contribution=validation_contribution,
            lead_lag_driver=lead_lag_driver,
            mirroring_driver=mirroring_driver,
            regime_driver=regime_driver,
            infoflow_driver=infoflow_driver,
            icp_p_value=icp_p_value,
            vmm_p_value=vmm_p_value,
            lead_lag_significance=lead_lag_significance,
            mirroring_significance=mirroring_significance,
            data_completeness=data_quality_metrics.get("completeness", 0.0),
            data_consistency=data_quality_metrics.get("consistency", 0.0),
            sample_size_adequacy=data_quality_metrics.get("sample_size_adequacy", 0.0),
        )

    def _calculate_icp_contribution(self, icp_result: ICPResult) -> float:
        """Calculate ICP contribution to risk score"""
        if icp_result.reject_h0:
            # Higher effect size and power = higher contribution
            base_contribution = 40.0  # Base contribution for rejection
            effect_bonus = min(20.0, icp_result.effect_size * 100.0)
            power_bonus = min(10.0, icp_result.power * 10.0)
            return min(70.0, base_contribution + effect_bonus + power_bonus)
        else:
            # No rejection = low contribution
            return 5.0

    def _calculate_vmm_contribution(self, vmm_result: VMMOutput) -> float:
        """Calculate VMM contribution to risk score"""
        # Use structural stability as main indicator
        stability = getattr(vmm_result, "structural_stability", 0.0)
        convergence = 1.0 if getattr(vmm_result, "convergence_status", "") == "converged" else 0.5

        return min(70.0, stability * 50.0 + convergence * 20.0)

    def _calculate_crypto_contribution(self, crypto_moments: CryptoMoments) -> float:
        """Calculate crypto moments contribution to risk score"""
        # Extract key moments
        lead_lag_beta = np.max(getattr(crypto_moments, "lead_lag_betas", np.array([0.0])))
        mirroring_ratio = np.max(getattr(crypto_moments, "mirroring_ratios", np.array([0.0])))
        spread_frequency = np.mean(
            getattr(crypto_moments, "spread_floor_frequency", np.array([0.0]))
        )
        undercut_rate = np.mean(
            getattr(crypto_moments, "undercut_initiation_rate", np.array([0.0]))
        )

        # Weighted contribution
        contribution = (
            lead_lag_beta * 15.0
            + mirroring_ratio * 15.0
            + spread_frequency * 10.0
            + undercut_rate * 10.0
        )

        return min(50.0, contribution)

    def _calculate_validation_contribution(self, validation_results: Dict[str, Any]) -> float:
        """Calculate validation layers contribution to risk score"""
        total_contribution = 0.0
        n_layers = 0

        for layer_name, layer_result in validation_results.items():
            if layer_result is not None:
                contribution = self._calculate_layer_contribution(layer_name, layer_result)
                total_contribution += contribution
                n_layers += 1

        return total_contribution / max(1, n_layers)

    def _calculate_layer_contribution(self, layer_name: str, layer_result: Any) -> float:
        """Calculate contribution from a specific validation layer"""
        if layer_name == "lead_lag":
            persistence = getattr(layer_result, "persistence_score", 0.0)
            entropy = getattr(layer_result, "switching_entropy", 1.0)
            return min(25.0, persistence * 20.0 + (1.0 - entropy) * 5.0)

        elif layer_name == "mirroring":
            ratio = getattr(layer_result, "mirroring_ratio", 0.0)
            score = getattr(layer_result, "coordination_score", 0.0)
            return min(25.0, ratio * 15.0 + score * 10.0)

        elif layer_name == "hmm":
            stability = getattr(layer_result, "regime_stability", 0.0)
            coordination_score = getattr(layer_result, "coordination_regime_score", 0.0)
            return min(25.0, stability * 15.0 + coordination_score * 10.0)

        elif layer_name == "infoflow":
            hub_score = getattr(layer_result, "information_hub_score", 0.0)
            network_score = getattr(layer_result, "coordination_network_score", 0.0)
            return min(25.0, hub_score * 15.0 + network_score * 10.0)

        return 0.0

    def _calculate_lead_lag_driver(self, lead_lag_result: Optional[LeadLagResult]) -> float:
        """Calculate lead-lag driver contribution"""
        if lead_lag_result is None:
            return 0.0

        persistence = getattr(lead_lag_result, "persistence_score", 0.0)
        entropy = getattr(lead_lag_result, "switching_entropy", 1.0)

        # High persistence and low entropy = strong driver
        return min(100.0, persistence * 60.0 + (1.0 - entropy) * 40.0)

    def _calculate_mirroring_driver(self, mirroring_result: Optional[MirroringResult]) -> float:
        """Calculate mirroring driver contribution"""
        if mirroring_result is None:
            return 0.0

        ratio = getattr(mirroring_result, "mirroring_ratio", 0.0)
        score = getattr(mirroring_result, "coordination_score", 0.0)

        return min(100.0, ratio * 70.0 + score * 30.0)

    def _calculate_regime_driver(self, hmm_result: Optional[HMMResult]) -> float:
        """Calculate regime driver contribution"""
        if hmm_result is None:
            return 0.0

        stability = getattr(hmm_result, "regime_stability", 0.0)
        coordination_score = getattr(hmm_result, "coordination_regime_score", 0.0)

        return min(100.0, stability * 50.0 + coordination_score * 50.0)

    def _calculate_infoflow_driver(self, infoflow_result: Optional[InfoFlowResult]) -> float:
        """Calculate information flow driver contribution"""
        if infoflow_result is None:
            return 0.0

        hub_score = getattr(infoflow_result, "information_hub_score", 0.0)
        network_score = getattr(infoflow_result, "coordination_network_score", 0.0)

        return min(100.0, hub_score * 60.0 + network_score * 40.0)

    def _calculate_lead_lag_significance(self, lead_lag_result: Optional[LeadLagResult]) -> float:
        """Calculate lead-lag statistical significance"""
        if lead_lag_result is None:
            return 0.0

        # Use average p-value from Granger tests
        avg_p = getattr(lead_lag_result, "avg_granger_p", 1.0)
        return 1.0 - avg_p  # Convert to significance (higher = more significant)

    def _calculate_mirroring_significance(
        self, mirroring_result: Optional[MirroringResult]
    ) -> float:
        """Calculate mirroring statistical significance"""
        if mirroring_result is None:
            return 0.0

        # Use average correlation as significance proxy
        avg_correlation = getattr(mirroring_result, "avg_pearson_correlation", 0.0)
        return abs(avg_correlation)  # Absolute correlation as significance

    def generate_provenance_info(
        self,
        analysis_id: str,
        data_file_paths: List[str],
        configs: Dict[str, Any],
        result_file_paths: Dict[str, str],
        seed: Optional[int] = None,
    ) -> ProvenanceInfo:
        """
        Generate provenance tracking information

        Args:
            analysis_id: Unique identifier for this analysis
            data_file_paths: Paths to input data files
            configs: Analysis configurations
            result_file_paths: Paths to result files
            seed: Random seed used

        Returns:
            ProvenanceInfo with comprehensive tracking
        """

        # Generate content hash
        content_hash = self._generate_content_hash(data_file_paths, configs)

        # Generate signature (simplified for now)
        signature = self._generate_signature(content_hash)

        return ProvenanceInfo(
            analysis_id=analysis_id,
            timestamp=datetime.now(),
            version=self.version,
            seed=seed,
            data_file_paths=data_file_paths,
            config_files=[],
            icp_config=configs.get("icp", {}),
            vmm_config=configs.get("vmm", {}),
            validation_configs=configs.get("validation", {}),
            result_file_paths=result_file_paths,
            intermediate_artifacts=[],
            content_hash=content_hash,
            signature=signature,
        )

    def _generate_content_hash(self, data_file_paths: List[str], configs: Dict[str, Any]) -> str:
        """Generate content hash for provenance tracking"""
        content = {
            "data_files": data_file_paths,
            "configs": configs,
            "timestamp": datetime.now().isoformat(),
        }

        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _generate_signature(self, content_hash: str) -> str:
        """Generate cryptographic signature (simplified)"""
        # In production, this would use proper cryptographic signing
        return f"ACD_SIG_{content_hash[:16]}"

    def generate_regulatory_bundle(
        self,
        integrated_result: IntegratedResult,
        validation_results: Dict[str, Any],
        attribution_table: AttributionTable,
        provenance: ProvenanceInfo,
        case_study_name: str = "ACD Analysis",
    ) -> RegulatoryBundle:
        """
        Generate regulatory-ready analysis bundle

        Args:
            integrated_result: Results from integrated analysis
            validation_results: Results from validation layers
            attribution_table: Risk attribution table
            provenance: Provenance tracking information
            case_study_name: Name of the case study

        Returns:
            RegulatoryBundle with comprehensive regulatory-ready content
        """

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            integrated_result, attribution_table, case_study_name
        )

        # Generate key findings
        key_findings = self._generate_key_findings(
            integrated_result, validation_results, attribution_table
        )

        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(attribution_table)

        # Generate recommendations
        recommendations = self._generate_recommendations(integrated_result, attribution_table)

        # Generate methodology
        methodology = self._generate_methodology(provenance)

        # Generate statistical results
        statistical_results = self._generate_statistical_results(
            integrated_result, validation_results
        )

        # Generate data tables
        data_tables = self._generate_data_tables(validation_results)

        # Generate audit trail
        audit_trail = self._generate_audit_trail(provenance)

        # Generate bundle ID
        bundle_id = (
            f"ACD_BUNDLE_{provenance.analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        return RegulatoryBundle(
            executive_summary=executive_summary,
            key_findings=key_findings,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            methodology=methodology,
            attribution_table=attribution_table,
            statistical_results=statistical_results,
            charts_and_graphs=[],  # Will be populated by chart generation
            data_tables=data_tables,
            alternative_explanations=integrated_result.alternative_explanations,
            provenance=provenance,
            audit_trail=audit_trail,
            bundle_id=bundle_id,
            created_at=datetime.now(),
            expires_at=None,
        )

    def _generate_executive_summary(
        self,
        integrated_result: IntegratedResult,
        attribution_table: AttributionTable,
        case_study_name: str,
    ) -> str:
        """Generate executive summary"""

        risk_level = attribution_table.risk_band
        confidence = attribution_table.confidence_level

        summary = f"""
# Executive Summary: {case_study_name}

## Risk Assessment
**Overall Risk Level:** {risk_level}
**Confidence Level:** {confidence:.1%}
**Composite Risk Score:** {attribution_table.total_risk_score:.1f}/100

## Key Findings
"""

        if risk_level == "RED":
            summary += "- **HIGH RISK**: Multiple coordination indicators detected requiring immediate attention\n"
        elif risk_level == "AMBER":
            summary += "- **MEDIUM RISK**: Borderline coordination patterns detected requiring enhanced monitoring\n"
        else:
            summary += "- **LOW RISK**: No significant coordination indicators detected\n"

        # Add top drivers
        drivers = [
            ("ICP Analysis", attribution_table.icp_contribution),
            ("VMM Analysis", attribution_table.vmm_contribution),
            ("Lead-Lag Patterns", attribution_table.lead_lag_driver),
            ("Mirroring Behavior", attribution_table.mirroring_driver),
            ("Regime Analysis", attribution_table.regime_driver),
            ("Information Flow", attribution_table.infoflow_driver),
        ]

        drivers.sort(key=lambda x: x[1], reverse=True)
        top_drivers = drivers[:3]

        summary += f"\n## Top Risk Drivers\n"
        for driver, score in top_drivers:
            summary += f"- **{driver}**: {score:.1f}/100\n"

        summary += f"\n## Statistical Significance\n"
        summary += f"- **ICP p-value**: {attribution_table.icp_p_value:.4f}\n"
        if attribution_table.vmm_p_value is not None:
            summary += f"- **VMM p-value**: {attribution_table.vmm_p_value:.4f}\n"
        summary += f"- **Lead-Lag Significance**: {attribution_table.lead_lag_significance:.3f}\n"
        summary += f"- **Mirroring Significance**: {attribution_table.mirroring_significance:.3f}\n"

        return summary.strip()

    def _generate_key_findings(
        self,
        integrated_result: IntegratedResult,
        validation_results: Dict[str, Any],
        attribution_table: AttributionTable,
    ) -> List[str]:
        """Generate key findings list"""

        findings = []

        # ICP findings
        if integrated_result.icp_result.reject_h0:
            findings.append(
                f"ICP analysis rejected invariance hypothesis (p={integrated_result.icp_result.p_value:.4f}), indicating coordination patterns"
            )
        else:
            findings.append(
                f"ICP analysis failed to reject invariance hypothesis (p={integrated_result.icp_result.p_value:.4f}), suggesting competitive behavior"
            )

        # VMM findings
        vmm_stability = getattr(integrated_result.vmm_result, "structural_stability", 0.0)
        if vmm_stability > 0.7:
            findings.append(
                f"VMM analysis detected high structural instability ({vmm_stability:.3f}), consistent with coordination"
            )
        else:
            findings.append(
                f"VMM analysis found structural stability ({vmm_stability:.3f}), consistent with competitive behavior"
            )

        # Validation findings
        if validation_results.get("lead_lag"):
            persistence = getattr(validation_results["lead_lag"], "persistence_score", 0.0)
            if persistence > 0.7:
                findings.append(
                    f"Lead-lag analysis detected persistent price leadership patterns (persistence={persistence:.3f})"
                )

        if validation_results.get("mirroring"):
            ratio = getattr(validation_results["mirroring"], "mirroring_ratio", 0.0)
            if ratio > 0.6:
                findings.append(
                    f"Mirroring analysis detected high price similarity (ratio={ratio:.3f})"
                )

        # Data quality findings
        if attribution_table.data_completeness < 0.9:
            findings.append(
                f"Data completeness concerns: {attribution_table.data_completeness:.1%} complete"
            )

        if attribution_table.sample_size_adequacy < 0.8:
            findings.append(
                f"Sample size adequacy concerns: {attribution_table.sample_size_adequacy:.1%} adequate"
            )

        return findings

    def _generate_risk_assessment(self, attribution_table: AttributionTable) -> str:
        """Generate risk assessment section"""

        risk_level = attribution_table.risk_band
        confidence = attribution_table.confidence_level

        assessment = f"""
# Risk Assessment

## Overall Risk Classification: {risk_level}

**Risk Score:** {attribution_table.total_risk_score:.1f}/100
**Confidence Level:** {confidence:.1%}

## Risk Attribution Breakdown

### Component Contributions
- **ICP Analysis**: {attribution_table.icp_contribution:.1f}/100
- **VMM Analysis**: {attribution_table.vmm_contribution:.1f}/100
- **Crypto Moments**: {attribution_table.crypto_moments_contribution:.1f}/100
- **Validation Layers**: {attribution_table.validation_contribution:.1f}/100

### Driver Analysis
- **Lead-Lag Patterns**: {attribution_table.lead_lag_driver:.1f}/100
- **Mirroring Behavior**: {attribution_table.mirroring_driver:.1f}/100
- **Regime Analysis**: {attribution_table.regime_driver:.1f}/100
- **Information Flow**: {attribution_table.infoflow_driver:.1f}/100

## Data Quality Assessment
- **Completeness**: {attribution_table.data_completeness:.1%}
- **Consistency**: {attribution_table.data_consistency:.1%}
- **Sample Size Adequacy**: {attribution_table.sample_size_adequacy:.1%}
"""

        return assessment.strip()

    def _generate_recommendations(
        self, integrated_result: IntegratedResult, attribution_table: AttributionTable
    ) -> List[str]:
        """Generate recommendations based on analysis results"""

        recommendations = []

        # Risk-based recommendations
        if attribution_table.risk_band == "RED":
            recommendations.append(
                "**IMMEDIATE ACTION REQUIRED**: High coordination risk detected - recommend immediate regulatory investigation"
            )
            recommendations.append("Consider regulatory notification and detailed market study")
            recommendations.append("Implement enhanced surveillance and monitoring protocols")
        elif attribution_table.risk_band == "AMBER":
            recommendations.append(
                "**ENHANCED MONITORING**: Medium coordination risk detected - recommend enhanced monitoring"
            )
            recommendations.append("Continue surveillance and consider additional data sources")
            recommendations.append("Prepare for potential escalation if patterns persist")
        else:
            recommendations.append(
                "**ROUTINE MONITORING**: Low coordination risk - continue standard surveillance protocols"
            )
            recommendations.append("Maintain baseline monitoring and periodic review")

        # Confidence-based recommendations
        if attribution_table.confidence_level < 0.7:
            recommendations.append(
                "**LOW CONFIDENCE**: Consider additional data or longer observation period"
            )
            recommendations.append("Review data quality and analysis parameters")

        # Data quality recommendations
        if attribution_table.data_completeness < 0.9:
            recommendations.append("**DATA QUALITY**: Address data completeness issues")

        if attribution_table.sample_size_adequacy < 0.8:
            recommendations.append(
                "**SAMPLE SIZE**: Consider increasing sample size for more reliable results"
            )

        # Methodology recommendations
        recommendations.append("Validate findings with additional data sources and time periods")
        recommendations.append("Consider alternative explanations for observed patterns")
        recommendations.append("Implement ongoing monitoring system for early detection")

        return recommendations

    def _generate_methodology(self, provenance: ProvenanceInfo) -> str:
        """Generate methodology section"""

        methodology = f"""
# Methodology

## Analysis Framework
This analysis uses the Algorithmic Coordination Diagnostic (ACD) framework version {provenance.version}.

## Components
1. **ICP (Invariant Causal Prediction)**: Tests for environment-invariant relationships
2. **VMM (Variational Method of Moments)**: Analyzes structural stability and regime changes
3. **Validation Layers**: Lead-lag, mirroring, HMM regime detection, information flow
4. **Crypto Moments**: Market microstructure analysis specific to crypto markets

## Configuration
- **Analysis ID**: {provenance.analysis_id}
- **Timestamp**: {provenance.timestamp.isoformat()}
- **Seed**: {provenance.seed if provenance.seed else 'Not specified'}

## Data Sources
{chr(10).join(f"- {path}" for path in provenance.data_file_paths)}

## Provenance
- **Content Hash**: {provenance.content_hash}
- **Signature**: {provenance.signature}
"""

        return methodology.strip()

    def _generate_statistical_results(
        self, integrated_result: IntegratedResult, validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate statistical results summary"""

        results = {
            "icp_results": {
                "reject_invariance": integrated_result.icp_result.reject_h0,
                "p_value": integrated_result.icp_result.p_value,
                "effect_size": integrated_result.icp_result.effect_size,
                "power": integrated_result.icp_result.power,
                "n_environments": integrated_result.icp_result.n_environments,
            },
            "vmm_results": {
                "structural_stability": getattr(
                    integrated_result.vmm_result, "structural_stability", None
                ),
                "regime_confidence": getattr(
                    integrated_result.vmm_result, "regime_confidence", None
                ),
                "convergence_status": getattr(
                    integrated_result.vmm_result, "convergence_status", None
                ),
                "iterations": getattr(integrated_result.vmm_result, "iterations", None),
            },
            "validation_results": {},
        }

        # Add validation results
        for layer_name, layer_result in validation_results.items():
            if layer_result is not None:
                results["validation_results"][layer_name] = self._extract_layer_results(
                    layer_name, layer_result
                )

        return results

    def _extract_layer_results(self, layer_name: str, layer_result: Any) -> Dict[str, Any]:
        """Extract key results from validation layer"""

        if layer_name == "lead_lag":
            return {
                "persistence_score": getattr(layer_result, "persistence_score", None),
                "switching_entropy": getattr(layer_result, "switching_entropy", None),
                "avg_granger_p": getattr(layer_result, "avg_granger_p", None),
                "n_windows": getattr(layer_result, "n_windows", None),
            }

        elif layer_name == "mirroring":
            return {
                "mirroring_ratio": getattr(layer_result, "mirroring_ratio", None),
                "coordination_score": getattr(layer_result, "coordination_score", None),
                "avg_cosine_similarity": getattr(layer_result, "avg_cosine_similarity", None),
                "avg_pearson_correlation": getattr(layer_result, "avg_pearson_correlation", None),
            }

        elif layer_name == "hmm":
            return {
                "regime_stability": getattr(layer_result, "regime_stability", None),
                "coordination_regime_score": getattr(
                    layer_result, "coordination_regime_score", None
                ),
                "n_states": getattr(layer_result, "n_states", None),
                "log_likelihood": getattr(layer_result, "log_likelihood", None),
            }

        elif layer_name == "infoflow":
            return {
                "information_hub_score": getattr(layer_result, "information_hub_score", None),
                "coordination_network_score": getattr(
                    layer_result, "coordination_network_score", None
                ),
                "avg_transfer_entropy": getattr(layer_result, "avg_transfer_entropy", None),
                "network_density": getattr(layer_result, "network_density", None),
            }

        return {}

    def _generate_data_tables(self, validation_results: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Generate data tables for regulatory bundle"""

        tables = {}

        # Create summary table
        summary_data = []
        for layer_name, layer_result in validation_results.items():
            if layer_result is not None:
                summary_data.append(
                    {
                        "Layer": layer_name,
                        "Status": "Completed",
                        "Key_Metric": self._get_key_metric(layer_name, layer_result),
                    }
                )
            else:
                summary_data.append(
                    {"Layer": layer_name, "Status": "Not Available", "Key_Metric": "N/A"}
                )

        tables["validation_summary"] = pd.DataFrame(summary_data)

        return tables

    def _get_key_metric(self, layer_name: str, layer_result: Any) -> str:
        """Get key metric for a validation layer"""

        if layer_name == "lead_lag":
            persistence = getattr(layer_result, "persistence_score", None)
            return f"Persistence: {persistence:.3f}" if persistence is not None else "N/A"

        elif layer_name == "mirroring":
            ratio = getattr(layer_result, "mirroring_ratio", None)
            return f"Ratio: {ratio:.3f}" if ratio is not None else "N/A"

        elif layer_name == "hmm":
            stability = getattr(layer_result, "regime_stability", None)
            return f"Stability: {stability:.3f}" if stability is not None else "N/A"

        elif layer_name == "infoflow":
            hub_score = getattr(layer_result, "information_hub_score", None)
            return f"Hub Score: {hub_score:.3f}" if hub_score is not None else "N/A"

        return "N/A"

    def _generate_audit_trail(self, provenance: ProvenanceInfo) -> List[str]:
        """Generate audit trail"""

        trail = [
            f"Analysis initiated: {provenance.timestamp.isoformat()}",
            f"Analysis ID: {provenance.analysis_id}",
            f"Version: {provenance.version}",
            f"Seed: {provenance.seed if provenance.seed else 'Not specified'}",
            f"Data files: {len(provenance.data_file_paths)} files",
            f"Content hash: {provenance.content_hash}",
            f"Signature: {provenance.signature}",
            f"Bundle generated: {datetime.now().isoformat()}",
        ]

        return trail

    def save_bundle(self, bundle: RegulatoryBundle, format: str = "json") -> Dict[str, str]:
        """
        Save regulatory bundle to files

        Args:
            bundle: Regulatory bundle to save
            format: Output format ("json", "pdf", or "both")

        Returns:
            Dictionary with file paths
        """

        file_paths = {}

        # Create bundle directory
        bundle_dir = self.output_dir / bundle.bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON format
        if format in ["json", "both"]:
            json_path = bundle_dir / f"{bundle.bundle_id}.json"
            self._save_bundle_json(bundle, json_path)
            file_paths["json"] = str(json_path)

        # Save PDF format (placeholder for now)
        if format in ["pdf", "both"]:
            pdf_path = bundle_dir / f"{bundle.bundle_id}.pdf"
            self._save_bundle_pdf(bundle, pdf_path)
            file_paths["pdf"] = str(pdf_path)

        # Save attribution table separately
        attribution_path = bundle_dir / f"{bundle.bundle_id}_attribution.json"
        self._save_attribution_table(bundle.attribution_table, attribution_path)
        file_paths["attribution"] = str(attribution_path)

        # Save provenance separately
        provenance_path = bundle_dir / f"{bundle.bundle_id}_provenance.json"
        self._save_provenance(bundle.provenance, provenance_path)
        file_paths["provenance"] = str(provenance_path)

        logger.info(f"Regulatory bundle saved to {bundle_dir}")
        return file_paths

    def _save_bundle_json(self, bundle: RegulatoryBundle, file_path: Path) -> None:
        """Save bundle as JSON"""

        # Convert bundle to dictionary
        bundle_dict = {
            "bundle_id": bundle.bundle_id,
            "created_at": bundle.created_at.isoformat(),
            "expires_at": bundle.expires_at.isoformat() if bundle.expires_at else None,
            "executive_summary": bundle.executive_summary,
            "key_findings": bundle.key_findings,
            "risk_assessment": bundle.risk_assessment,
            "recommendations": bundle.recommendations,
            "methodology": bundle.methodology,
            "attribution_table": asdict(bundle.attribution_table),
            "statistical_results": bundle.statistical_results,
            "alternative_explanations": bundle.alternative_explanations,
            "provenance": asdict(bundle.provenance),
            "audit_trail": bundle.audit_trail,
        }

        with open(file_path, "w") as f:
            json.dump(bundle_dict, f, indent=2, default=str)

    def _save_bundle_pdf(self, bundle: RegulatoryBundle, file_path: Path) -> None:
        """Save bundle as PDF (placeholder implementation)"""

        # For now, create a simple text file
        # In production, this would generate a proper PDF
        with open(file_path.with_suffix(".txt"), "w") as f:
            f.write(bundle.executive_summary)
            f.write("\n\n")
            f.write(bundle.risk_assessment)
            f.write("\n\n")
            f.write(bundle.methodology)
            f.write("\n\n")
            f.write("Key Findings:\n")
            for finding in bundle.key_findings:
                f.write(f"- {finding}\n")
            f.write("\n")
            f.write("Recommendations:\n")
            for rec in bundle.recommendations:
                f.write(f"- {rec}\n")

    def _save_attribution_table(self, attribution_table: AttributionTable, file_path: Path) -> None:
        """Save attribution table separately"""

        with open(file_path, "w") as f:
            json.dump(asdict(attribution_table), f, indent=2, default=str)

    def _save_provenance(self, provenance: ProvenanceInfo, file_path: Path) -> None:
        """Save provenance information separately"""

        with open(file_path, "w") as f:
            json.dump(asdict(provenance), f, indent=2, default=str)


def generate_regulatory_bundle(
    integrated_result: IntegratedResult,
    validation_results: Dict[str, Any],
    data_quality_metrics: Dict[str, float],
    case_study_name: str = "ACD Analysis",
    output_dir: str = "artifacts/reports",
    seed: Optional[int] = None,
) -> Tuple[RegulatoryBundle, Dict[str, str]]:
    """
    Convenience function to generate and save regulatory bundle

    Args:
        integrated_result: Results from integrated analysis
        validation_results: Results from validation layers
        data_quality_metrics: Data quality assessment metrics
        case_study_name: Name of the case study
        output_dir: Output directory for reports
        seed: Random seed used

    Returns:
        Tuple of (RegulatoryBundle, file_paths)
    """

    # Initialize generator
    generator = ReportV2Generator(output_dir)

    # Generate attribution table
    attribution_table = generator.generate_attribution_table(
        integrated_result, validation_results, data_quality_metrics
    )

    # Generate provenance info
    analysis_id = f"ACD_{case_study_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    provenance = generator.generate_provenance_info(
        analysis_id=analysis_id,
        data_file_paths=[],  # Will be populated by caller
        configs={},  # Will be populated by caller
        result_file_paths={},  # Will be populated by caller
        seed=seed,
    )

    # Generate regulatory bundle
    bundle = generator.generate_regulatory_bundle(
        integrated_result, validation_results, attribution_table, provenance, case_study_name
    )

    # Save bundle
    file_paths = generator.save_bundle(bundle, format="both")

    return bundle, file_paths


if __name__ == "__main__":
    # Example usage
    print("ACD Reporting v2 - Attribution Tables and Provenance-Tracked Outputs")
    print("This module provides enhanced reporting capabilities for regulatory readiness.")
